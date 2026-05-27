---
project: blueprinted.io
summary: >-
  blueprinted.io is a solo-developer personal rebuild of an existing knowledge management MVP.
  It captures tasks, principles, and workflows from technical documents via an AI-assisted ingestion
  pipeline. The core philosophy is human-in-the-loop: AI assists ingestion and search, but humans
  confirm everything — no machine may perform a confirmed state transition on a governed record.
  The v1 platform is designed for a single operator and tenant.
stack: Python/FastAPI, PostgreSQL/pgvector, React/TypeScript, ARQ, Authentik
repos:
  platform: "blueprinted-io/platform — Python backend, at platform/"
  app: "blueprinted-io/app — React frontend, at app/"
  note: "Working directory root (/home/ewan/projects/blueprinted/) is not a git repo. Commit and push from within each subdirectory."
state: "Sprint 8 — Core read screens (in progress)"
spec: "docs/requirements.md (v4.5)"
sessions: "SESSIONS.md (active — one entry only); SESSIONS_ARCHIVE.md (history — do not load unless explicitly asked)"
sprints: SPRINTS.md
rules: docs/rules.md
architecture: "docs/architecture.md — code architecture conventions and session working-practice rules (planning, ambiguity handling, session scope)"
session_protocol: docs/session_protocol.md
code_style: docs/code_style.md
---

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
