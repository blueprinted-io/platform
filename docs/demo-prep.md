# Demo Prep — Real Data Population

Goal: populate the system with real learning content via the API, using an agent credential, to demonstrate the full governance lifecycle to a non-technical audience.

## Why this matters

- Real content makes the governance model legible without explanation
- Agent ingestion via API proves the "AI as one consumer among many" architecture in practice
- Human confirmation step is the demo moment — machine drafts, human approves, enforced in code

## What needs doing

### 1. Users
- Create real user accounts in Authentik (at minimum: an admin, a contributor, a viewer)
- Assign domain access to contributor

### 2. Machine credential path
- Wire up API key issuance properly (currently a placeholder)
- Admin creates API key with `agent:` role, receives `bp_` prefixed key once
- Verify agent auth path attaches machine principal to request context correctly

### 3. Agent-driven ingestion
- Agent authenticates via API key
- Submits real learning documents through existing ingestion endpoint
- Triage and extraction run as normal
- Content lands in review queue awaiting human confirmation

### 4. Human confirmation
- Log in as reviewer/admin
- Walk through review queue with real content
- Confirm a record — this is the demo moment
- Shows: machine can draft, human must approve, no exceptions

## Demo narrative

> "What you're looking at is content that was ingested by an AI agent — it drafted, extracted, and structured it. But it can't publish it. A human has to confirm every record. That's not a policy, it's enforced in the code."

## Notes

- Seeding via DB directly is fine for test data but defeats the purpose here — go via the API
- The ingestion + confirmation flow also stress-tests auth, schema, and the review queue UI in one pass
- Keep a confirmed record and a pending record available for the demo — shows the queue in use
