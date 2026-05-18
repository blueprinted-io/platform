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

### Fields

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

### Output rules

1. Output valid JSON only. No preamble, no markdown, no code fences.
2. Every field must be present, even if null or empty string.
3. Do not invent content not present in the source.
4. Do not use em dashes in any field. Use commas, colons, or rewrite the
   sentence instead.
5. Use EXACTLY the field names defined above. Do not substitute synonyms:
   "summary" not "why" or "purpose"; "explanation" not "how" or "content"
   or "body"; "analogies" not "examples"; "title" not "name" or "concept".

### Known-Good Example

Input:
SECTION: Changed Block Tracking

SOURCE TEXT:
Veeam Agent for Microsoft Windows uses Changed Block Tracking (CBT) to identify
which data blocks have changed since the last backup job ran. Instead of reading
every block on the disk to detect changes, CBT records a digest of file system
metadata (for volume-level backups) or file modification timestamps (for
file-level backups). During an incremental backup job, only the blocks flagged
by CBT are read from the VSS snapshot and transferred to the repository, rather
than the full volume.

Two CBT mechanisms are available. The default mechanism reads the NTFS change
journal and file system metadata. The optional Veeam CBT Driver is a kernel
driver that provides more reliable tracking, particularly for machines running
large database workloads where the default mechanism may miss high-frequency
changes. The driver must be installed separately via the agent's Control Panel
and requires a reboot. It cannot be used on Windows Server 2012 R2 volumes
protected by BitLocker.

Output:
{
  "principles": [
    {
      "title": "Changed Block Tracking Reduces Incremental Backup Data Volume",
      "summary": "CBT identifies only modified disk blocks between backups, so incremental jobs transfer a fraction of the data a full backup would require.",
      "explanation": "## How CBT Works\n\nVeeam Agent uses **Changed Block Tracking (CBT)** to avoid reading entire volumes during incremental backup jobs. Rather than scanning every block for differences, CBT maintains a record of which blocks have changed since the last backup:\n\n- For **volume-level backups**: digests of NTFS file system metadata are compared.\n- For **file-level backups**: file modification timestamps are used.\n\nDuring an incremental job, Veeam creates a VSS snapshot of the volume and then reads only the blocks flagged by CBT, transferring them to the backup repository.\n\n## CBT Mechanism Options\n\nTwo mechanisms are available:\n\n| Mechanism | How it works | When to use |\n|---|---|---|\n| Default (NTFS change journal) | Reads the NTFS change journal and file system metadata | General workloads |\n| Veeam CBT Driver | Kernel driver for precise block-level tracking | Machines with large database workloads or high write rates |\n\nThe Veeam CBT Driver provides more reliable tracking where the default mechanism may miss high-frequency changes. It requires a separate installation via the agent Control Panel and a reboot. It cannot be used on Windows Server 2012 R2 volumes protected by BitLocker.",
      "analogies": null,
      "software_name": "Veeam Agent for Microsoft Windows",
      "software_version": null
    }
  ]
}

## User Message Template

SECTION: {section_title}

SOURCE TEXT:
{text}
