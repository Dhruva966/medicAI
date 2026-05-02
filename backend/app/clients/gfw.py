"""Global Fishing Watch — AIS positions, vessel identity, encounters.

NEEDS-SETUP-FOR-PRODUCTION:
  - Get a token at https://globalfishingwatch.org/our-apis/
  - Set GFW_TOKEN in backend/.env
  - Implement search_vessel/get_track/get_encounters against the v3 API

For v1 the seed scenario is our AIS source of truth — these methods return
empty results unless GFW_TOKEN is configured.
"""

from typing import Any

import httpx

from app.config import get_settings

BASE_URL = "https://gateway.api.globalfishingwatch.org/v3"


def _client() -> httpx.Client | None:
    token = get_settings().gfw_token
    if not token:
        return None
    return httpx.Client(
        base_url=BASE_URL,
        headers={"Authorization": f"Bearer {token}"},
        timeout=30.0,
    )


def search_vessel(query: str) -> list[dict[str, Any]]:
    c = _client()
    if not c:
        return []
    raise NotImplementedError("gfw.search_vessel — token detected but call not wired")


def get_track(vessel_id: str, start: str, end: str) -> list[dict[str, Any]]:
    c = _client()
    if not c:
        return []
    raise NotImplementedError("gfw.get_track — token detected but call not wired")


def get_encounters(vessel_id: str, start: str, end: str) -> list[dict[str, Any]]:
    c = _client()
    if not c:
        return []
    raise NotImplementedError("gfw.get_encounters — token detected but call not wired")
