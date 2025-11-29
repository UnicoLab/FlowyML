"""Main CLI entry point for flowyml."""

import click
from pathlib import Path
from flowyml.utils.config import get_config


@click.group()
@click.version_option(version="0.1.0", prog_name="flowyml")
def cli() -> None:
    """Flowyml - Next-Generation ML Pipeline Framework.

    A developer-first ML pipeline orchestration framework that makes
    ML pipelines feel effortless while providing production-grade capabilities.
    """
    pass


@cli.command()
@click.option("--name", prompt="Project name", help="Name of the project")
@click.option(
    "--template",
    default="basic",
    type=click.Choice(["basic", "pytorch", "tensorflow", "sklearn"]),
    help="Project template",
)
@click.option("--dir", "directory", default=".", help="Directory to create project in")
def init(name: str, template: str, directory: str) -> None:
    """Initialize a new flowyml project."""
    from flowyml.cli.init import init_project

    project_dir = Path(directory) / name
    click.echo(f"Initializing flowyml project '{name}' with template '{template}'...")

    try:
        init_project(name, template, project_dir)
        click.echo(f"✓ Project '{name}' created successfully at {project_dir}")
        click.echo("\nNext steps:")
        click.echo(f"  cd {name}")
        click.echo("  flowyml run training_pipeline")
    except Exception as e:
        click.echo(f"✗ Error creating project: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.argument("pipeline_name")
@click.option("--stack", default="local", help="Stack to use for execution")
@click.option("--context", "-c", multiple=True, help="Context parameters (key=value)")
@click.option("--debug", is_flag=True, help="Enable debug mode")
def run(pipeline_name: str, stack: str, context: tuple, debug: bool) -> None:
    """Run a pipeline."""
    from flowyml.cli.run import run_pipeline

    # Parse context parameters
    ctx_params = {}
    for param in context:
        key, value = param.split("=", 1)
        ctx_params[key] = value

    click.echo(f"Running pipeline '{pipeline_name}' on stack '{stack}'...")

    try:
        result = run_pipeline(pipeline_name, stack, ctx_params, debug)
        click.echo("✓ Pipeline completed successfully")
        click.echo(f"  Run ID: {result.get('run_id', 'N/A')}")
        click.echo(f"  Duration: {result.get('duration', 'N/A')}")
    except Exception as e:
        click.echo(f"✗ Pipeline failed: {e}", err=True)
        raise click.Abort()


@cli.group()
def ui() -> None:
    """UI server commands."""
    pass


@ui.command()
@click.option("--host", default="localhost", help="Host to bind to")
@click.option("--port", default=8080, help="Port to bind to")
@click.option("--dev", is_flag=True, help="Run in development mode")
@click.option("--open-browser", "-o", is_flag=True, help="Open browser automatically")
def start(host: str, port: int, dev: bool, open_browser: bool) -> None:
    """Start the flowyml UI server."""
    from flowyml.ui.utils import is_ui_running

    # Check if already running
    if is_ui_running(host, port):
        click.echo(f"ℹ️  UI server is already running at http://{host}:{port}")
        if open_browser:
            import webbrowser

            webbrowser.open(f"http://{host}:{port}")
        return

    click.echo(f"🚀 Starting flowyml UI on http://{host}:{port}...")
    if dev:
        click.echo("   Development mode: Auto-reload enabled")

    try:
        from flowyml.cli.ui import start_ui_server

        # Open browser if requested
        if open_browser:
            import webbrowser
            import threading

            def open_browser_delayed() -> None:
                import time

                time.sleep(1.5)  # Wait for server to start
                webbrowser.open(f"http://{host}:{port}")

            threading.Thread(target=open_browser_delayed, daemon=True).start()

        start_ui_server(host, port, dev)
    except ImportError:
        click.echo("✗ UI server not available. Install with: pip install flowyml[ui]", err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(f"✗ Error starting UI: {e}", err=True)
        raise click.Abort()


@ui.command()
def stop() -> None:
    """Stop the flowyml UI server."""
    click.echo("Stopping flowyml UI server...")
    click.echo("ℹ️  To stop the UI server:")
    click.echo("   - If running in foreground: Press Ctrl+C")
    click.echo("   - If running in background: pkill -f 'flowyml ui start'")


@ui.command()
@click.option("--host", default="localhost", help="Host to check")
@click.option("--port", default=8080, help="Port to check")
def status(host: str, port: int) -> None:
    """Check if the UI server is running."""
    from flowyml.ui.utils import is_ui_running, get_ui_url

    if is_ui_running(host, port):
        url = get_ui_url(host, port)
        click.echo(f"✅ UI server is running at {url}")
        click.echo("   Status: Healthy")
        click.echo(f"   Health endpoint: {url}/api/health")
    else:
        click.echo(f"❌ UI server is not running on {host}:{port}")
        click.echo(f"   Start with: flowyml ui start --host {host} --port {port}")


@cli.group()
def experiment() -> None:
    """Experiment tracking commands."""
    pass


@experiment.command("list")
@click.option("--limit", default=10, help="Number of experiments to show")
@click.option("--pipeline", help="Filter by pipeline name")
def list_experiments(limit: int, pipeline: str) -> None:
    """List experiments."""
    from flowyml.cli.experiment import list_experiments_cmd

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
@click.argument("run_ids", nargs=-1, required=True)
def compare(run_ids: tuple) -> None:
    """Compare multiple experiment runs."""
    from flowyml.cli.experiment import compare_runs

    click.echo(f"Comparing {len(run_ids)} runs...")

    try:
        comparison = compare_runs(list(run_ids))
        click.echo("\nComparison Results:")
        click.echo(comparison)
    except Exception as e:
        click.echo(f"✗ Error comparing runs: {e}", err=True)


@cli.group()
def stack() -> None:
    """Stack management commands."""
    pass


@stack.command("list")
def list_stacks() -> None:
    """List available stacks."""
    click.echo("Available stacks:\n")
    click.echo("  local (default) - Local execution")
    click.echo("  aws             - AWS (SageMaker, S3, Step Functions)")
    click.echo("  gcp             - Google Cloud (Vertex AI, GCS)")
    click.echo("  azure           - Azure (ML, Blob Storage)")


@stack.command()
@click.argument("stack_name")
def switch(stack_name: str) -> None:
    """Switch active stack."""
    config = get_config()
    config.default_stack = stack_name
    config.save()
    click.echo(f"✓ Switched to stack '{stack_name}'")


@cli.group()
def cache() -> None:
    """Cache management commands."""
    pass


@cache.command()
def stats() -> None:
    """Show cache statistics."""
    from flowyml.core.cache import CacheStore

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
@click.confirmation_option(prompt="Are you sure you want to clear the cache?")
def clear() -> None:
    """Clear all cache."""
    from flowyml.core.cache import CacheStore

    try:
        cache = CacheStore()
        cache.clear()
        click.echo("✓ Cache cleared successfully")
    except Exception as e:
        click.echo(f"✗ Error clearing cache: {e}", err=True)


@cli.group()
def config() -> None:
    """Configuration management commands."""
    pass


@config.command("show")
def show_config() -> None:
    """Show current configuration."""
    cfg = get_config()

    click.echo("flowyml Configuration:\n")
    click.echo(f"  flowyml Home: {cfg.flowyml_home}")
    click.echo(f"  Artifacts Dir: {cfg.artifacts_dir}")
    click.echo(f"  Metadata DB: {cfg.metadata_db}")
    click.echo(f"  Default Stack: {cfg.default_stack}")
    click.echo(f"  Execution Mode: {cfg.execution_mode}")
    if cfg.execution_mode == "remote":
        click.echo(f"  Remote Server URL: {cfg.remote_server_url}")
        click.echo(f"  Remote UI URL: {cfg.remote_ui_url}")
    click.echo(f"  Enable Caching: {cfg.enable_caching}")
    click.echo(f"  Log Level: {cfg.log_level}")
    click.echo(f"  UI Port: {cfg.ui_port}")
    click.echo(f"  Debug Mode: {cfg.debug_mode}")


@config.command("set-mode")
@click.argument("mode", type=click.Choice(["local", "remote"]))
def set_mode(mode: str) -> None:
    """Set execution mode (local or remote)."""
    cfg = get_config()
    cfg.execution_mode = mode
    cfg.save()
    click.echo(f"✓ Execution mode set to '{mode}'")


@config.command("set-url")
@click.option("--server", help="Remote server URL")
@click.option("--ui", help="Remote UI URL")
def set_url(server: str, ui: str) -> None:
    """Set remote server and UI URLs."""
    cfg = get_config()
    if server:
        cfg.remote_server_url = server
        click.echo(f"✓ Remote server URL set to '{server}'")
    if ui:
        cfg.remote_ui_url = ui
        click.echo(f"✓ Remote UI URL set to '{ui}'")
    cfg.save()


@cli.command()
@click.argument("run_id")
@click.option("--step", help="Filter by step name")
@click.option("--tail", default=100, help="Number of lines to show")
def logs(run_id: str, step: str, tail: int) -> None:
    """View logs for a pipeline run."""
    click.echo(f"Logs for run '{run_id}':")

    if step:
        click.echo(f"  Step: {step}")

    click.echo("\nLog entries:")
    click.echo(f"  (Showing last {tail} lines)")
    click.echo("  [Log output would appear here]")


if __name__ == "__main__":
    cli()
