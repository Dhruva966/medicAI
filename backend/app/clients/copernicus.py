"""Sentinel-1 SAR overlay client.

Real Copernicus access requires OAuth2 + scene download + image processing.
For v1 we return a curated demo overlay derived from the vessel's last AIS gap.

NEEDS-SETUP-FOR-PRODUCTION:
  - Set COPERNICUS_CLIENT_ID + COPERNICUS_CLIENT_SECRET in backend/.env
  - Implement get_oauth_token() using the dataspace OAuth endpoint
  - Replace get_sar_overlay() with a real Sentinel-1 GRD search + render
"""

from datetime import timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.models import AISGap


def get_oauth_token() -> str:
    """TODO: exchange client_id/secret for an access token."""
    raise NotImplementedError("copernicus OAuth not wired up — see module docstring")


def get_sar_overlay(db: Session, imo: str) -> dict[str, Any]:
    """Return a curated SAR overlay for a vessel's most-recent dark period.

    Production path: query Sentinel-1 GRD for scenes intersecting the gap's
    bounding box ± 12h and render them as Web-Mercator tiles.
    """
    gap = (
        db.query(AISGap)
        .filter(AISGap.vessel_imo == imo)
        .order_by(AISGap.start_at.desc())
        .first()
    )

    if not gap:
        return {
            "image_url": None,
            "bbox": None,
            "acquired_at": None,
            "ais_position": None,
            "sar_position": None,
            "note": "no recent AIS gap for this vessel",
        }

    # Centerpoint between last/next known positions.
    cx = (gap.last_known_lon + gap.next_known_lon) / 2
    cy = (gap.last_known_lat + gap.next_known_lat) / 2

    # Demo SAR detection: vessel was somewhere along the path that AIS denied.
    # Bias the SAR position 60% toward next-known (i.e. closer to where it ended up).
    sar_lat = gap.last_known_lat + 0.6 * (gap.next_known_lat - gap.last_known_lat)
    sar_lon = gap.last_known_lon + 0.6 * (gap.next_known_lon - gap.last_known_lon)

    # Half-degree bbox around the centerpoint.
    return {
        "image_url": None,  # TODO: signed Sentinel-1 GRD tile URL
        "bbox": [cx - 0.5, cy - 0.5, cx + 0.5, cy + 0.5],
        "acquired_at": (gap.start_at + timedelta(hours=gap.duration_hours / 2)).isoformat(),
        "ais_position": [gap.last_known_lat, gap.last_known_lon],
        "sar_position": [sar_lat, sar_lon],
        "note": "Demo overlay. Production uses Sentinel-1 GRD via Copernicus Data Space.",
    }
