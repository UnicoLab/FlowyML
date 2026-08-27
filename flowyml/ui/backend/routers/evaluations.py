"""FlowyML Evaluations — FastAPI Router.

REST API endpoints for managing evaluations, viewing results,
comparing runs, and listing available scorers.
"""

import logging

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/evaluations", tags=["evaluations"])

#: Upper bound on any client-supplied page size. Without it a request such as
#: `?limit=100000000` makes the server materialise an unbounded result set.
MAX_PAGE_SIZE = 1000



# ─── Request/Response Models ─────────────────────────────────────────


class EvalRunRequest(BaseModel):
    """Request body for starting an evaluation run."""

    data: list[dict] | dict = Field(..., description="Evaluation data")
    scorers: list[str] = Field(..., description="List of scorer names")
    experiment: str | None = Field(None, description="Experiment name")
    threshold: float | None = Field(None, description="Pass/fail threshold")
    dataset_name: str | None = Field(None, description="Dataset name")


class ScoreItem(BaseModel):
    """A single score from evaluation."""

    name: str
    value: float | str | bool
    rationale: str | None = None
    passed: bool | None = None


class EvalResultResponse(BaseModel):
    """Response body for evaluation results."""

    eval_id: str
    experiment: str | None = None
    summary: dict[str, float] = {}
    passed: bool = True
    pass_rate: float = 1.0
    dataset_name: str | None = None
    created_at: str = ""
    scorer_count: int = 0


class ScorerInfo(BaseModel):
    """Information about an available scorer."""

    name: str
    scorer_type: str = Field(alias="type")
    description: str
    cls: str = Field(alias="class", default="")

    model_config = ConfigDict(populate_by_name=True)


class CompareRequest(BaseModel):
    """Request body for comparing evaluations."""

    eval_ids: list[str] = Field(..., min_length=2, description="Eval IDs to compare")
    threshold: float = Field(0.05, description="Regression threshold")


# ─── Endpoints ────────────────────────────────────────────────────────


@router.post("/run", response_model=EvalResultResponse)
async def run_evaluation(request: EvalRunRequest):
    """Run an evaluation with specified scorers.

    Accepts evaluation data and a list of scorer names, runs the evaluation,
    and returns aggregated results.
    """
    from flowyml.evals import evaluate, EvalDataset, get_scorer

    # Build scorers
    scorer_list = []
    for s_name in request.scorers:
        try:
            scorer = get_scorer(s_name, threshold=request.threshold)
            scorer_list.append(scorer)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    # Build dataset
    if isinstance(request.data, list):
        eval_ds = EvalDataset.create_genai(
            name=request.dataset_name or "api_dataset",
            examples=request.data,
        )
    else:
        eval_ds = EvalDataset(
            name=request.dataset_name or "api_dataset",
            data=request.data,
        )

    # Run evaluation
    try:
        result = evaluate(
            data=eval_ds,
            scorers=scorer_list,
            experiment=request.experiment,
            store=True,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {e}")

    return EvalResultResponse(
        eval_id=result.eval_id,
        experiment=result.experiment,
        summary=result.summary,
        passed=result.passed,
        pass_rate=result.pass_rate,
        dataset_name=result.dataset_name,
        created_at=result.created_at,
        scorer_count=len(scorer_list),
    )


@router.get("/results/{eval_id}")
async def get_eval_result(eval_id: str):
    """Get detailed results for an evaluation run."""
    try:
        from flowyml.storage.sql import SQLMetadataStore

        store = SQLMetadataStore()
        run = store.load_run(eval_id)
        if not run:
            raise HTTPException(status_code=404, detail=f"Evaluation '{eval_id}' not found")
        return run
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def list_evaluations(
    experiment: str | None = Query(None, description="Filter by experiment"),
    limit: int = Query(20, ge=1, le=MAX_PAGE_SIZE, description="Max results"),
):
    """List recent evaluation runs."""
    try:
        from flowyml.storage.sql import SQLMetadataStore

        store = SQLMetadataStore()
        runs = store.list_runs(limit=limit * 3)  # Fetch more to filter

        eval_runs = [r for r in runs if r.get("tags", {}).get("type") == "evaluation"]
        if experiment:
            eval_runs = [r for r in eval_runs if experiment in r.get("pipeline_name", "")]

        return {"evaluations": eval_runs[:limit], "total": len(eval_runs)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compare")
async def compare_evaluations(request: CompareRequest):
    """Compare two or more evaluation runs."""
    try:
        from flowyml.storage.sql import SQLMetadataStore

        store = SQLMetadataStore()
        runs = {}
        for eid in request.eval_ids:
            run = store.load_run(eid)
            if run:
                runs[eid] = run
            else:
                raise HTTPException(status_code=404, detail=f"Evaluation '{eid}' not found")

        # Build comparison
        all_metrics = set()
        for run in runs.values():
            all_metrics.update(run.get("metrics", {}).keys())

        comparison = {"eval_ids": request.eval_ids, "metrics": {}}

        for metric in sorted(all_metrics):
            values = {}
            for eid, run in runs.items():
                values[eid] = run.get("metrics", {}).get(metric)
            comparison["metrics"][metric] = values

        return comparison
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scorers", response_model=list[ScorerInfo])
async def get_available_scorers(
    scorer_type: str | None = Query(None, description="Filter by type"),
):
    """List all available scorers."""
    from flowyml.evals.scorers import list_scorers

    return list_scorers(scorer_type)
