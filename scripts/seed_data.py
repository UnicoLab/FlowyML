#!/usr/bin/env python3
"""
Comprehensive seed data generator for FlowyML UI testing.
Creates realistic, interconnected pipeline runs, artifacts, metrics, and schedules.
"""

import json
import random
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from flowyml.core.project import ProjectManager  # noqa: E402

# Configuration
PROJECTS = ["ml-training", "data-pipeline", "model-serving"]
PIPELINES = {
    "training_pipeline": {
        "steps": ["load_data", "preprocess", "train_model", "evaluate", "register_model"],
        "artifacts": {
            "load_data": [("raw_dataset", "Dataset")],
            "preprocess": [("preprocessed_data", "Dataset"), ("preprocessing_stats", "Metrics")],
            "train_model": [("trained_model", "Model"), ("training_metrics", "Metrics")],
            "evaluate": [("evaluation_report", "Metrics"), ("confusion_matrix", "Metrics")],
            "register_model": [("model_metadata", "Metadata")],
        },
    },
    "etl_pipeline": {
        "steps": ["extract", "transform", "load", "validate"],
        "artifacts": {
            "extract": [("raw_data", "Dataset")],
            "transform": [("transformed_data", "Dataset"), ("transform_stats", "Metrics")],
            "load": [("loaded_data", "Dataset")],
            "validate": [("validation_report", "Metrics")],
        },
    },
    "inference_pipeline": {
        "steps": ["load_model", "preprocess_input", "predict", "postprocess"],
        "artifacts": {
            "load_model": [("model", "Model")],
            "preprocess_input": [("processed_input", "Dataset")],
            "predict": [("predictions", "Dataset"), ("prediction_metrics", "Metrics")],
            "postprocess": [("final_output", "Dataset")],
        },
    },
}

ORCHESTRATORS = ["local", "vertex_ai", "sagemaker", "azure_ml"]
STATUSES = ["completed", "failed", "running"]


def reset_database(db_path=".flowyml/metadata.db"):
    """Remove existing database to start fresh."""
    db_file = Path(db_path)
    if db_file.exists():
        db_file.unlink()
        print(f"✅ Removed existing database: {db_path}")
    db_file.parent.mkdir(parents=True, exist_ok=True)


def generate_run_id():
    """Generate a realistic run ID."""
    return f"run_{uuid.uuid4().hex[:16]}"


def generate_artifact_id():
    """Generate a realistic artifact ID."""
    return f"artifact_{uuid.uuid4().hex[:16]}"


def create_seed_data():
    """Create comprehensive seed data."""
    print("\n🌱 Creating Seed Data for FlowyML UI\n")
    print("=" * 60)

    # Reset database
    reset_database()

    # Initialize project manager
    project_manager = ProjectManager()

    # Create projects
    print("\n📁 Creating Projects...")
    project_stores = {}
    for project_name in PROJECTS:
        project = project_manager.create_project(project_name)
        project_stores[project_name] = project.metadata_store
        print(f"   ✓ {project_name}")

    # Generate runs and artifacts
    total_runs = 0
    total_artifacts = 0

    print("\n🔄 Creating Pipeline Runs...")

    for project_name in PROJECTS:
        project_store = project_stores[project_name]

        # Create 20-30 runs per project
        num_runs = random.randint(20, 30)

        for _ in range(num_runs):
            pipeline_name = random.choice(list(PIPELINES.keys()))
            pipeline_config = PIPELINES[pipeline_name]

            run_id = generate_run_id()
            status = random.choices(STATUSES, weights=[70, 20, 10])[0]  # 70% completed, 20% failed, 10% running

            # Generate timestamps
            base_date = datetime.now() - timedelta(days=random.randint(0, 30))
            start_time = base_date.isoformat()

            if status != "running":
                duration = random.uniform(10, 600)  # 10s to 10min
                end_time = (base_date + timedelta(seconds=duration)).isoformat()
            else:
                duration = None
                end_time = None

            # Generate orchestrator metadata
            orchestrator_type = random.choice(ORCHESTRATORS)

            # Build step metadata
            steps_metadata = {}
            for step_name in pipeline_config["steps"]:
                step_success = status == "completed" or (status == "running" and random.random() > 0.3)
                step_duration = random.uniform(1, 100)

                steps_metadata[step_name] = {
                    "success": step_success,
                    "cached": random.random() < 0.3,  # 30% cache hit rate
                    "duration": step_duration,
                    "inputs": [],
                    "outputs": [f"{step_name}_output"],
                    "error": None if step_success else "Step execution failed",
                }

            # Create DAG structure
            dag = {}
            for idx, step_name in enumerate(pipeline_config["steps"]):
                dag[step_name] = {
                    "dependencies": [pipeline_config["steps"][idx - 1]] if idx > 0 else [],
                }

            # Save run
            run_metadata = {
                "run_id": run_id,
                "pipeline_name": pipeline_name,
                "status": status,
                "start_time": start_time,
                "end_time": end_time,
                "duration": duration,
                "project": project_name,
                "metadata": json.dumps(
                    {
                        "orchestrator_type": orchestrator_type,
                        "steps": steps_metadata,
                        "dag": dag,
                        "version": f"v{random.randint(1, 5)}.{random.randint(0, 9)}.{random.randint(0, 9)}",
                    },
                ),
            }

            project_store.save_run(run_id, run_metadata)
            total_runs += 1

            # Create artifacts for this run
            if status == "completed":
                for step_name, artifact_list in pipeline_config.get("artifacts", {}).items():
                    for artifact_name, artifact_type in artifact_list:
                        artifact_id = generate_artifact_id()

                        artifact_metadata = {
                            "artifact_id": artifact_id,
                            "name": artifact_name,
                            "type": artifact_type,
                            "run_id": run_id,
                            "step": step_name,
                            "pipeline_name": pipeline_name,
                            "project": project_name,
                            "created_at": start_time,
                            "size_bytes": random.randint(1024, 1024 * 1024 * 100),  # 1KB to 100MB
                            "properties": json.dumps(
                                {
                                    "format": random.choice(["parquet", "pkl", "json", "csv"]),
                                    "schema_version": f"v{random.randint(1, 3)}",
                                    "rows": random.randint(1000, 1000000) if artifact_type == "Dataset" else None,
                                },
                            ),
                        }

                        project_store.save_artifact(artifact_id, artifact_metadata)
                        total_artifacts += 1

    # Create model metrics for leaderboard
    print("\n📊 Creating Model Metrics...")
    metrics_count = 0

    for project_name in ["ml-training", "model-serving"]:
        project_store = project_stores[project_name]

        # Create metrics for 5-10 models
        num_models = random.randint(5, 10)

        for i in range(num_models):
            model_name = f"model_{chr(65+i).lower()}_v{random.randint(1,5)}"

            # Create 3-5 metric entries per model (different timestamps)
            for _ in range(random.randint(3, 5)):
                metrics = {
                    "accuracy": random.uniform(0.75, 0.99),
                    "precision": random.uniform(0.70, 0.95),
                    "recall": random.uniform(0.65, 0.95),
                    "f1_score": random.uniform(0.70, 0.93),
                    "latency_ms": random.uniform(10, 500),
                }

                project_store.log_model_metrics(
                    project=project_name,
                    model_name=model_name,
                    metrics=metrics,
                    run_id=None,
                    environment=random.choice(["production", "staging", "dev"]),
                    tags={"version": f"v{random.randint(1, 5)}", "experiment": f"exp_{random.randint(1, 20)}"},
                )
                metrics_count += 1

    # Create experiments
    print("\n🧪 Creating Experiments...")
    experiments_count = 0

    experiment_names = [
        "baseline_model",
        "optimized_model",
        "ensemble_approach",
        "feature_engineering_v1",
        "hyperparameter_tuning",
        "model_comparison",
        "data_augmentation",
        "transfer_learning",
        "neural_architecture_search",
    ]

    for project_name in PROJECTS:
        project_store = project_stores[project_name]

        # Create 3-5 experiments per project
        num_experiments = random.randint(3, 5)

        for i in range(num_experiments):
            exp_name = random.choice(experiment_names)
            experiment_id = f"exp_{uuid.uuid4().hex[:12]}"

            # Create experiment with metadata
            project_store.save_experiment(
                experiment_id=experiment_id,
                name=f"{exp_name}_{i+1}",
                description=f"Experiment testing {exp_name} approach for {project_name}",
                tags={
                    "project": project_name,
                    "type": random.choice(["model_training", "feature_engineering", "hyperparameter_tuning"]),
                    "status": random.choice(["completed", "running", "failed"]),
                    "created_by": random.choice(["alice", "bob", "charlie"]),
                    "framework": random.choice(["pytorch", "tensorflow", "scikit-learn"]),
                },
            )
            experiments_count += 1

    # Summary
    print("\n" + "=" * 60)
    print("✅ Seed Data Created Successfully!")
    print("=" * 60)
    print("\n📊 Summary:")
    print(f"   Projects:    {len(PROJECTS)}")
    print(f"   Runs:        {total_runs}")
    print(f"   Artifacts:   {total_artifacts}")
    print(f"   Metrics:     {metrics_count}")
    print(f"   Experiments: {experiments_count}")
    print("\n💡 Distribution:")
    print(f"   Pipelines: {', '.join(PIPELINES.keys())}")
    print("   Statuses:  ~70% completed, ~20% failed, ~10% running")
    print("   Cache:     ~30% cached steps")
    print("\n🚀 Start the UI with: make ui-dev")
    print("   Then navigate to:")
    print("   - Projects: http://localhost:3000/projects")
    print("   - Runs: http://localhost:3000/runs")
    print("   - Assets: http://localhost:3000/assets")
    print("   - Experiments: http://localhost:3000/experiments")
    print("   - Observability: http://localhost:3000/observability")
    print()


if __name__ == "__main__":
    create_seed_data()
