"""Environment-driven configuration."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from .env / environment."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Anthropic
    anthropic_api_key: str = ""
    llm_model: str = "claude-sonnet-4-5"

    # External data
    gfw_token: str = ""
    aisstream_key: str = ""
    copernicus_client_id: str = ""
    copernicus_client_secret: str = ""
    equasis_session: str = ""
    ofac_sdn_url: str = "https://www.treasury.gov/ofac/downloads/sdn.xml"

    # Master switch — when False, all external clients use bundled fixtures
    # so tests and the curated demo stay deterministic and offline.
    live_data_mode: bool = False

    # AIS ingester scope (live mode only). Bbox = [min_lat, min_lon, max_lat, max_lon].
    # Default: Persian Gulf — a documented gray-zone hotspot with reasonable AIS density.
    ais_bbox: str = "23.0,48.0,30.5,57.0"
    ais_min_position_msgs: int = 3   # require N positions before persisting a vessel

    # App
    database_url: str = "sqlite:///./shadowfleet.db"
    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def ais_bbox_tuple(self) -> tuple[float, float, float, float] | None:
        try:
            parts = [float(p.strip()) for p in self.ais_bbox.split(",")]
            if len(parts) != 4:
                return None
            return (parts[0], parts[1], parts[2], parts[3])
        except (ValueError, AttributeError):
            return None


@lru_cache
def get_settings() -> Settings:
    return Settings()
