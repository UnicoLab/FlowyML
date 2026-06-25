"""Multi-cloud observability providers for FlowyML.

Abstracts cloud-specific APIs (status sync, logs, artifacts) behind a
unified interface so the UI backend works identically for GCP, AWS, and Azure.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

logger = logging.getLogger("flowyml.ui.cloud_providers")


@dataclass
class CloudStepInfo:
    """Normalized step info from any cloud provider."""

    name: str
    status: str  # completed | failed | running | pending
    success: bool = False
    error: str | None = None
    duration: float | None = None
    start_time: str | None = None
    end_time: str | None = None


@dataclass
class CloudRunInfo:
    """Normalized run info from any cloud provider."""

    state: str  # running | completed | failed | cancelled
    status: str  # mapped to flowyml status
    dashboard_url: str = ""
    duration: float | None = None
    end_time: str | None = None
    steps: dict[str, CloudStepInfo] = field(default_factory=dict)


@dataclass
class CloudArtifact:
    """Normalized artifact from any cloud provider."""

    artifact_id: str
    name: str
    artifact_type: str = "Unknown"
    step: str = "unknown"
    path: str = ""
    size_bytes: int = 0
    materializer: str = "unknown"
    storage: str = "cloud"
    created_at: str | None = None
    properties: dict = field(default_factory=dict)


class CloudProvider(ABC):
    """Abstract base for cloud observability providers."""

    @abstractmethod
    def get_run_status(self, remote_job_id: str) -> CloudRunInfo | None:
        """Fetch current run status from the cloud provider."""

    @abstractmethod
    def get_step_logs(self, run: dict, step_name: str, remote_job_id: str) -> str:
        """Fetch logs for a specific step from the cloud provider."""

    @abstractmethod
    def discover_artifacts(self, run: dict, run_id: str) -> list[CloudArtifact]:
        """Discover artifacts produced by the run."""

    @abstractmethod
    def get_dashboard_url(self, remote_job_id: str) -> str:
        """Build the console/dashboard URL for this run."""


# ─── GCP / Vertex AI ────────────────────────────────────────────────


class GCPProvider(CloudProvider):
    """Google Cloud Platform — Vertex AI Pipelines."""

    def __init__(self):
        self._project_id: str | None = None

    @property
    def project_id(self) -> str:
        if not self._project_id:
            self._project_id = self._resolve_project_id()
        return self._project_id

    @staticmethod
    def _resolve_project_id() -> str:
        import subprocess

        try:
            result = subprocess.run(
                ["gcloud", "config", "get-value", "project"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            pid = result.stdout.strip()
            if pid and not pid.isdigit():
                return pid
        except Exception:
            pass
        return "unknown-project"

    @staticmethod
    def _parse_job_id(remote_job_id: str) -> tuple[str, str, str]:
        """Parse projects/{p}/locations/{l}/pipelineJobs/{j}."""
        parts = remote_job_id.split("/")
        project = parts[1] if len(parts) > 1 else ""
        location = parts[3] if len(parts) > 3 else ""
        job_short = parts[-1] if parts else ""
        return project, location, job_short

    def get_dashboard_url(self, remote_job_id: str) -> str:
        _project_num, _location, job_short = self._parse_job_id(remote_job_id)
        return f"https://console.cloud.google.com/vertex-ai/pipelines/runs/{job_short}?project={self.project_id}"

    def get_run_status(self, remote_job_id: str) -> CloudRunInfo | None:
        try:
            from google.cloud import aiplatform
        except ImportError:
            return None

        project, location, _job_short = self._parse_job_id(remote_job_id)

        try:
            aiplatform.init(project=project, location=location)
            job = aiplatform.PipelineJob.get(remote_job_id)
        except Exception as e:
            logger.warning("GCP status fetch failed: %s", e)
            return None

        state_map = {
            "PIPELINE_STATE_SUCCEEDED": "completed",
            "PIPELINE_STATE_FAILED": "failed",
            "PIPELINE_STATE_CANCELLED": "cancelled",
            "PIPELINE_STATE_RUNNING": "running",
            "PIPELINE_STATE_PENDING": "running",
            "PIPELINE_STATE_QUEUED": "running",
        }
        task_state_map = {
            "SUCCEEDED": "completed",
            "FAILED": "failed",
            "CANCELLED": "cancelled",
            "RUNNING": "running",
            "PENDING": "pending",
            "SKIPPED": "completed",
        }

        gcp_state = job.state.name if job.state else "UNKNOWN"
        status = state_map.get(gcp_state, "unknown")

        info = CloudRunInfo(
            state=gcp_state,
            status=status,
            dashboard_url=self.get_dashboard_url(remote_job_id),
        )

        # Duration
        try:
            if job.create_time and job.update_time:
                info.duration = (job.update_time - job.create_time).total_seconds()
                info.end_time = job.update_time.isoformat()
        except Exception:
            pass

        # Per-task details
        for task in job.task_details or []:
            ts = task.state.name if task.state else "UNKNOWN"
            task_status = task_state_map.get(ts, "unknown")
            dur = None
            t_start = t_end = None
            try:
                if task.start_time and task.end_time:
                    dur = (task.end_time - task.start_time).total_seconds()
                    t_start = task.start_time.isoformat()
                    t_end = task.end_time.isoformat()
            except Exception:
                pass
            error_msg = task.error.message if task.error and task.error.message else None
            info.steps[task.task_name] = CloudStepInfo(
                name=task.task_name,
                status=task_status,
                success=task_status == "completed",
                error=error_msg,
                duration=dur,
                start_time=t_start,
                end_time=t_end,
            )

        return info

    def get_step_logs(self, run: dict, step_name: str, remote_job_id: str) -> str:
        try:
            from google.cloud import logging as gcp_logging
        except ImportError:
            return "[google-cloud-logging not installed]"

        steps = run.get("steps", {})
        step_data = steps.get(step_name, {})
        execution_group = step_data.get("execution_group", "")

        _project, _loc, job_short = self._parse_job_id(remote_job_id)
        filter_str = f'resource.labels.pipeline_job_id="{job_short}"'

        try:
            client = gcp_logging.Client(project=self.project_id)
            entries = list(
                client.list_entries(
                    filter_=filter_str,
                    order_by="timestamp asc",
                    max_results=500,
                ),
            )
        except Exception as e:
            return f"[Cloud Logging error: {e}]"

        if not entries:
            return f"[No logs for pipeline: {job_short}]"

        lines = []
        for entry in entries:
            ts = entry.timestamp.strftime("%H:%M:%S") if entry.timestamp else ""
            payload = entry.payload
            if not isinstance(payload, dict):
                if payload:
                    lines.append(f"[{ts}] {payload}")
                continue

            task_name = payload.get("taskName", "")
            inner = payload.get("payload", {})
            inner_task = inner.get("taskName", "") if isinstance(inner, dict) else ""
            effective_task = task_name or inner_task

            if execution_group and effective_task and effective_task not in (execution_group, job_short, ""):
                continue

            state = (inner.get("state", "") if isinstance(inner, dict) else "") or payload.get("state", "")
            message = payload.get("message", "")
            machine = ""
            if isinstance(inner, dict):
                res = (
                    inner.get("container", {}).get("resources", {}) if isinstance(inner.get("container"), dict) else {}
                )
                m = res.get("resolvedMachineType", "")
                if m:
                    machine = f" [machine: {m}]"

            if message and state:
                lines.append(f"[{ts}] [{effective_task}] {state} — {message}{machine}")
            elif state:
                lines.append(f"[{ts}] [{effective_task}] {state}{machine}")
            elif message:
                lines.append(f"[{ts}] [{effective_task}] {message}{machine}")

        if not lines:
            return f"[No log entries for {execution_group or 'pipeline'}]"

        header = f"☁️ GCP Cloud Logging — {execution_group or 'all groups'} ({len(lines)} entries)\n{'─' * 60}\n"
        return header + "\n".join(lines)

    def discover_artifacts(self, run: dict, run_id: str) -> list[CloudArtifact]:
        import json as json_mod

        try:
            from google.cloud import storage
        except ImportError:
            return []

        bucket_name = None
        try:
            from flowyml.core.stack import get_active_stack

            stack = get_active_stack()
            bucket_name = getattr(stack.artifact_store, "bucket_name", None)
        except Exception:
            pass
        if not bucket_name:
            bucket_name = "flowyml-test-artifacts"

        prefix = f"staging/runs/{run_id}/artifacts/"
        try:
            client = storage.Client()
            blobs = list(client.bucket(bucket_name).list_blobs(prefix=prefix))
        except Exception as e:
            logger.warning("GCS scan failed: %s", e)
            return []

        # Read meta sidecars
        meta_files = {}
        for blob in blobs:
            if blob.name.endswith(".meta.json"):
                try:
                    meta = json_mod.loads(blob.download_as_text())
                    base = blob.name.rsplit(".meta.json", 1)[0].split("/")[-1]
                    meta_files[base] = meta
                except Exception:
                    pass

        # Build artifact list
        steps = run.get("steps", {})
        results = []
        for blob in blobs:
            if blob.name.endswith(".meta.json"):
                continue
            file_name = blob.name.split("/")[-1]
            base_name = file_name.rsplit(".", 1)[0]
            meta = meta_files.get(base_name, {})

            # Find producing step
            step = "unknown"
            if isinstance(steps, dict):
                for sn, sd in steps.items():
                    if isinstance(sd, dict) and base_name in sd.get("outputs", []):
                        step = sn
                        break

            results.append(
                CloudArtifact(
                    artifact_id=f"{run_id}:{base_name}",
                    name=base_name,
                    artifact_type=meta.get("artifact_type", meta.get("type", "Unknown")),
                    step=step,
                    path=f"gs://{bucket_name}/{blob.name}",
                    size_bytes=blob.size or 0,
                    materializer=meta.get("materializer", "unknown"),
                    storage="gcs",
                    created_at=blob.time_created.isoformat() if blob.time_created else None,
                    properties=meta.get("properties", {}),
                ),
            )
        return results


# ─── AWS / SageMaker ────────────────────────────────────────────────


class AWSProvider(CloudProvider):
    """Amazon Web Services — SageMaker Pipelines."""

    def get_dashboard_url(self, remote_job_id: str) -> str:
        # Format: arn:aws:sagemaker:{region}:{account}:pipeline/{name}/execution/{id}
        parts = remote_job_id.split(":")
        region = parts[3] if len(parts) > 3 else "us-east-1"
        # Extract pipeline name and execution id
        resource = parts[-1] if parts else remote_job_id
        return f"https://{region}.console.aws.amazon.com/sagemaker/home?region={region}#/pipeline-executions/{resource}"

    def get_run_status(self, remote_job_id: str) -> CloudRunInfo | None:
        try:
            import boto3
        except ImportError:
            return None

        state_map = {
            "Executing": "running",
            "Succeeded": "completed",
            "Failed": "failed",
            "Stopped": "cancelled",
            "Stopping": "running",
        }

        try:
            client = boto3.client("sagemaker")
            execution_arn = remote_job_id

            resp = client.describe_pipeline_execution(PipelineExecutionArn=execution_arn)
            sm_status = resp.get("PipelineExecutionStatus", "Unknown")
            status = state_map.get(sm_status, "unknown")

            info = CloudRunInfo(
                state=sm_status,
                status=status,
                dashboard_url=self.get_dashboard_url(remote_job_id),
            )

            # Duration
            start = resp.get("CreationTime")
            end = resp.get("LastModifiedTime")
            if start and end:
                info.duration = (end - start).total_seconds()
                info.end_time = end.isoformat()

            # Per-step details
            steps_resp = client.list_pipeline_execution_steps(
                PipelineExecutionArn=execution_arn,
            )
            for step in steps_resp.get("PipelineExecutionSteps", []):
                step_name = step.get("StepName", "unknown")
                step_status = state_map.get(step.get("StepStatus", ""), "unknown")
                dur = None
                s_start = step.get("StartTime")
                s_end = step.get("EndTime")
                if s_start and s_end:
                    dur = (s_end - s_start).total_seconds()

                info.steps[step_name] = CloudStepInfo(
                    name=step_name,
                    status=step_status,
                    success=step_status == "completed",
                    error=step.get("FailureReason"),
                    duration=dur,
                    start_time=s_start.isoformat() if s_start else None,
                    end_time=s_end.isoformat() if s_end else None,
                )

            return info
        except Exception as e:
            logger.warning("AWS status fetch failed: %s", e)
            return None

    def get_step_logs(self, run: dict, step_name: str, remote_job_id: str) -> str:
        try:
            import boto3
        except ImportError:
            return "[boto3 not installed]"

        try:
            logs_client = boto3.client("logs")
            # SageMaker logs go to /aws/sagemaker/ProcessingJobs or TrainingJobs
            log_group = "/aws/sagemaker/ProcessingJobs"
            # The log stream name typically matches the job name
            steps = run.get("steps", {})
            step_data = steps.get(step_name, {})
            job_name = step_data.get("cloud_job_name", step_name)

            resp = logs_client.get_log_events(
                logGroupName=log_group,
                logStreamName=job_name,
                startFromHead=True,
                limit=500,
            )
            events = resp.get("events", [])
            if not events:
                return f"[No CloudWatch logs for {job_name}]"

            lines = []
            for event in events:
                ts = event.get("timestamp", 0)
                from datetime import datetime, timezone

                dt = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
                msg = event.get("message", "").strip()
                if msg:
                    lines.append(f"[{dt.strftime('%H:%M:%S')}] {msg}")

            header = f"☁️ AWS CloudWatch — {step_name} ({len(lines)} entries)\n{'─' * 60}\n"
            return header + "\n".join(lines)
        except Exception as e:
            return f"[CloudWatch error: {e}]"

    def discover_artifacts(self, run: dict, run_id: str) -> list[CloudArtifact]:
        try:
            import boto3
        except ImportError:
            return []

        # Default S3 bucket pattern
        bucket_name = None
        try:
            from flowyml.core.stack import get_active_stack

            stack = get_active_stack()
            bucket_name = getattr(stack.artifact_store, "bucket_name", None)
        except Exception:
            pass

        if not bucket_name:
            return []

        prefix = f"staging/runs/{run_id}/artifacts/"
        try:
            import json as json_mod

            s3 = boto3.client("s3")
            resp = s3.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
            objects = resp.get("Contents", [])
        except Exception as e:
            logger.warning("S3 scan failed: %s", e)
            return []

        # Read meta sidecars
        meta_files = {}
        for obj in objects:
            key = obj["Key"]
            if key.endswith(".meta.json"):
                try:
                    body = s3.get_object(Bucket=bucket_name, Key=key)["Body"].read()
                    meta = json_mod.loads(body)
                    base = key.rsplit(".meta.json", 1)[0].split("/")[-1]
                    meta_files[base] = meta
                except Exception:
                    pass

        steps = run.get("steps", {})
        results = []
        for obj in objects:
            key = obj["Key"]
            if key.endswith(".meta.json"):
                continue
            file_name = key.split("/")[-1]
            base_name = file_name.rsplit(".", 1)[0]
            meta = meta_files.get(base_name, {})

            step = "unknown"
            if isinstance(steps, dict):
                for sn, sd in steps.items():
                    if isinstance(sd, dict) and base_name in sd.get("outputs", []):
                        step = sn
                        break

            results.append(
                CloudArtifact(
                    artifact_id=f"{run_id}:{base_name}",
                    name=base_name,
                    artifact_type=meta.get("artifact_type", meta.get("type", "Unknown")),
                    step=step,
                    path=f"s3://{bucket_name}/{key}",
                    size_bytes=obj.get("Size", 0),
                    materializer=meta.get("materializer", "unknown"),
                    storage="s3",
                    created_at=obj.get("LastModified", "").isoformat()
                    if hasattr(obj.get("LastModified", ""), "isoformat")
                    else None,
                    properties=meta.get("properties", {}),
                ),
            )
        return results


# ─── Azure / Azure ML ───────────────────────────────────────────────


class AzureProvider(CloudProvider):
    """Microsoft Azure — Azure Machine Learning Pipelines."""

    def get_dashboard_url(self, remote_job_id: str) -> str:
        # remote_job_id format: subscription/{sub}/resourceGroups/{rg}/...
        # For Azure ML Studio links
        return f"https://ml.azure.com/runs/{remote_job_id}"

    def get_run_status(self, remote_job_id: str) -> CloudRunInfo | None:
        try:
            from azure.ai.ml import MLClient
            from azure.identity import DefaultAzureCredential
        except ImportError:
            return None

        state_map = {
            "Completed": "completed",
            "Failed": "failed",
            "Canceled": "cancelled",
            "Running": "running",
            "Preparing": "running",
            "Queued": "running",
            "NotStarted": "pending",
        }

        try:
            credential = DefaultAzureCredential()
            # Parse job details from remote_job_id
            ml_client = MLClient(credential=credential)
            job = ml_client.jobs.get(remote_job_id)
            az_status = job.status or "Unknown"
            status = state_map.get(az_status, "unknown")

            info = CloudRunInfo(
                state=az_status,
                status=status,
                dashboard_url=job.studio_url or self.get_dashboard_url(remote_job_id),
            )

            # Duration
            if hasattr(job, "creation_context"):
                start = getattr(job.creation_context, "created_at", None)
                end = getattr(job.creation_context, "last_modified_at", None)
                if start and end:
                    info.duration = (end - start).total_seconds()
                    info.end_time = end.isoformat()

            # Per-step details (pipeline jobs have children)
            if hasattr(job, "jobs"):
                for step_name, step_job in (job.jobs or {}).items():
                    child = ml_client.jobs.get(step_job.name) if hasattr(step_job, "name") else step_job
                    child_status = state_map.get(getattr(child, "status", ""), "unknown")
                    info.steps[step_name] = CloudStepInfo(
                        name=step_name,
                        status=child_status,
                        success=child_status == "completed",
                    )

            return info
        except Exception as e:
            logger.warning("Azure status fetch failed: %s", e)
            return None

    def get_step_logs(self, run: dict, step_name: str, remote_job_id: str) -> str:
        try:
            import importlib.util

            has_azure = importlib.util.find_spec("azure.ai.ml") is not None
        except (ImportError, ModuleNotFoundError):
            has_azure = False
        if not has_azure:
            return "[azure-ai-ml not installed]"

        try:
            # Get child job logs
            steps = run.get("steps", {})
            step_data = steps.get(step_name, {})
            child_job_name = step_data.get("cloud_job_name", step_name)

            # Simplified — Azure ML SDK doesn't have a clean log streaming API
            # Fall back to downloading the user_logs/std_log.txt
            return f"[Azure ML logs: visit {self.get_dashboard_url(remote_job_id)} for step: {child_job_name}]"
        except Exception as e:
            return f"[Azure ML error: {e}]"

    def discover_artifacts(self, run: dict, run_id: str) -> list[CloudArtifact]:
        try:
            from azure.storage.blob import BlobServiceClient
        except ImportError:
            return []

        # Azure Blob Storage artifact discovery
        connection_string = None
        container_name = None
        try:
            from flowyml.core.stack import get_active_stack

            stack = get_active_stack()
            connection_string = getattr(stack.artifact_store, "connection_string", None)
            container_name = getattr(stack.artifact_store, "container_name", None)
        except Exception:
            pass

        if not connection_string or not container_name:
            return []

        prefix = f"staging/runs/{run_id}/artifacts/"
        try:
            import json as json_mod

            blob_service = BlobServiceClient.from_connection_string(connection_string)
            container_client = blob_service.get_container_client(container_name)
            blobs = list(container_client.list_blobs(name_starts_with=prefix))
        except Exception as e:
            logger.warning("Azure Blob scan failed: %s", e)
            return []

        meta_files = {}
        for blob in blobs:
            if blob.name.endswith(".meta.json"):
                try:
                    data = container_client.download_blob(blob).readall()
                    meta = json_mod.loads(data)
                    base = blob.name.rsplit(".meta.json", 1)[0].split("/")[-1]
                    meta_files[base] = meta
                except Exception:
                    pass

        steps = run.get("steps", {})
        results = []
        for blob in blobs:
            if blob.name.endswith(".meta.json"):
                continue
            file_name = blob.name.split("/")[-1]
            base_name = file_name.rsplit(".", 1)[0]
            meta = meta_files.get(base_name, {})

            step = "unknown"
            if isinstance(steps, dict):
                for sn, sd in steps.items():
                    if isinstance(sd, dict) and base_name in sd.get("outputs", []):
                        step = sn
                        break

            results.append(
                CloudArtifact(
                    artifact_id=f"{run_id}:{base_name}",
                    name=base_name,
                    artifact_type=meta.get("artifact_type", meta.get("type", "Unknown")),
                    step=step,
                    path=f"az://{container_name}/{blob.name}",
                    size_bytes=blob.size or 0,
                    materializer=meta.get("materializer", "unknown"),
                    storage="azure_blob",
                    created_at=blob.creation_time.isoformat() if blob.creation_time else None,
                    properties=meta.get("properties", {}),
                ),
            )
        return results


# ─── Provider Factory ───────────────────────────────────────────────

_PROVIDERS: dict[str, type[CloudProvider]] = {
    "vertex_ai": GCPProvider,
    "gcp": GCPProvider,
    "sagemaker": AWSProvider,
    "aws": AWSProvider,
    "azure_ml": AzureProvider,
    "azure": AzureProvider,
}


def get_provider(platform: str) -> CloudProvider | None:
    """Get the cloud provider for a given platform name."""
    cls = _PROVIDERS.get(platform.lower())
    if cls:
        return cls()
    return None


def detect_provider(run: dict) -> CloudProvider | None:
    """Auto-detect provider from run metadata."""
    platform = run.get("platform", "")
    if not platform:
        metadata = run.get("metadata", {})
        if isinstance(metadata, dict):
            platform = metadata.get("platform", "")

    if platform:
        return get_provider(platform)

    # Heuristic: check remote_job_id format
    job_id = run.get("remote_job_id", "") or ""
    if not job_id:
        metadata = run.get("metadata", {})
        if isinstance(metadata, dict):
            job_id = metadata.get("remote_job_id", "")

    if "pipelineJobs" in job_id or "locations" in job_id:
        return GCPProvider()
    if job_id.startswith("arn:aws:"):
        return AWSProvider()
    if "microsoft" in job_id.lower() or "azure" in job_id.lower():
        return AzureProvider()

    return None
