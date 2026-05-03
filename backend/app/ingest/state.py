"""In-memory rolling state for the live ingester.

We don't persist every AIS position — that's too much write traffic. Instead
we keep a per-vessel ring buffer of the last N positions in memory, plus
identity (IMO / name / type / flag) once it arrives via ShipStaticData.

The event extractor reads this state on a tick and emits AISGap / Encounter
rows when patterns are detected.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from threading import RLock
from typing import Iterable

POSITION_BUFFER_SIZE = 200


@dataclass
class Position:
    lat: float
    lon: float
    sog: float | None     # speed over ground (knots)
    cog: float | None     # course over ground (degrees)
    received_at: datetime


@dataclass
class VesselState:
    mmsi: int
    imo: str | None = None
    name: str | None = None
    ship_type: str | None = None
    flag: str | None = None
    call_sign: str | None = None
    length_m: float | None = None
    beam_m: float | None = None
    destination: str | None = None
    positions: deque[Position] = field(default_factory=lambda: deque(maxlen=POSITION_BUFFER_SIZE))
    last_persisted_imo: str | None = None
    last_gap_emitted_at: datetime | None = None

    @property
    def latest(self) -> Position | None:
        return self.positions[-1] if self.positions else None

    def add_position(self, p: Position) -> None:
        self.positions.append(p)


class IngesterState:
    """Thread-safe registry of all vessels seen on the stream."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._by_mmsi: dict[int, VesselState] = {}
        self._stats: dict[str, int] = {
            "position_msgs": 0,
            "static_msgs": 0,
            "vessels_with_imo": 0,
            "vessels_total": 0,
            "events_persisted": 0,
        }

    def get_or_create(self, mmsi: int) -> VesselState:
        with self._lock:
            v = self._by_mmsi.get(mmsi)
            if v is None:
                v = VesselState(mmsi=mmsi)
                self._by_mmsi[mmsi] = v
                self._stats["vessels_total"] = len(self._by_mmsi)
            return v

    def all_vessels(self) -> list[VesselState]:
        with self._lock:
            return list(self._by_mmsi.values())

    def vessels_with_imo(self) -> list[VesselState]:
        with self._lock:
            return [v for v in self._by_mmsi.values() if v.imo]

    def bump(self, key: str, by: int = 1) -> None:
        with self._lock:
            self._stats[key] = self._stats.get(key, 0) + by

    def refresh_imo_count(self) -> None:
        with self._lock:
            self._stats["vessels_with_imo"] = sum(1 for v in self._by_mmsi.values() if v.imo)

    def stats(self) -> dict[str, int]:
        with self._lock:
            return dict(self._stats)
