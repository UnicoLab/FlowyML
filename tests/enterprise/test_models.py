"""Tests for enterprise stack Pydantic models."""

import pytest
import yaml
from pydantic import ValidationError

from flowyml.stacks.enterprise.models import (
    PolicyConfig,
    RegistryIndex,
    StackDefinition,
    StackLock,
    StackLockEntry,
)


class TestStackDefinitionFromDict:
    """StackDefinition.from_dict — valid creation."""

    def test_stack_definition_from_dict(self, sample_stack_dict):
        """Valid dict creates a StackDefinition with correct properties."""
        stack = StackDefinition.from_dict(sample_stack_dict)
        assert stack.name == "test_cpu_stack", "Name should match metadata.name"
        assert stack.version == "1.0.0", "Version should match metadata.version"
        assert stack.backend == "local", "Backend should match spec.backend"

    def test_stack_definition_from_yaml(self, tmp_stack_file):
        """Load a StackDefinition from a YAML file on disk."""
        stack = StackDefinition.from_yaml(tmp_stack_file)
        assert stack.name == "test_cpu_stack", "Stack loaded from YAML should have correct name"
        assert stack.version == "1.0.0"

    def test_stack_definition_invalid_version(self, sample_stack_dict):
        """Non-semver version string is rejected."""
        sample_stack_dict["metadata"]["version"] = "abc"
        with pytest.raises(ValidationError, match="Invalid semantic version"):
            StackDefinition.from_dict(sample_stack_dict)

    def test_stack_definition_invalid_backend(self, sample_stack_dict):
        """Unknown backend is rejected."""
        sample_stack_dict["spec"]["backend"] = "unknown_backend"
        with pytest.raises(ValidationError, match="Unsupported backend"):
            StackDefinition.from_dict(sample_stack_dict)

    def test_stack_definition_invalid_compute_type(self, sample_stack_dict):
        """Unknown compute type is rejected."""
        sample_stack_dict["spec"]["compute"]["type"] = "fpga"
        with pytest.raises(ValidationError, match="Unsupported compute type"):
            StackDefinition.from_dict(sample_stack_dict)

    def test_stack_definition_instance_range(self, sample_stack_dict):
        """minInstances > maxInstances is rejected."""
        sample_stack_dict["spec"]["compute"]["minInstances"] = 5
        sample_stack_dict["spec"]["compute"]["maxInstances"] = 2
        with pytest.raises(ValidationError, match="minInstances.*cannot exceed.*maxInstances"):
            StackDefinition.from_dict(sample_stack_dict)

    def test_stack_definition_compute_digest(self, sample_stack):
        """compute_digest() returns a deterministic SHA-256 hash."""
        digest_a = sample_stack.compute_digest()
        digest_b = sample_stack.compute_digest()
        assert digest_a == digest_b, "Digest should be deterministic"
        assert digest_a.startswith("sha256:"), "Digest should have sha256: prefix"

    def test_stack_definition_to_stack(self, sample_stack):
        """to_stack() returns a runtime Stack with the correct name."""
        runtime_stack = sample_stack.to_stack()
        assert hasattr(runtime_stack, "name"), "Runtime stack should have a name attribute"
        assert runtime_stack.name == "test_cpu_stack"

    def test_stack_definition_name_validation(self, sample_stack_dict):
        """Name starting with a digit is rejected."""
        sample_stack_dict["metadata"]["name"] = "123invalid"
        with pytest.raises(ValidationError):
            StackDefinition.from_dict(sample_stack_dict)

    def test_stack_definition_api_version_validation(self, sample_stack_dict):
        """Wrong apiVersion is rejected."""
        sample_stack_dict["apiVersion"] = "v99"
        with pytest.raises(ValidationError, match="Unsupported apiVersion"):
            StackDefinition.from_dict(sample_stack_dict)

    def test_stack_definition_extra_fields_forbidden(self, sample_stack_dict):
        """Extra top-level fields are rejected (extra='forbid')."""
        sample_stack_dict["unknown_field"] = "should_fail"
        with pytest.raises(ValidationError):
            StackDefinition.from_dict(sample_stack_dict)


class TestStackLock:
    """StackLock round-trip serialization."""

    def test_stack_lock_round_trip(self, sample_stack, tmp_path):
        """Create a StackLock, save to YAML, reload, and verify content."""
        lock = StackLock(
            project="test-project",
            resolvedStacks={
                "test_cpu_stack": StackLockEntry(
                    source="local://",
                    digest=sample_stack.compute_digest(),
                    resolvedAt="2026-06-01T00:00:00Z",
                ),
            },
        )
        lock_path = str(tmp_path / "flowyml.lock")
        lock.to_yaml(lock_path)

        loaded = StackLock.from_yaml(lock_path)
        assert loaded.project == "test-project", "Project name should survive round-trip"
        assert "test_cpu_stack" in loaded.resolved_stacks, "Stack entry should survive round-trip"
        assert loaded.resolved_stacks["test_cpu_stack"].digest == sample_stack.compute_digest()


class TestRegistryIndex:
    """RegistryIndex loading."""

    def test_registry_index_from_yaml(self, tmp_path):
        """Create a RegistryIndex YAML, load it, and verify content."""
        index_data = {
            "apiVersion": "flowyml.io/v1",
            "kind": "StackRegistry",
            "metadata": {"name": "test-registry", "version": "1.0.0"},
            "stacks": [
                {"name": "stack_a", "path": "stacks/a.yaml"},
                {"name": "stack_b", "path": "stacks/b.yaml"},
            ],
        }
        index_path = tmp_path / "registry.yaml"
        with open(index_path, "w") as f:
            yaml.dump(index_data, f)

        idx = RegistryIndex.from_yaml(str(index_path))
        assert idx.metadata.name == "test-registry"
        assert len(idx.stacks) == 2, "Index should contain 2 stack entries"
        assert idx.stacks[0].name == "stack_a"


class TestPolicyConfig:
    """PolicyConfig validation."""

    def test_policy_config_package_overlap(self):
        """Packages in both allowed and denied lists are rejected."""
        with pytest.raises(ValidationError, match="both allowed and denied"):
            PolicyConfig(
                allowedPythonPackages=["numpy", "pandas"],
                deniedPythonPackages=["pandas"],
            )
