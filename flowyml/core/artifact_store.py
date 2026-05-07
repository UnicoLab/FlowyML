"""Artifact Store — Cross-group artifact persistence for remote execution.

When running per-group on Vertex AI, each group runs in its own container.
Step outputs from group A need to be available as inputs to group B.
This module provides artifact stores backed by GCS or local filesystem,
using the FlowyML materializer system for type-aware serialization.

Serialization is handled by the materializer registry:
    - FlowyML Artifact types → metadata JSON + cloudpickle data
    - ArviZ InferenceData → netCDF
    - pandas DataFrame → parquet
    - numpy ndarray → .npy
    - Everything else → cloudpickle (handles PyMC, sklearn, closures, etc.)

Usage inside step runner:
    store = GCSArtifactStore("gs://bucket/staging", run_id="abc123")
    store.save("payment_dataset", df)       # After group A completes
    df = store.load("payment_dataset")      # At group B start
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

logger = logging.getLogger("flowyml.artifact_store.gcs")


class GCSArtifactStore:
    """GCS-backed artifact store for cross-group artifact passing.

    Uses the materializer registry to serialize objects with the best
    available strategy for each type. A metadata sidecar (.meta.json)
    records which materializer and file extension were used.

    Args:
        bucket_uri: GCS bucket URI (e.g., "gs://bucket-name/staging")
        run_id: Unique run identifier for namespacing
    """

    def __init__(self, bucket_uri: str, run_id: str):
        self.bucket_uri = bucket_uri.rstrip("/")
        self.run_id = run_id
        self._prefix = f"{self.bucket_uri}/runs/{run_id}/artifacts"

    def save(self, name: str, value: Any) -> str:
        """Serialize and upload an artifact to GCS.

        Uses the materializer registry to find the best serializer for
        the value's type. Saves a metadata sidecar alongside the data.

        Args:
            name: Artifact name (e.g., "bayesian_model")
            value: Python object to serialize

        Returns:
            GCS URI of the saved artifact
        """
        from google.cloud import storage
        from flowyml.core.materializers import materializer_registry

        # Find the right materializer for this type
        materializer = materializer_registry.get_materializer(value)
        mat_name = type(materializer).__name__
        artifact_type = type(value).__name__
        extension = materializer.get_extension()

        # Serialize to a temp directory
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_path = Path(tmp_dir) / name
            materializer.save(value, base_path)

            # Find all files produced by the materializer
            produced_files = list(Path(tmp_dir).glob(f"{name}*"))
            if not produced_files:
                raise RuntimeError(
                    f"Materializer {mat_name} produced no files for '{name}'",
                )

            # Upload each file to GCS
            bucket_name, _ = self._parse_gcs_uri(self._prefix)
            client = storage.Client()
            bucket = client.bucket(bucket_name)

            uploaded_paths = []
            total_size = 0
            for local_file in produced_files:
                blob_uri = f"{self._prefix}/{local_file.name}"
                _, blob_name = self._parse_gcs_uri(blob_uri)
                blob = bucket.blob(blob_name)
                blob.upload_from_filename(str(local_file))
                uploaded_paths.append(blob_uri)
                total_size += local_file.stat().st_size

            # Write metadata sidecar
            meta = {
                "name": name,
                "materializer": mat_name,
                "artifact_type": artifact_type,
                "extension": extension,
                "files": [p.name for p in produced_files],
                "total_size_bytes": total_size,
            }
            meta_uri = f"{self._prefix}/{name}.meta.json"
            _, meta_blob_name = self._parse_gcs_uri(meta_uri)
            meta_blob = bucket.blob(meta_blob_name)
            meta_blob.upload_from_string(
                json.dumps(meta, indent=2),
                content_type="application/json",
            )

        primary_uri = f"{self._prefix}/{name}{extension}"
        logger.info(
            "💾 Saved artifact to GCS: %s → %s (%s via %s, %.1f KB)",
            name,
            primary_uri,
            artifact_type,
            mat_name,
            total_size / 1024,
        )
        return primary_uri

    def load(self, name: str) -> Any:
        """Download and deserialize an artifact from GCS.

        Reads the metadata sidecar to determine which materializer
        to use for deserialization.

        Args:
            name: Artifact name

        Returns:
            Deserialized Python object

        Raises:
            FileNotFoundError: If artifact doesn't exist in GCS
        """
        from google.cloud import storage
        from flowyml.core.materializers import materializer_registry

        bucket_name, _ = self._parse_gcs_uri(self._prefix)
        client = storage.Client()
        bucket = client.bucket(bucket_name)

        # Read metadata sidecar
        meta_uri = f"{self._prefix}/{name}.meta.json"
        _, meta_blob_name = self._parse_gcs_uri(meta_uri)
        meta_blob = bucket.blob(meta_blob_name)

        if meta_blob.exists():
            meta = json.loads(meta_blob.download_as_string())
            mat_name = meta.get("materializer", "CloudPickleMaterializer")
            files = meta.get("files", [])
            artifact_type = meta.get("artifact_type", "unknown")
        else:
            # Legacy fallback: no metadata sidecar, assume pickle
            mat_name = "CloudPickleMaterializer"
            files = [f"{name}.pkl"]
            artifact_type = "unknown"

        # Download all artifact files to temp directory
        with tempfile.TemporaryDirectory() as tmp_dir:
            for filename in files:
                blob_uri = f"{self._prefix}/{filename}"
                _, blob_name = self._parse_gcs_uri(blob_uri)
                blob = bucket.blob(blob_name)
                if blob.exists():
                    local_path = Path(tmp_dir) / filename
                    blob.download_to_filename(str(local_path))

            # Find materializer and deserialize
            materializer = materializer_registry.get_materializer_for_type(artifact_type)
            # Override with exact materializer from metadata if possible
            if mat_name == "FlowyMLArtifactMaterializer":
                from flowyml.core.materializers import FlowyMLArtifactMaterializer

                materializer = FlowyMLArtifactMaterializer()
            elif mat_name == "CloudPickleMaterializer":
                from flowyml.core.materializers import CloudPickleMaterializer

                materializer = CloudPickleMaterializer()

            base_path = Path(tmp_dir) / name
            value = materializer.load(base_path)

        total_size = sum(
            bucket.blob(self._parse_gcs_uri(f"{self._prefix}/{f}")[1]).size or 0
            for f in files
            if bucket.blob(self._parse_gcs_uri(f"{self._prefix}/{f}")[1]).exists()
        )

        logger.info(
            "📦 Loaded artifact from GCS: %s (%s via %s, %.1f KB)",
            name,
            artifact_type,
            mat_name,
            total_size / 1024 if total_size else 0,
        )
        return value

    def exists(self, name: str) -> bool:
        """Check if an artifact exists in GCS.

        Checks for metadata sidecar first (new format), then
        falls back to checking for a .pkl file (legacy format).
        """
        from google.cloud import storage

        bucket_name, _ = self._parse_gcs_uri(self._prefix)
        client = storage.Client()
        bucket = client.bucket(bucket_name)

        # Check metadata sidecar (new format)
        meta_uri = f"{self._prefix}/{name}.meta.json"
        _, meta_blob_name = self._parse_gcs_uri(meta_uri)
        if bucket.blob(meta_blob_name).exists():
            return True

        # Legacy fallback: check .pkl
        pkl_uri = f"{self._prefix}/{name}.pkl"
        _, pkl_blob_name = self._parse_gcs_uri(pkl_uri)
        return bucket.blob(pkl_blob_name).exists()

    def list_artifacts(self) -> list[str]:
        """List all artifacts for this run."""
        from google.cloud import storage

        bucket_name, prefix = self._parse_gcs_uri(self._prefix)

        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blobs = bucket.list_blobs(prefix=prefix)

        artifacts = set()
        for blob in blobs:
            rel = blob.name.replace(prefix + "/", "")
            if rel:
                # Extract artifact name (strip any extension)
                base = rel.split(".")[0]
                if base:
                    artifacts.add(base)
        return sorted(artifacts)

    @staticmethod
    def _parse_gcs_uri(uri: str) -> tuple[str, str]:
        """Parse gs://bucket/path into (bucket, path)."""
        uri = uri.replace("gs://", "")
        parts = uri.split("/", 1)
        bucket = parts[0]
        blob_path = parts[1] if len(parts) > 1 else ""
        return bucket, blob_path


class LocalArtifactStore:
    """Local filesystem artifact store (for local execution and testing).

    Same interface as GCSArtifactStore but uses local disk.
    Uses the materializer registry for type-aware serialization.
    """

    def __init__(self, base_dir: str, run_id: str):
        self.base_dir = Path(base_dir)
        self.run_id = run_id
        self._dir = self.base_dir / run_id / "artifacts"
        self._dir.mkdir(parents=True, exist_ok=True)

    def save(self, name: str, value: Any) -> str:
        """Save artifact to local disk using materializer."""
        from flowyml.core.materializers import materializer_registry

        materializer = materializer_registry.get_materializer(value)
        mat_name = type(materializer).__name__
        artifact_type = type(value).__name__
        extension = materializer.get_extension()

        base_path = self._dir / name
        materializer.save(value, base_path)

        # Find all produced files
        produced_files = list(self._dir.glob(f"{name}*"))
        total_size = sum(f.stat().st_size for f in produced_files if f.is_file())

        # Write metadata sidecar
        meta = {
            "name": name,
            "materializer": mat_name,
            "artifact_type": artifact_type,
            "extension": extension,
            "files": [p.name for p in produced_files if not p.name.endswith(".meta.json")],
            "total_size_bytes": total_size,
        }
        meta_path = self._dir / f"{name}.meta.json"
        meta_path.write_text(json.dumps(meta, indent=2))

        primary_path = self._dir / f"{name}{extension}"
        logger.info(
            "💾 Saved artifact locally: %s → %s (%s via %s, %.1f KB)",
            name,
            primary_path,
            artifact_type,
            mat_name,
            total_size / 1024,
        )
        return str(primary_path)

    def load(self, name: str) -> Any:
        """Load artifact from local disk using materializer."""
        from flowyml.core.materializers import materializer_registry

        meta_path = self._dir / f"{name}.meta.json"
        if meta_path.exists():
            meta = json.loads(meta_path.read_text())
            mat_name = meta.get("materializer", "CloudPickleMaterializer")
            artifact_type = meta.get("artifact_type", "unknown")
        else:
            mat_name = "CloudPickleMaterializer"
            artifact_type = "unknown"

        # Find materializer
        materializer = materializer_registry.get_materializer_for_type(artifact_type)
        if mat_name == "FlowyMLArtifactMaterializer":
            from flowyml.core.materializers import FlowyMLArtifactMaterializer

            materializer = FlowyMLArtifactMaterializer()
        elif mat_name == "CloudPickleMaterializer":
            from flowyml.core.materializers import CloudPickleMaterializer

            materializer = CloudPickleMaterializer()

        base_path = self._dir / name
        value = materializer.load(base_path)

        logger.info(
            "📦 Loaded artifact locally: %s (%s via %s)",
            name,
            artifact_type,
            mat_name,
        )
        return value

    def exists(self, name: str) -> bool:
        """Check if artifact exists."""
        meta_path = self._dir / f"{name}.meta.json"
        if meta_path.exists():
            return True
        # Legacy fallback
        return (self._dir / f"{name}.pkl").exists()

    def list_artifacts(self) -> list[str]:
        """List all artifacts for this run."""
        artifacts = set()
        for p in self._dir.iterdir():
            if p.is_file():
                base = p.name.split(".")[0]
                if base:
                    artifacts.add(base)
        return sorted(artifacts)


def create_artifact_store(
    run_id: str,
    staging_bucket: str | None = None,
    local_dir: str | None = None,
) -> GCSArtifactStore | LocalArtifactStore:
    """Factory to create the appropriate artifact store.

    Uses GCS if a staging bucket is provided, otherwise falls back to local.
    """
    if staging_bucket and staging_bucket.startswith("gs://"):
        return GCSArtifactStore(staging_bucket, run_id)
    else:
        base = local_dir or os.environ.get(
            "FLOWYML_ARTIFACT_DIR",
            "/tmp/flowyml_artifacts",  # noqa: S108
        )
        return LocalArtifactStore(base, run_id)
