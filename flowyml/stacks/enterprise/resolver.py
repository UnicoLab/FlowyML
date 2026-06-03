"""Stack resolution logic for the Enterprise Stack Registry.

The ``StackResolver`` implements the multi-layer resolution strategy:

1. Explicit CLI argument
2. Environment variable (``FLOWYML_STACK`` / ``FLOWYML_ENV``)
3. Project config (``flowyml.yaml``)
4. Registry default

It also supports direct URI resolution (e.g.
``github://org/repo@v1#stack_name``) for ad-hoc usage.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from flowyml.stacks.enterprise.exceptions import StackNotFoundError
from flowyml.stacks.enterprise.lock import StackLockManager
from flowyml.stacks.enterprise.models import StackDefinition, StackReference
from flowyml.stacks.enterprise.project_config import (
    EnvironmentConfig,
    ProjectConfig,
    load_project_config,
)
from flowyml.stacks.enterprise.registry import EnterpriseStackRegistry

logger = logging.getLogger(__name__)

__all__ = [
    "StackResolver",
]


class StackResolver:
    """Resolves which stack to use for a pipeline run.

    Resolution precedence (highest → lowest):

    1. **CLI argument** — ``stack`` parameter passed directly.
    2. **Environment variable** — ``FLOWYML_STACK`` or ``FLOWYML_ENV``.
    3. **Project config** — per-environment mapping in ``flowyml.yaml``.
    4. **Registry default** — ``defaults.stack`` in config.

    Additionally, if the value looks like a URI (contains ``://``), the
    resolver fetches the stack directly from that source.

    Args:
        registry: Optional ``EnterpriseStackRegistry`` for named look-ups.
        project_config: Optional project configuration.
        lock_manager: Optional lock manager for pinned resolution.
    """

    def __init__(
        self,
        registry: EnterpriseStackRegistry | None = None,
        project_config: ProjectConfig | None = None,
        lock_manager: StackLockManager | None = None,
        *,
        auto_bootstrap: bool = True,
    ) -> None:
        self._registry = registry
        self._project_config = project_config
        self._lock_manager = lock_manager

        # Auto-bootstrap: if all args are None, try to discover
        # project config and create a registry automatically.
        if auto_bootstrap and registry is None and project_config is None:
            self._auto_bootstrap()

    # ------------------------------------------------------------------
    # Class methods
    # ------------------------------------------------------------------

    @classmethod
    def auto(cls) -> StackResolver:
        """Create a fully-bootstrapped resolver by auto-discovering config.

        This is the recommended way to create a ``StackResolver`` in CLI
        tools and pipeline code.  It:

        1. Discovers ``flowyml.yaml`` in the current directory tree.
        2. Creates an ``EnterpriseStackRegistry`` from configured sources
           plus local ``stacks/`` directories.
        3. Optionally attaches a ``StackLockManager``.

        Returns:
            A fully-configured ``StackResolver``.
        """
        instance = cls(auto_bootstrap=True)
        return instance

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def resolve(
        self,
        stack: str | None = None,
        env: str | None = None,
    ) -> StackDefinition:
        """Resolve the stack to use for execution.

        Resolution order:
        1. ``stack`` parameter (CLI arg / direct name / URI)
        2. ``FLOWYML_STACK`` / ``FLOWYML_ENV`` environment variables
        3. Project config for the given ``env``
        4. Registry default stack

        Args:
            stack: Explicit stack name or URI.  Takes highest priority.
            env: Target environment name (e.g. ``production``).

        Returns:
            The resolved ``StackDefinition``.

        Raises:
            StackNotFoundError: If resolution fails at every layer.
        """
        # 1. Explicit stack argument
        if stack is not None:
            logger.debug("Resolving from explicit argument: '%s'", stack)
            return self._resolve_value(stack)

        # 2. Environment variables
        env_value = self._resolve_from_env()
        if env_value is not None:
            logger.debug("Resolving from environment variable: '%s'", env_value)
            return self._resolve_value(env_value)

        # 3. Project config
        config_value = self._resolve_from_project_config(env)
        if config_value is not None:
            logger.debug("Resolving from project config: '%s'", config_value)
            return self._resolve_value(config_value)

        # 4. Registry default (from project config defaults.stack)
        if self._project_config is not None:
            default_stack = self._project_config.defaults.stack
            if default_stack:
                logger.debug("Resolving from registry default: '%s'", default_stack)
                return self._resolve_value(default_stack)

        raise StackNotFoundError(
            stack_name="(unspecified)",
            available=self._available_names(),
        )

    def resolve_from_uri(self, uri: str) -> StackDefinition:
        """Resolve a stack from a direct URI.

        Supports fragment-based stack selection::

            github://org/repo@v1#stack_name

        The part before ``#`` is the source URI; the part after is the
        stack name within that source.

        Args:
            uri: Full URI, optionally with ``#stack_name`` fragment.

        Returns:
            The resolved ``StackDefinition``.

        Raises:
            StackNotFoundError: If the stack is not found at the URI.
            StackSourceError: If the source cannot be accessed.
        """
        stack_name: str | None = None
        source_uri = uri

        if "#" in uri:
            source_uri, stack_name = uri.rsplit("#", 1)

        from flowyml.stacks.enterprise.sources.base import parse_source_uri

        source = parse_source_uri(source_uri)

        if stack_name:
            return source.fetch(stack_name)

        # No fragment — return the first (or only) stack from the source
        stacks = source.fetch_all()
        if not stacks:
            raise StackNotFoundError(
                stack_name="(any)",
                source=source_uri,
            )
        return stacks[0]

    # ------------------------------------------------------------------
    # Listing
    # ------------------------------------------------------------------

    def list_stacks(self) -> list[StackReference]:
        """List all available stacks across all registered sources.

        Returns:
            List of ``StackReference`` objects, or empty list if no
            registry is configured.
        """
        if self._registry is None:
            return []
        try:
            return self._registry.list_stacks()
        except Exception as exc:
            logger.warning("Failed to list stacks: %s", exc)
            return []

    # ------------------------------------------------------------------
    # Environment helpers
    # ------------------------------------------------------------------

    def get_environment_config(self, env: str) -> EnvironmentConfig | None:
        """Retrieve the environment configuration for a named environment.

        Args:
            env: Environment name.

        Returns:
            ``EnvironmentConfig`` or ``None`` if no project config or env.
        """
        if self._project_config is None:
            return None
        return self._project_config.environments.get(env)

    # ------------------------------------------------------------------
    # Private resolution layers
    # ------------------------------------------------------------------

    def _resolve_from_env(self) -> str | None:
        """Check ``FLOWYML_STACK`` and ``FLOWYML_ENV`` environment variables.

        ``FLOWYML_STACK`` is a direct stack name or URI.
        ``FLOWYML_ENV`` selects an environment from the project config,
        whose ``stack`` field is then returned.

        Returns:
            Stack name/URI string or ``None``.
        """
        stack_var = os.environ.get("FLOWYML_STACK")
        if stack_var:
            return stack_var

        env_var = os.environ.get("FLOWYML_ENV")
        if env_var and self._project_config is not None:
            env_config = self._project_config.environments.get(env_var)
            if env_config is not None and env_config.stack:
                return env_config.stack

        return None

    def _resolve_from_project_config(self, env: str | None) -> str | None:
        """Look up the stack in the project config for a given environment.

        Args:
            env: Environment name.  If ``None``, only the default stack
                 is considered (handled by the caller).

        Returns:
            Stack name/URI string or ``None``.
        """
        if self._project_config is None:
            return None

        if env is not None:
            env_config = self._project_config.environments.get(env)
            if env_config is not None and env_config.stack:
                return env_config.stack

        return None

    # ------------------------------------------------------------------
    # Auto-bootstrap
    # ------------------------------------------------------------------

    def _auto_bootstrap(self) -> None:
        """Discover project config and create a registry automatically.

        Called when ``StackResolver()`` is created with no arguments. This
        enables the resolver to work out-of-the-box in pipeline code and
        CLI commands without manual registry setup.
        """
        # 1. Try to discover flowyml.yaml
        try:
            config = load_project_config()
            if config is not None:
                self._project_config = config
                logger.debug(
                    "Auto-discovered project config: %s",
                    config.project.name,
                )
        except Exception as exc:
            logger.debug("Failed to load project config: %s", exc)
            config = None

        # 2. Build registry from config sources + local stacks/ directories
        sources: list[str] = []

        # Add sources from project config
        if config is not None and config.registry.sources:
            sources.extend(config.registry.sources)

        # 3. Discover local stack directories
        local_stack_dirs = [
            Path.cwd() / "stacks",
            Path.cwd() / ".flowyml" / "stacks",
            Path.home() / ".flowyml" / "stacks",
        ]

        try:
            from flowyml.stacks.enterprise.sources.local import LocalStackSource

            local_paths = [str(d) for d in local_stack_dirs if d.is_dir()]
            if local_paths:
                local_source = LocalStackSource(paths=local_paths)
                # Create registry with local source
                self._registry = EnterpriseStackRegistry(sources=[local_source])
                logger.debug(
                    "Auto-created registry with local stacks from: %s",
                    local_paths,
                )
        except ImportError:
            pass
        except Exception as exc:
            logger.debug("Failed to create local stack source: %s", exc)

        # Add remote sources from config
        if sources and self._registry is not None:
            for uri in sources:
                try:
                    from flowyml.stacks.enterprise.sources.base import parse_source_uri

                    source = parse_source_uri(uri)
                    self._registry.add_source(source)
                    logger.debug("Added remote source: %s", uri)
                except Exception as exc:
                    logger.debug("Failed to add source '%s': %s", uri, exc)
        elif sources and self._registry is None:
            try:
                self._registry = EnterpriseStackRegistry.from_sources(sources)
            except Exception as exc:
                logger.debug("Failed to create registry from sources: %s", exc)

        # 4. Attach lock manager if flowyml.lock exists
        lock_path = Path.cwd() / "flowyml.lock"
        if lock_path.exists():
            try:
                project_name = config.project.name if config is not None else "default"
                self._lock_manager = StackLockManager(
                    lock_path=str(lock_path),
                    project_name=project_name,
                )
                if self._registry is not None:
                    self._registry.set_lock_manager(self._lock_manager)
                logger.debug("Attached lock manager from %s", lock_path)
            except Exception as exc:
                logger.debug("Failed to load lock file: %s", exc)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_value(self, value: str) -> StackDefinition:
        """Resolve a stack value that is either a URI or a plain name.

        Args:
            value: Stack name or URI.

        Returns:
            ``StackDefinition``.

        Raises:
            StackNotFoundError: If the stack cannot be found.
        """
        # Direct URI
        if "://" in value:
            return self.resolve_from_uri(value)

        # Named look-up via registry
        if self._registry is not None:
            return self._registry.resolve(value)

        raise StackNotFoundError(
            stack_name=value,
            suggestion=(
                "No registry is configured.  Pass a registry to the "
                "StackResolver or use a full URI (e.g. github://org/repo@v1#stack). "
                "Alternatively, place stack YAML files in a 'stacks/' directory."
            ),
        )

    def _available_names(self) -> list[str] | None:
        """Return names of available stacks, if a registry is attached."""
        if self._registry is None:
            return None
        try:
            return [ref.name for ref in self._registry.list_stacks()]
        except Exception:
            return None
