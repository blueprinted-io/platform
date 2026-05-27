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

## 5. Startup hook requires `ctx['redis']` — verify ARQ sets this

The startup hook uses `ctx.get('redis')` to re-enqueue `extraction_queued` chunks after
a crash. ARQ's `Worker` class sets `ctx['redis']` before calling `on_startup`, but this
has not been verified end-to-end in a running worker. If the key name differs, the
re-enqueue silently skips. Verify during the next end-to-end ingestion test.
