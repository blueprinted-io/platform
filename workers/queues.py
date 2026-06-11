"""Queue names shared between API enqueue sites and worker entrypoints (§14).

Kept import-light so api/ can import it without pulling worker-only
dependencies (PyMuPDF, Playwright).
"""

INGESTION_QUEUE = "ingestion"
