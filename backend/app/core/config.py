from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "CampusShield"
    database_url: str = "sqlite:///./data/campusshield.db"

    # auth
    jwt_secret: str = "dev-only-secret"
    jwt_expire_minutes: int = 8 * 60  # one working day
    session_cookie: str = "cs_session"
    cookie_secure: bool = False  # True once served over HTTPS
    login_max_failures: int = 5
    login_lockout_minutes: int = 15
    service_api_key: str = "dev-only-service-key"

    # accounts created on first start
    admin_email: str = "admin@campusshield.local"
    admin_password: str = "Admin@123"
    admin_name: str = "Campus IT Admin"
    auditor_email: str = "auditor@campusshield.local"
    auditor_password: str = "Auditor@123"
    auditor_name: str = "Security Auditor"

    # scanning
    authorized_subnets: str = "172.25.0.0/24"
    scanner_self_ip: str | None = None

    # automation
    n8n_webhook_url: str | None = None
    n8n_webhook_secret: str | None = None

    @property
    def authorized_subnet_list(self) -> list[str]:
        return [s.strip() for s in self.authorized_subnets.split(",") if s.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
