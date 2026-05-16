# JSON Import Schema Specification

**Status:** Stable, v1
**Governs:** `POST /api/v1/ingestions/json` request body
**Source of truth for:** the importable JSON payload format

This document defines the structure of JSON payloads accepted by the JSON
ingestion endpoint. It is the single authoritative reference for this format.

See also: `prompts/external/manual_json_authoring.md` — the operator-facing
authoring guide for producing conformant JSON manually or via LLM assistance.

Note: the candidate JSON written to `ingestion_candidates` by the LLM
extraction pipeline (§11.4) is a different artifact. That schema describes
pipeline-internal representations; this document describes the user-importable
payload format.

---

## Envelope

```json
{
  "schema_version": "1.0",
  "items": [ ]
}
```

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `schema_version` | string | Yes | Must be `"1.0"` for v1 payloads |
| `items` | array | Yes | One or more task or principle objects (see below) |

---

## Task Object

```json
{
  "type": "task",
  "id": "T001",
  "title": "string",
  "outcome": "string",
  "software_name": "string | null",
  "software_version": "string | null",
  "domain": "string",
  "facts": ["string"],
  "concepts": ["string"],
  "dependencies": ["string"],
  "irreversible": false,
  "task_order": ["T001", "T002"],
  "steps": [
    {
      "id": "S001",
      "text": "string",
      "completion": "string",
      "actions": ["string"],
      "notes": "string | null"
    }
  ]
}
```

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `type` | string | Yes | Must be `"task"` |
| `id` | string | No | Import-time label for this task (e.g. `"T001"`). Used as the target of `task_order` references within the same payload. Not persisted — the committed Task record receives its own UUID. Must be unique within the payload if present. |
| `title` | string | Yes | Concise noun phrase, 5-10 words, operator perspective |
| `outcome` | string | Yes | One sentence, passive voice, observable end state |
| `software_name` | string or null | Yes | Product name as it appears in the source; null if unknown |
| `software_version` | string or null | Yes | Version string from the source; null if not stated |
| `domain` | string | Yes | Domain name this task belongs to |
| `facts` | string array | Yes | Background knowledge items; empty array if none |
| `concepts` | string array | Yes | Task-specific reasons this task must be performed; empty array if none |
| `dependencies` | string array | Yes | Preconditions as full sentences; empty array if none |
| `irreversible` | boolean | Yes | true only if the task cannot be undone without significant effort |
| `task_order` | string array | Yes | Import IDs of tasks this task depends on (e.g. `["T001"]`); empty array if none. Each entry must match an `id` present on another task in the same payload. Forward references are allowed. Not persisted. |
| `steps` | array | Yes | Ordered step objects; must not be empty |

### Step Object

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `id` | string | Yes | Sequential import ID, e.g. `"S001"` — not persisted, used for ordering within the import |
| `text` | string | Yes | The instruction itself. Start with a concrete verb. |
| `completion` | string | Yes | Observable confirmation the step is done. Specific, not "Done." |
| `actions` | string array | Yes | Concrete substeps: CLI commands, menu paths, keyboard shortcuts. Empty array if step text is self-explanatory. |
| `notes` | string or null | Yes | Alternatives, caveats, and tool-choice guidance that contextualise the actions without being actions themselves (e.g. "vim or any other editor may be substituted"). null if none. |

---

## Principle Object

```json
{
  "type": "principle",
  "title": "string",
  "summary": "string",
  "explanation": "string",
  "analogies": "string | null",
  "software_name": "string | null",
  "software_version": "string | null",
  "domain": "string"
}
```

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `type` | string | Yes | Must be `"principle"` |
| `title` | string | Yes | Concise noun phrase, 5-12 words |
| `summary` | string | Yes | One sentence, active voice: what this explains and why it matters |
| `explanation` | string | Yes | Full conceptual content; markdown supported, rendered as HTML |
| `analogies` | string or null | Yes | Analogies or comparisons from the source; null if none |
| `software_name` | string or null | Yes | Product or technology name from the source; null if not determinable |
| `software_version` | string or null | Yes | Version string from the source; null if not stated |
| `domain` | string | Yes | Domain name this principle belongs to |

---

## Validation rules

- `schema_version` must be `"1.0"`. Unknown versions are rejected with HTTP 422.
- `items` must contain at least one object.
- Every required field must be present. Missing fields are rejected with a
  field-level error identifying the offending item and field.
- `task_order` references must resolve within the same payload. Each entry must
  match the `id` field of another task item in the same payload. Forward
  references are allowed (an item may reference an `id` that appears later in
  `items`). Dangling references (IDs not present in the payload) are rejected.
  Task items without an `id` field cannot be referenced in `task_order` and
  must have an empty `task_order` array.
- Task `id` values must be unique within the payload. Duplicate IDs are rejected.
- Ingestion creates records in `draft` status. No `confirmed` records can be
  created via import.
