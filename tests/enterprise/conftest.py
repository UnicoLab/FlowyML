"""Shared fixtures for the Enterprise Stack Registry test suite."""

import pytest
import tempfile
import os
import yaml


@pytest.fixture
def sample_stack_dict():
    return {
        "apiVersion": "flowyml.io/v1",
        "kind": "Stack",
        "metadata": {
            "name": "test_cpu_stack",
            "version": "1.0.0",
            "description": "Test CPU stack",
            "owner": "test-team",
            "tags": ["test", "cpu"],
        },
        "spec": {
            "backend": "local",
            "runtime": {"pythonVersion": "3.11"},
            "compute": {"type": "cpu"},
        },
    }


@pytest.fixture
def sample_stack(sample_stack_dict):
    from flowyml.stacks.enterprise.models import StackDefinition

    return StackDefinition.from_dict(sample_stack_dict)


@pytest.fixture
def azureml_stack_dict():
    return {
        "apiVersion": "flowyml.io/v1",
        "kind": "Stack",
        "metadata": {
            "name": "aml_cpu_small",
            "version": "1.2.0",
            "description": "AzureML CPU stack",
            "owner": "ml-platform-team",
            "tags": ["azureml", "cpu", "production"],
        },
        "spec": {
            "backend": "azureml",
            "runtime": {"pythonVersion": "3.11", "baseImage": "myregistry.azurecr.io/flowyml/sklearn:1.2.0"},
            "compute": {"type": "cpu", "size": "Standard_DS3_v2", "region": "francecentral"},
            "policies": {
                "allowCustomDockerImage": False,
                "deniedPythonPackages": ["torch-nightly"],
                "maxRuntimeMinutes": 120,
            },
            "permissions": {
                "allowedGroups": ["ml-team", "data-science"],
            },
        },
    }


@pytest.fixture
def azureml_stack(azureml_stack_dict):
    from flowyml.stacks.enterprise.models import StackDefinition

    return StackDefinition.from_dict(azureml_stack_dict)


@pytest.fixture
def tmp_stack_file(sample_stack_dict, tmp_path):
    path = tmp_path / "test_stack.yaml"
    with open(path, "w") as f:
        yaml.dump(sample_stack_dict, f)
    return str(path)


@pytest.fixture
def tmp_stacks_dir(sample_stack_dict, azureml_stack_dict, tmp_path):
    stacks_dir = tmp_path / "stacks"
    stacks_dir.mkdir()
    with open(stacks_dir / "local.yaml", "w") as f:
        yaml.dump(sample_stack_dict, f)
    with open(stacks_dir / "azureml.yaml", "w") as f:
        yaml.dump(azureml_stack_dict, f)
    return str(stacks_dir)
