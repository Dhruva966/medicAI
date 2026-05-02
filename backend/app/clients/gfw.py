"""Global Fishing Watch — AIS positions, vessel identity, encounters.

Docs: https://globalfishingwatch.org/our-apis/
"""

from typing import Any

import httpx

from app.config import get_settings


BASE_URL = "https://gateway.api.globalfishingwatch.org/v3"


def _client() -> httpx.Client:
    token = get_settings().gfw_token
    return httpx.Client(
        base_url=BASE_URL,
        headers={"Authorization": f"Bearer {token}"} if token else {},
        timeout=30.0,
    )


def search_vessel(query: str) -> list[dict[str, Any]]:
    """Search GFW for vessels by name / IMO / MMSI."""
    raise NotImplementedError("gfw.search_vessel not implemented yet")


def get_track(vessel_id: str, start: str, end: str) -> list[dict[str, Any]]:
    """Return AIS positions for `vessel_id` between two ISO timestamps."""
    raise NotImplementedError("gfw.get_track not implemented yet")


def get_encounters(vessel_id: str, start: str, end: str) -> list[dict[str, Any]]:
    """Return encounter events involving `vessel_id`."""
    raise NotImplementedError("gfw.get_encounters not implemented yet")
