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
    copernicus_client_id: str = ""
    copernicus_client_secret: str = ""
    equasis_session: str = ""
    ofac_sdn_url: str = "https://www.treasury.gov/ofac/downloads/sdn.xml"

    # App
    database_url: str = "sqlite:///./shadowfleet.db"
    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
