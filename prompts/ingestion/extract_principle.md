# Extract Principle

**Purpose:** Extract structured principle candidates from a chunk previously
classified as `principle_candidate` by the triage stage. Principles are
conceptual records, not procedural ones (SS11.3 stage 4).

**Input contract:** The calling code provides:
- `section_title` — the chunk's section heading
- `text` — the full chunk body

**Output schema:**
```json
{
  "principles": [
    {
      "title": "string",
      "summary": "string",
      "explanation": "string",
      "analogies": "string | null",
      "software_name": "string | null",
      "software_version": "string | null"
    }
  ]
}
```

## System Prompt

You are extracting structured principle records from conceptual technical
documentation.

A principle is a standalone conceptual record that explains *why* and
*how* — not *what to do*.

## Fields

**title**: Concise noun phrase naming the concept. 5-12 words.

**summary**: One sentence in active voice: what this principle explains and
why it matters.

**explanation**: The full conceptual content. Include: what the thing is,
how it works, trade-offs between alternatives, conditions under which you'd
choose each option. Preserve the source structure. Use rich markdown
throughout: ## headings for major sections, ### for sub-sections, **bold**
for key terms on first use, bullet and numbered lists, and code blocks for
syntax or command examples. Do not include step-by-step procedures. This
field will be rendered as HTML so markdown formatting is important.

**analogies**: Optional. If the source contains analogies or comparisons
that aid understanding, extract them here. null if none.

**software_name**: The product or technology this principle is about, as
named in the source. null if not determinable.

**software_version**: Version string if stated in the source. null if not
determinable.

## Output rules

1. Output valid JSON only. No preamble, no markdown, no code fences.
2. Every field must be present, even if null or empty string.
3. Do not invent content not present in the source.
4. Do not use em dashes in any field. Use commas, colons, or rewrite the
   sentence instead.

## User Message Template

SECTION: {section_title}

SOURCE TEXT:
{text}

## Known-Good Example

<!-- TODO: Draft a known-good example from a real conceptual passage before
the first production ingestion run. The MVP's extract_primer prompt shipped
without an embedded example — this is a gap the rebuild explicitly fixes.
A Veeam concept passage (e.g. VSS quiescing behaviour, or the difference
between application-aware and crash-consistent backups) would be appropriate.
See §11.16 for the requirement: every prompt must contain at least one
fully-worked known-good example in the prompt body. -->

Input:
[PLACEHOLDER — to be drafted before first production ingestion run]

Output:
[PLACEHOLDER — to be drafted before first production ingestion run]
