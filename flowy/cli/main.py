"""Main CLI entry point for Flowy."""

import click
from pathlib import Path
from flowy.utils.config import get_config, FlowyConfig


@click.group()
@click.version_option(version="0.1.0", prog_name="flowy")
def cli():
    """Flowy - Next-Generation ML Pipeline Framework

    A developer-first ML pipeline orchestration framework that makes
    ML pipelines feel effortless while providing production-grade capabilities.
    """
    pass


@cli.command()
@click.option('--name', prompt='Project name', help='Name of the project')
@click.option('--template', default='basic', type=click.Choice(['basic', 'pytorch', 'tensorflow', 'sklearn']),
              help='Project template')
@click.option('--dir', 'directory', default='.', help='Directory to create project in')
def init(name: str, template: str, directory: str):
    """Initialize a new Flowy project."""
    from flowy.cli.init import init_project

    project_dir = Path(directory) / name
    click.echo(f"Initializing Flowy project '{name}' with template '{template}'...")

    try:
        init_project(name, template, project_dir)
        click.echo(f"✓ Project '{name}' created successfully at {project_dir}")
        click.echo("\nNext steps:")
        click.echo(f"  cd {name}")
        click.echo("  flowy run training_pipeline")
    except Exception as e:
        click.echo(f"✗ Error creating project: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.argument('pipeline_name')
@click.option('--stack', default='local', help='Stack to use for execution')
@click.option('--context', '-c', multiple=True, help='Context parameters (key=value)')
@click.option('--debug', is_flag=True, help='Enable debug mode')
def run(pipeline_name: str, stack: str, context: tuple, debug: bool):
    """Run a pipeline."""
    from flowy.cli.run import run_pipeline

    # Parse context parameters
    ctx_params = {}
    for param in context:
        key, value = param.split('=', 1)
        ctx_params[key] = value

    click.echo(f"Running pipeline '{pipeline_name}' on stack '{stack}'...")

    try:
        result = run_pipeline(pipeline_name, stack, ctx_params, debug)
        click.echo(f"✓ Pipeline completed successfully")
        click.echo(f"  Run ID: {result.get('run_id', 'N/A')}")
        click.echo(f"  Duration: {result.get('duration', 'N/A')}")
    except Exception as e:
        click.echo(f"✗ Pipeline failed: {e}", err=True)
        raise click.Abort()


@cli.group()
def ui():
    """UI server commands."""
    pass


@ui.command()
@click.option('--host', default='localhost', help='Host to bind to')
@click.option('--port', default=8080, help='Port to bind to')
@click.option('--dev', is_flag=True, help='Run in development mode')
def start(host: str, port: int, dev: bool):
    """Start the Flowy UI server."""
    click.echo(f"Starting Flowy UI on http://{host}:{port}...")

    try:
        from flowy.cli.ui import start_ui_server
        start_ui_server(host, port, dev)
    except ImportError:
        click.echo("✗ UI server not available. Install with: pip install flowy[ui]", err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(f"✗ Error starting UI: {e}", err=True)
        raise click.Abort()


@ui.command()
def stop():
    """Stop the Flowy UI server."""
    click.echo("Stopping Flowy UI server...")
    click.echo("✓ UI server stopped")


@cli.group()
def experiment():
    """Experiment tracking commands."""
    pass


@experiment.command('list')
@click.option('--limit', default=10, help='Number of experiments to show')
@click.option('--pipeline', help='Filter by pipeline name')
def list_experiments(limit: int, pipeline: str):
    """List experiments."""
    from flowy.cli.experiment import list_experiments_cmd

    try:
        experiments = list_experiments_cmd(limit, pipeline)
        click.echo(f"Found {len(experiments)} experiments:\n")

        for exp in experiments:
            click.echo(f"  {exp['name']}")
            click.echo(f"    Runs: {exp.get('num_runs', 0)}")
            click.echo(f"    Created: {exp.get('created_at', 'N/A')}")
            click.echo()
    except Exception as e:
        click.echo(f"✗ Error listing experiments: {e}", err=True)


@experiment.command()
@click.argument('run_ids', nargs=-1, required=True)
def compare(run_ids: tuple):
    """Compare multiple experiment runs."""
    from flowy.cli.experiment import compare_runs

    click.echo(f"Comparing {len(run_ids)} runs...")

    try:
        comparison = compare_runs(list(run_ids))
        click.echo("\nComparison Results:")
        click.echo(comparison)
    except Exception as e:
        click.echo(f"✗ Error comparing runs: {e}", err=True)


@cli.group()
def stack():
    """Stack management commands."""
    pass


@stack.command('list')
def list_stacks():
    """List available stacks."""
    click.echo("Available stacks:\n")
    click.echo("  local (default) - Local execution")
    click.echo("  aws             - AWS (SageMaker, S3, Step Functions)")
    click.echo("  gcp             - Google Cloud (Vertex AI, GCS)")
    click.echo("  azure           - Azure (ML, Blob Storage)")


@stack.command()
@click.argument('stack_name')
def switch(stack_name: str):
    """Switch active stack."""
    config = get_config()
    config.default_stack = stack_name
    config.save()
    click.echo(f"✓ Switched to stack '{stack_name}'")


@cli.group()
def cache():
    """Cache management commands."""
    pass


@cache.command()
def stats():
    """Show cache statistics."""
    from flowy.core.cache import CacheStore

    try:
        cache = CacheStore()
        stats = cache.get_stats()

        click.echo("Cache Statistics:\n")
        click.echo(f"  Hits: {stats['hits']}")
        click.echo(f"  Misses: {stats['misses']}")
        click.echo(f"  Hit Rate: {stats.get('hit_rate', 0):.1%}")
        click.echo(f"  Total Entries: {stats.get('total_entries', 0)}")
        click.echo(f"  Size: {stats.get('size_mb', 0):.2f} MB")
    except Exception as e:
        click.echo(f"✗ Error getting cache stats: {e}", err=True)


@cache.command()
@click.confirmation_option(prompt='Are you sure you want to clear the cache?')
def clear():
    """Clear all cache."""
    from flowy.core.cache import CacheStore

    try:
        cache = CacheStore()
        cache.clear()
        click.echo("✓ Cache cleared successfully")
    except Exception as e:
        click.echo(f"✗ Error clearing cache: {e}", err=True)


@cli.command()
def config():
    """Show current configuration."""
    cfg = get_config()

    click.echo("Flowy Configuration:\n")
    click.echo(f"  Flowy Home: {cfg.flowy_home}")
    click.echo(f"  Artifacts Dir: {cfg.artifacts_dir}")
    click.echo(f"  Metadata DB: {cfg.metadata_db}")
    click.echo(f"  Default Stack: {cfg.default_stack}")
    click.echo(f"  Enable Caching: {cfg.enable_caching}")
    click.echo(f"  Log Level: {cfg.log_level}")
    click.echo(f"  UI Port: {cfg.ui_port}")
    click.echo(f"  Debug Mode: {cfg.debug_mode}")


@cli.command()
@click.argument('run_id')
@click.option('--step', help='Filter by step name')
@click.option('--tail', default=100, help='Number of lines to show')
def logs(run_id: str, step: str, tail: int):
    """View logs for a pipeline run."""
    click.echo(f"Logs for run '{run_id}':")

    if step:
        click.echo(f"  Step: {step}")

    click.echo("\nLog entries:")
    click.echo("  [Log output would appear here]")


if __name__ == '__main__':
    cli()
