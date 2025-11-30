import pytest
from flowyml.core.pipeline import Pipeline
from flowyml.core.step import step
from flowyml.core.orchestrator import LocalOrchestrator


@step(outputs=["msg"])
def step_one() -> str:
    return "hello"


@step
def step_two(msg: str) -> str:
    return f"{msg} world"


def test_local_orchestrator_execution():
    """Test that LocalOrchestrator executes a simple pipeline correctly."""
    pipeline = Pipeline("test_orchestrator_pipeline")
    pipeline.add_step(step_one)
    pipeline.add_step(step_two)

    # Manually run with orchestrator
    orchestrator = LocalOrchestrator()

    # We need to simulate what Pipeline.run does before calling orchestrator
    # But for this test, we can just call pipeline.run() which now uses the orchestrator internally
    # This verifies the integration.

    result = pipeline.run()

    if not result.success:
        print(f"Pipeline failed. State: {result.state}")
        for name, res in result.step_results.items():
            print(f"Step {name}: success={res.success}, error={res.error}")

    assert result.success
    assert result.outputs["step_two"] == "hello world"
    assert result.step_results["step_one"].success
    assert result.step_results["step_two"].success


def test_orchestrator_direct_call():
    """Test calling orchestrator directly."""
    pipeline = Pipeline("test_direct_orchestrator")
    pipeline.add_step(step_one)

    orchestrator = LocalOrchestrator()
    import uuid

    run_id = str(uuid.uuid4())

    # We need to ensure pipeline is built
    pipeline.build()

    result = orchestrator.run_pipeline(pipeline, run_id=run_id)

    assert result.success
    assert result.outputs["step_one"] == "hello"
