"""Stack management for flowyml.

This module provides both the runtime ``Stack`` classes (local, GCP, AWS, Azure)
and the enterprise governance layer (``StackDefinition``, ``EnterpriseStackRegistry``,
``PolicyEngine``).

Quick start::

    # By name (resolved via enterprise registry or legacy config)
    Pipeline("training", stack="aml_cpu_small")

    # By environment
    Pipeline("training", env="prod")

    # By definition
    from flowyml.stacks.enterprise import StackDefinition

    stack = StackDefinition.from_yaml("stacks/my_stack.yaml")
    Pipeline("training", stack=stack)

    # Context manager
    from flowyml.stacks import use_stack

    with use_stack("staging"):
        pipeline.run()
"""

from flowyml.stacks.base import Stack, StackConfig
from flowyml.stacks.local import LocalStack
from flowyml.stacks.gcp import (
    GCPStack,
    VertexAIOrchestrator,
    GCSArtifactStore,
    GCRContainerRegistry,
)
from flowyml.stacks.aws import AWSStack, AWSBatchOrchestrator, S3ArtifactStore, ECRContainerRegistry
from flowyml.stacks.azure import (
    AzureMLStack,
    AzureMLOrchestrator,
    AzureBlobArtifactStore,
    ACRContainerRegistry,
)
from flowyml.stacks.components import (
    ResourceConfig,
    DockerConfig,
    Orchestrator,
    ArtifactStore,
    ContainerRegistry,
)
from flowyml.stacks.registry import StackRegistry, get_registry, get_active_stack, set_active_stack
from flowyml.stacks.plugins import (
    get_component_registry,
    register_component,
    load_component,
)

# --- Enterprise Stack Registry ---
# These imports are lazy-safe: if any dependency is missing, they silently
# degrade to None and the rest of the stacks module still works.
import contextlib

with contextlib.suppress(ImportError):
    from flowyml.stacks.enterprise import (
        StackDefinition,
        StackMetadata,
        StackSpec,
        EnterpriseStackRegistry,
        PolicyEngine,
        PolicyResult,
        PolicyContext,
        StackLockManager,
        ProjectConfig,
        EnvironmentConfig,
        ExecutionContext,
        BackendAdapter,
        AuditRecord,
        AuditStore,
    )


# --- Unified use_stack() context manager ---


def use_stack(name_or_definition):
    """Context manager for temporarily using a different stack.

    Works with both string names and enterprise StackDefinition objects.

    Args:
        name_or_definition: Stack name (str), URI (str), or StackDefinition.

    Yields:
        The resolved stack (StackConfig, StackDefinition, or Stack).

    Examples::

        # By name (from flowyml.yaml or enterprise registry)
        with use_stack("staging"):
            pipeline.run()

        # By URI
        with use_stack("github://org/repo@v1#my_stack"):
            pipeline.run()

        # By definition
        stack_def = StackDefinition.from_yaml("stacks/prod.yaml")
        with use_stack(stack_def):
            pipeline.run()
    """
    from contextlib import contextmanager

    @contextmanager
    def _use_stack():
        import os

        # Try enterprise resolver first
        try:
            from flowyml.stacks.enterprise.models import StackDefinition as _StackDef

            if isinstance(name_or_definition, _StackDef):
                # Set environment variable so Pipeline resolves it
                old_val = os.environ.get("FLOWYML_STACK")
                # Store the definition on a thread-local for the resolver to pick up
                import threading

                if not hasattr(use_stack, "_local"):
                    use_stack._local = threading.local()
                use_stack._local.current_definition = name_or_definition
                try:
                    yield name_or_definition
                finally:
                    use_stack._local.current_definition = None
                    if old_val is not None:
                        os.environ["FLOWYML_STACK"] = old_val
                    elif "FLOWYML_STACK" in os.environ:
                        del os.environ["FLOWYML_STACK"]
                return
        except ImportError:
            pass

        if isinstance(name_or_definition, str):
            # Try plugin StackManager first
            try:
                from flowyml.plugins.stack_config import get_stack_manager

                manager = get_stack_manager()
                with manager.use_stack(name_or_definition) as stack:
                    yield stack
                return
            except (ImportError, ValueError):
                pass

            # Fallback: set env var
            old_val = os.environ.get("FLOWYML_STACK")
            os.environ["FLOWYML_STACK"] = name_or_definition
            try:
                yield name_or_definition
            finally:
                if old_val is not None:
                    os.environ["FLOWYML_STACK"] = old_val
                elif "FLOWYML_STACK" in os.environ:
                    del os.environ["FLOWYML_STACK"]
        else:
            yield name_or_definition

    return _use_stack()


# ZenML integration - lazy imports to avoid errors when ZenML is not installed
# NOTE: These functions are deprecated. Use native FlowyML plugins instead.
# See: https://unicolab.github.io/FlowyML/latest/plugins/native-plugins/
def get_zenml_bridge():
    """Get a ZenML bridge for importing ZenML components.

    .. deprecated::
        ZenML integration is deprecated. Use native FlowyML plugins instead.
        See the Native Plugins documentation for the recommended approach.
    """
    import warnings

    warnings.warn(
        "get_zenml_bridge() is deprecated. Use native FlowyML plugins instead. "
        "See: https://unicolab.github.io/FlowyML/latest/plugins/native-plugins/",
        DeprecationWarning,
        stacklevel=2,
    )
    from flowyml.stacks.zenml_bridge import ZenMLBridge

    return ZenMLBridge()


def import_all_zenml():
    """Import all components from all installed ZenML integrations.

    .. deprecated::
        ZenML integration is deprecated. Use native FlowyML plugins instead.
        See the Native Plugins documentation for the recommended approach.

    Example:
        >>> from flowyml.stacks import import_all_zenml
        >>> components = import_all_zenml()
    """
    import warnings

    warnings.warn(
        "import_all_zenml() is deprecated. Use native FlowyML plugins instead. "
        "See: https://unicolab.github.io/FlowyML/latest/plugins/native-plugins/",
        DeprecationWarning,
        stacklevel=2,
    )
    from flowyml.stacks.zenml_bridge import import_all_zenml as _import_all

    return _import_all()


__all__ = [
    # Runtime Stack classes
    "Stack",
    "StackConfig",
    "LocalStack",
    "GCPStack",
    "AWSStack",
    "AzureMLStack",
    "VertexAIOrchestrator",
    "AWSBatchOrchestrator",
    "AzureMLOrchestrator",
    "GCSArtifactStore",
    "S3ArtifactStore",
    "AzureBlobArtifactStore",
    "GCRContainerRegistry",
    "ECRContainerRegistry",
    "ACRContainerRegistry",
    "ResourceConfig",
    "DockerConfig",
    "Orchestrator",
    "ArtifactStore",
    "ContainerRegistry",
    # Legacy Registry
    "StackRegistry",
    "get_registry",
    "get_active_stack",
    "set_active_stack",
    # Plugin system
    "get_component_registry",
    "register_component",
    "load_component",
    # Unified context manager
    "use_stack",
    # Enterprise Stack Registry (when available)
    "StackDefinition",
    "StackMetadata",
    "StackSpec",
    "EnterpriseStackRegistry",
    "PolicyEngine",
    "PolicyResult",
    "PolicyContext",
    "StackLockManager",
    "ProjectConfig",
    "EnvironmentConfig",
    "ExecutionContext",
    "BackendAdapter",
    "AuditRecord",
    "AuditStore",
    # Deprecated
    "get_zenml_bridge",
    "import_all_zenml",
]
