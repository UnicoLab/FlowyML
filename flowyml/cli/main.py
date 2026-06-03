"""Main CLI entry point for flowyml."""

import os
import rich_click as click
from flowyml.cli.rich_utils import recho
from pathlib import Path
from flowyml.utils.config import get_config

# Import model commands early to avoid E402 error
from flowyml.cli.models import (
    list_models,
    promote_model,
    show_model,
    delete_model,
)
from flowyml.cli.evals import eval_cli

# ── Rich-Click Styling Configuration ────────────────────────────────
click.rich_click.USE_RICH_MARKUP = True
click.rich_click.USE_MARKDOWN = False
click.rich_click.SHOW_ARGUMENTS = True
click.rich_click.GROUP_ARGUMENTS_OPTIONS = True
click.rich_click.STYLE_ERRORS_SUGGESTION = "magenta italic"
click.rich_click.ERRORS_SUGGESTION = "Try running the '--help' flag for more information."
click.rich_click.ERRORS_EPILOGUE = "To get help, run: [bold cyan]flowyml --help[/]"
click.rich_click.STYLE_HELPTEXT = ""
click.rich_click.STYLE_OPTION = "bold cyan"
click.rich_click.STYLE_SWITCH = "bold green"
click.rich_click.STYLE_METAVAR = "bold yellow"
click.rich_click.STYLE_USAGE = "bold"
click.rich_click.STYLE_USAGE_COMMAND = "bold cyan"
click.rich_click.MAX_WIDTH = 100
click.rich_click.SHOW_METAVARS_COLUMN = True
click.rich_click.APPEND_METAVARS_HELP = False
click.rich_click.COMMAND_GROUPS = {
    "flowyml": [
        {
            "name": "🚀 Quick Start",
            "commands": ["go", "stop", "status", "info", "tui"],
        },
        {
            "name": "⚡ Pipeline Execution",
            "commands": ["run", "init", "logs"],
        },
        {
            "name": "📊 Data & Tracking",
            "commands": ["experiment", "models", "eval"],
        },
        {
            "name": "🔧 Infrastructure",
            "commands": ["stack", "docker", "config", "cache", "db", "schedule"],
        },
        {
            "name": "🌐 Services",
            "commands": ["ui", "zenml", "plugin"],
        },
    ],
}
click.rich_click.OPTION_GROUPS = {
    "flowyml run": [
        {
            "name": "Execution Options",
            "options": ["--stack", "--context", "--debug", "--retry"],
        },
    ],
    "flowyml go": [
        {
            "name": "Server Options",
            "options": ["--host", "--port", "--open-browser"],
        },
    ],
}


@click.group()
@click.version_option(version="0.1.0", prog_name="flowyml")
def cli() -> None:
    """[bold cyan]🌊 FlowyML[/] — Next-Generation ML Pipeline Framework

    A developer-first ML pipeline orchestration framework that makes
    ML pipelines feel [bold]effortless[/] while providing production-grade
    capabilities.

    [dim]Get started:[/]  [bold]flowyml go[/]          Launch the dashboard
    [dim]Terminal UI:[/]   [bold]flowyml tui[/]         Full-screen dashboard
    [dim]System info:[/]   [bold]flowyml info[/]        Show system status
    [dim]Run pipeline:[/]  [bold]flowyml run <name>[/]  Execute a pipeline
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
    recho(f"Initializing flowyml project '{name}' with template '{template}'...")

    try:
        init_project(name, template, project_dir)
        recho(f"[green]✓Project '{name}' created successfully at {project_dir}")
        recho("\nNext steps:")
        recho(f"  cd {name}")
        recho("  flowyml run training_pipeline")
    except Exception as e:
        recho(f"[red]✗Error creating project: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.argument("pipeline_name")
@click.option("--stack", default="local", help="Stack to use (name, URI, or 'local')")
@click.option("--env", "env_name", default=None, help="Environment from flowyml.yaml (e.g. 'dev', 'staging', 'prod')")
@click.option("--dry-run", "dry_run", is_flag=True, help="Validate without executing (resolve stack, check policies)")
@click.option("--context", "-c", multiple=True, help="Context parameters (key=value)")
@click.option("--debug", is_flag=True, help="Enable debug mode")
@click.option("--retry", type=int, help="Number of retries for the pipeline")
def run(
    pipeline_name: str,
    stack: str,
    env_name: str | None,
    dry_run: bool,
    context: tuple,
    debug: bool,
    retry: int | None,
) -> None:
    r"""Run a pipeline.

    Examples:
        \b
        flowyml run my_pipeline                        # Default local stack
        flowyml run my_pipeline --stack aml_cpu_small   # Named enterprise stack
        flowyml run my_pipeline --env prod              # From project config
        flowyml run my_pipeline --dry-run               # Validate only
    """
    from flowyml.cli.run import run_pipeline
    from flowyml.core.retry_policy import OrchestratorRetryPolicy

    # Parse context parameters
    ctx_params = {}
    for param in context:
        key, value = param.split("=", 1)
        ctx_params[key] = value

    if dry_run:
        recho(f"🔍 Dry run: pipeline '{pipeline_name}' on stack '{stack}'...")
    else:
        recho(f"Running pipeline '{pipeline_name}' on stack '{stack}'...")
    if env_name:
        recho(f"  Environment: {env_name}")

    kwargs = {}
    if retry:
        kwargs["retry_policy"] = OrchestratorRetryPolicy(max_attempts=retry)
        recho(f"  Retry policy enabled: max_attempts={retry}")
    if env_name:
        kwargs["env"] = env_name
    if dry_run:
        kwargs["dry_run"] = True

    try:
        result = run_pipeline(
            pipeline_name,
            stack=stack if stack != "local" else None,
            env=env_name,
            dry_run=dry_run,
            context_params=ctx_params,
            debug=debug,
            **{k: v for k, v in kwargs.items() if k not in ("env", "dry_run")},
        )
        if dry_run:
            recho("[green]✓ Dry run validation passed.")
        else:
            recho("[green]✓Pipeline completed successfully")
            recho(f"  Run ID: {result.get('run_id', 'N/A')}")
            recho(f"  Duration: {result.get('duration', 'N/A')}")
    except Exception as e:
        recho(f"[red]✗Pipeline failed: {e}", err=True)
        raise click.Abort()


@cli.command("step-runner")
@click.option(
    "--pipeline",
    "pipeline_module",
    envvar="FLOWYML_PIPELINE_MODULE",
    help="Pipeline module path (module:function)",
)
@click.option("--steps", "step_names", envvar="FLOWYML_STEP_NAMES", help="Comma-separated step names to execute")
@click.option("--run-id", envvar="FLOWYML_RUN_ID", help="Run identifier for artifact namespacing")
@click.option("--group", "group_name", envvar="FLOWYML_EXECUTION_GROUP", default="", help="Execution group name")
@click.option(
    "--artifact-dir",
    envvar="FLOWYML_ARTIFACT_DIR",
    default=None,
    help="Artifact directory for intermediate results",
)
def step_runner_cmd(
    pipeline_module: str | None,
    step_names: str | None,
    run_id: str | None,
    group_name: str,
    artifact_dir: str | None,
) -> None:
    r"""Run specific pipeline steps (used by remote containers).

    This command is the container-side entrypoint for per-group remote
    execution. The orchestrator submits containers that invoke this
    command with the appropriate step names.

    Can be invoked via CLI args or environment variables:

    \b
    Examples:
        flowyml step-runner --pipeline my.mod:build_pipe --steps step1,step2 --run-id abc123
        FLOWYML_PIPELINE_MODULE=... FLOWYML_STEP_NAMES=... flowyml step-runner
    """
    import logging
    import json as _json
    import sys
    from flowyml.core.step_runner import StepRunner

    # ── Platform-aware log configuration ──────────────────────────────
    platform = os.environ.get("FLOWYML_PLATFORM", "").lower()

    if platform == "gcp":
        # GCP Cloud Logging: structured JSON on stdout for proper severity parsing
        class GCPFormatter(logging.Formatter):
            """Format log records as JSON for Google Cloud Logging."""

            _SEVERITY_MAP = {
                "DEBUG": "DEBUG",
                "INFO": "INFO",
                "WARNING": "WARNING",
                "ERROR": "ERROR",
                "CRITICAL": "CRITICAL",
            }

            def format(self, record: logging.LogRecord) -> str:  # noqa: A003
                entry = {
                    "severity": self._SEVERITY_MAP.get(record.levelname, "DEFAULT"),
                    "message": record.getMessage(),
                    "logger": record.name,
                }
                if record.exc_info and record.exc_info[0]:
                    entry["exception"] = self.formatException(record.exc_info)
                return _json.dumps(entry, ensure_ascii=False)

        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(GCPFormatter())
        logging.root.handlers.clear()
        logging.root.addHandler(handler)
        logging.root.setLevel(logging.INFO)
    else:
        # Local / generic: clean human-readable format
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
            datefmt="%H:%M:%S",
        )

    # ── Intercept loguru → route through stdlib logging ───────────────
    # This prevents duplicate log lines (one from loguru, one from stdlib)
    try:
        from loguru import logger as loguru_logger

        # Remove loguru default stderr sink, add a stdlib-routing sink
        loguru_logger.remove()

        def _loguru_sink(message):
            """Route loguru messages through stdlib logging."""
            record = message.record
            level = record["level"].name
            stdlib_level = getattr(logging, level, logging.INFO)
            logging.getLogger(record["name"]).log(
                stdlib_level,
                record["message"],
            )

        loguru_logger.add(_loguru_sink, level="INFO", format="{message}")
    except ImportError:
        pass  # loguru not installed, no interception needed

    if not pipeline_module:
        # Try to read from flowyml.yaml
        try:
            config = get_config()
            pipeline_module = config.get("pipeline_module")
        except Exception:
            pass

    if not pipeline_module:
        recho("[red]✗ --pipeline or FLOWYML_PIPELINE_MODULE is required", err=True)
        raise click.Abort()
    if not step_names:
        recho("[red]✗ --steps or FLOWYML_STEP_NAMES is required", err=True)
        raise click.Abort()
    if not run_id:
        import uuid

        run_id = uuid.uuid4().hex[:8]

    steps_list = [s.strip() for s in step_names.split(",") if s.strip()]

    recho("[bold cyan]🔧 FlowyML Step Runner[/]")
    recho(f"  Pipeline: {pipeline_module}")
    recho(f"  Steps:    {', '.join(steps_list)}")
    recho(f"  Run ID:   {run_id}")
    recho(f"  Stack:    {os.environ.get('FLOWYML_STACK', 'local')}")
    recho(f"  Platform: {platform or 'local'}")
    if group_name:
        recho(f"  Group:    {group_name}")

    try:
        runner = StepRunner(
            pipeline_module=pipeline_module,
            step_names=steps_list,
            run_id=run_id,
            group_name=group_name,
            artifact_dir=artifact_dir,
        )
        results = runner.run()
        recho(f"[green]✓ {len(results)} steps completed successfully")
    except Exception as e:
        recho(f"[red]✗ Step runner failed: {e}", err=True)
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
        run_pipeline(pipeline_name, stack=stack if stack != "local" else None)

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

        recho(f"[green]✓Schedule created for '{pipeline_name}' ({schedule_type}={value})")
        recho("  Note: Ensure the scheduler service is running to execute this schedule.")
    except Exception as e:
        recho(f"[red]✗Error creating schedule: {e}", err=True)


@schedule.command("list")
def list_schedules() -> None:
    """List all active schedules."""
    from flowyml.core.scheduler import PipelineScheduler

    scheduler = PipelineScheduler()
    jobs = scheduler.list_schedules()

    if not jobs:
        recho("No active schedules found.")
        return

    recho(f"Found {len(jobs)} schedules:\n")
    for job in jobs:
        recho(f"  {job.pipeline_name} ({job.schedule_type}: {job.schedule_value})")
        recho(f"    Next run: {job.next_run}")
        recho()


@schedule.command("start")
def start_scheduler() -> None:
    """Start the scheduler service (blocking)."""
    from flowyml.core.scheduler import PipelineScheduler

    recho("[bold cyan]🚀 Starting Scheduler Service...")
    scheduler = PipelineScheduler()

    try:
        # In a real app, this would load definitions from DB and register them
        # For now, it just runs the scheduler loop for existing in-memory jobs
        # (which might be empty if we restarted).
        # To make this persistent, we'd need to serialize job definitions to DB.
        # The current Scheduler implementation supports SQLite persistence for job state,
        # but we need to re-register jobs on startup.

        recho("  Scheduler running. Press Ctrl+C to stop.")
        scheduler.start(blocking=True)
    except KeyboardInterrupt:
        scheduler.stop()
        recho("\n🛑 Scheduler stopped.")


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
        recho(f"[yellow]ℹ️  UI server is already running at http://{host}:{port}")
        if open_browser:
            import webbrowser

            webbrowser.open(f"http://{host}:{port}")
        return

    recho(f"[bold cyan]🚀 Starting flowyml UI on http://{host}:{port}...")
    if dev:
        recho("   Development mode: Auto-reload enabled")

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
        recho("[red]✗UI server not available. Install with: pip install flowyml[ui]", err=True)
        raise click.Abort()
    except Exception as e:
        recho(f"[red]✗Error starting UI: {e}", err=True)
        raise click.Abort()


@ui.command()
def stop() -> None:
    """Stop the flowyml UI server."""
    recho("Stopping flowyml UI server...")
    recho("[yellow]ℹ️  To stop the UI server:")
    recho("   - If running in foreground: Press Ctrl+C")
    recho("   - If running in background: pkill -f 'flowyml ui start'")


@ui.command()
@click.option("--host", default="localhost", help="Host to check")
@click.option("--port", default=8080, help="Port to check")
def status(host: str, port: int) -> None:
    """Check if the UI server is running."""
    from flowyml.ui.utils import is_ui_running, get_ui_url

    if is_ui_running(host, port):
        url = get_ui_url(host, port)
        recho(f"[green]✅UI server is running at {url}")
        recho("   Status: Healthy")
        recho(f"   Health endpoint: {url}/api/health")
    else:
        recho(f"[red]❌UI server is not running on {host}:{port}")
        recho(f"   Start with: flowyml ui start --host {host} --port {port}")


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
    from flowyml.cli.rich_utils import get_console, RICH_AVAILABLE

    try:
        experiments = list_experiments_cmd(limit, pipeline)
        console = get_console()

        if RICH_AVAILABLE and console:
            from rich.table import Table as RichTable
            from rich import box as rich_box

            table = RichTable(
                title=f"[bold cyan]🧪 Experiments ({len(experiments)})[/bold cyan]",
                box=rich_box.ROUNDED,
                border_style="cyan",
            )
            table.add_column("Name", style="cyan", width=30)
            table.add_column("Runs", justify="right", style="green", width=8)
            table.add_column("Project", style="yellow", width=20)
            table.add_column("Created", style="dim", width=20)

            for exp in experiments:
                table.add_row(
                    exp.get("name", "—"),
                    str(exp.get("num_runs", exp.get("run_count", 0))),
                    exp.get("project", "—"),
                    (exp.get("created_at") or "—")[:19],
                )
            console.print(table)
        else:
            recho(f"Found {len(experiments)} experiments:\n")
            for exp in experiments:
                recho(f"  {exp['name']}")
                recho(f"    Runs: {exp.get('num_runs', 0)}")
                recho(f"    Created: {exp.get('created_at', 'N/A')}")
                recho()
    except Exception as e:
        recho(f"[red]✗Error listing experiments: {e}", err=True)


@experiment.command()
@click.argument("run_ids", nargs=-1, required=True)
def compare(run_ids: tuple) -> None:
    """Compare multiple experiment runs."""
    from flowyml.cli.experiment import compare_runs

    recho(f"Comparing {len(run_ids)} runs...")

    try:
        comparison = compare_runs(list(run_ids))
        recho("\nComparison Results:")
        recho(comparison)
    except Exception as e:
        recho(f"[red]✗Error comparing runs: {e}", err=True)


@cli.group()
def cache() -> None:
    """Cache management commands."""
    pass


@cache.command()
def stats() -> None:
    """Show cache statistics."""
    from flowyml.core.cache import CacheStore
    from flowyml.cli.rich_utils import get_console, RICH_AVAILABLE

    try:
        cache = CacheStore()
        cache_stats = cache.stats()
        console = get_console()

        if RICH_AVAILABLE and console:
            from flowyml.cli.rich_utils import print_kv_panel, print_stats_cards

            cards = [
                ("Hits", str(cache_stats.get("hits", 0)), "green"),
                ("Misses", str(cache_stats.get("misses", 0)), "red"),
                ("Hit Rate", f"{cache_stats.get('hit_rate', 0):.1%}", "cyan"),
                ("Entries", str(cache_stats.get("total_entries", 0)), "yellow"),
            ]
            print_stats_cards(cards, console=console)
            print_kv_panel(
                "💾 Cache Statistics",
                {
                    "Size": f"{cache_stats.get('total_size_mb', 0):.2f} MB",
                    "Hits": str(cache_stats.get("hits", 0)),
                    "Misses": str(cache_stats.get("misses", 0)),
                    "Hit Rate": f"{cache_stats.get('hit_rate', 0):.1%}",
                    "Total Entries": str(cache_stats.get("total_entries", 0)),
                },
                console=console,
            )
        else:
            recho("Cache Statistics:\n")
            recho(f"  Hits: {cache_stats['hits']}")
            recho(f"  Misses: {cache_stats['misses']}")
            recho(f"  Hit Rate: {cache_stats.get('hit_rate', 0):.1%}")
            recho(f"  Total Entries: {cache_stats.get('total_entries', 0)}")
            recho(f"  Size: {cache_stats.get('total_size_mb', 0):.2f} MB")
    except Exception as e:
        recho(f"[red]✗Error getting cache stats: {e}", err=True)


@cache.command()
@click.confirmation_option(prompt="Are you sure you want to clear the cache?")
def clear() -> None:
    """Clear all cache."""
    from flowyml.core.cache import CacheStore

    try:
        cache = CacheStore()
        cache.clear()
        recho("[green]✓Cache cleared successfully")
    except Exception as e:
        recho(f"[red]✗Error clearing cache: {e}", err=True)


@cli.group()
def models() -> None:
    """Model registry management commands."""
    pass


@cli.group()
def db() -> None:
    """Database management commands."""
    pass


@db.command("migrate")
@click.option("--revision", default="head", help="Target revision (default: head)")
@click.option("--sql", is_flag=True, help="Generate SQL instead of running migration")
def migrate(revision: str, sql: bool) -> None:
    """Run database migrations.

    This applies Alembic migrations to your database schema.

    Examples:
        flowyml db migrate              # Upgrade to latest
        flowyml db migrate --revision 001_initial
        flowyml db migrate --sql        # Print SQL without executing
    """
    import os

    db_url = os.getenv("FLOWYML_DATABASE_URL", "sqlite:///flowyml.db")
    recho("🔄 Running database migrations...")
    recho(f"   Database: {db_url[:50]}...")

    try:
        from alembic.config import Config
        from alembic import command

        # Get alembic.ini path (project root)
        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", db_url)

        if sql:
            command.upgrade(alembic_cfg, revision, sql=True)
        else:
            command.upgrade(alembic_cfg, revision)
            recho(f"[green]✅Migrations applied successfully to revision: {revision}")
    except Exception as e:
        recho(f"[red]❌Migration failed: {e}", err=True)
        raise click.Abort()


@db.command("downgrade")
@click.argument("revision", default="-1")
def downgrade(revision: str) -> None:
    """Downgrade database schema.

    Examples:
        flowyml db downgrade -1         # Downgrade one revision
        flowyml db downgrade base       # Downgrade to empty database
    """
    import os

    db_url = os.getenv("FLOWYML_DATABASE_URL", "sqlite:///flowyml.db")
    recho("🔄 Downgrading database...")

    try:
        from alembic.config import Config
        from alembic import command

        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", db_url)

        command.downgrade(alembic_cfg, revision)
        recho(f"[green]✅Downgraded to revision: {revision}")
    except Exception as e:
        recho(f"[red]❌Downgrade failed: {e}", err=True)
        raise click.Abort()


@db.command("current")
def current() -> None:
    """Show current database revision."""
    import os

    db_url = os.getenv("FLOWYML_DATABASE_URL", "sqlite:///flowyml.db")

    try:
        from alembic.config import Config
        from alembic import command

        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", db_url)

        recho("Current database revision:")
        command.current(alembic_cfg, verbose=True)
    except Exception as e:
        recho(f"[red]❌Failed to get current revision: {e}", err=True)


@db.command("history")
def history() -> None:
    """Show migration history."""
    try:
        from alembic.config import Config
        from alembic import command

        alembic_cfg = Config("alembic.ini")
        recho("Migration history:")
        command.history(alembic_cfg, verbose=True)
    except Exception as e:
        recho(f"[red]❌Failed to get history: {e}", err=True)


@db.command("reset")
@click.option("--all", "purge_all", is_flag=True, help="Purge ALL tables")
@click.option("--runs", "purge_runs", is_flag=True, help="Purge runs, metrics, params, artifacts")
@click.option("--traces", "purge_traces", is_flag=True, help="Purge traces")
@click.option("--artifacts", "purge_artifacts", is_flag=True, help="Purge artifacts")
@click.option("--models", "purge_models", is_flag=True, help="Purge model versions")
@click.option("--experiments", "purge_experiments", is_flag=True, help="Purge experiments")
@click.option("--metrics", "purge_metrics", is_flag=True, help="Purge metrics")
@click.option("--backup/--no-backup", default=True, help="Backup DB before reset (default: yes)")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
def db_reset(
    purge_all: bool,
    purge_runs: bool,
    purge_traces: bool,
    purge_artifacts: bool,
    purge_models: bool,
    purge_experiments: bool,
    purge_metrics: bool,
    backup: bool,
    yes: bool,
) -> None:
    r"""Reset (purge) database tables.

    Selectively delete data from the metadata database. Use --all to wipe
    everything, or pick specific tables to purge.

    \b
    Examples:
        flowyml db reset --all --yes           # Wipe everything, no prompt
        flowyml db reset --runs --traces       # Purge runs and traces
        flowyml db reset --all --no-backup     # Reset without backup
    """
    from flowyml.cli.rich_utils import get_console, print_db_stats

    console = get_console()

    # Determine what to purge
    targets: list[str] = []
    if purge_all:
        targets = [
            "experiment_runs",
            "metrics",
            "model_metrics",
            "parameters",
            "artifacts",
            "traces",
            "pipeline_templates",
            "pipeline_definitions",
            "model_versions",
            "experiments",
            "projects",
            "runs",
        ]
    else:
        if purge_runs:
            targets.extend(["experiment_runs", "metrics", "parameters", "artifacts", "runs"])
        if purge_traces:
            targets.append("traces")
        if purge_artifacts and "artifacts" not in targets:
            targets.append("artifacts")
        if purge_models:
            targets.append("model_versions")
        if purge_experiments:
            if "experiment_runs" not in targets:
                targets.append("experiment_runs")
            targets.append("experiments")
        if purge_metrics:
            if "metrics" not in targets:
                targets.append("metrics")
            if "model_metrics" not in targets:
                targets.append("model_metrics")

    if not targets:
        recho("No tables selected. Use --all or pick specific tables (--runs, --traces, etc.)")
        recho("Run 'flowyml db reset --help' for options.")
        return

    # Show current stats
    try:
        from flowyml.storage.sql import SQLMetadataStore
        from sqlalchemy import func, select, delete as sa_delete

        store = SQLMetadataStore()
        all_tables = {
            "runs": store.runs,
            "artifacts": store.artifacts,
            "metrics": store.metrics,
            "model_metrics": store.model_metrics,
            "parameters": store.parameters,
            "experiments": store.experiments,
            "experiment_runs": store.experiment_runs,
            "traces": store.traces,
            "pipeline_definitions": store.pipeline_definitions,
            "projects": store.projects,
            "model_versions": store.model_versions,
            "pipeline_templates": store.pipeline_templates,
        }

        # Count rows before
        before_counts: dict[str, int] = {}
        with store.engine.connect() as conn:
            for name in targets:
                tbl = all_tables.get(name)
                if tbl is not None:
                    cnt = conn.execute(select(func.count()).select_from(tbl)).scalar() or 0
                    before_counts[name] = cnt

        total_before = sum(before_counts.values())

        if console:
            print_db_stats(before_counts, console=console)
            console.print(f"[bold yellow]⚠  Will delete {total_before} rows from {len(targets)} table(s)[/bold yellow]")
        else:
            recho(f"\nWill delete {total_before} rows from {len(targets)} table(s):")
            for name, cnt in before_counts.items():
                recho(f"  {name}: {cnt} rows")

        if total_before == 0:
            recho("\n✅ Tables are already empty. Nothing to reset.")
            return

        # Confirmation
        if not yes:
            if not click.confirm("\n🔥 Proceed with database reset?", default=False):
                recho("Cancelled.")
                return

        # Backup
        if backup:
            db_file = Path(".flowyml/metadata.db")
            if db_file.exists():
                import shutil
                from datetime import datetime as dt

                backup_path = db_file.with_suffix(f".{dt.now().strftime('%Y%m%d_%H%M%S')}.bak")
                shutil.copy2(db_file, backup_path)
                recho(f"💾 Backup saved to {backup_path}")

        # Purge
        deleted: dict[str, int] = {}
        with store.engine.connect() as conn:
            for name in targets:
                tbl = all_tables.get(name)
                if tbl is not None:
                    result = conn.execute(sa_delete(tbl))
                    deleted[name] = result.rowcount
            conn.commit()

        total_deleted = sum(deleted.values())

        if console:
            from rich.table import Table as RichTable
            from rich import box as rich_box

            table = RichTable(
                title="[bold green]✅ Database Reset Complete[/bold green]",
                box=rich_box.ROUNDED,
                border_style="green",
            )
            table.add_column("Table", style="cyan")
            table.add_column("Deleted", justify="right", style="red")
            for name, cnt in deleted.items():
                table.add_row(name, str(cnt))
            table.add_row("─" * 25, "─" * 8, style="dim")
            table.add_row("[bold]TOTAL[/]", f"[bold red]{total_deleted}[/]")
            console.print(table)
        else:
            recho(f"\n✅ Deleted {total_deleted} rows total.")
            for name, cnt in deleted.items():
                recho(f"  {name}: {cnt} rows deleted")

    except Exception as e:
        recho(f"[red]❌Reset failed: {e}", err=True)
        raise click.Abort()


@db.command("stats")
def db_stats_cmd() -> None:
    """Show database table statistics and size."""
    from flowyml.cli.rich_utils import get_console, print_db_stats

    console = get_console()

    try:
        from flowyml.storage.sql import SQLMetadataStore
        from sqlalchemy import func, select

        store = SQLMetadataStore()
        all_tables = {
            "runs": store.runs,
            "artifacts": store.artifacts,
            "metrics": store.metrics,
            "model_metrics": store.model_metrics,
            "parameters": store.parameters,
            "experiments": store.experiments,
            "experiment_runs": store.experiment_runs,
            "traces": store.traces,
            "pipeline_definitions": store.pipeline_definitions,
            "projects": store.projects,
            "model_versions": store.model_versions,
            "pipeline_templates": store.pipeline_templates,
        }

        counts: dict[str, int] = {}
        with store.engine.connect() as conn:
            for name, tbl in all_tables.items():
                try:
                    cnt = conn.execute(select(func.count()).select_from(tbl)).scalar() or 0
                    counts[name] = cnt
                except Exception:
                    counts[name] = 0

        # Get DB file size
        db_file = Path(".flowyml/metadata.db")
        if db_file.exists():
            size = db_file.stat().st_size
            if size < 1024:
                db_size = f"{size} B"
            elif size < 1024 * 1024:
                db_size = f"{size / 1024:.1f} KB"
            else:
                db_size = f"{size / (1024 * 1024):.2f} MB"
        else:
            db_size = "N/A"

        print_db_stats(counts, db_size=db_size, console=console)

    except Exception as e:
        recho(f"[red]❌Error getting DB stats: {e}", err=True)


# Register model commands
models.add_command(list_models)
models.add_command(promote_model)
models.add_command(show_model)
models.add_command(delete_model)

# Register evaluation commands

cli.add_command(eval_cli)


# ============================================================================
# flowyml info - Premium system dashboard
# ============================================================================


@cli.command("info")
def system_info() -> None:
    r"""📋 Show FlowyML system information and statistics.

    Displays a premium dashboard with version info, configuration,
    database statistics, and system health at a glance.

    \b
    Examples:
        flowyml info
    """
    import platform
    import sys
    from flowyml.cli.rich_utils import (
        get_console,
        print_banner,
        print_kv_panel,
        print_stats_cards,
        print_db_stats,
    )
    from flowyml.ui.utils import is_ui_running

    console = get_console()

    # Banner
    print_banner(console=console, subtitle="Next-Generation ML Pipeline Framework")

    # System info
    try:
        import flowyml

        version = getattr(flowyml, "__version__", "0.1.0")
    except Exception:
        version = "0.1.0"

    cfg = get_config()
    ui_running = is_ui_running("localhost", cfg.ui_port)
    ui_status = f"✅ Running on :{cfg.ui_port}" if ui_running else f"❌ Not running (port {cfg.ui_port})"

    system_data = {
        "FlowyML Version": version,
        "Python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "Platform": platform.platform(),
        "Home Directory": str(cfg.flowyml_home),
        "Default Stack": cfg.default_stack,
        "Execution Mode": cfg.execution_mode,
        "Caching": "✅ Enabled" if cfg.enable_caching else "❌ Disabled",
        "Log Level": cfg.log_level,
        "UI Server": ui_status,
    }

    if console:
        print_kv_panel("🌊 System Information", system_data, console=console)
    else:
        recho("\n🌊 System Information")
        for k, v in system_data.items():
            recho(f"  {k:<20} {v}")
        recho()

    # DB stats
    try:
        from flowyml.storage.sql import SQLMetadataStore
        from sqlalchemy import func, select

        store = SQLMetadataStore()
        all_tables = {
            "runs": store.runs,
            "artifacts": store.artifacts,
            "metrics": store.metrics,
            "traces": store.traces,
            "experiments": store.experiments,
            "model_versions": store.model_versions,
        }

        counts: dict[str, int] = {}
        with store.engine.connect() as conn:
            for name, tbl in all_tables.items():
                try:
                    cnt = conn.execute(select(func.count()).select_from(tbl)).scalar() or 0
                    counts[name] = cnt
                except Exception:
                    counts[name] = 0

        # Stat cards
        cards = [
            ("Total Runs", str(counts.get("runs", 0)), "green"),
            ("Experiments", str(counts.get("experiments", 0)), "cyan"),
            ("Models", str(counts.get("model_versions", 0)), "magenta"),
            ("Traces", str(counts.get("traces", 0)), "yellow"),
        ]
        print_stats_cards(cards, console=console)

        # DB file size
        db_file = Path(".flowyml/metadata.db")
        if db_file.exists():
            size = db_file.stat().st_size
            db_size = f"{size / (1024 * 1024):.2f} MB" if size >= 1024 * 1024 else f"{size / 1024:.1f} KB"
        else:
            db_size = "N/A"

        print_db_stats(counts, db_size=db_size, console=console)

    except Exception:
        if console:
            console.print("[dim]Database not available[/dim]")
        else:
            recho("  Database: not available")

    # Quick commands
    if console:
        from rich.panel import Panel as RichPanel
        from rich import box as rich_box

        tips = (
            "[bold cyan]Quick Commands:[/]\n\n"
            "  flowyml go          [dim]Start UI dashboard[/]\n"
            "  flowyml run <file>  [dim]Run a pipeline[/]\n"
            "  flowyml tui         [dim]Open terminal dashboard[/]\n"
            "  flowyml db stats    [dim]Show database statistics[/]\n"
            "  flowyml db reset    [dim]Reset database[/]\n"
            "  flowyml stack list  [dim]List configured stacks[/]\n"
            "  flowyml models list [dim]List registered models[/]\n"
        )
        console.print(RichPanel(tips, border_style="dim", box=rich_box.ROUNDED))
    else:
        recho("\nQuick Commands:")
        recho("  flowyml go          Start UI dashboard")
        recho("  flowyml run <file>  Run a pipeline")
        recho("  flowyml tui         Open terminal dashboard")
        recho("  flowyml db reset    Reset database")


# ============================================================================
# flowyml tui - Terminal User Interface
# ============================================================================


@cli.command("tui")
def launch_tui() -> None:
    r"""🖥  Launch the interactive Terminal User Interface.

    Opens a full-screen Textual dashboard with tabs for:
    - Dashboard: stats, recent runs
    - Runs: browsable run list with detail view
    - Database: table statistics and purge tools
    - Config: current configuration

    \b
    Navigation:
      Tab/Shift+Tab - Switch tabs
      q             - Quit
      r             - Refresh data

    \b
    Examples:
        flowyml tui
    """
    try:
        from flowyml.cli.tui import launch_tui as _launch

        _launch()
    except ImportError:
        recho("[red]❌TUI requires 'textual'. Install with: pip install textual", err=True)
        raise click.Abort()
    except Exception as e:
        recho(f"[red]❌TUI error: {e}", err=True)
        raise click.Abort()


@cli.group()
def config() -> None:
    """Configuration management commands."""
    pass


@config.command("show")
def show_config() -> None:
    """Show current configuration."""
    from flowyml.cli.rich_utils import get_console, RICH_AVAILABLE, print_kv_panel

    cfg = get_config()
    console = get_console()

    data = {
        "FlowyML Home": str(cfg.flowyml_home),
        "Artifacts Dir": str(cfg.artifacts_dir),
        "Metadata DB": str(cfg.metadata_db),
        "Default Stack": cfg.default_stack,
        "Execution Mode": cfg.execution_mode,
        "Enable Caching": "✅ Yes" if cfg.enable_caching else "❌ No",
        "Log Level": cfg.log_level,
        "UI Port": str(cfg.ui_port),
        "Debug Mode": "✅ Yes" if cfg.debug_mode else "❌ No",
    }
    if cfg.execution_mode == "remote":
        data["Remote Server URL"] = cfg.remote_server_url
        data["Remote UI URL"] = cfg.remote_ui_url

    if RICH_AVAILABLE and console:
        print_kv_panel("⚙  FlowyML Configuration", data, console=console)
    else:
        recho("FlowyML Configuration:\n")
        for k, v in data.items():
            recho(f"  {k:<20} {v}")


@config.command("set-mode")
@click.argument("mode", type=click.Choice(["local", "remote"]))
def set_mode(mode: str) -> None:
    """Set execution mode (local or remote)."""
    cfg = get_config()
    cfg.execution_mode = mode
    cfg.save()
    recho(f"[green]✓Execution mode set to '{mode}'")


@config.command("set-url")
@click.option("--server", help="Remote server URL")
@click.option("--ui", help="Remote UI URL")
def set_url(server: str, ui: str) -> None:
    """Set remote server and UI URLs."""
    cfg = get_config()
    if server:
        cfg.remote_server_url = server
        recho(f"[green]✓Remote server URL set to '{server}'")
    if ui:
        cfg.remote_ui_url = ui
        recho(f"[green]✓Remote UI URL set to '{ui}'")
    cfg.save()


@config.command("set-token")
@click.argument("token")
def set_token(token: str) -> None:
    """Set the API token for remote authentication."""
    cfg = get_config()
    cfg.api_token = token
    cfg.save()
    recho(f"[green]✓API token set (length: {len(token)})")


@cli.command()
@click.argument("run_id")
@click.option("--step", help="Filter by step name")
@click.option("--tail", default=100, help="Number of lines to show")
def logs(run_id: str, step: str, tail: int) -> None:
    """View logs for a pipeline run."""
    from flowyml.cli.rich_utils import get_console, RICH_AVAILABLE

    console = get_console()

    try:
        from flowyml.storage.sql import SQLMetadataStore

        store = SQLMetadataStore()
        run = store.load_run(run_id)

        if not run:
            recho(f"[red]❌Run '{run_id}' not found.", err=True)
            return

        if RICH_AVAILABLE and console:
            from rich.panel import Panel as RichPanel
            from rich import box as rich_box

            st = run.get("status", "—")
            ico = {"completed": "✅", "failed": "❌", "running": "⏳"}.get(st, "❓")

            lines = [
                f"[bold cyan]📋 Run: {run_id}[/]",
                f"  Pipeline:  {run.get('pipeline_name', '—')}",
                f"  Status:    {ico} {st}",
                f"  Started:   {run.get('start_time', '—')}",
                f"  Ended:     {run.get('end_time', '—')}",
            ]
            dur = run.get("duration")
            if isinstance(dur, (int, float)):
                lines.append(f"  Duration:  {dur:.2f}s")

            steps = run.get("steps") or run.get("step_results") or []
            if isinstance(steps, list) and steps:
                lines.append(f"\n[bold yellow]Steps ({len(steps)}):[/]")
                for s in steps:
                    if isinstance(s, dict):
                        sn = s.get("step_name") or s.get("name", "—")
                        ss = s.get("status", "—")
                        si = {"completed": "✅", "failed": "❌", "running": "⏳"}.get(ss, "❓")
                        sd = s.get("duration")
                        sds = f" ({sd:.2f}s)" if isinstance(sd, (int, float)) else ""
                        if step and sn != step:
                            continue
                        lines.append(f"  {si} {sn}{sds}")
                        if s.get("error"):
                            lines.append(f"     [red]Error: {s['error']}[/]")

            metrics = run.get("metrics") or {}
            if metrics:
                lines.append("\n[bold green]Metrics:[/]")
                for k, v in sorted(metrics.items()):
                    lines.append(
                        f"  {k}: {v:.4f}" if isinstance(v, float) else f"  {k}: {v}",
                    )

            console.print(
                RichPanel(
                    "\n".join(lines),
                    border_style="cyan",
                    box=rich_box.ROUNDED,
                ),
            )
        else:
            recho(f"Run: {run_id}")
            recho(f"  Pipeline: {run.get('pipeline_name', '—')}")
            recho(f"  Status: {run.get('status', '—')}")
            steps = run.get("steps") or run.get("step_results") or []
            if isinstance(steps, list):
                for s in steps:
                    if isinstance(s, dict):
                        sn = s.get("step_name") or s.get("name", "—")
                        if step and sn != step:
                            continue
                        recho(f"  Step: {sn} — {s.get('status', '—')}")
    except Exception as e:
        recho(f"[red]❌Error loading run: {e}", err=True)


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
            recho("[green]✅flowyml is already running!")
            recho(f"🌐 Dashboard: {url}")
            recho("\nRun 'flowyml stop' to stop the server.")

        if open_browser:
            import webbrowser

            webbrowser.open(url)
        return

    # Start the UI server as a background subprocess
    if rich_available:
        console.print("[bold cyan]🌊 flowyml[/bold cyan] - Starting up...\n")
    else:
        recho("🌊 flowyml - Starting up...")

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
                console.print(
                    "[dim]Tip: The dashboard runs in the background. Your pipelines will[/dim]",
                )
                console.print("[dim]automatically show a clickable URL when they run.[/dim]")
            else:
                recho("[green]✅flowyml is ready!")
                recho(f"🌐 Dashboard: {url}")
                recho(f"📊 View pipelines: {url}/pipelines")
                recho(f"📜 View runs: {url}/runs")
                recho("\nRun 'flowyml stop' to stop the server.")
                recho("\nTip: The dashboard runs in the background. Your pipelines will")
                recho("automatically show a clickable URL when they run.")

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
            recho(f"[red]❌Failed to start flowyml UI server: {e}")
            recho("Possible issues:")
            recho(f"  • Port {port} might be in use")
            recho("  • Missing dependencies (uvicorn, fastapi)")
            recho(f"\nTry: flowyml go --port {port + 1}")
            recho("Or run 'flowyml ui start' for verbose output.")


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
                    console.print(
                        f"[green]✅ flowyml server (PID {pid}) stopped successfully.[/green]",
                    )
                else:
                    recho(f"[green]✅flowyml server (PID {pid}) stopped successfully.")
                return
            except ProcessLookupError:
                # Process already dead, clean up PID file
                pid_file.unlink(missing_ok=True)
            except PermissionError:
                if rich_available:
                    console.print(f"[red]❌ Permission denied to stop process {pid}[/red]")
                else:
                    recho(f"[red]❌Permission denied to stop process {pid}")
                return
        except (ValueError, IndexError):
            # Invalid PID file, remove it
            pid_file.unlink(missing_ok=True)

    # Check if server is running
    if not is_ui_running(host, port):
        if rich_available:
            console.print(f"[yellow]ℹ️  No flowyml server running on {host}:{port}[/yellow]")
        else:
            recho(f"[yellow]ℹ️  No flowyml server running on {host}:{port}")
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
        recho("[yellow]ℹ️  Server running but not started with 'flowyml go'.")
        recho("To stop it:")
        recho("  • If running in foreground: Press Ctrl+C")
        recho(f"  • Find and kill: pkill -f 'uvicorn.*:{port}'")
        recho(f"  • Or find PID: lsof -i :{port}")


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
            recho("[green]✅flowyml is running")
            recho(f"🌐 Dashboard: {url}")
            recho(f"💚 Health: {url}/api/health")
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
            recho(f"[red]❌flowyml is not running on {host}:{port}")
            recho("Start with: flowyml go")


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
        recho("Installed ZenML integrations:\n")
    else:
        integrations = registry.list_zenml_integrations()
        recho("Available ZenML integrations:\n")

    if not integrations:
        recho("  No integrations found.")
        recho("\n  Make sure ZenML is installed: pip install zenml")
        return

    for name in sorted(integrations):
        recho(f"  • {name}")

    recho(f"\nTotal: {len(integrations)} integrations")

    if not installed:
        recho("\nTo install an integration:")
        recho("  flowyml zenml install <integration_name>")


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

    recho(f"Installing ZenML integration '{integration_name}'...")

    registry = get_component_registry()
    success = registry.install_zenml_integration(integration_name)

    if success:
        recho(f"[green]✓Successfully installed '{integration_name}'")
        recho("\nTo use this integration in FlowyML:")
        recho(f"  flowyml zenml import {integration_name}")
    else:
        recho(f"[red]✗Failed to install '{integration_name}'", err=True)
        recho("  Check that ZenML is installed and the integration name is correct.")


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

    recho(f"Importing ZenML integration '{integration_name}'...")

    registry = get_component_registry()
    components = registry.import_zenml_integration(integration_name)

    if components:
        recho(f"[green]✓Successfully imported {len(components)} components:\n")
        for comp in components:
            recho(f"  • {comp.__name__}")
        recho("\nThese components are now available in your FlowyML stacks.")
    else:
        recho(f"[red]✗No components imported from '{integration_name}'", err=True)
        recho("  Make sure the integration is installed:")
        recho(f"    flowyml zenml install {integration_name}")


@zenml.command("import-all")
def import_all_zenml_integrations() -> None:
    """Import all components from all installed ZenML integrations.

    This is the easiest way to make all ZenML components available
    in FlowyML with a single command.

    Example:
        flowyml zenml import-all
    """
    from flowyml.stacks.plugins import get_component_registry

    recho("Importing all installed ZenML integrations...")

    registry = get_component_registry()
    result = registry.import_all_zenml()

    if result:
        total = sum(len(comps) for comps in result.values())
        recho(f"[green]✓Successfully imported {total} components from {len(result)} integrations:\n")

        for integration_name, components in result.items():
            recho(f"  {integration_name}:")
            for comp in components:
                recho(f"    • {comp.__name__}")

        recho("\nAll components are now available in your FlowyML stacks.")
    else:
        recho("[red]✗No components imported", err=True)
        recho("  Make sure ZenML is installed and you have some integrations installed:")
        recho("    pip install zenml")
        recho("    flowyml zenml install mlflow")


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
        recho(f"[green]✓ZenML is installed (version {zenml_version})\n")

        from flowyml.stacks.plugins import get_component_registry

        registry = get_component_registry()

        available = registry.list_zenml_integrations()
        installed = registry.list_installed_zenml_integrations()

        recho(f"  Available integrations: {len(available)}")
        recho(f"  Installed integrations: {len(installed)}")

        if installed:
            recho(f"\n  Installed: {', '.join(installed[:5])}")
            if len(installed) > 5:
                recho(f"             ...and {len(installed) - 5} more")

        recho("\n  Quick start:")
        recho("    flowyml zenml import-all  # Import all installed integrations")
    else:
        recho("[red]✗ZenML is not installed\n")
        recho("  To install ZenML:")
        recho("    pip install zenml")
        recho("\n  After installing, you can:")
        recho("    flowyml zenml list        # List available integrations")
        recho("    flowyml zenml install aws # Install an integration")
        recho("    flowyml zenml import-all  # Import all components")


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
        recho("No plugins found.")
        return

    recho(f"\n📦 {title}:\n")

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
        recho(f"  {type_name}:")
        for name, desc, status in sorted(items):
            recho(f"    {status} {name:<20} - {desc[:50]}")
        recho()

    recho("Install a plugin with: flowyml plugin install <name>")


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
        recho(f"[red]✗Plugin '{name}' not found", err=True)
        recho("\nAvailable plugins:")
        for p in manager.list_available()[:10]:
            recho(f"  • {p}")
        if len(manager.list_available()) > 10:
            recho(f"  ... and {len(manager.list_available()) - 10} more")
        return

    recho(f"Installing plugin '{name}'...")
    recho(f"  Packages: {', '.join(info.packages)}")

    if manager.install(name, upgrade=upgrade):
        recho(f"\n✓ Plugin '{name}' installed successfully!")
        recho("\nUsage:")
        recho("  from flowyml.plugins import get_plugin")
        recho(f'  plugin = get_plugin("{name}")')
    else:
        recho(f"\n✗ Failed to install '{name}'", err=True)


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
        recho(f"[red]✗Plugin '{name}' not found", err=True)
        return

    is_installed = manager.is_installed(name)
    status = "✓ Installed" if is_installed else "○ Not installed"

    recho(f"\n📦 Plugin: {info.name}")
    recho(f"   Status: {status}")
    recho(f"   Type: {info.plugin_type.value.replace('_', ' ').title()}")
    recho(f"   Description: {info.description}")
    recho(f"   Version: {info.version}")
    recho(f"   Author: {info.author}")
    recho("\n   Packages:")
    for pkg in info.packages:
        recho(f"     • {pkg}")
    if info.tags:
        recho(f"\n   Tags: {', '.join(info.tags)}")
    if info.documentation_url:
        recho(f"\n   Docs: {info.documentation_url}")

    if not is_installed:
        recho(f"\n   Install with: flowyml plugin install {name}")


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
        recho(f"Plugin '{name}' is not installed")
        return

    recho(f"Uninstalling plugin '{name}'...")

    if manager.uninstall(name):
        recho(f"[green]✓Plugin '{name}' uninstalled")
    else:
        recho(f"[red]✗Failed to uninstall '{name}'", err=True)


@plugin.command("install-git")
@click.argument("git_url")
def plugin_install_git(git_url: str) -> None:
    """Install a community plugin from a git repository.

    Example:
        flowyml plugin install-git https://github.com/user/flowyml-custom-plugin.git
    """
    from flowyml.plugins import get_manager

    manager = get_manager()

    recho(f"Installing plugin from {git_url}...")

    if manager.install_from_git(git_url):
        recho("[green]✓Plugin installed from git!")
        recho("  Run 'flowyml plugin list --installed' to see available plugins")
    else:
        recho("[red]✗Failed to install from git", err=True)


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
        recho(f"[red]✗{config_path} already exists. Use --force to overwrite.", err=True)
        return

    content = generate_config_template(
        tracker=tracker,
        store=store,
        orchestrator=orchestrator,
        registry=registry,
    )

    with open(config_path, "w") as f:
        f.write(content)

    recho(f"[green]✓Created {config_path}")
    recho("\nNext steps:")
    recho("  1. Edit flowyml.yaml with your settings")

    # Show which plugins to install
    plugins_to_install = [p for p in [tracker, store, orchestrator, registry] if p]
    if plugins_to_install:
        recho(f"  2. Install plugins: flowyml plugin install {' '.join(plugins_to_install)}")

    recho("  3. Use in code:")
    recho("     from flowyml.plugins import start_run, log_metrics, save_model")
    recho('     start_run("my_training")')


@stack.command("show")
def stack_show() -> None:
    """Show the currently configured stack.

    Displays all plugins configured in flowyml.yaml and their status.
    """
    from flowyml.plugins import validate_stack, get_config

    config = get_config()
    plugins_config = config.plugins_config

    if not plugins_config:
        recho("No stack configured. Run 'flowyml stack init' to create flowyml.yaml")
        return

    recho("\n📦 Current Stack:\n")

    validation = validate_stack()

    for role, conf in plugins_config.items():
        if isinstance(conf, dict):
            plugin_type = conf.get("type", "unknown")
            is_installed = validation.get(role, False)
            status = "✓" if is_installed else "○"

            recho(f"  {status} {role}:")
            recho(f"      type: {plugin_type}")

            # Show key config values (not sensitive ones)
            for key, value in conf.items():
                if key != "type" and "key" not in key.lower() and "secret" not in key.lower():
                    recho(f"      {key}: {value}")
            recho()

    # Show missing plugins
    missing = [role for role, installed in validation.items() if not installed]
    if missing:
        recho("⚠️  Some plugins are not installed:")
        for role in missing:
            plugin_type = plugins_config.get(role, {}).get("type")
            if plugin_type:
                recho(f"    flowyml plugin install {plugin_type}")


@stack.command("validate")
def stack_validate() -> None:
    """Validate the current stack configuration.

    Checks that all configured plugins are installed and can be initialized.
    """
    from flowyml.plugins import get_config, validate_stack

    recho("Validating stack configuration...\n")

    config = get_config()

    if not config._config_path:
        recho("[red]✗No flowyml.yaml found", err=True)
        recho("  Run 'flowyml stack init' to create one")
        return

    recho(f"Config file: {config._config_path}\n")

    validation = validate_stack()

    if not validation:
        recho("No plugins configured")
        return

    all_valid = True
    for role, is_installed in validation.items():
        status = "✓" if is_installed else "✗"
        recho(f"  {status} {role}")
        if not is_installed:
            all_valid = False

    recho()
    if all_valid:
        recho("[green]✓All plugins are installed and ready!")
    else:
        recho("[red]✗Some plugins need to be installed")
        recho("  Run 'flowyml stack show' for installation commands")


@stack.command("install")
def stack_install() -> None:
    """Install all plugins configured in flowyml.yaml."""
    from flowyml.plugins import get_config, get_manager

    config = get_config()
    plugins_config = config.plugins_config
    manager = get_manager()

    if not plugins_config:
        recho("No stack configured. Run 'flowyml stack init' first.")
        return

    recho("Installing stack plugins...\n")

    for _role, conf in plugins_config.items():
        if isinstance(conf, dict):
            plugin_type = conf.get("type")
            if plugin_type:
                if manager.is_installed(plugin_type):
                    recho(f"  ✓ {plugin_type} (already installed)")
                else:
                    recho(f"  Installing {plugin_type}...")
                    if manager.install(plugin_type):
                        recho(f"  ✓ {plugin_type} installed")
                    else:
                        recho(f"  ✗ Failed to install {plugin_type}")

    recho("\n✓ Stack installation complete!")
    recho("  Run 'flowyml stack validate' to verify the configuration")


@stack.command("list")
def list_stacks() -> None:
    """List available stacks from flowyml.yaml."""
    from flowyml.cli.rich_utils import get_console, RICH_AVAILABLE

    console = get_console()

    stacks = [
        ("local", "Local", "Default local execution", True),
    ]
    active = "local"

    # Try to get real stack info from flowyml.yaml
    try:
        from flowyml.plugins.stack_config import get_stack_manager

        sm = get_stack_manager()
        active = sm.active_stack_name
        real_stacks = sm.list_stacks()
        if real_stacks:
            stacks = []
            for sname in real_stacks:
                sc = sm.get_stack(sname)
                orch_type = (sc.orchestrator or {}).get("type", "local")
                desc = f"{orch_type} orchestrator"
                stacks.append((sname, orch_type.capitalize(), desc, sname == active))
    except Exception:
        pass

    if RICH_AVAILABLE and console:
        from rich.table import Table as RichTable
        from rich import box as rich_box

        table = RichTable(
            title="[bold cyan]🏗  Available Stacks[/bold cyan]",
            box=rich_box.ROUNDED,
            border_style="cyan",
        )
        table.add_column("Stack", style="cyan", width=16)
        table.add_column("Type", width=12)
        table.add_column("Description", width=35)
        table.add_column("Status", justify="center", width=10)

        for name, stype, desc, _ in stacks:
            is_active = name == active
            status = "[bold green]✅ Active[/]" if is_active else "[dim]—[/]"
            style = "bold green" if is_active else ""
            table.add_row(name, stype, desc, status, style=style)

        console.print(table)
    else:
        recho("Available stacks:\n")
        for name, stype, desc, _ in stacks:
            marker = " (active)" if name == active else ""
            recho(f"  {name:<16} {stype:<12} {desc}{marker}")


@stack.command("switch")
@click.argument("stack_name")
def stack_switch(stack_name: str) -> None:
    """Switch active stack.

    Examples:
        flowyml stack switch gcp-prod
        flowyml stack switch local
    """
    try:
        from flowyml.plugins.stack_config import get_stack_manager

        sm = get_stack_manager()
        available = sm.list_stacks()
        if stack_name not in available:
            recho(f"[red]✗Stack '{stack_name}' not found. Available: {', '.join(available)}")
            return
        sm.set_active_stack(stack_name)
        recho(f"[green]✓ Switched to stack '{stack_name}'")
    except Exception as e:
        recho(f"[red]✗Error switching stack: {e}", err=True)


@stack.command("info")
def stack_info() -> None:
    """Show detailed info about the active stack."""
    try:
        from flowyml.plugins.stack_config import get_stack_manager

        sm = get_stack_manager()
        active = sm.active_stack_name
        sc = sm.get_stack(active)

        recho(f"\n[bold cyan]🏗  Active Stack: {active}[/]\n")
        if sc.orchestrator:
            recho(f"  [cyan]Orchestrator:[/]  {sc.orchestrator.get('type', '—')}")
        if sc.artifact_store:
            recho(f"  [cyan]Artifact Store:[/] {sc.artifact_store.get('type', '—')}")
            if "bucket" in (sc.artifact_store or {}):
                recho(f"                     bucket={sc.artifact_store['bucket']}")
        if sc.container_registry:
            recho(f"  [cyan]Registry:[/]       {sc.container_registry.get('type', '—')}")
        if sc.model_deployer:
            recho(f"  [cyan]Deployer:[/]       {sc.model_deployer.get('type', '—')}")
        recho()
    except Exception as e:
        recho(f"[red]✗Error: {e}", err=True)


# ---------------------------------------------------------------------------
# Docker Commands
# ---------------------------------------------------------------------------


@cli.group("docker")
def docker_cli():
    """Docker image management for FlowyML pipelines.

    Build, push, and manage Docker images used for remote execution.
    """
    pass


@docker_cli.command("build")
@click.option("--tag", "-t", default=None, help="Image tag (default: content-hash)")
@click.option("--stack", "-s", default=None, help="Use Docker config from an enterprise stack")
@click.option("--push", is_flag=True, help="Push to registry after build")
@click.option("--registry", default=None, help="Target container registry URI")
@click.option("--platform", default="linux/amd64", help="Target platform")
@click.option("--gpu/--no-gpu", default=False, help="Enable GPU/CUDA support")
@click.option("--cuda", default=None, help="CUDA version (e.g. 12.4)")
@click.option(
    "--deps",
    type=click.Choice(["auto", "pip", "uv", "poetry", "conda", "pipenv"]),
    default="auto",
    help="Dependency manager",
)
@click.option("--base-image", default=None, help="Base Docker image")
@click.option("--dry-run", is_flag=True, help="Generate Dockerfile only, don't build")
@click.option("--no-cache", is_flag=True, help="Disable BuildKit cache")
@click.option("--context", default=".", help="Build context directory")
def docker_build(tag, stack, push, registry, platform, gpu, cuda, deps, base_image, dry_run, no_cache, context):
    """Build a Docker image from the current project.

    Auto-detects dependencies from requirements.txt, pyproject.toml,
    uv.lock, poetry.lock, Pipfile, environment.yml, or setup.py.

    Examples:
        flowyml docker build
        flowyml docker build --gpu --push --registry myregistry.azurecr.io
        flowyml docker build --stack aml_gpu_large --push
        flowyml docker build --deps poetry --dry-run
    """
    try:
        from flowyml.stacks.components import DockerConfig
        from flowyml.core.image_builder import DockerImageBuilder

        # Start from stack's docker config or defaults
        docker_cfg = None
        if stack:
            try:
                from flowyml.stacks.enterprise.resolver import StackResolver

                resolver = StackResolver()
                definition = resolver.resolve(stack)
                docker_cfg = definition.to_docker_config()
                recho(f"Using Docker config from stack '{stack}'")
            except Exception as e:
                recho(f"[yellow]Warning: Could not load stack '{stack}': {e}")

        if docker_cfg is None:
            docker_cfg = DockerConfig()

        # Apply CLI overrides
        docker_cfg.build_context = context
        docker_cfg.platform = platform
        if gpu:
            docker_cfg.gpu_enabled = True
        if cuda:
            docker_cfg.cuda_version = cuda
        if base_image:
            docker_cfg.base_image = base_image
        if no_cache:
            docker_cfg.cache_pip = False
        if registry:
            docker_cfg.registry_uri = registry

        # Dependency manager override
        if deps != "auto":
            docker_cfg.use_uv = deps == "uv"
            docker_cfg.use_poetry = deps == "poetry"
            docker_cfg.use_conda = deps == "conda"
            docker_cfg.use_pipenv = deps == "pipenv"

        builder = DockerImageBuilder()

        if dry_run:
            dockerfile_content = builder.generate_dockerfile(docker_cfg)
            recho("[bold]Generated Dockerfile:[/bold]")
            recho("─" * 60)
            print(dockerfile_content)
            recho("─" * 60)
            return

        # Generate tag
        image_tag = tag or builder.generate_tag(docker_cfg, base_name="flowyml")
        recho(f"Building image: [bold]{image_tag}[/bold]")

        built = builder.build_image(docker_cfg, tag=image_tag)
        recho(f"[green]✓ Built: {built}")

        if push:
            target_registry = registry or docker_cfg.registry_uri
            if not target_registry:
                recho("[red]✗ No registry specified. Use --registry <uri>")
                return
            pushed = builder.push_image(built, registry_uri=target_registry)
            recho(f"[green]✓ Pushed: {pushed}")

    except Exception as e:
        recho(f"[red]✗ Docker build failed: {e}", err=True)


@docker_cli.command("push")
@click.argument("image_tag")
@click.option("--registry", "-r", default=None, help="Target registry URI (re-tags if needed)")
def docker_push(image_tag, registry):
    """Push a Docker image to a container registry.

    Examples:
        flowyml docker push my-pipeline:abc123
        flowyml docker push my-pipeline:abc123 --registry myregistry.azurecr.io
    """
    try:
        from flowyml.core.image_builder import DockerImageBuilder

        builder = DockerImageBuilder()
        pushed = builder.push_image(image_tag, registry_uri=registry)
        recho(f"[green]✓ Pushed: {pushed}")
    except Exception as e:
        recho(f"[red]✗ Push failed: {e}", err=True)


@docker_cli.command("generate")
@click.option("--context", default=".", help="Build context directory")
@click.option("--gpu/--no-gpu", default=False, help="Enable GPU/CUDA")
@click.option("--cuda", default=None, help="CUDA version")
@click.option("--deps", type=click.Choice(["auto", "pip", "uv", "poetry", "conda", "pipenv"]), default="auto")
@click.option("--output", "-o", default=None, help="Write Dockerfile to path")
@click.option("--stack", "-s", default=None, help="Use config from enterprise stack")
def docker_generate(context, gpu, cuda, deps, output, stack):
    """Generate a Dockerfile without building.

    Useful for inspecting, customising, or debugging the auto-generated
    Dockerfile before running a build.

    Examples:
        flowyml docker generate
        flowyml docker generate --gpu --deps poetry
        flowyml docker generate -o Dockerfile.flowyml
    """
    try:
        from flowyml.stacks.components import DockerConfig
        from flowyml.core.image_builder import DockerImageBuilder

        docker_cfg = None
        if stack:
            try:
                from flowyml.stacks.enterprise.resolver import StackResolver

                resolver = StackResolver()
                definition = resolver.resolve(stack)
                docker_cfg = definition.to_docker_config()
            except Exception:
                pass

        if docker_cfg is None:
            docker_cfg = DockerConfig()

        docker_cfg.build_context = context
        if gpu:
            docker_cfg.gpu_enabled = True
        if cuda:
            docker_cfg.cuda_version = cuda
        if deps != "auto":
            docker_cfg.use_uv = deps == "uv"
            docker_cfg.use_poetry = deps == "poetry"
            docker_cfg.use_conda = deps == "conda"
            docker_cfg.use_pipenv = deps == "pipenv"

        builder = DockerImageBuilder()
        content = builder.generate_dockerfile(docker_cfg)

        if output:
            from pathlib import Path

            Path(output).write_text(content)
            recho(f"[green]✓ Dockerfile written to: {output}")
        else:
            print(content)

    except Exception as e:
        recho(f"[red]✗ Generation failed: {e}", err=True)


@docker_cli.command("inspect")
@click.option("--context", default=".", help="Project directory to inspect")
@click.option("--stack", "-s", default=None, help="Show config from enterprise stack")
def docker_inspect(context, stack):
    """Inspect the auto-detected Docker configuration.

    Shows which dependency manager, base image, and build options
    would be used for the current project.

    Examples:
        flowyml docker inspect
        flowyml docker inspect --stack aml_gpu_large
    """
    try:
        from pathlib import Path
        from flowyml.stacks.components import DockerConfig
        from flowyml.core.image_builder import DockerImageBuilder

        if stack:
            try:
                from flowyml.stacks.enterprise.resolver import StackResolver

                resolver = StackResolver()
                definition = resolver.resolve(stack)
                docker_cfg = definition.to_docker_config()
                recho(f"[bold]Docker config from stack: {stack}[/bold]")
            except Exception as e:
                recho(f"[red]✗ Could not load stack: {e}", err=True)
                return
        else:
            docker_cfg = DockerConfig(build_context=context)
            recho("[bold]Auto-detected Docker config[/bold]")

        builder = DockerImageBuilder()
        manager = builder._detect_dependency_manager(docker_cfg)
        tag_preview = builder.generate_tag(docker_cfg, base_name="preview")

        ctx = Path(docker_cfg.build_context).resolve()

        recho("")
        recho(f"  Build context    : {ctx}")
        recho(f"  Base image       : {docker_cfg.base_image}")
        recho(f"  Dep manager      : {manager}")
        recho(f"  GPU enabled      : {docker_cfg.gpu_enabled}")
        if docker_cfg.gpu_enabled and docker_cfg.cuda_version:
            recho(f"  CUDA version     : {docker_cfg.cuda_version}")
        recho(f"  Multi-stage      : {docker_cfg.multi_stage}")
        recho(f"  BuildKit cache   : {docker_cfg.cache_pip}")
        recho(f"  Platform         : {docker_cfg.platform}")
        recho(f"  Tag strategy     : {docker_cfg.tag_strategy}")
        recho(f"  Tag preview      : {tag_preview}")
        recho(f"  Auto-build       : {docker_cfg.auto_build}")
        recho(f"  Auto-push        : {docker_cfg.auto_push}")
        if docker_cfg.registry_uri:
            recho(f"  Registry         : {docker_cfg.registry_uri}")
        if docker_cfg.health_check:
            recho(f"  Health check     : {docker_cfg.health_check}")
        if docker_cfg.labels:
            recho(f"  Labels           : {docker_cfg.labels}")

        # Show detected project files
        recho("")
        recho("[bold]Detected project files:[/bold]")
        dep_files = [
            "requirements.txt",
            "pyproject.toml",
            "uv.lock",
            "poetry.lock",
            "Pipfile",
            "Pipfile.lock",
            "environment.yml",
            "conda.yaml",
            "setup.py",
            "setup.cfg",
            "Dockerfile",
        ]
        for f in dep_files:
            path = ctx / f
            if path.is_file():
                size = path.stat().st_size
                recho(f"  ✓ {f} ({size:,} bytes)")

    except Exception as e:
        recho(f"[red]✗ Inspect failed: {e}", err=True)


@docker_cli.command("login")
@click.argument("registry")
@click.option("--username", "-u", default=None, help="Registry username")
@click.option("--password-stdin", is_flag=True, help="Read password from stdin")
def docker_login(registry, username, password_stdin):
    """Login to a container registry.

    Examples:
        flowyml docker login myregistry.azurecr.io -u admin
        echo $TOKEN | flowyml docker login docker.io -u myuser --password-stdin
    """
    import subprocess as sp

    try:
        cmd = ["docker", "login", registry]
        if username:
            cmd.extend(["--username", username])
        if password_stdin:
            cmd.append("--password-stdin")

        sp.run(cmd, check=True, text=True)
        recho(f"[green]✓ Logged in to {registry}")
    except sp.CalledProcessError as e:
        recho(f"[red]✗ Login failed: {e}", err=True)
    except FileNotFoundError:
        recho("[red]✗ Docker CLI not found. Install Docker first.", err=True)


# ── Enterprise CLI Registration ──────────────────────────────────────────
# Register enterprise commands if the enterprise module is available.
# This is silent — if enterprise deps are missing, the base CLI still works.

try:
    from flowyml.cli.enterprise_cli import register_enterprise_commands

    register_enterprise_commands(cli)
except ImportError:
    pass  # Enterprise module not installed


if __name__ == "__main__":
    cli()
