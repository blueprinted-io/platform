# Session Protocol — blueprinted.io

## Starting a session

1. Read `CLAUDE.md` first.
2. Read `SESSIONS.md` for immediate context. Do not read `SESSIONS_ARCHIVE.md` unless explicitly asked.
3. State what you are working on and confirm understanding of the relevant spec sections before writing any code.

---

## Closeout format

Four sections only. Target 15–25 lines total. No git hashes. No docker commands. No "watch out for"
lists — if something needs watching, fix it or file it as broken. Done means committed. Broken means
broken, stated plainly.

```
## Session — YYYY-MM-DD (one-line topic)

### Decisions
One line per decision. Architectural choices, deliberate deferrals, spec deviations.
Only things that affect future work and are not obvious from the code.

### Done
One line per completed item. Committed work only.
Include TEST_REVISED markers where applicable.

### Broken / Incomplete
"X is broken because Y." Omit section if nothing is broken.

### Next
Single most important thing to pick up. One short paragraph.
State any prerequisites in one sentence.
```

---

## Closeout mechanic

1. Write new session entry in the format above.
2. Review the entry for secrets — redact actual values; env var names are fine.
3. Move the current `SESSIONS.md` entry to the top of `SESSIONS_ARCHIVE.md`, above existing entries.
4. Replace `SESSIONS.md` content with the new entry only, leaving the header block unchanged.
5. Commit both files: `chore: session close-out — [brief description]`
6. Push to origin.
