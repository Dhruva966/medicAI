"""OFAC Specially Designated Nationals (SDN) list.

For v1 we ship a small curated fixture of vessel and entity names used in the
demo scenario. Replace `_BUNDLED_SDN` with a real download from the OFAC
public XML feed (https://www.treasury.gov/ofac/downloads/sdn.xml) once the
ingestion pipeline is wired up.
"""

from typing import Any

# Curated subset matching the demo seed. Real OFAC feed is much larger.
_BUNDLED_SDN: list[dict[str, Any]] = [
    {
        "kind": "vessel",
        "imo": "9322762",
        "name": "KRUSHEVA",
        "listing_ref": "OFAC SDN 2024-12-04 (Russian shadow fleet)",
    },
    {
        "kind": "vessel",
        "imo": "9417987",
        "name": "GLORIOUS DAWN",
        "listing_ref": "OFAC SDN 2025-01-10 (Iranian petroleum network)",
    },
    {
        "kind": "owner",
        "name": "Sovcomflot OJSC",
        "country": "Russia",
        "listing_ref": "OFAC SDN 2024-02-23",
    },
    {
        "kind": "owner",
        "name": "Hong Kong Pearl Maritime Ltd",
        "country": "Hong Kong",
        "listing_ref": "OFAC SDN 2024-12-04 (front company)",
    },
    {
        "kind": "owner",
        "name": "NIOC International Affairs",
        "country": "Iran",
        "listing_ref": "OFAC SDN 2018-11-05",
    },
]


def load_sdn_list() -> list[dict[str, Any]]:
    """Return the bundled SDN list. TODO: download + parse real XML feed."""
    return list(_BUNDLED_SDN)


def is_sanctioned_vessel(imo: str) -> bool:
    return any(e["kind"] == "vessel" and e["imo"] == imo for e in _BUNDLED_SDN)


def is_sanctioned_owner(name: str) -> bool:
    n = name.strip().lower()
    return any(e["kind"] == "owner" and e["name"].lower() == n for e in _BUNDLED_SDN)


def lookup_vessel(imo: str) -> dict[str, Any] | None:
    for e in _BUNDLED_SDN:
        if e["kind"] == "vessel" and e["imo"] == imo:
            return e
    return None


def lookup_owner(name: str) -> dict[str, Any] | None:
    n = name.strip().lower()
    for e in _BUNDLED_SDN:
        if e["kind"] == "owner" and e["name"].lower() == n:
            return e
    return None
