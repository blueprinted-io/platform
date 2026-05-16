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
        extra="ignore",  # .env also carries Docker Compose vars not in this model
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

    # -----------------------------------------------------------------------
    # LLM — shared convenience-mode settings (§11.1)
    # Per-pipeline settings below fall back to these when empty.
    # -----------------------------------------------------------------------
    llm_base_url: str = ""
    llm_model: str = ""
    llm_api_key: SecretStr = SecretStr("")

    # -----------------------------------------------------------------------
    # LLM — triage pipeline (§11.1)
    # -----------------------------------------------------------------------
    llm_triage_base_url: str = ""
    llm_triage_model: str = ""
    llm_triage_api_key: SecretStr = SecretStr("")
    llm_triage_timeout_seconds: int = 60

    # -----------------------------------------------------------------------
    # LLM — extraction pipeline (§11.1)
    # -----------------------------------------------------------------------
    llm_extraction_base_url: str = ""
    llm_extraction_model: str = ""
    llm_extraction_api_key: SecretStr = SecretStr("")
    llm_extraction_timeout_seconds: int = 120

    # -----------------------------------------------------------------------
    # Embedding (§12)
    # OpenAI-compatible endpoint. Leave base_url empty to disable embedding.
    # -----------------------------------------------------------------------
    llm_embedding_base_url: str = ""
    llm_embedding_model: str = "text-embedding-3-small"
    llm_embedding_api_key: SecretStr = SecretStr("")
    llm_embedding_timeout_seconds: int = 30

    def resolved_triage_base_url(self) -> str:
        return self.llm_triage_base_url or self.llm_base_url

    def resolved_triage_model(self) -> str:
        return self.llm_triage_model or self.llm_model

    def resolved_triage_api_key(self) -> str:
        return (
            self.llm_triage_api_key.get_secret_value()
            or self.llm_api_key.get_secret_value()
        )

    def resolved_extraction_base_url(self) -> str:
        return self.llm_extraction_base_url or self.llm_base_url

    def resolved_extraction_model(self) -> str:
        return self.llm_extraction_model or self.llm_model

    def resolved_extraction_api_key(self) -> str:
        return (
            self.llm_extraction_api_key.get_secret_value()
            or self.llm_api_key.get_secret_value()
        )


def get_settings() -> Settings:
    return Settings()
