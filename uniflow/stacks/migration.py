"""Stack Migration Tools.

This module provides tools to migrate stacks from external systems (e.g., ZenML)
to UniFlow configuration.
"""

from typing import Any
import yaml
from dataclasses import asdict

from uniflow.stacks.plugin_config import PluginConfig


class StackMigrator:
    """Migrates stacks from external systems to UniFlow."""

    def migrate_zenml_stack(self, stack_name: str) -> dict[str, Any]:
        """Migrate a ZenML stack to UniFlow configuration."""
        try:
            from zenml.client import Client

            client = Client()
            stack = client.get_stack(stack_name)
        except ImportError:
            raise ImportError("ZenML is not installed. Please install it with: pip install zenml")
        except KeyError:
            raise ValueError(f"ZenML stack '{stack_name}' not found.")

        # Generate plugin configs for each component
        plugins = []
        stack_config = {
            "name": stack.name,
            "components": {},
        }

        for component_type, components in stack.components.items():
            # Handle list of components (ZenML specific)
            if not isinstance(components, list):
                components = [components]

            for component in components:
                # Create plugin config
                plugin_name = f"zenml_{component.name}"

                # Determine source class path
                # This relies on ZenML component having a valid module path
                # We might need to inspect the object class
                source_class = component.__class__.__module__ + "." + component.__class__.__name__

                plugin = PluginConfig(
                    name=plugin_name,
                    source=source_class,
                    component_type=self._map_zenml_type(component.type),
                    adaptation={
                        "method_mapping": {"run_pipeline": "run"} if component.type == "orchestrator" else {},
                    },
                )
                plugins.append(plugin)

                # Add to stack config
                # We use the plugin name as the component type in UniFlow stack config
                # This assumes the plugin is registered with this name
                stack_config["components"][component_type] = {
                    "type": plugin_name,
                    "config": component.configuration,
                }

        return {
            "plugins": [asdict(p) for p in plugins],
            "stack": stack_config,
        }

    def _map_zenml_type(self, zenml_type: str) -> str:
        """Map ZenML component type to UniFlow type."""
        type_mapping = {
            "orchestrator": "orchestrator",
            "artifact_store": "artifact_store",
            "container_registry": "container_registry",
        }
        return type_mapping.get(zenml_type, "custom")

    def generate_yaml(self, migration_data: dict[str, Any]) -> str:
        """Generate YAML configuration from migration data."""
        output = {
            "plugins": migration_data["plugins"],
            "stacks": {
                migration_data["stack"]["name"]: migration_data["stack"]["components"],
            },
        }
        return yaml.dump(output, sort_keys=False)
