# ShadowFleet OS

**AI-powered maritime deception detection for gray-zone warfare, sanctions enforcement, and naval domain awareness.**

> We help commanders detect when a ship is lying.

ShadowFleet OS fuses AIS, satellite imagery, IMO registry history, ownership records, port calls, route plausibility, ship-to-ship proximity, flag changes, and sanctions lists into a per-vessel deception risk score with an evidence-backed interdiction brief.

See [CONTEXT.md](CONTEXT.md) for the full origin pitch and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the system overview.

---

## Quickstart

### Prereqs

- Python 3.11+
- Node 20+ with [pnpm](https://pnpm.io/)
- [uv](https://github.com/astral-sh/uv) for Python package management

### Install

```bash
make install
```

This runs `uv sync` in `backend/` and `pnpm install` in `frontend/`.

### Configure

```bash
cp backend/.env.example backend/.env
# fill in ANTHROPIC_API_KEY and any other keys you have
```

### Run

```bash
# Both at once (backend in background, frontend in foreground)
make dev

# Or in separate terminals
make backend     # http://localhost:8000  (FastAPI + auto-reload)
make frontend    # http://localhost:5173  (Vite dev server)
```

### Seed demo data

```bash
make seed
```

### Test

```bash
make test
```

---

## Project layout

```
shadowfleet/
├── backend/         FastAPI + SQLAlchemy + SQLite + Anthropic SDK
├── frontend/        Vite + React + TS + Tailwind + Leaflet + D3
└── docs/            architecture, scoring rubric, demo flow
```

---

## Status

Pre-build scaffold. All services and clients are stubbed (`raise NotImplementedError`) — fill them in incrementally.
