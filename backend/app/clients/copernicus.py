"""Sentinel-1 SAR via Copernicus Data Space Ecosystem.

Docs: https://documentation.dataspace.copernicus.eu/APIs.html
"""

from typing import Any


def get_oauth_token() -> str:
    """Exchange client_id/client_secret for an access token."""
    raise NotImplementedError("copernicus.get_oauth_token not implemented yet")


def get_sar_overlay(imo: str) -> dict[str, Any]:
    """Find a Sentinel-1 SAR scene covering this vessel's last AIS gap.

    Returns a dict with image URL, bounding box, and acquisition time
    that the frontend SARViewer can overlay on the Leaflet map.
    """
    raise NotImplementedError("copernicus.get_sar_overlay not implemented yet")
