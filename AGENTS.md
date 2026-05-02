# AGENTS.md

## Mission

Build ShadowFleet OS as an explainable maritime deception detection MVP for
gray-zone warfare, sanctions enforcement, and maritime domain awareness.

A vessel's "maritime story" is the picture it paints of itself through AIS,
flag, ownership, route, and port history. ShadowFleet OS detects when that
story does not match reality, then generates a transparent analyst
assessment with evidence and recommended next actions.

## Working rules

- Prefer deterministic, evidence-backed heuristics over opaque ML in v1.
- Never scrape login-gated or paid maritime sources. If access is unavailable,
  create provider interfaces plus fixture/mock implementations.
- Every detection must store source provenance, timestamps, and geospatial
  context.
- Recommended actions must remain analyst-supportive: `monitor`, `investigate`,
  `sanctions review`, `notify command`. No autonomous enforcement, no
  categorical "illegal vessel" labels.
- Keep provider integrations (`app/clients/`) separate from detection logic
  (`app/detectors/`) and orchestration (`app/services/`).
- Write or update tests for every new detector and API feature.
- Update docs whenever architecture, commands, or behavior change.
- Make reasonable assumptions and document them. Do not stop the build because
  a real data integration is unavailable — mock it cleanly behind an interface.

## Stack (current vs target)

| Layer | Current | Target | Migration trigger |
|---|---|---|---|
| Backend | Python 3.11+ + FastAPI | same | — |
| ORM | SQLAlchemy 2.0 | same | — |
| Database | SQLite | PostgreSQL + PostGIS | When spatial queries appear (geofence joins, etc.) |
| Frontend | Vite + React + TS + Tailwind | same | — |
| Map | Leaflet + CartoDB Dark | MapLibre GL | When WebGL marker styling becomes the bottleneck |
| LLM | Anthropic SDK (claude-sonnet-4-5) | same | — |
| Backend tests | pytest | same | — |
| Frontend tests | TS strict + (Vitest TBD) | Vitest | When component logic gets complex enough to warrant unit tests |
| Local dev | `uv` + `pnpm` direct | `docker compose --profile full up` | Optional — for parity with prod |
| Package mgmt | uv (Python), pnpm (JS) | same | — |

## Repo layout

```
backend/
  app/
    main.py            FastAPI factory, CORS, lifespan
    config.py          Pydantic-settings (.env)
    db.py              SQLAlchemy engine + Base + init_db
    models/            Vessel, Owner, FlagHistory, AISGap, Encounter,
                       PortCall, STSTransfer, RiskScore, ScoreComponent, Evidence
    schemas/           Pydantic v2 response/request shapes
    routers/           vessels, scores, briefs, network, satellite, evidence
    detectors/         dark_activity, kinematic_anomaly, sts_proximity,
                       sanctions_match, identity_inconsistency, route_plausibility
    services/          scoring, brief_generator, network_builder, playbook_matcher
    clients/           gfw, ofac, copernicus, equasis  (real or fixture-backed)
    seed/              demo_vessels.py (the demo_shadow_001 scenario)
  tests/               smoke + full pipeline test
  pyproject.toml
  .env.example
  Dockerfile           production image (used by `docker compose --profile full up`)

frontend/
  src/
    main.tsx, App.tsx
    components/        Header, VesselList, VesselMap, VesselDetail,
                       ScoreBreakdown, EvidenceTimeline, OwnershipGraph,
                       SARViewer, InterdictionBrief, Legend
    lib/               api.ts, types.ts, score.ts
    styles/index.css
  vite.config.ts (proxies /api -> :8000)
  Dockerfile           multi-stage nginx build
  nginx.conf

docs/                  ARCHITECTURE, SCORING_RUBRIC, DEMO_FLOW
docker-compose.yml     postgres+postgis (optional), backend+frontend (full profile)
Makefile               install, dev, backend, frontend, seed, test
```

## Commands

```bash
# install everything
cd backend && uv sync
cd frontend && pnpm install

# seed the demo scenario (58 vessels, 6 detectors, scores precomputed)
cd backend && uv run python -m app.seed.demo_vessels

# run
cd backend && uv run uvicorn app.main:app --reload --port 8000
cd frontend && pnpm dev

# test
cd backend && uv run pytest -q
cd frontend && pnpm typecheck
```

## Definition of done (phase-1 MVP — currently met)

- ✅ App boots locally (uvicorn + vite dev both clean)
- ✅ Demo fixture `demo_shadow_001` loads via the seed module
- ✅ `GET /vessels/{imo}/score` returns score + transparent component breakdown
- ✅ `POST /vessels/{imo}/brief` returns an evidence-backed analyst brief
- ✅ UI renders map + vessel detail + score breakdown + evidence + network + SAR + brief
- ✅ Detector + integration tests pass
- ✅ README and docs explain setup, what is real, what is mocked

## Detector contract

Every detector under `backend/app/detectors/` exports:

```python
NAME: str            # rubric component name (e.g. "dark_activity")
WEIGHT: int          # rubric weight; total across all detectors = RUBRIC_MAX
def detect(db: Session, vessel: Vessel) -> DetectorResult: ...
```

`DetectorResult` carries an aggregated `value` (0..1) and a list of
`EvidencePayload` records. The scoring engine in `services/scoring.py` walks
`ALL_DETECTORS`, persists `RiskScore` + `ScoreComponent` + `Evidence`, and
normalizes the raw total to 0–1000.

## Evidence object schema

Every detector emits one or more evidence records that an analyst can trace:

```python
{
  "id": int,
  "vessel_imo": str,
  "detector_name": str,
  "title": str,                # one short line
  "description": str,          # one paragraph, evidence-grounded
  "source_type": "ais|sanctions|registry|satellite|port",
  "source_ref": str,           # e.g. "ofac://sdn/owner/12", "aisgap://4"
  "start_time": datetime | None,
  "end_time": datetime | None,
  "geometry": dict,            # GeoJSON
  "severity": "low|medium|high|critical",
  "confidence": float,         # 0..1
  "score_contribution": int,
  "analyst_notes": str | None,
}
```

These are persisted, returned by the API at `GET /vessels/{imo}/evidence`,
and rendered verbatim in the UI Evidence tab so every alert traces back.

## Risk engine

- Six implemented detectors, weights sum to `RUBRIC_MAX = 860`.
- Total = `round(sum(component contributions) * 1000 / RUBRIC_MAX)`, clamped 0–1000.
- Bands: low 0–249 · medium 250–549 · high 550–799 · critical 800+
- Recommendation: `monitor → investigate → sanctions review → notify command`.

## Demo scenario `demo_shadow_001`

Hero vessel: **IMO 9876543 / ATLANTIS PIONEER** under flag Cook Islands. Curated to score in the **critical** band (~819) with five firing detectors:

- 16h AIS dark window inside a known STS-transfer corridor (Arabian Sea)
- Implied speed > 80 kn across an 18h dark gap (impossible kinematics)
- 3h open-water encounter with sanctioned sister vessel `KRUSHEVA`
- Owner chain: Marshall Pacific Holdings (shell) → Hong Kong Pearl Maritime (shell, OFAC SDN) → Sovcomflot OJSC (OFAC SDN)
- Four flag changes in 12 months ending on a flag of convenience

47 routine vessels and 8 medium-risk vessels round out the map.

## Data and integration discipline

| Source | v1 status | Notes |
|---|---|---|
| AIS positions / encounters | Seeded fixtures | Real GFW client behind `app/clients/gfw.py`, token-gated |
| OFAC SDN list | Bundled subset | Replace with public XML feed in `ofac.py` |
| Equasis ownership / flag history | Read from local DB | Real Equasis is registration-gated |
| Sentinel-1 SAR | Curated demo overlay | OAuth + scene fetch stubbed in `copernicus.py` |
| NGA WPI / UN/LOCODE port metadata | Inline subset in `route_plausibility.py` | Bundle full lists when route logic gets richer |

Mocked adapters present the same call signatures real ones will. Always
document which providers are real vs simulated in the README table.

## Verification

Codex performs better when "done" is concrete. Before declaring a task done:

1. `uv run pytest -q` passes.
2. `pnpm typecheck` passes.
3. `uvicorn` + `vite dev` both still boot.
4. Summarize: what was implemented, what is mocked, what should be replaced
   with real providers later.

If a recurring wrong pattern shows up, run a retrospective and update this
file rather than re-stating the rule in chat.
