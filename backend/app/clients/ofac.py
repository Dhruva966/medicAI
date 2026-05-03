"""OFAC Specially Designated Nationals (SDN) list — live feed with on-disk cache.

Source: https://www.treasury.gov/ofac/downloads/sdn.xml (public, no auth).

Behavior:
  - In live mode (settings.live_data_mode=True): cache (24h) -> live fetch -> fixture
  - In demo mode (default): bundled fixture only — keeps tests deterministic
  - Live entries are merged with the bundled fixture; bundled IMOs/names that are
    not in the live feed remain (so the curated demo scenario keeps working).

Public API (unchanged from previous version):
    load_sdn_list() -> list[dict]
    is_sanctioned_vessel(imo) -> bool
    is_sanctioned_owner(name) -> bool
    lookup_vessel(imo) -> dict | None
    lookup_owner(name) -> dict | None
    status() -> dict   # for /health
"""

from __future__ import annotations

import json
import logging
import re
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from threading import Lock
from typing import Any

import httpx

from app.config import get_settings

log = logging.getLogger(__name__)

# Bundled fallback — mirrors the curated demo seed so the hero scenario keeps
# working even when offline.
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

CACHE_TTL_SECONDS = 24 * 60 * 60
CACHE_PATH = Path(__file__).resolve().parents[2] / ".cache" / "ofac_sdn.json"

# OFAC sdn.xml ships with a namespace that's changed over time
# (legacy tempuri.org → modern sanctionslistservice.ofac.treas.gov).
# The parser strips the namespace and matches by local name, so we don't care.
_IMO_RE = re.compile(r"\b(\d{7})\b")

_lock = Lock()
_state: dict[str, Any] = {
    "loaded": False,
    "source": "fixture",        # "fixture" | "live" | "cache"
    "fetched_at": None,
    "entries": list(_BUNDLED_SDN),
    "vessel_by_imo": {},
    "owner_by_name": {},
}


def _build_indexes(entries: list[dict[str, Any]]) -> tuple[dict, dict]:
    by_imo: dict[str, dict] = {}
    by_name: dict[str, dict] = {}
    for e in entries:
        if e.get("kind") == "vessel" and e.get("imo"):
            by_imo[str(e["imo"])] = e
        elif e.get("kind") == "owner" and e.get("name"):
            by_name[e["name"].strip().lower()] = e
    return by_imo, by_name


def _local(tag: str) -> str:
    """Return the local element name, stripping any XML namespace prefix."""
    return tag.rsplit("}", 1)[-1]


def _find_local(parent: ET.Element, name: str) -> ET.Element | None:
    for c in parent:
        if _local(c.tag) == name:
            return c
    return None


def _findall_local(parent: ET.Element, name: str) -> list[ET.Element]:
    return [c for c in parent if _local(c.tag) == name]


def _text_local(parent: ET.Element, name: str) -> str:
    el = _find_local(parent, name)
    return (el.text or "").strip() if el is not None and el.text else ""


def _extract_imo(id_list_el: ET.Element | None) -> str:
    """OFAC stores IMOs as `idType=Vessel Registration Identification, idNumber='IMO 1234567'`.

    Older feeds used `idType=IMO Number, idNumber='1234567'`. We accept both.
    """
    if id_list_el is None:
        return ""
    for id_node in _findall_local(id_list_el, "id"):
        id_type = _text_local(id_node, "idType")
        id_num = _text_local(id_node, "idNumber")
        if not id_num:
            continue
        if id_type == "IMO Number" and id_num.isdigit() and len(id_num) == 7:
            return id_num
        if id_type in ("Vessel Registration Identification", "Vessel Identification"):
            m = _IMO_RE.search(id_num)
            if m:
                return m.group(1)
    return ""


def _parse_sdn_xml(xml_bytes: bytes) -> list[dict[str, Any]]:
    """Parse OFAC sdn.xml. Returns vessel + entity records (skips individuals/aircraft).

    Namespace-agnostic — handles both the legacy tempuri.org schema and the
    modern sanctionslistservice.ofac.treas.gov schema.
    """
    out: list[dict[str, Any]] = []
    root = ET.fromstring(xml_bytes)

    for entry in root:
        if _local(entry.tag) != "sdnEntry":
            continue

        sdn_type = _text_local(entry, "sdnType")
        if sdn_type not in ("Vessel", "Entity"):
            continue

        last = _text_local(entry, "lastName")
        first = _text_local(entry, "firstName")
        full_name = " ".join(p for p in (first, last) if p) or last
        if not full_name:
            continue

        plist = _find_local(entry, "programList")
        programs: list[str] = []
        if plist is not None:
            programs = [
                (p.text or "").strip()
                for p in _findall_local(plist, "program")
                if (p.text or "").strip()
            ]
        listing_ref = "OFAC SDN" + (f" ({', '.join(programs)})" if programs else "")

        if sdn_type == "Vessel":
            imo = _extract_imo(_find_local(entry, "idList"))
            if not imo:
                continue
            # Vessel flag is sometimes present in vesselInfo
            flag = ""
            vinfo = _find_local(entry, "vesselInfo")
            if vinfo is not None:
                flag = _text_local(vinfo, "vesselFlag")
            out.append({
                "kind": "vessel",
                "imo": imo,
                "name": full_name,
                "flag": flag,
                "listing_ref": listing_ref,
            })
        else:  # Entity
            country = ""
            addrs = _find_local(entry, "addressList")
            if addrs is not None:
                a = _find_local(addrs, "address")
                if a is not None:
                    country = _text_local(a, "country")
            out.append({
                "kind": "owner",
                "name": full_name,
                "country": country,
                "listing_ref": listing_ref,
            })

    return out


def _read_cache() -> list[dict[str, Any]] | None:
    if not CACHE_PATH.exists():
        return None
    try:
        data = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    fetched = data.get("fetched_at", 0)
    if time.time() - fetched > CACHE_TTL_SECONDS:
        return None
    entries = data.get("entries")
    return entries if isinstance(entries, list) else None


def _write_cache(entries: list[dict[str, Any]]) -> None:
    try:
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        CACHE_PATH.write_text(
            json.dumps({"fetched_at": time.time(), "entries": entries}),
            encoding="utf-8",
        )
    except OSError as exc:
        log.warning("ofac: cache write failed: %s", exc)


def _fetch_live(url: str) -> list[dict[str, Any]] | None:
    try:
        with httpx.Client(timeout=30.0) as c:
            r = c.get(url, follow_redirects=True)
            r.raise_for_status()
            entries = _parse_sdn_xml(r.content)
        if not entries:
            log.warning("ofac: live feed returned 0 parsable entries")
            return None
        return entries
    except (httpx.HTTPError, ET.ParseError) as exc:
        log.warning("ofac: live fetch failed (%s)", exc)
        return None


def _merge(live: list[dict[str, Any]], fixture: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Live takes precedence; fixture entries fill in IMOs/names not in live."""
    live_imos = {str(e["imo"]) for e in live if e.get("kind") == "vessel" and e.get("imo")}
    live_names = {e["name"].strip().lower() for e in live if e.get("kind") == "owner" and e.get("name")}
    out = list(live)
    for e in fixture:
        if e.get("kind") == "vessel" and str(e.get("imo", "")) not in live_imos:
            out.append(e)
        elif e.get("kind") == "owner" and e.get("name", "").strip().lower() not in live_names:
            out.append(e)
    return out


def ensure_loaded() -> None:
    """Idempotent loader. First call resolves source per LIVE_DATA_MODE."""
    if _state["loaded"]:
        return
    with _lock:
        if _state["loaded"]:
            return

        settings = get_settings()
        if not settings.live_data_mode:
            entries = list(_BUNDLED_SDN)
            source = "fixture"
        else:
            cached = _read_cache()
            if cached:
                entries = _merge(cached, _BUNDLED_SDN)
                source = "cache"
            else:
                live = _fetch_live(settings.ofac_sdn_url)
                if live is not None:
                    _write_cache(live)
                    entries = _merge(live, _BUNDLED_SDN)
                    source = "live"
                else:
                    entries = list(_BUNDLED_SDN)
                    source = "fixture"

        by_imo, by_name = _build_indexes(entries)
        _state["entries"] = entries
        _state["vessel_by_imo"] = by_imo
        _state["owner_by_name"] = by_name
        _state["source"] = source
        _state["fetched_at"] = time.time()
        _state["loaded"] = True
        log.info(
            "ofac: loaded %d entries (%d vessels, %d owners) from %s",
            len(entries), len(by_imo), len(by_name), source,
        )


def status() -> dict[str, Any]:
    ensure_loaded()
    source = _state["source"]
    return {
        "configured": True,
        "mode": "live" if source in ("live", "cache") else "mock",
        "source": source,
        "entry_count": len(_state["entries"]),
        "vessel_count": len(_state["vessel_by_imo"]),
        "owner_count": len(_state["owner_by_name"]),
        "fetched_at": _state["fetched_at"],
    }


def reset() -> None:
    """Clear cached state — used in tests to force a re-load."""
    with _lock:
        _state["loaded"] = False
        _state["source"] = "fixture"
        _state["fetched_at"] = None
        _state["entries"] = list(_BUNDLED_SDN)
        _state["vessel_by_imo"] = {}
        _state["owner_by_name"] = {}


# ── Public API (signatures unchanged) ─────────────────────────────────────

def load_sdn_list() -> list[dict[str, Any]]:
    ensure_loaded()
    return list(_state["entries"])


def is_sanctioned_vessel(imo: str) -> bool:
    ensure_loaded()
    return str(imo) in _state["vessel_by_imo"]


def is_sanctioned_owner(name: str) -> bool:
    ensure_loaded()
    return name.strip().lower() in _state["owner_by_name"]


def lookup_vessel(imo: str) -> dict[str, Any] | None:
    ensure_loaded()
    return _state["vessel_by_imo"].get(str(imo))


def lookup_owner(name: str) -> dict[str, Any] | None:
    ensure_loaded()
    return _state["owner_by_name"].get(name.strip().lower())
