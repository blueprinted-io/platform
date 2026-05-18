# Active Session — blueprinted.io
One entry only. On closeout: move this entry to the top of SESSIONS_ARCHIVE.md (above existing entries), replace with new entry.
Archive: SESSIONS_ARCHIVE.md (do not load unless explicitly asked).
Format and rules: docs/session_protocol.md

## Session — 2026-05-18 (draft edit shortcut + small fixes)

### Decisions
- Draft records are mutable before submission; immutability only applies after submit. Detail pages now show "Edit" (direct link) for drafts and "Revise" (new version) for all other statuses.
- `buttonVariants` applied directly to `Link` elements rather than `asChild` — Base UI's `Button` primitive does not support the Radix `asChild` pattern.

### Done
- `TaskDetailPage`, `WorkflowDetailPage`, `PrincipleDetailPage`: draft records show "Edit [type]" link; Revise button hidden for drafts.

### Next
More small fixes to address — pick up with user at session start.