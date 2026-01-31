"""FlowyML Artifact Store Plugins."""

try:
    from flowyml.plugins.stores.s3 import S3ArtifactStore
except ImportError:
    S3ArtifactStore = None  # boto3 not installed

try:
    from flowyml.plugins.stores.gcs import GCSArtifactStore
except ImportError:
    GCSArtifactStore = None  # google-cloud-storage not installed

__all__ = ["S3ArtifactStore", "GCSArtifactStore"]
