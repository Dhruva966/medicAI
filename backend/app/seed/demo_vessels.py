"""Seed the demo scenario `demo_shadow_001`.

Creates ~50 vessels (10 deliberately suspicious, 40 routine traffic) with
realistic owners, flag history, port calls, AIS gaps, encounters, and STS
transfers. The hero vessel `9876543` is the one the demo flow walks through.

Run with: `cd backend && uv run python -m app.seed.demo_vessels`
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from typing import Any

from app import db as _db
from app.models import (
    AISGap,
    Encounter,
    FlagHistory,
    Owner,
    PortCall,
    STSTransfer,
    Vessel,
)


# Reproducible randomness so the demo looks the same every time.
RNG = random.Random(42)
NOW = datetime(2026, 5, 1, tzinfo=timezone.utc).replace(tzinfo=None)


# ---------------------------------------------------------------------------
# Static fixture data
# ---------------------------------------------------------------------------

CLEAN_FLAGS = ["Liberia", "Marshall Islands", "Greece", "Singapore", "Norway", "United Kingdom", "Japan"]
CLEAN_TYPES = ["tanker", "bulker", "container", "general cargo", "lng tanker"]

CLEAN_OWNERS: list[dict[str, Any]] = [
    {"name": "Maersk Tankers A/S", "country": "Denmark"},
    {"name": "Frontline Plc", "country": "Cyprus"},
    {"name": "Teekay Corporation", "country": "Canada"},
    {"name": "K Line Pte Ltd", "country": "Singapore"},
    {"name": "Mitsui O.S.K. Lines", "country": "Japan"},
    {"name": "Stena Bulk", "country": "Sweden"},
    {"name": "Euronav NV", "country": "Belgium"},
    {"name": "Scorpio Tankers", "country": "Monaco"},
]

# Sketchy owners — sanctioned, shell, or chained to a sanctioned parent.
SKETCHY_OWNERS: list[dict[str, Any]] = [
    {
        "name": "Sovcomflot OJSC",
        "country": "Russia",
        "sanctioned": True,
        "sanctioned_at": datetime(2024, 2, 23),
        "shell_company": False,
    },
    {
        "name": "Hong Kong Pearl Maritime Ltd",
        "country": "Hong Kong",
        "sanctioned": True,
        "sanctioned_at": datetime(2024, 12, 4),
        "shell_company": True,
    },
    {
        "name": "Marshall Pacific Holdings Ltd",
        "country": "Marshall Islands",
        "sanctioned": False,
        "shell_company": True,
    },
    {
        "name": "NIOC International Affairs",
        "country": "Iran",
        "sanctioned": True,
        "sanctioned_at": datetime(2018, 11, 5),
        "shell_company": False,
    },
]

CLEAN_PORTS = [
    "Rotterdam", "Singapore", "Houston", "Long Beach", "Yokohama",
    "Shanghai", "Lagos", "Fujairah",
]
SKETCHY_PORTS = ["Novorossiysk", "Primorsk", "Ust-Luga", "Kozmino", "Sikka", "Vadinar"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ll_around(lat: float, lon: float, jitter: float = 2.0) -> tuple[float, float]:
    return (lat + RNG.uniform(-jitter, jitter), lon + RNG.uniform(-jitter, jitter))


# ---------------------------------------------------------------------------
# Seed
# ---------------------------------------------------------------------------

def seed() -> None:
    db = _db.SessionLocal()

    # Wipe — idempotent reseed.
    for tbl in (
        "evidence", "score_components", "risk_scores",
        "sts_transfers", "encounters", "ais_gaps", "port_calls",
        "flag_history", "vessels", "owners",
    ):
        db.execute(__import__("sqlalchemy").text(f"DELETE FROM {tbl}"))
    db.commit()

    # ---- Owners
    clean_owner_objs: list[Owner] = []
    for spec in CLEAN_OWNERS:
        o = Owner(name=spec["name"], country=spec["country"], shell_company=False, sanctioned=False)
        db.add(o)
        clean_owner_objs.append(o)
    db.flush()

    sketchy_owner_objs: list[Owner] = []
    for spec in SKETCHY_OWNERS:
        o = Owner(
            name=spec["name"],
            country=spec.get("country"),
            shell_company=spec.get("shell_company", False),
            sanctioned=spec.get("sanctioned", False),
            sanctioned_at=spec.get("sanctioned_at"),
        )
        db.add(o)
        sketchy_owner_objs.append(o)
    db.flush()

    # Build the hero ownership chain:
    #   Marshall Pacific Holdings (shell) -> Hong Kong Pearl (shell, sanctioned) -> Sovcomflot (sanctioned)
    marshall_pacific = next(o for o in sketchy_owner_objs if o.name == "Marshall Pacific Holdings Ltd")
    hk_pearl = next(o for o in sketchy_owner_objs if o.name == "Hong Kong Pearl Maritime Ltd")
    sovcomflot = next(o for o in sketchy_owner_objs if o.name == "Sovcomflot OJSC")
    marshall_pacific.parent_owner_id = hk_pearl.id
    hk_pearl.parent_owner_id = sovcomflot.id
    db.flush()

    # ---- Sister vessel (sanctioned by IMO) — appears in the ownership graph.
    sister = Vessel(
        imo="9322762",
        mmsi="273123450",
        name="KRUSHEVA",
        type="tanker",
        flag="Russia",
        gross_tonnage=62000,
        length_m=247.0,
        beam_m=42.0,
        year_built=2007,
        owner_id=sovcomflot.id,
        last_seen_lat=44.5,
        last_seen_lon=37.5,
        last_seen_at=NOW - timedelta(days=14),
    )
    db.add(sister)

    # ---- Hero vessel — the one the demo flow walks through.
    hero = Vessel(
        imo="9876543",
        mmsi="538008142",
        name="ATLANTIS PIONEER",
        type="tanker",
        flag="Cook Islands",
        gross_tonnage=55400,
        length_m=228.0,
        beam_m=32.2,
        year_built=2008,
        owner_id=marshall_pacific.id,
        last_seen_lat=12.4,
        last_seen_lon=68.9,
        last_seen_at=NOW - timedelta(hours=18),
    )
    db.add(hero)
    db.flush()

    # Flag history — five flags, four changes in the past 12 months.
    db.add_all([
        FlagHistory(
            vessel_imo=hero.imo, flag="Greece",
            start_date=NOW - timedelta(days=395), end_date=NOW - timedelta(days=260),
        ),
        FlagHistory(
            vessel_imo=hero.imo, flag="Marshall Islands",
            start_date=NOW - timedelta(days=260), end_date=NOW - timedelta(days=180),
        ),
        FlagHistory(
            vessel_imo=hero.imo, flag="Saint Kitts and Nevis",
            start_date=NOW - timedelta(days=180), end_date=NOW - timedelta(days=110),
        ),
        FlagHistory(
            vessel_imo=hero.imo, flag="Comoros",
            start_date=NOW - timedelta(days=110), end_date=NOW - timedelta(days=35),
        ),
        FlagHistory(
            vessel_imo=hero.imo, flag="Cook Islands",
            start_date=NOW - timedelta(days=35), end_date=None,
        ),
    ])

    # Port calls — recent calls are all in the Russian Black Sea / Arctic export range.
    db.add_all([
        PortCall(vessel_imo=hero.imo, port_name="Novorossiysk", port_country="Russia",
                 arrival_at=NOW - timedelta(days=120), departure_at=NOW - timedelta(days=117)),
        PortCall(vessel_imo=hero.imo, port_name="Primorsk", port_country="Russia",
                 arrival_at=NOW - timedelta(days=90),  departure_at=NOW - timedelta(days=88)),
        PortCall(vessel_imo=hero.imo, port_name="Ust-Luga", port_country="Russia",
                 arrival_at=NOW - timedelta(days=60),  departure_at=NOW - timedelta(days=58)),
        PortCall(vessel_imo=hero.imo, port_name="Sikka", port_country="India",
                 arrival_at=NOW - timedelta(days=22),  departure_at=NOW - timedelta(days=20)),
    ])

    # AIS gap — 16h dark window inside a known STS zone in the Arabian Sea.
    gap = AISGap(
        vessel_imo=hero.imo,
        start_at=NOW - timedelta(days=10, hours=4),
        end_at=NOW - timedelta(days=9, hours=12),
        duration_hours=16.0,
        last_known_lat=22.10, last_known_lon=68.50,
        next_known_lat=21.80, next_known_lon=66.20,
        in_known_sts_zone=True,
    )
    db.add(gap)

    # Second AIS gap — implies impossible speed: 1500 nm in 18h ≈ 83 kn.
    gap2 = AISGap(
        vessel_imo=hero.imo,
        start_at=NOW - timedelta(days=40),
        end_at=NOW - timedelta(days=39, hours=6),
        duration_hours=18.0,
        last_known_lat=43.90, last_known_lon=33.70,
        next_known_lat=29.20, next_known_lon=49.10,
        in_known_sts_zone=False,
    )
    db.add(gap2)

    # Suspicious encounter — 2.5h with sister vessel, far from port.
    enc = Encounter(
        vessel_a_imo=hero.imo,
        vessel_b_imo=sister.imo,
        start_at=NOW - timedelta(days=10, hours=1),
        end_at=NOW - timedelta(days=9, hours=22),
        duration_hours=3.0,
        lat=21.95, lon=67.40,
        in_port=False,
    )
    db.add(enc)
    db.flush()

    db.add(STSTransfer(
        encounter_id=enc.id,
        transfer_type="oil",
        estimated_volume=72000,
        in_known_zone=True,
    ))

    # ---- Boring background traffic — 48 routine vessels.
    used_imos: set[str] = {hero.imo, sister.imo}
    routine_vessels: list[Vessel] = []
    for i in range(48):
        imo = f"94{RNG.randint(10000, 99999)}"
        while imo in used_imos:
            imo = f"94{RNG.randint(10000, 99999)}"
        used_imos.add(imo)

        owner = RNG.choice(clean_owner_objs)
        flag = RNG.choice(CLEAN_FLAGS)
        vtype = RNG.choice(CLEAN_TYPES)
        v = Vessel(
            imo=imo,
            mmsi=str(RNG.randint(200000000, 700000000)),
            name=_routine_name(i),
            type=vtype,
            flag=flag,
            gross_tonnage=RNG.randint(20000, 120000),
            length_m=float(RNG.randint(180, 320)),
            beam_m=float(RNG.randint(28, 50)),
            year_built=RNG.randint(2005, 2022),
            owner_id=owner.id,
            last_seen_lat=RNG.uniform(-55, 60),
            last_seen_lon=RNG.uniform(-170, 170),
            last_seen_at=NOW - timedelta(hours=RNG.randint(1, 72)),
        )
        db.add(v)
        routine_vessels.append(v)
    db.flush()

    # Routine flag history (single flag) and recent port calls.
    for v in routine_vessels:
        db.add(FlagHistory(
            vessel_imo=v.imo, flag=v.flag,
            start_date=NOW - timedelta(days=RNG.randint(400, 1500)),
            end_date=None,
        ))
        for _ in range(RNG.randint(1, 3)):
            port = RNG.choice(CLEAN_PORTS)
            arr = NOW - timedelta(days=RNG.randint(5, 200))
            db.add(PortCall(
                vessel_imo=v.imo, port_name=port, port_country="—",
                arrival_at=arr, departure_at=arr + timedelta(days=RNG.randint(1, 4)),
            ))

    # ---- A handful of medium-risk vessels — partial signals only, so they sit
    # in the medium band rather than the critical one.
    for i in range(8):
        imo = f"95{RNG.randint(10000, 99999)}"
        while imo in used_imos:
            imo = f"95{RNG.randint(10000, 99999)}"
        used_imos.add(imo)

        owner = RNG.choice(clean_owner_objs)
        flag = RNG.choice(["Panama", "Liberia", "Comoros"])  # FOC bias
        v = Vessel(
            imo=imo,
            mmsi=str(RNG.randint(200000000, 700000000)),
            name=_sketchy_name(i),
            type="tanker",
            flag=flag,
            gross_tonnage=RNG.randint(40000, 150000),
            length_m=float(RNG.randint(220, 330)),
            beam_m=float(RNG.randint(32, 56)),
            year_built=RNG.randint(2002, 2014),
            owner_id=owner.id,
            last_seen_lat=RNG.uniform(0, 45),
            last_seen_lon=RNG.uniform(20, 110),
            last_seen_at=NOW - timedelta(hours=RNG.randint(1, 80)),
        )
        db.add(v)
        db.flush()

        # 1 medium AIS gap.
        last_lat, last_lon = _ll_around(v.last_seen_lat, v.last_seen_lon)
        next_lat, next_lon = _ll_around(v.last_seen_lat, v.last_seen_lon)
        db.add(AISGap(
            vessel_imo=v.imo,
            start_at=NOW - timedelta(days=RNG.randint(7, 25), hours=2),
            end_at=NOW - timedelta(days=RNG.randint(7, 25)),
            duration_hours=float(RNG.randint(5, 9)),
            last_known_lat=last_lat, last_known_lon=last_lon,
            next_known_lat=next_lat, next_known_lon=next_lon,
            in_known_sts_zone=False,
        ))
        # One older flag in the history.
        db.add_all([
            FlagHistory(vessel_imo=v.imo, flag="Marshall Islands",
                        start_date=NOW - timedelta(days=600), end_date=NOW - timedelta(days=200)),
            FlagHistory(vessel_imo=v.imo, flag=v.flag,
                        start_date=NOW - timedelta(days=200), end_date=None),
        ])
        for _ in range(RNG.randint(1, 2)):
            arr = NOW - timedelta(days=RNG.randint(20, 200))
            db.add(PortCall(
                vessel_imo=v.imo,
                port_name=RNG.choice(CLEAN_PORTS + SKETCHY_PORTS[:2]),
                port_country="—",
                arrival_at=arr, departure_at=arr + timedelta(days=RNG.randint(1, 3)),
            ))

    db.commit()

    # Pre-compute scores for every vessel so the map can color markers
    # immediately on first load.
    from app.models import Vessel as _V
    from app.services import scoring as _scoring
    for v in db.query(_V).all():
        try:
            _scoring.score_vessel(db, v.imo)
        except Exception:
            # Don't let one bad vessel block seeding the rest.
            db.rollback()

    db.close()


def _routine_name(i: int) -> str:
    prefixes = ["MAERSK", "STAR", "BLUE", "PACIFIC", "NORDIC", "CRYSTAL", "OCEANIC", "AURORA"]
    suffixes = ["VOYAGER", "TRADER", "MERCURY", "HORIZON", "SPIRIT", "PHOENIX", "VENTURE", "STAR"]
    return f"{prefixes[i % len(prefixes)]} {suffixes[(i * 3) % len(suffixes)]}"


def _sketchy_name(i: int) -> str:
    names = ["KOPER STAR", "NEW ASCENT", "SILVER BIRCH", "SHANTY MOON",
             "RED HORIZON", "GULF FLAME", "TIDE RUNNER", "BAY DRIFTER"]
    return names[i % len(names)]


def main() -> None:
    _db.init_db()
    seed()
    print("seeded ShadowFleet OS demo scenario (50 vessels, hero IMO 9876543)")


if __name__ == "__main__":
    main()
