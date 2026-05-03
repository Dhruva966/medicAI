"""Live AIS ingester — CLI entrypoint.

Usage:
    uv run python -m app.ingest.run
    uv run python -m app.ingest.run --bbox "23.0,48.0,30.5,57.0"
    uv run python -m app.ingest.run --tick-seconds 30 --duration-seconds 300

Behavior:
    - Connects to AISStream WebSocket (key from AISSTREAM_KEY)
    - Pumps PositionReport + ShipStaticData into rolling state
    - Every TICK_SECONDS, persists vessels and detects gaps/encounters
    - Re-scores any touched vessel so the API reflects live data
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import signal
import sys

from app.config import get_settings
from app.db import init_db
from app.ingest import aisstream_listener, event_extractor
from app.ingest.state import IngesterState

log = logging.getLogger("app.ingest")


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="ShadowFleet live AIS ingester")
    p.add_argument(
        "--bbox",
        help="min_lat,min_lon,max_lat,max_lon (overrides AIS_BBOX env)",
    )
    p.add_argument(
        "--tick-seconds",
        type=float,
        default=30.0,
        help="How often to run event extraction + persistence (default 30s)",
    )
    p.add_argument(
        "--duration-seconds",
        type=float,
        default=0.0,
        help="Auto-stop after this many seconds (0 = run until Ctrl+C)",
    )
    p.add_argument(
        "--log-level",
        default="INFO",
        help="DEBUG, INFO, WARNING, ERROR",
    )
    return p.parse_args()


async def _ticker(state: IngesterState, every_seconds: float, stop_event: asyncio.Event) -> None:
    while not stop_event.is_set():
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=every_seconds)
        except asyncio.TimeoutError:
            pass
        if stop_event.is_set():
            break
        try:
            counts = event_extractor.tick(state)
            stats = state.stats()
            log.info(
                "tick: vessels=%d (with_imo=%d) pos_msgs=%d static_msgs=%d "
                "this_cycle: persisted=%d gaps=%d encounters=%d",
                stats["vessels_total"],
                stats["vessels_with_imo"],
                stats["position_msgs"],
                stats["static_msgs"],
                counts["vessels_touched"],
                counts["gaps"],
                counts["encounters"],
            )
        except Exception:  # noqa: BLE001
            log.exception("tick failed — continuing")


async def _stopper_after(seconds: float, stop_event: asyncio.Event) -> None:
    if seconds <= 0:
        return
    await asyncio.sleep(seconds)
    log.info("duration reached — shutting down")
    stop_event.set()


async def _main_async(args: argparse.Namespace) -> int:
    settings = get_settings()

    if not settings.live_data_mode:
        log.error("LIVE_DATA_MODE=false — set it to true in backend/.env to ingest live AIS")
        return 2
    if not settings.aisstream_key:
        log.error("AISSTREAM_KEY is empty — register at https://aisstream.io and set it")
        return 2
    if args.bbox:
        # Override at runtime by mutating the Settings cache value.
        settings.ais_bbox = args.bbox
        if not settings.ais_bbox_tuple:
            log.error("--bbox is malformed: %r", args.bbox)
            return 2

    init_db()

    state = IngesterState()
    stop_event = asyncio.Event()

    def _handle_signal() -> None:
        log.info("signal received — shutting down")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig_name in ("SIGINT", "SIGTERM"):
        sig = getattr(signal, sig_name, None)
        if sig is None:
            continue
        try:
            loop.add_signal_handler(sig, _handle_signal)
        except NotImplementedError:
            # Windows doesn't support SIGTERM via add_signal_handler; SIGINT works.
            pass

    listener_task = asyncio.create_task(
        aisstream_listener.run(state, stop_event=stop_event), name="aisstream"
    )
    ticker_task = asyncio.create_task(
        _ticker(state, args.tick_seconds, stop_event), name="ticker"
    )
    stopper_task = asyncio.create_task(
        _stopper_after(args.duration_seconds, stop_event), name="stopper"
    )

    try:
        await stop_event.wait()
    finally:
        for t in (listener_task, ticker_task, stopper_task):
            t.cancel()
        # Run one final tick so any buffered state is persisted.
        try:
            event_extractor.tick(state)
        except Exception:  # noqa: BLE001
            log.exception("final tick failed")
        for t in (listener_task, ticker_task, stopper_task):
            try:
                await t
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass

    stats = state.stats()
    log.info(
        "shutdown summary: vessels=%d (with_imo=%d) position_msgs=%d static_msgs=%d events_persisted=%d",
        stats["vessels_total"],
        stats["vessels_with_imo"],
        stats["position_msgs"],
        stats["static_msgs"],
        stats["events_persisted"],
    )
    return 0


def main() -> int:
    args = _parse_args()
    logging.basicConfig(
        level=args.log_level.upper(),
        format="%(asctime)s %(levelname)-7s %(name)s :: %(message)s",
        datefmt="%H:%M:%S",
    )
    try:
        return asyncio.run(_main_async(args))
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())
