# Issues — Triage/Extraction Split Sprint

---

## 1. ~~`approve` endpoint does not validate that merged estimates' survivors are still pending~~ — RESOLVED

Analysis confirmed the original `pending` filter already handles this correctly: if a
merge survivor is subsequently rejected, it leaves `pending` and `approved_count` is
naturally 0. The approve handler now loads all estimates for the chunk and includes an
explanatory comment documenting the invariant.

---

## 2. ~~Extraction result takes only the first LLM item per estimate~~ — RESOLVED

`_extract_from_estimate` now logs a `extract_items_discarded` warning when the LLM
returns more than one item, making the discard visible in logs.

---

## 3. ~~`extract_chunk` job does not hold a `processing`-equivalent status~~ — RESOLVED

`extract_chunk` now sets chunk status to `extracting` before any LLM calls. The startup
hook resets `extracting` → `extraction_queued` on worker restart. `_extract_from_estimate`
guards against re-running if a candidate already exists for that chunk+type combination.

---

## 4. Frontend estimate review UI not yet built

The estimate review workflow (list estimates → reject/merge/type-correct → approve) has
no frontend implementation. The API is complete. Implement in the next app-side sprint.

---

## 6. ~~`str(exc)` returns empty string for some httpx exceptions~~ — RESOLVED

Some httpx exceptions (e.g. transient `RemoteProtocolError`) have an empty `str()`.
`error_detail` was stored as `""` and log fields were blank, making failures
invisible in logs. Fixed by adding `_exc_str(exc)` helper (`str(exc) or repr(exc)`)
used at all error-capture sites in `workers/main.py`.

---

## 5. ~~Startup hook requires `ctx['redis']` — verify ARQ sets this~~ — RESOLVED

`tests/test_startup_hook.py` verifies both paths: with `ctx['redis']` set (mock ARQ pool),
`enqueue_job("extract_chunk", ...)` is called for every `extraction_queued` chunk; without
`ctx['redis']`, the re-enqueue block is skipped cleanly. The `processing → queued` and
`extracting → extraction_queued` SQL resets are also covered.
