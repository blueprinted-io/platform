"""System settings service — DB-backed key/value config store (§10.4, §11.1).

LLM API keys are stored encrypted with Fernet symmetric encryption, keyed from
app_secret_key. Keys are never returned via GET — only written.
"""

import base64
import uuid

from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.settings import SystemSetting


def _make_fernet(app_secret_key: str) -> Fernet:
    # Derive a 32-byte key from the app secret; Fernet requires URL-safe base64.
    raw = app_secret_key.encode()[:32].ljust(32, b"\x00")
    return Fernet(base64.urlsafe_b64encode(raw))


def _encrypt(value: str, app_secret_key: str) -> str:
    return _make_fernet(app_secret_key).encrypt(value.encode()).decode()


def _decrypt(value: str, app_secret_key: str) -> str:
    return _make_fernet(app_secret_key).decrypt(value.encode()).decode()


async def get_setting(
    session: AsyncSession,
    key: str,
    default: str | None = None,
    app_secret_key: str = "",
) -> str | None:
    row = (
        await session.execute(select(SystemSetting).where(SystemSetting.key == key))
    ).scalar_one_or_none()
    if row is None or row.value is None:
        return default
    if row.encrypted and app_secret_key:
        return _decrypt(row.value, app_secret_key)
    return row.value


async def set_setting(
    session: AsyncSession,
    key: str,
    value: str | None,
    *,
    encrypted: bool = False,
    app_secret_key: str = "",
    updated_by_id: uuid.UUID | None = None,
) -> None:
    row = (
        await session.execute(select(SystemSetting).where(SystemSetting.key == key))
    ).scalar_one_or_none()

    stored_value = value
    if value is not None and encrypted and app_secret_key:
        stored_value = _encrypt(value, app_secret_key)

    if row is None:
        row = SystemSetting(
            key=key,
            value=stored_value,
            encrypted=encrypted,
            updated_by_id=updated_by_id,
        )
        session.add(row)
    else:
        if stored_value is not None:
            row.value = stored_value
            row.encrypted = encrypted
        row.updated_by_id = updated_by_id


class LLMSettings:
    """Resolved LLM configuration loaded from system_settings (per-job resolver)."""

    def __init__(
        self,
        triage_base_url: str,
        triage_model: str,
        triage_api_key: str,
        triage_timeout: int,
        extraction_base_url: str,
        extraction_model: str,
        extraction_api_key: str,
        extraction_timeout: int,
        embedding_base_url: str,
        embedding_model: str,
        embedding_api_key: str,
        embedding_timeout: int,
    ) -> None:
        self.triage_base_url = triage_base_url
        self.triage_model = triage_model
        self.triage_api_key = triage_api_key
        self.triage_timeout = triage_timeout
        self.extraction_base_url = extraction_base_url
        self.extraction_model = extraction_model
        self.extraction_api_key = extraction_api_key
        self.extraction_timeout = extraction_timeout
        self.embedding_base_url = embedding_base_url
        self.embedding_model = embedding_model
        self.embedding_api_key = embedding_api_key
        self.embedding_timeout = embedding_timeout


async def load_llm_settings(
    session: AsyncSession, app_secret_key: str, fallback_settings: object
) -> LLMSettings:
    """Load LLM config from system_settings, falling back to env Settings.

    The per-job resolver pattern: called at the start of each worker job so that
    LLM config changes take effect on the next job without a worker restart.
    """

    async def _get(key: str, fallback: str) -> str:
        result = await get_setting(session, key, default=fallback, app_secret_key=app_secret_key)
        return result or ""

    async def _get_int(key: str, fallback: int) -> int:
        val = await get_setting(session, key, default=str(fallback))
        try:
            return int(val or fallback)
        except ValueError:
            return fallback

    def _secret(attr: str) -> str:
        """Extract a SecretStr value from the fallback Settings object, or empty string."""
        secret = getattr(fallback_settings, attr, None)
        if secret is None:
            return ""
        get_val = getattr(secret, "get_secret_value", None)
        return get_val() if callable(get_val) else str(secret)

    fs = fallback_settings

    base_url = await _get("llm_base_url", getattr(fs, "llm_base_url", ""))
    model = await _get("llm_model", getattr(fs, "llm_model", ""))
    api_key = await _get("llm_api_key", _secret("llm_api_key"))

    triage_base_url = await _get("llm_triage_base_url", getattr(fs, "llm_triage_base_url", ""))
    triage_model = await _get("llm_triage_model", getattr(fs, "llm_triage_model", ""))
    triage_api_key = await _get("llm_triage_api_key", _secret("llm_triage_api_key"))
    triage_timeout = await _get_int(
        "llm_triage_timeout_seconds", getattr(fs, "llm_triage_timeout_seconds", 60)
    )

    extraction_base_url = await _get(
        "llm_extraction_base_url", getattr(fs, "llm_extraction_base_url", "")
    )
    extraction_model = await _get("llm_extraction_model", getattr(fs, "llm_extraction_model", ""))
    extraction_api_key = await _get("llm_extraction_api_key", _secret("llm_extraction_api_key"))
    extraction_timeout = await _get_int(
        "llm_extraction_timeout_seconds", getattr(fs, "llm_extraction_timeout_seconds", 120)
    )

    embedding_base_url = await _get(
        "llm_embedding_base_url", getattr(fs, "llm_embedding_base_url", "")
    )
    embedding_model = await _get(
        "llm_embedding_model",
        getattr(fs, "llm_embedding_model", "text-embedding-3-small"),
    )
    embedding_api_key = await _get("llm_embedding_api_key", _secret("llm_embedding_api_key"))
    embedding_timeout = await _get_int(
        "llm_embedding_timeout_seconds", getattr(fs, "llm_embedding_timeout_seconds", 30)
    )

    return LLMSettings(
        triage_base_url=triage_base_url or base_url,
        triage_model=triage_model or model,
        triage_api_key=triage_api_key or api_key,
        triage_timeout=triage_timeout,
        extraction_base_url=extraction_base_url or base_url,
        extraction_model=extraction_model or model,
        extraction_api_key=extraction_api_key or api_key,
        extraction_timeout=extraction_timeout,
        embedding_base_url=embedding_base_url,
        embedding_model=embedding_model,
        embedding_api_key=embedding_api_key,
        embedding_timeout=embedding_timeout,
    )
