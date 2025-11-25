"""
Enhanced CLI for UniFlow with stack management.

Allows running pipelines with different stacks from command line
without modifying pipeline code.
"""

import click
import sys
from pathlib import Path
from typing import Optional


@click.group()
@click.version_option()
def cli():
    """UniFlow - Unified ML Pipeline Framework"""
    pass


@cli.group()
def component():
    """Manage stack components and plugins"""
    pass


@component.command("list")
@click.option("--type", "-t", help="Filter by component type")
def list_components(type: Optional[str]):
    """List all registered components"""
    from uniflow.stacks.plugins import get_component_registry
    
    registry = get_component_registry()
    components = registry.list_all()
    
    if type:
        if type in components:
            click.echo(f"\n{type.capitalize()}:")
            for name in components[type]:
                click.echo(f"  • {name}")
        else:
            click.echo(f"Unknown component type: {type}", err=True)
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
def load_component_cli(source: str, name: Optional[str]):
    """
    Load a component from various sources.
    
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
def stack():
    """Manage infrastructure stacks"""
    pass


@stack.command("list")
@click.option("--config", "-c", help="Path to uniflow.yaml")
def list_stacks(config: Optional[str]):
    """List all configured stacks"""
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
        stack_type = config_data.get('type', 'unknown')
        click.echo(f"  • {stack_name}{marker} [{stack_type}]")
    click.echo()


@stack.command("show")
@click.argument("stack_name")
@click.option("--config", "-c", help="Path to uniflow.yaml")
def show_stack(stack_name: str, config: Optional[str]):
    """Show detailed stack configuration"""
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
def set_default_stack(stack_name: str, config: Optional[str]):
    """Set the default stack"""
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
    stack: Optional[str],
    resources: Optional[str],
    config: Optional[str],
    context: tuple,
    dry_run: bool
):
    """
    Run a pipeline with specified stack and resources.
    
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
        if '=' in ctx_item:
            key, value = ctx_item.split('=', 1)
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
        if hasattr(attr, '__class__') and attr.__class__.__name__ == 'Pipeline':
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
    
    click.echo(f"\n✅ Pipeline completed successfully!")
    click.echo(f"Results: {result}")


@cli.command()
@click.option("--output", "-o", default="uniflow.yaml", help="Output file path")
def init(output: str):
    """Initialize a new UniFlow project with example configuration"""
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
        with open(output_path, 'w') as f:
            f.write(basic_config)
        
        click.echo(f"✅ Created {output}")
    
    click.echo("\nNext steps:")
    click.echo("  1. Edit uniflow.yaml to configure your stacks")
    click.echo("  2. Run: uniflow stack list")
    click.echo("  3. Run your pipeline: uniflow run pipeline.py")


if __name__ == "__main__":
    cli()
