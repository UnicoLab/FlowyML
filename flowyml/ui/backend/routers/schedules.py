from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from flowyml.core.scheduler import PipelineScheduler
from flowyml.registry.pipeline_registry import pipeline_registry

router = APIRouter()
# Note: In a real app, the scheduler instance should be a singleton managed by the app state
# For now, we instantiate it here, but it might not persist state across reloads if not handled carefully.
# Ideally, the scheduler is started when the backend starts.
scheduler = PipelineScheduler()
scheduler.start()  # Start the scheduler thread


class ScheduleRequest(BaseModel):
    name: str
    pipeline_name: str
    schedule_type: str  # 'daily', 'hourly', 'interval', 'cron'
    hour: int | None = 0
    minute: int | None = 0
    interval_seconds: int | None = 0
    cron_expression: str | None = None
    timezone: str = "UTC"
    project_name: str | None = None


@router.get("/")
async def list_schedules():
    """List all active schedules."""
    # Convert Schedule objects to dicts for JSON serialization
    schedules = scheduler.list_schedules()
    return [
        {
            "pipeline_name": s.pipeline_name,
            "schedule_type": s.schedule_type,
            "schedule_value": s.schedule_value,
            "enabled": s.enabled,
            "last_run": s.last_run,
            "next_run": s.next_run,
            "timezone": s.timezone,
        }
        for s in schedules
    ]


@router.get("/health")
async def get_scheduler_health():
    """Get scheduler health metrics."""
    return scheduler.health_check()


@router.post("/")
async def create_schedule(schedule: ScheduleRequest):
    """Create a new schedule."""
    # 1. Look up pipeline factory
    pipeline_factory = pipeline_registry.get(schedule.pipeline_name)

    if not pipeline_factory:
        # Try to see if it's a template
        from flowyml.core.templates import TEMPLATES, create_from_template

        if schedule.pipeline_name in TEMPLATES:
            # For templates, we need a way to instantiate them with default args or args provided in request
            # This is a simplification for the demo
            def template_wrapper():
                # Create and run template pipeline
                # Note: This assumes default args work. In reality, we'd need more config.
                p = create_from_template(schedule.pipeline_name)
                return p.run()

            pipeline_func = template_wrapper
        else:
            # Check if it's a historical pipeline (in metadata but not registry)
            # This means we can't run it because we don't have the code loaded
            from flowyml.storage.metadata import SQLiteMetadataStore

            store = SQLiteMetadataStore()
            pipelines = store.list_pipelines()

            if schedule.pipeline_name in pipelines:
                # Try to load pipeline definition
                from flowyml.storage.metadata import SQLiteMetadataStore

                store = SQLiteMetadataStore()
                pipeline_def = store.get_pipeline_definition(schedule.pipeline_name)

                if pipeline_def:
                    # Reconstruct pipeline from definition
                    from flowyml.core.pipeline import Pipeline
                    from flowyml.core.context import Context

                    def pipeline_wrapper():
                        # Reconstruct pipeline each time
                        p = Pipeline.from_definition(pipeline_def, Context())
                        return p.run()

                    pipeline_func = pipeline_wrapper
                else:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Pipeline '{schedule.pipeline_name}' found in history but no definition stored. Please run the pipeline again to enable scheduling.",
                    )
            else:
                raise HTTPException(
                    status_code=404,
                    detail=f"Pipeline '{schedule.pipeline_name}' not found in registry. Please register it using @register_pipeline.",
                )
    else:
        # Create a wrapper to instantiate and run the pipeline
        def pipeline_wrapper():
            # Instantiate fresh pipeline for each run
            p = pipeline_factory()
            return p.run()

        pipeline_func = pipeline_wrapper

    # 2. Schedule it
    try:
        if schedule.schedule_type == "daily":
            scheduler.schedule_daily(
                name=schedule.name,
                pipeline_func=pipeline_func,
                hour=schedule.hour,
                minute=schedule.minute,
                timezone=schedule.timezone,
            )
        elif schedule.schedule_type == "hourly":
            scheduler.schedule_hourly(
                name=schedule.name,
                pipeline_func=pipeline_func,
                minute=schedule.minute,
                timezone=schedule.timezone,
            )
        elif schedule.schedule_type == "interval":
            scheduler.schedule_interval(
                name=schedule.name,
                pipeline_func=pipeline_func,
                seconds=schedule.interval_seconds,
                timezone=schedule.timezone,
            )
        elif schedule.schedule_type == "cron":
            if not schedule.cron_expression:
                raise HTTPException(status_code=400, detail="Cron expression required for cron schedule")
            scheduler.schedule_cron(
                name=schedule.name,
                pipeline_func=pipeline_func,
                cron_expression=schedule.cron_expression,
                timezone=schedule.timezone,
            )
        else:
            raise HTTPException(status_code=400, detail="Invalid schedule type")

        return {"status": "success", "message": f"Scheduled '{schedule.name}'"}

    except ImportError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{schedule_name}")
async def delete_schedule(schedule_name: str):
    """Remove a schedule."""
    scheduler.unschedule(schedule_name)
    return {"status": "success", "message": f"Schedule {schedule_name} removed"}


@router.post("/{schedule_name}/enable")
async def enable_schedule(schedule_name: str):
    """Enable a schedule."""
    scheduler.enable(schedule_name)
    return {"status": "success"}


@router.post("/{schedule_name}/disable")
async def disable_schedule(schedule_name: str):
    """Disable a schedule."""
    scheduler.disable(schedule_name)
    return {"status": "success"}


@router.get("/{schedule_name}/history")
async def get_schedule_history(schedule_name: str, limit: int = 50):
    """Get execution history for a schedule."""
    return scheduler.get_history(schedule_name, limit)


@router.get("/registered-pipelines")
async def list_registered_pipelines(project: str = None):
    """List all pipelines available for scheduling."""
    from flowyml.core.templates import list_templates
    from flowyml.storage.metadata import SQLiteMetadataStore

    registered = pipeline_registry.list_pipelines()
    templates = list_templates()

    # Also get pipelines from metadata store (historical runs)
    metadata_pipelines = []
    try:
        store = SQLiteMetadataStore()
        import sqlite3

        conn = sqlite3.connect(store.db_path)
        cursor = conn.cursor()

        if project:
            cursor.execute(
                "SELECT DISTINCT pipeline_name FROM runs WHERE project = ? ORDER BY pipeline_name",
                (project,),
            )
        else:
            cursor.execute("SELECT DISTINCT pipeline_name FROM runs ORDER BY pipeline_name")

        metadata_pipelines = [row[0] for row in cursor.fetchall()]
        conn.close()
    except Exception as e:
        print(f"Failed to fetch pipelines from metadata store: {e}")

    return {
        "registered": list(registered.keys()),
        "templates": templates,
        "metadata": metadata_pipelines,
    }
