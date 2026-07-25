"""Temporary canary to exercise the CI auto-fix bot end to end. Safe to delete.

Introduces a deliberate ruff F401 (unused import) so the CI lint step fails
and the auto-fix pipeline is triggered. Expected outcome: the bot opens an
`autofix/<sha>` PR that removes the unused import below.
"""
