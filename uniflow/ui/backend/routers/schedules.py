from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from uniflow.core.scheduler import PipelineScheduler
from uniflow.registry.pipeline_registry import pipeline_registry

router = APIRouter()
# Note: In a real app, the scheduler instance should be a singleton managed by the app state
# For now, we instantiate it here, but it might not persist state across reloads if not handled carefully.
# Ideally, the scheduler is started when the backend starts.
scheduler = PipelineScheduler()
scheduler.start()  # Start the scheduler thread


class ScheduleRequest(BaseModel):
    name: str
    pipeline_name: str
    schedule_type: str  # 'daily', 'hourly', 'interval'
    hour: int | None = 0
    minute: int | None = 0
    interval_seconds: int | None = 0
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
        }
        for s in schedules
    ]


@router.post("/")
async def create_schedule(schedule: ScheduleRequest):
    """Create a new schedule."""
    # 1. Look up pipeline factory
    pipeline_factory = pipeline_registry.get(schedule.pipeline_name)

    if not pipeline_factory:
        # Try to see if it's a template
        from uniflow.core.templates import TEMPLATES, create_from_template

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
            )
        elif schedule.schedule_type == "hourly":
            scheduler.schedule_hourly(
                name=schedule.name,
                pipeline_func=pipeline_func,
                minute=schedule.minute,
            )
        elif schedule.schedule_type == "interval":
            scheduler.schedule_interval(
                name=schedule.name,
                pipeline_func=pipeline_func,
                seconds=schedule.interval_seconds,
            )
        else:
            raise HTTPException(status_code=400, detail="Invalid schedule type")

        return {"status": "success", "message": f"Scheduled '{schedule.name}'"}

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


@router.get("/registered-pipelines")
async def list_registered_pipelines():
    """List all pipelines available for scheduling."""
    from uniflow.core.templates import list_templates

    registered = pipeline_registry.list_pipelines()
    templates = list_templates()

    return {
        "registered": list(registered.keys()),
        "templates": templates,
    }
