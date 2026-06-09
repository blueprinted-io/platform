"""Blueprinted CLI — all operational tasks for a running instance.

Usage:
    blueprinted migrate [--dry-run] [--tenant SLUG] [--status]
    blueprinted healthcheck
    blueprinted tenants list|create|delete
    blueprinted backup [--output PATH]
    blueprinted upgrade
    blueprinted api-keys create|revoke
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
        result = subprocess.run(
            [*alembic_cmd, "current"], check=False
        )
        raise typer.Exit(result.returncode)

    if dry_run:
        typer.echo("Dry run — showing pending migrations (no changes applied):")
        result = subprocess.run(
            [*alembic_cmd, "history", "--indicate-current"], check=False
        )
        raise typer.Exit(result.returncode)

    if tenant:
        typer.echo(f"Migrating tenant schema: {tenant}")
        typer.echo("Single-tenant migration not yet implemented (Sprint 10+)")
        raise typer.Exit(1)

    typer.echo("Migrating system schema...")
    result = subprocess.run([*alembic_cmd, "upgrade", "head"], check=False)
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


# ---------------------------------------------------------------------------
# Tenants
# ---------------------------------------------------------------------------

tenants_app = typer.Typer(help="Manage tenants (multi-tenant deployments).")
app.add_typer(tenants_app, name="tenants")


@tenants_app.command("list")
def tenants_list() -> None:
    """List all registered tenants."""
    typer.echo("Tenant management is not yet implemented (single-tenant v1).")
    typer.echo("Tenant: default")


@tenants_app.command("create")
def tenants_create(
    slug: str = typer.Argument(help="Unique tenant slug (e.g. acme)"),
) -> None:
    """Register a new tenant schema and run its migrations."""
    typer.echo(f"Creating tenant: {slug}")
    typer.echo("Multi-tenant provisioning not yet implemented.")
    raise typer.Exit(1)


@tenants_app.command("delete")
def tenants_delete(
    slug: str = typer.Argument(help="Tenant slug to remove"),
    confirm: bool = typer.Option(False, "--confirm", help="Skip confirmation prompt"),
) -> None:
    """Remove a tenant schema. Irreversible — take a backup first."""
    if not confirm:
        confirmed = typer.confirm(
            f"Delete tenant '{slug}' and all its data? This is irreversible."
        )
        if not confirmed:
            typer.echo("Aborted.")
            raise typer.Exit(0)
    typer.echo(f"Deleting tenant: {slug}")
    typer.echo("Multi-tenant removal not yet implemented.")
    raise typer.Exit(1)


# ---------------------------------------------------------------------------
# Backup
# ---------------------------------------------------------------------------

@app.command()
def backup(
    output: str = typer.Option("", "--output", "-o", help="Output file path (default: stdout)"),
    database_url: str = typer.Option(
        "",
        "--database-url",
        envvar="DATABASE_URL_SYNC",
        help="PostgreSQL connection string",
    ),
) -> None:
    """Dump all tenant schemas using pg_dump.

    Recommended before running blueprinted upgrade.
    """
    if not database_url:
        typer.echo(
            "DATABASE_URL_SYNC is not set. Pass --database-url or set the env var.", err=True
        )
        raise typer.Exit(1)

    cmd = ["pg_dump", database_url]
    if output:
        cmd += ["-f", output]
        typer.echo(f"Backing up to {output} ...")
    else:
        typer.echo("Dumping to stdout ...")

    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        typer.echo("Backup failed.", err=True)
        raise typer.Exit(result.returncode)
    typer.echo("Backup complete." if output else "")


# ---------------------------------------------------------------------------
# Upgrade
# ---------------------------------------------------------------------------

@app.command()
def upgrade(
    skip_backup_prompt: bool = typer.Option(
        False, "--skip-backup-prompt", help="Skip the backup reminder"
    ),
    api_url: str = typer.Option(
        "http://localhost:8000", "--api-url", help="API base URL for health check"
    ),
) -> None:
    """Pre-flight check, optional backup reminder, migrate, restart Docker Compose."""
    if not skip_backup_prompt:
        confirmed = typer.confirm("Have you taken a backup before upgrading?")
        if not confirmed:
            typer.echo("Run 'blueprinted backup' first, then retry with the backup confirmed.")
            raise typer.Exit(1)

    typer.echo("Running pre-flight checks...")
    try:
        resp = httpx.get(f"{api_url}/healthz", timeout=5)
        if resp.status_code != 200:
            typer.echo(f"Health check failed ({resp.status_code}). Aborting upgrade.", err=True)
            raise typer.Exit(1)
    except httpx.ConnectError:
        typer.echo("Cannot reach API — proceeding with offline upgrade.")

    typer.echo("Applying migrations...")
    alembic_cmd = ["alembic", "-c", str(ALEMBIC_INI), "upgrade", "head"]
    result = subprocess.run(alembic_cmd, check=False)
    if result.returncode != 0:
        typer.echo("Migration failed — aborting upgrade.", err=True)
        raise typer.Exit(result.returncode)

    typer.echo("Restarting services...")
    compose_result = subprocess.run(
        ["docker", "compose", "-f", str(PROJECT_ROOT / "deploy" / "docker-compose.yml"),
         "restart", "api", "worker"],
        check=False,
    )
    if compose_result.returncode != 0:
        typer.echo("Docker Compose restart failed — check container logs.", err=True)
        raise typer.Exit(compose_result.returncode)

    typer.echo("Upgrade complete.")


# ---------------------------------------------------------------------------
# API keys
# ---------------------------------------------------------------------------

api_keys_app = typer.Typer(help="Manage scoped API keys for machine credentials (§5.3).")
app.add_typer(api_keys_app, name="api-keys")


@api_keys_app.command("create")
def api_keys_create(
    name: str = typer.Argument(help="Human-readable label for this key"),
    role: str = typer.Option(..., "--role", help="Agent role (e.g. agent:workflow_consumer)"),
    api_url: str = typer.Option("http://localhost:8000", "--api-url", help="API base URL"),
    token: str = typer.Option("", "--token", envvar="BLUEPRINTED_ADMIN_TOKEN",
                               help="Admin Bearer token"),
) -> None:
    """Create a scoped API key. The raw key is shown once — store it securely."""
    if not token:
        typer.echo(
            "Admin token required. Pass --token or set BLUEPRINTED_ADMIN_TOKEN.", err=True
        )
        raise typer.Exit(1)

    try:
        resp = httpx.post(
            f"{api_url}/api/v1/admin/api-keys",
            json={"name": name, "role": role},
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
    except httpx.ConnectError as exc:
        typer.echo("Cannot connect to API.", err=True)
        raise typer.Exit(1) from exc

    if resp.status_code != 201:
        typer.echo(f"Error {resp.status_code}: {resp.text}", err=True)
        raise typer.Exit(1)

    data = resp.json()
    typer.echo(f"Created API key '{data['name']}' ({data['id']})")
    typer.echo(f"Role: {data['role']}")
    typer.echo(f"\nKey (shown once — store securely):\n  {data['raw_key']}")


@api_keys_app.command("revoke")
def api_keys_revoke(
    key_id: str = typer.Argument(help="UUID of the API key to revoke"),
    api_url: str = typer.Option("http://localhost:8000", "--api-url", help="API base URL"),
    token: str = typer.Option("", "--token", envvar="BLUEPRINTED_ADMIN_TOKEN",
                               help="Admin Bearer token"),
) -> None:
    """Revoke a scoped API key. Immediate effect."""
    if not token:
        typer.echo(
            "Admin token required. Pass --token or set BLUEPRINTED_ADMIN_TOKEN.", err=True
        )
        raise typer.Exit(1)

    try:
        resp = httpx.delete(
            f"{api_url}/api/v1/admin/api-keys/{key_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
    except httpx.ConnectError as exc:
        typer.echo("Cannot connect to API.", err=True)
        raise typer.Exit(1) from exc

    if resp.status_code == 204:
        typer.echo(f"API key {key_id} revoked.")
    else:
        typer.echo(f"Error {resp.status_code}: {resp.text}", err=True)
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
