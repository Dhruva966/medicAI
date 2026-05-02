# ShadowFleet OS

**AI-powered maritime deception detection for gray-zone warfare, sanctions enforcement, and naval domain awareness.**

> We help commanders detect when a ship is lying.

ShadowFleet OS fuses AIS, satellite imagery, IMO registry history, ownership records, port calls, route plausibility, ship-to-ship proximity, flag changes, and sanctions lists into a per-vessel deception risk score with an evidence-backed interdiction brief.

See [CONTEXT.md](CONTEXT.md) for the founding pitch, [AGENTS.md](AGENTS.md) for the build contract, [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for system shape, and [docs/SCORING_RUBRIC.md](docs/SCORING_RUBRIC.md) for the rubric.

---

## What's in the box

**Phase-1 MVP, working end to end.**

- Curated demo scenario `demo_shadow_001` with **58 vessels** — one critical-band hero (`ATLANTIS PIONEER`, IMO 9876543) flanked by routine traffic
- Six explainable detectors: dark-activity, kinematic anomaly, STS proximity, sanctions match, identity inconsistency, route plausibility
- Transparent 0–1000 risk score with per-component contribution and full evidence trail
- Per-vessel interdiction brief (deterministic template by default, optional Claude when `ANTHROPIC_API_KEY` is set)
- D3 force-directed ownership network reaching sanctioned parents and sister vessels
- SAR vs AIS cross-check view (curated demo overlay)
- Beautiful dark-mode operator console with searchable vessel list and live world map

```
backend/        FastAPI + SQLAlchemy + SQLite + Anthropic SDK + 6 detectors
frontend/       Vite + React + TS + Tailwind + Leaflet + D3
docs/           ARCHITECTURE, SCORING_RUBRIC, DEMO_FLOW
docker-compose  Optional Postgres + PostGIS production-stack path
```

---

## Quickstart

### Prereqs

- Python 3.11+ and [uv](https://github.com/astral-sh/uv)
- Node 20+ and [pnpm](https://pnpm.io/)

### Install + seed + run

```bash
# 1. Backend
cd backend
uv sync
cp .env.example .env                                 # optional — fill keys later
uv run python -m app.seed.demo_vessels               # seeds 58 vessels + scores
uv run uvicorn app.main:app --reload --port 8000

# 2. Frontend (in another terminal)
cd frontend
pnpm install
pnpm dev                                              # http://localhost:5173
```

Open `http://localhost:5173` and click `ATLANTIS PIONEER` in the left list — the side panel walks through the score, evidence, ownership network, SAR cross-check, and a one-click interdiction brief.

### Tests

```bash
cd backend && uv run pytest -q     # 4 tests, full pipeline coverage
cd frontend && pnpm typecheck       # strict TS
```

---

## What's real, what needs setup

This was scaffolded by an AI agent with no live access to commercial maritime data feeds. The architecture is honest about what's wired up and what's a clean adapter waiting for credentials.

| Capability | Status | What's needed |
|---|---|---|
| FastAPI app + routes | ✅ Real | — |
| SQLAlchemy models + SQLite | ✅ Real | — |
| Six deception detectors | ✅ Real | — |
| Score rubric + persistence | ✅ Real | — |
| Evidence records + timeline | ✅ Real | — |
| Ownership graph builder | ✅ Real | — |
| Demo scenario `demo_shadow_001` | ✅ Real | — |
| Interdiction brief (template) | ✅ Real | — |
| Interdiction brief (Claude) | 🟡 Wired | Set `ANTHROPIC_API_KEY` in `backend/.env` |
| OFAC SDN list | 🟡 Bundled fixture | Replace `_BUNDLED_SDN` with the public XML feed in `app/clients/ofac.py` |
| Global Fishing Watch AIS | 🟡 Adapter only | Set `GFW_TOKEN`, implement the three stub methods in `app/clients/gfw.py` |
| Equasis ownership/flag history | 🟡 Reads from local DB | Real Equasis is registration-gated — see `app/clients/equasis.py` |
| Sentinel-1 SAR overlay | 🟡 Curated demo data | Set `COPERNICUS_*` keys, implement OAuth + scene fetch in `app/clients/copernicus.py` |
| Postgres + PostGIS | 🟡 Optional | `docker compose up -d postgres` + set `DATABASE_URL` |
| MapLibre GL | ⏳ Future | Currently using Leaflet with CartoDB Dark tiles |
| Vitest frontend tests | ⏳ Future | TS strict-mode is enforced via `pnpm typecheck` |

### Optional: switch to Postgres + PostGIS

The hackathon scaffold uses SQLite so there's no infra setup. To run against PostGIS:

```bash
docker compose up -d postgres
export DATABASE_URL=postgresql+psycopg://shadowfleet:shadowfleet@localhost:5433/shadowfleet
cd backend && uv run python -m app.seed.demo_vessels
uv run uvicorn app.main:app --reload --port 8000
```

Once you actually need spatial queries (geofence intersections, proximity joins), wire up GeoAlchemy2 in `app/models/evidence.py` to replace the JSON-blob geometry storage with native `Geometry` columns. The detectors are written so this swap is local.

### Optional: full-container dev

```bash
docker compose --profile full up
# backend on :8000, frontend on :5173, postgres on :5433
```

---

## Demo flow (3 min)

See [docs/DEMO_FLOW.md](docs/DEMO_FLOW.md) for the script. TL;DR:

1. **The map.** 58 vessels worldwide, one pulses red.
2. **Click it.** `ATLANTIS PIONEER`. Score 819, **CRITICAL**. Recommendation: *notify command*.
3. **Score breakdown.** Five detectors firing — dark gap, STS encounter, impossible speed, sanctioned ownership chain, flag-hopping.
4. **Evidence tab.** Every alert traces back to a stored, citable record with severity, source, and confidence.
5. **Network tab.** Hero → shell company → sanctioned shell → Sovcomflot OJSC. Sister vessel `KRUSHEVA` is on the OFAC SDN list.
6. **SAR tab.** AIS-reported position vs SAR detection during the dark window — different ocean.
7. **Brief tab.** One-click structured interdiction brief, copyable as markdown.

---

## Architecture & docs

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — system overview
- [docs/SCORING_RUBRIC.md](docs/SCORING_RUBRIC.md) — the 0–1000 rubric
- [docs/DEMO_FLOW.md](docs/DEMO_FLOW.md) — 3-minute demo script
- [AGENTS.md](AGENTS.md) — the build contract for AI agents working in this repo
- [CONTEXT.md](CONTEXT.md) — origin pitch and framing
