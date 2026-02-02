"""Main CLI entry point for flowyml."""

import click
from pathlib import Path
from flowyml.utils.config import get_config

# Import model commands early to avoid E402 error
from flowyml.cli.models import (
    list_models,
    promote_model,
    show_model,
    delete_model,
)


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
@click.option("--retry", type=int, help="Number of retries for the pipeline")
def run(pipeline_name: str, stack: str, context: tuple, debug: bool, retry: int | None) -> None:
    """Run a pipeline."""
    from flowyml.cli.run import run_pipeline
    from flowyml.core.retry_policy import OrchestratorRetryPolicy

    # Parse context parameters
    ctx_params = {}
    for param in context:
        key, value = param.split("=", 1)
        ctx_params[key] = value

    click.echo(f"Running pipeline '{pipeline_name}' on stack '{stack}'...")

    kwargs = {}
    if retry:
        kwargs["retry_policy"] = OrchestratorRetryPolicy(max_attempts=retry)
        click.echo(f"  Retry policy enabled: max_attempts={retry}")

    try:
        result = run_pipeline(pipeline_name, stack, ctx_params, debug, **kwargs)
        click.echo("✓ Pipeline completed successfully")
        click.echo(f"  Run ID: {result.get('run_id', 'N/A')}")
        click.echo(f"  Duration: {result.get('duration', 'N/A')}")
    except Exception as e:
        click.echo(f"✗ Pipeline failed: {e}", err=True)
        raise click.Abort()


@cli.group()
def schedule() -> None:
    """Schedule management commands."""
    pass


@schedule.command("create")
@click.argument("pipeline_name")
@click.argument("schedule_type", type=click.Choice(["cron", "interval", "daily", "hourly"]))
@click.argument("value")
@click.option("--stack", default="local", help="Stack to use for execution")
def create_schedule(pipeline_name: str, schedule_type: str, value: str, stack: str) -> None:
    """Create a new schedule for a pipeline.

    VALUE format depends on SCHEDULE_TYPE:
    - cron: "*/5 * * * *"
    - interval: seconds (e.g. 60)
    - daily: "HH:MM" (e.g. 14:30)
    - hourly: minute (e.g. 30)
    """
    from flowyml.core.scheduler import PipelineScheduler
    from flowyml.cli.run import run_pipeline

    # We need a callable for the scheduler.
    # Since CLI is stateless, we wrap the run_pipeline command.
    # Note: In a real distributed system, this would submit to a scheduler service.
    # Here we are just registering it in the local scheduler DB.

    # For now, we'll just use the scheduler API to register the definition
    scheduler = PipelineScheduler()

    # Define a wrapper that runs the pipeline via CLI logic
    def job_func():
        run_pipeline(pipeline_name, stack, {}, False)

    try:
        if schedule_type == "cron":
            scheduler.schedule_cron(pipeline_name, job_func, value)
        elif schedule_type == "interval":
            scheduler.schedule_interval(pipeline_name, job_func, seconds=int(value))
        elif schedule_type == "daily":
            if ":" in value:
                h, m = map(int, value.split(":"))
                scheduler.schedule_daily(pipeline_name, job_func, hour=h, minute=m)
            else:
                raise ValueError("Daily value must be HH:MM")
        elif schedule_type == "hourly":
            scheduler.schedule_hourly(pipeline_name, job_func, minute=int(value))

        click.echo(f"✓ Schedule created for '{pipeline_name}' ({schedule_type}={value})")
        click.echo("  Note: Ensure the scheduler service is running to execute this schedule.")
    except Exception as e:
        click.echo(f"✗ Error creating schedule: {e}", err=True)


@schedule.command("list")
def list_schedules() -> None:
    """List all active schedules."""
    from flowyml.core.scheduler import PipelineScheduler

    scheduler = PipelineScheduler()
    jobs = scheduler.get_jobs()

    if not jobs:
        click.echo("No active schedules found.")
        return

    click.echo(f"Found {len(jobs)} schedules:\n")
    for job in jobs:
        click.echo(f"  {job.id} - {job.name}")
        click.echo(f"    Next run: {job.next_run_time}")
        click.echo()


@schedule.command("start")
def start_scheduler() -> None:
    """Start the scheduler service (blocking)."""
    from flowyml.core.scheduler import PipelineScheduler
    import time

    click.echo("🚀 Starting Scheduler Service...")
    scheduler = PipelineScheduler()

    try:
        # In a real app, this would load definitions from DB and register them
        # For now, it just runs the scheduler loop for existing in-memory jobs
        # (which might be empty if we restarted).
        # To make this persistent, we'd need to serialize job definitions to DB.
        # The current Scheduler implementation supports SQLite persistence for job state,
        # but we need to re-register jobs on startup.

        click.echo("  Scheduler running. Press Ctrl+C to stop.")
        while True:
            scheduler.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        click.echo("\n🛑 Scheduler stopped.")


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
def models() -> None:
    """Model registry management commands."""
    pass


# Register model commands
models.add_command(list_models)
models.add_command(promote_model)
models.add_command(show_model)
models.add_command(delete_model)


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

    cfg.save()


@config.command("set-token")
@click.argument("token")
def set_token(token: str) -> None:
    """Set the API token for remote authentication."""
    cfg = get_config()
    cfg.api_token = token
    cfg.save()
    click.echo(f"✓ API token set (length: {len(token)})")


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


# ============================================================================
# Quick Commands: flowyml go / stop / status
# ============================================================================


@cli.command()
@click.option("--host", default="localhost", help="Host to bind to")
@click.option("--port", default=8080, type=int, help="Port to bind to")
@click.option("--open-browser", "-o", is_flag=True, help="Open browser automatically")
def go(host: str, port: int, open_browser: bool) -> None:
    r"""🚀 Start flowyml - Initialize UI dashboard and show welcome message.

    This is the quickest way to get started with flowyml. It starts the UI
    dashboard server in the background and displays the URL to access it.

    \b
    Examples:
        flowyml go              # Start on default port 8080
        flowyml go -o           # Start and open browser
        flowyml go --port 9000  # Start on custom port
    """
    import subprocess
    import sys
    import time
    from flowyml.ui.utils import is_ui_running

    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.text import Text
        from rich import box

        console = Console()
        rich_available = True
    except ImportError:
        rich_available = False

    url = f"http://{host}:{port}"

    # Check if already running
    if is_ui_running(host, port):
        if rich_available:
            panel_content = Text()
            panel_content.append("✅ ", style="green")
            panel_content.append("flowyml is already running!\n\n", style="bold green")
            panel_content.append("🌐 Dashboard: ", style="bold")
            panel_content.append(url, style="cyan underline link " + url)
            panel_content.append("\n\n", style="")
            panel_content.append("Run ", style="dim")
            panel_content.append("flowyml stop", style="bold yellow")
            panel_content.append(" to stop the server.", style="dim")

            console.print(
                Panel(
                    panel_content,
                    title="[bold cyan]🌊 flowyml[/bold cyan]",
                    border_style="cyan",
                    box=box.DOUBLE,
                ),
            )
        else:
            click.echo("✅ flowyml is already running!")
            click.echo(f"🌐 Dashboard: {url}")
            click.echo("\nRun 'flowyml stop' to stop the server.")

        if open_browser:
            import webbrowser

            webbrowser.open(url)
        return

    # Start the UI server as a background subprocess
    if rich_available:
        console.print("[bold cyan]🌊 flowyml[/bold cyan] - Starting up...\n")
    else:
        click.echo("🌊 flowyml - Starting up...")

    try:
        # Start uvicorn as a background process
        # Using subprocess with nohup-like behavior
        cmd = [
            sys.executable,
            "-m",
            "uvicorn",
            "flowyml.ui.backend.main:app",
            "--host",
            host,
            "--port",
            str(port),
            "--log-level",
            "warning",
        ]

        # Start as detached background process
        if sys.platform == "win32":
            # Windows: use CREATE_NEW_PROCESS_GROUP
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
            )
        else:
            # Unix: use start_new_session
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )

        # Wait for server to start (up to 8 seconds)
        started = False
        for _ in range(80):
            time.sleep(0.1)
            if is_ui_running(host, port):
                started = True
                break

        if started:
            # Save PID for later stop command
            pid_file = Path.home() / ".flowyml" / "ui_server.pid"
            pid_file.parent.mkdir(parents=True, exist_ok=True)
            pid_file.write_text(f"{process.pid}\n{host}\n{port}")

            if rich_available:
                panel_content = Text()
                panel_content.append("✅ ", style="green")
                panel_content.append("flowyml is ready!\n\n", style="bold green")
                panel_content.append("🌐 Dashboard: ", style="bold")
                panel_content.append(url, style="cyan underline link " + url)
                panel_content.append("\n\n", style="")
                panel_content.append("📊 View pipelines: ", style="")
                panel_content.append(f"{url}/pipelines", style="cyan")
                panel_content.append("\n", style="")
                panel_content.append("📜 View runs: ", style="")
                panel_content.append(f"{url}/runs", style="cyan")
                panel_content.append("\n\n", style="")
                panel_content.append("Run ", style="dim")
                panel_content.append("flowyml stop", style="bold yellow")
                panel_content.append(" to stop the server.", style="dim")

                console.print(
                    Panel(
                        panel_content,
                        title="[bold cyan]🌊 flowyml[/bold cyan]",
                        border_style="green",
                        box=box.DOUBLE,
                    ),
                )

                console.print()
                console.print("[dim]Tip: The dashboard runs in the background. Your pipelines will[/dim]")
                console.print("[dim]automatically show a clickable URL when they run.[/dim]")
            else:
                click.echo("✅ flowyml is ready!")
                click.echo(f"🌐 Dashboard: {url}")
                click.echo(f"📊 View pipelines: {url}/pipelines")
                click.echo(f"📜 View runs: {url}/runs")
                click.echo("\nRun 'flowyml stop' to stop the server.")
                click.echo("\nTip: The dashboard runs in the background. Your pipelines will")
                click.echo("automatically show a clickable URL when they run.")

            if open_browser:
                import webbrowser

                webbrowser.open(url)
        else:
            # Server didn't start, kill the process
            process.terminate()
            raise RuntimeError("Server failed to start within timeout")

    except Exception as e:
        if rich_available:
            panel_content = Text()
            panel_content.append("❌ ", style="red")
            panel_content.append("Failed to start flowyml UI server.\n\n", style="bold red")
            panel_content.append(f"Error: {str(e)[:100]}\n\n", style="dim red")
            panel_content.append("Possible issues:\n", style="")
            panel_content.append(f"  • Port {port} might be in use\n", style="dim")
            panel_content.append("  • Missing dependencies (uvicorn, fastapi)\n", style="dim")
            panel_content.append("\n", style="")
            panel_content.append("Try:\n", style="")
            panel_content.append(f"  flowyml go --port {port + 1}", style="bold yellow")
            panel_content.append("  (use different port)\n", style="dim")
            panel_content.append("  flowyml ui start", style="bold yellow")
            panel_content.append("  (for verbose output)", style="dim")

            console.print(
                Panel(
                    panel_content,
                    title="[bold red]Error[/bold red]",
                    border_style="red",
                    box=box.ROUNDED,
                ),
            )
        else:
            click.echo(f"❌ Failed to start flowyml UI server: {e}")
            click.echo("Possible issues:")
            click.echo(f"  • Port {port} might be in use")
            click.echo("  • Missing dependencies (uvicorn, fastapi)")
            click.echo(f"\nTry: flowyml go --port {port + 1}")
            click.echo("Or run 'flowyml ui start' for verbose output.")


@cli.command("stop")
@click.option("--host", default="localhost", help="Host of the server")
@click.option("--port", default=8080, type=int, help="Port of the server")
def stop_server(host: str, port: int) -> None:
    r"""🛑 Stop flowyml - Shutdown the UI dashboard server.

    Stops the flowyml UI server if it's running.

    \b
    Examples:
        flowyml stop              # Stop server on default port
        flowyml stop --port 9000  # Stop server on custom port
    """
    import os
    import signal
    import time
    from flowyml.ui.utils import is_ui_running

    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.text import Text
        from rich import box

        console = Console()
        rich_available = True
    except ImportError:
        rich_available = False

    pid_file = Path.home() / ".flowyml" / "ui_server.pid"

    # First check if we have a PID file from 'flowyml go'
    if pid_file.exists():
        try:
            content = pid_file.read_text().strip().split("\n")
            pid = int(content[0])
            # Note: saved_host and saved_port are in the file but we use the CLI args
            # to allow stopping a server on a different port if needed

            # Try to kill the process
            try:
                os.kill(pid, signal.SIGTERM)
                time.sleep(0.5)

                # Clean up PID file
                pid_file.unlink(missing_ok=True)

                if rich_available:
                    console.print(f"[green]✅ flowyml server (PID {pid}) stopped successfully.[/green]")
                else:
                    click.echo(f"✅ flowyml server (PID {pid}) stopped successfully.")
                return
            except ProcessLookupError:
                # Process already dead, clean up PID file
                pid_file.unlink(missing_ok=True)
            except PermissionError:
                if rich_available:
                    console.print(f"[red]❌ Permission denied to stop process {pid}[/red]")
                else:
                    click.echo(f"❌ Permission denied to stop process {pid}")
                return
        except (ValueError, IndexError):
            # Invalid PID file, remove it
            pid_file.unlink(missing_ok=True)

    # Check if server is running
    if not is_ui_running(host, port):
        if rich_available:
            console.print(f"[yellow]ℹ️  No flowyml server running on {host}:{port}[/yellow]")
        else:
            click.echo(f"ℹ️  No flowyml server running on {host}:{port}")
        return

    # Server is running but we don't have a PID file - must be from 'flowyml ui start'
    if rich_available:
        panel_content = Text()
        panel_content.append("ℹ️  ", style="yellow")
        panel_content.append("Server running but not started with 'flowyml go'.\n\n", style="")
        panel_content.append("To stop it:\n", style="")
        panel_content.append("  • If running in foreground: ", style="dim")
        panel_content.append("Press Ctrl+C\n", style="bold")
        panel_content.append("  • Find and kill: ", style="dim")
        panel_content.append(f"pkill -f 'uvicorn.*:{port}'\n", style="bold")
        panel_content.append("  • Or find PID: ", style="dim")
        panel_content.append(f"lsof -i :{port}", style="bold")

        console.print(
            Panel(
                panel_content,
                title="[bold yellow]Manual Stop Required[/bold yellow]",
                border_style="yellow",
                box=box.ROUNDED,
            ),
        )
    else:
        click.echo("ℹ️  Server running but not started with 'flowyml go'.")
        click.echo("To stop it:")
        click.echo("  • If running in foreground: Press Ctrl+C")
        click.echo(f"  • Find and kill: pkill -f 'uvicorn.*:{port}'")
        click.echo(f"  • Or find PID: lsof -i :{port}")


@cli.command("status")
@click.option("--host", default="localhost", help="Host to check")
@click.option("--port", default=8080, type=int, help="Port to check")
def server_status(host: str, port: int) -> None:
    r"""📊 Check flowyml status - Show if the UI server is running.

    \b
    Examples:
        flowyml status              # Check default port
        flowyml status --port 9000  # Check custom port
    """
    from flowyml.ui.utils import is_ui_running

    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.text import Text
        from rich import box

        console = Console()
        rich_available = True
    except ImportError:
        rich_available = False

    if is_ui_running(host, port):
        url = f"http://{host}:{port}"
        if rich_available:
            panel_content = Text()
            panel_content.append("✅ ", style="green")
            panel_content.append("flowyml is running\n\n", style="bold green")
            panel_content.append("🌐 Dashboard: ", style="bold")
            panel_content.append(url, style="cyan underline link " + url)
            panel_content.append("\n", style="")
            panel_content.append("💚 Health: ", style="")
            panel_content.append(f"{url}/api/health", style="dim")

            console.print(
                Panel(
                    panel_content,
                    title="[bold cyan]🌊 flowyml Status[/bold cyan]",
                    border_style="green",
                    box=box.ROUNDED,
                ),
            )
        else:
            click.echo("✅ flowyml is running")
            click.echo(f"🌐 Dashboard: {url}")
            click.echo(f"💚 Health: {url}/api/health")
    else:
        if rich_available:
            panel_content = Text()
            panel_content.append("❌ ", style="red")
            panel_content.append(f"flowyml is not running on {host}:{port}\n\n", style="")
            panel_content.append("Start with: ", style="dim")
            panel_content.append("flowyml go", style="bold cyan")

            console.print(
                Panel(
                    panel_content,
                    title="[bold cyan]🌊 flowyml Status[/bold cyan]",
                    border_style="red",
                    box=box.ROUNDED,
                ),
            )
        else:
            click.echo(f"❌ flowyml is not running on {host}:{port}")
            click.echo("Start with: flowyml go")


# ============================================================================
# ZenML Integration Commands
# ============================================================================


@cli.group()
def zenml() -> None:
    """ZenML integration commands - Seamlessly use ZenML components in FlowyML.

    FlowyML can automatically discover and wrap ZenML integrations,
    making them available as first-class FlowyML stack components.
    """
    pass


@zenml.command("list")
@click.option("--installed", is_flag=True, help="Show only installed integrations")
def list_zenml_integrations(installed: bool) -> None:
    """List available ZenML integrations.

    Shows all ZenML integrations that can be used with FlowyML.
    Use --installed to see only the integrations you have installed.
    """
    from flowyml.stacks.plugins import get_component_registry

    registry = get_component_registry()

    if installed:
        integrations = registry.list_installed_zenml_integrations()
        click.echo("Installed ZenML integrations:\n")
    else:
        integrations = registry.list_zenml_integrations()
        click.echo("Available ZenML integrations:\n")

    if not integrations:
        click.echo("  No integrations found.")
        click.echo("\n  Make sure ZenML is installed: pip install zenml")
        return

    for name in sorted(integrations):
        click.echo(f"  • {name}")

    click.echo(f"\nTotal: {len(integrations)} integrations")

    if not installed:
        click.echo("\nTo install an integration:")
        click.echo("  flowyml zenml install <integration_name>")


@zenml.command("install")
@click.argument("integration_name")
def install_zenml_integration(integration_name: str) -> None:
    """Install a ZenML integration and its dependencies.

    This installs the ZenML integration package and all required
    dependencies, making it available for use in FlowyML pipelines.

    Examples:
        flowyml zenml install mlflow
        flowyml zenml install kubernetes
        flowyml zenml install aws
    """
    from flowyml.stacks.plugins import get_component_registry

    click.echo(f"Installing ZenML integration '{integration_name}'...")

    registry = get_component_registry()
    success = registry.install_zenml_integration(integration_name)

    if success:
        click.echo(f"✓ Successfully installed '{integration_name}'")
        click.echo("\nTo use this integration in FlowyML:")
        click.echo(f"  flowyml zenml import {integration_name}")
    else:
        click.echo(f"✗ Failed to install '{integration_name}'", err=True)
        click.echo("  Check that ZenML is installed and the integration name is correct.")


@zenml.command("import")
@click.argument("integration_name")
def import_zenml_integration(integration_name: str) -> None:
    """Import components from a ZenML integration.

    Discovers all flavors provided by a ZenML integration and registers
    them as FlowyML stack components, ready to use in your pipelines.

    Examples:
        flowyml zenml import mlflow
        flowyml zenml import kubernetes
    """
    from flowyml.stacks.plugins import get_component_registry

    click.echo(f"Importing ZenML integration '{integration_name}'...")

    registry = get_component_registry()
    components = registry.import_zenml_integration(integration_name)

    if components:
        click.echo(f"✓ Successfully imported {len(components)} components:\n")
        for comp in components:
            click.echo(f"  • {comp.__name__}")
        click.echo("\nThese components are now available in your FlowyML stacks.")
    else:
        click.echo(f"✗ No components imported from '{integration_name}'", err=True)
        click.echo("  Make sure the integration is installed:")
        click.echo(f"    flowyml zenml install {integration_name}")


@zenml.command("import-all")
def import_all_zenml_integrations() -> None:
    """Import all components from all installed ZenML integrations.

    This is the easiest way to make all ZenML components available
    in FlowyML with a single command.

    Example:
        flowyml zenml import-all
    """
    from flowyml.stacks.plugins import get_component_registry

    click.echo("Importing all installed ZenML integrations...")

    registry = get_component_registry()
    result = registry.import_all_zenml()

    if result:
        total = sum(len(comps) for comps in result.values())
        click.echo(f"✓ Successfully imported {total} components from {len(result)} integrations:\n")

        for integration_name, components in result.items():
            click.echo(f"  {integration_name}:")
            for comp in components:
                click.echo(f"    • {comp.__name__}")

        click.echo("\nAll components are now available in your FlowyML stacks.")
    else:
        click.echo("✗ No components imported", err=True)
        click.echo("  Make sure ZenML is installed and you have some integrations installed:")
        click.echo("    pip install zenml")
        click.echo("    flowyml zenml install mlflow")


@zenml.command("status")
def zenml_status() -> None:
    """Check ZenML availability and show integration summary.

    Shows whether ZenML is installed and a summary of available
    and installed integrations.
    """
    try:
        import zenml

        zenml_version = zenml.__version__
        zenml_available = True
    except ImportError:
        zenml_available = False
        zenml_version = None

    if zenml_available:
        click.echo(f"✓ ZenML is installed (version {zenml_version})\n")

        from flowyml.stacks.plugins import get_component_registry

        registry = get_component_registry()

        available = registry.list_zenml_integrations()
        installed = registry.list_installed_zenml_integrations()

        click.echo(f"  Available integrations: {len(available)}")
        click.echo(f"  Installed integrations: {len(installed)}")

        if installed:
            click.echo(f"\n  Installed: {', '.join(installed[:5])}")
            if len(installed) > 5:
                click.echo(f"             ...and {len(installed) - 5} more")

        click.echo("\n  Quick start:")
        click.echo("    flowyml zenml import-all  # Import all installed integrations")
    else:
        click.echo("✗ ZenML is not installed\n")
        click.echo("  To install ZenML:")
        click.echo("    pip install zenml")
        click.echo("\n  After installing, you can:")
        click.echo("    flowyml zenml list        # List available integrations")
        click.echo("    flowyml zenml install aws # Install an integration")
        click.echo("    flowyml zenml import-all  # Import all components")


# =============================================================================
# NATIVE PLUGIN COMMANDS
# =============================================================================


@cli.group()
def plugin() -> None:
    """Native plugin management commands.

    Manage FlowyML plugins without external framework dependencies.
    Install plugins directly (e.g., 'flowyml plugin install mlflow')
    and FlowyML will install only the underlying packages you need.
    """
    pass


@plugin.command("list")
@click.option("--installed", is_flag=True, help="Show only installed plugins")
@click.option(
    "--type",
    "plugin_type",
    type=click.Choice(
        [
            "experiment_tracker",
            "artifact_store",
            "orchestrator",
            "container_registry",
            "feature_store",
            "data_validator",
            "alerter",
        ],
    ),
    help="Filter by plugin type",
)
def plugin_list(installed: bool, plugin_type: str) -> None:
    """List available plugins.

    Shows all plugins in the FlowyML catalog. Use --installed to see
    only plugins whose packages are already installed.

    Examples:
        flowyml plugin list
        flowyml plugin list --installed
        flowyml plugin list --type experiment_tracker
    """
    from flowyml.plugins import get_manager, PluginType

    manager = get_manager()

    # Convert string to PluginType if provided
    ptype = PluginType(plugin_type) if plugin_type else None

    if installed:
        plugins = manager.list_installed(ptype)
        title = "Installed Plugins"
    else:
        plugins = manager.list_available(ptype)
        title = "Available Plugins"

    if not plugins:
        click.echo("No plugins found.")
        return

    click.echo(f"\n📦 {title}:\n")

    # Group by type for better display
    from flowyml.plugins import get_plugin_info

    grouped = {}
    for name in plugins:
        info = get_plugin_info(name)
        if info:
            type_name = info.plugin_type.value.replace("_", " ").title()
            if type_name not in grouped:
                grouped[type_name] = []
            is_installed = manager.is_installed(name)
            status = "✓" if is_installed else " "
            grouped[type_name].append((name, info.description, status))

    for type_name, items in sorted(grouped.items()):
        click.echo(f"  {type_name}:")
        for name, desc, status in sorted(items):
            click.echo(f"    {status} {name:<20} - {desc[:50]}")
        click.echo()

    click.echo("Install a plugin with: flowyml plugin install <name>")


@plugin.command("install")
@click.argument("name")
@click.option("--upgrade", is_flag=True, help="Upgrade to latest version")
def plugin_install(name: str, upgrade: bool) -> None:
    """Install a plugin.

    Installs the underlying packages for a plugin directly.
    For example, 'flowyml plugin install mlflow' installs the mlflow package.

    Examples:
        flowyml plugin install mlflow
        flowyml plugin install kubernetes
        flowyml plugin install s3 --upgrade
    """
    from flowyml.plugins import get_manager, get_plugin_info

    manager = get_manager()
    info = get_plugin_info(name)

    if not info:
        click.echo(f"✗ Plugin '{name}' not found", err=True)
        click.echo("\nAvailable plugins:")
        for p in manager.list_available()[:10]:
            click.echo(f"  • {p}")
        if len(manager.list_available()) > 10:
            click.echo(f"  ... and {len(manager.list_available()) - 10} more")
        return

    click.echo(f"Installing plugin '{name}'...")
    click.echo(f"  Packages: {', '.join(info.packages)}")

    if manager.install(name, upgrade=upgrade):
        click.echo(f"\n✓ Plugin '{name}' installed successfully!")
        click.echo("\nUsage:")
        click.echo("  from flowyml.plugins import get_plugin")
        click.echo(f'  plugin = get_plugin("{name}")')
    else:
        click.echo(f"\n✗ Failed to install '{name}'", err=True)


@plugin.command("info")
@click.argument("name")
def plugin_info(name: str) -> None:
    """Show detailed information about a plugin.

    Displays the plugin description, required packages, documentation URL,
    and current installation status.
    """
    from flowyml.plugins import get_plugin_info, get_manager

    info = get_plugin_info(name)
    manager = get_manager()

    if not info:
        click.echo(f"✗ Plugin '{name}' not found", err=True)
        return

    is_installed = manager.is_installed(name)
    status = "✓ Installed" if is_installed else "○ Not installed"

    click.echo(f"\n📦 Plugin: {info.name}")
    click.echo(f"   Status: {status}")
    click.echo(f"   Type: {info.plugin_type.value.replace('_', ' ').title()}")
    click.echo(f"   Description: {info.description}")
    click.echo(f"   Version: {info.version}")
    click.echo(f"   Author: {info.author}")
    click.echo("\n   Packages:")
    for pkg in info.packages:
        click.echo(f"     • {pkg}")
    if info.tags:
        click.echo(f"\n   Tags: {', '.join(info.tags)}")
    if info.documentation_url:
        click.echo(f"\n   Docs: {info.documentation_url}")

    if not is_installed:
        click.echo(f"\n   Install with: flowyml plugin install {name}")


@plugin.command("uninstall")
@click.argument("name")
@click.confirmation_option(prompt="Are you sure you want to uninstall?")
def plugin_uninstall(name: str) -> None:
    """Uninstall a plugin.

    Removes the underlying packages for a plugin.
    """
    from flowyml.plugins import get_manager

    manager = get_manager()

    if not manager.is_installed(name):
        click.echo(f"Plugin '{name}' is not installed")
        return

    click.echo(f"Uninstalling plugin '{name}'...")

    if manager.uninstall(name):
        click.echo(f"✓ Plugin '{name}' uninstalled")
    else:
        click.echo(f"✗ Failed to uninstall '{name}'", err=True)


@plugin.command("install-git")
@click.argument("git_url")
def plugin_install_git(git_url: str) -> None:
    """Install a community plugin from a git repository.

    Example:
        flowyml plugin install-git https://github.com/user/flowyml-custom-plugin.git
    """
    from flowyml.plugins import get_manager

    manager = get_manager()

    click.echo(f"Installing plugin from {git_url}...")

    if manager.install_from_git(git_url):
        click.echo("✓ Plugin installed from git!")
        click.echo("  Run 'flowyml plugin list --installed' to see available plugins")
    else:
        click.echo("✗ Failed to install from git", err=True)


# =============================================================================
# STACK COMMANDS (Config-based plugin management)
# =============================================================================


@cli.group()
def stack() -> None:
    """Stack configuration commands.

    Configure your FlowyML stack (experiment_tracker, artifact_store,
    orchestrator, etc.) in flowyml.yaml for seamless integration.

    With a configured stack, your code stays clean:
        from flowyml.plugins import start_run, log_metrics, save_model

        start_run("training")
        log_metrics({"accuracy": 0.95})
        save_model(model, "models/classifier")
    """
    pass


@stack.command("init")
@click.option("--tracker", type=str, help="Experiment tracker plugin (e.g., mlflow)")
@click.option("--store", type=str, help="Artifact store plugin (e.g., gcs, s3)")
@click.option("--orchestrator", type=str, help="Orchestrator plugin (e.g., vertex_ai)")
@click.option("--registry", type=str, help="Container registry plugin (e.g., gcr)")
@click.option("--force", is_flag=True, help="Overwrite existing config")
def stack_init(
    tracker: str,
    store: str,
    orchestrator: str,
    registry: str,
    force: bool,
) -> None:
    """Initialize a flowyml.yaml configuration file.

    Creates a template configuration file with your selected plugins.
    You can then customize the configuration with your settings.

    Examples:
        flowyml stack init --tracker mlflow --store gcs
        flowyml stack init --tracker mlflow --store s3 --orchestrator kubernetes
    """
    import os
    from flowyml.plugins import generate_config_template

    config_path = "flowyml.yaml"

    if os.path.exists(config_path) and not force:
        click.echo(f"✗ {config_path} already exists. Use --force to overwrite.", err=True)
        return

    content = generate_config_template(
        tracker=tracker,
        store=store,
        orchestrator=orchestrator,
        registry=registry,
    )

    with open(config_path, "w") as f:
        f.write(content)

    click.echo(f"✓ Created {config_path}")
    click.echo("\nNext steps:")
    click.echo("  1. Edit flowyml.yaml with your settings")

    # Show which plugins to install
    plugins_to_install = [p for p in [tracker, store, orchestrator, registry] if p]
    if plugins_to_install:
        click.echo(f"  2. Install plugins: flowyml plugin install {' '.join(plugins_to_install)}")

    click.echo("  3. Use in code:")
    click.echo("     from flowyml.plugins import start_run, log_metrics, save_model")
    click.echo('     start_run("my_training")')


@stack.command("show")
def stack_show() -> None:
    """Show the currently configured stack.

    Displays all plugins configured in flowyml.yaml and their status.
    """
    from flowyml.plugins import validate_stack, get_config

    config = get_config()
    plugins_config = config.plugins_config

    if not plugins_config:
        click.echo("No stack configured. Run 'flowyml stack init' to create flowyml.yaml")
        return

    click.echo("\n📦 Current Stack:\n")

    validation = validate_stack()

    for role, conf in plugins_config.items():
        if isinstance(conf, dict):
            plugin_type = conf.get("type", "unknown")
            is_installed = validation.get(role, False)
            status = "✓" if is_installed else "○"

            click.echo(f"  {status} {role}:")
            click.echo(f"      type: {plugin_type}")

            # Show key config values (not sensitive ones)
            for key, value in conf.items():
                if key != "type" and "key" not in key.lower() and "secret" not in key.lower():
                    click.echo(f"      {key}: {value}")
            click.echo()

    # Show missing plugins
    missing = [role for role, installed in validation.items() if not installed]
    if missing:
        click.echo("⚠️  Some plugins are not installed:")
        for role in missing:
            plugin_type = plugins_config.get(role, {}).get("type")
            if plugin_type:
                click.echo(f"    flowyml plugin install {plugin_type}")


@stack.command("validate")
def stack_validate() -> None:
    """Validate the current stack configuration.

    Checks that all configured plugins are installed and can be initialized.
    """
    from flowyml.plugins import get_config, validate_stack

    click.echo("Validating stack configuration...\n")

    config = get_config()

    if not config._config_path:
        click.echo("✗ No flowyml.yaml found", err=True)
        click.echo("  Run 'flowyml stack init' to create one")
        return

    click.echo(f"Config file: {config._config_path}\n")

    validation = validate_stack()

    if not validation:
        click.echo("No plugins configured")
        return

    all_valid = True
    for role, is_installed in validation.items():
        status = "✓" if is_installed else "✗"
        click.echo(f"  {status} {role}")
        if not is_installed:
            all_valid = False

    click.echo()
    if all_valid:
        click.echo("✓ All plugins are installed and ready!")
    else:
        click.echo("✗ Some plugins need to be installed")
        click.echo("  Run 'flowyml stack show' for installation commands")


@stack.command("install")
def stack_install() -> None:
    """Install all plugins configured in flowyml.yaml."""
    from flowyml.plugins import get_config, get_manager

    config = get_config()
    plugins_config = config.plugins_config
    manager = get_manager()

    if not plugins_config:
        click.echo("No stack configured. Run 'flowyml stack init' first.")
        return

    click.echo("Installing stack plugins...\n")

    for _role, conf in plugins_config.items():
        if isinstance(conf, dict):
            plugin_type = conf.get("type")
            if plugin_type:
                if manager.is_installed(plugin_type):
                    click.echo(f"  ✓ {plugin_type} (already installed)")
                else:
                    click.echo(f"  Installing {plugin_type}...")
                    if manager.install(plugin_type):
                        click.echo(f"  ✓ {plugin_type} installed")
                    else:
                        click.echo(f"  ✗ Failed to install {plugin_type}")

    click.echo("\n✓ Stack installation complete!")
    click.echo("  Run 'flowyml stack validate' to verify the configuration")


if __name__ == "__main__":
    cli()
