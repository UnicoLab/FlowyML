"""Tests for enterprise stack sources."""

import pytest
import yaml

from flowyml.stacks.enterprise.exceptions import StackNotFoundError, StackSourceError
from flowyml.stacks.enterprise.models import StackDefinition
from flowyml.stacks.enterprise.sources.local import LocalStackSource


class TestLocalStackSource:
    """LocalStackSource discovery and loading."""

    def test_local_source_list_stacks(self, tmp_stacks_dir):
        """Scanning a directory discovers all valid stack YAML files."""
        source = LocalStackSource(paths=[tmp_stacks_dir])
        refs = source.list_stacks()
        assert len(refs) == 2, f"Expected 2 stack refs, got {len(refs)}"
        names = {r.name for r in refs}
        assert "test_cpu_stack" in names
        assert "aml_cpu_small" in names

    def test_local_source_load_stack(self, tmp_stacks_dir):
        """load_stack() returns a StackDefinition with the correct name."""
        source = LocalStackSource(paths=[tmp_stacks_dir])
        stack = source.load_stack("test_cpu_stack")
        assert isinstance(stack, StackDefinition)
        assert stack.name == "test_cpu_stack"

    def test_local_source_stack_not_found(self, tmp_stacks_dir):
        """load_stack() raises StackNotFoundError for unknown stacks."""
        source = LocalStackSource(paths=[tmp_stacks_dir])
        with pytest.raises(StackNotFoundError):
            source.load_stack("nonexistent_stack")


class TestParseSourceUri:
    """parse_source_uri() URI parsing."""

    def test_parse_source_uri_local_path(self):
        """file:// URIs create a source without raising StackSourceError."""
        from flowyml.stacks.enterprise.sources.base import parse_source_uri

        # This should not raise StackSourceError (though the path may
        # not exist, the source is constructed lazily)
        try:
            source = parse_source_uri("file:///tmp/stacks")
            assert source is not None
        except (ImportError, Exception) as exc:
            # FileStackSource might fail if the path doesn't exist, but
            # it should NOT be a StackSourceError for the URI format
            assert not isinstance(exc, StackSourceError), f"file:// URIs should be recognised, got: {exc}"

    def test_parse_source_uri_github(self):
        """github:// URIs are recognised as valid."""
        from flowyml.stacks.enterprise.sources.base import parse_source_uri

        try:
            source = parse_source_uri("github://org/repo@v1")
            assert source is not None
        except ImportError:
            pytest.skip("Git source dependencies not installed")
        except StackSourceError:
            pytest.fail("github:// URIs should be a recognised scheme")

    def test_parse_source_uri_http(self):
        """http:// URIs are supported via HTTPStackSource."""
        from flowyml.stacks.enterprise.sources.base import parse_source_uri

        try:
            source = parse_source_uri("http://example.com")
            assert source is not None
        except ImportError:
            pytest.skip("HTTP source dependencies not installed")


class TestRegistryIndexSource:
    """RegistryIndexSource loading and resolution."""

    def test_registry_index_source(self, sample_stack_dict, tmp_path):
        """A RegistryIndexSource discovers and loads stacks from an index."""
        from flowyml.stacks.enterprise.sources.registry_index import RegistryIndexSource

        # Create the directory structure: index + stack files
        stacks_dir = tmp_path / "definitions"
        stacks_dir.mkdir()

        # Write the stack YAML
        stack_path = stacks_dir / "local.yaml"
        with open(stack_path, "w") as f:
            yaml.dump(sample_stack_dict, f)

        # Write the registry index
        index_data = {
            "apiVersion": "flowyml.io/v1",
            "kind": "StackRegistry",
            "metadata": {"name": "test-registry", "version": "1.0.0"},
            "stacks": [{"name": "test_cpu_stack", "path": "definitions/local.yaml"}],
        }
        index_path = tmp_path / "registry.yaml"
        with open(index_path, "w") as f:
            yaml.dump(index_data, f)

        source = RegistryIndexSource(index_path=str(index_path))

        # List stacks
        refs = source.list_stacks()
        assert len(refs) == 1, "Index should list 1 stack"
        assert refs[0].name == "test_cpu_stack"

        # Load a stack
        stack = source.load_stack("test_cpu_stack")
        assert stack.name == "test_cpu_stack"
        assert stack.version == "1.0.0"
