"""Model Explorer API for interactive model testing."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime
from uuid import uuid4

router = APIRouter(prefix="/explorer", tags=["model-explorer"])


# ==================== Schemas ====================


class InputFieldSchema(BaseModel):
    """Schema for a single input field."""

    name: str
    type: str  # noqa: A003  # number, integer, string, boolean, array, object
    description: Optional[str] = None
    default: Optional[Any] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    step: Optional[float] = None
    enum: Optional[list[Any]] = None  # For categorical inputs
    required: bool = True


class ModelSchema(BaseModel):
    """Schema describing model inputs and outputs."""

    model_id: str
    model_name: str
    model_type: str
    inputs: list[InputFieldSchema]
    outputs: list[InputFieldSchema]
    example_input: Optional[dict] = None
    example_output: Optional[dict] = None


class PredictionRequest(BaseModel):
    """Request for a single prediction."""

    deployment_id: Optional[str] = None
    model_artifact_id: Optional[str] = None
    inputs: dict[str, Any]


class PredictionResult(BaseModel):
    """Result of a single prediction."""

    id: str  # noqa: A003
    inputs: dict[str, Any]
    outputs: dict[str, Any]
    latency_ms: float
    timestamp: str


class SweepRequest(BaseModel):
    """Request for parameter sweep."""

    deployment_id: Optional[str] = None
    model_artifact_id: Optional[str] = None
    base_inputs: dict[str, Any]
    sweep_param: str
    sweep_values: list[Any]


class SweepResult(BaseModel):
    """Result of parameter sweep."""

    id: str  # noqa: A003
    sweep_param: str
    results: list[dict]  # [{input_value, outputs, latency_ms}]
    total_latency_ms: float
    timestamp: str


class ExplorationSession(BaseModel):
    """An exploration session with prediction history."""

    id: str  # noqa: A003
    model_id: str
    model_name: str
    created_at: str
    predictions: list[PredictionResult]
    sweeps: list[SweepResult]


# ==================== In-Memory State ====================

_sessions: dict[str, dict] = {}


# ==================== Endpoints ====================


@router.get("/schema/{model_id}")
async def get_model_schema(model_id: str) -> ModelSchema:
    """Get the input/output schema for a model.

    This introspects the model to determine its expected inputs and outputs.
    """
    # TODO: Actually introspect the model
    # For MVP, return mock schema based on common patterns

    # Try to determine model type from artifacts
    from flowyml.ui.backend.dependencies import get_store

    store = get_store()

    try:
        artifacts = store.list_artifacts()
        model_artifact = next(
            (a for a in artifacts if a.get("artifact_id") == model_id),
            None,
        )

        if not model_artifact:
            raise HTTPException(status_code=404, detail="Model not found")

        model_type = model_artifact.get("asset_type", "unknown")
        model_name = model_artifact.get("name", "Unknown Model")

    except StopIteration:
        raise HTTPException(status_code=404, detail="Model not found")
    except Exception:
        model_type = "unknown"
        model_name = "Unknown Model"

    # Generate schema based on model type
    # In production, this would introspect the actual model
    inputs = _infer_input_schema(model_type)
    outputs = _infer_output_schema(model_type)

    return ModelSchema(
        model_id=model_id,
        model_name=model_name,
        model_type=model_type,
        inputs=inputs,
        outputs=outputs,
        example_input=_generate_example_input(inputs),
        example_output=_generate_example_output(outputs),
    )


@router.post("/predict")
async def predict(request: PredictionRequest) -> PredictionResult:
    """Run a prediction with the given inputs."""
    import time

    # Validate we have either deployment or model artifact
    if not request.deployment_id and not request.model_artifact_id:
        raise HTTPException(
            status_code=400,
            detail="Either deployment_id or model_artifact_id required",
        )

    start = time.time()
    prediction_id = str(uuid4())

    # Try real prediction if we have a deployment_id
    if request.deployment_id:
        try:
            from flowyml.serving.model_server import predict as model_predict, get_server

            server = get_server(request.deployment_id)
            if server is not None:
                # Use real model prediction
                import asyncio

                loop = asyncio.get_event_loop()
                outputs = await loop.run_in_executor(
                    None,
                    lambda: model_predict(request.deployment_id, request.inputs),
                )
                latency = (time.time() - start) * 1000

                result = PredictionResult(
                    id=prediction_id,
                    inputs=request.inputs,
                    outputs=outputs,
                    latency_ms=latency,
                    timestamp=datetime.now().isoformat(),
                )

                # Store in session
                session_id = request.deployment_id
                if session_id in _sessions:
                    _sessions[session_id]["predictions"].append(result.model_dump())

                return result
        except Exception as e:
            # Return error with details instead of falling back to mock
            raise HTTPException(
                status_code=500,
                detail=f"Prediction failed for deployment {request.deployment_id}: {str(e)}",
            )

    # Try direct model loading for artifact
    if request.model_artifact_id:
        try:
            from flowyml.serving.model_server import load_and_predict
            import asyncio

            loop = asyncio.get_event_loop()
            outputs, _ = await loop.run_in_executor(
                None,
                lambda: load_and_predict(request.model_artifact_id, request.inputs),
            )
            latency = (time.time() - start) * 1000

            result = PredictionResult(
                id=prediction_id,
                inputs=request.inputs,
                outputs=outputs,
                latency_ms=latency,
                timestamp=datetime.now().isoformat(),
            )

            session_id = request.model_artifact_id
            if session_id in _sessions:
                _sessions[session_id]["predictions"].append(result.model_dump())

            return result
        except Exception as e:
            # Return error with details
            raise HTTPException(
                status_code=500,
                detail=f"Prediction failed for artifact {request.model_artifact_id}: {str(e)}",
            )

    # No deployment or artifact - return helpful error
    raise HTTPException(
        status_code=400,
        detail="Either deployment_id or model_artifact_id required, and must be running",
    )


@router.post("/sweep")
async def parameter_sweep(request: SweepRequest) -> SweepResult:
    """Run a parameter sweep over a range of values."""
    import time

    if not request.deployment_id and not request.model_artifact_id:
        raise HTTPException(
            status_code=400,
            detail="Either deployment_id or model_artifact_id required",
        )

    sweep_id = str(uuid4())
    results = []
    total_start = time.time()

    for value in request.sweep_values:
        start = time.time()

        # Create input with swept parameter
        inputs = request.base_inputs.copy()
        inputs[request.sweep_param] = value

        # Run prediction
        outputs = _mock_predict(inputs)
        latency = (time.time() - start) * 1000

        results.append(
            {
                "input_value": value,
                "outputs": outputs,
                "latency_ms": latency,
            },
        )

    total_latency = (time.time() - total_start) * 1000

    sweep_result = SweepResult(
        id=sweep_id,
        sweep_param=request.sweep_param,
        results=results,
        total_latency_ms=total_latency,
        timestamp=datetime.now().isoformat(),
    )

    # Store in session
    session_id = request.deployment_id or request.model_artifact_id
    if session_id in _sessions:
        _sessions[session_id]["sweeps"].append(sweep_result.model_dump())

    return sweep_result


@router.get("/sessions")
async def list_sessions() -> list[dict]:
    """List all exploration sessions."""
    return [
        {
            "id": s["id"],
            "model_id": s["model_id"],
            "model_name": s["model_name"],
            "created_at": s["created_at"],
            "prediction_count": len(s["predictions"]),
            "sweep_count": len(s["sweeps"]),
        }
        for s in _sessions.values()
    ]


@router.post("/sessions")
async def create_session(
    model_id: str,
    model_name: str = "Model",
) -> dict:
    """Create a new exploration session."""
    session_id = str(uuid4())

    session = {
        "id": session_id,
        "model_id": model_id,
        "model_name": model_name,
        "created_at": datetime.now().isoformat(),
        "predictions": [],
        "sweeps": [],
    }

    _sessions[session_id] = session

    return {"session_id": session_id}


@router.get("/sessions/{session_id}")
async def get_session(session_id: str) -> ExplorationSession:
    """Get exploration session details."""
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = _sessions[session_id]
    return ExplorationSession(
        id=session["id"],
        model_id=session["model_id"],
        model_name=session["model_name"],
        created_at=session["created_at"],
        predictions=[PredictionResult(**p) for p in session["predictions"]],
        sweeps=[SweepResult(**s) for s in session["sweeps"]],
    )


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str) -> dict:
    """Delete an exploration session."""
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    del _sessions[session_id]
    return {"status": "deleted", "session_id": session_id}


# ==================== Helper Functions ====================


def _infer_input_schema(model_type: str) -> list[InputFieldSchema]:
    """Infer input schema based on model type."""
    # Common ML model input patterns
    if model_type.lower() in ("keras_model", "tensorflow"):
        return [
            InputFieldSchema(
                name="feature_1",
                type="number",
                description="First input feature",
                min_value=0,
                max_value=100,
                step=0.1,
                default=50.0,
            ),
            InputFieldSchema(
                name="feature_2",
                type="number",
                description="Second input feature",
                min_value=0,
                max_value=100,
                step=0.1,
                default=50.0,
            ),
            InputFieldSchema(
                name="feature_3",
                type="number",
                description="Third input feature",
                min_value=0,
                max_value=100,
                step=0.1,
                default=50.0,
            ),
        ]
    elif model_type.lower() in ("sklearn_model", "scikit-learn"):
        return [
            InputFieldSchema(
                name="X",
                type="array",
                description="Feature array",
                default=[[0.5, 0.5, 0.5]],
            ),
        ]
    else:
        # Generic schema
        return [
            InputFieldSchema(
                name="input",
                type="object",
                description="Model input",
                default={},
            ),
        ]


def _infer_output_schema(model_type: str) -> list[InputFieldSchema]:
    """Infer output schema based on model type."""
    if model_type.lower() in ("keras_model", "tensorflow", "sklearn_model"):
        return [
            InputFieldSchema(
                name="prediction",
                type="number",
                description="Predicted value",
            ),
            InputFieldSchema(
                name="confidence",
                type="number",
                description="Prediction confidence",
                min_value=0,
                max_value=1,
            ),
        ]
    else:
        return [
            InputFieldSchema(
                name="output",
                type="object",
                description="Model output",
            ),
        ]


def _generate_example_input(inputs: list[InputFieldSchema]) -> dict:
    """Generate example input based on schema."""
    example = {}
    for field in inputs:
        if field.default is not None:
            example[field.name] = field.default
        elif field.type == "number":
            example[field.name] = (field.min_value or 0) + ((field.max_value or 100) - (field.min_value or 0)) / 2
        elif field.type == "integer":
            example[field.name] = int((field.min_value or 0) + ((field.max_value or 100) - (field.min_value or 0)) / 2)
        elif field.type == "string":
            example[field.name] = ""
        elif field.type == "boolean":
            example[field.name] = False
        elif field.type == "array":
            example[field.name] = []
        else:
            example[field.name] = {}
    return example


def _generate_example_output(outputs: list[InputFieldSchema]) -> dict:
    """Generate example output based on schema."""
    example = {}
    for field in outputs:
        if field.type == "number":
            example[field.name] = 0.5
        elif field.type == "integer":
            example[field.name] = 0
        elif field.type == "string":
            example[field.name] = "result"
        elif field.type == "boolean":
            example[field.name] = True
        elif field.type == "array":
            example[field.name] = []
        else:
            example[field.name] = {}
    return example


def _mock_predict(inputs: dict) -> dict:
    """Mock prediction for testing."""
    import random

    # Simple mock: sum numeric inputs and add noise
    numeric_sum = 0
    for value in inputs.values():
        if isinstance(value, (int, float)):
            numeric_sum += value
        elif isinstance(value, list):
            for v in value:
                if isinstance(v, (int, float)):
                    numeric_sum += v
                elif isinstance(v, list):
                    numeric_sum += sum(x for x in v if isinstance(x, (int, float)))

    # Add some randomness to simulate model behavior
    prediction = numeric_sum * 0.1 + random.uniform(-0.1, 0.1)
    confidence = 0.7 + random.uniform(0, 0.25)

    return {
        "prediction": round(prediction, 4),
        "confidence": round(min(confidence, 1.0), 4),
        "class": "positive" if prediction > 0 else "negative",
    }


@router.get("/model-info/{deployment_id}")
async def get_model_info(deployment_id: str) -> dict:
    """Get real model information by introspecting the loaded model.

    This returns actual input/output specs from the deployed model,
    which the frontend can use to format inputs correctly.
    """
    try:
        from flowyml.serving.model_server import get_server
        from flowyml.utils.model_introspection import introspect_model

        server = get_server(deployment_id)

        # Check if we have a real server with a model
        if server and server.model is not None:
            # Use the shared utility to introspect the model
            info = introspect_model(server.model, server.framework)

            # Add deployment-specific metadata
            info.update(
                {
                    "deployment_id": deployment_id,
                    "model_path": server.model_path,
                    "started_at": server.started_at.isoformat() if server.started_at else None,
                },
            )

            return info

    except Exception:
        pass  # Fall through to mock info

    # Mock/Default info for non-running deployments (e.g. on-demand only)
    return {
        "deployment_id": deployment_id,
        "framework": "keras",  # Assume keras/tf for now as likely default
        "input_features": 10,
        "input_shape": [None, 10],
        "output_shape": [None, 1],
        "mock": True,
        "note": "Model server not running - showing expected schema",
    }


@router.get("/logs/{deployment_id}")
async def get_deployment_logs(deployment_id: str, lines: int = 100) -> dict:
    """Get logs from a deployed model server.

    Returns recent log entries for debugging and monitoring.
    """
    from datetime import datetime

    try:
        from flowyml.serving.model_server import get_server_logs, get_server

        server = get_server(deployment_id)
        if server:
            logs = get_server_logs(deployment_id, lines)
            return {
                "deployment_id": deployment_id,
                "log_count": len(logs),
                "logs": logs,
            }
    except Exception:
        pass  # Fall through to mock logs

    # Return informative mock logs for deployments without running servers
    mock_logs = [
        {
            "timestamp": datetime.now().isoformat(),
            "level": "INFO",
            "message": f"Model Explorer session started for deployment: {deployment_id}",
        },
        {
            "timestamp": datetime.now().isoformat(),
            "level": "INFO",
            "message": "No dedicated model server running - predictions use on-demand inference",
        },
        {
            "timestamp": datetime.now().isoformat(),
            "level": "INFO",
            "message": "Tip: Deploy model to see live server logs",
        },
    ]

    return {
        "deployment_id": deployment_id,
        "log_count": len(mock_logs),
        "logs": mock_logs,
        "mock": True,
    }
