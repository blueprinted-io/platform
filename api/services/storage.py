"""File storage abstraction (§4.4).

v1 implements local-disk storage only. The interface is kept minimal so an
S3-compatible backend can be wired in without changing call sites.
"""

import hashlib
import uuid
from pathlib import Path

from api.config import Settings


def _ingestion_dir(settings: Settings, ingestion_id: uuid.UUID) -> Path:
    return Path(settings.storage_local_root) / "ingestions" / str(ingestion_id)


def save_ingestion_file(
    settings: Settings, ingestion_id: uuid.UUID, filename: str, data: bytes
) -> tuple[str, str]:
    """Write uploaded file to local storage. Returns (storage_path, sha256_hex)."""
    dest_dir = _ingestion_dir(settings, ingestion_id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / filename
    dest.write_bytes(data)
    sha256 = hashlib.sha256(data).hexdigest()
    return str(dest), sha256


def read_ingestion_file(settings: Settings, storage_path: str) -> bytes:
    """Read a previously stored ingestion file."""
    return Path(storage_path).read_bytes()


def delete_ingestion_dir(settings: Settings, ingestion_id: uuid.UUID) -> None:
    """Remove the storage directory for an ingestion (no-op if absent)."""
    import shutil
    dest_dir = _ingestion_dir(settings, ingestion_id)
    if dest_dir.exists():
        shutil.rmtree(dest_dir)
