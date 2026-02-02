"""
AI Context Router - Provides comprehensive context for the AI assistant.

This endpoint aggregates run details, logs, metrics, and step code to provide
rich context for the in-browser AI assistant.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..database import get_db_session
from ..models import Run, Metric, StepLog

router = APIRouter(prefix="/api/ai", tags=["ai"])


class AIContextRequest(BaseModel):
    """Request model for AI context."""

    page_type: str  # 'run', 'pipeline', 'experiment', 'asset'
    resource_id: str  # run_id, pipeline_name, etc.
    include_logs: bool = True
    include_code: bool = True
    include_metrics: bool = True
    max_log_lines: int = 100


class AIContextResponse(BaseModel):
    """Response model with comprehensive AI context."""

    page_type: str
    resource_id: str
    summary: dict
    details: dict
    suggestions: list[str] = []


def _summarize_run(run: Run, include_logs: bool = True, include_code: bool = True, max_log_lines: int = 100) -> dict:
    """Generate a comprehensive summary of a run for AI context."""
    steps_info = []
    failed_steps = []

    if run.steps:
        for name, step_data in run.steps.items():
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
                step_summary["error"] = step_data["error"][:500]  # Truncate long errors
                failed_steps.append(name)

            # Include source code if requested
            if include_code and step_data.get("source_code"):
                step_summary["source_code"] = step_data["source_code"][:2000]  # Limit code size

            # Include inputs/outputs
            step_summary["inputs"] = step_data.get("inputs", [])[:5]
            step_summary["outputs"] = step_data.get("outputs", [])[:5]

            steps_info.append(step_summary)

    summary = {
        "run_id": str(run.run_id),
        "pipeline_name": run.pipeline_name,
        "status": run.status,
        "duration": f"{run.duration:.2f}s" if run.duration else None,
        "start_time": run.start_time.isoformat() if run.start_time else None,
        "end_time": run.end_time.isoformat() if run.end_time else None,
        "total_steps": len(steps_info),
        "successful_steps": len([s for s in steps_info if s["status"] == "success"]),
        "failed_steps": len(failed_steps),
        "cached_steps": len([s for s in steps_info if s["cached"]]),
        "steps": steps_info,
        "failed_step_names": failed_steps,
        "context_params": run.context or {},
        "environment": run.environment or {},
    }

    return summary


def _get_run_logs(run_id: str, max_lines: int = 100) -> dict:
    """Fetch recent logs for a run."""
    logs_by_step = {}

    with get_db_session() as session:
        # Fetch step logs
        step_logs = (
            session.query(StepLog)
            .filter(
                StepLog.run_id == run_id,
            )
            .order_by(StepLog.timestamp.desc())
            .limit(max_lines * 10)
            .all()
        )  # Get extra then filter

        for log in step_logs:
            step_name = log.step_name
            if step_name not in logs_by_step:
                logs_by_step[step_name] = []
            if len(logs_by_step[step_name]) < max_lines:
                logs_by_step[step_name].append(
                    {
                        "level": log.level,
                        "message": log.message[:500],  # Truncate long messages
                        "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                    },
                )

    return logs_by_step


def _get_run_metrics(run_id: str) -> list:
    """Fetch metrics for a run."""
    metrics = []

    with get_db_session() as session:
        db_metrics = (
            session.query(Metric)
            .filter(
                Metric.run_id == run_id,
            )
            .limit(50)
            .all()
        )

        for m in db_metrics:
            metrics.append(
                {
                    "name": m.name,
                    "value": m.value if isinstance(m.value, (int, float)) else str(m.value)[:100],
                    "step": m.step,
                },
            )

    return metrics


def _generate_suggestions(summary: dict) -> list[str]:
    """Generate AI-friendly suggestions based on run data."""
    suggestions = []

    if summary.get("failed_steps", 0) > 0:
        suggestions.append(f"Analyze the {summary['failed_steps']} failed step(s) and suggest fixes")

    if summary.get("cached_steps", 0) == 0 and summary.get("total_steps", 0) > 3:
        suggestions.append("Consider enabling caching for frequently-run steps")

    if summary.get("duration") and float(summary["duration"].replace("s", "")) > 300:
        suggestions.append("The run took over 5 minutes - consider optimization opportunities")

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
        with get_db_session() as session:
            run = session.query(Run).filter(Run.run_id == request.resource_id).first()

            if not run:
                raise HTTPException(status_code=404, detail="Run not found")

            # Generate comprehensive summary
            summary = _summarize_run(
                run,
                include_logs=request.include_logs,
                include_code=request.include_code,
                max_log_lines=request.max_log_lines,
            )

        # Fetch additional data outside the session
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
    raise HTTPException(status_code=400, detail=f"Unsupported page type: {request.page_type}")


@router.get("/context/run/{run_id}")
async def get_run_ai_context(
    run_id: str,
    include_logs: bool = True,
    include_code: bool = True,
    include_metrics: bool = True,
):
    """
    Convenience endpoint for getting AI context for a specific run.
    """
    return await get_ai_context(
        AIContextRequest(
            page_type="run",
            resource_id=run_id,
            include_logs=include_logs,
            include_code=include_code,
            include_metrics=include_metrics,
        ),
    )
