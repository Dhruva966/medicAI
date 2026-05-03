"""AISStream.io — live AIS WebSocket client.

This module exposes a single status() probe and the WebSocket URL.
The actual streaming consumer lives in app.ingest.aisstream_listener.

NEEDS-SETUP-FOR-PRODUCTION:
  - Register at https://aisstream.io and get a free API key
  - Set AISSTREAM_KEY in backend/.env
  - Run `uv run python -m app.ingest.run`
"""

from typing import Any

from app.config import get_settings

WS_URL = "wss://stream.aisstream.io/v0/stream"


def status() -> dict[str, Any]:
    s = get_settings()
    configured = bool(s.aisstream_key)
    return {
        "configured": configured,
        "mode": "live" if (configured and s.live_data_mode) else "mock",
        "ws_url": WS_URL,
        "bbox": s.ais_bbox if configured else None,
        "note": (
            "Listener runs separately via `python -m app.ingest.run`."
            if configured else "Set AISSTREAM_KEY and LIVE_DATA_MODE=true to enable."
        ),
    }
