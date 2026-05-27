# Issues — Triage/Extraction Split Sprint

Issues noted during implementation. Address before the next sprint or as a dedicated session.

---

## 1. `approve` endpoint does not validate that merged estimates' survivors are still pending

When a merged estimate's `merged_into_id` target has also been rejected, the chunk
could be approved with zero valid estimates while still returning `extraction_queued > 0`
if a pending estimate exists that hasn't been flagged. More specifically: if an estimate
is marked `merged` pointing to a `rejected` survivor, approving the chunk will approve
zero estimates for that merge chain but the count returned is `pending` rows only.
This is correct but the UX may confuse operators — the surviving estimate of a merge
could be independently rejected afterward, leaving a dangling `merged` pointer.

**Suggested fix:** On approve, treat any `merged` estimate whose `merged_into_id` target
is `rejected` as if it were also rejected (no extraction). Or: prevent rejecting an
estimate that is the target of a merge (enforce via PATCH guard).

---

## 2. Extraction result takes only the first LLM item per estimate

`_extract_from_estimate` takes only `items[0]` from the extraction result. This means
if the LLM returns multiple tasks/principles for a single estimate, only the first is
persisted. This is intentional for the targeted-extraction model (one estimate = one
candidate), but if the LLM returns more, data is silently discarded.

**Suggested fix:** Log a warning when `len(items) > 1` so the discard is visible.

---

## 3. `extract_chunk` job does not hold a `processing`-equivalent status

When `extract_chunk` runs, the chunk stays in `extraction_queued`. If the worker
crashes mid-extraction, the startup hook re-enqueues the job, which will pick up
all approved estimates again — including ones that already produced candidates. This
creates duplicate candidates.

**Suggested fix:** Add a chunk status `extracting` set at the start of `extract_chunk`,
reset to `extraction_queued` by the startup hook on crash, and guard
`_extract_from_estimate` against re-running if a candidate already exists for that
estimate (check `ingestion_candidates.chunk_id + record_type` or add an
`estimate_id FK` to `ingestion_candidates`).

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
