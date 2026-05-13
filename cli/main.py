"""Blueprinted CLI — all operational tasks for a running instance.

Usage:
    blueprinted migrate [--dry-run] [--tenant SLUG] [--status]
    blueprinted healthcheck
"""

import subprocess
import sys
from pathlib import Path

import httpx
import typer

app = typer.Typer(
    name="blueprinted",
    help="Blueprinted platform CLI",
    add_completion=False,
)

# Resolve the project root so the CLI works regardless of cwd
PROJECT_ROOT = Path(__file__).parent.parent
ALEMBIC_INI = PROJECT_ROOT / "migrations" / "alembic.ini"


@app.command("migrate")
def migrate(
    dry_run: bool = typer.Option(False, "--dry-run", help="Show pending migrations, no changes"),
    tenant: str = typer.Option("", "--tenant", help="Migrate a single tenant schema"),
    status: bool = typer.Option(False, "--status", help="Show current migration version"),
) -> None:
    """Run pending database migrations.

    Migrates the system schema first, then all tenant schemas in alphabetical
    order. Use --tenant to target a single schema (e.g. for recovery).
    """
    alembic_cmd = ["alembic", "-c", str(ALEMBIC_INI)]

    if status:
        result = subprocess.run(  # noqa: S603
            [*alembic_cmd, "current"], check=False
        )
        raise typer.Exit(result.returncode)

    if dry_run:
        typer.echo("Dry run — showing pending migrations (no changes applied):")
        result = subprocess.run(  # noqa: S603
            [*alembic_cmd, "history", "--indicate-current"], check=False
        )
        raise typer.Exit(result.returncode)

    # Sprint 4: when tenant schemas exist, iterate them here after system schema.
    if tenant:
        typer.echo(f"Migrating tenant schema: {tenant}")
        typer.echo("Single-tenant migration not yet implemented (Sprint 4)")
        raise typer.Exit(1)

    typer.echo("Migrating system schema...")
    result = subprocess.run([*alembic_cmd, "upgrade", "head"], check=False)  # noqa: S603
    if result.returncode != 0:
        typer.echo("Migration failed.", err=True)
        sys.exit(result.returncode)
    typer.echo("Migrations complete.")


@app.command()
def healthcheck() -> None:
    """Verify instance state — database connectivity and migration version."""
    typer.echo("Checking /healthz ...")
    try:
        response = httpx.get("http://localhost:8000/healthz", timeout=5)
        typer.echo(response.text)
        raise typer.Exit(0 if response.status_code == 200 else 1)
    except httpx.ConnectError as exc:
        typer.echo("Cannot connect to API. Is the server running?", err=True)
        raise typer.Exit(1) from exc


if __name__ == "__main__":
    app()
