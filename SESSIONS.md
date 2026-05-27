# Active Session — blueprinted.io
One entry only. On closeout: move this entry to the top of SESSIONS_ARCHIVE.md (above existing entries), replace with new entry.
Archive: SESSIONS_ARCHIVE.md (do not load unless explicitly asked).
Format and rules: docs/session_protocol.md

## Session — 2026-05-27 (Triage/extraction split — §11.5a)

### Decisions
- `_parse_llm_json`: replaced `# type: ignore` with `cast(dict[str, Any], ...)` on `json.loads` return; `repair_json` return no longer needs suppression (json_repair now ships stubs).
- `_triage_chunk` replaces `_process_single_chunk` — triage now stops at `triage_complete` and writes estimates; extraction is a separate `extract_chunk` ARQ job triggered by `POST .../estimates/approve`.
- `reference_material` / `skip` chunks that produce empty estimates skip directly to `done` (no approval step needed).
- Startup hook re-enqueues `extraction_queued` chunks via `ctx['redis']` in case the ARQ job was lost between approve and pickup.
- Issues doc created at `docs/issues.md` with 5 items to address in a follow-up session.

### Done
- `workers/main.py`: CI fix (cast instead of type-ignore); triage/extraction split.
- `prompts/ingestion/triage.md`: output schema extended with `estimates` array.
- `migrations/versions/20260527_a1b2c3d4e5f6_triage_estimates.py`: new `ingestion_triage_estimates` table.
- `api/models/ingestion.py`: `IngestionTriageEstimate` ORM model; relationships wired.
- `api/models/__init__.py`: ingestion models registered.
- `api/schemas/triage_estimate.py`: response/request schemas.
- `api/routes/triage_estimates.py`: GET/PATCH/merge/approve endpoints.
- `api/routes/v1.py`: triage_estimates router wired.
- `tests/test_triage_estimates.py`: 18 tests covering all new endpoints.
- `docs/issues.md`: sprint issues log created.

### Next
Apply migration to dev DB (`alembic upgrade head` inside the API container, or manual SQL via docker exec).
Run the end-to-end ingestion flow: submit a PDF, select sections, watch triage_complete status, review estimates in the API, approve, confirm extraction runs.
Then: build the frontend estimate review UI (app-side sprint).
