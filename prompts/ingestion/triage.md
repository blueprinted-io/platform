# Triage

**Purpose:** Classify a single chunk of technical documentation into one of four
categories so that downstream pipeline stages know how to process it. Runs once
per chunk after section selection (SS11.3 stage 3).

**Input contract:** The calling code provides:
- `section_title` — the chunk's section heading from PDF outline or HTML h-tags
- `text` — the chunk body, truncated to 6000 characters

**Output schema:**
```json
{
  "category": "task_candidate | principle_candidate | reference_material | skip",
  "confidence": 0.0,
  "reason": "one sentence",
  "estimates": [
    {"title": "estimated candidate title", "type": "task | principle"}
  ]
}
```

All fields are required. `confidence` is 0.0–1.0. `estimates` lists one entry per expected
extractable candidate in this chunk — the LLM's best guess at how many records the chunk
contains and what they are called. For `reference_material` and `skip`, `estimates` must
be an empty array. For `task_candidate` and `principle_candidate`, at least one estimate
is required. `type` must match the category (`task_candidate` → `task`, `principle_candidate`
→ `principle`), except where the chunk clearly contains both types.

## System Prompt

Classify this section of technical documentation as exactly one of:

- "task_candidate": describes one or more concrete procedures an operator
  would perform. Includes sections that describe multiple related procedures,
  which will be extracted as separate tasks downstream.
- "principle_candidate": conceptual or explanatory material covering how
  something works, why it behaves that way, trade-off analysis, or guidance
  on when to choose one approach over another. No imperative steps;
  declarative, not instructional.
- "reference_material": API references, glossaries, command tables, code
  snippets, configuration file examples, or other lookup-style content that
  is useful to retain as reference but is not extractable as task or
  principle records.
- "skip": administrative, introductory, legal, appendix, index, marketing,
  or no actionable content.

Do not use em dashes in any output. Use commas, colons, or rewrite instead.

Return JSON only, no markdown, no commentary.

### Known-Good Example

Input:
SECTION: 3.2 Configuring the iSCSI Initiator on Ubuntu

TEXT:
This section describes how to install and configure the open-iscsi
package on Ubuntu 22.04. First, update the package index using apt.
Then install open-iscsi. After installation, enable the iscsid
service to start automatically on boot, then start it. Verify the
service is running with systemctl status iscsid.

Output:
{"category": "task_candidate", "confidence": 0.95, "reason": "Section describes a concrete installation procedure with imperative steps and observable completion checks.", "estimates": [{"title": "Configure iSCSI Initiator on Ubuntu", "type": "task"}]}

## User Message Template

SECTION: {section_title}

TEXT:
{text}
