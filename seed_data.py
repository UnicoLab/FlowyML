import json
import random
import uuid
from datetime import datetime, timedelta
from flowyml.core.project import ProjectManager
from flowyml.storage.metadata import SQLiteMetadataStore
import sqlite3


def seed_data():
    print("🌱 Seeding database with demo data...")

    # Initialize Project Manager
    pm = ProjectManager()

    # Create Demo Project
    project_name = "demo-project"
    print(f"Creating project: {project_name}")

    # Delete existing if any
    pm.delete_project(project_name, confirm=True)

    project = pm.create_project(
        project_name,
        description="A demo project showcasing FlowyML features with synthetic data.",
    )

    # Initialize Metadata Store directly for lower-level access if needed,
    # but we should try to use Project/Pipeline abstractions where possible.
    # However, for bulk seeding runs, accessing the store might be easier.
    # IMPORTANT: The API currently uses the global store at .flowyml/metadata.db
    # so we must write there for the UI to see it, even if Project creates a local one.
    store = SQLiteMetadataStore()

    # Pipelines
    pipelines = ["data-preprocessing", "model-training", "model-evaluation", "deployment"]
    print(f"Creating pipelines: {pipelines}")

    for p_name in pipelines:
        project.create_pipeline(p_name)

    # Generate Runs
    statuses = ["completed", "failed", "running"]

    print("Generating runs and artifacts...")

    # Helper to generate DAG and steps
    def generate_dag_and_steps(pipeline_type, status, run_duration):
        dag = {"nodes": []}
        steps = {}

        if pipeline_type == "data-preprocessing":
            node_ids = ["load_raw_data", "clean_data", "validate_schema", "split_train_test"]
            dag["nodes"] = [
                {"id": "load_raw_data", "name": "Load Raw Data", "inputs": [], "outputs": ["raw_batch"]},
                {"id": "clean_data", "name": "Clean Data", "inputs": ["raw_batch"], "outputs": ["cleaned_batch"]},
                {
                    "id": "validate_schema",
                    "name": "Validate Schema",
                    "inputs": ["cleaned_batch"],
                    "outputs": ["validated_data"],
                },
                {
                    "id": "split_train_test",
                    "name": "Split Train/Test",
                    "inputs": ["validated_data"],
                    "outputs": ["train_set", "test_set"],
                },
            ]
        elif pipeline_type == "model-training":
            node_ids = ["load_dataset", "feature_engineering", "train_model", "evaluate_model", "save_model"]
            dag["nodes"] = [
                {"id": "load_dataset", "name": "Load Dataset", "inputs": [], "outputs": ["train_set"]},
                {
                    "id": "feature_engineering",
                    "name": "Feature Engineering",
                    "inputs": ["train_set"],
                    "outputs": ["features"],
                },
                {"id": "train_model", "name": "Train Model", "inputs": ["features"], "outputs": ["model_weights"]},
                {"id": "evaluate_model", "name": "Evaluate Model", "inputs": ["model_weights"], "outputs": ["metrics"]},
                {"id": "save_model", "name": "Save Model", "inputs": ["model_weights"], "outputs": ["final_model"]},
            ]
        elif pipeline_type == "model-evaluation":
            node_ids = ["load_test_set", "load_model", "run_inference", "calculate_metrics"]
            dag["nodes"] = [
                {"id": "load_test_set", "name": "Load Test Set", "inputs": [], "outputs": ["test_data"]},
                {"id": "load_model", "name": "Load Model", "inputs": [], "outputs": ["model"]},
                {
                    "id": "run_inference",
                    "name": "Run Inference",
                    "inputs": ["test_data", "model"],
                    "outputs": ["predictions"],
                },
                {
                    "id": "calculate_metrics",
                    "name": "Calculate Metrics",
                    "inputs": ["predictions"],
                    "outputs": ["eval_report"],
                },
            ]
        else:  # deployment
            node_ids = ["package_model", "run_security_scan", "deploy_to_staging", "health_check"]
            dag["nodes"] = [
                {
                    "id": "package_model",
                    "name": "Package Model",
                    "inputs": ["model_artifact"],
                    "outputs": ["docker_image"],
                },
                {
                    "id": "run_security_scan",
                    "name": "Security Scan",
                    "inputs": ["docker_image"],
                    "outputs": ["scan_report"],
                },
                {
                    "id": "deploy_to_staging",
                    "name": "Deploy to Staging",
                    "inputs": ["docker_image", "scan_report"],
                    "outputs": ["deployment_status"],
                },
                {
                    "id": "health_check",
                    "name": "Health Check",
                    "inputs": ["deployment_status"],
                    "outputs": ["health_status"],
                },
            ]

        # Generate steps execution data
        step_duration = run_duration / len(node_ids)

        for i, node_id in enumerate(node_ids):
            step_status = "success"
            error = None

            # Simulate failure in the last or second to last step if run failed
            if status == "failed" and i >= len(node_ids) - 2:
                if i == len(node_ids) - 2 and random.random() > 0.5:
                    step_status = "failed"
                    error = "Step execution failed due to timeout"
                elif i == len(node_ids) - 1:
                    step_status = "failed"
                    error = "Dependency failed"

            # Simulate running state
            if status == "running" and i == len(node_ids) - 1:
                step_status = "running"
            elif status == "running" and i < len(node_ids) - 1:
                step_status = "success"

            steps[node_id] = {
                "success": step_status == "success",
                "error": error,
                "duration": random.uniform(step_duration * 0.8, step_duration * 1.2),
                "cached": random.random() > 0.8,
                "inputs": dag["nodes"][i]["inputs"],
                "outputs": dag["nodes"][i]["outputs"],
            }

            # Stop generating steps if we hit a failure or running state
            if step_status in ["failed", "running"]:
                break

        return dag, steps

    # 1. Data Preprocessing Runs
    for i in range(5):
        run_id = str(uuid.uuid4())
        status = "completed" if i < 4 else "failed"
        start_time = datetime.now() - timedelta(days=random.randint(1, 10))
        duration = random.uniform(10, 60)
        end_time = start_time + timedelta(seconds=duration)

        dag, steps = generate_dag_and_steps("data-preprocessing", status, duration)

        metadata = {
            "run_id": run_id,
            "pipeline_name": "data-preprocessing",
            "status": status,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration": duration,
            "project": project_name,
            "parameters": {"batch_size": 32, "validation_split": 0.2},
            "metrics": {"records_processed": 1000 * (i + 1)},
            "dag": dag,
            "steps": steps,
        }
        store.save_run(run_id, metadata)

        if status == "completed":
            # Create artifacts for each output in the DAG
            # Artifact 1: Raw Data (from load_raw_data step)
            artifact_id = str(uuid.uuid4())
            artifact_meta = {
                "artifact_id": artifact_id,
                "name": f"raw-batch-{i+1}",
                "type": "dataset",
                "run_id": run_id,
                "step": "load_raw_data",
                "path": f"/data/raw/batch_{i+1}.csv",
                "project": project_name,
                "format": "csv",
                "size_bytes": 2048 * 1024 * (i + 1),
                "properties": {
                    "rows": 1000 * (i + 1),
                    "columns": 15,
                },
            }
            store.save_artifact(artifact_id, artifact_meta)

            # Artifact 2: Cleaned Data (from clean_data step)
            artifact_id = str(uuid.uuid4())
            artifact_meta = {
                "artifact_id": artifact_id,
                "name": f"cleaned-batch-{i+1}",
                "type": "dataset",
                "run_id": run_id,
                "step": "clean_data",
                "path": f"/data/cleaned/batch_{i+1}.csv",
                "project": project_name,
                "format": "csv",
                "size_bytes": 1024 * 1024 * (i + 1),
                "properties": {
                    "rows": 980 * (i + 1),
                    "columns": 15,
                    "null_percentage": 0.02,
                },
            }
            store.save_artifact(artifact_id, artifact_meta)

    # 2. Model Training Runs
    for i in range(8):
        run_id = str(uuid.uuid4())
        status = random.choice(statuses)
        start_time = datetime.now() - timedelta(days=random.randint(0, 5))
        duration = random.uniform(300, 1200)
        end_time = start_time + timedelta(seconds=duration) if status != "running" else None

        # Generate training history for models
        epochs = random.randint(10, 50)
        train_history = {
            "epochs": list(range(1, epochs + 1)),
            "train_loss": [0.5 * (0.95**epoch) + random.uniform(0, 0.05) for epoch in range(epochs)],
            "val_loss": [0.55 * (0.95**epoch) + random.uniform(0, 0.06) for epoch in range(epochs)],
            "train_accuracy": [0.5 + 0.4 * (1 - 0.95**epoch) + random.uniform(0, 0.02) for epoch in range(epochs)],
            "val_accuracy": [0.48 + 0.4 * (1 - 0.95**epoch) + random.uniform(0, 0.03) for epoch in range(epochs)],
        }

        dag, steps = generate_dag_and_steps("model-training", status, duration)

        final_accuracy = train_history["val_accuracy"][-1] if status == "completed" else random.uniform(0.7, 0.95)
        final_loss = train_history["val_loss"][-1] if status == "completed" else random.uniform(0.1, 0.5)

        metadata = {
            "run_id": run_id,
            "pipeline_name": "model-training",
            "status": status,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat() if end_time else None,
            "duration": duration if end_time else None,
            "project": project_name,
            "parameters": {
                "learning_rate": random.choice([0.001, 0.01, 0.0001]),
                "epochs": epochs,
                "optimizer": "adam",
                "batch_size": random.choice([16, 32, 64]),
            },
            "metrics": {
                "accuracy": final_accuracy,
                "loss": final_loss,
            },
            "dag": dag,
            "steps": steps,
        }
        store.save_run(run_id, metadata)

        if status == "completed":
            # Artifact: Model with training history
            artifact_id = str(uuid.uuid4())
            artifact_meta = {
                "artifact_id": artifact_id,
                "name": f"model-v{i+1}",
                "type": "model",
                "run_id": run_id,
                "step": "save_model",
                "path": f"/models/v{i+1}.pt",
                "project": project_name,
                "properties": {
                    "framework": "pytorch",
                    "accuracy": final_accuracy,
                    "loss": final_loss,
                    "epochs_trained": epochs,
                    "model_size_mb": random.randint(50, 500),
                    "parameters_count": random.randint(1000000, 10000000),
                },
                "training_history": train_history,
            }
            store.save_artifact(artifact_id, artifact_meta)

            # Artifact: Feature set
            artifact_id = str(uuid.uuid4())
            artifact_meta = {
                "artifact_id": artifact_id,
                "name": f"features-v{i+1}",
                "type": "dataset",
                "run_id": run_id,
                "step": "feature_engineering",
                "path": f"/features/v{i+1}.npz",
                "project": project_name,
                "format": "numpy",
                "size_bytes": 512 * 1024,
                "properties": {
                    "feature_count": random.randint(50, 200),
                    "samples": 10000,
                },
            }
            store.save_artifact(artifact_id, artifact_meta)

    # 3. Evaluation Runs
    for i in range(3):
        run_id = str(uuid.uuid4())
        status = "completed"
        start_time = datetime.now() - timedelta(hours=random.randint(1, 24))
        duration = random.uniform(50, 200)
        end_time = start_time + timedelta(seconds=duration)

        dag, steps = generate_dag_and_steps("model-evaluation", status, duration)

        metadata = {
            "run_id": run_id,
            "pipeline_name": "model-evaluation",
            "status": status,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration": duration,
            "project": project_name,
            "parameters": {"test_set": "test-v1"},
            "metrics": {
                "f1_score": random.uniform(0.8, 0.92),
                "precision": random.uniform(0.8, 0.95),
                "recall": random.uniform(0.75, 0.9),
            },
            "dag": dag,
            "steps": steps,
        }
        store.save_run(run_id, metadata)
        # Artifact: Evaluation Report
        artifact_id = str(uuid.uuid4())
        artifact_meta = {
            "artifact_id": artifact_id,
            "name": f"eval-report-{i+1}",
            "type": "report",
            "run_id": run_id,
            "step": "calculate_metrics",
            "path": f"/reports/eval_{i+1}.json",
            "project": project_name,
            "format": "json",
            "size_bytes": 4096,
            "properties": {
                "test_samples": 1000,
                "classes": 10,
            },
        }
        store.save_artifact(artifact_id, artifact_meta)

    # 4. Experiments
    print("Creating experiments...")

    # Experiment 1: Hyperparameter Optimization
    exp_id_1 = "exp-hyperopt-001"
    conn = sqlite3.connect(store.db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT OR REPLACE INTO experiments
        (experiment_id, name, description, tags, project)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            exp_id_1,
            "Hyperparameter Optimization",
            "Tuning learning rate and batch size for better accuracy.",
            json.dumps({"priority": "high", "team": "ml-ops", "status": "active"}),
            project_name,
        ),
    )
    conn.commit()
    conn.close()

    # Link training runs to hyperopt experiment
    training_runs = store.query(pipeline_name="model-training", project=project_name)
    for run in training_runs[:4]:
        store.log_experiment_run(
            exp_id_1,
            run["run_id"],
            metrics=run.get("metrics"),
            parameters=run.get("parameters"),
        )

    # Experiment 2: Model Architecture Search
    exp_id_2 = "exp-arch-search-001"
    conn = sqlite3.connect(store.db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT OR REPLACE INTO experiments
        (experiment_id, name, description, tags, project)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            exp_id_2,
            "Model Architecture Search",
            "Comparing different neural network architectures for optimal performance.",
            json.dumps({"priority": "medium", "team": "research", "status": "completed"}),
            project_name,
        ),
    )
    conn.commit()
    conn.close()

    # Link remaining training runs to architecture search
    for run in training_runs[4:7]:
        store.log_experiment_run(
            exp_id_2,
            run["run_id"],
            metrics=run.get("metrics"),
            parameters=run.get("parameters"),
        )

    # Experiment 3: Data Quality Impact
    exp_id_3 = "exp-data-quality-001"
    conn = sqlite3.connect(store.db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT OR REPLACE INTO experiments
        (experiment_id, name, description, tags, project)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            exp_id_3,
            "Data Quality Impact Study",
            "Analyzing the impact of data preprocessing quality on model performance.",
            json.dumps({"priority": "low", "team": "data-engineering", "status": "planning"}),
            project_name,
        ),
    )
    conn.commit()
    conn.close()

    # Link preprocessing and evaluation runs
    preprocessing_runs = store.query(pipeline_name="data-preprocessing", project=project_name)
    for run in preprocessing_runs[:2]:
        store.log_experiment_run(
            exp_id_3,
            run["run_id"],
            metrics=run.get("metrics"),
            parameters=run.get("parameters"),
        )

    print(f"✅ Database seeded successfully! Project '{project_name}' created.")


if __name__ == "__main__":
    seed_data()
