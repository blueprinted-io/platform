# Active Session — blueprinted.io
One entry only. On closeout: move this entry to the top of SESSIONS_ARCHIVE.md (above existing entries), replace with new entry.
Archive: SESSIONS_ARCHIVE.md (do not load unless explicitly asked).
Format and rules: docs/session_protocol.md

## Session — 2026-06-11 (Sprint 12: pagination + worker split)

### Decisions
- List endpoints return a Page envelope {items, total, limit, offset} (limit default 20, max 100) — total is required for UI page controls. In-place /api/v1 shape change accepted as a pre-GA exception to the breaking-changes rule; spec bumped v4.10 → v4.11 (§6).
- Worker split is two processes: default worker (embeddings + review-claim-expiry cron) and ingestion worker on a dedicated `ingestion` queue (chunk_pdf, process_chunks, extract_chunk, crawl_html, render_nav_pages). The load-bearing startup recovery hook runs on the ingestion worker only.
- Queue routing is part of the job contract — ARQ workers fail unregistered jobs, so every ingestion enqueue passes _queue_name; enforced by a static call-site scan test.

### Done
- Pagination on GET /tasks, /workflows, /principles: generic Page[T] schema, latest-version-only totals, id-desc ordering tiebreaker for stable pages.
- workers/main.py (1330-line god worker) split into embeddings, maintenance, ingestion_pdf, ingestion_html, extraction, llm, common, queues modules; new workers/ingestion.py entrypoint; worker-ingestion service added to docker-compose.
- Five ingestion enqueue sites route to the ingestion queue via INGESTION_QUEUE constant (import-light workers/queues.py).
- Fixed latent bug: admin health endpoint missing rollback after ProgrammingError left the transaction aborted (masked in CI by pre-run migrations).
- 23 new tests (pagination behaviour + worker queue routing); conftest gains TEST_DATABASE_URL/_SYNC overrides for local runs against the port-5433 test container. 345 passing, ruff/mypy clean.
- Spec v4.11: §6 pagination convention, §14 two-worker contract.

### Broken / Incomplete
- App frontend still expects bare arrays from the three list endpoints — Sprint 8 screens must adopt the Page envelope.
- Production deploy needs the new worker-ingestion container started — the old single worker no longer runs ingestion jobs.
- (carried) Auth failure rate limiting not implemented; Authentik theme logos broken — cosmetic.

### Next
Update the app repo (Sprint 8 read screens) to consume the Page envelope from /tasks, /workflows, /principles. Prerequisite: restart the deploy stack so the worker-ingestion service is running.
