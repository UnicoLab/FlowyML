"""Unit tests for the Generic Bridge."""

import pytest
from unittest.mock import MagicMock
from typing import Any

from flowyml.stacks.bridge import GenericBridge, AdaptationRule
from flowyml.stacks.components import ComponentType, Orchestrator, ArtifactStore


# Mock external classes
class ExternalOrchestrator:
    def __init__(self, **kwargs):
        self.config = kwargs

    def run(self, pipeline, **kwargs):
        return "run_result"

    def dict(self):
        return {"name": "external_orch"}


class ExternalStore:
    pass  # No specific methods, relies on inference or rules


def test_generic_bridge_inference():
    """Test component type inference."""
    bridge = GenericBridge()

    # Test inference by name
    class MyOrchestrator:
        pass

    wrapper = bridge.wrap_component(MyOrchestrator, "test_orch")
    assert issubclass(wrapper, Orchestrator)

    class MyArtifactStore:
        pass

    wrapper = bridge.wrap_component(MyArtifactStore, "test_store")
    assert issubclass(wrapper, ArtifactStore)


def test_generic_bridge_rules():
    """Test rule-based adaptation."""
    # Define a rule
    rule = AdaptationRule(
        name_pattern=".*External.*",
        target_type=ComponentType.ORCHESTRATOR,
        method_mapping={"run_pipeline": "run"},
    )

    bridge = GenericBridge(rules=[rule])

    # Wrap component matching the rule
    WrapperClass = bridge.wrap_component(ExternalOrchestrator, "test_orch")
    wrapper = WrapperClass()

    assert isinstance(wrapper, Orchestrator)
    assert wrapper.component_type == ComponentType.ORCHESTRATOR

    # Test method delegation via mapping
    result = wrapper.run_pipeline("pipeline")
    assert result == "run_result"

    # Test attribute delegation
    assert wrapper.config == {}


def test_generic_bridge_source_type_matching():
    """Test matching by source type (inheritance)."""

    class BaseExternal:
        pass

    class ConcreteExternal(BaseExternal):
        def save(self, artifact, path):
            pass

        def load(self, path):
            pass

        def exists(self, path):
            return True

    rule = AdaptationRule(
        source_type=f"{BaseExternal.__module__}.BaseExternal",
        target_type=ComponentType.ARTIFACT_STORE,
    )

    bridge = GenericBridge(rules=[rule])

    WrapperClass = bridge.wrap_component(ConcreteExternal, "test_comp")
    wrapper = WrapperClass()

    assert isinstance(wrapper, ArtifactStore)
    # Verify abstract methods are implemented (via wrapper or external)
    assert wrapper.exists("path") is True
