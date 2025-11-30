"""AWS Stack Components and Preset Stack."""

from __future__ import annotations

import base64
import subprocess
import uuid
from pathlib import Path
from typing import Any

from flowyml.stacks.base import Stack
from flowyml.stacks.components import ArtifactStore, ContainerRegistry, ResourceConfig, DockerConfig
from flowyml.core.remote_orchestrator import RemoteOrchestrator
from flowyml.stacks.plugins import register_component
from flowyml.storage.metadata import SQLiteMetadataStore
from flowyml.core.submission_result import SubmissionResult
from flowyml.core.execution_status import ExecutionStatus
from flowyml.stacks.components import Orchestrator


@register_component(name="s3")
class S3ArtifactStore(ArtifactStore):
    """Artifact store backed by Amazon S3."""

    def __init__(
        self,
        name: str = "s3",
        bucket_name: str | None = None,
        prefix: str = "flowyml",
        region: str | None = None,
        session_kwargs: dict[str, Any] | None = None,
    ):
        super().__init__(name)
        self.bucket_name = bucket_name
        self.prefix = prefix.strip("/")
        self.region = region
        self.session_kwargs = session_kwargs or {}

    def _client(self):
        import boto3

        return boto3.client("s3", region_name=self.region, **self.session_kwargs)

    def _object_key(self, path: str) -> str:
        normalized = path.lstrip("/")
        return f"{self.prefix}/{normalized}" if self.prefix else normalized

    def validate(self) -> bool:
        if not self.bucket_name:
            raise ValueError("bucket_name is required for S3ArtifactStore")
        try:
            self._client().head_bucket(Bucket=self.bucket_name)
        except Exception as exc:
            raise ValueError(f"Unable to access bucket '{self.bucket_name}': {exc}") from exc
        return True

    def save(self, artifact: Any, path: str) -> str:
        """Save artifact to S3. Accepts file paths, bytes, or strings."""
        key = self._object_key(path)
        client = self._client()

        if isinstance(artifact, (str, Path)) and Path(artifact).exists():
            client.upload_file(str(Path(artifact)), self.bucket_name, key)
        else:
            body = artifact if isinstance(artifact, bytes) else str(artifact).encode()
            client.put_object(Bucket=self.bucket_name, Key=key, Body=body)

        return f"s3://{self.bucket_name}/{key}"

    def load(self, path: str) -> bytes:
        key = self._object_key(path)
        client = self._client()
        obj = client.get_object(Bucket=self.bucket_name, Key=key)
        return obj["Body"].read()

    def exists(self, path: str) -> bool:
        key = self._object_key(path)
        client = self._client()
        try:
            client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except Exception:
            return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type": "s3",
            "bucket_name": self.bucket_name,
            "prefix": self.prefix,
            "region": self.region,
        }


@register_component(name="ecr")
class ECRContainerRegistry(ContainerRegistry):
    """Amazon Elastic Container Registry integration."""

    def __init__(
        self,
        name: str = "ecr",
        account_id: str | None = None,
        region: str = "us-east-1",
        registry_alias: str | None = None,
    ):
        super().__init__(name)
        self.account_id = account_id
        self.region = region
        self.registry_alias = registry_alias

    def _client(self):
        import boto3

        return boto3.client("ecr", region_name=self.region)

    def validate(self) -> bool:
        if not self.account_id:
            raise ValueError("account_id is required for ECRContainerRegistry")
        return True

    def _login(self) -> None:
        client = self._client()
        auth = client.get_authorization_token()
        data = auth["authorizationData"][0]
        token = base64.b64decode(data["authorizationToken"]).decode()
        username, password = token.split(":")
        endpoint = data["proxyEndpoint"]
        subprocess.run(["docker", "login", "--username", username, "--password", password, endpoint], check=True)

    def push_image(self, image_name: str, tag: str = "latest") -> str:
        full_uri = self.get_image_uri(image_name, tag)
        self._login()
        subprocess.run(["docker", "tag", f"{image_name}:{tag}", full_uri], check=True)
        subprocess.run(["docker", "push", full_uri], check=True)
        return full_uri

    def pull_image(self, image_name: str, tag: str = "latest") -> None:
        full_uri = self.get_image_uri(image_name, tag)
        self._login()
        subprocess.run(["docker", "pull", full_uri], check=True)

    def get_image_uri(self, image_name: str, tag: str = "latest") -> str:
        registry = self.registry_alias or f"{self.account_id}.dkr.ecr.{self.region}.amazonaws.com"
        return f"{registry}/{image_name}:{tag}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type": "ecr",
            "account_id": self.account_id,
            "region": self.region,
            "registry_alias": self.registry_alias,
        }


@register_component(name="aws_batch")
class AWSBatchOrchestrator(RemoteOrchestrator):
    """Submit Flow yML jobs to AWS Batch."""

    def __init__(
        self,
        name: str = "aws_batch",
        region: str = "us-east-1",
        job_queue: str | None = None,
        job_definition: str | None = None,
        parameters: dict[str, str] | None = None,
    ):
        super().__init__(name)
        self.region = region
        self.job_queue = job_queue
        self.job_definition = job_definition
        self.parameters = parameters or {}

    def _client(self):
        import boto3

        return boto3.client("batch", region_name=self.region)

    def validate(self) -> bool:
        if not self.job_queue or not self.job_definition:
            raise ValueError("job_queue and job_definition are required for AWSBatchOrchestrator")
        return True

    def run_pipeline(
        self,
        pipeline: Any,
        run_id: str,
        resources: ResourceConfig | None = None,
        docker_config: DockerConfig | None = None,
        inputs: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
        **kwargs,
    ) -> SubmissionResult:
        """Submit pipeline to AWS Batch.

        Returns:
            SubmissionResult with job ID and optional wait function.
        """
        from flowyml.core.submission_result import SubmissionResult
        import time

        client = self._client()
        job_name = kwargs.get("job_name") or f"{pipeline.name}-{getattr(pipeline, 'run_id', uuid.uuid4().hex)[:8]}"

        env = [
            {"name": "FLOWYML_PIPELINE_NAME", "value": pipeline.name},
            {"name": "FLOWYML_RUN_ID", "value": getattr(pipeline, "run_id", uuid.uuid4().hex)},
        ]
        if docker_config and docker_config.env_vars:
            for key, value in docker_config.env_vars.items():
                env.append({"name": key, "value": value})

        container_overrides: dict[str, Any] = {"environment": env}
        if docker_config and docker_config.image:
            container_overrides["command"] = ["python", "-m", "flowyml.cli.run"]

        if resources:
            container_overrides["resourceRequirements"] = [
                {"type": "VCPU", "value": resources.cpu},
                {"type": "MEMORY", "value": resources.memory.replace("Gi", "")},
            ]
            if resources.gpu:
                container_overrides["resourceRequirements"].append(
                    {"type": "GPU", "value": str(resources.gpu_count or 1)},
                )

        response = client.submit_job(
            jobName=job_name,
            jobQueue=self.job_queue,
            jobDefinition=self.job_definition,
            containerOverrides=container_overrides,
            parameters=self.parameters,
        )
        job_id = response["jobId"]

        # Create wait function
        def wait_for_completion():
            """Poll job status until completion."""
            while True:
                status = self.get_run_status(job_id)
                if status.is_finished:
                    if not status.is_successful:
                        raise RuntimeError(f"AWS Batch job {job_id} failed with status: {status}")
                    break
                time.sleep(10)  # Poll every 10 seconds

        return SubmissionResult(
            job_id=job_id,
            wait_for_completion=wait_for_completion,
            metadata={
                "platform": "aws_batch",
                "region": self.region,
                "job_queue": self.job_queue,
                "job_name": job_name,
            },
        )

    def get_run_status(self, job_id: str) -> ExecutionStatus:
        """Get status of AWS Batch job.

        Args:
            job_id: The AWS Batch job ID.

        Returns:
            Current execution status.
        """
        from flowyml.core.execution_status import ExecutionStatus

        client = self._client()
        try:
            response = client.describe_jobs(jobs=[job_id])
            if not response.get("jobs"):
                return ExecutionStatus.FAILED

            job = response["jobs"][0]
            status = job.get("status", "UNKNOWN")

            # Map AWS Batch status to ExecutionStatus
            status_map = {
                "SUBMITTED": ExecutionStatus.PROVISIONING,
                "PENDING": ExecutionStatus.PROVISIONING,
                "RUNNABLE": ExecutionStatus.PROVISIONING,
                "STARTING": ExecutionStatus.INITIALIZING,
                "RUNNING": ExecutionStatus.RUNNING,
                "SUCCEEDED": ExecutionStatus.COMPLETED,
                "FAILED": ExecutionStatus.FAILED,
            }
            return status_map.get(status, ExecutionStatus.RUNNING)
        except Exception as e:
            print(f"Error fetching job status: {e}")
            return ExecutionStatus.FAILED

    def stop_run(self, job_id: str, graceful: bool = True) -> None:
        """Stop an AWS Batch job.

        Args:
            job_id: The AWS Batch job ID.
            graceful: If True, allow job to finish current work. If False, terminate immediately.
        """
        client = self._client()
        reason = "Stopped by user"

        try:
            if graceful:
                # Cancel the job (allows cleanup)
                client.cancel_job(jobId=job_id, reason=reason)
            else:
                # Terminate immediately
                client.terminate_job(jobId=job_id, reason=reason)
        except Exception as e:
            print(f"Error stopping job {job_id}: {e}")
            raise

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type": "aws_batch",
            "region": self.region,
            "job_queue": self.job_queue,
            "job_definition": self.job_definition,
        }


@register_component(name="sagemaker")
class SageMakerOrchestrator(RemoteOrchestrator):
    """Amazon SageMaker Training/Inference Orchestrator."""

    def __init__(
        self,
        name: str = "sagemaker",
        region: str = "us-east-1",
        role_arn: str | None = None,
        default_instance_type: str = "ml.m5.xlarge",
        default_instance_count: int = 1,
        volume_size_gb: int = 50,
        output_path: str | None = None,
    ):
        super().__init__(name)
        self.region = region
        self.role_arn = role_arn
        self.default_instance_type = default_instance_type
        self.default_instance_count = default_instance_count
        self.volume_size_gb = volume_size_gb
        self.output_path = output_path

    def _client(self):
        import boto3

        return boto3.client("sagemaker", region_name=self.region)

    def validate(self) -> bool:
        if not self.role_arn:
            raise ValueError("role_arn is required for SageMakerOrchestrator")
        return True

    def run_pipeline(
        self,
        pipeline: Any,
        run_id: str,
        resources: ResourceConfig | None = None,
        docker_config: DockerConfig | None = None,
        inputs: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
        hyperparameters: dict[str, str] | None = None,
        **kwargs,
    ) -> SubmissionResult:
        client = self._client()
        training_image = docker_config.image if docker_config and docker_config.image else kwargs.get("training_image")
        if not training_image:
            raise ValueError("A Docker image must be provided via DockerConfig for SageMaker training.")

        instance_type = (
            kwargs.get("instance_type") or (resources.machine_type if resources else None) or self.default_instance_type
        )
        instance_count = (
            kwargs.get("instance_count")
            or (resources.gpu_count if resources and resources.gpu_count else None)
            or self.default_instance_count
        )

        job_name = kwargs.get("job_name") or f"{pipeline.name}-{getattr(pipeline, 'run_id', uuid.uuid4().hex)[:8]}"
        training_input_s3 = kwargs.get("input_s3_uri")
        output_path = kwargs.get("output_s3_uri") or self.output_path
        if not output_path:
            raise ValueError("output_path must be provided for SageMaker training outputs.")

        create_kwargs = {
            "TrainingJobName": job_name,
            "AlgorithmSpecification": {
                "TrainingImage": training_image,
                "TrainingInputMode": "File",
            },
            "RoleArn": self.role_arn,
            "OutputDataConfig": {"S3OutputPath": output_path},
            "ResourceConfig": {
                "InstanceType": instance_type,
                "InstanceCount": instance_count,
                "VolumeSizeInGB": kwargs.get("volume_size_gb", self.volume_size_gb),
            },
            "StoppingCondition": {"MaxRuntimeInSeconds": kwargs.get("max_runtime", 3600 * 24)},
        }

        if training_input_s3:
            create_kwargs["InputDataConfig"] = [
                {
                    "ChannelName": "training",
                    "DataSource": {
                        "S3DataSource": {
                            "S3DataType": "S3Prefix",
                            "S3Uri": training_input_s3,
                            "S3DataDistributionType": "FullyReplicated",
                        },
                    },
                },
            ]

        if hyperparameters:
            create_kwargs["HyperParameters"] = hyperparameters

        client.create_training_job(**create_kwargs)

        # Return Submission Result
        from flowyml.core.submission_result import SubmissionResult
        import time

        job_id = job_name

        # Create wait function
        def wait_for_completion():
            """Poll training job status until completion."""
            while True:
                status = self.get_run_status(job_id)
                if status.is_finished:
                    if not status.is_successful:
                        raise RuntimeError(f"SageMaker job {job_id} failed with status: {status}")
                    break
                time.sleep(15)  # Poll every 15 seconds

        return SubmissionResult(
            job_id=job_id,
            wait_for_completion=wait_for_completion,
            metadata={
                "platform": "sagemaker",
                "region": self.region,
                "instance_type": instance_type,
                "job_name": job_name,
            },
        )

    def deploy_model(
        self,
        model_artifact_s3_uri: str,
        inference_image: str,
        endpoint_name: str,
        instance_type: str = "ml.m5.large",
        instance_count: int = 1,
        wait: bool = True,
    ) -> str:
        client = self._client()
        model_name = f"{endpoint_name}-model"
        client.create_model(
            ModelName=model_name,
            PrimaryContainer={
                "Image": inference_image,
                "ModelDataUrl": model_artifact_s3_uri,
            },
            ExecutionRoleArn=self.role_arn,
        )

        endpoint_config_name = f"{endpoint_name}-config"
        client.create_endpoint_config(
            EndpointConfigName=endpoint_config_name,
            ProductionVariants=[
                {
                    "VariantName": "AllTraffic",
                    "ModelName": model_name,
                    "InstanceType": instance_type,
                    "InitialInstanceCount": instance_count,
                },
            ],
        )

        client.create_endpoint(EndpointName=endpoint_name, EndpointConfigName=endpoint_config_name)

        if wait:
            waiter = client.get_waiter("endpoint_in_service")
            waiter.wait(EndpointName=endpoint_name)
        return endpoint_name

    def get_run_status(self, job_id: str) -> ExecutionStatus:
        """Get status of SageMaker training job.

        Args:
            job_id: The SageMaker training job name.

        Returns:
            Current execution status.
        """
        from flowyml.core.execution_status import ExecutionStatus

        client = self._client()
        try:
            response = client.describe_training_job(TrainingJobName=job_id)
            status = response.get("TrainingJobStatus", "Unknown")

            # Map SageMaker status to ExecutionStatus
            status_map = {
                "InProgress": ExecutionStatus.RUNNING,
                "Completed": ExecutionStatus.COMPLETED,
                "Failed": ExecutionStatus.FAILED,
                "Stopping": ExecutionStatus.STOPPING,
                "Stopped": ExecutionStatus.STOPPED,
            }
            return status_map.get(status, ExecutionStatus.RUNNING)
        except Exception as e:
            print(f"Error fetching training job status: {e}")
            return ExecutionStatus.FAILED

    def stop_run(self, job_id: str, graceful: bool = True) -> None:
        """Stop a SageMaker training job.

        Args:
            job_id: The SageMaker training job name.
            graceful: Graceful shutdown (SageMaker always stops gracefully).
        """
        client = self._client()

        try:
            client.stop_training_job(TrainingJobName=job_id)
        except Exception as e:
            print(f"Error stopping training job {job_id}: {e}")
            raise

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type": "sagemaker",
            "region": self.region,
            "role_arn": self.role_arn,
            "default_instance_type": self.default_instance_type,
        }


class AWSStack(Stack):
    """Pre-built stack for AWS Batch, S3, and ECR."""

    def __init__(
        self,
        name: str = "aws",
        region: str = "us-east-1",
        bucket_name: str | None = None,
        account_id: str | None = None,
        job_queue: str | None = None,
        job_definition: str | None = None,
        registry_alias: str | None = None,
        orchestrator_type: str = "batch",
        role_arn: str | None = None,
        metadata_store: Any | None = None,
    ):
        orchestrator: Orchestrator
        if orchestrator_type == "sagemaker":
            orchestrator = SageMakerOrchestrator(region=region, role_arn=role_arn)
        else:
            orchestrator = AWSBatchOrchestrator(region=region, job_queue=job_queue, job_definition=job_definition)

        artifact_store = S3ArtifactStore(bucket_name=bucket_name, region=region)
        container_registry = ECRContainerRegistry(account_id=account_id, region=region, registry_alias=registry_alias)

        if metadata_store is None:
            metadata_store = SQLiteMetadataStore()

        super().__init__(
            name=name,
            executor=None,
            artifact_store=artifact_store,
            metadata_store=metadata_store,
            container_registry=container_registry,
            orchestrator=orchestrator,
        )

        self.region = region
        self.bucket_name = bucket_name

    def validate(self) -> bool:
        self.orchestrator.validate()
        self.artifact_store.validate()
        self.container_registry.validate()
        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type": "aws",
            "region": self.region,
            "bucket_name": self.bucket_name,
            "orchestrator": self.orchestrator.to_dict(),
            "artifact_store": self.artifact_store.to_dict(),
            "container_registry": self.container_registry.to_dict(),
        }
