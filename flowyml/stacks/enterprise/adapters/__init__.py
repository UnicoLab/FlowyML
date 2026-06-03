"""Backend adapters for the Enterprise Stack Registry.

This sub-package provides concrete ``BackendAdapter`` implementations that
bridge FlowyML pipeline graphs to specific execution platforms.

Available adapters:

* ``LocalBackendAdapter`` — wraps the existing local executor / orchestrator.
* ``MockEnterpriseBackendAdapter`` — in-memory adapter for testing.
* ``AzureMLBackendAdapter`` — maps FlowyML concepts to Azure ML primitives.
"""

from __future__ import annotations

from flowyml.stacks.enterprise.adapters.local import LocalBackendAdapter
from flowyml.stacks.enterprise.adapters.mock import MockEnterpriseBackendAdapter
from flowyml.stacks.enterprise.adapters.azureml import AzureMLBackendAdapter

__all__ = [
    "LocalBackendAdapter",
    "MockEnterpriseBackendAdapter",
    "AzureMLBackendAdapter",
]
