# Active Session — blueprinted.io
One entry only. On closeout: move this entry to the top of SESSIONS_ARCHIVE.md (above existing entries), replace with new entry.
Archive: SESSIONS_ARCHIVE.md (do not load unless explicitly asked).
Format and rules: docs/session_protocol.md

## Session — 2026-05-29 (estimate review UI — §11.5a)

### Decisions
- Per-chunk links in IngestionDetailPage (one button per triage_complete chunk) rather than a single "review all" entry point — keeps the operator oriented to which section they're reviewing.
- Merge flow uses checkbox-select + merged title input rather than drag-and-drop — consistent with SectionSelectionPage pattern and simpler to implement correctly.
- Polling in IngestionDetailPage extended to cover `extraction_queued` and `extracting` so the page stays live during the extraction phase.

### Done
- `src/pages/EstimateReviewPage.tsx`: inline title editing, type toggle, reject, merge, approve. Resolved estimates shown below at reduced opacity.
- `src/pages/IngestionDetailPage.tsx`: triage_complete action card with per-chunk links; polling updated for extraction statuses.
- `src/components/StatusBadge.tsx`: triage_complete, extraction_queued, extracting mapped to submitted (amber) style.
- `src/App.tsx`: route `ingestion/:id/chunks/:chunkId/estimates` wired.
- CI: clean pass (blueprinted-io/app).

### Next
Issue 4 is resolved. Remaining platform gaps: HTML ingestion worker tests (crawl_html, render_nav_pages) and embedding worker tests. Issue 5 (startup hook re-enqueue crash scenario) still open. Or continue app-side — candidate review page already exists; next natural app screen is ingestion list improvements or task list (§23.3).
