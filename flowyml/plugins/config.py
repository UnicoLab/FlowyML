"""FlowyML Plugin Configuration System.

This module provides YAML-based configuration for plugins, allowing
users to define their stack configuration in a file and use plugins
without manual setup in code.

Usage:
    # flowyml.yaml
    plugins:
      experiment_tracker:
        type: mlflow
        tracking_uri: http://localhost:5000
        experiment_name: my_experiments

      artifact_store:
        type: gcs
        bucket: my-ml-artifacts
        prefix: experiments/
        project: my-gcp-project

      orchestrator:
        type: vertex_ai
        project: my-gcp-project
        location: us-central1

    # In code - just use
    from flowyml.plugins.config import get_tracker, get_artifact_store

    tracker = get_tracker()  # Uses config from flowyml.yaml
    tracker.start_run("my_run")
"""

import os
import yaml
import logging
from pathlib import Path
from typing import Any

from flowyml.plugins.manager import get_manager
from flowyml.plugins.base import (
    BasePlugin,
    ExperimentTracker,
    ArtifactStorePlugin,
    OrchestratorPlugin,
    ContainerRegistryPlugin,
    FeatureStorePlugin,
    DataValidatorPlugin,
    AlerterPlugin,
)

logger = logging.getLogger(__name__)


# Default config file names to search for
CONFIG_FILE_NAMES = [
    "flowyml.yaml",
    "flowyml.yml",
    ".flowyml.yaml",
    ".flowyml.yml",
]


class PluginConfig:
    """Manages plugin configuration from YAML files.

    Configuration can be loaded from:
    1. A specific file path
    2. Auto-discovered from current directory
    3. Environment variable FLOWYML_CONFIG

    Example flowyml.yaml:

        plugins:
          experiment_tracker:
            type: mlflow
            tracking_uri: http://localhost:5000
            experiment_name: my_experiments

          artifact_store:
            type: s3
            bucket: my-ml-artifacts
            prefix: experiments/

          orchestrator:
            type: kubernetes
            namespace: ml-pipelines

          container_registry:
            type: gcr
            project: my-gcp-project
            location: us-central1
            repository: ml-images
    """

    def __init__(self, config_path: str = None):
        """Initialize the plugin configuration.

        Args:
            config_path: Optional path to config file. If not provided,
                        auto-discovers from current directory.
        """
        self._config_path = config_path
        self._config: dict = {}
        self._manager = get_manager()
        self._instances: dict[str, BasePlugin] = {}

        # Load config
        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from file."""
        config_path = self._find_config_file()

        if config_path:
            try:
                with open(config_path) as f:
                    raw_config = yaml.safe_load(f) or {}

                # Substitute environment variables
                self._config = self._substitute_env_vars(raw_config)
                self._config_path = config_path
                logger.info(f"Loaded plugin config from: {config_path}")
            except Exception as e:
                logger.warning(f"Failed to load config from {config_path}: {e}")
                self._config = {}
        else:
            logger.debug("No config file found, using defaults")
            self._config = {}

    def _substitute_env_vars(self, obj: Any) -> Any:
        """Recursively substitute environment variables in config.

        Supports ${VAR_NAME} and ${VAR_NAME:-default} syntax.

        Args:
            obj: Config object (dict, list, or scalar).

        Returns:
            Object with environment variables substituted.
        """
        import re

        if isinstance(obj, dict):
            return {k: self._substitute_env_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._substitute_env_vars(item) for item in obj]
        elif isinstance(obj, str):
            # Pattern: ${VAR_NAME} or ${VAR_NAME:-default}
            pattern = r"\$\{([^}:]+)(?::-([^}]*))?\}"

            def replace(match):
                var_name = match.group(1)
                default = match.group(2)
                value = os.environ.get(var_name)
                if value is not None:
                    return value
                elif default is not None:
                    return default
                else:
                    logger.warning(f"Environment variable '{var_name}' not set")
                    return match.group(0)  # Keep original if not found

            return re.sub(pattern, replace, obj)
        else:
            return obj

    def _find_config_file(self) -> str | None:
        """Find the configuration file.

        Searches in order:
        1. Explicit path provided to constructor
        2. FLOWYML_CONFIG environment variable
        3. Current directory and parent directories
        """
        # Check explicit path
        if self._config_path:
            if os.path.exists(self._config_path):
                return self._config_path
            logger.warning(f"Config file not found: {self._config_path}")

        # Check environment variable
        env_config = os.environ.get("FLOWYML_CONFIG")
        if env_config and os.path.exists(env_config):
            return env_config

        # Search current directory and parents
        current = Path.cwd()
        for _ in range(5):  # Search up to 5 levels
            for name in CONFIG_FILE_NAMES:
                config_file = current / name
                if config_file.exists():
                    return str(config_file)
            parent = current.parent
            if parent == current:
                break
            current = parent

        return None

    def reload(self) -> None:
        """Reload configuration from file."""
        self._instances.clear()
        self._load_config()

    @property
    def plugins_config(self) -> dict:
        """Get the plugins configuration section."""
        return self._config.get("plugins", {})

    def get_plugin_config(self, plugin_role: str) -> dict | None:
        """Get configuration for a specific plugin role.

        Args:
            plugin_role: Role like 'experiment_tracker', 'artifact_store', etc.

        Returns:
            Configuration dictionary or None.
        """
        return self.plugins_config.get(plugin_role)

    def _get_plugin(self, plugin_role: str, plugin_class: type = None) -> BasePlugin | None:
        """Get or create a plugin instance for a role.

        Args:
            plugin_role: Role like 'experiment_tracker'.
            plugin_class: Optional base class to validate against.

        Returns:
            Plugin instance or None if not configured.
        """
        # Check cache
        if plugin_role in self._instances:
            return self._instances[plugin_role]

        # Get config
        config = self.get_plugin_config(plugin_role)
        if not config:
            return None

        # Extract plugin type
        plugin_type = config.pop("type", None)
        if not plugin_type:
            logger.error(f"Plugin config for '{plugin_role}' missing 'type'")
            return None

        # Check if installed
        if not self._manager.is_installed(plugin_type):
            logger.info(f"Installing plugin '{plugin_type}'...")
            self._manager.install(plugin_type)

        # Load and instantiate
        try:
            plugin = self._manager.get_instance(plugin_type, **config)
            plugin.initialize()
            self._instances[plugin_role] = plugin
            return plugin
        except Exception as e:
            logger.error(f"Failed to create plugin '{plugin_type}': {e}")
            return None

    def get_experiment_tracker(self) -> ExperimentTracker | None:
        """Get the configured experiment tracker."""
        return self._get_plugin("experiment_tracker", ExperimentTracker)

    def get_artifact_store(self) -> ArtifactStorePlugin | None:
        """Get the configured artifact store."""
        return self._get_plugin("artifact_store", ArtifactStorePlugin)

    def get_orchestrator(self) -> OrchestratorPlugin | None:
        """Get the configured orchestrator."""
        return self._get_plugin("orchestrator", OrchestratorPlugin)

    def get_container_registry(self) -> ContainerRegistryPlugin | None:
        """Get the configured container registry."""
        return self._get_plugin("container_registry", ContainerRegistryPlugin)

    def get_feature_store(self) -> FeatureStorePlugin | None:
        """Get the configured feature store."""
        return self._get_plugin("feature_store", FeatureStorePlugin)

    def get_data_validator(self) -> DataValidatorPlugin | None:
        """Get the configured data validator."""
        return self._get_plugin("data_validator", DataValidatorPlugin)

    def get_alerter(self) -> AlerterPlugin | None:
        """Get the configured alerter."""
        return self._get_plugin("alerter", AlerterPlugin)


# =============================================================================
# GLOBAL CONFIG INSTANCE
# =============================================================================

_config: PluginConfig | None = None


def get_config(config_path: str = None) -> PluginConfig:
    """Get the global plugin configuration.

    Args:
        config_path: Optional path to config file.

    Returns:
        PluginConfig instance.
    """
    global _config
    if _config is None or config_path:
        _config = PluginConfig(config_path)
    return _config


def reload_config() -> None:
    """Reload the global configuration from file."""
    global _config
    if _config:
        _config.reload()


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


def get_tracker() -> ExperimentTracker | None:
    """Get the configured experiment tracker.

    Reads configuration from flowyml.yaml and returns the configured
    experiment tracker, ready to use.

    Example:
        tracker = get_tracker()
        if tracker:
            tracker.start_run("my_experiment")
    """
    return get_config().get_experiment_tracker()


def get_artifact_store() -> ArtifactStorePlugin | None:
    """Get the configured artifact store.

    Example:
        store = get_artifact_store()
        if store:
            store.save(model, "models/latest.pkl")
    """
    return get_config().get_artifact_store()


def get_orchestrator() -> OrchestratorPlugin | None:
    """Get the configured orchestrator.

    Example:
        orchestrator = get_orchestrator()
        if orchestrator:
            orchestrator.run_pipeline(my_pipeline, "run-001")
    """
    return get_config().get_orchestrator()


def get_container_registry() -> ContainerRegistryPlugin | None:
    """Get the configured container registry."""
    return get_config().get_container_registry()


def get_feature_store() -> FeatureStorePlugin | None:
    """Get the configured feature store."""
    return get_config().get_feature_store()


def get_data_validator() -> DataValidatorPlugin | None:
    """Get the configured data validator."""
    return get_config().get_data_validator()


def get_alerter() -> AlerterPlugin | None:
    """Get the configured alerter."""
    return get_config().get_alerter()


# =============================================================================
# CLI INIT COMMAND SUPPORT
# =============================================================================


def generate_config_template(
    tracker: str = None,
    store: str = None,
    orchestrator: str = None,
    registry: str = None,
) -> str:
    """Generate a flowyml.yaml template.

    Args:
        tracker: Experiment tracker plugin name.
        store: Artifact store plugin name.
        orchestrator: Orchestrator plugin name.
        registry: Container registry plugin name.

    Returns:
        YAML configuration string.
    """
    config = {
        "# FlowyML Configuration": None,
        "# Run 'flowyml plugin list' to see available plugins": None,
        "plugins": {},
    }

    if tracker:
        config["plugins"]["experiment_tracker"] = {
            "type": tracker,
            "# Add plugin-specific configuration below": None,
        }
        if tracker == "mlflow":
            config["plugins"]["experiment_tracker"].update(
                {
                    "tracking_uri": "http://localhost:5000",
                    "experiment_name": "my_experiments",
                },
            )

    if store:
        config["plugins"]["artifact_store"] = {
            "type": store,
        }
        if store == "s3":
            config["plugins"]["artifact_store"].update(
                {
                    "bucket": "my-ml-artifacts",
                    "prefix": "experiments/",
                },
            )
        elif store == "gcs":
            config["plugins"]["artifact_store"].update(
                {
                    "bucket": "my-ml-artifacts",
                    "prefix": "experiments/",
                    "project": "my-gcp-project",
                },
            )

    if orchestrator:
        config["plugins"]["orchestrator"] = {
            "type": orchestrator,
        }
        if orchestrator == "vertex_ai":
            config["plugins"]["orchestrator"].update(
                {
                    "project": "my-gcp-project",
                    "location": "us-central1",
                    "staging_bucket": "gs://my-staging-bucket",
                },
            )
        elif orchestrator == "kubernetes":
            config["plugins"]["orchestrator"].update(
                {
                    "namespace": "ml-pipelines",
                },
            )

    if registry:
        config["plugins"]["container_registry"] = {
            "type": registry,
        }
        if registry == "gcr":
            config["plugins"]["container_registry"].update(
                {
                    "project": "my-gcp-project",
                    "location": "us-central1",
                    "repository": "ml-images",
                    "use_artifact_registry": True,
                },
            )

    # Generate YAML
    lines = ["# FlowyML Configuration", "# Run 'flowyml plugin list' to see available plugins", ""]
    lines.append(yaml.dump({"plugins": config["plugins"]}, default_flow_style=False, sort_keys=False))

    return "\n".join(lines)
