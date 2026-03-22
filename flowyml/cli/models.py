"""CLI commands for model registry management."""

import rich_click as click
from pathlib import Path
from flowyml.registry.model_registry import ModelRegistry, ModelStage
from flowyml.utils.config import get_config
from flowyml.cli.rich_utils import get_console, print_rich_text, print_rich_panel
from flowyml.cli.rich_utils import recho


def get_registry() -> ModelRegistry:
    """Get ModelRegistry instance with default path."""
    config = get_config()
    registry_path = Path(config.flowyml_home) / "model_registry"
    return ModelRegistry(str(registry_path))


@click.command()
@click.argument("model_name", required=False)
@click.option(
    "--stage",
    type=click.Choice(["development", "staging", "production", "archived"]),
    help="Filter by stage",
)
def list_models(model_name: str | None, stage: str | None) -> None:
    """List all models or versions of a specific model.

    If MODEL_NAME is provided, lists all versions of that model.
    Otherwise, lists all registered models.
    """
    console = get_console()
    try:
        registry = get_registry()

        if model_name:
            # List versions of a specific model
            versions = registry.list_versions(model_name)

            if not versions:
                print_rich_text(
                    ("❌ ", "red"),
                    (f"Model '{model_name}' not found or has no versions.", "red"),
                    console=console,
                )
                return

            # Filter by stage if provided
            if stage:
                stage_enum = ModelStage(stage)
                versions = [v for v in versions if v.stage == stage_enum]

            if not versions:
                print_rich_text(
                    ("❌ ", "red"),
                    (f"No versions found for model '{model_name}' with stage '{stage}'.", "red"),
                    console=console,
                )
                return

            # Use rich table for versions
            if console:
                from rich.table import Table
                from rich import box

                table = Table(
                    title=f"[bold cyan]📦 Model: {model_name}[/bold cyan]",
                    box=box.ROUNDED,
                    show_header=True,
                    header_style="bold cyan",
                    border_style="cyan",
                )
                table.add_column("Version", style="cyan", width=15)
                table.add_column("Stage", justify="center", width=12)
                table.add_column("Framework", width=12)
                table.add_column("Created", width=20)
                table.add_column("Metrics", style="yellow", width=30)
                table.add_column("Tags", style="dim", width=30)

                # Sort by created_at (newest first)
                versions.sort(key=lambda v: v.created_at, reverse=True)

                for version in versions:
                    stage_icon = {
                        ModelStage.DEVELOPMENT: "🔧",
                        ModelStage.STAGING: "🧪",
                        ModelStage.PRODUCTION: "✅",
                        ModelStage.ARCHIVED: "📦",
                    }.get(version.stage, "📌")

                    stage_text = f"{stage_icon} {version.stage.value}"
                    metrics_str = (
                        ", ".join(f"{k}={v:.4f}" for k, v in version.metrics.items()) if version.metrics else "-"
                    )
                    tags_str = ", ".join(f"{k}={v}" for k, v in version.tags.items()) if version.tags else "-"

                    table.add_row(
                        version.version,
                        stage_text,
                        version.framework,
                        version.created_at,
                        metrics_str,
                        tags_str,
                    )

                console.print(table)
                if version.description:
                    console.print(f"[dim]Description: {version.description}[/dim]")
                console.print()
            else:
                # Fallback to simple output
                recho(f"\n📦 Model: {model_name}")
                recho(f"   Versions: {len(versions)}\n")
                versions.sort(key=lambda v: v.created_at, reverse=True)
                for version in versions:
                    stage_icon = {
                        ModelStage.DEVELOPMENT: "🔧",
                        ModelStage.STAGING: "🧪",
                        ModelStage.PRODUCTION: "✅",
                        ModelStage.ARCHIVED: "📦",
                    }.get(version.stage, "📌")
                    recho(f"  {stage_icon} {version.version}")
                    recho(f"     Stage: {version.stage.value}")
                    recho(f"     Framework: {version.framework}")
                    recho(f"     Created: {version.created_at}")
                    if version.metrics:
                        metrics_str = ", ".join(f"{k}={v:.4f}" for k, v in version.metrics.items())
                        recho(f"     Metrics: {metrics_str}")
                    if version.tags:
                        tags_str = ", ".join(f"{k}={v}" for k, v in version.tags.items())
                        recho(f"     Tags: {tags_str}")
                    if version.description:
                        recho(f"     Description: {version.description}")
                    recho()
        else:
            # List all models
            model_names = registry.list_models()

            if not model_names:
                print_rich_panel(
                    "Register a model using ModelRegistry.register() in your pipeline.",
                    title="📭 No models registered yet",
                    style="yellow",
                    console=console,
                )
                return

            # Use rich table for all models
            if console:
                from rich.table import Table
                from rich import box

                table = Table(
                    title=f"[bold cyan]📦 Registered Models: {len(model_names)}[/bold cyan]",
                    box=box.ROUNDED,
                    show_header=True,
                    header_style="bold cyan",
                    border_style="cyan",
                )
                table.add_column("Model", style="cyan", width=30)
                table.add_column("Versions", justify="center", width=10)
                table.add_column("Latest Version", width=15)
                table.add_column("Stage", justify="center", width=12)
                table.add_column("Framework", width=12)

                for name in sorted(model_names):
                    versions = registry.list_versions(name)
                    latest = registry.get_latest_version(name)

                    if latest:
                        stage_icon = {
                            ModelStage.DEVELOPMENT: "🔧",
                            ModelStage.STAGING: "🧪",
                            ModelStage.PRODUCTION: "✅",
                            ModelStage.ARCHIVED: "📦",
                        }.get(latest.stage, "📌")

                        stage_text = f"{stage_icon} {latest.stage.value}"
                        table.add_row(
                            name,
                            str(len(versions)),
                            latest.version,
                            stage_text,
                            latest.framework,
                        )
                    else:
                        table.add_row(name, "0", "-", "-", "-")

                console.print(table)
                console.print()
            else:
                # Fallback to simple output
                recho(f"\n📦 Registered Models: {len(model_names)}\n")
                for name in sorted(model_names):
                    versions = registry.list_versions(name)
                    latest = registry.get_latest_version(name)
                    if latest:
                        stage_icon = {
                            ModelStage.DEVELOPMENT: "🔧",
                            ModelStage.STAGING: "🧪",
                            ModelStage.PRODUCTION: "✅",
                            ModelStage.ARCHIVED: "📦",
                        }.get(latest.stage, "📌")
                        recho(f"  {stage_icon} {name}")
                        recho(f"     Versions: {len(versions)}")
                        recho(f"     Latest: {latest.version} ({latest.stage.value})")
                        recho()
                    else:
                        recho(f"  📌 {name} (no versions)")
                        recho()

    except Exception as e:
        recho(f"[red]✗Error listing models: {e}", err=True)
        raise click.Abort()


@click.command("promote")
@click.argument("model_name")
@click.argument("version")
@click.option(
    "--to",
    "to_stage",
    required=True,
    type=click.Choice(["development", "staging", "production", "archived"]),
    help="Target stage to promote to",
)
def promote_model(model_name: str, version: str, to_stage: str) -> None:
    """Promote a model version to a different stage.

    Example:
        flowyml models promote sentiment_classifier v1.0.0 --to production
    """
    console = get_console()
    try:
        registry = get_registry()

        # Check if model version exists
        model_version = registry.get_version(model_name, version)
        if not model_version:
            print_rich_text(
                ("❌ ", "red"),
                (f"Model '{model_name}' version '{version}' not found.", "red"),
                console=console,
            )
            raise click.Abort()

        # Convert string to ModelStage enum
        target_stage = ModelStage(to_stage)

        # Promote the model
        updated_version = registry.promote(model_name, version, target_stage)

        stage_icon = {
            ModelStage.DEVELOPMENT: "🔧",
            ModelStage.STAGING: "🧪",
            ModelStage.PRODUCTION: "✅",
            ModelStage.ARCHIVED: "📦",
        }.get(target_stage, "📌")

        # Use rich panel for promotion result
        if console:
            from rich.table import Table
            from rich import box

            table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
            table.add_column("", style="cyan", width=20)
            table.add_column("", style="green")

            table.add_row("Model", model_name)
            table.add_row("Version", version)
            table.add_row("Previous Stage", f"{model_version.stage.value}")
            table.add_row("New Stage", f"{stage_icon} {updated_version.stage.value}")

            content = "[bold green]✅ Promotion Successful[/bold green]\n\n"
            console.print(content)
            console.print(table)
        else:
            recho(
                f"✅ {stage_icon} Model '{model_name}' version '{version}' promoted to {to_stage}",
            )
            recho(f"   Previous stage: {model_version.stage.value}")
            recho(f"   New stage: {updated_version.stage.value}")

    except ValueError as e:
        recho(f"[red]❌Error: {e}", err=True)
        raise click.Abort()
    except Exception as e:
        recho(f"[red]✗Error promoting model: {e}", err=True)
        raise click.Abort()


@click.command("show")
@click.argument("model_name")
@click.argument("version")
def show_model(model_name: str, version: str) -> None:
    """Show detailed information about a specific model version."""
    console = get_console()
    try:
        registry = get_registry()

        model_version = registry.get_version(model_name, version)
        if not model_version:
            print_rich_text(
                ("❌ ", "red"),
                (f"Model '{model_name}' version '{version}' not found.", "red"),
                console=console,
            )
            raise click.Abort()

        stage_icon = {
            ModelStage.DEVELOPMENT: "🔧",
            ModelStage.STAGING: "🧪",
            ModelStage.PRODUCTION: "✅",
            ModelStage.ARCHIVED: "📦",
        }.get(model_version.stage, "📌")

        if console:
            from rich.table import Table
            from rich import box

            # Main info table
            table = Table(
                title=f"[bold cyan]{stage_icon} Model: {model_name} v{version}[/bold cyan]",
                box=box.ROUNDED,
                show_header=False,
                border_style="cyan",
            )
            table.add_column("Property", style="cyan", width=20)
            table.add_column("Value", style="green")

            table.add_row("Version", model_version.version)
            table.add_row("Stage", f"{stage_icon} {model_version.stage.value}")
            table.add_row("Framework", model_version.framework)
            table.add_row("Created", model_version.created_at)
            table.add_row("Updated", model_version.updated_at)
            table.add_row("Path", f"[dim]{model_version.model_path}[/dim]")

            if model_version.description:
                table.add_row("Description", model_version.description)
            if model_version.author:
                table.add_row("Author", model_version.author)
            if model_version.parent_version:
                table.add_row("Parent Version", model_version.parent_version)

            console.print(table)
            console.print()

            # Metrics table if available
            if model_version.metrics:
                metrics_table = Table(
                    title="[bold yellow]📊 Metrics[/bold yellow]",
                    box=box.ROUNDED,
                    show_header=True,
                    header_style="bold yellow",
                    border_style="yellow",
                )
                metrics_table.add_column("Metric", style="yellow", width=20)
                metrics_table.add_column("Value", style="green", justify="right")
                for key, value in sorted(model_version.metrics.items()):
                    metrics_table.add_row(key, f"{value:.6f}")
                console.print(metrics_table)
                console.print()

            # Tags table if available
            if model_version.tags:
                tags_table = Table(
                    title="[bold dim]🏷️  Tags[/bold dim]",
                    box=box.SIMPLE,
                    show_header=False,
                )
                tags_table.add_column("Key", style="cyan", width=20)
                tags_table.add_column("Value", style="dim")
                for key, value in sorted(model_version.tags.items()):
                    tags_table.add_row(key, value)
                console.print(tags_table)
                console.print()
        else:
            # Fallback to simple output
            recho(f"\n{stage_icon} Model: {model_name}")
            recho(f"   Version: {model_version.version}")
            recho(f"   Stage: {model_version.stage.value}")
            recho(f"   Framework: {model_version.framework}")
            recho(f"   Created: {model_version.created_at}")
            recho(f"   Updated: {model_version.updated_at}")
            recho(f"   Path: {model_version.model_path}")
            if model_version.description:
                recho(f"   Description: {model_version.description}")
            if model_version.author:
                recho(f"   Author: {model_version.author}")
            if model_version.parent_version:
                recho(f"   Parent Version: {model_version.parent_version}")
            if model_version.metrics:
                recho("\n   Metrics:")
                for key, value in sorted(model_version.metrics.items()):
                    recho(f"     {key}: {value:.6f}")
            if model_version.tags:
                recho("\n   Tags:")
                for key, value in sorted(model_version.tags.items()):
                    recho(f"     {key}: {value}")
            recho()

    except Exception as e:
        recho(f"[red]✗Error showing model: {e}", err=True)
        raise click.Abort()


@click.command("delete")
@click.argument("model_name")
@click.argument("version")
@click.confirmation_option(prompt="Are you sure you want to delete this model version?")
def delete_model(model_name: str, version: str) -> None:
    """Delete a specific model version.

    WARNING: This will permanently delete the model version and its artifacts.
    """
    try:
        registry = get_registry()

        model_version = registry.get_version(model_name, version)
        if not model_version:
            recho(f"[red]❌Model '{model_name}' version '{version}' not found.")
            raise click.Abort()

        # Delete model file
        model_path = Path(model_version.model_path)
        if model_path.exists():
            if model_path.is_file():
                model_path.unlink()
            elif model_path.is_dir():
                import shutil

                shutil.rmtree(model_path)

        # Remove from metadata
        if model_name in registry._metadata:
            registry._metadata[model_name] = [v for v in registry._metadata[model_name] if v["version"] != version]

            # Remove model entry if no versions left
            if not registry._metadata[model_name]:
                del registry._metadata[model_name]

            registry._save_metadata()

        recho(f"[green]✅Deleted model '{model_name}' version '{version}'")

    except Exception as e:
        recho(f"[red]✗Error deleting model: {e}", err=True)
        raise click.Abort()
