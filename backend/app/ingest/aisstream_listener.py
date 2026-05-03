"""AISStream.io WebSocket consumer.

Subscribes to PositionReport + ShipStaticData inside a bounding box and
updates the in-memory IngesterState. Auto-reconnects with exponential
backoff. Designed to run forever inside an asyncio task.

Message format reference: https://aisstream.io/documentation
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

import websockets

from app.clients.aisstream import WS_URL
from app.config import get_settings
from app.ingest.state import IngesterState, Position

log = logging.getLogger(__name__)

# AIS ship-type code → friendly label (subset; everything else is "other").
# Per ITU-R M.1371, codes 70-79 are cargo, 80-89 are tankers.
def _ship_type_label(code: int | None) -> str:
    if code is None:
        return "unknown"
    if 70 <= code <= 79:
        return "cargo"
    if 80 <= code <= 89:
        return "tanker"
    if code in (60, 61, 62, 63, 64, 65, 66, 67, 68, 69):
        return "passenger"
    if code == 30:
        return "fishing"
    if 31 <= code <= 32:
        return "tug"
    if 36 <= code <= 37:
        return "yacht"
    if 50 <= code <= 59:
        return "service"
    return "other"


def _build_subscription(api_key: str, bbox: tuple[float, float, float, float]) -> str:
    """AISStream subscription frame.

    bbox = (min_lat, min_lon, max_lat, max_lon)
    AISStream wants [[[lat1, lon1], [lat2, lon2]]] (NW + SE corners).
    """
    min_lat, min_lon, max_lat, max_lon = bbox
    return json.dumps({
        "APIKey": api_key,
        "BoundingBoxes": [[[min_lat, min_lon], [max_lat, max_lon]]],
        "FilterMessageTypes": ["PositionReport", "ShipStaticData"],
    })


def _handle_position(state: IngesterState, msg: dict[str, Any]) -> None:
    meta = msg.get("MetaData") or {}
    mmsi = meta.get("MMSI")
    if not mmsi:
        return

    pr = (msg.get("Message") or {}).get("PositionReport") or {}
    lat = pr.get("Latitude") or meta.get("latitude")
    lon = pr.get("Longitude") or meta.get("longitude")
    if lat is None or lon is None:
        return

    sog = pr.get("Sog")
    cog = pr.get("Cog")

    vessel = state.get_or_create(int(mmsi))
    vessel.add_position(Position(
        lat=float(lat),
        lon=float(lon),
        sog=float(sog) if sog is not None else None,
        cog=float(cog) if cog is not None else None,
        received_at=datetime.now(timezone.utc).replace(tzinfo=None),
    ))

    name = meta.get("ShipName")
    if name and not vessel.name:
        vessel.name = str(name).strip()

    state.bump("position_msgs")


def _handle_static(state: IngesterState, msg: dict[str, Any]) -> None:
    meta = msg.get("MetaData") or {}
    mmsi = meta.get("MMSI")
    if not mmsi:
        return

    sd = (msg.get("Message") or {}).get("ShipStaticData") or {}
    vessel = state.get_or_create(int(mmsi))

    imo = sd.get("ImoNumber")
    if imo and int(imo) > 0:
        vessel.imo = str(int(imo))

    name = sd.get("Name") or meta.get("ShipName")
    if name:
        vessel.name = str(name).strip()

    type_code = sd.get("Type")
    if type_code is not None:
        vessel.ship_type = _ship_type_label(int(type_code))

    call_sign = sd.get("CallSign")
    if call_sign:
        vessel.call_sign = str(call_sign).strip()

    dim = sd.get("Dimension") or {}
    a = dim.get("A") or 0
    b = dim.get("B") or 0
    c = dim.get("C") or 0
    d = dim.get("D") or 0
    if a or b:
        vessel.length_m = float(a + b)
    if c or d:
        vessel.beam_m = float(c + d)

    dest = sd.get("Destination")
    if dest:
        vessel.destination = str(dest).strip()

    state.bump("static_msgs")
    state.refresh_imo_count()


async def run(state: IngesterState, *, stop_event: asyncio.Event | None = None) -> None:
    """Connect to AISStream and pump messages into state. Reconnects on drop."""
    settings = get_settings()
    if not settings.aisstream_key:
        raise RuntimeError("AISSTREAM_KEY is empty — set it in backend/.env")

    bbox = settings.ais_bbox_tuple
    if not bbox:
        raise RuntimeError(f"AIS_BBOX is malformed: {settings.ais_bbox!r}")

    sub_frame = _build_subscription(settings.aisstream_key, bbox)
    backoff = 1.0

    log.info(
        "aisstream: connecting to %s, bbox=(%.2f,%.2f → %.2f,%.2f)",
        WS_URL, *bbox,
    )

    while not (stop_event and stop_event.is_set()):
        try:
            async with websockets.connect(WS_URL, ping_interval=20, ping_timeout=20) as ws:
                await ws.send(sub_frame)
                log.info("aisstream: subscribed")
                backoff = 1.0
                async for raw in ws:
                    if stop_event and stop_event.is_set():
                        break
                    try:
                        msg = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    msg_type = msg.get("MessageType")
                    if msg_type == "PositionReport":
                        _handle_position(state, msg)
                    elif msg_type == "ShipStaticData":
                        _handle_static(state, msg)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 — listener is long-lived; never die
            log.warning("aisstream: connection lost (%s) — reconnecting in %.1fs", exc, backoff)
            try:
                await asyncio.sleep(backoff)
            except asyncio.CancelledError:
                raise
            backoff = min(backoff * 2, 60.0)
