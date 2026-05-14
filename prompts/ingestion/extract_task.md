# Extract Task

**Purpose:** Extract structured task candidates from a chunk previously
classified as `task_candidate` by the triage stage. May produce zero, one, or
many task candidates per chunk depending on chunk content (SS11.3 stage 4).

**Input contract:** The calling code provides:
- `section_title` — the chunk's section heading
- `text` — the full chunk body (no truncation)

**Output schema:**
```json
{
  "tasks": [
    {
      "id": "T001",
      "title": "string",
      "outcome": "string",
      "software_name": "string | null",
      "software_version": "string | null",
      "procedure_name": "string",
      "facts": ["string"],
      "concepts": ["string"],
      "dependencies": ["string"],
      "irreversible": true,
      "steps": [
        {
          "text": "string",
          "completion": "string",
          "actions": ["string"],
          "notes": "string | null"
        }
      ]
    }
  ]
}
```

Every field on every object must be present, including `null` and `[]` values.

## System Prompt

You are extracting structured task records from a section of technical
documentation.

## Field definitions

**title**: A concise noun phrase (5-10 words) naming the task from the
operator's perspective. Must be unique within the document. Do not start with
a verb. Do not repeat the software name unless necessary for clarity.

Good: "Initial Backup Job Configuration" / "Agent Installation on Windows
Server"
Bad: "Configure a backup job" (verb start) / "Veeam Backup Configuration"
(too generic)

**outcome**: A single sentence in passive voice describing the observable end
state after all steps are complete. Specific to this procedure.

**facts**: Background knowledge the learner needs about the subject matter
before they can make sense of this task. The "what" — what are the components
involved, what do they do, what are they for. This is not technical reference
data (commands and port numbers belong in steps); it is the definitional
understanding a learner needs so they are not confused about what they are
working with. Can be short for simple tasks, long for complex ones. Write each
as a complete sentence.

Good: "Veeam Agent for Microsoft Windows is a backup agent installed locally
on each Windows machine that Veeam will protect." / "iscsid is the iSCSI
daemon that manages active iSCSI sessions on the local machine."
Bad: "The default iSCSI port is 3260." (technical trivia, not definitional
knowledge) / "Run sudo apt install open-iscsi." (belongs in steps)

**concepts**: The specific reason THIS task must be performed, not a general
description of the technology. Every task in a product has a different
concept; if the concept you write could apply equally to a different task in
the same product, it is too generic and must be rewritten. Ask: what
specifically breaks, fails, or cannot happen if this particular task is
skipped? Write in plain English. A substantive explanation of one or two
paragraphs is expected; do not summarise to a single line. Implementation
details and "by the way" information belong in step notes, not here.

Good (for "Install Veeam Agent"): a paragraph explaining that Veeam uses an
agent-based architecture: the Veeam server cannot back up a Windows machine
unless an agent is running locally on it, because the agent is the only
component that can interface with that machine's VSS and OS-level APIs.
Without this installation step, no backup jobs targeting this machine can
run.
Bad: any sentence that describes what the product does in general ("Veeam
Agent provides backup and recovery capabilities..."). This would be true
regardless of which task is being performed and tells the learner nothing
about why this specific task is necessary.

**dependencies**: Specific preconditions that must be true before the
operator can start. Full sentences.

Good: "Ubuntu machine is accessible with sudo privileges." / "No backup jobs
are currently running."

**software_name**: The name of the software product this content relates to,
as it appears in the source document (e.g. "Veeam Agent for Microsoft
Windows", "Ubuntu", "PostgreSQL"). null if not determinable.

**software_version**: The version of that software this content was written
for, exactly as it appears in the source document, in headers, titles,
footers, or version declarations (e.g. "6.1", "22.04 LTS", "v3.2.1"). null
if the document does not state a version.

**procedure_name**: A short imperative phrase naming the method used,
distinct from the task title.

Example: title "Upgrade Veeam Agent for Microsoft Windows" → procedure_name
"Interactive upgrade via Control Panel"

**irreversible**: true only if completing this task produces changes that
are difficult or impossible to undo without significant additional work or
data loss risk. Formatting a disk: true. Installing or upgrading software:
false.

**steps**: Each step is a single physical or digital action.

- Start with a concrete verb: open, close, press, click, run, record,
  insert, remove, verify, enter, select.
- Do NOT start with abstract verbs: configure, manage, set up, ensure,
  handle, prepare, edit.
- One action only. If the step contains "and", "then", or "also", split it
  into two consecutive steps.
- text: the instruction itself.
- completion: observable confirmation the step is done. Specific, not "Step
  is complete." or "Done."
    Good: "Terminal shows 'OK'." / "Wizard advances to the License
    Agreement screen."
    Bad: "Software is installed." / "Step is complete."
- actions: array of substeps giving the concrete method: menu navigation
  paths, exact CLI commands, keyboard shortcuts. Empty array [] if the step
  text is self-explanatory.
- notes: "oh by the way" information from the source: edge cases, uncommon
  configurations, or conditional caveats that don't always apply. Extract
  from callouts, notes, or asides in the source text. null if none.

## Output rules

1. Output valid JSON only. No preamble, no explanation, no markdown code
   fences.
2. Assign each task a sequential ID starting at T001 (T001, T002, T003...).
   Never skip or reuse IDs.
3. Every field must be present in every object, even if null, false, or [].
   Never omit a field.
4. Do not invent content. Extract only what is present in the source text.
   If facts, concepts, or dependencies are not present in the source, use [].
5. Do not use em dashes in any field. Use commas, colons, or rewrite the
   sentence instead.

## User Message Template

SECTION: {section_title}

SOURCE TEXT:
{text}

## Known-Good Example

Input:
SECTION: 3.2 Configuring the iSCSI Initiator on Ubuntu

SOURCE TEXT:
This section describes how to install and configure the open-iscsi package on
Ubuntu 22.04. First, update the package index using apt: run
`sudo apt update`. Then install open-iscsi: run `sudo apt install open-iscsi`.
After installation, enable the iscsid service to start automatically on boot:
run `sudo systemctl enable iscsid`. Then start it: run
`sudo systemctl start iscsid`. Verify the service is running with
`systemctl status iscsid` — the output should show "active (running)".

Output:
{
  "tasks": [
    {
      "id": "T001",
      "title": "iSCSI Initiator Installation on Ubuntu",
      "outcome": "The open-iscsi package is installed, the iscsid service is enabled and running, and the host is ready to establish iSCSI connections.",
      "software_name": "open-iscsi",
      "software_version": "22.04",
      "procedure_name": "Package installation via apt",
      "facts": [
        "open-iscsi is the iSCSI initiator software for Linux, providing the userspace tools and daemon needed to connect to iSCSI targets.",
        "iscsid is the iSCSI daemon that manages active iSCSI sessions on the local machine."
      ],
      "concepts": [
        "iSCSI (Internet Small Computer Systems Interface) is a protocol that allows SCSI commands to be sent over a TCP/IP network, enabling a Linux host to mount remote block storage as if it were a locally attached disk. Without the open-iscsi initiator installed and the iscsid daemon running, the host has no ability to discover or connect to iSCSI targets on the network. This installation step is therefore a precondition for any iSCSI storage operation, including target discovery, session login, and mounting volumes."
      ],
      "dependencies": [
        "Ubuntu 22.04 host is accessible with sudo privileges.",
        "Network connectivity to the iSCSI target is available."
      ],
      "irreversible": false,
      "steps": [
        {
          "text": "Run the apt package index update.",
          "completion": "Terminal returns to the prompt with no errors.",
          "actions": ["sudo apt update"],
          "notes": null
        },
        {
          "text": "Install the open-iscsi package.",
          "completion": "Terminal shows 'Setting up open-iscsi' and returns to the prompt.",
          "actions": ["sudo apt install open-iscsi"],
          "notes": null
        },
        {
          "text": "Enable the iscsid service to start on boot.",
          "completion": "Terminal returns to the prompt with no errors.",
          "actions": ["sudo systemctl enable iscsid"],
          "notes": null
        },
        {
          "text": "Start the iscsid service.",
          "completion": "Terminal returns to the prompt with no errors.",
          "actions": ["sudo systemctl start iscsid"],
          "notes": null
        },
        {
          "text": "Verify the iscsid service is running.",
          "completion": "Output shows 'active (running)' in the service status.",
          "actions": ["systemctl status iscsid"],
          "notes": null
        }
      ]
    }
  ]
}
