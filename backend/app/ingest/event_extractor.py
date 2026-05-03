"""Event extractor — turns rolling AIS state into persisted DB rows.

Runs on a fixed tick. For each tick:
  1. Persist new vessels once we have IMO + enough position samples.
  2. Update last_seen_* on persisted vessels.
  3. Detect AIS gaps (no position for >GAP_THRESHOLD_HOURS).
  4. Detect close encounters (two persisted vessels <PROXIMITY_NM for >MIN_DURATION).
  5. Re-score affected vessels.

This is intentionally heuristic. STS classification + port-call detection
are stubbed out: STS needs known-zone polygons; ports need a UN/LOCODE
geo-fence dataset. Both are documented follow-ups in the README.
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timedelta, timezone
from typing import Iterable

from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import SessionLocal
from app.ingest.state import IngesterState, VesselState
from app.models import AISGap, Encounter, Vessel
from app.services import scoring

log = logging.getLogger(__name__)

# Detection thresholds — keep aligned with detector logic in app/detectors/.
GAP_THRESHOLD_HOURS = 4.0
ENCOUNTER_PROXIMITY_NM = 2.0
ENCOUNTER_MIN_DURATION_MINUTES = 30.0


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _haversine_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in nautical miles."""
    r_nm = 3440.065  # Earth radius
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r_nm * math.asin(math.sqrt(a))


def _persist_vessels(db: Session, state: IngesterState, min_positions: int) -> list[str]:
    """Insert/update Vessel rows for any tracked vessels with IMO + enough samples.
    Returns list of IMOs that were newly persisted or had position updates."""
    touched: list[str] = []
    for v in state.vessels_with_imo():
        if not v.positions or len(v.positions) < min_positions:
            continue
        latest = v.latest
        if latest is None:
            continue

        existing = db.query(Vessel).filter(Vessel.imo == v.imo).first()
        if not existing:
            db.add(Vessel(
                imo=v.imo,
                mmsi=str(v.mmsi),
                name=v.name or f"MMSI-{v.mmsi}",
                type=v.ship_type or "unknown",
                flag=v.flag or "unknown",
                length_m=v.length_m,
                beam_m=v.beam_m,
                last_seen_lat=latest.lat,
                last_seen_lon=latest.lon,
                last_seen_at=latest.received_at,
            ))
            v.last_persisted_imo = v.imo
            touched.append(v.imo)
        else:
            existing.last_seen_lat = latest.lat
            existing.last_seen_lon = latest.lon
            existing.last_seen_at = latest.received_at
            if not existing.mmsi and v.mmsi:
                existing.mmsi = str(v.mmsi)
            if v.name and existing.name.startswith("MMSI-"):
                existing.name = v.name
            if v.ship_type and existing.type == "unknown":
                existing.type = v.ship_type
            if v.length_m and not existing.length_m:
                existing.length_m = v.length_m
            if v.beam_m and not existing.beam_m:
                existing.beam_m = v.beam_m
            touched.append(v.imo)
    db.commit()
    return touched


def _detect_gaps(db: Session, state: IngesterState) -> int:
    """Emit an AISGap row when a known vessel goes dark for > threshold."""
    now = _now()
    n = 0
    for v in state.vessels_with_imo():
        if not v.imo or len(v.positions) < 2 or not v.last_persisted_imo:
            continue
        latest = v.latest
        prev = v.positions[-2]
        if latest is None:
            continue
        gap_h = (latest.received_at - prev.received_at).total_seconds() / 3600.0
        if gap_h < GAP_THRESHOLD_HOURS:
            continue
        # Don't emit twice for the same gap.
        if v.last_gap_emitted_at and v.last_gap_emitted_at >= prev.received_at:
            continue
        db.add(AISGap(
            vessel_imo=v.imo,
            start_at=prev.received_at,
            end_at=latest.received_at,
            duration_hours=gap_h,
            last_known_lat=prev.lat,
            last_known_lon=prev.lon,
            next_known_lat=latest.lat,
            next_known_lon=latest.lon,
            in_known_sts_zone=False,
        ))
        v.last_gap_emitted_at = prev.received_at
        n += 1
    if n:
        db.commit()
    return n


def _detect_encounters(db: Session, state: IngesterState) -> int:
    """Pairwise proximity check among persisted vessels with current positions.

    Hackathon-grade: O(n^2) brute force inside the bbox. With ~hundreds of
    vessels this is fine. Production would use a spatial index.
    """
    persisted = [v for v in state.vessels_with_imo() if v.last_persisted_imo and v.latest]
    n = 0
    now = _now()
    cutoff = now - timedelta(minutes=ENCOUNTER_MIN_DURATION_MINUTES)

    for i in range(len(persisted)):
        a = persisted[i]
        a_pos = a.latest
        if a_pos is None or a_pos.received_at < cutoff:
            continue
        for j in range(i + 1, len(persisted)):
            b = persisted[j]
            b_pos = b.latest
            if b_pos is None or b_pos.received_at < cutoff:
                continue
            d = _haversine_nm(a_pos.lat, a_pos.lon, b_pos.lat, b_pos.lon)
            if d > ENCOUNTER_PROXIMITY_NM:
                continue
            # Dedup: only insert if we don't already have an open encounter
            # with the same pair in the last hour.
            recent = (
                db.query(Encounter)
                .filter(Encounter.vessel_a_imo.in_([a.imo, b.imo]))
                .filter(Encounter.vessel_b_imo.in_([a.imo, b.imo]))
                .filter(Encounter.end_at >= now - timedelta(hours=1))
                .first()
            )
            if recent:
                continue
            mid_lat = (a_pos.lat + b_pos.lat) / 2
            mid_lon = (a_pos.lon + b_pos.lon) / 2
            duration_h = ENCOUNTER_MIN_DURATION_MINUTES / 60.0
            db.add(Encounter(
                vessel_a_imo=a.imo,
                vessel_b_imo=b.imo,
                start_at=now - timedelta(minutes=ENCOUNTER_MIN_DURATION_MINUTES),
                end_at=now,
                duration_hours=duration_h,
                lat=mid_lat,
                lon=mid_lon,
                in_port=False,
            ))
            n += 1
    if n:
        db.commit()
    return n


def _rescore(db: Session, imos: Iterable[str]) -> None:
    for imo in set(imos):
        try:
            scoring.score_vessel(db, imo)
        except Exception as exc:  # noqa: BLE001 — never let one bad vessel kill the loop
            log.warning("rescore failed for %s: %s", imo, exc)


def tick(state: IngesterState) -> dict[str, int]:
    """Run one extraction cycle. Returns counts for telemetry."""
    settings = get_settings()
    db = SessionLocal()
    try:
        touched = _persist_vessels(db, state, settings.ais_min_position_msgs)
        gaps = _detect_gaps(db, state)
        encs = _detect_encounters(db, state)
        if touched:
            _rescore(db, touched)
        state.bump("events_persisted", gaps + encs)
        return {"vessels_touched": len(touched), "gaps": gaps, "encounters": encs}
    finally:
        db.close()
