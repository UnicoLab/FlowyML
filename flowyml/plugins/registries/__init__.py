"""FlowyML Container Registry Plugins."""

try:
    from flowyml.plugins.registries.gcr import GCRRegistry
except ImportError:
    GCRRegistry = None

try:
    from flowyml.plugins.registries.ecr import ECRRegistry
except ImportError:
    ECRRegistry = None

__all__ = ["GCRRegistry", "ECRRegistry"]
