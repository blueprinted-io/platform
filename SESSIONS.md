# Active Session — blueprinted.io
One entry only. On closeout: move this entry to the top of SESSIONS_ARCHIVE.md (above existing entries), replace with new entry.
Archive: SESSIONS_ARCHIVE.md (do not load unless explicitly asked).
Format and rules: docs/session_protocol.md

## Session — 2026-05-18 (LLM ingestion pipeline repair)

### Decisions
- `response_format: json_object` was causing the extraction LLM to invent its own field names (`name`/`purpose` instead of `title`/`outcome`, `why`/`how` instead of `summary`/`explanation`). Removed entirely; fence stripping + `json_repair` fallback used instead, matching the MVP approach.
- Prompt parser (`_parse_prompt_file`) only captures text between `## System Prompt` and the next `##` heading — `## Field definitions`, `## Output rules`, and `## Known-Good Example` were all silently discarded. Fixed by demoting those sections to `###` and moving Known-Good Example before `## User Message Template` in all three ingestion prompts.
- `json-repair==0.30.3` added to `pyproject.toml` as a production dependency; `uv.lock` updated.
- Triage/extraction human-gate split (spec v4.6 §11.5a) is a meaningful architectural decision from the MVP — cheap triage estimates candidates, human corrects before expensive extraction runs. Deferred to a dedicated sprint; not winging it.
- Spec bumped to v4.6 documenting the triage/extraction split design.

### Done
- `workers/main.py`: removed `response_format`, added fence stripping in `_call_llm`, added `_parse_llm_json` with `json_repair` fallback, replaced bare `json.loads` calls in triage and extraction paths.
- `prompts/ingestion/extract_task.md`: `## Field definitions`, `## Output rules`, `## Known-Good Example` demoted to `###`; Known-Good Example moved before User Message Template; field-name synonym rule added.
- `prompts/ingestion/extract_principle.md`: same structural fix; real worked example added (CBT driver content); field-name synonym rule added.
- `prompts/ingestion/triage.md`: Known-Good Example moved before User Message Template.
- `pyproject.toml` + `uv.lock`: `json-repair==0.30.3` added.
- `docs/requirements.md`: bumped to v4.6; §11.3 pipeline stages, §11.5 chunk status table, new §11.5a Triage Estimate Review, new §11.8a ingestion_triage_estimates table, §11.6 and §11.7 updated.
- PDF ingestion verified end-to-end: triage classifying correctly, extraction producing valid candidates with correct field names, candidates committed to DB.

### Next
Queue remaining 17 Veeam PDF chunks to confirm principle extraction also works correctly end-to-end (one principle-heavy section has been queued but not fully verified). Once confirmed, ingestion is stable and the sprint can move to the Task list screen (§23.3) in blueprinted-io/app.