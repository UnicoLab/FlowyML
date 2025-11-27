"""Stack Registry - Manage and switch between different stacks.

This module provides a registry for storing, loading, and switching
between different infrastructure stacks.
"""

import json
from pathlib import Path
from typing import Any
from uniflow.stacks.base import Stack


class StackRegistry:
    """Registry for managing multiple stacks.

    The registry allows you to:
    - Register stacks with unique names
    - Switch between stacks seamlessly
    - Save and load stack configurations
    - List available stacks

    Example:
        ```python
        from uniflow.stacks import StackRegistry, LocalStack
        from uniflow.stacks.gcp import GCPStack

        # Initialize registry
        registry = StackRegistry()

        # Register stacks
        local_stack = LocalStack(name="local")
        registry.register_stack(local_stack)

        gcp_stack = GCPStack(name="production", project_id="my-project", bucket_name="my-artifacts")
        registry.register_stack(gcp_stack)

        # Switch stacks
        registry.set_active_stack("local")  # For development
        registry.set_active_stack("production")  # For production

        # Get active stack
        active = registry.get_active_stack()
        ```
    """

    def __init__(self, config_path: str | None = None):
        """Initialize stack registry.

        Args:
            config_path: Path to store stack configurations
        """
        self.config_path = Path(config_path or ".uniflow/stacks.json")
        self.stacks: dict[str, Stack] = {}
        self.active_stack_name: str | None = None

        # Create config directory
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        # Load existing configurations
        self.load()

    def register_stack(self, stack: Stack, set_active: bool = False) -> None:
        """Register a stack in the registry.

        Args:
            stack: Stack instance to register
            set_active: Whether to set this as the active stack
        """
        self.stacks[stack.name] = stack

        if set_active or self.active_stack_name is None:
            self.active_stack_name = stack.name

        # Save configuration
        self.save()

    def unregister_stack(self, name: str) -> None:
        """Remove a stack from the registry.

        Args:
            name: Name of the stack to remove
        """
        if name in self.stacks:
            del self.stacks[name]

            # If this was the active stack, clear it
            if self.active_stack_name == name:
                self.active_stack_name = list(self.stacks.keys())[0] if self.stacks else None

            self.save()

    def get_stack(self, name: str) -> Stack | None:
        """Get a specific stack by name.

        Args:
            name: Stack name

        Returns:
            Stack instance or None
        """
        return self.stacks.get(name)

    def get_active_stack(self) -> Stack | None:
        """Get the currently active stack.

        Returns:
            Active stack instance or None
        """
        if self.active_stack_name:
            return self.stacks.get(self.active_stack_name)
        return None

    def set_active_stack(self, name: str) -> None:
        """Set the active stack.

        Args:
            name: Name of the stack to activate
        """
        if name not in self.stacks:
            raise ValueError(f"Stack '{name}' not found in registry")

        self.active_stack_name = name
        self.save()

    def list_stacks(self) -> list[str]:
        """List all registered stacks.

        Returns:
            List of stack names
        """
        return list(self.stacks.keys())

    def describe_stack(self, name: str) -> dict[str, Any]:
        """Get detailed information about a stack.

        Args:
            name: Stack name

        Returns:
            Dictionary with stack details
        """
        stack = self.get_stack(name)
        if not stack:
            raise ValueError(f"Stack '{name}' not found")

        return {
            "name": stack.name,
            "is_active": name == self.active_stack_name,
            "config": stack.config.to_dict(),
        }

    def save(self) -> None:
        """Save stack configurations to disk."""
        config = {
            "active_stack": self.active_stack_name,
            "stacks": {name: self._serialize_stack(stack) for name, stack in self.stacks.items()},
        }

        with open(self.config_path, "w") as f:
            json.dump(config, f, indent=2)

    def load(self) -> None:
        """Load stack configurations from disk."""
        if not self.config_path.exists():
            return

        try:
            with open(self.config_path) as f:
                config = json.load(f)

            self.active_stack_name = config.get("active_stack")

            # Note: In a full implementation, we would deserialize
            # and recreate stack objects here. For now, stacks must
            # be registered programmatically.

        except Exception:
            pass

    def _serialize_stack(self, stack: Stack) -> dict[str, Any]:
        """Serialize a stack to dictionary."""
        return stack.config.to_dict()

    def clear(self) -> None:
        """Clear all registered stacks."""
        self.stacks.clear()
        self.active_stack_name = None
        self.save()

    def __repr__(self) -> str:
        active = f" (active: {self.active_stack_name})" if self.active_stack_name else ""
        return f"StackRegistry({len(self.stacks)} stacks{active})"


# Global registry instance
_global_registry: StackRegistry | None = None


def get_registry() -> StackRegistry:
    """Get the global stack registry instance.

    Returns:
        Global StackRegistry instance
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = StackRegistry()
    return _global_registry


def get_active_stack() -> Stack | None:
    """Get the currently active stack from the global registry.

    Returns:
        Active stack or None
    """
    return get_registry().get_active_stack()


def set_active_stack(name: str) -> None:
    """Set the active stack in the global registry.

    Args:
        name: Name of the stack to activate
    """
    get_registry().set_active_stack(name)
