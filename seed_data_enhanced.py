"""
Enhanced seed data script for FlowyML.
Creates comprehensive, fully-connected demo data with:
- Multiple projects
- Pipelines with complete DAGs
- Runs with steps and artifacts
- Experiments linking runs
- Model metrics and traces
"""
import json
import random
import uuid
from datetime import datetime, timedelta
from flowyml.core.project import ProjectManager
from flowyml.storage.metadata import SQLiteMetadataStore
import sqlite3


def seed_data():
    print("🌱 Seeding database with enhanced demo data...")

    # Initialize stores
    pm = ProjectManager()
    store = SQLiteMetadataStore()

    # Clear existing demo data
    for project_name in ["demo-ml-project", "demo-data-pipeline", "demo-deployment"]:
        try:
            pm.delete_project(project_name, confirm=True)
            print(f"Cleared existing project: {project_name}")
        except Exception:
            pass

    # ========== PROJECT 1: ML Training Project ==========
    print("\n📦 Creating ML Training Project...")
    ml_project = pm.create_project(
        "demo-ml-project",
        description="Machine learning model training and evaluation workflows",
    )

    # Create pipelines
    ml_pipelines = ["model-training", "model-evaluation", "hyperparameter-tuning"]
    for pipeline_name in ml_pipelines:
        ml_project.create_pipeline(pipeline_name)

    # Generate Model Training Runs with full artifacts
    print("  Creating model training runs...")
    for i in range(6):
        run_id = str(uuid.uuid4())
        status = "completed" if i < 5 else "failed"
        start_time = datetime.now() - timedelta(days=random.randint(0, 7))
        duration = random.uniform(300, 1200)
        end_time = start_time + timedelta(seconds=duration)

        # Training configuration
        learning_rate = random.choice([0.001, 0.01, 0.0001])
        batch_size = random.choice([16, 32, 64])
        epochs = random.randint(10, 50)

        # Generate realistic training metrics
        final_accuracy = random.uniform(0.85, 0.95) if status == "completed" else random.uniform(0.5, 0.7)
        final_loss = random.uniform(0.05, 0.15) if status == "completed" else random.uniform(0.3, 0.8)

        metadata = {
            "run_id": run_id,
            "pipeline_name": "model-training",
            "status": status,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration": duration,
            "project": "demo-ml-project",
            "parameters": {
                "learning_rate": learning_rate,
                "batch_size": batch_size,
                "epochs": epochs,
                "optimizer": "adam",
                "model_architecture": random.choice(["resnet50", "efficientnet", "vit"]),
            },
            "metrics": {
                "accuracy": final_accuracy,
                "loss": final_loss,
                "f1_score": random.uniform(0.8, 0.94),
            },
            "dag": {
                "nodes": [
                    {"id": "load_data", "name": "Load Dataset", "inputs": [], "outputs": ["dataset"]},
                    {"id": "preprocess", "name": "Preprocess", "inputs": ["dataset"], "outputs": ["processed_data"]},
                    {"id": "train", "name": "Train Model", "inputs": ["processed_data"], "outputs": ["model"]},
                    {
                        "id": "validate",
                        "name": "Validate",
                        "inputs": ["model", "processed_data"],
                        "outputs": ["metrics"],
                    },
                    {"id": "save", "name": "Save Model", "inputs": ["model"], "outputs": ["saved_model"]},
                ],
            },
            "steps": {
                "load_data": {"success": True, "duration": duration * 0.1, "cached": False},
                "preprocess": {"success": True, "duration": duration * 0.2, "cached": False},
                "train": {"success": status == "completed", "duration": duration * 0.5, "cached": False},
                "validate": {"success": status == "completed", "duration": duration * 0.1, "cached": False},
                "save": {"success": status == "completed", "duration": duration * 0.1, "cached": False},
            },
        }
        store.save_run(run_id, metadata)

        # Create artifacts for successful runs
        if status == "completed":
            # Model artifact
            model_artifact_id = str(uuid.uuid4())
            store.save_artifact(
                model_artifact_id,
                {
                    "artifact_id": model_artifact_id,
                    "name": f"model-v{i+1}",
                    "type": "model",
                    "run_id": run_id,
                    "step": "save",
                    "path": f"/models/v{i+1}.pt",
                    "project": "demo-ml-project",
                    "pipeline_name": "model-training",
                    "format": "pytorch",
                    "size_bytes": random.randint(50, 500) * 1024 * 1024,
                    "properties": {
                        "framework": "pytorch",
                        "accuracy": final_accuracy,
                        "loss": final_loss,
                        "parameters": random.randint(1000000, 50000000),
                    },
                    "created_at": end_time.isoformat(),
                },
            )

            # Dataset artifact
            dataset_artifact_id = str(uuid.uuid4())
            store.save_artifact(
                dataset_artifact_id,
                {
                    "artifact_id": dataset_artifact_id,
                    "name": f"processed-dataset-{i+1}",
                    "type": "dataset",
                    "run_id": run_id,
                    "step": "preprocess",
                    "path": f"/data/processed_{i+1}.parquet",
                    "project": "demo-ml-project",
                    "pipeline_name": "model-training",
                    "format": "parquet",
                    "size_bytes": random.randint(100, 500) * 1024 * 1024,
                    "properties": {
                        "rows": random.randint(10000, 100000),
                        "columns": random.randint(20, 50),
                        "features": random.randint(15, 45),
                    },
                    "created_at": (start_time + timedelta(seconds=duration * 0.3)).isoformat(),
                },
            )

            # Metrics artifact
            metrics_artifact_id = str(uuid.uuid4())
            store.save_artifact(
                metrics_artifact_id,
                {
                    "artifact_id": metrics_artifact_id,
                    "name": f"training-metrics-{i+1}",
                    "type": "metrics",
                    "run_id": run_id,
                    "step": "validate",
                    "path": f"/metrics/training_{i+1}.json",
                    "project": "demo-ml-project",
                    "pipeline_name": "model-training",
                    "format": "json",
                    "size_bytes": 4096,
                    "properties": {
                        "accuracy": final_accuracy,
                        "loss": final_loss,
                        "precision": random.uniform(0.8, 0.95),
                        "recall": random.uniform(0.8, 0.95),
                    },
                    "created_at": (end_time - timedelta(seconds=duration * 0.15)).isoformat(),
                },
            )

    # ========== PROJECT 2: Data Pipeline Project ==========
    print("\n📊 Creating Data Pipeline Project...")
    data_project = pm.create_project(
        "demo-data-pipeline",
        description="Data ingestion, transformation, and quality checks",
    )

    data_pipelines = ["data-ingestion", "data-transformation", "data-quality"]
    for pipeline_name in data_pipelines:
        data_project.create_pipeline(pipeline_name)

    # Generate Data Processing Runs
    print("  Creating data processing runs...")
    for i in range(4):
        run_id = str(uuid.uuid4())
        status = "completed"
        start_time = datetime.now() - timedelta(days=random.randint(0, 5))
        duration = random.uniform(10, 120)
        end_time = start_time + timedelta(seconds=duration)

        metadata = {
            "run_id": run_id,
            "pipeline_name": "data-transformation",
            "status": status,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration": duration,
            "project": "demo-data-pipeline",
            "parameters": {
                "source": "s3://data-lake/raw",
                "destination": "s3://data-lake/processed",
                "partition_by": "date",
            },
            "metrics": {
                "records_processed": random.randint(10000, 1000000),
                "records_filtered": random.randint(100, 10000),
                "data_quality_score": random.uniform(0.9, 1.0),
            },
            "dag": {
                "nodes": [
                    {"id": "extract", "name": "Extract", "inputs": [], "outputs": ["raw_data"]},
                    {"id": "transform", "name": "Transform", "inputs": ["raw_data"], "outputs": ["clean_data"]},
                    {"id": "validate", "name": "Validate", "inputs": ["clean_data"], "outputs": ["validated_data"]},
                    {"id": "load", "name": "Load", "inputs": ["validated_data"], "outputs": ["loaded_data"]},
                ],
            },
            "steps": {
                "extract": {"success": True, "duration": duration * 0.3, "cached": False},
                "transform": {"success": True, "duration": duration * 0.4, "cached": False},
                "validate": {"success": True, "duration": duration * 0.2, "cached": False},
                "load": {"success": True, "duration": duration * 0.1, "cached": False},
            },
        }
        store.save_run(run_id, metadata)

        # Create data artifacts
        for step, artifact_type in [("extract", "dataset"), ("transform", "dataset"), ("validate", "report")]:
            artifact_id = str(uuid.uuid4())
            store.save_artifact(
                artifact_id,
                {
                    "artifact_id": artifact_id,
                    "name": f"{step}-output-{i+1}",
                    "type": artifact_type,
                    "run_id": run_id,
                    "step": step,
                    "path": f"/data/{step}_{i+1}.parquet",
                    "project": "demo-data-pipeline",
                    "pipeline_name": "data-transformation",
                    "format": "parquet" if artifact_type == "dataset" else "json",
                    "size_bytes": random.randint(10, 100) * 1024 * 1024,
                    "properties": {
                        "records": random.randint(10000, 100000),
                    },
                    "created_at": start_time.isoformat(),
                },
            )

    # ========== PROJECT 3: Deployment Project ==========
    print("\n🚀 Creating Deployment Project...")
    deploy_project = pm.create_project(
        "demo-deployment",
        description="Model deployment and monitoring pipelines",
    )

    deploy_pipelines = ["model-deployment", "health-check", "rollback"]
    for pipeline_name in deploy_pipelines:
        deploy_project.create_pipeline(pipeline_name)

    # Generate Deployment Runs
    print("  Creating deployment runs...")
    for i in range(3):
        run_id = str(uuid.uuid4())
        status = random.choice(["completed", "completed", "failed"])
        start_time = datetime.now() - timedelta(hours=random.randint(1, 48))
        duration = random.uniform(60, 300)
        end_time = start_time + timedelta(seconds=duration) if status != "running" else None

        metadata = {
            "run_id": run_id,
            "pipeline_name": "model-deployment",
            "status": status,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat() if end_time else None,
            "duration": duration if end_time else None,
            "project": "demo-deployment",
            "parameters": {
                "environment": random.choice(["staging", "production"]),
                "model_version": f"v{i+1}",
                "replicas": random.choice([2, 3, 5]),
            },
            "metrics": {
                "deployment_time": duration,
                "health_check_passed": status == "completed",
            },
            "dag": {
                "nodes": [
                    {"id": "build", "name": "Build Image", "inputs": [], "outputs": ["image"]},
                    {"id": "test", "name": "Run Tests", "inputs": ["image"], "outputs": ["test_results"]},
                    {"id": "deploy", "name": "Deploy", "inputs": ["image", "test_results"], "outputs": ["deployment"]},
                    {"id": "verify", "name": "Verify", "inputs": ["deployment"], "outputs": ["status"]},
                ],
            },
            "steps": {
                "build": {"success": True, "duration": duration * 0.3, "cached": False},
                "test": {"success": True, "duration": duration * 0.2, "cached": False},
                "deploy": {"success": status == "completed", "duration": duration * 0.4, "cached": False},
                "verify": {"success": status == "completed", "duration": duration * 0.1, "cached": False},
            },
        }
        store.save_run(run_id, metadata)

    # ========== CREATE EXPERIMENTS ==========
    print("\n🔬 Creating experiments...")

    # Experiment 1: Link ML training runs
    exp_id_1 = "exp-hyperopt-ml"
    conn = sqlite3.connect(store.db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT OR REPLACE INTO experiments
        (experiment_id, name, description, tags, project, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            exp_id_1,
            "ML Hyperparameter Optimization",
            "Tuning learning rate, batch size, and model architecture",
            json.dumps({"team": "ml-research", "priority": "high", "status": "active"}),
            "demo-ml-project",
            datetime.now().isoformat(),
        ),
    )
    conn.commit()
    conn.close()

    # Link training runs to experiment
    ml_runs = store.query(pipeline_name="model-training", project="demo-ml-project")
    for run in ml_runs[:5]:
        store.log_experiment_run(
            exp_id_1,
            run["run_id"],
            metrics=run.get("metrics"),
            parameters=run.get("parameters"),
        )

    # Experiment 2: Data quality experiment
    exp_id_2 = "exp-data-quality"
    conn = sqlite3.connect(store.db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT OR REPLACE INTO experiments
        (experiment_id, name, description, tags, project, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            exp_id_2,
            "Data Quality Impact Study",
            "Analyzing how data quality affects model performance",
            json.dumps({"team": "data-engineering", "priority": "medium", "status": "completed"}),
            "demo-data-pipeline",
            datetime.now().isoformat(),
        ),
    )
    conn.commit()
    conn.close()

    # Link data processing runs
    data_runs = store.query(pipeline_name="data-transformation", project="demo-data-pipeline")
    for run in data_runs:
        store.log_experiment_run(
            exp_id_2,
            run["run_id"],
            metrics=run.get("metrics"),
            parameters=run.get("parameters"),
        )

    print("\n✅ Enhanced seed data created successfully!")
    print("   - 3 Projects: demo-ml-project, demo-data-pipeline, demo-deployment")
    print(f"   - {len(ml_pipelines) + len(data_pipelines) + len(deploy_pipelines)} Pipelines")
    print("   - ~13 Runs with complete DAGs and steps")
    print("   - Multiple Artifacts (models, datasets, metrics, reports)")
    print("   - 2 Experiments linking runs")
    print("\n🎉 All entities are fully connected with proper project attribution!")


if __name__ == "__main__":
    seed_data()
