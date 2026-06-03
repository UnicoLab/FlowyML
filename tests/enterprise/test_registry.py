"""Tests for the EnterpriseStackRegistry."""

import pytest

from flowyml.stacks.enterprise.exceptions import StackNotFoundError
from flowyml.stacks.enterprise.registry import EnterpriseStackRegistry
from flowyml.stacks.enterprise.sources.local import LocalStackSource


class TestEnterpriseStackRegistry:
    """EnterpriseStackRegistry resolution and listing."""

    def test_registry_from_source_local(self, tmp_stacks_dir):
        """Registry initialised with a LocalStackSource has 1 source."""
        source = LocalStackSource(paths=[tmp_stacks_dir])
        registry = EnterpriseStackRegistry(sources=[source])
        assert len(registry.sources) == 1, "Registry should have exactly 1 source"

    def test_registry_list_stacks(self, tmp_stacks_dir):
        """list_stacks() aggregates references from all sources."""
        source = LocalStackSource(paths=[tmp_stacks_dir])
        registry = EnterpriseStackRegistry(sources=[source])

        refs = registry.list_stacks()
        assert len(refs) >= 2, f"Expected at least 2 stack refs, got {len(refs)}"

    def test_registry_resolve_by_name(self, tmp_stacks_dir):
        """resolve() returns a StackDefinition matching the requested name."""
        source = LocalStackSource(paths=[tmp_stacks_dir])
        registry = EnterpriseStackRegistry(sources=[source])

        stack = registry.resolve("test_cpu_stack")
        assert stack.name == "test_cpu_stack"
        assert stack.version == "1.0.0"

    def test_registry_resolve_not_found(self, tmp_stacks_dir):
        """resolve() raises StackNotFoundError for unknown stacks."""
        source = LocalStackSource(paths=[tmp_stacks_dir])
        registry = EnterpriseStackRegistry(sources=[source])

        with pytest.raises(StackNotFoundError):
            registry.resolve("nonexistent_stack")
