"""FlowyML Plugin Manager - Installation, Loading, and Discovery.

This module provides the main interface for managing plugins:
installing dependencies, loading plugin classes, and discovering
available plugins.

Usage:
    from flowyml.plugins.manager import PluginManager

    manager = PluginManager()

    # Install a plugin
    manager.install("mlflow")

    # Load and use a plugin
    MLflowTracker = manager.load("mlflow")
    tracker = MLflowTracker(tracking_uri="http://localhost:5000")
"""

import subprocess
import sys
import importlib
import importlib.util
import logging

from flowyml.plugins.base import BasePlugin, PluginType
from flowyml.plugins.registry import (
    PLUGIN_CATALOG,
    PluginInfo,
    PluginStatus,
    get_plugin_info,
    list_plugin_names,
    register_plugin,
)

logger = logging.getLogger(__name__)


class PluginManager:
    """Manages FlowyML plugin lifecycle.

    The PluginManager handles:
    - Installing plugin dependencies
    - Loading plugin classes
    - Discovering available and installed plugins
    - Managing plugin instances

    Example:
        manager = PluginManager()

        # Check what's available
        print(manager.list_available())

        # Install a plugin (installs underlying packages)
        manager.install("mlflow")

        # Load the plugin class
        MLflowTracker = manager.load("mlflow")

        # Create an instance
        tracker = MLflowTracker(tracking_uri="http://localhost:5000")
    """

    # Cache of loaded plugin classes
    _loaded_plugins: dict[str, type[BasePlugin]] = {}

    # Cache of plugin instances
    _instances: dict[str, BasePlugin] = {}

    def __init__(self):
        """Initialize the plugin manager."""
        self._check_installed_status()

    def _check_installed_status(self) -> None:
        """Check which plugins have their packages installed."""
        for _name, info in PLUGIN_CATALOG.items():
            if self._are_packages_installed(info.packages):
                info.status = PluginStatus.INSTALLED

    def _are_packages_installed(self, packages: list[str]) -> bool:
        """Check if all required packages are installed.

        Args:
            packages: List of package requirements (e.g., ["mlflow>=2.0"])

        Returns:
            True if all packages are installed.
        """
        for pkg_spec in packages:
            # Extract package name from spec (e.g., "mlflow>=2.0" -> "mlflow")
            pkg_name = pkg_spec.split(">=")[0].split("==")[0].split("<")[0].strip()
            # Handle packages with dashes vs underscores
            pkg_name = pkg_name.replace("-", "_")

            try:
                if importlib.util.find_spec(pkg_name) is None:
                    # Try with dashes
                    pkg_name_dash = pkg_name.replace("_", "-")
                    if importlib.util.find_spec(pkg_name_dash) is None:
                        return False
            except (ValueError, AttributeError):
                # This can happen if a module is partially loaded or mocked without __spec__
                return False
        return True

    # =========================================================================
    # DISCOVERY METHODS
    # =========================================================================

    def list_available(self, plugin_type: PluginType = None) -> list[str]:
        """List all available plugins.

        Args:
            plugin_type: Optional filter by plugin type.

        Returns:
            List of plugin names.
        """
        return list_plugin_names(plugin_type)

    def list_installed(self, plugin_type: PluginType = None) -> list[str]:
        """List plugins that have their packages installed.

        Args:
            plugin_type: Optional filter by plugin type.

        Returns:
            List of installed plugin names.
        """
        installed = []
        for name, info in PLUGIN_CATALOG.items():
            if plugin_type and info.plugin_type != plugin_type:
                continue
            if self._are_packages_installed(info.packages):
                installed.append(name)
        return installed

    def get_info(self, name: str) -> PluginInfo | None:
        """Get information about a plugin.

        Args:
            name: Plugin name.

        Returns:
            PluginInfo if found, None otherwise.
        """
        return get_plugin_info(name)

    def is_installed(self, name: str) -> bool:
        """Check if a plugin's packages are installed.

        Args:
            name: Plugin name.

        Returns:
            True if installed.
        """
        info = get_plugin_info(name)
        if not info:
            return False
        return self._are_packages_installed(info.packages)

    # =========================================================================
    # INSTALLATION METHODS
    # =========================================================================

    def install(self, name: str, upgrade: bool = False) -> bool:
        """Install a plugin and its dependencies.

        This installs the underlying packages directly (e.g., mlflow, boto3)
        without requiring any external framework.

        Args:
            name: Plugin name to install.
            upgrade: If True, upgrade packages to latest versions.

        Returns:
            True if installation was successful.

        Raises:
            ValueError: If plugin is not found in catalog.
        """
        info = get_plugin_info(name)
        if not info:
            raise ValueError(
                f"Plugin '{name}' not found. Available plugins: {', '.join(list_plugin_names())}",
            )

        logger.info(f"Installing plugin '{name}' with packages: {info.packages}")

        try:
            # Build pip install command
            cmd = [sys.executable, "-m", "pip", "install"]
            if upgrade:
                cmd.append("--upgrade")
            cmd.extend(info.packages)

            # Run installation
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                info.status = PluginStatus.INSTALLED
                logger.info(f"Successfully installed plugin '{name}'")
                return True
            else:
                logger.error(f"Failed to install '{name}': {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Error installing plugin '{name}': {e}")
            return False

    def install_all(self, plugin_type: PluginType = None) -> dict[str, bool]:
        """Install all plugins (or all of a specific type).

        Args:
            plugin_type: Optional filter by plugin type.

        Returns:
            Dictionary mapping plugin names to success status.
        """
        results = {}
        for name in self.list_available(plugin_type):
            results[name] = self.install(name)
        return results

    def uninstall(self, name: str) -> bool:
        """Uninstall a plugin's packages.

        Args:
            name: Plugin name to uninstall.

        Returns:
            True if uninstallation was successful.
        """
        info = get_plugin_info(name)
        if not info:
            return False

        try:
            # Extract package names
            pkg_names = []
            for pkg_spec in info.packages:
                pkg_name = pkg_spec.split(">=")[0].split("==")[0].split("<")[0].strip()
                pkg_names.append(pkg_name)

            cmd = [sys.executable, "-m", "pip", "uninstall", "-y"] + pkg_names
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                info.status = PluginStatus.AVAILABLE
                # Remove from loaded cache
                self._loaded_plugins.pop(name, None)
                self._instances.pop(name, None)
                logger.info(f"Uninstalled plugin '{name}'")
                return True
            return False

        except Exception as e:
            logger.error(f"Error uninstalling plugin '{name}': {e}")
            return False

    # =========================================================================
    # LOADING METHODS
    # =========================================================================

    def load(self, name: str) -> type[BasePlugin]:
        """Load a plugin class.

        Args:
            name: Plugin name to load.

        Returns:
            The plugin class (not instantiated).

        Raises:
            ValueError: If plugin not found.
            ImportError: If plugin packages not installed.
        """
        # Check cache first
        if name in self._loaded_plugins:
            return self._loaded_plugins[name]

        info = get_plugin_info(name)
        if not info:
            raise ValueError(f"Plugin '{name}' not found in catalog")

        if not self._are_packages_installed(info.packages):
            raise ImportError(
                f"Plugin '{name}' packages not installed. Run: flowyml plugin install {name}",
            )

        # Load the plugin class
        try:
            module_path, class_name = info.wrapper_path.rsplit(":", 1)
            module = importlib.import_module(module_path)
            plugin_class = getattr(module, class_name)

            # Cache and return
            self._loaded_plugins[name] = plugin_class
            info.status = PluginStatus.LOADED
            return plugin_class

        except Exception as e:
            logger.error(f"Error loading plugin '{name}': {e}")
            raise ImportError(f"Could not load plugin '{name}': {e}")

    def get_instance(
        self,
        name: str,
        instance_name: str = None,
        **config,
    ) -> BasePlugin:
        """Get or create a plugin instance.

        Args:
            name: Plugin name.
            instance_name: Optional name for this instance (for caching).
            **config: Configuration for the plugin.

        Returns:
            Plugin instance.
        """
        cache_key = f"{name}:{instance_name}" if instance_name else name

        if cache_key in self._instances:
            return self._instances[cache_key]

        plugin_class = self.load(name)
        instance = plugin_class(name=instance_name, **config)

        if instance_name:
            self._instances[cache_key] = instance

        return instance

    # =========================================================================
    # COMMUNITY PLUGIN SUPPORT
    # =========================================================================

    def install_from_git(self, git_url: str, name: str = None) -> bool:
        """Install a community plugin from a git repository.

        Args:
            git_url: Git URL (e.g., https://github.com/user/flowyml-plugin.git)
            name: Optional plugin name override.

        Returns:
            True if installation was successful.
        """
        try:
            cmd = [sys.executable, "-m", "pip", "install", f"git+{git_url}"]
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info(f"Installed community plugin from {git_url}")
                # Try to discover and register the plugin
                self._discover_entrypoint_plugins()
                return True
            else:
                logger.error(f"Failed to install from git: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Error installing from git: {e}")
            return False

    def install_from_path(self, path: str) -> bool:
        """Install a plugin from a local path.

        Args:
            path: Path to the plugin package.

        Returns:
            True if installation was successful.
        """
        try:
            cmd = [sys.executable, "-m", "pip", "install", "-e", path]
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info(f"Installed plugin from {path}")
                self._discover_entrypoint_plugins()
                return True
            return False

        except Exception as e:
            logger.error(f"Error installing from path: {e}")
            return False

    def _discover_entrypoint_plugins(self) -> None:
        """Discover plugins registered via entry points.

        Community plugins can register themselves by adding an entry point
        in their setup.py or pyproject.toml:

            [project.entry-points."flowyml.plugins"]
            my_plugin = "my_package.plugins:MyPlugin"
        """
        try:
            # Python 3.10+
            from importlib.metadata import entry_points

            eps = entry_points()
            if hasattr(eps, "select"):
                # Python 3.10+
                flowyml_plugins = eps.select(group="flowyml.plugins")
            else:
                # Python 3.9
                flowyml_plugins = eps.get("flowyml.plugins", [])

            for ep in flowyml_plugins:
                try:
                    plugin_class = ep.load()
                    metadata = getattr(plugin_class, "METADATA", None)

                    if metadata:
                        info = PluginInfo(
                            name=metadata.name,
                            description=metadata.description,
                            plugin_type=metadata.plugin_type,
                            packages=metadata.packages,
                            wrapper_path=f"{plugin_class.__module__}:{plugin_class.__name__}",
                            version=metadata.version,
                            author=metadata.author,
                            status=PluginStatus.INSTALLED,
                        )
                        register_plugin(info)
                        logger.info(f"Discovered community plugin: {metadata.name}")
                    else:
                        logger.warning(f"Plugin {ep.name} missing METADATA")

                except Exception as e:
                    logger.debug(f"Could not load entry point {ep.name}: {e}")

        except Exception as e:
            logger.debug(f"Could not discover entry points: {e}")


# ============================================================================
# MODULE-LEVEL CONVENIENCE FUNCTIONS
# ============================================================================

# Global manager instance
_manager: PluginManager | None = None


def get_manager() -> PluginManager:
    """Get the global plugin manager instance."""
    global _manager
    if _manager is None:
        _manager = PluginManager()
    return _manager


def install(name: str, upgrade: bool = False) -> bool:
    """Install a plugin.

    Args:
        name: Plugin name.
        upgrade: If True, upgrade packages.

    Returns:
        True if successful.
    """
    return get_manager().install(name, upgrade)


def load(name: str) -> type[BasePlugin]:
    """Load a plugin class.

    Args:
        name: Plugin name.

    Returns:
        The plugin class.
    """
    return get_manager().load(name)


def get_plugin(name: str, **config) -> BasePlugin:
    """Get a plugin instance.

    Args:
        name: Plugin name.
        **config: Plugin configuration.

    Returns:
        Plugin instance.
    """
    return get_manager().get_instance(name, **config)


def list_available(plugin_type: PluginType = None) -> list[str]:
    """List available plugins."""
    return get_manager().list_available(plugin_type)


def list_installed(plugin_type: PluginType = None) -> list[str]:
    """List installed plugins."""
    return get_manager().list_installed(plugin_type)


def is_installed(name: str) -> bool:
    """Check if a plugin is installed."""
    return get_manager().is_installed(name)
