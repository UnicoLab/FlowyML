"""GCP Stack - Google Cloud Platform integration for flowyml.

This module provides GCP-specific implementations for running pipelines
on Google Cloud Platform using Vertex AI, Cloud Storage, and Container Registry.
"""

from typing import Any

import subprocess
from flowyml.stacks.base import Stack
from flowyml.stacks.components import (
    ArtifactStore,
    ContainerRegistry,
    ResourceConfig,
    DockerConfig,
)
from flowyml.core.remote_orchestrator import RemoteOrchestrator
from flowyml.stacks.plugins import register_component
from flowyml.core.submission_result import SubmissionResult
from flowyml.core.execution_status import ExecutionStatus


@register_component(name="vertex_ai")
class VertexAIOrchestrator(RemoteOrchestrator):
    """Vertex AI orchestrator for running pipelines on Google Cloud.

    This orchestrator submits pipeline jobs to Vertex AI Pipelines,
    allowing for scalable, managed execution in the cloud.

    Example:
        ```python
        from flowyml.stacks.gcp import VertexAIOrchestrator

        orchestrator = VertexAIOrchestrator(
            project_id="my-gcp-project",
            region="us-central1",
            service_account="my-sa@my-project.iam.gserviceaccount.com",
        )
        ```
    """

    def __init__(
        self,
        name: str = "vertex_ai",
        project_id: str | None = None,
        region: str = "europe-west1",
        service_account: str | None = None,
        network: str | None = None,
        encryption_key: str | None = None,
        staging_bucket: str | None = None,
    ):
        """Initialize Vertex AI orchestrator.

        Args:
            name: Name of the orchestrator
            project_id: GCP project ID
            region: GCP region for Vertex AI
            service_account: Service account email for job execution
            network: VPC network for jobs
            encryption_key: Customer-managed encryption key
            staging_bucket: GCS staging bucket for job artifacts
        """
        super().__init__(name)
        self.project_id = project_id
        self.region = region
        self.service_account = service_account
        self.network = network
        self.encryption_key = encryption_key
        self.staging_bucket = staging_bucket

    def validate(self) -> bool:
        """Validate Vertex AI configuration."""
        if not self.project_id:
            raise ValueError("project_id is required for VertexAIOrchestrator")

        # Check if google-cloud-aiplatform is installed
        import importlib.util

        if importlib.util.find_spec("google.cloud.aiplatform") is not None:
            return True
        raise ImportError(
            "google-cloud-aiplatform is required for VertexAIOrchestrator. "
            "Install with: pip install google-cloud-aiplatform",
        )

    # ── Auto Docker Build & Push ─────────────────────────────────────

    def _auto_build_and_push(
        self,
        docker_config: "DockerConfig | None",
        container_registry: "ContainerRegistry | None" = None,
    ) -> str:
        """Build and push a Docker image for remote execution.

        Delegates to :class:`~flowyml.core.image_builder.DockerImageBuilder`
        for consistent multi-stage builds, content-hash tagging, and
        BuildKit cache support.  Falls back to raw ``docker build`` if
        the builder is unavailable.

        Automatically uses ``--platform linux/amd64`` for GCP
        compatibility (critical on Apple Silicon machines).

        Args:
            docker_config: Docker configuration from the stack.
            container_registry: Registry configuration for tagging/pushing.

        Returns:
            The remote image URI to use in Vertex AI jobs.
        """
        import logging
        from pathlib import Path

        logger = logging.getLogger("flowyml.orchestrator.vertex_ai")

        # If image is already a full registry URI, assume pre-built
        if docker_config and docker_config.image and "/" in docker_config.image:
            logger.info("Using pre-built image: %s", docker_config.image)
            return docker_config.image

        # Build the registry URI
        registry_base = f"{self.region}-docker.pkg.dev/{self.project_id}"
        image_name = docker_config.image if docker_config and docker_config.image else "pipeline"
        remote_uri = f"{registry_base}/{image_name}/{image_name}:latest"

        # Resolve build context (fix: was incorrectly using 'context_dir')
        build_context = "."
        if docker_config and hasattr(docker_config, "build_context"):
            build_context = docker_config.build_context
        if not Path(build_context).is_dir():
            raise FileNotFoundError(
                f"Docker build context directory not found: {build_context}",
            )

        # Try using DockerImageBuilder for consistent builds
        try:
            from flowyml.core.image_builder import DockerImageBuilder

            builder = DockerImageBuilder()

            # Ensure platform is linux/amd64 for GCP
            if docker_config:
                docker_config.platform = "linux/amd64"

            logger.info("🐳 Building with DockerImageBuilder for linux/amd64...")
            built_tag = builder.build_image(docker_config, tag=remote_uri)

            # Push
            logger.info("📤 Pushing to Artifact Registry...")
            builder.push_image(built_tag)

            logger.info("✅ Image pushed: %s", remote_uri)
            return remote_uri

        except ImportError:
            logger.warning("DockerImageBuilder not available, falling back to subprocess")

        # Fallback: raw docker build + push
        dockerfile = "Dockerfile"
        if docker_config and docker_config.dockerfile:
            dockerfile = docker_config.dockerfile

        import os

        if not os.path.exists(dockerfile):
            logger.warning(
                "No Dockerfile found at '%s'. Skipping auto-build. "
                "Provide a pre-built image URI in docker_config.image.",
                dockerfile,
            )
            return remote_uri

        logger.info("🐳 Auto-building Docker image for linux/amd64...")
        logger.info("   Image: %s", remote_uri)

        build_cmd = [
            "docker",
            "build",
            "--platform",
            "linux/amd64",
            "-t",
            remote_uri,
            "-f",
            dockerfile,
            build_context,
        ]
        logger.info("   Build command: %s", " ".join(build_cmd))

        result = subprocess.run(build_cmd, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            logger.error("Docker build failed:\n%s", result.stderr[-2000:])
            raise RuntimeError(f"Docker build failed: {result.stderr[-500:]}")

        logger.info("✅ Docker image built successfully")

        # Push to Artifact Registry
        logger.info("📤 Pushing to Artifact Registry...")
        push_cmd = ["docker", "push", remote_uri]
        result = subprocess.run(push_cmd, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            logger.error("Docker push failed:\n%s", result.stderr[-2000:])
            raise RuntimeError(f"Docker push failed: {result.stderr[-500:]}")

        logger.info("✅ Image pushed: %s", remote_uri)
        return remote_uri

    def _build_worker_pool_specs(
        self,
        docker_config: "DockerConfig | None" = None,
        resources: "ResourceConfig | None" = None,
        command: list[str] | None = None,
        args: list[str] | None = None,
    ) -> list[dict]:
        """Build Vertex AI worker pool specifications.

        Translates FlowyML DockerConfig and ResourceConfig into the
        ``worker_pool_specs`` format expected by ``aiplatform.CustomJob``.

        Args:
            docker_config: Docker image and environment configuration.
            resources: CPU, memory, GPU resource requirements.
            command: Override container command (e.g. ["python", "-m", "flowyml"]).
            args: Override container args (e.g. ["run", "--steps", "step1,step2"]).

        Returns:
            List with a single worker pool spec dict.
        """
        from flowyml.stacks.components import ResourceConfig as _DefaultRC  # noqa: N814

        if resources is None:
            resources = _DefaultRC(cpu="4", memory="8Gi")

        # Determine machine type from resources
        cpu_count = int(resources.cpu) if resources.cpu else 4

        # Map to GCP machine type
        if resources.machine_type:
            machine_type = resources.machine_type
        elif cpu_count <= 2:
            machine_type = "n1-standard-4"
        elif cpu_count <= 4:
            machine_type = "n1-standard-8"
        else:
            machine_type = "n1-standard-16"

        # Build container spec
        container_spec: dict[str, Any] = {}
        if docker_config and docker_config.image:
            container_spec["image_uri"] = docker_config.image

            # Use provided command/args or fall back to docker_config
            if command:
                container_spec["command"] = command
            if args:
                container_spec["args"] = args

            # Environment variables
            env_vars = docker_config.env_vars or {}
            if env_vars:
                container_spec["env"] = [{"name": k, "value": str(v)} for k, v in env_vars.items()]

        # Build machine spec
        machine_spec: dict[str, Any] = {"machine_type": machine_type}

        # GPU configuration
        if resources.gpu:
            gpu_type_map = {
                "nvidia-tesla-t4": "NVIDIA_TESLA_T4",
                "nvidia-tesla-v100": "NVIDIA_TESLA_V100",
                "nvidia-tesla-a100": "NVIDIA_TESLA_A100",
                "nvidia-tesla-p100": "NVIDIA_TESLA_P100",
            }
            accelerator_type = gpu_type_map.get(resources.gpu, "NVIDIA_TESLA_T4")
            machine_spec["accelerator_type"] = accelerator_type
            machine_spec["accelerator_count"] = resources.gpu_count or 1

        worker_pool_spec = {
            "machine_spec": machine_spec,
            "replica_count": 1,
            "container_spec": container_spec,
        }

        return [worker_pool_spec]

    def _resource_from_group(self, group: Any) -> "ResourceConfig":
        """Convert a StepGroup's aggregated resources to a ResourceConfig.

        Args:
            group: StepGroup with aggregated_resources.

        Returns:
            ResourceConfig for the execution group.
        """
        agg = group.aggregated_resources
        if agg is None:
            return ResourceConfig(cpu="2", memory="4Gi")

        return ResourceConfig(
            cpu=str(agg.cpu) if agg.cpu else "2",
            memory=agg.memory or "4Gi",
            gpu=agg.gpu.type if agg.gpu else None,
            gpu_count=agg.gpu.count if agg.gpu else None,
            machine_type=getattr(agg, "machine_type", None),
        )

    def _submit_single_job(
        self,
        display_name: str,
        docker_config: "DockerConfig",
        resources: "ResourceConfig | None" = None,
        command: list[str] | None = None,
        args: list[str] | None = None,
    ) -> Any:
        """Submit a single Vertex AI CustomJob and return the job object.

        Args:
            display_name: Human-readable job name.
            docker_config: Docker image and env vars.
            resources: Resource requirements.
            command: Container entrypoint override.
            args: Container arguments override.

        Returns:
            google.cloud.aiplatform.CustomJob object (submitted).
        """
        from google.cloud import aiplatform

        worker_pool_specs = self._build_worker_pool_specs(
            docker_config=docker_config,
            resources=resources,
            command=command,
            args=args,
        )

        job = aiplatform.CustomJob(
            display_name=display_name,
            worker_pool_specs=worker_pool_specs,
            staging_bucket=self.staging_bucket,
            encryption_spec_key_name=self.encryption_key,
        )

        submit_kwargs = {}
        if self.service_account:
            submit_kwargs["service_account"] = self.service_account
        if self.network:
            submit_kwargs["network"] = self.network

        job.submit(**submit_kwargs)
        return job

    def _wait_for_job(self, job: Any, poll_interval: int = 15) -> None:
        """Block until a Vertex AI job reaches a terminal state, while streaming logs.

        Args:
            job: google.cloud.aiplatform.CustomJob object.
            poll_interval: Seconds between status polls.

        Raises:
            RuntimeError: If the job fails or is cancelled.
        """
        import time
        import sys

        try:
            from google.cloud import logging as cloud_logging

            logging_client = cloud_logging.Client(project=self.project_id)
            has_logging = True
        except Exception:
            has_logging = False

        job_id = job.resource_name.split("/")[-1]
        last_timestamp = None

        def fetch_logs():
            nonlocal last_timestamp
            if not has_logging:
                return

            try:
                # Filter for this specific custom job
                filter_str = f'resource.type="ml_job" AND resource.labels.job_id="{job_id}"'

                # Fetch logs chronologically
                entries = list(
                    logging_client.list_entries(
                        filter_=filter_str,
                        order_by=cloud_logging.DESCENDING,
                        max_results=100,
                    ),
                )

                # Reverse to print in chronological order
                entries.reverse()

                for entry in entries:
                    if last_timestamp and entry.timestamp <= last_timestamp:
                        continue

                    msg = entry.payload
                    if isinstance(msg, dict) and "message" in msg:
                        msg = msg["message"]

                    # Clean up common Vertex formatting issues
                    msg = str(msg).strip()
                    if msg:
                        # Print directly to stdout for real-time feel
                        print(f"  [remote] {msg}")
                        sys.stdout.flush()

                    last_timestamp = entry.timestamp
            except Exception:
                pass

        # Poll loop
        while True:
            job._sync_gca_resource()
            fetch_logs()

            state = job.state.name
            if state in (
                "JOB_STATE_SUCCEEDED",
                "JOB_STATE_FAILED",
                "JOB_STATE_CANCELLED",
                "JOB_STATE_EXPIRED",
            ):
                break

            # Sleep in smaller chunks to stream logs more responsively
            for _ in range(poll_interval):
                time.sleep(1)
                fetch_logs()

        # Final log fetch to catch tail
        fetch_logs()

        if job.state.name != "JOB_STATE_SUCCEEDED":
            import contextlib

            error_msg = ""
            with contextlib.suppress(Exception):
                error_msg = f": {job.error}" if job.error else ""
            raise RuntimeError(
                f"Vertex AI job '{job.display_name}' ended with state {job.state.name}{error_msg}",
            )

    def run_pipeline(
        self,
        pipeline: Any,
        run_id: str,
        resources: ResourceConfig | None = None,
        docker_config: DockerConfig | None = None,
        inputs: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> "SubmissionResult":
        """Run pipeline on Vertex AI with per-group orchestration.

        This is the core ZenML-parity feature: run a local command, and
        FlowyML automatically:
          1. Analyzes the pipeline DAG into execution groups
          2. Builds a Docker image for linux/amd64 (if needed)
          3. Pushes it to Artifact Registry
          4. Submits each group as a separate Vertex AI CustomJob
          5. Each container runs ``flowyml step-runner --steps ...``
          6. Waits for each group before submitting the next
          7. Streams logs back to the local console

        Args:
            pipeline: Pipeline to run
            run_id: Run identifier
            resources: Default resource configuration (overridden per-group)
            docker_config: Docker configuration (image, env vars)
            inputs: Input data
            context: Context variables
            **kwargs: Additional arguments

        Returns:
            SubmissionResult with job metadata for all groups
        """
        from google.cloud import aiplatform
        from flowyml.core.step_grouping import get_execution_units, StepGroup
        import logging
        import os

        logger = logging.getLogger("flowyml.orchestrator.vertex_ai")

        # Initialize Vertex AI
        aiplatform.init(
            project=self.project_id,
            location=self.region,
            staging_bucket=self.staging_bucket,
        )

        # ── Analyze execution groups ────────────────────────────────
        if not pipeline._built:
            pipeline.build()

        execution_units = get_execution_units(pipeline.dag, pipeline.steps)

        # Classify units
        groups = [u for u in execution_units if isinstance(u, StepGroup)]
        has_groups = len(groups) > 0

        logger.info(
            "Pipeline '%s': %d execution units (%d groups, %d standalone steps)",
            pipeline.name,
            len(execution_units),
            len(groups),
            len(execution_units) - len(groups),
        )

        # ── Resolve pipeline_module for step runner ─────────────────
        pipeline_module = kwargs.get("pipeline_module", "")
        if not pipeline_module:
            import yaml

            # Try to read raw config from flowyml.yaml
            config_path = os.environ.get("FLOWYML_CONFIG", "flowyml.yaml")
            try:
                if os.path.exists(config_path):
                    with open(config_path) as f:
                        raw_config = yaml.safe_load(f)
                    pipeline_module = raw_config.get("pipeline_module", "")
            except Exception as e:
                logger.warning("Could not read pipeline_module from config: %s", e)

        # ── Auto-build & push Docker image ──────────────────────────
        image_uri = ""
        if docker_config and docker_config.image and "/" in docker_config.image:
            # Pre-built image URI provided — use as-is
            image_uri = docker_config.image
            logger.info("Using pre-built image: %s", image_uri)
        elif has_groups and pipeline_module:
            # Auto-build & push
            try:
                image_uri = self._auto_build_and_push(docker_config)
            except Exception as e:
                logger.error("Auto-build failed: %s", e)
                raise RuntimeError(
                    f"Docker auto-build/push failed: {e}. "
                    f"You can manually build and push, then set docker.image "
                    f"in flowyml.yaml to the full registry URI.",
                ) from e
        elif docker_config and docker_config.image:
            image_uri = docker_config.image

        # ── Single-job fallback (no groups or no step runner) ───────
        if not has_groups or not pipeline_module:
            job_name = f"{pipeline.name}-{run_id[:8]}"
            logger.info("Submitting single CustomJob: %s", job_name)

            single_docker = DockerConfig(
                image=image_uri or (docker_config.image if docker_config else ""),
                env_vars=docker_config.env_vars if docker_config else {},
            )

            job = self._submit_single_job(
                display_name=job_name,
                docker_config=single_docker,
                resources=resources,
                command=docker_config.command if docker_config and docker_config.command else None,
                args=docker_config.args if docker_config and docker_config.args else None,
            )

            job_id = job.resource_name

            def wait_single():
                self._wait_for_job(job)

            return SubmissionResult(
                job_id=job_id,
                wait_for_completion=wait_single,
                metadata={
                    "platform": "vertex_ai",
                    "project": self.project_id,
                    "region": self.region,
                    "job_name": job_name,
                    "mode": "single_job",
                },
            )

        # ── KFP Vertex AI Pipelines Orchestration (ZenML-parity) ────
        # ZenML parity requires submitting the DAG via Kubeflow Pipelines (KFP)
        # so the entire topological graph is visualized natively in GCP Console.
        try:
            import importlib.util

            has_kfp = importlib.util.find_spec("kfp") is not None
        except (ImportError, ModuleNotFoundError):
            has_kfp = False
        if not has_kfp:
            raise ImportError(
                "kfp is required for Vertex AI Pipelines orchestration. Install with: pip install kfp kfp-server-api",
            )
        from kfp import dsl
        from kfp import compiler

        logger.info(
            "🚀 Compiling KFP Pipeline for %d execution units → Vertex AI Pipelines",
            len(execution_units),
        )
        logger.info("   Pipeline module: %s", pipeline_module)

        artifact_bucket = self.staging_bucket or f"gs://flowyml-{self.project_id}-artifacts"

        # Resolve Transparent Telemetry URL (Ngrok Tunneling)
        try:
            from flowyml.ui.utils import get_ui_server_url, get_ui_host_port

            server_url = os.getenv("FLOWYML_SERVER_URL")
            if not server_url:
                server_url = get_ui_server_url()
                # If it's local, auto-tunnel it!
                if server_url and ("localhost" in server_url or "127.0.0.1" in server_url):
                    try:
                        from flowyml.ui.tunnel import start_tunnel

                        host, port = get_ui_host_port()
                        tunnel_url = start_tunnel(port)
                        if tunnel_url:
                            server_url = tunnel_url
                            logger.info(
                                f"🌐 Transparent telemetry active! Remote pipelines will stream to: {tunnel_url}",
                            )
                    except Exception as e:
                        logger.warning(f"Auto-tunneling failed: {e}")
        except Exception:
            server_url = os.getenv("FLOWYML_SERVER_URL", "")

        # 1. Define KFP Container Component for Step Runner
        @dsl.container_component
        def flowyml_step_group():
            return dsl.ContainerSpec(
                image=image_uri,
                command=["flowyml", "step-runner"],
            )

        # 2. Build Pipeline DAG
        @dsl.pipeline(name=pipeline.name.replace("_", "-"), description="FlowyML Orchestrated Pipeline")
        def flowyml_pipeline():
            tasks = {}
            for unit in execution_units:
                if isinstance(unit, StepGroup):
                    group = unit
                    step_names = [s.name for s in group.steps]
                    group_name = group.group_name

                    # Derive resources
                    group_resources = self._resource_from_group(group)
                else:
                    group = None
                    step_names = [unit.name]
                    group_name = unit.name
                    group_resources = resources or ResourceConfig(cpu="2", memory="4Gi")

                # Create KFP Task
                task = flowyml_step_group()

                # Set Env Vars
                task.set_env_variable("FLOWYML_PIPELINE_MODULE", pipeline_module)
                task.set_env_variable("FLOWYML_STEP_NAMES", ",".join(step_names))
                task.set_env_variable("FLOWYML_RUN_ID", run_id)
                task.set_env_variable("FLOWYML_EXECUTION_GROUP", group_name)
                task.set_env_variable("FLOWYML_PIPELINE_NAME", pipeline.name)
                task.set_env_variable("PYTHONUNBUFFERED", "1")
                task.set_env_variable("FLOWYML_ARTIFACT_DIR", "/tmp/flowyml_artifacts")  # noqa: S108
                task.set_env_variable("FLOWYML_STAGING_BUCKET", artifact_bucket)
                task.set_env_variable("FLOWYML_CONFIG", "flowyml.yaml")

                # Inject active stack so remote container uses gcp-prod, not local
                active_stack = os.environ.get("FLOWYML_STACK", "gcp-prod")
                task.set_env_variable("FLOWYML_STACK", active_stack)
                # Platform identifier for log formatting
                task.set_env_variable("FLOWYML_PLATFORM", "gcp")

                # Telemetry connection for remote UI monitoring
                if server_url:
                    task.set_env_variable("FLOWYML_SERVER_URL", server_url)

                # Assign custom resources and names
                task.set_display_name(group_name)
                if group_resources:
                    if group_resources.cpu:
                        task.set_cpu_limit(str(group_resources.cpu))
                    if group_resources.memory:
                        task.set_memory_limit(group_resources.memory)

                tasks[group_name] = task

                # Determine topological dependencies using FlowyML DAG
                # Look for dependencies produced by previous execution units
                for s_name in step_names:
                    deps = pipeline.dag.get_dependencies(s_name)
                    for dep in deps:
                        dep_group_name = None
                        for prev_unit in execution_units:
                            if prev_unit == unit:
                                break
                            prev_names = (
                                [s.name for s in prev_unit.steps]
                                if isinstance(prev_unit, StepGroup)
                                else [prev_unit.name]
                            )
                            if dep in prev_names:
                                dep_group_name = (
                                    isinstance(prev_unit, StepGroup) and prev_unit.group_name or prev_unit.name
                                )
                                break

                        if dep_group_name and dep_group_name in tasks:
                            task.after(tasks[dep_group_name])

        # 3. Compile Pipeline YAML
        pipeline_yaml = f".flowyml_pipeline_{run_id[:8]}.yaml"
        compiler.Compiler().compile(
            pipeline_func=flowyml_pipeline,
            package_path=pipeline_yaml,
        )

        logger.info("✅ Pipeline compiled to %s", pipeline_yaml)

        # 4. Submit Vertex AI PipelineJob
        job_display_name = f"{pipeline.name}-{run_id[:8]}"
        pipeline_job = aiplatform.PipelineJob(
            display_name=job_display_name,
            template_path=pipeline_yaml,
            job_id=job_display_name.replace("_", "-").lower(),
            project=self.project_id,
            location=self.region,
            enable_caching=False,
        )

        logger.info("📤 Submitting PipelineJob to Vertex AI...")

        submit_kwargs = {}
        if self.service_account:
            submit_kwargs["service_account"] = self.service_account
        if self.network:
            submit_kwargs["network"] = self.network

        pipeline_job.submit(**submit_kwargs)

        dashboard_uri = ""
        try:
            dashboard_uri = pipeline_job._dashboard_uri()
            logger.info("──────────────────────────────────────────────────")
            logger.info("✨ Vertex AI Pipelines DAG successfully submitted!")
            logger.info("🔗 View Live Execution Graph: %s", dashboard_uri)
            logger.info("──────────────────────────────────────────────────")
        except Exception:
            logger.info("✅ Pipeline submitted successfully!")

        # Clean up temporary YAML
        import contextlib
        from pathlib import Path

        with contextlib.suppress(Exception):
            Path(pipeline_yaml).unlink(missing_ok=True)

        def wait_pipeline():
            # Simply poll until complete, but don't stream logs because KFP
            # provides a beautiful UI for that natively.
            pipeline_job.wait()

        return SubmissionResult(
            job_id=pipeline_job.resource_name,
            wait_for_completion=wait_pipeline,
            metadata={
                "platform": "vertex_ai",
                "project": self.project_id,
                "region": self.region,
                "mode": "kfp_pipeline",
                "job_name": job_display_name,
                "dashboard_uri": dashboard_uri,
            },
        )

    def get_run_status(self, job_id: str) -> "ExecutionStatus":
        """Get status of a Vertex AI job.

        Args:
            job_id: The job resource name.

        Returns:
            ExecutionStatus enum value.
        """
        from google.cloud import aiplatform

        try:
            job = aiplatform.CustomJob(job_id)
            state = job.state.name

            # Map Vertex AI states to ExecutionStatus
            status_map = {
                "JOB_STATE_QUEUED": ExecutionStatus.PROVISIONING,
                "JOB_STATE_PENDING": ExecutionStatus.PROVISIONING,
                "JOB_STATE_RUNNING": ExecutionStatus.RUNNING,
                "JOB_STATE_SUCCEEDED": ExecutionStatus.COMPLETED,
                "JOB_STATE_FAILED": ExecutionStatus.FAILED,
                "JOB_STATE_CANCELLING": ExecutionStatus.STOPPING,
                "JOB_STATE_CANCELLED": ExecutionStatus.CANCELLED,
                "JOB_STATE_PAUSED": ExecutionStatus.RUNNING,
                "JOB_STATE_EXPIRED": ExecutionStatus.FAILED,
                "JOB_STATE_UPDATING": ExecutionStatus.RUNNING,
            }
            return status_map.get(state, ExecutionStatus.RUNNING)
        except Exception as e:
            print(f"Error fetching job status: {e}")
            return ExecutionStatus.FAILED

    def get_run_details(self, job_id: str) -> dict:
        """Get full details of a Vertex AI job.

        Returns comprehensive job metadata including timing, resource
        usage, and error information for the FlowyML dashboard.

        Args:
            job_id: The job resource name.

        Returns:
            Dictionary with job details.
        """
        from google.cloud import aiplatform

        try:
            job = aiplatform.CustomJob(job_id)
            return {
                "job_id": job.resource_name,
                "display_name": job.display_name,
                "state": job.state.name,
                "create_time": job.create_time.isoformat() if job.create_time else None,
                "start_time": job.start_time.isoformat() if job.start_time else None,
                "end_time": job.end_time.isoformat() if job.end_time else None,
                "error": str(job.error) if job.error else None,
                "labels": dict(job.labels) if job.labels else {},
                "platform": "vertex_ai",
                "project": self.project_id,
                "region": self.region,
                "console_url": (
                    f"https://console.cloud.google.com/vertex-ai/training/"
                    f"{job.resource_name.split('/')[-1]}?project={self.project_id}"
                ),
            }
        except Exception as e:
            return {"job_id": job_id, "error": str(e)}

    def get_run_logs(self, job_id: str, max_entries: int = 200) -> str:
        """Get logs for a Vertex AI job from Cloud Logging.

        Args:
            job_id: The job resource name.
            max_entries: Maximum number of log entries to fetch.

        Returns:
            String containing the logs.
        """
        try:
            from google.cloud import logging as cloud_logging

            client = cloud_logging.Client(project=self.project_id)
            job_name = job_id.split("/")[-1]

            # Vertex AI custom jobs log under ml_job resource type
            filter_str = f'resource.type="ml_job" resource.labels.job_id="{job_name}"'

            entries = list(
                client.list_entries(
                    filter_=filter_str,
                    order_by=cloud_logging.DESCENDING,
                    max_results=max_entries,
                ),
            )

            logs = []
            for entry in reversed(entries):
                timestamp = entry.timestamp.strftime("%H:%M:%S") if entry.timestamp else ""
                severity = getattr(entry, "severity", "INFO")
                payload = entry.payload if entry.payload else str(entry)
                logs.append(f"[{timestamp}] [{severity}] {payload}")

            return "\n".join(logs) if logs else "No logs found yet."

        except ImportError:
            return "google-cloud-logging is required for log retrieval. Install with: pip install google-cloud-logging"
        except Exception as e:
            return f"Failed to fetch logs: {e}"

    def stream_logs(self, job_id: str, poll_interval: float = 5.0):
        """Stream logs from a Vertex AI job in real-time.

        Yields log lines as they become available, suitable for
        driving the FlowyML GUI's live log viewer.

        Args:
            job_id: The job resource name.
            poll_interval: Seconds between polling for new log entries.

        Yields:
            dict with keys: timestamp, severity, message, is_finished
        """
        import time

        seen_entries = set()
        job_finished = False

        while not job_finished:
            # Check job status
            status = self.get_run_status(job_id)
            job_finished = status in (
                ExecutionStatus.COMPLETED,
                ExecutionStatus.FAILED,
                ExecutionStatus.CANCELLED,
            )

            # Fetch recent logs
            try:
                from google.cloud import logging as cloud_logging

                client = cloud_logging.Client(project=self.project_id)
                job_name = job_id.split("/")[-1]

                filter_str = f'resource.type="ml_job" resource.labels.job_id="{job_name}"'

                entries = list(
                    client.list_entries(
                        filter_=filter_str,
                        order_by=cloud_logging.ASCENDING,
                        max_results=500,
                    ),
                )

                for entry in entries:
                    entry_id = getattr(entry, "insert_id", id(entry))
                    if entry_id not in seen_entries:
                        seen_entries.add(entry_id)
                        yield {
                            "timestamp": entry.timestamp.isoformat() if entry.timestamp else None,
                            "severity": getattr(entry, "severity", "INFO"),
                            "message": str(entry.payload) if entry.payload else str(entry),
                            "is_finished": False,
                        }

            except Exception as e:
                yield {
                    "timestamp": None,
                    "severity": "ERROR",
                    "message": f"Log polling error: {e}",
                    "is_finished": False,
                }

            if not job_finished:
                time.sleep(poll_interval)

        # Final status yield
        yield {
            "timestamp": None,
            "severity": "INFO",
            "message": f"Job completed with status: {status.name}",
            "is_finished": True,
        }

    def stop_run(self, job_id: str, graceful: bool = True) -> None:
        """Cancel a Vertex AI job.

        Args:
            job_id: The job resource name.
            graceful: Whether to wait for graceful shutdown.
        """
        from google.cloud import aiplatform

        try:
            job = aiplatform.CustomJob(job_id)
            job.cancel()
            print(f"Cancellation requested for job: {job_id}")
        except Exception as e:
            print(f"Error cancelling job {job_id}: {e}")
            raise

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "type": "vertex_ai",
            "project_id": self.project_id,
            "region": self.region,
            "service_account": self.service_account,
            "network": self.network,
            "console_url": f"https://console.cloud.google.com/vertex-ai/training?project={self.project_id}",
        }


@register_component(name="gcs")
class GCSArtifactStore(ArtifactStore):
    """Google Cloud Storage artifact store.

    Stores pipeline artifacts in Google Cloud Storage buckets.

    Example:
        ```python
        from flowyml.stacks.gcp import GCSArtifactStore

        artifact_store = GCSArtifactStore(bucket_name="my-flowyml-artifacts", project_id="my-gcp-project")
        ```
    """

    def __init__(
        self,
        name: str = "gcs",
        bucket_name: str | None = None,
        project_id: str | None = None,
        prefix: str = "flowyml",
    ):
        """Initialize GCS artifact store.

        Args:
            name: Name of the artifact store
            bucket_name: GCS bucket name
            project_id: GCP project ID
            prefix: Prefix for all artifacts in bucket.
                    Supports template variables:
                    - {date} → current date (YYYY-MM-DD)
                    - {pipeline_name} → pipeline name (if available)
        """
        super().__init__(name)
        self.bucket_name = bucket_name
        self.project_id = project_id
        self._prefix_template = prefix
        # Eagerly resolve {date} since it's fixed per session
        self.prefix = self._resolve_prefix(prefix)

    def validate(self) -> bool:
        """Validate GCS configuration."""
        if not self.bucket_name:
            raise ValueError("bucket_name is required for GCSArtifactStore")

        # Check if google-cloud-storage is installed
        import importlib.util

        if importlib.util.find_spec("google.cloud.storage") is not None:
            return True
        raise ImportError(
            "google-cloud-storage is required for GCSArtifactStore. Install with: pip install google-cloud-storage",
        )

    @staticmethod
    def _resolve_prefix(template: str) -> str:
        """Resolve template variables in the prefix.

        Args:
            template: Prefix template with optional {date}, {pipeline_name} vars.

        Returns:
            Resolved prefix string.
        """
        from datetime import datetime

        resolved = template
        if "{date}" in resolved:
            resolved = resolved.replace("{date}", datetime.now().strftime("%Y-%m-%d"))
        if "{pipeline_name}" in resolved:
            # Defer pipeline_name resolution to save() time
            pass
        return resolved

    @property
    def base_path(self) -> str:
        """Return the GCS base path for this store."""
        return f"gs://{self.bucket_name}/{self.prefix}"

    def save(self, artifact: Any, path: str) -> str:
        """Save artifact to GCS."""
        from google.cloud import storage
        import pickle

        client = storage.Client(project=self.project_id)
        bucket = client.bucket(self.bucket_name)

        # Full path with prefix
        full_path = f"{self.prefix}/{path}"
        blob = bucket.blob(full_path)

        # Serialize and upload
        data = pickle.dumps(artifact)
        blob.upload_from_string(data)

        return f"gs://{self.bucket_name}/{full_path}"

    def load(self, path: str) -> Any:
        """Load artifact from GCS."""
        from google.cloud import storage
        import pickle

        client = storage.Client(project=self.project_id)
        bucket = client.bucket(self.bucket_name)

        # Handle both full gs:// URIs and relative paths
        if path.startswith("gs://"):
            # Extract bucket and path from URI
            parts = path.replace("gs://", "").split("/", 1)
            blob_path = parts[1] if len(parts) > 1 else ""
        else:
            blob_path = f"{self.prefix}/{path}"

        blob = bucket.blob(blob_path)
        data = blob.download_as_bytes()

        return pickle.loads(data)

    def exists(self, path: str) -> bool:
        """Check if artifact exists in GCS."""
        from google.cloud import storage

        client = storage.Client(project=self.project_id)
        bucket = client.bucket(self.bucket_name)

        full_path = f"{self.prefix}/{path}"
        blob = bucket.blob(full_path)

        return blob.exists()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "type": "gcs",
            "bucket_name": self.bucket_name,
            "project_id": self.project_id,
            "prefix": self.prefix,
        }


@register_component(name="gcr")
class GCRContainerRegistry(ContainerRegistry):
    """Google Container Registry integration.

    Manages Docker images in Google Container Registry or Artifact Registry.

    Example:
        ```python
        from flowyml.stacks.gcp import GCRContainerRegistry

        registry = GCRContainerRegistry(project_id="my-gcp-project", registry_uri="gcr.io/my-gcp-project")
        ```
    """

    def __init__(
        self,
        name: str = "gcr",
        project_id: str | None = None,
        registry_uri: str | None = None,
        region: str | None = None,
        repository: str | None = None,
        use_artifact_registry: bool = False,
    ):
        """Initialize GCR container registry.

        Args:
            name: Name of the registry
            project_id: GCP project ID
            registry_uri: Full registry URI (e.g., gcr.io/project-id)
            region: Region for Artifact Registry (e.g., europe-west1)
            repository: Repository name in Artifact Registry
            use_artifact_registry: Whether to use Artifact Registry vs legacy GCR
        """
        super().__init__(name)
        self.project_id = project_id
        self.region = region
        self.repository = repository
        self.use_artifact_registry = use_artifact_registry

        if use_artifact_registry and region and project_id:
            self.registry_uri = registry_uri or f"{region}-docker.pkg.dev/{project_id}/{repository or 'default'}"
        else:
            self.registry_uri = registry_uri or f"gcr.io/{project_id}"

    def validate(self) -> bool:
        """Validate registry configuration."""
        if not self.project_id:
            raise ValueError("project_id is required for GCRContainerRegistry")
        return True

    def push_image(self, image_name: str, tag: str = "latest") -> str:
        """Push Docker image to GCR.

        Args:
            image_name: Name of the image
            tag: Image tag

        Returns:
            Full image URI
        """
        import subprocess

        full_uri = self.get_image_uri(image_name, tag)

        # Tag image
        subprocess.run(
            ["docker", "tag", f"{image_name}:{tag}", full_uri],
            check=True,
        )

        # Push to registry
        subprocess.run(
            ["docker", "push", full_uri],
            check=True,
        )

        return full_uri

    def pull_image(self, image_name: str, tag: str = "latest") -> None:
        """Pull Docker image from GCR."""
        import subprocess

        full_uri = self.get_image_uri(image_name, tag)
        subprocess.run(
            ["docker", "pull", full_uri],
            check=True,
        )

    def get_image_uri(self, image_name: str, tag: str = "latest") -> str:
        """Get full URI for an image."""
        return f"{self.registry_uri}/{image_name}:{tag}"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "type": "gcr",
            "project_id": self.project_id,
            "registry_uri": self.registry_uri,
            "region": self.region,
        }


class GCPStack(Stack):
    """Complete GCP stack for running flowyml pipelines on Google Cloud Platform.

    This stack integrates:
    - Vertex AI for orchestration
    - Google Cloud Storage for artifact storage
    - Google Container Registry for Docker images
    - Cloud SQL or Firestore for metadata storage

    Example:
        ```python
        from flowyml.stacks.gcp import GCPStack
        from flowyml.stacks.components import ResourceConfig, DockerConfig
        from flowyml import Pipeline, step

        # Create GCP stack
        stack = GCPStack(
            name="production",
            project_id="my-gcp-project",
            region="us-central1",
            bucket_name="my-flowyml-artifacts",
            registry_uri="gcr.io/my-gcp-project",
        )

        # Define resource requirements
        resources = ResourceConfig(cpu="4", memory="16Gi", gpu="nvidia-tesla-t4", gpu_count=1, machine_type="n1-highmem-4")

        # Define Docker configuration
        docker_config = DockerConfig(
            image="gcr.io/my-gcp-project/ml-pipeline:v1",
            requirements=["tensorflow>=2.12.0", "scikit-learn>=1.0.0"],
            env_vars={"PYTHONUNBUFFERED": "1"},
        )


        # Run pipeline on GCP
        @step
        def train_model():
            # Your training code
            pass


        pipeline = Pipeline("training", stack=stack)
        pipeline.add_step(train_model)

        result = pipeline.run(resources=resources, docker_config=docker_config)
        ```
    """

    def __init__(
        self,
        name: str = "gcp",
        project_id: str | None = None,
        region: str = "europe-west1",
        bucket_name: str | None = None,
        registry_uri: str | None = None,
        service_account: str | None = None,
        metadata_store: Any | None = None,
        model_deployer: Any | None = None,
    ):
        """Initialize GCP stack.

        Args:
            name: Stack name
            project_id: GCP project ID
            region: GCP region
            bucket_name: GCS bucket for artifacts
            registry_uri: Container registry URI
            service_account: Service account for job execution
            metadata_store: Metadata store (optional, defaults to local SQLite)
            model_deployer: Optional model deployer
        """
        # Create GCP components
        orchestrator = VertexAIOrchestrator(
            project_id=project_id,
            region=region,
            service_account=service_account,
        )

        artifact_store = GCSArtifactStore(
            bucket_name=bucket_name,
            project_id=project_id,
        )

        container_registry = GCRContainerRegistry(
            project_id=project_id,
            registry_uri=registry_uri,
            region=region,
        )

        # Use new generic deployer if provided, else use CloudRun default if desired,
        # but better to stick to generic injection or default creation
        if model_deployer is None:
            from flowyml.plugins.deployers.gcp_cloud_run import GCPCloudRunDeployer

            model_deployer = GCPCloudRunDeployer(project_id=project_id, region=region)

        # Initialize base stack
        super().__init__(
            name=name,
            executor=None,  # Vertex AI handles execution
            artifact_store=artifact_store,
            metadata_store=metadata_store,
            container_registry=container_registry,
            orchestrator=orchestrator,
            model_deployer=model_deployer,
        )

        self.project_id = project_id
        self.region = region
        # Legacy helpers kept for backward compatibility if needed, but stack now uses proper components
        self.vertex_endpoints = VertexEndpointManager(project_id=project_id, region=region)

    def validate(self) -> bool:
        """Validate all GCP stack components."""
        self.orchestrator.validate()
        self.artifact_store.validate()
        self.container_registry.validate()
        return True

    def to_dict(self) -> dict[str, Any]:
        """Convert stack configuration to dictionary."""
        return {
            "name": self.name,
            "type": "gcp",
            "project_id": self.project_id,
            "region": self.region,
            "orchestrator": self.orchestrator.to_dict(),
            "artifact_store": self.artifact_store.to_dict(),
            "container_registry": self.container_registry.to_dict(),
            "model_deployer": self.model_deployer.to_dict() if self.model_deployer else None,
        }


class VertexEndpointManager:
    """Deploy trained models as Vertex AI endpoints."""

    def __init__(self, project_id: str | None, region: str = "europe-west1"):
        self.project_id = project_id
        self.region = region

    def deploy_model(
        self,
        model_display_name: str,
        artifact_uri: str,
        serving_image: str,
        endpoint_display_name: str | None = None,
        machine_type: str = "n1-standard-4",
    ) -> str:
        from google.cloud import aiplatform

        aiplatform.init(project=self.project_id, location=self.region)
        model = aiplatform.Model.upload(
            display_name=model_display_name,
            artifact_uri=artifact_uri,
            serving_container_image_uri=serving_image,
        )
        endpoint = model.deploy(
            machine_type=machine_type,
            endpoint=aiplatform.Endpoint.create(
                display_name=endpoint_display_name or f"{model_display_name}-endpoint",
            ),
        )
        return endpoint.resource_name


class CloudRunDeployer:
    """Deploy container images to Cloud Run."""

    def __init__(self, project_id: str | None, region: str = "europe-west1"):
        self.project_id = project_id
        self.region = region

    def deploy_service(
        self,
        service_name: str,
        image: str,
        env: dict[str, str] | None = None,
        allow_unauthenticated: bool = True,
    ) -> str:
        command = [
            "gcloud",
            "run",
            "deploy",
            service_name,
            f"--image={image}",
            f"--region={self.region}",
            f"--project={self.project_id}",
        ]
        if allow_unauthenticated:
            command.append("--allow-unauthenticated")

        env = env or {}
        for key, value in env.items():
            command.append(f"--set-env-vars={key}={value}")

        subprocess.run(command, check=True)
        url_result = subprocess.run(
            [
                "gcloud",
                "run",
                "services",
                "describe",
                service_name,
                f"--region={self.region}",
                f"--project={self.project_id}",
                "--format=value(status.url)",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        return url_result.stdout.strip()
