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
- Keep provider integrations (clients/) separate from domain logic
  (services/, detectors/).
- Write or update tests for every new detector and API feature.
- Update docs whenever architecture, commands, or behavior change.
- Make reasonable assumptions and document them. Do not stop the build because
  a real data integration is unavailable — mock it cleanly behind an interface.

## Preferred stack

- Backend: Python 3.11+ + FastAPI
- Database: PostgreSQL + PostGIS (current scaffold uses SQLite — migrate when
  geospatial queries arrive)
- Frontend: React + TypeScript + Vite + MapLibre (current scaffold uses
  Leaflet — swap when implementing the map)
- Local dev: Docker Compose (not yet scaffolded — add when introducing
  Postgres/PostGIS)
- Backend tests: pytest
- Frontend tests: Vitest
- Package mgmt: uv (Python), pnpm (frontend)

## Repo layout

```
backend/         FastAPI app: app/{config,db,main}.py, models, schemas,
                 routers, services, clients, seed, tests
frontend/        Vite + React + TS: src/{components,lib,styles}
docs/            ARCHITECTURE.md, SCORING_RUBRIC.md, DEMO_FLOW.md
.env.example     in backend/ — every external key the app needs
Makefile         install, dev, backend, frontend, seed, test
```

Read `docs/ARCHITECTURE.md` for system shape and `docs/SCORING_RUBRIC.md` for
the rubric. The scaffold leaves every detector / service / external client
as `raise NotImplementedError` — fill them in incrementally.

## Commands

```
# install everything
cd backend && uv sync
cd frontend && pnpm install

# run
cd backend && uv run uvicorn app.main:app --reload --port 8000
cd frontend && pnpm dev

# test
cd backend && uv run pytest -q
cd frontend && pnpm typecheck
```

## Definition of done (phase-1 MVP)

- The app boots locally (`uvicorn` + `vite dev` both start cleanly).
- Demo fixture `demo_shadow_001` loads via `make seed`.
- `GET /vessels/{imo}/score` returns score + transparent component breakdown.
- `POST /vessels/{imo}/brief` returns an evidence-backed analyst brief.
- The UI renders map + vessel detail + score breakdown + brief flow for the
  selected vessel.
- Detector unit tests + at least one end-to-end API integration test pass.
- README and docs explain setup, what is real, what is mocked, and the
  assumptions made.

## Required detectors

Implement under `backend/app/services/` (or split into `backend/app/detectors/`
when the file gets too long):

- `dark_activity` — extended AIS gaps, especially in known STS zones
- `kinematic_anomaly` — impossible jumps, implausible speed, teleports
- `sts_proximity` — low-speed close encounters consistent with ship-to-ship
  transfer
- `sanctions_match` — direct OFAC SDN hits + N-hop ownership proximity
- `identity_inconsistency` — MMSI / IMO / name / call-sign desync between sources
- `route_plausibility` — stated route inconsistent with port history, draft,
  or fuel range

All feed into `services/scoring.py` with weighted, configurable contributions
(see `docs/SCORING_RUBRIC.md`).

## Evidence object schema

Every detector emits one or more evidence records that an analyst can trace:

```
{
  "id": "...",
  "vessel_imo": "...",
  "detector_name": "dark_activity",
  "title": "11h AIS gap near Lakonikos Gulf STS zone",
  "description": "...",
  "source_type": "ais|sanctions|registry|satellite|port",
  "source_ref": "gfw://track/123 or ofac://sdn/2024-12-04 etc.",
  "start_time": "...",
  "end_time": "...",
  "geometry": {...},          # GeoJSON
  "severity": "low|medium|high|critical",
  "confidence": 0.0,           # 0..1
  "score_contribution": 0,     # contributes to RiskScore
  "analyst_notes": null
}
```

These should be persisted, returned by the API, and surfaced verbatim in the
UI so every alert traces back to stored evidence.

## Risk engine requirements

- Weighted transparent scoring 0–1000 (see `docs/SCORING_RUBRIC.md`).
- Weights live in one place and are configurable.
- Score breakdown returned by API alongside the total.
- Recommendation derived from score band: `monitor | investigate | sanctions review | notify command`.

## Demo scenario `demo_shadow_001`

A curated fixture for the demo. Should include:

- A tanker-like vessel with realistic identity.
- A meaningful AIS dark period (≥6h) overlapping a known STS zone.
- A plausible suspicious proximity event (low speed, open water, > 1h).
- A sanctions-or-ownership-risk link via fixture data (shell company two hops
  from an SDN-listed vessel).
- A route plausibility problem (port history inconsistent with current course).
- Enough corroborating evidence to produce a high-band score.

## Data and integration discipline

Use real integrations only where access is immediate and clearly legal:

- **AIS:** NOAA AccessAIS archive for fixtures; Global Fishing Watch behind a
  client interface (token in `.env`).
- **Sanctions:** OFAC SDN list — ingest the public XML directly.
- **Registry / ownership:** Equasis is registration-gated; build adapter +
  mock, do not scrape.
- **Satellite:** Sentinel-1 SAR / Sentinel-2 optical via Copernicus Data Space —
  curated demo scenes only in v1.
- **Night detections:** VIIRS Boat Detection — adapter + mock for v1.
- **Port metadata:** NGA World Port Index, UN/LOCODE — bundle locally.

Mocked adapters must look identical to real ones from the calling code's
perspective. Document which providers are real vs simulated in the README.

## Verification

Codex performs better when "done" is concrete. Before declaring a task done:

1. `uv run pytest -q` passes.
2. `pnpm typecheck` passes.
3. `uvicorn` + `vite dev` both still boot.
4. Summarize: what was implemented, what is mocked, what should be replaced
   with real providers later.

If Codex repeatedly hits the same wrong pattern, run a retrospective and
update this file rather than re-stating the rule in chat.
