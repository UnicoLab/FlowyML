"""Plugin Configuration System.

This module handles the configuration of plugins and adaptation rules,
allowing users to define how external components map to UniFlow.
"""

from dataclasses import dataclass, field
from typing import Any
import yaml
from pathlib import Path

from uniflow.stacks.components import ComponentType
from uniflow.stacks.bridge import AdaptationRule


@dataclass
class PluginConfig:
    """Configuration for a single plugin."""

    name: str
    source: str  # Import path or bridge URI
    component_type: str = "orchestrator"  # orchestrator, artifact_store, etc.
    adaptation: dict[str, Any] = field(default_factory=dict)


class PluginManager:
    """Manages plugin configurations and rules."""

    def __init__(self):
        self.configs: list[PluginConfig] = []

    def load_from_yaml(self, path: str) -> None:
        """Load plugin configurations from a YAML file."""
        path_obj = Path(path)
        if not path_obj.exists():
            return

        with open(path) as f:
            data = yaml.safe_load(f)

        if not data or "plugins" not in data:
            return

        for p_data in data["plugins"]:
            self.configs.append(
                PluginConfig(
                    name=p_data["name"],
                    source=p_data["source"],
                    component_type=p_data.get("type", "orchestrator"),
                    adaptation=p_data.get("adaptation", {}),
                ),
            )

    def get_adaptation_rules(self) -> list[AdaptationRule]:
        """Convert configurations to adaptation rules."""
        rules = []
        for config in self.configs:
            # Determine target type
            target_type = ComponentType.ORCHESTRATOR
            if config.component_type == "artifact_store":
                target_type = ComponentType.ARTIFACT_STORE
            elif config.component_type == "container_registry":
                target_type = ComponentType.CONTAINER_REGISTRY

            # Extract mapping
            method_mapping = config.adaptation.get("method_mapping", {})
            attribute_mapping = config.adaptation.get("attribute_mapping", {})

            # Create rule
            rule = AdaptationRule(
                source_type=config.source,
                target_type=target_type,
                method_mapping=method_mapping,
                attribute_mapping=attribute_mapping,
            )
            rules.append(rule)

        return rules
