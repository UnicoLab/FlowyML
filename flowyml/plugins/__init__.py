"""FlowyML Native Plugin System.

A powerful, extensible plugin system that allows you to easily
integrate with external tools without requiring any framework dependencies.

Quick Start:
    # Install a plugin (just installs the underlying packages)
    from flowyml.plugins import install, load, get_plugin

    install("mlflow")   # Installs mlflow package directly

    # Load and use
    tracker = get_plugin("mlflow", tracking_uri="http://localhost:5000")
    tracker.start_run("my_experiment")
    tracker.log_metrics({"accuracy": 0.95})
    tracker.end_run()

Config-Based Usage (Recommended):
    # flowyml.yaml
    plugins:
      experiment_tracker:
        type: mlflow
        tracking_uri: http://localhost:5000
      artifact_store:
        type: gcs
        bucket: my-ml-artifacts

    # In code - just use, no setup needed
    from flowyml.plugins.stack import (
        start_run, log_metrics, save_artifact, save_model
    )

    start_run("my_training")
    log_metrics({"accuracy": 0.95})
    save_model(model, "models/classifier")

CLI Usage:
    # List available plugins
    flowyml plugin list

    # Install a plugin
    flowyml plugin install mlflow

    # Initialize config
    flowyml stack init --tracker mlflow --store gcs

Extending FlowyML:
    Community plugins can register via Python entry points:

    # In pyproject.toml
    [project.entry-points."flowyml.plugins"]
    my_tracker = "my_package.plugins:MyTracker"
"""

# Base classes for creating plugins
from flowyml.plugins.base import (
    BasePlugin,
    PluginType,
    PluginMetadata,
    # Core plugin types
    ExperimentTracker,
    ArtifactStorePlugin,
    OrchestratorPlugin,
    ContainerRegistryPlugin,
    FeatureStorePlugin,
    DataValidatorPlugin,
    ModelRegistryPlugin,
    ModelDeployerPlugin,
    AlerterPlugin,
)

# Registry for discovering plugins
from flowyml.plugins.registry import (
    PluginInfo,
    PluginStatus,
    PLUGIN_CATALOG,
    get_plugin_info,
    list_plugins,
    list_plugin_names,
    register_plugin,
    unregister_plugin,
)

# Manager for installing and loading plugins
from flowyml.plugins.manager import (
    PluginManager,
    get_manager,
    install,
    load,
    get_plugin,
    list_available,
    list_installed,
    is_installed,
)

# Config-based plugin access
from flowyml.plugins.config import (
    PluginConfig,
    get_config,
    reload_config,
    get_tracker,
    get_artifact_store,
    get_orchestrator,
    get_container_registry,
    get_feature_store,
    get_data_validator,
    get_alerter,
    generate_config_template,
)

# Multi-stack configuration
from flowyml.plugins.stack_config import (
    StackManager,
    StackConfig,
    ArtifactRoutingRule,
    ArtifactRoutingConfig,
    get_stack_manager,
    get_active_stack,
    list_stacks,
    set_active_stack,
    use_stack,
    use_stack_decorator,
    get_routing_for_type,
)

# Unified stack interface (config-driven)
from flowyml.plugins.stack import (
    # Experiment tracking
    start_run,
    end_run,
    run,
    log_params,
    log_metrics,
    log_artifact,
    set_tag,
    set_tags,
    # Artifact storage
    save_artifact,
    load_artifact,
    artifact_exists,
    list_artifacts,
    delete_artifact,
    # Model management
    save_model,
    load_model,
    # Container registry
    push_image,
    get_image_uri,
    # Orchestration
    run_pipeline,
    # Alerts
    send_alert,
    # Stack info
    show_stack,
    validate_stack,
)

# Pipeline integration
from flowyml.plugins.integration import (
    StackContext,
    run_with_stack,
    tracked,
    PipelinePluginIntegration,
    get_integration,
)

__all__ = [
    # Base classes
    "BasePlugin",
    "PluginType",
    "PluginMetadata",
    "ExperimentTracker",
    "ArtifactStorePlugin",
    "OrchestratorPlugin",
    "ContainerRegistryPlugin",
    "FeatureStorePlugin",
    "DataValidatorPlugin",
    "ModelRegistryPlugin",
    "ModelDeployerPlugin",
    "AlerterPlugin",
    # Registry
    "PluginInfo",
    "PluginStatus",
    "PLUGIN_CATALOG",
    "get_plugin_info",
    "list_plugins",
    "list_plugin_names",
    "register_plugin",
    "unregister_plugin",
    # Manager
    "PluginManager",
    "get_manager",
    "install",
    "load",
    "get_plugin",
    "list_available",
    "list_installed",
    "is_installed",
    # Config
    "PluginConfig",
    "get_config",
    "reload_config",
    "get_tracker",
    "get_artifact_store",
    "get_orchestrator",
    "get_container_registry",
    "get_feature_store",
    "get_data_validator",
    "get_alerter",
    "generate_config_template",
    # Stack (unified interface)
    "start_run",
    "end_run",
    "run",
    "log_params",
    "log_metrics",
    "log_artifact",
    "set_tag",
    "set_tags",
    "save_artifact",
    "load_artifact",
    "artifact_exists",
    "list_artifacts",
    "delete_artifact",
    "save_model",
    "load_model",
    "push_image",
    "get_image_uri",
    "run_pipeline",
    "send_alert",
    "show_stack",
    "validate_stack",
    # Integration
    "StackContext",
    "run_with_stack",
    "tracked",
    "PipelinePluginIntegration",
    "get_integration",
    # Multi-stack configuration
    "StackManager",
    "StackConfig",
    "ArtifactRoutingRule",
    "ArtifactRoutingConfig",
    "get_stack_manager",
    "get_active_stack",
    "list_stacks",
    "set_active_stack",
    "use_stack",
    "use_stack_decorator",
    "get_routing_for_type",
]
