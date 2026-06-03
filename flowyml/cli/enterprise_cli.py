"""Enterprise CLI commands for stack governance.

Extends the main ``flowyml`` CLI with commands for enterprise stack management,
policy validation, and audit.

Commands::

    flowyml stack list          # List all stacks (local + remote)
    flowyml stack inspect NAME  # Detailed stack definition view
    flowyml stack import URI    # Import stacks from remote source
    flowyml stack lock          # Lock resolved stacks
    flowyml stack verify        # Verify locked stacks match their digests
    flowyml stack diff A B      # Compare two stack definitions

    flowyml policy check        # Validate policies for a stack/env

    flowyml runs list           # List audit records
    flowyml runs inspect ID     # Show audit detail
"""

from __future__ import annotations

import rich_click as click
from flowyml.cli.rich_utils import recho


# ── Stack Enterprise Commands ─────────────────────────────────────────


@click.group("stack-enterprise")
def stack_enterprise_cli() -> None:
    """Enterprise stack management commands."""
    pass


@stack_enterprise_cli.command("list")
@click.option("--source", "-s", help="Filter by source URI")
@click.option("--format", "fmt", type=click.Choice(["table", "json", "yaml"]), default="table")
def stack_list(source: str | None, fmt: str) -> None:
    """List all available stacks across all sources.

    Shows stacks from local YAML files, project config sources, and
    the global registry.
    """
    from flowyml.cli.rich_utils import get_console, RICH_AVAILABLE

    try:
        from flowyml.stacks.enterprise.resolver import StackResolver

        resolver = StackResolver()
        stacks = resolver.list_stacks()

        if not stacks:
            recho("[yellow]ℹ️  No stacks found.")
            recho("   Create stack YAML files in stacks/ or configure registry.sources in flowyml.yaml.")
            return

        if fmt == "json":
            import json

            data = [{"name": s.name, "version": s.version, "source": s.source} for s in stacks]
            recho(json.dumps(data, indent=2))
            return

        if fmt == "yaml":
            import yaml

            data = [{"name": s.name, "version": s.version, "source": s.source} for s in stacks]
            recho(yaml.safe_dump(data, default_flow_style=False))
            return

        console = get_console()
        if RICH_AVAILABLE and console:
            from rich.table import Table as RichTable
            from rich import box as rich_box

            table = RichTable(
                title="[bold cyan]📦 Available Stacks[/bold cyan]",
                box=rich_box.ROUNDED,
                border_style="cyan",
            )
            table.add_column("Name", style="cyan bold", width=25)
            table.add_column("Version", style="green", width=12)
            table.add_column("Source", style="dim", width=40)

            for s in stacks:
                table.add_row(
                    s.name,
                    s.version or "—",
                    s.source or "local",
                )
            console.print(table)
        else:
            recho(f"Found {len(stacks)} stacks:\n")
            for s in stacks:
                recho(f"  {s.name} (v{s.version or '?'}) — {s.source or 'local'}")

    except ImportError:
        recho("[red]✗ Enterprise stack module not available.", err=True)
    except Exception as e:
        recho(f"[red]✗ Error listing stacks: {e}", err=True)


@stack_enterprise_cli.command("inspect")
@click.argument("stack_name")
@click.option("--version", "-v", help="Stack version")
def stack_inspect(stack_name: str, version: str | None) -> None:
    """Show detailed information about a stack definition."""
    from flowyml.cli.rich_utils import get_console, RICH_AVAILABLE

    try:
        from flowyml.stacks.enterprise.resolver import StackResolver

        resolver = StackResolver()
        try:
            definition = resolver.resolve(stack=stack_name)
        except Exception as e:
            recho(f"[red]✗ Stack '{stack_name}' not found: {e}", err=True)
            return

        console = get_console()
        if RICH_AVAILABLE and console:
            from rich.panel import Panel
            from rich.syntax import Syntax
            import yaml

            data = definition.model_dump(mode="json", by_alias=True, exclude_none=True)
            yaml_str = yaml.safe_dump(data, sort_keys=False, default_flow_style=False)

            panel = Panel(
                Syntax(yaml_str, "yaml", theme="monokai"),
                title=f"[bold cyan]📦 {definition.name} v{definition.version}[/bold cyan]",
                subtitle=f"[dim]backend: {definition.backend} | digest: {definition.compute_digest()[:20]}...[/dim]",
                border_style="cyan",
            )
            console.print(panel)
        else:
            import yaml

            data = definition.model_dump(mode="json", by_alias=True, exclude_none=True)
            recho(yaml.safe_dump(data, sort_keys=False, default_flow_style=False))

    except ImportError:
        recho("[red]✗ Enterprise stack module not available.", err=True)
    except Exception as e:
        recho(f"[red]✗ Error inspecting stack: {e}", err=True)


@stack_enterprise_cli.command("import")
@click.argument("source_uri")
def stack_import(source_uri: str) -> None:
    """Import stacks from a remote source.

    Downloads stack definitions from a Git repository, HTTP URL, or
    registry index and caches them locally.

    Examples:
        flowyml stack import github://my-org/flowyml-stacks@v1.2.0

        flowyml stack import https://registry.example.com/stacks/prod.yaml
    """
    try:
        from flowyml.stacks.enterprise.resolver import StackResolver

        resolver = StackResolver()
        definition = resolver.resolve_from_uri(source_uri)

        recho(f"[green]✓ Imported stack from {source_uri}:")
        recho(f"  • {definition.name} v{definition.version} (backend: {definition.backend})")

    except ImportError:
        recho("[red]✗ Enterprise stack module not available.", err=True)
    except Exception as e:
        recho(f"[red]✗ Error importing stacks: {e}", err=True)


@stack_enterprise_cli.command("lock")
@click.option("--stack", "stack_name", help="Stack name to lock (default: all from project config)")
def stack_lock(stack_name: str | None) -> None:
    """Lock stack definitions for reproducible execution.

    Creates or updates the flowyml.lock file with digest hashes of
    resolved stack definitions.
    """
    try:
        from flowyml.stacks.enterprise.lock import StackLockManager
        from flowyml.stacks.enterprise.resolver import StackResolver

        resolver = StackResolver()
        lock_manager = StackLockManager()

        if stack_name:
            # Lock a single stack
            try:
                definition = resolver.resolve(stack=stack_name)
            except Exception as e:
                recho(f"[red]✗ Stack '{stack_name}' not found: {e}", err=True)
                return

            lock_manager.lock(stack_name, definition, source_uri="local")
            recho(f"[green]✓ Locked stack '{stack_name}' (digest: {definition.compute_digest()[:20]}...)")
        else:
            # Lock all stacks from project config
            from flowyml.stacks.enterprise.project_config import load_project_config

            config = load_project_config()
            if config is None:
                recho("[yellow]ℹ️  No flowyml.yaml found. Specify --stack <name> explicitly.")
                return

            locked = 0
            for env_name, env_config in config.environments.items():
                try:
                    definition = resolver.resolve(stack=env_config.stack)
                    if definition:
                        lock_manager.lock(env_config.stack, definition, source_uri="project-config")
                        locked += 1
                        recho(f"  ✓ {env_config.stack} (env: {env_name})")
                except Exception as e:
                    recho(f"  ✗ {env_config.stack} (env: {env_name}): {e}")

            recho(f"\n[green]✓ Locked {locked} stack(s) → flowyml.lock")

    except ImportError:
        recho("[red]✗ Enterprise stack module not available.", err=True)
    except Exception as e:
        recho(f"[red]✗ Error locking stacks: {e}", err=True)


@stack_enterprise_cli.command("verify")
def stack_verify() -> None:
    """Verify all locked stacks match their recorded digests.

    Reads flowyml.lock and checks that each stack definition still
    matches the locked digest.
    """
    try:
        from flowyml.stacks.enterprise.lock import StackLockManager

        lock_manager = StackLockManager()
        results = lock_manager.verify()

        if not results:
            recho("[yellow]ℹ️  No stacks locked. Run 'flowyml stack lock' first.")
            return

        all_ok = True
        for r in results:
            if r.status == "verified":
                recho(f"  [green]✓[/green] {r.stack_name}: {r.message}")
            elif r.status == "modified":
                recho(f"  [red]✗[/red] {r.stack_name}: {r.message}")
                all_ok = False
            elif r.status == "missing":
                recho(f"  [yellow]?[/yellow] {r.stack_name}: {r.message}")
                all_ok = False

        if all_ok:
            recho("\n[green]✓ All locked stacks verified.")
        else:
            recho("\n[red]✗ Lock verification failed. Run 'flowyml stack lock' to update.")

    except ImportError:
        recho("[red]✗ Enterprise stack module not available.", err=True)
    except Exception as e:
        recho(f"[red]✗ Error verifying stacks: {e}", err=True)


@stack_enterprise_cli.command("diff")
@click.argument("stack_a")
@click.argument("stack_b")
def stack_diff(stack_a: str, stack_b: str) -> None:
    """Compare two stack definitions side by side."""
    try:
        from flowyml.stacks.enterprise.resolver import StackResolver
        import yaml

        resolver = StackResolver()
        try:
            def_a = resolver.resolve(stack=stack_a)
        except Exception as e:
            recho(f"[red]✗ Stack '{stack_a}' not found: {e}", err=True)
            return
        try:
            def_b = resolver.resolve(stack=stack_b)
        except Exception as e:
            recho(f"[red]✗ Stack '{stack_b}' not found: {e}", err=True)
            return

        data_a = yaml.safe_dump(
            def_a.model_dump(mode="json", by_alias=True, exclude_none=True),
            sort_keys=True,
            default_flow_style=False,
        )
        data_b = yaml.safe_dump(
            def_b.model_dump(mode="json", by_alias=True, exclude_none=True),
            sort_keys=True,
            default_flow_style=False,
        )

        import difflib

        diff = difflib.unified_diff(
            data_a.splitlines(keepends=True),
            data_b.splitlines(keepends=True),
            fromfile=f"{stack_a} v{def_a.version}",
            tofile=f"{stack_b} v{def_b.version}",
        )
        diff_text = "".join(diff)

        if not diff_text:
            recho(f"[green]✓ Stacks '{stack_a}' and '{stack_b}' are identical.")
        else:
            from flowyml.cli.rich_utils import get_console, RICH_AVAILABLE

            console = get_console()
            if RICH_AVAILABLE and console:
                from rich.syntax import Syntax

                console.print(Syntax(diff_text, "diff", theme="monokai"))
            else:
                recho(diff_text)

    except ImportError:
        recho("[red]✗ Enterprise stack module not available.", err=True)
    except Exception as e:
        recho(f"[red]✗ Error comparing stacks: {e}", err=True)


# ── Policy Commands ────────────────────────────────────────────────────


@click.group("policy")
def policy_cli() -> None:
    """Policy validation commands."""
    pass


@policy_cli.command("check")
@click.option("--stack", "stack_name", help="Stack name to validate")
@click.option("--env", "env_name", help="Environment to validate")
@click.option("--project", help="Project name (for permission checks)")
def policy_check(stack_name: str | None, env_name: str | None, project: str | None) -> None:
    """Validate policies for a stack or environment.

    Checks all policy rules and reports any violations.

    Examples:
        flowyml policy check --stack aml_cpu_small

        flowyml policy check --env prod --project churn-modeling
    """
    if not stack_name and not env_name:
        recho("[red]✗ Specify either --stack or --env.", err=True)
        return

    try:
        from flowyml.stacks.enterprise.resolver import StackResolver
        from flowyml.stacks.enterprise.policy import PolicyEngine, PolicyContext

        resolver = StackResolver()
        try:
            definition = resolver.resolve(stack=stack_name, env=env_name)
        except Exception as e:
            recho(f"[red]✗ Could not resolve stack: {e}", err=True)
            return

        engine = PolicyEngine()
        context = PolicyContext(
            stack=definition,
            project_name=project,
            environment=env_name,
        )
        results = engine.validate(context)

        passed = [r for r in results if r.status == "passed"]
        warnings = [r for r in results if r.status == "warning"]
        failed = [r for r in results if r.status == "failed"]

        recho(f"\n[bold]Policy Check: {definition.name} v{definition.version}[/bold]\n")

        for r in passed:
            recho(f"  [green]✓[/green] {r.rule_name}: {r.message}")
        for r in warnings:
            recho(f"  [yellow]⚠[/yellow] {r.rule_name}: {r.message}")
            if r.suggestion:
                recho(f"    [dim]→ {r.suggestion}[/dim]")
        for r in failed:
            recho(f"  [red]✗[/red] {r.rule_name}: {r.message}")
            if r.suggestion:
                recho(f"    [dim]→ {r.suggestion}[/dim]")

        recho(f"\n  Passed: {len(passed)} | Warnings: {len(warnings)} | Failed: {len(failed)}")

        if failed:
            recho("\n[red]✗ Policy check FAILED.[/red]")
        else:
            recho("\n[green]✓ Policy check PASSED.[/green]")

    except ImportError:
        recho("[red]✗ Enterprise stack module not available.", err=True)
    except Exception as e:
        recho(f"[red]✗ Error checking policy: {e}", err=True)


# ── Runs / Audit Commands ──────────────────────────────────────────────


@click.group("runs")
def runs_cli() -> None:
    """Pipeline run audit commands."""
    pass


@runs_cli.command("list")
@click.option("--limit", default=20, help="Maximum records to show")
@click.option("--project", help="Filter by project")
def runs_list(limit: int, project: str | None) -> None:
    """List recent pipeline run audit records."""
    try:
        from flowyml.stacks.enterprise.audit import AuditStore
        from flowyml.cli.rich_utils import get_console, RICH_AVAILABLE

        store = AuditStore()
        records = store.list_records(limit=limit)

        if project:
            records = [r for r in records if r.project == project]

        if not records:
            recho("[yellow]ℹ️  No audit records found.")
            return

        console = get_console()
        if RICH_AVAILABLE and console:
            from rich.table import Table as RichTable
            from rich import box as rich_box

            table = RichTable(
                title=f"[bold cyan]📋 Pipeline Runs ({len(records)})[/bold cyan]",
                box=rich_box.ROUNDED,
                border_style="cyan",
            )
            table.add_column("Run ID", style="cyan", width=12)
            table.add_column("Pipeline", style="bold", width=20)
            table.add_column("Stack", width=15)
            table.add_column("Env", width=8)
            table.add_column("Status", width=10)
            table.add_column("Started", style="dim", width=20)

            for r in records:
                status_style = {
                    "succeeded": "[green]✓ succeeded[/green]",
                    "failed": "[red]✗ failed[/red]",
                    "running": "[yellow]⏳ running[/yellow]",
                    "pending": "[dim]⏸ pending[/dim]",
                }.get(r.status, r.status)

                table.add_row(
                    r.run_id[:8] + "…",
                    r.pipeline,
                    r.stack_name,
                    r.environment,
                    status_style,
                    r.started_at[:19] if r.started_at else "—",
                )
            console.print(table)
        else:
            for r in records:
                recho(f"  {r.run_id[:8]} | {r.pipeline} | {r.stack_name} | {r.status}")

    except ImportError:
        recho("[red]✗ Enterprise stack module not available.", err=True)
    except Exception as e:
        recho(f"[red]✗ Error listing runs: {e}", err=True)


@runs_cli.command("inspect")
@click.argument("run_id")
def runs_inspect(run_id: str) -> None:
    """Show detailed audit information for a pipeline run."""
    try:
        from flowyml.stacks.enterprise.audit import AuditStore

        store = AuditStore()
        record = store.get(run_id)

        if record is None:
            recho(f"[red]✗ Run '{run_id}' not found.", err=True)
            return

        import yaml

        data = record.model_dump(mode="json", exclude_none=True)
        recho(yaml.safe_dump(data, sort_keys=False, default_flow_style=False))

    except ImportError:
        recho("[red]✗ Enterprise stack module not available.", err=True)
    except Exception as e:
        recho(f"[red]✗ Error inspecting run: {e}", err=True)


@runs_cli.command("export")
@click.argument("run_id")
@click.option("--format", "fmt", type=click.Choice(["json", "yaml"]), default="json")
@click.option("--output", "-o", help="Output file path")
def runs_export(run_id: str, fmt: str, output: str | None) -> None:
    """Export an audit record."""
    try:
        from flowyml.stacks.enterprise.audit import AuditStore

        store = AuditStore()
        exported = store.export(run_id, format=fmt)

        if output:
            with open(output, "w") as f:
                f.write(exported)
            recho(f"[green]✓ Exported to {output}")
        else:
            recho(exported)

    except ImportError:
        recho("[red]✗ Enterprise stack module not available.", err=True)
    except Exception as e:
        recho(f"[red]✗ Error exporting run: {e}", err=True)


# ── Registration Helper ──────────────────────────────────────────────


def register_enterprise_commands(cli_group: click.Group) -> None:
    """Register all enterprise CLI commands into the main CLI group.

    Merges stack enterprise subcommands into the existing ``stack`` group
    so users can run ``flowyml stack list``, ``flowyml stack lock``, etc.
    Also registers ``policy`` and ``runs`` as top-level groups.

    Args:
        cli_group: The main ``flowyml`` CLI group to register into.
    """
    # Try to merge enterprise stack commands into the existing 'stack' group
    existing_stack_group = cli_group.commands.get("stack")
    if isinstance(existing_stack_group, click.Group):
        # Merge enterprise commands into the existing stack group
        for cmd_name, cmd in stack_enterprise_cli.commands.items():
            if cmd_name not in existing_stack_group.commands:
                existing_stack_group.add_command(cmd, cmd_name)
    else:
        # No existing stack group — register as a new one
        cli_group.add_command(stack_enterprise_cli, "stack")

    # Also register as 'stack-gov' alias for backward compatibility
    cli_group.add_command(stack_enterprise_cli, "stack-gov")

    # Register policy and runs as top-level groups
    cli_group.add_command(policy_cli, "policy")
    cli_group.add_command(runs_cli, "runs")
