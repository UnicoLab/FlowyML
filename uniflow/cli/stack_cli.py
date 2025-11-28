"""Enhanced CLI for UniFlow with stack management.

Allows running pipelines with different stacks from command line
without modifying pipeline code.
"""

import click
import sys
from pathlib import Path


@click.group()
@click.version_option()
def cli() -> None:
    """UniFlow - Unified ML Pipeline Framework."""
    pass


@cli.group()
def component() -> None:
    """Manage stack components and plugins."""
    pass


@component.command("list")
@click.option("--type", "-t", "component_type", help="Filter by component type")
def list_components(component_type: str | None) -> None:
    """List all registered components."""
    from uniflow.stacks.plugins import get_component_registry

    registry = get_component_registry()
    components = registry.list_all()

    if component_type:
        if component_type in components:
            click.echo(f"\n{component_type.capitalize()}:")
            for name in components[component_type]:
                click.echo(f"  • {name}")
        else:
            click.echo(f"Unknown component type: {component_type}", err=True)
        return

    click.echo("\n📦 Registered Components:")
    for comp_type, names in components.items():
        if names:
            click.echo(f"\n{comp_type.capitalize()}:")
            for name in names:
                click.echo(f"  • {name}")
    click.echo()


@component.command("load")
@click.argument("source")
@click.option("--name", "-n", help="Custom name for component")
def load_component_cli(source: str, name: str | None) -> None:
    """Load a component from various sources.

    Examples:
        # From module
        uniflow component load my_package.components

        # From file
        uniflow component load /path/to/component.py:MyOrchestrator

        # From ZenML
        uniflow component load zenml:zenml.orchestrators.kubernetes.KubernetesOrchestrator
    """
    from uniflow.stacks.plugins import load_component

    try:
        load_component(source, name)
        click.echo(f"✅ Loaded component from: {source}")

        # Show what was loaded
        from uniflow.stacks.plugins import get_component_registry

        registry = get_component_registry()
        components = registry.list_all()

        click.echo("\nAvailable components:")
        for comp_type, names in components.items():
            for comp_name in names:
                if name and comp_name == name:
                    click.echo(f"  • {comp_name} [{comp_type}] ⭐ NEW")

    except Exception as e:
        click.echo(f"❌ Error loading component: {e}", err=True)
        sys.exit(1)


@cli.group()
def stack() -> None:
    """Manage infrastructure stacks."""
    pass


@stack.command("list")
@click.option("--config", "-c", help="Path to uniflow.yaml")
def list_stacks(config: str | None) -> None:
    """List all configured stacks."""
    from uniflow.utils.stack_config import load_config

    loader = load_config(config)
    stacks = loader.list_stacks()

    if not stacks:
        click.echo("No stacks configured. Create a uniflow.yaml file.")
        return

    default = loader.get_default_stack()

    click.echo("\nConfigured stacks:")
    for stack_name in stacks:
        marker = " (default)" if stack_name == default else ""
        config_data = loader.get_stack_config(stack_name)
        stack_type = config_data.get("type", "unknown")
        click.echo(f"  • {stack_name}{marker} [{stack_type}]")
    click.echo()


@stack.command("show")
@click.argument("stack_name")
@click.option("--config", "-c", help="Path to uniflow.yaml")
def show_stack(stack_name: str, config: str | None) -> None:
    """Show detailed stack configuration."""
    from uniflow.utils.stack_config import load_config
    import yaml

    loader = load_config(config)
    stack_config = loader.get_stack_config(stack_name)

    if not stack_config:
        click.echo(f"Stack '{stack_name}' not found", err=True)
        sys.exit(1)

    click.echo(f"\nStack: {stack_name}")
    click.echo(yaml.dump(stack_config, default_flow_style=False))


@stack.command("set-default")
@click.argument("stack_name")
@click.option("--config", "-c", help="Path to uniflow.yaml")
def set_default_stack(stack_name: str, config: str | None) -> None:
    """Set the default stack."""
    from uniflow.stacks.registry import get_registry

    registry = get_registry()

    if stack_name not in registry.list_stacks():
        click.echo(f"Stack '{stack_name}' not found", err=True)
        sys.exit(1)

    registry.set_active_stack(stack_name)
    click.echo(f"Set '{stack_name}' as active stack")


@cli.command()
@click.argument("pipeline_file")
@click.option("--stack", "-s", help="Stack to use (from uniflow.yaml)")
@click.option("--resources", "-r", help="Resource configuration to use")
@click.option("--config", "-c", help="Path to uniflow.yaml")
@click.option("--context", "-ctx", multiple=True, help="Context variables (key=value)")
@click.option("--dry-run", is_flag=True, help="Show what would be executed without running")
def run(
    pipeline_file: str,
    stack: str | None,
    resources: str | None,
    config: str | None,
    context: tuple,
    dry_run: bool,
) -> None:
    """Run a pipeline with specified stack and resources.

    Examples:
        # Run with local stack
        uniflow run pipeline.py

        # Run on production stack
        uniflow run pipeline.py --stack production

        # Run with GPU resources
        uniflow run pipeline.py --stack production --resources gpu_training

        # Pass context variables
        uniflow run pipeline.py --context data_path=gs://bucket/data.csv
    """
    from uniflow.utils.stack_config import (
        load_config,
        create_stack_from_config,
        create_resource_config_from_dict,
        create_docker_config_from_dict,
    )
    import importlib.util

    # Load configuration
    loader = load_config(config)

    # Determine stack to use
    stack_name = stack or loader.get_default_stack() or "local"

    click.echo(f"🚀 Running pipeline: {pipeline_file}")
    click.echo(f"📦 Stack: {stack_name}")

    if resources:
        click.echo(f"💻 Resources: {resources}")

    # Get stack configuration
    stack_config = loader.get_stack_config(stack_name)
    if not stack_config:
        click.echo(f"Stack '{stack_name}' not found in configuration", err=True)
        sys.exit(1)

    # Create stack instance
    stack_instance = create_stack_from_config(stack_config, stack_name)

    # Get resource configuration
    resource_config = None
    if resources:
        resource_dict = loader.get_resource_config(resources)
        if resource_dict:
            resource_config = create_resource_config_from_dict(resource_dict)

    # Get Docker configuration
    docker_dict = loader.get_docker_config()
    docker_config = create_docker_config_from_dict(docker_dict)

    # Parse context variables
    context_dict = {}
    for ctx_item in context:
        if "=" in ctx_item:
            key, value = ctx_item.split("=", 1)
            context_dict[key] = value

    if dry_run:
        click.echo("\n🔍 Dry run - configuration:")
        click.echo(f"  Stack: {stack_instance}")
        click.echo(f"  Resources: {resource_config}")
        click.echo(f"  Docker: {docker_config}")
        click.echo(f"  Context: {context_dict}")
        return

    # Load and run pipeline
    click.echo("\n⚙️  Loading pipeline...")

    # Import the pipeline file
    spec = importlib.util.spec_from_file_location("pipeline_module", pipeline_file)
    if spec is None or spec.loader is None:
        click.echo(f"Could not load pipeline file: {pipeline_file}", err=True)
        sys.exit(1)

    module = importlib.util.module_from_spec(spec)
    sys.modules["pipeline_module"] = module
    spec.loader.exec_module(module)

    # Find pipeline instance
    pipeline = None
    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if hasattr(attr, "__class__") and attr.__class__.__name__ == "Pipeline":
            pipeline = attr
            break

    if pipeline is None:
        click.echo("No Pipeline instance found in file", err=True)
        sys.exit(1)

    # Override stack
    pipeline.stack = stack_instance

    click.echo("🏃 Running pipeline...\n")

    # Run pipeline
    result = pipeline.run(
        context=context_dict,
        resources=resource_config,
        docker_config=docker_config,
    )

    click.echo("\n✅ Pipeline completed successfully!")
    click.echo(f"Results: {result}")


@cli.command()
@click.option("--output", "-o", default="uniflow.yaml", help="Output file path")
def init(output: str) -> None:
    """Initialize a new UniFlow project with example configuration."""
    import shutil

    # Copy example config
    example_path = Path(__file__).parent.parent.parent / "uniflow.yaml.example"
    output_path = Path(output)

    if output_path.exists():
        click.confirm(f"{output} already exists. Overwrite?", abort=True)

    if example_path.exists():
        shutil.copy(example_path, output_path)
        click.echo(f"✅ Created {output}")
    else:
        # Create basic config
        basic_config = """# UniFlow Configuration

stacks:
  local:
    type: local
    artifact_store:
      path: .uniflow/artifacts
    metadata_store:
      path: .uniflow/metadata.db

default_stack: local

resources:
  default:
    cpu: "2"
    memory: "8Gi"

docker:
  base_image: "python:3.11-slim"
  use_poetry: true
"""
        with open(output_path, "w") as f:
            f.write(basic_config)

        click.echo(f"✅ Created {output}")

    click.echo("\nNext steps:")
    click.echo("  1. Edit uniflow.yaml to configure your stacks")
    click.echo("  2. Run: uniflow stack list")
    click.echo("  3. Run your pipeline: uniflow run pipeline.py")


@cli.group()
def plugin() -> None:
    """Manage plugins and integrations."""
    pass


@plugin.command("list")
@click.option("--installed", is_flag=True, help="Show only installed plugins")
def list_plugins(installed: bool) -> None:
    """List available and installed plugins."""
    from uniflow.stacks.plugins import get_component_registry

    registry = get_component_registry()
    plugins = registry.list_plugins()

    if not plugins:
        click.echo("No plugins found.")
        return

    click.echo("\n🔌 Plugins:")
    for p in plugins:
        status = "✅ Installed" if p.is_installed else "Available"
        click.echo(f"  • {p.name} ({p.version}) - {status}")
        if p.description:
            click.echo(f"    {p.description}")
    click.echo()


@plugin.command("search")
@click.argument("query", required=False)
@click.option("--source", "-s", type=click.Choice(["pypi", "zenml", "all"]), default="all")
def search_plugins(query: str | None, source: str) -> None:
    """Search for available plugins."""
    click.echo(f"Searching for plugins matching '{query or '*'}' from {source}...")

    # In a real implementation, this would query PyPI or a central registry
    # For now, we'll simulate discovery of common ZenML plugins

    common_plugins = [
        {"name": "zenml-kubernetes", "desc": "Kubernetes orchestrator for ZenML/UniFlow"},
        {"name": "zenml-mlflow", "desc": "MLflow integration for experiment tracking"},
        {"name": "zenml-aws", "desc": "AWS stack components (S3, ECR, SageMaker)"},
        {"name": "zenml-gcp", "desc": "Google Cloud stack components"},
        {"name": "zenml-azure", "desc": "Azure stack components"},
        {"name": "zenml-airflow", "desc": "Airflow orchestrator integration"},
    ]

    found = False
    for p in common_plugins:
        if not query or query.lower() in p["name"] or query.lower() in p["desc"].lower():
            click.echo(f"\n📦 {p['name']}")
            click.echo(f"   {p['desc']}")
            click.echo(f"   Install: uniflow plugin install {p['name']}")
            found = True

    if not found:
        click.echo("No plugins found matching your query.")


@plugin.command("install")
@click.argument("plugin_name")
def install_plugin(plugin_name: str) -> None:
    """Install a plugin."""
    from uniflow.stacks.plugins import get_component_registry

    registry = get_component_registry()

    try:
        from rich.console import Console

        console = Console()

        with console.status(f"[bold green]Installing {plugin_name}..."):
            if registry.install_plugin(plugin_name):
                console.print(f"[bold green]✅ Successfully installed {plugin_name}![/bold green]")
            else:
                console.print(f"[bold red]❌ Failed to install {plugin_name}[/bold red]")

    except ImportError:
        click.echo(f"Installing {plugin_name}...")
        if registry.install_plugin(plugin_name):
            click.echo(f"✅ Successfully installed {plugin_name}!")
        else:
            click.echo(f"❌ Failed to install {plugin_name}")


@plugin.command("info")
@click.argument("plugin_name")
def plugin_info(plugin_name: str) -> None:
    """Get detailed info about a plugin."""
    # Simulated info
    info = {
        "name": plugin_name,
        "version": "1.0.0",
        "author": "UniFlow Team",
        "description": "A powerful plugin for UniFlow.",
        "components": ["Orchestrator", "ArtifactStore"],
        "dependencies": ["zenml>=0.40.0", "boto3"],
    }

    try:
        from rich.console import Console
        from rich.markdown import Markdown
        from rich.panel import Panel

        console = Console()

        content = f"""
# {info['name']} (v{info['version']})

{info['description']}

**Author:** {info['author']}

## Components
{chr(10).join(f'- {c}' for c in info['components'])}

## Dependencies
{chr(10).join(f'- {d}' for d in info['dependencies'])}
"""
        console.print(Panel(Markdown(content), title="Plugin Info", expand=False))

    except ImportError:
        click.echo(f"Plugin: {info['name']}")
        click.echo(f"Version: {info['version']}")
        click.echo(f"Description: {info['description']}")


@plugin.command("import-zenml-stack")
@click.argument("stack_name")
@click.option("--output", "-o", default="uniflow.yaml", help="Output file path")
def import_zenml_stack(stack_name: str, output: str) -> None:
    """Import an existing ZenML stack."""
    from uniflow.stacks.migration import StackMigrator

    migrator = StackMigrator()

    try:
        # Try to use rich if available
        try:
            from rich.console import Console
            from rich.panel import Panel

            console = Console()
            use_rich = True
        except ImportError:
            use_rich = False

        if use_rich:
            console.print(f"🔍 Analyzing ZenML stack [bold cyan]'{stack_name}'[/bold cyan]...")
        else:
            click.echo(f"🔍 Analyzing ZenML stack '{stack_name}'...")

        migration_data = migrator.migrate_zenml_stack(stack_name)

        msg = f"✅ Found stack '{stack_name}' with {len(migration_data['plugins'])} components."
        if use_rich:
            console.print(f"[bold green]{msg}[/bold green]")
            console.print("\n[bold]Plugins to configure:[/bold]")
            for p in migration_data["plugins"]:
                console.print(f"  • [cyan]{p['name']}[/cyan] ([dim]{p['source']}[/dim])")
        else:
            click.echo(msg)
            click.echo("\nPlugins to configure:")
            for p in migration_data["plugins"]:
                click.echo(f"  • {p['name']} ({p['source']})")

        if click.confirm(f"\nGenerate configuration in {output}?", default=True):
            yaml_content = migrator.generate_yaml(migration_data)

            # Append or write new
            mode = "a" if Path(output).exists() else "w"
            with open(output, mode) as f:
                if mode == "a":
                    f.write("\n" + yaml_content)
                else:
                    f.write(yaml_content)

            if use_rich:
                console.print(
                    Panel(
                        f"✅ Successfully imported stack to [bold]{output}[/bold]\n\nYou can now use it with: [green]uniflow run --stack {stack_name}[/green]",
                        title="Success",
                        style="green",
                    ),
                )
            else:
                click.echo(f"✅ Successfully imported stack to {output}")
                click.echo(f"You can now use it with: uniflow run --stack {stack_name}")

    except ImportError:
        click.echo("❌ ZenML is not installed. Install it with: pip install zenml", err=True)
    except ValueError as e:
        click.echo(f"❌ {e}", err=True)
    except Exception as e:
        click.echo(f"❌ Migration failed: {e}", err=True)


if __name__ == "__main__":
    cli()
