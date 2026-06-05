"""Enterprise Stack Registry for FlowyML.

This sub-package implements a governed workflow abstraction layer that lets
platform teams centrally define, approve, version, and govern execution
stacks, while data scientists consume those stacks without changing pipeline
code.

Architecture::

    FlowyML Pipeline Code
            ↓
    Project Config / Stack Selector
            ↓
    Enterprise Stack Registry
            ↓
    Policy Validation
            ↓
    Backend Adapter
            ↓
    Local / AzureML / Kubernetes / Ray / Databricks / Other

Key principle::

    Data scientists write workflows.
    Platform teams control execution environments.
"""

from __future__ import annotations

from flowyml.stacks.enterprise.models import (
    ComputeConfig,
    ObservabilityConfig,
    PermissionsConfig,
    PolicyConfig,
    RegistryIndex,
    RegistryIndexEntry,
    RuntimeConfig,
    SecretsConfig,
    SecurityConfig,
    SignatureConfig,
    StackDefinition,
    StackLock,
    StackLockEntry,
    StackMetadata,
    StackReference,
    StackSpec,
    StorageConfig,
)
from flowyml.stacks.enterprise.exceptions import (
    PolicyViolationError,
    StackError,
    StackLockError,
    StackNotFoundError,
    StackSecurityError,
    StackSourceError,
    StackValidationError,
)
from flowyml.stacks.enterprise.registry import EnterpriseStackRegistry
from flowyml.stacks.enterprise.policy import (
    BackendAllowedRule,
    BaseImageApprovedRule,
    CostLimitRule,
    ExternalNetworkRule,
    MaxRuntimeRule,
    PackageAllowListRule,
    PackageDenyListRule,
    PolicyContext,
    PolicyEngine,
    PolicyResult,
    PolicyRule,
    ProjectPermissionRule,
    SignedStackRule,
    StackExistsRule,
    StackLockedRule,
    UserPermissionRule,
)
from flowyml.stacks.enterprise.lock import LockVerificationResult, StackLockManager
from flowyml.stacks.enterprise.project_config import (
    DefaultsConfig,
    EnvironmentConfig,
    ProjectConfig,
    ProjectInfo,
    RegistryConfig,
    load_project_config,
    resolve_environment,
)
from flowyml.stacks.enterprise.execution import ExecutionContext, BackendAdapter, RunHandle, RunStatus
from flowyml.stacks.enterprise.audit import AuditRecord, AuditStore
from flowyml.stacks.enterprise.resolver import StackResolver
from flowyml.stacks.enterprise.sources.base import StackSource, parse_source_uri
from flowyml.stacks.enterprise.secrets import (
    SecretsProvider,
    EnvSecretsProvider,
    LocalSecretsProvider,
    VaultSecretsProvider,
    AzureKeyVaultProvider,
    AWSSecretsManagerProvider,
    GCPSecretManagerProvider,
    get_secrets_provider,
)

__all__ = [
    # Models
    "StackDefinition",
    "StackMetadata",
    "StackSpec",
    "RuntimeConfig",
    "ComputeConfig",
    "StorageConfig",
    "SecretsConfig",
    "ObservabilityConfig",
    "PolicyConfig",
    "PermissionsConfig",
    "SecurityConfig",
    "SignatureConfig",
    "StackReference",
    "StackLock",
    "StackLockEntry",
    "RegistryIndex",
    "RegistryIndexEntry",
    # Exceptions
    "StackError",
    "StackNotFoundError",
    "StackValidationError",
    "StackSourceError",
    "StackLockError",
    "PolicyViolationError",
    "StackSecurityError",
    # Registry
    "EnterpriseStackRegistry",
    # Policy
    "PolicyEngine",
    "PolicyResult",
    "PolicyContext",
    "PolicyRule",
    "StackExistsRule",
    "StackLockedRule",
    "UserPermissionRule",
    "ProjectPermissionRule",
    "BackendAllowedRule",
    "BaseImageApprovedRule",
    "PackageAllowListRule",
    "PackageDenyListRule",
    "ExternalNetworkRule",
    "MaxRuntimeRule",
    "CostLimitRule",
    "SignedStackRule",
    # Lock
    "StackLockManager",
    "LockVerificationResult",
    # Project Config
    "ProjectConfig",
    "EnvironmentConfig",
    "DefaultsConfig",
    "ProjectInfo",
    "RegistryConfig",
    "load_project_config",
    "resolve_environment",
    # Execution
    "ExecutionContext",
    "BackendAdapter",
    "RunHandle",
    "RunStatus",
    # Audit
    "AuditRecord",
    "AuditStore",
    # Resolver
    "StackResolver",
    # Sources
    "StackSource",
    "parse_source_uri",
    # Secrets
    "SecretsProvider",
    "EnvSecretsProvider",
    "LocalSecretsProvider",
    "VaultSecretsProvider",
    "AzureKeyVaultProvider",
    "AWSSecretsManagerProvider",
    "GCPSecretManagerProvider",
    "get_secrets_provider",
]
