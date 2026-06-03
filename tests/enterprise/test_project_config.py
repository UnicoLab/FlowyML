"""Tests for project-level configuration."""

import pytest
import yaml

from flowyml.stacks.enterprise.project_config import (
    DefaultsConfig,
    EnvironmentConfig,
    ProjectConfig,
    ProjectInfo,
    RegistryConfig,
    load_project_config,
    resolve_environment,
)


def _make_project_config_dict():
    """Return a valid flowyml.yaml structure as a dict."""
    return {
        "project": {
            "name": "test-project",
            "owner": "test-team",
        },
        "defaults": {
            "stack": "local_dev",
            "environment": "dev",
        },
        "environments": {
            "dev": {"stack": "local_dev"},
            "production": {
                "stack": "aml_gpu_large",
                "requireLock": True,
                "requirePolicyValidation": True,
            },
        },
        "registry": {
            "sources": ["file:///tmp/stacks"],
        },
    }


class TestLoadProjectConfig:
    """load_project_config() loading and discovery."""

    def test_load_project_config_from_file(self, tmp_path):
        """Loading from an explicit file path returns a valid ProjectConfig."""
        config_data = _make_project_config_dict()
        config_path = tmp_path / "flowyml.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config_data, f)

        config = load_project_config(path=str(config_path))
        assert config is not None, "Config should be loaded"
        assert config.project.name == "test-project"
        assert config.project.owner == "test-team"
        assert len(config.environments) == 2
        assert "production" in config.environments

    def test_load_project_config_auto_discovery(self, tmp_path, monkeypatch):
        """Auto-discovery returns None when no flowyml.yaml exists in tree."""
        # Point CWD to a directory with no flowyml.yaml
        monkeypatch.chdir(tmp_path)
        config = load_project_config(path=None)
        assert config is None, "Auto-discovery should return None when no config exists"


class TestResolveEnvironment:
    """resolve_environment() lookup and fallback."""

    def _make_config(self):
        """Create a ProjectConfig for testing."""
        return ProjectConfig(
            project=ProjectInfo(name="test-project", owner="test-team"),
            defaults=DefaultsConfig(stack="local_dev", environment="dev"),
            environments={
                "dev": EnvironmentConfig(stack="local_dev"),
                "production": EnvironmentConfig(
                    stack="aml_gpu_large",
                    requireLock=True,
                    requirePolicyValidation=True,
                ),
            },
            registry=RegistryConfig(sources=["file:///tmp/stacks"]),
        )

    def test_resolve_environment(self):
        """Resolving a known environment returns its configuration."""
        config = self._make_config()
        env = resolve_environment(config, "production")

        assert env.stack == "aml_gpu_large"
        assert env.require_lock is True, "Production should require lock"
        assert env.require_policy_validation is True

    def test_resolve_environment_not_found(self):
        """Resolving an unknown environment returns a default config."""
        config = self._make_config()
        env = resolve_environment(config, "nonexistent")

        assert env.stack == "local_dev", "Fallback should use defaults.stack"
        assert env.require_lock is False, "Default should not require lock"
