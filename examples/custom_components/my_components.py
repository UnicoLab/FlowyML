"""
Example: Custom Orchestrator Component.

This example shows how to create a custom stack component
that can be used in uniflow.yaml or registered programmatically.
"""

from typing import Any
import importlib.util
from uniflow.stacks.components import Orchestrator, ResourceConfig, DockerConfig
from uniflow.stacks.plugins import register_component, get_component_registry


@register_component
class AirflowOrchestrator(Orchestrator):
    """
    Custom Airflow orchestrator for UniFlow.

    This orchestrator converts UniFlow pipelines to Airflow DAGs.

    Configuration in uniflow.yaml:
    ```yaml
    stacks:
      airflow_stack:
        type: local
        orchestrator:
          type: airflow
          airflow_home: /path/to/airflow
          dag_folder: /path/to/dags
    ```

    Or programmatically:
    ```python
    from my_components import AirflowOrchestrator
    from uniflow.stacks import Stack

    orchestrator = AirflowOrchestrator(
        airflow_home="/path/to/airflow",
        dag_folder="/path/to/dags"
    )

    stack = Stack(
        name="airflow",
        orchestrator=orchestrator,
        # ... other components
    )
    ```
    """

    def __init__(
        self,
        name: str = "airflow",
        airflow_home: str = "~/airflow",
        dag_folder: str = "~/airflow/dags",
        default_args: dict[str, Any] = None,
    ):
        """
        Initialize Airflow orchestrator.

        Args:
            name: Orchestrator name
            airflow_home: Path to Airflow home directory
            dag_folder: Path to DAGs folder
            default_args: Default arguments for Airflow DAG
        """
        super().__init__(name)
        self.airflow_home = airflow_home
        self.dag_folder = dag_folder
        self.default_args = default_args or {}

    def validate(self) -> bool:
        """Validate Airflow configuration."""
        # Check if Airflow is installed
        if importlib.util.find_spec("airflow") is not None:
            return True
        raise ImportError(
            "Apache Airflow is not installed. Install with: pip install apache-airflow",
        )

    def run_pipeline(
        self,
        pipeline: Any,
        resources: ResourceConfig = None,
        docker_config: DockerConfig = None,
        **kwargs,
    ) -> str:
        """
        Convert UniFlow pipeline to Airflow DAG and execute.

        Args:
            pipeline: UniFlow pipeline
            resources: Resource configuration
            docker_config: Docker configuration
            **kwargs: Additional arguments

        Returns:
            DAG run ID
        """
        from airflow import DAG
        from airflow.operators.python import PythonOperator
        from datetime import datetime, timedelta

        # Create Airflow DAG
        dag = DAG(
            dag_id=pipeline.name,
            default_args={
                "owner": "uniflow",
                "start_date": datetime.now() - timedelta(days=1),
                "retries": 1,
                **self.default_args,
            },
            schedule_interval=None,
            catchup=False,
        )

        # Convert UniFlow steps to Airflow tasks
        tasks = {}
        for step in pipeline.steps:

            def create_task_callable(step_func):
                def task_callable(**context):
                    # Execute step
                    return step_func()

                return task_callable

            task = PythonOperator(
                task_id=step.name,
                python_callable=create_task_callable(step.func),
                dag=dag,
            )
            tasks[step.name] = task

        # Set up dependencies based on pipeline graph
        # (Simplified - actual implementation would use pipeline.graph)
        for i in range(len(pipeline.steps) - 1):
            current_step = pipeline.steps[i]
            next_step = pipeline.steps[i + 1]
            tasks[current_step.name] >> tasks[next_step.name]

        # Trigger DAG run
        from airflow.models import DagBag

        dag_bag = DagBag(self.dag_folder)
        dag_bag.bag_dag(dag, dag)

        # Trigger execution
        dag.create_dagrun(
            run_id=f"uniflow_{pipeline.run_id}",
            state="running",
            execution_date=datetime.now(),
        )

        return f"airflow_run_{pipeline.run_id}"

    def get_run_status(self, run_id: str) -> str:
        """Get status of an Airflow DAG run."""
        from airflow.models import DagRun

        # Extract DAG run ID
        dagrun_id = run_id.replace("airflow_run_", "")

        # Query Airflow database
        dagrun = DagRun.find(run_id=f"uniflow_{dagrun_id}")

        if dagrun:
            return dagrun[0].state
        return "UNKNOWN"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "type": "airflow",
            "airflow_home": self.airflow_home,
            "dag_folder": self.dag_folder,
            "default_args": self.default_args,
        }


@register_component
class MinIOArtifactStore:
    """
    Custom MinIO artifact store.

    Example usage in uniflow.yaml:
    ```yaml
    stacks:
      minio_stack:
        type: local
        artifact_store:
          type: minio
          endpoint: localhost:9000
          bucket: uniflow-artifacts
          access_key: ${MINIO_ACCESS_KEY}
          secret_key: ${MINIO_SECRET_KEY}
    ```
    """

    def __init__(
        self,
        name: str = "minio",
        endpoint: str = "localhost:9000",
        bucket: str = "uniflow",
        access_key: str = "",
        secret_key: str = "",
        secure: bool = False,
    ):
        self.name = name
        self.endpoint = endpoint
        self.bucket = bucket
        self.access_key = access_key
        self.secret_key = secret_key
        self.secure = secure
        self._client = None

    @property
    def client(self):
        """Get or create MinIO client."""
        if self._client is None:
            from minio import Minio

            self._client = Minio(
                self.endpoint,
                access_key=self.access_key,
                secret_key=self.secret_key,
                secure=self.secure,
            )

            # Create bucket if it doesn't exist
            if not self._client.bucket_exists(self.bucket):
                self._client.make_bucket(self.bucket)

        return self._client

    def save(self, artifact: Any, path: str) -> str:
        """Save artifact to MinIO."""
        import pickle
        import io

        # Serialize artifact
        data = pickle.dumps(artifact)
        data_stream = io.BytesIO(data)

        # Upload to MinIO
        self.client.put_object(
            self.bucket,
            path,
            data_stream,
            length=len(data),
        )

        return f"s3://{self.bucket}/{path}"

    def load(self, path: str) -> Any:
        """Load artifact from MinIO."""
        import pickle

        # Handle s3:// URIs
        if path.startswith("s3://"):
            path = path.replace(f"s3://{self.bucket}/", "")

        # Download from MinIO
        response = self.client.get_object(self.bucket, path)
        data = response.read()

        return pickle.loads(data)

    def exists(self, path: str) -> bool:
        """Check if artifact exists."""
        try:
            self.client.stat_object(self.bucket, path)
            return True
        except Exception:
            return False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "type": "minio",
            "endpoint": self.endpoint,
            "bucket": self.bucket,
        }


# You can also create components without decorator
class RedisCache:
    """Custom Redis cache component."""

    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0):
        self.host = host
        self.port = port
        self.db = db

    # ... implementation


# Manually register if not using decorator
get_component_registry().register(RedisCache, "redis_cache")
