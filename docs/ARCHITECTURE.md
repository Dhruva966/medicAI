# ShadowFleet OS — Architecture

System overview. Implementation lives under `backend/` and `frontend/`.

## High level

```
                 ┌──────────────────┐
                 │     Frontend     │  React + Tailwind + Leaflet (CartoDB dark)
                 │  (Vite, :5173)   │  + D3 force layout for ownership graph
                 └────────┬─────────┘
                          │ JSON over HTTP (proxied /api -> :8000)
                          ▼
                 ┌──────────────────┐
                 │     Backend      │  FastAPI routers
                 │  (uvicorn, :8000)│  /vessels · /scores · /briefs ·
                 │                  │  /network · /satellite · /evidence
                 └────────┬─────────┘
                          │
        ┌─────────────────┼────────────────────┐
        ▼                 ▼                    ▼
   ┌─────────┐       ┌─────────┐          ┌──────────┐
   │ Detect- │       │ SQLite  │          │ External │
   │  ors    │       │  + ORM  │          │ Clients  │
   ├─────────┤       ├─────────┤          ├──────────┤
   │ dark_   │       │ Vessel  │          │  GFW     │ AIS
   │ activ.  │       │ Owner   │          │  OFAC    │ SDN
   │ kinem.  │       │ Events  │          │ Coperni. │ SAR
   │ sts     │       │ Scores  │          │ Equasis  │ Ownership
   │ sancti. │       │ Evidence│          └──────────┘
   │ ident.  │       └─────────┘
   │ route   │
   └─────────┘
        │
        ▼
   ┌──────────────────┐
   │   Services       │
   ├──────────────────┤
   │ scoring          │ ← detectors → ScoreComponent + Evidence rows
   │ brief_generator  │ ← Anthropic Claude OR deterministic template
   │ network_builder  │ ← walks Owner.parent_owner_id, surfaces SDN ties
   │ playbook_matcher │ ← named patterns (dark_transfer, flag_hop_laundering, identity_swap)
   └──────────────────┘
```

## Pipeline

1. **Ingest** — clients (GFW, OFAC, Copernicus, Equasis) populate SQLAlchemy tables. v1 ships seeded fixtures.
2. **Detect** — six modules under `app/detectors/` walk the events for one vessel and emit `DetectorResult` containing an aggregated value and a list of `EvidencePayload` records.
3. **Score** — `services/scoring.py` runs every detector, persists `RiskScore` + `ScoreComponent` + `Evidence`, and normalizes the raw total to 0–1000 (see [SCORING_RUBRIC.md](SCORING_RUBRIC.md)).
4. **Classify** — `services/playbook_matcher.py` tags named evasion patterns from detector signal combinations.
5. **Brief** — `services/brief_generator.py` packages evidence + components and either calls Claude (when `ANTHROPIC_API_KEY` is set) or runs a deterministic template.
6. **Render** — frontend pulls everything for the selected vessel: map track, score breakdown, evidence timeline, ownership graph, SAR overlay, brief.

## Data model

`backend/app/models/`:

- `vessel.py` — `Vessel`, `Owner`, `FlagHistory`
- `event.py` — `AISGap`, `Encounter`, `PortCall`, `STSTransfer`
- `score.py` — `RiskScore`, `ScoreComponent`
- `evidence.py` — `Evidence` (linked to `score_component_id` so every alert traces back)

Relationships:

- `Vessel.owner` → `Owner` → `Owner.parent` (recursive)
- `RiskScore.components` → `ScoreComponent.evidence_records` → `Evidence`
- `Encounter.sts_transfer` → `STSTransfer` (1-1)

## Out of scope (hackathon cut)

- Auth / multi-tenant
- Real-time AIS streaming (use snapshots / seed data)
- Database migrations (SQLAlchemy `create_all` on startup)
- CI / deploy automation
