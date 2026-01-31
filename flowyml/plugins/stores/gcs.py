"""GCS Artifact Store - Native FlowyML Plugin.

This is a native FlowyML implementation for Google Cloud Storage,
without requiring any external framework dependencies.

Usage:
    from flowyml.plugins import get_plugin

    store = get_plugin("gcs",
        bucket="my-ml-artifacts",
        prefix="experiments/"
    )

    # Save artifacts
    store.save(my_model, "models/model.pkl")

    # Load artifacts
    model = store.load("models/model.pkl")
"""

import logging
from typing import Any
import pickle
import json

from flowyml.plugins.base import ArtifactStorePlugin, PluginMetadata, PluginType

logger = logging.getLogger(__name__)


class GCSArtifactStore(ArtifactStorePlugin):
    """Native Google Cloud Storage artifact store for FlowyML.

    This store integrates directly with GCS without any
    intermediate framework, providing full control over
    artifact storage.

    Args:
        bucket: GCS bucket name.
        prefix: Optional prefix/folder within the bucket.
        project: GCP project ID (uses default if not provided).
        credentials_path: Path to service account JSON file.

    Example:
        store = GCSArtifactStore(
            bucket="my-ml-artifacts",
            prefix="experiments/",
            project="my-gcp-project"
        )

        # Save a model
        store.save(trained_model, "models/classifier.pkl")

        # Load a model
        model = store.load("models/classifier.pkl")

        # Check if exists
        if store.exists("models/classifier.pkl"):
            print("Model found!")
    """

    METADATA = PluginMetadata(
        name="gcs",
        description="Google Cloud Storage artifact storage",
        plugin_type=PluginType.ARTIFACT_STORE,
        version="1.0.0",
        author="FlowyML",
        packages=["google-cloud-storage>=2.0", "gcsfs>=2023.0"],
        documentation_url="https://cloud.google.com/storage/docs",
        tags=["artifact-store", "gcp", "cloud", "popular"],
    )

    def __init__(
        self,
        bucket: str,
        prefix: str = "",
        project: str = None,
        credentials_path: str = None,
        **kwargs,
    ):
        """Initialize the GCS artifact store."""
        super().__init__(
            name=kwargs.pop("name", "gcs"),
            bucket=bucket,
            prefix=prefix,
            project=project,
            credentials_path=credentials_path,
            **kwargs,
        )

        self._client = None
        self._bucket_obj = None
        self._gcsfs = None
        self._bucket = bucket
        self._prefix = prefix.strip("/")

    def initialize(self) -> None:
        """Initialize GCS connection."""
        try:
            from google.cloud import storage

            # Build client kwargs
            client_kwargs = {}

            if self._config.get("project"):
                client_kwargs["project"] = self._config["project"]

            if self._config.get("credentials_path"):
                from google.oauth2 import service_account

                credentials = service_account.Credentials.from_service_account_file(
                    self._config["credentials_path"],
                )
                client_kwargs["credentials"] = credentials

            self._client = storage.Client(**client_kwargs)
            self._bucket_obj = self._client.bucket(self._bucket)

            # Optionally initialize gcsfs for filesystem-like operations
            try:
                import gcsfs

                fs_kwargs = {}
                if self._config.get("project"):
                    fs_kwargs["project"] = self._config["project"]
                if self._config.get("credentials_path"):
                    fs_kwargs["token"] = self._config["credentials_path"]
                self._gcsfs = gcsfs.GCSFileSystem(**fs_kwargs)
            except ImportError:
                logger.debug("gcsfs not available, using google-cloud-storage only")

            self._is_initialized = True
            logger.info(f"GCS artifact store initialized: gs://{self._bucket}/{self._prefix}")

        except ImportError:
            raise ImportError(
                "google-cloud-storage is not installed. Run: flowyml plugin install gcs",
            )

    def _ensure_initialized(self) -> None:
        """Ensure GCS is initialized."""
        if not self._is_initialized:
            self.initialize()

    def _get_full_path(self, path: str) -> str:
        """Get the full GCS blob name for a path."""
        if self._prefix:
            return f"{self._prefix}/{path.lstrip('/')}"
        return path.lstrip("/")

    def _get_gcs_uri(self, path: str) -> str:
        """Get the full GCS URI for a path."""
        blob_name = self._get_full_path(path)
        return f"gs://{self._bucket}/{blob_name}"

    def save(self, artifact: Any, path: str) -> str:
        """Save an artifact to GCS.

        Args:
            artifact: The artifact to save. Can be:
                - bytes: Saved directly
                - str: Saved as UTF-8 text
                - dict/list: Saved as JSON
                - Other objects: Pickled
            path: Path within the store.

        Returns:
            Full GCS URI of the saved artifact.
        """
        self._ensure_initialized()

        blob_name = self._get_full_path(path)
        blob = self._bucket_obj.blob(blob_name)

        # Determine how to serialize
        if isinstance(artifact, bytes):
            blob.upload_from_string(artifact)
        elif isinstance(artifact, str):
            blob.upload_from_string(artifact.encode("utf-8"))
        elif isinstance(artifact, (dict, list)):
            blob.upload_from_string(
                json.dumps(artifact).encode("utf-8"),
                content_type="application/json",
            )
        else:
            # Pickle the object
            blob.upload_from_string(pickle.dumps(artifact))

        uri = self._get_gcs_uri(path)
        logger.info(f"Saved artifact to {uri}")
        return uri

    def save_file(self, local_path: str, remote_path: str) -> str:
        """Upload a local file to GCS.

        Args:
            local_path: Path to local file.
            remote_path: Path in GCS.

        Returns:
            Full GCS URI.
        """
        self._ensure_initialized()

        blob_name = self._get_full_path(remote_path)
        blob = self._bucket_obj.blob(blob_name)
        blob.upload_from_filename(local_path)

        uri = self._get_gcs_uri(remote_path)
        logger.info(f"Uploaded {local_path} to {uri}")
        return uri

    def load(self, path: str, deserialize: bool = True) -> Any:
        """Load an artifact from GCS.

        Args:
            path: Path to the artifact.
            deserialize: If True, attempts to deserialize (JSON/pickle).
                        If False, returns raw bytes.

        Returns:
            The loaded artifact.
        """
        self._ensure_initialized()

        blob_name = self._get_full_path(path)
        blob = self._bucket_obj.blob(blob_name)
        body = blob.download_as_bytes()

        if not deserialize:
            return body

        # Try to deserialize
        # First try JSON
        try:
            return json.loads(body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass

        # Try pickle
        try:
            return pickle.loads(body)
        except Exception:
            pass

        # Try UTF-8 string
        try:
            return body.decode("utf-8")
        except UnicodeDecodeError:
            pass

        # Return raw bytes
        return body

    def download_file(self, remote_path: str, local_path: str) -> str:
        """Download a file from GCS to local filesystem.

        Args:
            remote_path: Path in GCS.
            local_path: Local destination path.

        Returns:
            Local path.
        """
        self._ensure_initialized()

        blob_name = self._get_full_path(remote_path)
        blob = self._bucket_obj.blob(blob_name)

        # Ensure local directory exists
        from pathlib import Path

        Path(local_path).parent.mkdir(parents=True, exist_ok=True)

        blob.download_to_filename(local_path)
        logger.info(f"Downloaded {self._get_gcs_uri(remote_path)} to {local_path}")
        return local_path

    def exists(self, path: str) -> bool:
        """Check if an artifact exists in GCS.

        Args:
            path: Path to check.

        Returns:
            True if the artifact exists.
        """
        self._ensure_initialized()

        blob_name = self._get_full_path(path)
        blob = self._bucket_obj.blob(blob_name)
        return blob.exists()

    def delete(self, path: str) -> bool:
        """Delete an artifact from GCS.

        Args:
            path: Path to delete.

        Returns:
            True if deletion was successful.
        """
        self._ensure_initialized()

        blob_name = self._get_full_path(path)
        blob = self._bucket_obj.blob(blob_name)

        try:
            blob.delete()
            logger.info(f"Deleted {self._get_gcs_uri(path)}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete {path}: {e}")
            return False

    def list(self, path: str = "") -> list[str]:  # noqa: A003
        """List artifacts in a GCS directory.

        Args:
            path: Directory path to list.

        Returns:
            List of artifact paths (relative to prefix).
        """
        self._ensure_initialized()

        prefix = self._get_full_path(path)
        if prefix and not prefix.endswith("/"):
            prefix += "/"

        try:
            blobs = self._client.list_blobs(self._bucket, prefix=prefix)

            items = []
            for blob in blobs:
                # Remove the base prefix to get relative path
                name = blob.name
                if self._prefix:
                    name = name[len(self._prefix) + 1 :]
                items.append(name)

            return items

        except Exception as e:
            logger.error(f"Failed to list {path}: {e}")
            return []

    @property
    def root_path(self) -> str:
        """Get the root GCS URI."""
        if self._prefix:
            return f"gs://{self._bucket}/{self._prefix}"
        return f"gs://{self._bucket}"

    def get_uri(self, path: str) -> str:
        """Get the full GCS URI for a path."""
        return self._get_gcs_uri(path)

    def get_signed_url(self, path: str, expiration_minutes: int = 60) -> str:
        """Generate a signed URL for temporary access.

        Args:
            path: Path to the artifact.
            expiration_minutes: URL expiration time in minutes.

        Returns:
            Signed URL string.
        """
        self._ensure_initialized()

        from datetime import timedelta

        blob_name = self._get_full_path(path)
        blob = self._bucket_obj.blob(blob_name)

        url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(minutes=expiration_minutes),
            method="GET",
        )
        return url

    def save_typed_artifact(
        self,
        artifact: Any,
        path: str,
        run_id: str = "",
        step_name: str = "",
    ) -> str:
        """Save a FlowyML typed artifact with proper handling.

        Handles Model, Dataset, Metrics, and Parameters types with
        appropriate serialization and metadata.

        Args:
            artifact: A FlowyML artifact type (Model, Dataset, etc.)
            path: Base path (will be formatted with run_id/step_name)
            run_id: Pipeline run ID for path templating
            step_name: Step name for path templating

        Returns:
            Full GCS URI of the saved artifact.
        """
        self._ensure_initialized()

        # Detect artifact type
        artifact_type = type(artifact).__name__

        # Format path with run info
        formatted_path = path.format(
            run_id=run_id,
            step_name=step_name,
            artifact_name=artifact_type.lower(),
        )

        # Handle different artifact types
        if artifact_type == "Model":
            # Save model data
            model_data = artifact.data if hasattr(artifact, "data") else artifact
            model_path = f"{formatted_path}/model.pkl"
            self.save(model_data, model_path)

            # Save metadata
            if hasattr(artifact, "metadata") and artifact.metadata:
                self.save(artifact.metadata, f"{formatted_path}/metadata.json")

            return self._get_gcs_uri(formatted_path)

        elif artifact_type == "Dataset":
            # Save dataset
            data = artifact.data if hasattr(artifact, "data") else artifact

            # Check format
            fmt = getattr(artifact, "format", "pickle")
            if fmt == "parquet":
                # Use parquet if available
                try:
                    import pandas as pd

                    if isinstance(data, pd.DataFrame):
                        with self._bucket_obj.blob(
                            self._get_full_path(f"{formatted_path}/data.parquet"),
                        ).open("wb") as f:
                            data.to_parquet(f)
                        return self._get_gcs_uri(formatted_path)
                except ImportError:
                    pass

            # Fallback to pickle
            self.save(data, f"{formatted_path}/data.pkl")
            return self._get_gcs_uri(formatted_path)

        elif artifact_type in ("Metrics", "Parameters"):
            # Save as JSON
            data = dict(artifact) if hasattr(artifact, "__iter__") else artifact
            return self.save(data, f"{formatted_path}.json")

        else:
            # Generic artifact
            return self.save(artifact, formatted_path)
