"""Remote storage backends for flowyml."""

import shutil
import tempfile
import cloudpickle
from typing import Any
from pathlib import Path
import requests

from flowyml.storage.metadata import MetadataStore
from flowyml.storage.artifacts import ArtifactStore


class RemoteMetadataStore(MetadataStore):
    """Remote metadata storage using FlowyML API."""

    def __init__(self, api_url: str, api_token: str | None = None):
        """Initialize remote metadata store.

        Args:
            api_url: Base URL of the FlowyML API (e.g. http://localhost:8080/api)
            api_token: Optional API token for authentication
        """
        self.api_url = api_url.rstrip("/")
        self._session = requests.Session()
        if api_token:
            self._session.headers.update({"Authorization": f"Bearer {api_token}"})

    def _url(self, path: str) -> str:
        return f"{self.api_url}/{path.lstrip('/')}"

    def save_run(self, run_id: str, metadata: dict) -> None:
        """Save run metadata to remote server."""
        url = self._url("runs/")

        # Extract fields expected by API
        payload = {
            "run_id": run_id,
            "pipeline_name": metadata.get("pipeline_name", "unknown"),
            "status": metadata.get("status", "pending"),
            "start_time": metadata.get("start_time"),
            "end_time": metadata.get("end_time"),
            "duration": metadata.get("duration"),
            "project": metadata.get("project"),
            "metadata": metadata,  # Full metadata blob
            "metrics": metadata.get("metrics"),
            "parameters": metadata.get("parameters"),
        }

        response = self._session.post(url, json=payload)
        response.raise_for_status()

    def load_run(self, run_id: str) -> dict | None:
        """Load run metadata from remote server."""
        url = self._url(f"runs/{run_id}")
        try:
            response = self._session.get(url)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()
        except requests.RequestException:
            return None

    def list_runs(self, limit: int | None = None, **filters) -> list[dict]:
        """List all runs."""
        url = self._url("runs/")
        params = filters.copy()
        if limit:
            params["limit"] = limit

        response = self._session.get(url, params=params)
        response.raise_for_status()
        return response.json().get("runs", [])

    def list_pipelines(self) -> list[str]:
        """List all unique pipeline names."""
        # Try to use the pipelines endpoint
        try:
            url = self._url("pipelines/")
            response = self._session.get(url)
            if response.status_code == 200:
                pipelines = response.json().get("pipelines", [])
                return sorted([p["name"] for p in pipelines])
        except Exception:
            pass

        # Fallback to querying runs
        try:
            runs = self.list_runs(limit=1000)
            pipelines = {r.get("pipeline_name") for r in runs if r.get("pipeline_name")}
            return sorted(pipelines)
        except Exception:
            return []

    def save_artifact(self, artifact_id: str, metadata: dict) -> None:
        """Save artifact metadata."""
        url = self._url("assets/")

        payload = {
            "artifact_id": artifact_id,
            "name": metadata.get("name", "unknown"),
            "type": metadata.get("type", "unknown"),
            "run_id": metadata.get("run_id", "unknown"),
            "step": metadata.get("step", "unknown"),
            "project": metadata.get("project"),
            "metadata": metadata,
            "value": metadata.get("value"),
        }

        response = self._session.post(url, json=payload)
        response.raise_for_status()

    def load_artifact(self, artifact_id: str) -> dict | None:
        """Load artifact metadata."""
        url = self._url(f"assets/{artifact_id}")
        try:
            response = self._session.get(url)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()
        except requests.RequestException:
            return None

    def list_assets(self, limit: int | None = None, **filters) -> list[dict]:
        """List assets with optional filters."""
        url = self._url("assets/")
        params = filters.copy()
        if limit:
            params["limit"] = limit

        response = self._session.get(url, params=params)
        response.raise_for_status()
        return response.json().get("assets", [])

    def query(self, **filters) -> list[dict]:
        """Query runs with filters."""
        return self.list_runs(**filters)

    def save_metric(self, run_id: str, name: str, value: float, step: int = 0) -> None:
        """Save a single metric value."""
        url = self._url("metrics/")
        payload = {
            "run_id": run_id,
            "name": name,
            "value": value,
            "step": step,
        }
        response = self._session.post(url, json=payload)
        response.raise_for_status()

    def get_metrics(self, run_id: str, name: str | None = None) -> list[dict]:
        """Get metrics for a run."""
        url = self._url(f"runs/{run_id}/metrics")
        response = self._session.get(url)
        response.raise_for_status()
        metrics = response.json().get("metrics", [])
        if name:
            return [m for m in metrics if m["name"] == name]
        return metrics

    def save_experiment(self, experiment_id: str, name: str, description: str = "", tags: dict = None) -> None:
        """Save experiment metadata."""
        url = self._url("experiments/")
        payload = {
            "experiment_id": experiment_id,
            "name": name,
            "description": description,
            "tags": tags or {},
            # Project is handled via separate update if needed, or we can add it to payload if API supported it
            # The API we added supports project in payload
            "project": tags.get("project") if tags else None,
        }
        response = self._session.post(url, json=payload)
        response.raise_for_status()

    def log_experiment_run(
        self,
        experiment_id: str,
        run_id: str,
        metrics: dict = None,
        parameters: dict = None,
    ) -> None:
        """Log a run to an experiment."""
        url = self._url(f"experiments/{experiment_id}/runs")
        payload = {
            "run_id": run_id,
            "metrics": metrics,
            "parameters": parameters,
        }
        response = self._session.post(url, json=payload)
        response.raise_for_status()

    def list_experiments(self) -> list[dict]:
        """List all experiments."""
        url = self._url("experiments/")
        response = self._session.get(url)
        response.raise_for_status()
        return response.json().get("experiments", [])

    def get_experiment(self, experiment_id: str) -> dict | None:
        """Get experiment details."""
        url = self._url(f"experiments/{experiment_id}")
        try:
            response = self._session.get(url)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()
        except requests.RequestException:
            return None

    def update_experiment_project(self, experiment_name: str, project_name: str) -> None:
        """Update the project for an experiment."""
        url = self._url(f"experiments/{experiment_name}/project")
        payload = {"project_name": project_name}
        response = self._session.put(url, json=payload)
        response.raise_for_status()

    def log_model_metrics(
        self,
        project: str,
        model_name: str,
        metrics: dict[str, float],
        run_id: str | None = None,
        environment: str | None = None,
        tags: dict | None = None,
    ) -> None:
        """Log production model metrics."""
        url = self._url("metrics/log")
        payload = {
            "project": project,
            "model_name": model_name,
            "metrics": metrics,
            "run_id": run_id,
            "environment": environment,
            "tags": tags,
        }
        response = self._session.post(url, json=payload)
        response.raise_for_status()

    def list_model_metrics(
        self,
        project: str | None = None,
        model_name: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """List logged model metrics."""
        url = self._url("metrics")
        params = {"limit": limit}
        if project:
            params["project"] = project
        if model_name:
            params["model_name"] = model_name

        response = self._session.get(url, params=params)
        response.raise_for_status()
        return response.json().get("metrics", [])

    def save_trace_event(self, event: dict) -> None:
        """Save a trace event."""
        url = self._url("traces/")
        response = self._session.post(url, json=event)
        response.raise_for_status()

    def save_pipeline_definition(self, pipeline_name: str, definition: dict) -> None:
        """Save pipeline definition."""
        url = self._url("pipelines/")
        payload = {"pipeline_name": pipeline_name, "definition": definition}
        response = self._session.post(url, json=payload)
        response.raise_for_status()

    def update_pipeline_project(self, pipeline_name: str, project_name: str) -> None:
        """Update the project for a pipeline."""
        url = self._url(f"pipelines/{pipeline_name}/project")
        payload = {"project_name": project_name}
        response = self._session.put(url, json=payload)
        response.raise_for_status()

    def get_statistics(self) -> dict:
        """Get global statistics."""
        url = self._url("stats/")
        response = self._session.get(url)
        response.raise_for_status()
        return response.json()


class RemoteArtifactStore(ArtifactStore):
    """Remote artifact storage using FlowyML API."""

    def __init__(self, api_url: str, local_cache_dir: str = ".flowyml/cache/artifacts", api_token: str | None = None):
        """Initialize remote artifact store.

        Args:
            api_url: Base URL of the FlowyML API
            local_cache_dir: Directory to cache downloaded artifacts
            api_token: Optional API token for authentication
        """
        self.api_url = api_url.rstrip("/")
        self.local_cache = Path(local_cache_dir)
        self.local_cache.mkdir(parents=True, exist_ok=True)
        self._session = requests.Session()
        if api_token:
            self._session.headers.update({"Authorization": f"Bearer {api_token}"})

    def _url(self, path: str) -> str:
        return f"{self.api_url}/{path.lstrip('/')}"

    def save(self, artifact: Any, path: str, metadata: dict | None = None) -> str:
        """Save artifact to remote server.

        This method handles serialization (if needed), metadata creation/validation,
        and file upload to the remote server.

        Args:
            artifact: Object to save
            path: Path/identifier for the artifact
            metadata: Optional metadata dictionary

        Returns:
            The remote path or identifier
        """
        import pickle
        import hashlib
        import tempfile

        # 1. Determine artifact_id
        if metadata and metadata.get("artifact_id"):
            artifact_id = metadata["artifact_id"]
        else:
            # Generate deterministic ID from path if not provided
            artifact_id = hashlib.md5(path.encode()).hexdigest()

        # 2. Serialize locally to a temporary file
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            pickle.dump(artifact, tmp)
            tmp_path = Path(tmp.name)

        try:
            # 3. Ensure metadata exists on server
            # We try to load it first. If not found, we create a placeholder.
            # This is critical because the upload endpoint requires existing metadata.
            if not self.load_artifact_metadata(artifact_id):
                create_url = self._url("assets/")
                payload = {
                    "artifact_id": artifact_id,
                    "name": metadata.get("name", "unknown") if metadata else "unknown",
                    "type": type(artifact).__name__,
                    "run_id": metadata.get("run_id", "unknown") if metadata else "unknown",
                    "step": metadata.get("step", "unknown") if metadata else "unknown",
                    "project": metadata.get("project") if metadata else None,
                    "metadata": metadata or {},
                }
                self._session.post(create_url, json=payload)

            # 4. Upload content
            upload_url = self._url(f"assets/{artifact_id}/upload")
            with open(tmp_path, "rb") as f:
                # Use a generic filename for pickle dump
                files = {"file": ("artifact.pkl", f)}
                response = self._session.post(upload_url, files=files)
                response.raise_for_status()

            remote_path = response.json().get("path")
            return remote_path or path

        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def materialize(self, obj: Any, name: str, run_id: str, step_name: str, project_name: str = "default") -> str:
        """Materialize artifact to remote storage.

        Uses registered materializers if available, otherwise falls back to cloudpickle.
        Handles directory compression if materializer produces a directory.
        """
        from flowyml.storage.materializers.base import get_materializer

        artifact_id = f"{run_id}_{step_name}_{name}"

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            file_path = temp_path / name

            # 1. Materialize locally
            materializer = get_materializer(obj)
            if materializer:
                materializer.save(obj, file_path)
                if file_path.is_dir():
                    shutil.make_archive(str(file_path), "zip", file_path)
                    upload_path = file_path.with_suffix(".zip")
                    filename = f"{name}.zip"
                else:
                    upload_path = file_path
                    filename = name
            else:
                # Fallback to cloudpickle
                upload_path = temp_path / f"{name}.pkl"
                with open(upload_path, "wb") as f:
                    cloudpickle.dump(obj, f)
                filename = f"{name}.pkl"

            # 2. Create metadata
            create_url = self._url("assets/")
            payload = {
                "artifact_id": artifact_id,
                "name": name,
                "type": type(obj).__name__,  # Store simple type name for reference
                # Store full type path in metadata for robust loading
                "run_id": run_id,
                "step": step_name,
                "project": project_name,
                "metadata": {
                    "type_module": type(obj).__module__,
                    "type_name": type(obj).__name__,
                },
            }
            # Ensure we don't fail if it already exists (idempotency)
            # The API should handle upserts or we check existence.
            # For now, we post. If it exists, we might get 409 or it updates.
            # Our current API implementation updates if exists.
            self._session.post(create_url, json=payload)

            # 3. Upload content
            upload_url = self._url(f"assets/{artifact_id}/upload")
            with open(upload_path, "rb") as f:
                files = {"file": (filename, f)}
                response = self._session.post(upload_url, files=files)
                response.raise_for_status()

            return response.json().get("path")

    def load(self, path: str) -> Any:
        """Load artifact from remote storage.

        Args:
            path: The remote path or artifact ID.

        Returns:
            The deserialized object.
        """
        import re
        import pickle
        from flowyml.storage.materializers.base import get_materializer_by_type_name

        # 1. Determine artifact_id
        # Try to treat path as artifact_id first
        if self.load_artifact_metadata(path):
            artifact_id = path
        else:
            # Try to extract ID from path (project/run_id/artifact_id/filename)
            parts = Path(path).parts
            if len(parts) >= 2:
                potential_id = parts[-2]
                if self.load_artifact_metadata(potential_id):
                    artifact_id = potential_id
                else:
                    # Fallback: assume path is ID even if metadata check failed (maybe network issue?)
                    # or just fail? Let's assume path is ID as last resort.
                    artifact_id = path
            else:
                artifact_id = path

        # 2. Get metadata to help with deserialization
        meta = self.load_artifact_metadata(artifact_id)

        # 3. Download to local cache
        download_url = self._url(f"assets/{artifact_id}/download")
        response = self._session.get(download_url, stream=True)
        response.raise_for_status()

        local_path = self.local_cache / artifact_id
        local_path.mkdir(parents=True, exist_ok=True)

        filename = "content"
        if "content-disposition" in response.headers:
            fname = re.findall("filename=(.+)", response.headers["content-disposition"])
            if fname:
                filename = fname[0].strip('"')

        file_path = local_path / filename

        with open(file_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        # 4. Handle Decompression
        load_path = file_path
        if filename.endswith(".zip"):
            shutil.unpack_archive(file_path, local_path)
            # The content is inside the directory.
            # Materializers usually expect the directory path or file path.
            # If it was a directory, we pass the directory.
            # The directory name matches the artifact name usually.
            # Let's assume the unzipped content is what we want.
            # If we zipped "name", it unzips to "name".
            # We need to find the unzipped item.
            # It's likely the filename without .zip
            unzipped_name = filename[:-4]
            load_path = local_path / unzipped_name

        # 5. Deserialize
        # A. Try Pickle/Cloudpickle
        if filename.endswith(".pkl"):
            with open(file_path, "rb") as f:
                return pickle.load(f)

        # B. Try Materializer using metadata
        if meta:
            # Try to construct full type name
            type_module = meta.get("metadata", {}).get("type_module")
            type_name = meta.get("metadata", {}).get("type_name")

            if type_module and type_name:
                full_type_name = f"{type_module}.{type_name}"
                materializer = get_materializer_by_type_name(full_type_name)
                if materializer:
                    return materializer.load(load_path)

            # Fallback: try simple type name from 'type' field
            simple_type = meta.get("type")
            if simple_type:
                # This is less reliable but worth a try
                # We need to iterate registry to find matching class name
                # This is handled by get_materializer_by_type_name logic for simple names
                # But we need a dummy module prefix to trigger that logic if we only have simple name?
                # Actually get_materializer_by_type_name handles simple name matching too.
                materializer = get_materializer_by_type_name(simple_type)
                if materializer:
                    return materializer.load(load_path)

        # C. Fallback: Return path
        # If we can't deserialize, we return the path so the user can handle it manually.
        return load_path

    def load_artifact_metadata(self, artifact_id: str) -> dict | None:
        """Helper to load metadata."""
        url = self._url(f"assets/{artifact_id}")
        try:
            response = self._session.get(url)
            if response.status_code == 404:
                return None
            return response.json()
        except Exception:
            return None

    def exists(self, path: str) -> bool:
        """Check if artifact exists."""
        # Try to treat path as artifact_id
        meta = self.load_artifact_metadata(path)
        if meta:
            return True

        # Try to extract ID from path
        parts = Path(path).parts
        if len(parts) >= 2:
            potential_id = parts[-2]
            meta = self.load_artifact_metadata(potential_id)
            if meta:
                return True

        return False

    def delete(self, path: str) -> None:
        """Delete artifact."""
        # Extract ID
        artifact_id = path
        parts = Path(path).parts
        if len(parts) >= 2:
            potential_id = parts[-2]
            if self.load_artifact_metadata(potential_id):
                artifact_id = potential_id

        url = self._url(f"assets/{artifact_id}")
        self._session.delete(url)

    def list_artifacts(self, prefix: str = "") -> list[str]:
        """List artifacts."""
        url = self._url("assets/")
        response = self._session.get(url, params={"limit": 1000})
        if response.status_code != 200:
            return []

        assets = response.json().get("assets", [])
        paths = [a.get("path") for a in assets if a.get("path")]

        if prefix:
            return [p for p in paths if p.startswith(prefix)]
        return paths
