# Active Session — blueprinted.io
One entry only. On closeout: move this entry to the top of SESSIONS_ARCHIVE.md (above existing entries), replace with new entry.
Archive: SESSIONS_ARCHIVE.md (do not load unless explicitly asked).
Format and rules: docs/session_protocol.md

## Session — 2026-05-18 (workflow/principle revise flow + dialog fix)

### Decisions
- Workflows and principles follow the same revise rules as tasks: any status, note required unless returned, returned records inherit the return note.
- Workflows and principles use UUID-based URLs (`/workflows/:id`, `/principles/:id`); after revise, navigate to `/{id}/edit` on the new draft.
- `WorkflowEditPage` and `PrincipleEditPage` created — previously only create pages existed for these types.
- Dialog CSS variables (`bg-popover`, `bg-muted`, `bg-transparent`) were not resolving to solid colours; replaced with concrete Tailwind values throughout.

### Done
- `ReviseRequest`, `WorkflowVersionSummary`, `PrincipleVersionSummary` schemas added.
- `list_workflows` and `list_principles` deduped to latest version per record_id.
- `GET /{record_id}/versions` endpoints added for both workflows and principles.
- `revise_workflow` and `revise_principle`: note enforcement, change_note propagation, 409 duplicate guard, post-commit id capture.
- `WorkflowDetailPage` and `PrincipleDetailPage`: version history strip, change_note callout, revise button + dialog, navigate to edit on success.
- `WorkflowEditPage` and `PrincipleEditPage` created; routes `workflows/:id/edit` and `principles/:id/edit` added in `App.tsx`.
- "Facts & Concepts" removed from sidebar nav; unused `BookOpen` import cleaned up.
- Dialog popup: `bg-popover` → `bg-white`, footer `bg-muted/50` → `bg-gray-50`, overlay `bg-black/10` → `bg-black/50`.
- Textarea: all CSS variable classes replaced with concrete values (`bg-white`, `border-gray-300`, `text-gray-900`).

### Next
Workflows and principles currently have no step/ref editing on the edit page — refs are managed on the detail page but there is no inline UI for adding/removing task refs or principle refs from `WorkflowEditPage`. That is the natural next gap to close.