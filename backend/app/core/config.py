from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "CampusShield"
    database_url: str = "sqlite:///./data/campusshield.db"
    jwt_secret: str = "dev-only-secret"
    service_api_key: str = "dev-only-service-key"
    authorized_subnets: str = "172.25.0.0/24"
    scanner_self_ip: str | None = None
    n8n_webhook_url: str | None = None
    n8n_webhook_secret: str | None = None

    @property
    def authorized_subnet_list(self) -> list[str]:
        return [s.strip() for s in self.authorized_subnets.split(",") if s.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
