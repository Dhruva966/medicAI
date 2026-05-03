"""External-data clients. Each module exposes a `status()` reporting live/mock state."""

from app.clients import aisstream, copernicus, equasis, gfw, ofac

__all__ = ["aisstream", "copernicus", "equasis", "gfw", "ofac"]
