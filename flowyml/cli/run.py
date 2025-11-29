"""Pipeline execution CLI commands."""

import importlib.util
import sys
from pathlib import Path
from typing import Any


def run_pipeline(pipeline_name: str, stack: str, context_params: dict[str, Any], debug: bool) -> dict[str, Any]:
    """Run a pipeline by name.

    Args:
        pipeline_name: Name of the pipeline to run
        stack: Stack to use for execution
        context_params: Context parameters to override
        debug: Enable debug mode

    Returns:
        Dictionary with run results
    """
    # Try to find pipeline file
    pipeline_paths = [
        Path(f"pipelines/{pipeline_name}.py"),
        Path(f"{pipeline_name}.py"),
        Path(f"pipelines/{pipeline_name}_pipeline.py"),
    ]

    pipeline_file = None
    for path in pipeline_paths:
        if path.exists():
            pipeline_file = path
            break

    if pipeline_file is None:
        raise FileNotFoundError(
            f"Pipeline '{pipeline_name}' not found. Looked in:\n" + "\n".join(f"  - {p}" for p in pipeline_paths),
        )

    # Load pipeline module
    spec = importlib.util.spec_from_file_location(pipeline_name, pipeline_file)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load pipeline from {pipeline_file}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[pipeline_name] = module
    spec.loader.exec_module(module)

    # Get pipeline
    if hasattr(module, "create_pipeline"):
        pipeline = module.create_pipeline()
    elif hasattr(module, "pipeline"):
        pipeline = module.pipeline
    else:
        raise AttributeError(
            "Pipeline module must define 'create_pipeline()' function or 'pipeline' variable",
        )

    # Override context parameters
    if context_params:
        for key, value in context_params.items():
            setattr(pipeline.context, key, value)

    # Set stack if not default
    if stack != "local":
        pipeline.set_stack(stack)

    # Run pipeline
    result = pipeline.run(debug=debug)

    return {
        "run_id": result.run_id,
        "status": result.status,
        "duration": result.duration,
        "outputs": result.outputs,
    }
