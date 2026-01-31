"""S3 Artifact Store - Native FlowyML Plugin.

This is a native FlowyML implementation for AWS S3 artifact storage,
without requiring any external framework dependencies.

Usage:
    from flowyml.plugins import get_plugin

    store = get_plugin("s3",
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


class S3ArtifactStore(ArtifactStorePlugin):
    """Native S3 artifact store for FlowyML.

    This store integrates directly with AWS S3 without any
    intermediate framework, providing full control over
    artifact storage.

    Args:
        bucket: S3 bucket name.
        prefix: Optional prefix/folder within the bucket.
        region: AWS region (uses default if not provided).
        access_key: AWS access key (uses environment/credentials if not provided).
        secret_key: AWS secret key (uses environment/credentials if not provided).
        endpoint_url: Custom S3 endpoint (for S3-compatible services like MinIO).

    Example:
        store = S3ArtifactStore(
            bucket="my-ml-artifacts",
            prefix="experiments/",
            region="us-east-1"
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
        name="s3",
        description="AWS S3 artifact storage",
        plugin_type=PluginType.ARTIFACT_STORE,
        version="1.0.0",
        author="FlowyML",
        packages=["boto3>=1.28", "s3fs>=2023.0"],
        documentation_url="https://docs.aws.amazon.com/s3/",
        tags=["artifact-store", "aws", "cloud", "popular"],
    )

    def __init__(
        self,
        bucket: str,
        prefix: str = "",
        region: str = None,
        access_key: str = None,
        secret_key: str = None,
        endpoint_url: str = None,
        **kwargs,
    ):
        """Initialize the S3 artifact store."""
        super().__init__(
            name=kwargs.pop("name", "s3"),
            bucket=bucket,
            prefix=prefix,
            region=region,
            access_key=access_key,
            secret_key=secret_key,
            endpoint_url=endpoint_url,
            **kwargs,
        )

        self._s3_client = None
        self._s3fs = None
        self._bucket = bucket
        self._prefix = prefix.strip("/")

    def initialize(self) -> None:
        """Initialize S3 connection."""
        try:
            import boto3

            # Build client kwargs
            client_kwargs = {}

            if self._config.get("region"):
                client_kwargs["region_name"] = self._config["region"]

            if self._config.get("endpoint_url"):
                client_kwargs["endpoint_url"] = self._config["endpoint_url"]

            if self._config.get("access_key") and self._config.get("secret_key"):
                client_kwargs["aws_access_key_id"] = self._config["access_key"]
                client_kwargs["aws_secret_access_key"] = self._config["secret_key"]

            self._s3_client = boto3.client("s3", **client_kwargs)

            # Optionally initialize s3fs for filesystem-like operations
            try:
                import s3fs

                fs_kwargs = {}
                if self._config.get("endpoint_url"):
                    fs_kwargs["client_kwargs"] = {"endpoint_url": self._config["endpoint_url"]}
                if self._config.get("access_key"):
                    fs_kwargs["key"] = self._config["access_key"]
                    fs_kwargs["secret"] = self._config["secret_key"]
                self._s3fs = s3fs.S3FileSystem(**fs_kwargs)
            except ImportError:
                logger.debug("s3fs not available, using boto3 only")

            self._is_initialized = True
            logger.info(f"S3 artifact store initialized: s3://{self._bucket}/{self._prefix}")

        except ImportError:
            raise ImportError(
                "boto3 is not installed. Run: flowyml plugin install s3",
            )

    def _ensure_initialized(self) -> None:
        """Ensure S3 is initialized."""
        if not self._is_initialized:
            self.initialize()

    def _get_full_path(self, path: str) -> str:
        """Get the full S3 key for a path."""
        if self._prefix:
            return f"{self._prefix}/{path.lstrip('/')}"
        return path.lstrip("/")

    def _get_s3_uri(self, path: str) -> str:
        """Get the full S3 URI for a path."""
        key = self._get_full_path(path)
        return f"s3://{self._bucket}/{key}"

    def save(self, artifact: Any, path: str) -> str:
        """Save an artifact to S3.

        Args:
            artifact: The artifact to save. Can be:
                - bytes: Saved directly
                - str: Saved as UTF-8 text
                - dict/list: Saved as JSON
                - Other objects: Pickled
            path: Path within the store.

        Returns:
            Full S3 URI of the saved artifact.
        """
        self._ensure_initialized()

        key = self._get_full_path(path)

        # Determine how to serialize
        if isinstance(artifact, bytes):
            body = artifact
        elif isinstance(artifact, str):
            body = artifact.encode("utf-8")
        elif isinstance(artifact, (dict, list)):
            body = json.dumps(artifact).encode("utf-8")
        else:
            # Pickle the object
            body = pickle.dumps(artifact)

        self._s3_client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=body,
        )

        uri = self._get_s3_uri(path)
        logger.info(f"Saved artifact to {uri}")
        return uri

    def save_file(self, local_path: str, remote_path: str) -> str:
        """Upload a local file to S3.

        Args:
            local_path: Path to local file.
            remote_path: Path in S3.

        Returns:
            Full S3 URI.
        """
        self._ensure_initialized()

        key = self._get_full_path(remote_path)
        self._s3_client.upload_file(local_path, self._bucket, key)

        uri = self._get_s3_uri(remote_path)
        logger.info(f"Uploaded {local_path} to {uri}")
        return uri

    def load(self, path: str, deserialize: bool = True) -> Any:
        """Load an artifact from S3.

        Args:
            path: Path to the artifact.
            deserialize: If True, attempts to deserialize (JSON/pickle).
                        If False, returns raw bytes.

        Returns:
            The loaded artifact.
        """
        self._ensure_initialized()

        key = self._get_full_path(path)

        response = self._s3_client.get_object(Bucket=self._bucket, Key=key)
        body = response["Body"].read()

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
        """Download a file from S3 to local filesystem.

        Args:
            remote_path: Path in S3.
            local_path: Local destination path.

        Returns:
            Local path.
        """
        self._ensure_initialized()

        key = self._get_full_path(remote_path)

        # Ensure local directory exists
        from pathlib import Path

        Path(local_path).parent.mkdir(parents=True, exist_ok=True)

        self._s3_client.download_file(self._bucket, key, local_path)
        logger.info(f"Downloaded {self._get_s3_uri(remote_path)} to {local_path}")
        return local_path

    def exists(self, path: str) -> bool:
        """Check if an artifact exists in S3.

        Args:
            path: Path to check.

        Returns:
            True if the artifact exists.
        """
        self._ensure_initialized()

        key = self._get_full_path(path)

        try:
            self._s3_client.head_object(Bucket=self._bucket, Key=key)
            return True
        except Exception:
            return False

    def delete(self, path: str) -> bool:
        """Delete an artifact from S3.

        Args:
            path: Path to delete.

        Returns:
            True if deletion was successful.
        """
        self._ensure_initialized()

        key = self._get_full_path(path)

        try:
            self._s3_client.delete_object(Bucket=self._bucket, Key=key)
            logger.info(f"Deleted {self._get_s3_uri(path)}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete {path}: {e}")
            return False

    def list(self, path: str = "") -> list[str]:  # noqa: A003
        """List artifacts in an S3 directory.

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
            response = self._s3_client.list_objects_v2(
                Bucket=self._bucket,
                Prefix=prefix,
            )

            items = []
            for obj in response.get("Contents", []):
                # Remove the base prefix to get relative path
                key = obj["Key"]
                if self._prefix:
                    key = key[len(self._prefix) + 1 :]
                items.append(key)

            return items

        except Exception as e:
            logger.error(f"Failed to list {path}: {e}")
            return []

    @property
    def root_path(self) -> str:
        """Get the root S3 URI."""
        if self._prefix:
            return f"s3://{self._bucket}/{self._prefix}"
        return f"s3://{self._bucket}"

    def get_uri(self, path: str) -> str:
        """Get the full S3 URI for a path."""
        return self._get_s3_uri(path)

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
            Full S3 URI of the saved artifact.
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

            return self._get_s3_uri(formatted_path)

        elif artifact_type == "Dataset":
            # Save dataset
            data = artifact.data if hasattr(artifact, "data") else artifact

            # Check format
            fmt = getattr(artifact, "format", "pickle")
            if fmt == "parquet":
                # Use parquet if available
                try:
                    import pandas as pd
                    import io

                    if isinstance(data, pd.DataFrame):
                        buffer = io.BytesIO()
                        data.to_parquet(buffer)
                        buffer.seek(0)
                        key = self._get_full_path(f"{formatted_path}/data.parquet")
                        self._s3_client.put_object(
                            Bucket=self._bucket,
                            Key=key,
                            Body=buffer.getvalue(),
                        )
                        return self._get_s3_uri(formatted_path)
                except ImportError:
                    pass

            # Fallback to pickle
            self.save(data, f"{formatted_path}/data.pkl")
            return self._get_s3_uri(formatted_path)

        elif artifact_type in ("Metrics", "Parameters"):
            # Save as JSON
            data = dict(artifact) if hasattr(artifact, "__iter__") else artifact
            return self.save(data, f"{formatted_path}.json")

        else:
            # Generic artifact
            return self.save(artifact, formatted_path)
