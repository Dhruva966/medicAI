# ShadowFleet OS — Architecture

One-page system overview. Implementation lives under `backend/` and `frontend/`.

## High level

```
                 ┌──────────────────┐
                 │     Frontend     │  React + Leaflet map + D3 ownership graph
                 │  (Vite, :5173)   │  ScoreBreakdown · InterdictionBrief · SARViewer
                 └────────┬─────────┘
                          │ JSON over HTTP
                          ▼
                 ┌──────────────────┐
                 │     Backend      │  FastAPI routers
                 │  (uvicorn, :8000)│  /vessels · /scores · /briefs · /network · /satellite
                 └────────┬─────────┘
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
   ┌─────────┐       ┌─────────┐       ┌─────────┐
   │Services │       │ SQLite  │       │External │
   │         │       │  + ORM  │       │ Clients │
   ├─────────┤       ├─────────┤       ├─────────┤
   │ scoring │       │ Vessel  │       │  GFW    │ (Global Fishing Watch)
   │ brief   │       │ Owner   │       │  OFAC   │ (sanctions list)
   │ network │       │ Events  │       │ Coperni │ (Sentinel-1 SAR)
   │ playbook│       │ Scores  │       │ Equasis │ (ownership/flag)
   └─────────┘       └─────────┘       └─────────┘
        │
        ▼
   ┌─────────┐
   │ Claude  │   Anthropic SDK — generates the interdiction brief
   │ sonnet  │   from structured evidence + score breakdown
   │  4.5    │
   └─────────┘
```

## Pipeline

1. **Ingest** — clients pull AIS gaps, port calls, ownership history, sanctions hits, SAR overlays into SQLAlchemy tables.
2. **Score** — `services/scoring.py` runs the rubric (see [SCORING_RUBRIC.md](SCORING_RUBRIC.md)) and writes `RiskScore` + `ScoreComponent` rows.
3. **Classify** — `services/playbook_matcher.py` tags known evasion patterns (dark transfer, flag-hop, identity laundering).
4. **Brief** — `services/brief_generator.py` packages the evidence and asks Claude for an interdiction-ready writeup.
5. **Render** — frontend pulls everything for a clicked vessel: map track, score breakdown, ownership graph, SAR overlay, brief.

## Data model

See `backend/app/models/`:
- `vessel.py` — `Vessel`, `Owner`, `FlagHistory`
- `event.py` — `AISGap`, `Encounter`, `PortCall`, `STSTransfer`
- `score.py` — `RiskScore`, `ScoreComponent`

## Out of scope (hackathon cut)

- Auth / multi-tenant
- Real-time AIS streaming (use snapshots / seed data)
- Database migrations (SQLAlchemy `create_all` on startup)
- Docker / CI / deploy
