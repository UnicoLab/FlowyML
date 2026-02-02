"""
Test experiments tracking.
"""
import pytest
from flowyml.tracking.experiment import Experiment
from flowyml.storage.metadata import SQLiteMetadataStore
from datetime import datetime


def test_experiments_tracking(tmp_path):
    """Test experiment tracking with a temporary database."""
    # Isolate test environment
    test_home = tmp_path / ".flowyml"
    from flowyml.utils.config import update_config, reset_config, get_config

    update_config(
        flowyml_home=test_home,
        artifacts_dir=test_home / "artifacts",
        metadata_db=test_home / "metadata.db",
        experiments_dir=test_home / "experiments",
        enable_ui=False,
    )
    get_config().create_directories()

    try:
        from flowyml.storage.sql import SQLMetadataStore

        store = SQLMetadataStore(db_path=str(test_home / "metadata.db"))

        # 1. Create Experiment
        exp_name = f"test_experiment_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        exp = Experiment(
            name=exp_name,
            description="Testing experiment tracking integration",
            tags={"framework": "flowyml", "test": "true"},
            metadata_store=store,
        )

        # 2. Log Runs
        run_ids = [
            f"run_alpha_{datetime.now().strftime('%H%M%S')}",
            f"run_beta_{datetime.now().strftime('%H%M%S')}",
        ]

        # Create dummy runs in DB first
        for run_id in run_ids:
            store.save_run(
                run_id,
                {
                    "run_id": run_id,
                    "pipeline_name": "test_pipeline",
                    "status": "completed",
                    "start_time": datetime.now().isoformat(),
                    "duration": 1.0,
                    "success": True,
                },
            )

        # Log to experiment
        exp.log_run(run_ids[0], metrics={"accuracy": 0.85, "loss": 0.15}, parameters={"lr": 0.01})
        exp.log_run(run_ids[1], metrics={"accuracy": 0.92, "loss": 0.08}, parameters={"lr": 0.001})

        # Verify experiment data
        saved_exp = store.get_experiment(exp_name)
        assert saved_exp is not None
        assert saved_exp["name"] == exp_name

        # Verify runs in experiment
        runs = store.list_experiment_runs(exp_name)
        assert len(runs) == 2
        ids = [r["run_id"] for r in runs]
        assert run_ids[0] in ids
        assert run_ids[1] in ids
    finally:
        reset_config()
