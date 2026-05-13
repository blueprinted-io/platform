"""Bootstrap configuration loaded from environment variables.

Runtime configuration lives in system_settings (database-backed).
Only values required before the database is available belong here.
"""

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # -----------------------------------------------------------------------
    # Application
    # -----------------------------------------------------------------------
    app_env: str = "development"
    app_secret_key: SecretStr = SecretStr("change-me-in-production")
    log_level: str = "INFO"

    # -----------------------------------------------------------------------
    # Database
    # -----------------------------------------------------------------------
    database_url: str = "postgresql+asyncpg://blueprinted:blueprinted@localhost:5432/blueprinted"
    # Synchronous URL used only by Alembic CLI (migrations run outside the async loop)
    database_url_sync: str = "postgresql+psycopg2://blueprinted:blueprinted@localhost:5432/blueprinted"

    # -----------------------------------------------------------------------
    # Redis (ARQ broker + rate limit backend)
    # -----------------------------------------------------------------------
    redis_url: str = "redis://localhost:6379/0"

    # -----------------------------------------------------------------------
    # Authentik OIDC
    # -----------------------------------------------------------------------
    oidc_issuer: str = ""
    oidc_client_id: str = ""
    oidc_client_secret: SecretStr = SecretStr("")
    # JWKS URI for RS256 token verification.
    # Find this in Authentik: Applications → Providers → your provider → "JWKS URL".
    oidc_jwks_uri: str = ""
    # Audience claim expected in tokens ("aud"). Set to the Authentik application client ID.
    oidc_audience: str = ""
    # JWT claim that carries the user's roles list. Configure in Authentik property mappings.
    oidc_roles_claim: str = "roles"

    # -----------------------------------------------------------------------
    # Storage
    # -----------------------------------------------------------------------
    storage_backend: str = "local"  # "local" | "s3"
    storage_local_root: str = "uploads"


def get_settings() -> Settings:
    return Settings()
