"""FlowyML Stack Configuration - Multi-Stack Support with Type-Based Routing.

This module extends the plugin configuration to support:
1. Multiple named stacks in a single config file
2. Type-based artifact routing (Model → registry, Dataset → store, etc.)
3. Stack switching via environment variable or code
4. Path templating for artifacts

Example flowyml.yaml:
    stacks:
      local:
        orchestrator: { type: local }
        artifact_store: { type: local, path: "./artifacts" }

      gcp-prod:
        orchestrator: { type: vertex_ai, project: ${GCP_PROJECT} }
        artifact_routing:
          Model: { store: gcs, register: true }
        model_registry: { type: vertex_model_registry }
        model_deployer: { type: vertex_endpoints }

      aws-staging:
        orchestrator: { type: sagemaker, region: us-east-1 }
        artifact_routing:
          Model: { store: s3, register: true }
        model_registry: { type: sagemaker_model_registry }

    active_stack: local  # Default stack

Usage:
    from flowyml.plugins.stack_config import get_active_stack, use_stack

    # Get current stack
    stack = get_active_stack()

    # Switch stack temporarily
    with use_stack("gcp-prod"):
        pipeline.run()

    # Or via environment variable
    # FLOWYML_STACK=gcp-prod flowyml run my_pipeline
"""

import os
import logging
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Optional
from collections.abc import Callable

from flowyml.plugins.config import get_config, PluginConfig

logger = logging.getLogger(__name__)


# =============================================================================
# ARTIFACT ROUTING CONFIGURATION
# =============================================================================


@dataclass
class ArtifactRoutingRule:
    """Configuration for routing a specific artifact type.

    Attributes:
        store: Name of the artifact store to use (e.g., "gcs", "s3", "local")
        path: Path template for the artifact (supports {run_id}, {step_name})
        register: Whether to register the artifact (e.g., models to registry)
        deploy: Whether deployment is enabled (still requires approval or condition)
        deploy_condition: Condition for auto-deploy ("manual", "auto", "on_approval")
        deploy_min_metrics: Minimum metrics required for deployment (e.g., {"accuracy": 0.9})
        endpoint_name: Optional endpoint name for deployment
        log_to_tracker: Whether to log to experiment tracker (e.g., for Metrics)
        metadata: Additional metadata to attach

    Deployment Modes:
        - deploy=False: Never deploy
        - deploy=True, deploy_condition="manual": Register only, deploy via CLI/UI
        - deploy=True, deploy_condition="on_approval": Wait for human approval
        - deploy=True, deploy_condition="auto": Deploy if metrics meet thresholds
    """

    store: str | None = None
    path: str = "{run_id}/{step_name}/{artifact_name}"
    register: bool = False
    deploy: bool = False
    deploy_condition: str = "manual"  # "manual", "auto", "on_approval"
    deploy_min_metrics: dict[str, float] = field(default_factory=dict)
    endpoint_name: str | None = None
    log_to_tracker: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ArtifactRoutingRule":
        """Create from dictionary."""
        return cls(
            store=data.get("store"),
            path=data.get("path", "{run_id}/{step_name}/{artifact_name}"),
            register=data.get("register", False),
            deploy=data.get("deploy", False),
            deploy_condition=data.get("deploy_condition", "manual"),
            deploy_min_metrics=data.get("deploy_min_metrics", {}),
            endpoint_name=data.get("endpoint_name"),
            log_to_tracker=data.get("log_to_tracker", False),
            metadata=data.get("metadata", {}),
        )

    def should_auto_deploy(self, metrics: dict[str, float] = None) -> bool:
        """Check if model should be auto-deployed based on condition and metrics.

        Args:
            metrics: Current model's metrics to compare against thresholds.

        Returns:
            True if auto-deployment should proceed.
        """
        if not self.deploy:
            return False

        if self.deploy_condition == "manual":
            return False  # Requires manual deployment via CLI

        if self.deploy_condition == "on_approval":
            return False  # Requires human approval

        if self.deploy_condition == "auto":
            # Check if metrics meet minimum thresholds
            if self.deploy_min_metrics and metrics:
                for metric_name, min_value in self.deploy_min_metrics.items():
                    if metric_name not in metrics:
                        return False
                    if metrics[metric_name] < min_value:
                        return False
            return True

        return False

    def format_path(
        self,
        run_id: str = "",
        step_name: str = "",
        artifact_name: str = "",
        **kwargs,
    ) -> str:
        """Format the path template with actual values.

        Args:
            run_id: The run identifier
            step_name: The step name
            artifact_name: The artifact name
            **kwargs: Additional template variables

        Returns:
            Formatted path string.
        """
        return self.path.format(
            run_id=run_id,
            step_name=step_name,
            artifact_name=artifact_name,
            **kwargs,
        )


@dataclass
class ArtifactRoutingConfig:
    """Configuration for all artifact type routing.

    Maps artifact type names (Model, Dataset, Metrics, etc.) to routing rules.
    """

    rules: dict[str, ArtifactRoutingRule] = field(default_factory=dict)
    default: ArtifactRoutingRule | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ArtifactRoutingConfig":
        """Create from dictionary."""
        rules = {}
        default = None

        for type_name, rule_data in data.items():
            if type_name == "default":
                default = ArtifactRoutingRule.from_dict(rule_data)
            else:
                rules[type_name] = ArtifactRoutingRule.from_dict(rule_data)

        return cls(rules=rules, default=default)

    def get_rule(self, artifact_type: str) -> ArtifactRoutingRule | None:
        """Get routing rule for an artifact type.

        Args:
            artifact_type: Name of the artifact type (Model, Dataset, etc.)

        Returns:
            Routing rule or default if not found.
        """
        if artifact_type in self.rules:
            return self.rules[artifact_type]
        return self.default


# =============================================================================
# STACK CONFIGURATION
# =============================================================================


@dataclass
class StackConfig:
    """Configuration for a single named stack.

    A stack is a collection of plugins that work together to run pipelines.
    """

    name: str
    orchestrator: dict[str, Any] | None = None
    artifact_store: dict[str, Any] | None = None
    experiment_tracker: dict[str, Any] | None = None
    model_registry: dict[str, Any] | None = None
    model_deployer: dict[str, Any] | None = None
    container_registry: dict[str, Any] | None = None
    feature_store: dict[str, Any] | None = None
    data_validator: dict[str, Any] | None = None
    alerter: dict[str, Any] | None = None
    artifact_routing: ArtifactRoutingConfig | None = None
    artifact_stores: dict[str, dict[str, Any]] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, name: str, data: dict[str, Any]) -> "StackConfig":
        """Create from dictionary."""
        # Extract artifact routing
        routing_data = data.get("artifact_routing", {})
        routing = ArtifactRoutingConfig.from_dict(routing_data) if routing_data else None

        # Extract named artifact stores
        stores = data.get("artifact_stores", {})

        return cls(
            name=name,
            orchestrator=data.get("orchestrator"),
            artifact_store=data.get("artifact_store"),
            experiment_tracker=data.get("experiment_tracker"),
            model_registry=data.get("model_registry"),
            model_deployer=data.get("model_deployer"),
            container_registry=data.get("container_registry"),
            feature_store=data.get("feature_store"),
            data_validator=data.get("data_validator"),
            alerter=data.get("alerter"),
            artifact_routing=routing,
            artifact_stores=stores,
        )

    def get_routing_for_type(self, artifact_type: str) -> ArtifactRoutingRule | None:
        """Get routing configuration for an artifact type.

        Args:
            artifact_type: Name of the artifact type.

        Returns:
            Routing rule or None.
        """
        if self.artifact_routing:
            return self.artifact_routing.get_rule(artifact_type)
        return None

    def to_stack(self) -> Any:
        """Hydrate this StackConfig into a live Stack with real components.

        Resolves each component dict (orchestrator, artifact_store, etc.) into
        a real object using the ComponentRegistry, then assembles them into a
        ``Stack`` instance.

        Returns:
            A fully-wired ``Stack`` ready for pipeline execution.

        Example::

            manager = get_stack_manager()
            stack_config = manager.get_stack("gcp-prod")
            live_stack = stack_config.to_stack()
            pipeline = Pipeline("train", stack=live_stack)
        """
        from flowyml.stacks.base import Stack

        # --- Orchestrator ---
        orchestrator = self._instantiate_component(
            self.orchestrator,
            fallback_type="local",
        )
        # Fallback: if the registry didn't know the type, use LocalOrchestrator
        if orchestrator is None:
            from flowyml.core.orchestrator import LocalOrchestrator

            orchestrator = LocalOrchestrator()

        # --- Artifact store ---
        artifact_store = self._instantiate_component(
            self.artifact_store,
            fallback_type="local",
        )
        if artifact_store is None:
            from flowyml.storage.artifacts import LocalArtifactStore

            path = (self.artifact_store or {}).get("path", ".flowyml/artifacts")
            artifact_store = LocalArtifactStore(path)

        # --- Metadata store (always local for now) ---
        from flowyml.storage.metadata import SQLiteMetadataStore

        metadata_store = SQLiteMetadataStore()

        # --- Container registry (optional) ---
        container_registry = self._instantiate_component(self.container_registry)

        # --- Model deployer (optional) ---
        model_deployer = self._instantiate_component(self.model_deployer)

        # --- Build the live stack ---
        live_stack = Stack(
            name=self.name,
            executor=None,  # orchestrator handles execution
            artifact_store=artifact_store,
            metadata_store=metadata_store,
            container_registry=container_registry,
            orchestrator=orchestrator,
            model_deployer=model_deployer,
        )

        # Attach routing config so the routing module can read it
        live_stack._artifact_routing = self.artifact_routing
        live_stack._artifact_stores = self.artifact_stores
        live_stack._model_registry_config = self.model_registry
        live_stack._experiment_tracker_config = self.experiment_tracker

        return live_stack

    @staticmethod
    def _instantiate_component(
        config: dict[str, Any] | None,
        fallback_type: str | None = None,
    ) -> Any | None:
        """Instantiate a stack component from its config dict.

        Looks up ``config["type"]`` in the global ``ComponentRegistry``.
        If the class is found, it is instantiated by forwarding all remaining
        keys as keyword arguments.

        Args:
            config: Component configuration dict (must have a ``type`` key).
            fallback_type: Default type name when config is None or has no type.

        Returns:
            Component instance, or ``None`` if unresolvable.
        """
        if config is None:
            if fallback_type is None:
                return None
            config = {"type": fallback_type}

        comp_type = config.get("type", fallback_type)
        if comp_type is None:
            return None

        # Import the provider modules so @register_component decorators fire
        _ensure_providers_loaded(comp_type)

        from flowyml.stacks.plugins import get_component_registry

        registry = get_component_registry()
        component_cls = registry.get_component(comp_type)
        if component_cls is None:
            logger.warning(
                f"Component type '{comp_type}' not found in registry. " f"Available: {registry.list_all()}",
            )
            return None

        # Forward all config keys except 'type' as kwargs
        kwargs = {k: v for k, v in config.items() if k != "type"}

        # Map common YAML keys to constructor params
        mapped = {}
        for k, v in kwargs.items():
            mapped[_YAML_KEY_ALIASES.get(k, k)] = v

        try:
            return component_cls(**mapped)
        except TypeError as exc:
            # Gracefully handle unexpected kwargs
            logger.warning(f"Failed to instantiate {comp_type}: {exc}")
            try:
                return component_cls()
            except Exception:
                return None


# Aliases that map YAML shorthand keys to Python constructor parameter names.
_YAML_KEY_ALIASES: dict[str, str] = {
    "bucket": "bucket_name",
    "project": "project_id",
    "region": "region",
}

# Component types provided by each cloud provider module.
_GCP_COMPONENT_TYPES = {"vertex_ai", "gcs", "gcr", "vertex_model_registry", "vertex_endpoint"}
_AWS_COMPONENT_TYPES = {"sagemaker", "s3", "ecr", "aws_batch", "sagemaker_model_registry"}
_AZURE_COMPONENT_TYPES = {"azure_ml", "azure_blob", "acr"}


def _ensure_providers_loaded(comp_type: str) -> None:
    """Import provider modules lazily so their @register_component fires."""
    import contextlib

    if comp_type in _GCP_COMPONENT_TYPES:
        with contextlib.suppress(ImportError):
            import flowyml.stacks.gcp  # noqa: F401
    elif comp_type in _AWS_COMPONENT_TYPES:
        with contextlib.suppress(ImportError):
            import flowyml.stacks.aws  # noqa: F401
    elif comp_type in _AZURE_COMPONENT_TYPES:
        with contextlib.suppress(ImportError):
            import flowyml.stacks.azure  # noqa: F401


# =============================================================================
# MULTI-STACK MANAGER
# =============================================================================


class StackManager:
    """Manages multiple stacks and the active stack.

    The stack manager:
    1. Loads stack definitions from config
    2. Tracks the active stack
    3. Provides stack switching via context manager
    """

    _instance: Optional["StackManager"] = None

    def __init__(self, config: PluginConfig = None):
        """Initialize the stack manager.

        Args:
            config: Optional PluginConfig instance.
        """
        self._config = config or get_config()
        self._stacks: dict[str, StackConfig] = {}
        self._active_stack_name: str | None = None
        self._stack_context: list[str] = []  # Stack for context manager nesting

        self._load_stacks()

    def _load_stacks(self) -> None:
        """Load stack definitions from config."""
        raw_config = self._config._config

        # Check for stacks section (new format)
        stacks_data = raw_config.get("stacks", {})

        if stacks_data:
            # New multi-stack format
            for name, stack_data in stacks_data.items():
                self._stacks[name] = StackConfig.from_dict(name, stack_data)

            # Set active stack from config or env var
            self._active_stack_name = (
                os.environ.get("FLOWYML_STACK")
                or raw_config.get("active_stack")
                or next(iter(self._stacks.keys()), None)
            )
            logger.info(f"Loaded {len(self._stacks)} stacks, active: {self._active_stack_name}")
        else:
            # Legacy single-stack format - create a "default" stack from plugins section
            plugins = raw_config.get("plugins", {})
            if plugins:
                self._stacks["default"] = StackConfig.from_dict("default", plugins)
                self._active_stack_name = "default"
                logger.info("Loaded legacy config as 'default' stack")

    @classmethod
    def get_instance(cls, config: PluginConfig = None) -> "StackManager":
        """Get or create the singleton instance.

        Args:
            config: Optional PluginConfig to use.

        Returns:
            StackManager instance.
        """
        if cls._instance is None or config is not None:
            cls._instance = cls(config)
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton instance."""
        cls._instance = None

    @property
    def active_stack(self) -> StackConfig | None:
        """Get the currently active stack configuration."""
        if self._active_stack_name:
            return self._stacks.get(self._active_stack_name)
        return None

    @property
    def active_stack_name(self) -> str | None:
        """Get the name of the active stack."""
        return self._active_stack_name

    def list_stacks(self) -> list[str]:
        """List all available stack names.

        Returns:
            List of stack names.
        """
        return list(self._stacks.keys())

    def get_stack(self, name: str) -> StackConfig | None:
        """Get a stack by name.

        Args:
            name: Stack name.

        Returns:
            Stack configuration or None.
        """
        return self._stacks.get(name)

    def set_active_stack(self, name: str) -> bool:
        """Set the active stack.

        Args:
            name: Stack name to activate.

        Returns:
            True if successful.
        """
        if name not in self._stacks:
            logger.error(f"Stack '{name}' not found. Available: {list(self._stacks.keys())}")
            return False

        self._active_stack_name = name
        logger.info(f"Active stack set to: {name}")
        return True

    def register_stack(self, name: str, config: StackConfig) -> None:
        """Register a new stack configuration.

        Args:
            name: Stack name.
            config: Stack configuration.
        """
        self._stacks[name] = config
        logger.info(f"Registered stack: {name}")

    @contextmanager
    def use_stack(self, name: str):
        """Context manager for temporarily using a different stack.

        Args:
            name: Stack name to use.

        Yields:
            The stack configuration.
        """
        if name not in self._stacks:
            raise ValueError(f"Stack '{name}' not found. Available: {list(self._stacks.keys())}")

        # Save current and switch
        previous = self._active_stack_name
        self._stack_context.append(previous)
        self._active_stack_name = name

        try:
            yield self._stacks[name]
        finally:
            # Restore previous
            self._active_stack_name = self._stack_context.pop()

    def get_routing_for_type(self, artifact_type: str) -> ArtifactRoutingRule | None:
        """Get artifact routing for a type in the active stack.

        Args:
            artifact_type: Name of the artifact type.

        Returns:
            Routing rule or None.
        """
        stack = self.active_stack
        if stack:
            return stack.get_routing_for_type(artifact_type)
        return None


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


def get_stack_manager(config: PluginConfig = None) -> StackManager:
    """Get the global stack manager.

    Args:
        config: Optional PluginConfig to use.

    Returns:
        StackManager instance.
    """
    return StackManager.get_instance(config)


def get_active_stack() -> StackConfig | None:
    """Get the currently active stack configuration.

    Returns:
        Active stack configuration or None.
    """
    return get_stack_manager().active_stack


def list_stacks() -> list[str]:
    """List all available stack names.

    Returns:
        List of stack names.
    """
    return get_stack_manager().list_stacks()


def set_active_stack(name: str) -> bool:
    """Set the active stack by name.

    Args:
        name: Stack name to activate.

    Returns:
        True if successful.
    """
    return get_stack_manager().set_active_stack(name)


@contextmanager
def use_stack(name: str):
    """Context manager for temporarily using a different stack.

    Example:
        with use_stack("gcp-prod"):
            pipeline.run()

    Args:
        name: Stack name to use.

    Yields:
        The stack configuration.
    """
    with get_stack_manager().use_stack(name) as stack:
        yield stack


def use_stack_decorator(stack_name: str) -> Callable:
    """Decorator to run a function with a specific stack.

    Example:
        @use_stack_decorator("gcp-prod")
        def train():
            pipeline.run()

    Args:
        stack_name: Stack name to use.

    Returns:
        Decorator function.
    """

    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            with use_stack(stack_name):
                return func(*args, **kwargs)

        return wrapper

    return decorator


def get_routing_for_type(artifact_type: str) -> ArtifactRoutingRule | None:
    """Get artifact routing configuration for a type.

    Args:
        artifact_type: Name of the artifact type (Model, Dataset, etc.)

    Returns:
        Routing rule or None.
    """
    return get_stack_manager().get_routing_for_type(artifact_type)
