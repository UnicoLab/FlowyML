"""
Test pipeline to verify UI integration works.
"""

import pytest
import time
from flowyml import Pipeline, step, context
from flowyml.utils.config import update_config, reset_config, get_config


def test_ui_integration(tmp_path):
    """Test pipeline execution and UI integration with isolated config."""
    # Isolate test environment
    test_home = tmp_path / ".flowyml"
    update_config(
        flowyml_home=test_home,
        artifacts_dir=test_home / "artifacts",
        metadata_db=test_home / "metadata.db",
        cache_dir=test_home / "cache",
        runs_dir=test_home / "runs",
        enable_ui=False,
    )
    get_config().create_directories()

    try:
        # Define context with parameters
        ctx = context(
            learning_rate=0.001,
            epochs=5,
            batch_size=32,
        )

        # Define steps
        @step(outputs=["data/processed"])
        def load_and_preprocess():
            """Load and preprocess data."""
            time.sleep(0.1)
            return {"samples": 1000, "features": 20}

        @step(inputs=["data/processed"], outputs=["model/trained"])
        def train_model(data, learning_rate: float, epochs: int):
            """Train a model with auto-injected parameters."""
            time.sleep(0.1)
            return {"accuracy": 0.95, "loss": 0.05}

        # Create and run pipeline
        pipeline = Pipeline("ui_test_pipeline", context=ctx)
        pipeline.add_step(load_and_preprocess)
        pipeline.add_step(train_model)

        result = pipeline.run(debug=True)

        assert result.success is True
        assert "model/trained" in result.outputs
        assert result.outputs["model/trained"]["accuracy"] == 0.95
    finally:
        reset_config()
