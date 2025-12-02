"""Generic Bridge for adapting external components to flowyml.

This module provides a universal bridge that can wrap components from other
frameworks (ZenML, Airflow, Prefect, etc.) using rule-based adaptation.
"""

import inspect
from dataclasses import dataclass, field
from typing import Any
import logging

from flowyml.stacks.components import (
    StackComponent,
    Orchestrator,
    ArtifactStore,
    ContainerRegistry,
    ComponentType,
)

logger = logging.getLogger(__name__)


@dataclass
class AdaptationRule:
    """Rule for adapting an external component."""

    # Matching criteria
    source_type: str | None = None  # e.g., "zenml.orchestrators.base.BaseOrchestrator"
    name_pattern: str | None = None  # e.g., ".*Orchestrator"
    has_methods: list[str] = field(default_factory=list)  # e.g., ["run", "prepare_pipeline"]

    # Adaptation logic
    target_type: ComponentType = ComponentType.ORCHESTRATOR
    method_mapping: dict[str, str] = field(default_factory=dict)  # flowyml_method -> external_method
    attribute_mapping: dict[str, str] = field(default_factory=dict)  # flowyml_attr -> external_attr


class GenericBridge:
    """Universal bridge for external components."""

    def __init__(self, rules: list[AdaptationRule] | None = None):
        self.rules = rules or []

    def is_available(self) -> bool:
        """Check if the bridge is available (always true for generic)."""
        return True

    def wrap_component(
        self,
        external_class: Any,
        name: str,
        config: dict[str, Any] | None = None,
    ) -> type[StackComponent]:
        """Dynamically create a wrapper class based on rules.

        Args:
            external_class: The external component class to wrap
            name: Name for the component
            config: Optional configuration dictionary

        Returns:
            A flowyml StackComponent class that wraps the external component
        """
        # Determine component type and applicable rule
        rule = self._find_matching_rule(external_class)
        component_type = rule.target_type if rule else self._infer_component_type(external_class)

        # Create the wrapper class dynamically
        if component_type == ComponentType.ORCHESTRATOR:
            return self._create_orchestrator_wrapper(external_class, name, rule)
        elif component_type == ComponentType.ARTIFACT_STORE:
            return self._create_artifact_store_wrapper(external_class, name, rule)
        elif component_type == ComponentType.CONTAINER_REGISTRY:
            return self._create_container_registry_wrapper(external_class, name, rule)
        else:
            return self._create_generic_wrapper(external_class, name, component_type, rule)

    def _find_matching_rule(self, external_class: Any) -> AdaptationRule | None:
        """Find the first rule that matches the external class."""
        for rule in self.rules:
            # Check source type
            if rule.source_type:
                # Check inheritance hierarchy names
                mro_names = [c.__module__ + "." + c.__name__ for c in inspect.getmro(external_class)]
                if rule.source_type not in mro_names:
                    continue

            # Check name pattern
            if rule.name_pattern:
                import re

                if not re.match(rule.name_pattern, external_class.__name__):
                    continue

            # Check methods
            if rule.has_methods:
                has_all = True
                for method in rule.has_methods:
                    if not hasattr(external_class, method):
                        has_all = False
                        break
                if not has_all:
                    continue

            return rule
        return None

    def _infer_component_type(self, external_class: Any) -> ComponentType:
        """Infer component type if no rule matches."""
        name = external_class.__name__.lower()
        if "orchestrator" in name:
            return ComponentType.ORCHESTRATOR
        elif "artifact" in name and "store" in name:
            return ComponentType.ARTIFACT_STORE
        elif "container" in name and "registry" in name:
            return ComponentType.CONTAINER_REGISTRY
        return ComponentType.ORCHESTRATOR  # Default

    def _create_orchestrator_wrapper(
        self,
        external_class: Any,
        name: str,
        rule: AdaptationRule | None,
    ) -> type[Orchestrator]:
        """Create a wrapper for an Orchestrator."""

        class GenericOrchestratorWrapper(Orchestrator):
            def __init__(self, **kwargs):
                super().__init__(name)
                self._external_component = external_class(**kwargs)
                self._rule = rule

            @property
            def component_type(self) -> ComponentType:
                return ComponentType.ORCHESTRATOR

            def validate(self) -> bool:
                # Try to find a validate method
                if hasattr(self._external_component, "validate"):
                    return self._external_component.validate()
                return True

            def to_dict(self) -> dict[str, Any]:
                if hasattr(self._external_component, "dict"):
                    return self._external_component.dict()
                if hasattr(self._external_component, "to_dict"):
                    return self._external_component.to_dict()
                return {"name": self.name, "type": "generic_wrapper"}

            def run_pipeline(self, pipeline: Any, **kwargs) -> Any:
                """Delegate pipeline execution."""
                method_name = "run"
                if self._rule and "run_pipeline" in self._rule.method_mapping:
                    method_name = self._rule.method_mapping["run_pipeline"]

                if hasattr(self._external_component, method_name):
                    method = getattr(self._external_component, method_name)
                    return method(pipeline, **kwargs)

                logger.warning(f"Orchestrator {self.name} does not have method '{method_name}'")
                return None

            def get_run_status(self, run_id: str) -> str:
                return "unknown"

            def __getattr__(self, name: str) -> Any:
                """Delegate unknown attributes to external component."""
                return getattr(self._external_component, name)

        GenericOrchestratorWrapper.__name__ = f"Wrapped{external_class.__name__}"
        return GenericOrchestratorWrapper

    def _create_artifact_store_wrapper(
        self,
        external_class: Any,
        name: str,
        rule: AdaptationRule | None,
    ) -> type[ArtifactStore]:
        """Create a wrapper for an Artifact Store."""

        class GenericArtifactStoreWrapper(ArtifactStore):
            def __init__(self, **kwargs):
                super().__init__(name)
                self._external_component = external_class(**kwargs)
                self._rule = rule

            @property
            def component_type(self) -> ComponentType:
                return ComponentType.ARTIFACT_STORE

            def validate(self) -> bool:
                return True

            def to_dict(self) -> dict[str, Any]:
                if hasattr(self._external_component, "dict"):
                    return self._external_component.dict()
                return {"name": self.name}

            # Explicitly implement abstract methods to satisfy ABC
            def save(self, artifact: Any, path: str) -> str:
                return self._external_component.save(artifact, path)

            def load(self, path: str) -> Any:
                return self._external_component.load(path)

            def exists(self, path: str) -> bool:
                return self._external_component.exists(path)

            def __getattr__(self, name: str) -> Any:
                return getattr(self._external_component, name)

        GenericArtifactStoreWrapper.__name__ = f"Wrapped{external_class.__name__}"
        return GenericArtifactStoreWrapper

    def _create_container_registry_wrapper(
        self,
        external_class: Any,
        name: str,
        rule: AdaptationRule | None,
    ) -> type[ContainerRegistry]:
        """Create a wrapper for a Container Registry."""

        class GenericContainerRegistryWrapper(ContainerRegistry):
            def __init__(self, **kwargs):
                super().__init__(name)
                self._external_component = external_class(**kwargs)
                self._rule = rule

            @property
            def component_type(self) -> ComponentType:
                return ComponentType.CONTAINER_REGISTRY

            def validate(self) -> bool:
                return True

            def to_dict(self) -> dict[str, Any]:
                if hasattr(self._external_component, "dict"):
                    return self._external_component.dict()
                return {"name": self.name}

            # Explicitly implement abstract methods to satisfy ABC
            def push_image(self, image_name: str, tag: str = "latest") -> str:
                return self._external_component.push_image(image_name, tag)

            def pull_image(self, image_name: str, tag: str = "latest") -> None:
                return self._external_component.pull_image(image_name, tag)

            def get_image_uri(self, image_name: str, tag: str = "latest") -> str:
                return self._external_component.get_image_uri(image_name, tag)

            def __getattr__(self, name: str) -> Any:
                return getattr(self._external_component, name)

        GenericContainerRegistryWrapper.__name__ = f"Wrapped{external_class.__name__}"
        return GenericContainerRegistryWrapper

    def _create_generic_wrapper(
        self,
        external_class: Any,
        name: str,
        comp_type: ComponentType,
        rule: AdaptationRule | None,
    ) -> type[StackComponent]:
        """Create a generic wrapper."""

        class GenericWrapper(StackComponent):
            def __init__(self, **kwargs):
                super().__init__(name)
                self._external_component = external_class(**kwargs)
                self._rule = rule

            @property
            def component_type(self) -> ComponentType:
                return comp_type

            def validate(self) -> bool:
                return True

            def to_dict(self) -> dict[str, Any]:
                if hasattr(self._external_component, "dict"):
                    return self._external_component.dict()
                return {"name": self.name}

            def __getattr__(self, name: str) -> Any:
                return getattr(self._external_component, name)

        GenericWrapper.__name__ = f"Wrapped{external_class.__name__}"
        return GenericWrapper
