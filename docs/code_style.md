# Code Style — blueprinted.io

## Language

- Application code: Python
- Prose (comments, docstrings, error messages, documentation): British English
- Technical terms (function names, variable names, API paths): standard conventions regardless of locale

---

## Formatting

- Follow Ruff defaults, enforced in CI
- Type hints: always, everywhere, no exceptions

---

## Docstrings

- Public functions and classes: one-line summary, plus parameter notes if non-obvious
- No multi-line blocks where a single line suffices

---

## Comments

- Explain *why*, not *what* — code explains what; comments explain intent, constraints, and non-obvious decisions
- No commented-out code committed to main

---

## What Claude Should Never Do

- Modify an existing test file without a `TEST_REVISED` authorisation
- Access the database directly from outside the core service
- Perform a confirmed state transition from an automated process
- Add a relationship kind without explicit instruction
- Change the embedding column dimension without a migration
- Remove or disable the ARQ worker startup hook
- Use `print()` in application code
- Hardcode configuration values
- Make a silent assumption when the spec is ambiguous — stop and ask
- Expand session scope without flagging it
- Proceed past a plan step without confirmation
