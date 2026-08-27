"""
AI Context Router - Provides comprehensive context for the AI assistant.

This endpoint aggregates run details, logs, metrics, and step code to provide
rich context for the in-browser AI assistant.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from ..dependencies import get_store
from ..artifact_paths import resolve_run_log_path
import json
from flowyml.utils.config import get_config

router = APIRouter(prefix="/api/ai", tags=["ai"])

#: Page types this router can build context for. Kept in one place so the
#: error message and the documented contract cannot drift apart.
SUPPORTED_PAGE_TYPES = frozenset({"run"})


class AIContextRequest(BaseModel):
    """Request model for AI context."""

    page_type: str  # 'run', 'pipeline', 'experiment', 'asset'
    resource_id: str  # run_id, pipeline_name, etc.
    include_logs: bool = True
    include_code: bool = True
    include_metrics: bool = True
    # Bounded: this drives how much log text is read into memory and returned.
    max_log_lines: int = Field(default=100, ge=1, le=5000)


class AIContextResponse(BaseModel):
    """Response model with comprehensive AI context."""

    page_type: str
    resource_id: str
    summary: dict
    details: dict
    suggestions: list[str] = []


def _summarize_run(
    run: dict,
    include_logs: bool = True,
    include_code: bool = True,
    max_log_lines: int = 100,
) -> dict:
    """Generate a comprehensive summary of a run for AI context."""
    steps_info = []
    failed_steps = []

    steps = run.get("steps", {})
    if isinstance(steps, str):
        try:
            steps = json.loads(steps)
        except Exception:
            steps = {}

    if steps:
        for name, step_data in steps.items():
            step_summary = {
                "name": name,
                "status": "success"
                if step_data.get("success")
                else ("failed" if step_data.get("error") else "pending"),
                "duration": f"{step_data.get('duration', 0):.2f}s",
                "cached": step_data.get("cached", False),
            }

            # Include error details for failed steps
            if step_data.get("error"):
                step_summary["error"] = str(step_data["error"])[:500]  # Truncate long errors
                failed_steps.append(name)

            # Include source code if requested
            if include_code and step_data.get("source_code"):
                step_summary["source_code"] = step_data["source_code"][:2000]  # Limit code size

            # Include inputs/outputs
            step_summary["inputs"] = step_data.get("inputs", [])[:5]
            step_summary["outputs"] = step_data.get("outputs", [])[:5]

            steps_info.append(step_summary)

    summary = {
        "run_id": str(run.get("run_id")),
        "pipeline_name": run.get("pipeline_name"),
        "status": run.get("status"),
        "duration": f"{run.get('duration', 0):.2f}s" if run.get("duration") else None,
        "start_time": run.get("start_time"),
        "end_time": run.get("end_time"),
        "total_steps": len(steps_info),
        "successful_steps": len([s for s in steps_info if s["status"] == "success"]),
        "failed_steps": len(failed_steps),
        "cached_steps": len([s for s in steps_info if s["cached"]]),
        "steps": steps_info,
        "failed_step_names": failed_steps,
        "context_params": run.get("context") or {},
        "environment": run.get("environment") or {},
    }

    return summary


def _get_run_logs(run_id: str, max_lines: int = 100) -> dict:
    """Fetch recent logs for a run from filesystem."""
    logs_by_step = {}
    runs_dir = get_config().runs_dir
    # Confined: run_id reaches here from a URL path parameter.
    log_dir = resolve_run_log_path(runs_dir, run_id)

    if not log_dir.exists():
        return {}

    for log_file in log_dir.glob("*.log"):
        step_name = log_file.stem
        try:
            with open(log_file) as f:
                lines = f.readlines()
                # Get last N lines
                recent_lines = lines[-max_lines:]
                logs_by_step[step_name] = [{"message": line.strip(), "level": "INFO"} for line in recent_lines]
        except Exception:
            continue

    return logs_by_step


def _get_run_metrics(run_id: str) -> list:
    """Fetch metrics for a run."""
    metrics = []
    store = get_store()

    db_metrics = store.get_metrics(run_id)
    if db_metrics:
        for m in db_metrics[:50]:
            metrics.append(
                {
                    "name": m.get("name"),
                    "value": m.get("value"),
                    "step": m.get("step"),
                },
            )

    return metrics


def _generate_suggestions(summary: dict) -> list[str]:
    """Generate AI-friendly suggestions based on run data."""
    suggestions = []

    if summary.get("failed_steps", 0) > 0:
        suggestions.append(
            f"Analyze the {summary['failed_steps']} failed step(s) and suggest fixes",
        )

    if summary.get("cached_steps", 0) == 0 and summary.get("total_steps", 0) > 3:
        suggestions.append("Consider enabling caching for frequently-run steps")

    duration_str = summary.get("duration")
    if duration_str:
        try:
            duration = float(duration_str.replace("s", ""))
            if duration > 300:
                suggestions.append(
                    "The run took over 5 minutes - consider optimization opportunities",
                )
        except (ValueError, AttributeError):
            pass

    return suggestions


@router.post("/context", response_model=AIContextResponse)
async def get_ai_context(request: AIContextRequest):
    """
    Get comprehensive AI context for a specific page/resource.

    This endpoint aggregates all relevant information that the AI assistant
    might need to provide helpful, context-aware responses.
    """
    if request.page_type == "run":
        # Fetch run data
        store = get_store()
        run = store.load_run(request.resource_id)

        if not run:
            raise HTTPException(status_code=404, detail="Run not found")

        # Generate comprehensive summary
        summary = _summarize_run(
            run,
            include_logs=request.include_logs,
            include_code=request.include_code,
            max_log_lines=request.max_log_lines,
        )

        # Fetch additional data
        details = {}

        if request.include_logs:
            details["logs"] = _get_run_logs(request.resource_id, request.max_log_lines)

        if request.include_metrics:
            details["metrics"] = _get_run_metrics(request.resource_id)

        # Generate suggestions
        suggestions = _generate_suggestions(summary)

        return AIContextResponse(
            page_type=request.page_type,
            resource_id=request.resource_id,
            summary=summary,
            details=details,
            suggestions=suggestions,
        )

    # Add more page types as needed
    raise HTTPException(
        status_code=400,
        detail=(
            f"Unsupported page type: {request.page_type}. "
            f"Supported page types: {sorted(SUPPORTED_PAGE_TYPES)}"
        ),
    )


@router.get("/context/{page_type}/{resource_id}")
async def get_resource_ai_context(
    page_type: str,
    resource_id: str,
    include_logs: bool = True,
    include_code: bool = True,
    include_metrics: bool = True,
):
    """Convenience GET form of :func:`get_ai_context`.

    Accepts any ``page_type`` so that an unsupported one yields the same
    explanatory 400 as the POST endpoint. Previously this route was hardcoded
    to ``/context/run/{run_id}``, so the UI - which builds the URL from a
    generic ``pageType`` - got an unexplained routing 404 for every other page.
    """
    return await get_ai_context(
        AIContextRequest(
            page_type=page_type,
            resource_id=resource_id,
            include_logs=include_logs,
            include_code=include_code,
            include_metrics=include_metrics,
        ),
    )
