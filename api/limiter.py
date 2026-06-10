"""Rate limiter singleton (§5.4).

Instantiated once and imported by main.py (for exception handler) and
individual route modules (for @limiter.limit() decorators).

Storage backend uses the same Redis instance as ARQ so no extra infra is needed.
The storage_uri falls back to in-memory when LIMITER_STORAGE_URI is absent — safe
for tests but in-memory limits are not shared across workers in production.
"""

import os

from slowapi import Limiter
from slowapi.util import get_remote_address

_storage_uri = os.environ.get("LIMITER_STORAGE_URI", "memory://")

# Disable rate limiting when no real backend is configured (tests, local dev).
# Production must set LIMITER_STORAGE_URI=redis://... to activate limits.
_enabled = not _storage_uri.startswith("memory://")

limiter = Limiter(key_func=get_remote_address, storage_uri=_storage_uri, enabled=_enabled)
