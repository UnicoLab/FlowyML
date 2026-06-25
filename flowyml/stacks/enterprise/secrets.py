"""Enterprise Secrets Management — Multi-Provider Secret Resolution.

Provides a unified interface for retrieving secrets from enterprise
key management systems. Configured via the ``spec.secrets`` section
of an enterprise StackDefinition.

Supported providers:
    - ``env``               — Environment variables (built-in, zero deps)
    - ``local``             — Local .env files (built-in, zero deps)
    - ``hashicorp_vault``   — HashiCorp Vault via ``hvac``
    - ``azure_key_vault``   — Azure Key Vault via ``azure-keyvault-secrets``
    - ``aws_secrets_manager`` — AWS Secrets Manager via ``boto3``
    - ``gcp_secret_manager``  — GCP Secret Manager via ``google-cloud-secret-manager``

Usage::

    from flowyml.stacks.enterprise.secrets import get_secrets_provider

    # From stack config
    provider = get_secrets_provider("hashicorp_vault", scope="secret/data/ml/production")
    api_key = provider.get_secret("OPENAI_API_KEY")

    # Bulk read
    all_secrets = provider.list_secrets()
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

logger = logging.getLogger(__name__)

__all__ = [
    "SecretsProvider",
    "EnvSecretsProvider",
    "LocalSecretsProvider",
    "VaultSecretsProvider",
    "AzureKeyVaultProvider",
    "AWSSecretsManagerProvider",
    "GCPSecretManagerProvider",
    "get_secrets_provider",
]


# ---------------------------------------------------------------------------
# Optional SDK imports
# ---------------------------------------------------------------------------

try:
    import hvac  # type: ignore[import-untyped]

    _HVAC_AVAILABLE = True
except ImportError:
    _HVAC_AVAILABLE = False
    hvac = None  # type: ignore[assignment]

try:
    from azure.identity import DefaultAzureCredential  # type: ignore[import-untyped]
    from azure.keyvault.secrets import SecretClient  # type: ignore[import-untyped]

    _AZURE_KV_AVAILABLE = True
except ImportError:
    _AZURE_KV_AVAILABLE = False
    DefaultAzureCredential = None  # type: ignore[assignment,misc]
    SecretClient = None  # type: ignore[assignment,misc]

try:
    import boto3  # type: ignore[import-untyped]

    _BOTO3_AVAILABLE = True
except ImportError:
    _BOTO3_AVAILABLE = False
    boto3 = None  # type: ignore[assignment]

try:
    from google.cloud import secretmanager  # type: ignore[import-untyped]

    _GCP_SM_AVAILABLE = True
except ImportError:
    _GCP_SM_AVAILABLE = False
    secretmanager = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# SDK requirement helpers
# ---------------------------------------------------------------------------


def _require_hvac() -> None:
    """Raise ``ImportError`` with an actionable message if ``hvac`` is missing."""
    if not _HVAC_AVAILABLE:
        raise ImportError(
            "HashiCorp Vault SDK (hvac) is required. Install with: pip install hvac",
        )


def _require_azure_keyvault() -> None:
    """Raise ``ImportError`` if Azure Key Vault SDK is missing."""
    if not _AZURE_KV_AVAILABLE:
        raise ImportError(
            "Azure Key Vault SDK is required for AzureKeyVaultProvider but is "
            "not installed.\n\n"
            "Install it with:\n"
            "  pip install azure-keyvault-secrets azure-identity\n\n"
            "Or install the FlowyML Azure extra:\n"
            "  pip install flowyml[azure]",
        )


def _require_boto3() -> None:
    """Raise ``ImportError`` if ``boto3`` is missing."""
    if not _BOTO3_AVAILABLE:
        raise ImportError(
            "AWS SDK (boto3) is required for AWSSecretsManagerProvider but is "
            "not installed.\n\n"
            "Install it with:\n"
            "  pip install boto3\n\n"
            "Or install the FlowyML AWS extra:\n"
            "  pip install flowyml[aws]",
        )


def _require_gcp_secret_manager() -> None:
    """Raise ``ImportError`` if GCP Secret Manager SDK is missing."""
    if not _GCP_SM_AVAILABLE:
        raise ImportError(
            "GCP Secret Manager SDK is required for GCPSecretManagerProvider "
            "but is not installed.\n\n"
            "Install it with:\n"
            "  pip install google-cloud-secret-manager\n\n"
            "Or install the FlowyML GCP extra:\n"
            "  pip install flowyml[gcp]",
        )


# ---------------------------------------------------------------------------
# SecretsProvider protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class SecretsProvider(Protocol):
    """Protocol that every secrets provider must implement.

    Providers resolve secret values from external key management systems
    such as HashiCorp Vault, Azure Key Vault, AWS Secrets Manager, or
    GCP Secret Manager.
    """

    @property
    def provider_name(self) -> str:
        """Canonical name of this provider (e.g. ``env``, ``hashicorp_vault``)."""
        ...

    def get_secret(self, key: str) -> str | None:
        """Retrieve a single secret by key.

        Args:
            key: The secret name / key to look up.

        Returns:
            The secret value as a string, or ``None`` if not found.
        """
        ...

    def get_secrets(self, keys: list[str]) -> dict[str, str | None]:
        """Retrieve multiple secrets in a single call.

        Args:
            keys: List of secret names to look up.

        Returns:
            Dictionary mapping each key to its value (or ``None``).
        """
        ...

    def list_secrets(self) -> list[str]:
        """List available secret keys.

        Returns:
            A list of secret key names accessible through this provider.
        """
        ...

    def set_secret(self, key: str, value: str) -> None:
        """Set (create or update) a secret.

        Args:
            key: The secret name / key.
            value: The secret value.

        Raises:
            NotImplementedError: If the provider does not support writes.
        """
        ...


# ---------------------------------------------------------------------------
# EnvSecretsProvider
# ---------------------------------------------------------------------------


class EnvSecretsProvider:
    """Secrets provider backed by OS environment variables.

    A simple, zero-dependency provider that reads secrets directly from
    ``os.environ``.  The optional *scope* parameter acts as a prefix
    filter — e.g. ``scope="ML_"`` restricts operations to environment
    variables whose names start with ``ML_``.

    Args:
        scope: Optional prefix filter for environment variable names.
    """

    def __init__(self, scope: str | None = None) -> None:
        self._scope = scope or ""

    @property
    def provider_name(self) -> str:
        """Canonical provider name."""
        return "env"

    def get_secret(self, key: str) -> str | None:
        """Get an environment variable value.

        Args:
            key: Environment variable name.

        Returns:
            The value, or ``None`` if not set.
        """
        full_key = f"{self._scope}{key}" if self._scope else key
        value = os.environ.get(full_key)
        logger.debug("EnvSecretsProvider.get_secret(%s) → %s", full_key, "found" if value else "missing")
        return value

    def get_secrets(self, keys: list[str]) -> dict[str, str | None]:
        """Batch-get environment variables.

        Args:
            keys: List of environment variable names.

        Returns:
            Dictionary mapping each key to its value (or ``None``).
        """
        return {key: self.get_secret(key) for key in keys}

    def list_secrets(self) -> list[str]:
        """List environment variable names matching the scope prefix.

        Returns:
            Sorted list of matching environment variable names. If a
            scope prefix is set, the prefix is stripped from the
            returned names.
        """
        if self._scope:
            return sorted(k[len(self._scope) :] for k in os.environ if k.startswith(self._scope))
        return sorted(os.environ.keys())

    def set_secret(self, key: str, value: str) -> None:
        """Set an environment variable in the current process.

        Args:
            key: Environment variable name.
            value: Environment variable value.
        """
        full_key = f"{self._scope}{key}" if self._scope else key
        os.environ[full_key] = value
        logger.info("EnvSecretsProvider: set %s", full_key)

    def __repr__(self) -> str:
        return f"EnvSecretsProvider(scope={self._scope!r})"


# ---------------------------------------------------------------------------
# LocalSecretsProvider
# ---------------------------------------------------------------------------


class LocalSecretsProvider:
    """Secrets provider backed by local ``.env`` files.

    Parses a simple ``KEY=VALUE`` format (one per line).  Blank lines and
    lines starting with ``#`` are ignored.  Values may optionally be
    surrounded by single or double quotes, which are stripped.

    No external dependency on ``python-dotenv`` — the parser is built-in.

    Args:
        scope: Path to the ``.env`` file.  Defaults to ``.env`` in the
            current working directory.
    """

    def __init__(self, scope: str | None = None) -> None:
        self._path = Path(scope) if scope else Path(".env")
        self._secrets: dict[str, str] | None = None

    @property
    def provider_name(self) -> str:
        """Canonical provider name."""
        return "local"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_secret(self, key: str) -> str | None:
        """Get a secret from the .env file.

        Args:
            key: The secret key to look up.

        Returns:
            The value, or ``None`` if not found.
        """
        secrets = self._ensure_loaded()
        value = secrets.get(key)
        logger.debug("LocalSecretsProvider.get_secret(%s) → %s", key, "found" if value else "missing")
        return value

    def get_secrets(self, keys: list[str]) -> dict[str, str | None]:
        """Batch-get secrets from the .env file.

        Args:
            keys: List of secret keys to look up.

        Returns:
            Dictionary mapping each key to its value (or ``None``).
        """
        return {key: self.get_secret(key) for key in keys}

    def list_secrets(self) -> list[str]:
        """List all secret keys in the .env file.

        Returns:
            Sorted list of secret key names.
        """
        secrets = self._ensure_loaded()
        return sorted(secrets.keys())

    def set_secret(self, key: str, value: str) -> None:
        """Set a secret — appends (or updates) the key in the .env file.

        Args:
            key: The secret key.
            value: The secret value.
        """
        secrets = self._ensure_loaded()
        secrets[key] = value
        self._write_env(secrets)
        logger.info("LocalSecretsProvider: set %s in %s", key, self._path)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_loaded(self) -> dict[str, str]:
        """Parse and cache the .env file contents.

        Returns:
            Dictionary of parsed KEY=VALUE pairs.
        """
        if self._secrets is not None:
            return self._secrets

        self._secrets = {}
        if not self._path.exists():
            logger.debug("Env file '%s' does not exist; returning empty secrets.", self._path)
            return self._secrets

        logger.debug("Loading secrets from '%s'.", self._path)
        content = self._path.read_text(encoding="utf-8")
        for lineno, raw_line in enumerate(content.splitlines(), start=1):
            line = raw_line.strip()
            # Skip blank lines and comments
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                logger.warning(
                    "Skipping malformed line %d in %s: no '=' found.",
                    lineno,
                    self._path,
                )
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            # Strip surrounding quotes
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
                value = value[1:-1]
            self._secrets[key] = value

        logger.info("Loaded %d secrets from '%s'.", len(self._secrets), self._path)
        return self._secrets

    def _write_env(self, secrets: dict[str, str]) -> None:
        """Write all secrets back to the .env file.

        Args:
            secrets: Complete set of secrets to persist.
        """
        self._path.parent.mkdir(parents=True, exist_ok=True)
        lines = [f"{k}={v}" for k, v in sorted(secrets.items())]
        self._path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def __repr__(self) -> str:
        return f"LocalSecretsProvider(path={str(self._path)!r})"


# ---------------------------------------------------------------------------
# VaultSecretsProvider
# ---------------------------------------------------------------------------


class VaultSecretsProvider:
    """Secrets provider backed by HashiCorp Vault.

    Connects to Vault using one of two authentication methods:

    1. **Token auth** — reads ``VAULT_TOKEN`` from the environment.
    2. **AppRole auth** — reads ``VAULT_ROLE_ID`` and ``VAULT_SECRET_ID``
       from the environment.

    The Vault server address is taken from the ``VAULT_ADDR`` environment
    variable (defaults to ``http://127.0.0.1:8200``).

    The ``hvac`` SDK is an *optional* dependency — a clear error message
    is raised if it is missing.

    Args:
        scope: Vault path to read secrets from
            (e.g. ``secret/data/ml/production``).
        vault_addr: Override for the Vault server address.
        vault_token: Override for the Vault token (prefer env var).
    """

    def __init__(
        self,
        scope: str | None = None,
        vault_addr: str | None = None,
        vault_token: str | None = None,
    ) -> None:
        self._scope = scope or "secret/data"
        self._vault_addr = vault_addr or os.environ.get("VAULT_ADDR", "http://127.0.0.1:8200")
        self._vault_token = vault_token
        self._client: Any = None

    @property
    def provider_name(self) -> str:
        """Canonical provider name."""
        return "hashicorp_vault"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_secret(self, key: str) -> str | None:
        """Get a single secret from Vault.

        Reads the secret path defined by *scope* and returns the value
        for *key* from the response data.

        Args:
            key: The secret key to look up within the scope path.

        Returns:
            The secret value, or ``None`` if not found.
        """
        client = self._get_client()
        try:
            response = client.secrets.kv.v2.read_secret_version(
                path=self._scope,
                raise_on_deleted_version=True,
            )
            data: dict[str, Any] = response.get("data", {}).get("data", {})
            value = data.get(key)
            logger.debug(
                "VaultSecretsProvider.get_secret(%s) at path '%s' → %s",
                key,
                self._scope,
                "found" if value else "missing",
            )
            return str(value) if value is not None else None
        except Exception:
            logger.exception("Failed to read secret '%s' from Vault path '%s'.", key, self._scope)
            return None

    def get_secrets(self, keys: list[str]) -> dict[str, str | None]:
        """Batch-get secrets from Vault.

        Reads the scope path once and extracts the requested keys.

        Args:
            keys: List of secret keys to look up.

        Returns:
            Dictionary mapping each key to its value (or ``None``).
        """
        client = self._get_client()
        try:
            response = client.secrets.kv.v2.read_secret_version(
                path=self._scope,
                raise_on_deleted_version=True,
            )
            data: dict[str, Any] = response.get("data", {}).get("data", {})
            result: dict[str, str | None] = {}
            for key in keys:
                val = data.get(key)
                result[key] = str(val) if val is not None else None
            return result
        except Exception:
            logger.exception("Failed to read secrets from Vault path '%s'.", self._scope)
            return dict.fromkeys(keys)

    def list_secrets(self) -> list[str]:
        """List secret keys available at the scope path.

        Returns:
            Sorted list of secret key names.
        """
        client = self._get_client()
        try:
            response = client.secrets.kv.v2.read_secret_version(
                path=self._scope,
                raise_on_deleted_version=True,
            )
            data: dict[str, Any] = response.get("data", {}).get("data", {})
            return sorted(data.keys())
        except Exception:
            logger.exception("Failed to list secrets from Vault path '%s'.", self._scope)
            return []

    def set_secret(self, key: str, value: str) -> None:
        """Create or update a secret in Vault.

        Reads the current data at the scope path, merges the new key,
        and writes the updated data back.

        Args:
            key: The secret key.
            value: The secret value.
        """
        client = self._get_client()
        # Read existing data to merge
        try:
            response = client.secrets.kv.v2.read_secret_version(
                path=self._scope,
                raise_on_deleted_version=True,
            )
            existing: dict[str, Any] = response.get("data", {}).get("data", {})
        except Exception:
            existing = {}

        existing[key] = value
        client.secrets.kv.v2.create_or_update_secret(
            path=self._scope,
            secret=existing,
        )
        logger.info("VaultSecretsProvider: set '%s' at path '%s'.", key, self._scope)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_client(self) -> Any:
        """Lazy-initialise and return the ``hvac.Client``.

        Authenticates via token (``VAULT_TOKEN``) or AppRole
        (``VAULT_ROLE_ID`` + ``VAULT_SECRET_ID``).

        Returns:
            An authenticated ``hvac.Client`` instance.

        Raises:
            ImportError: If ``hvac`` is not installed.
            RuntimeError: If no authentication credentials are found.
        """
        _require_hvac()

        if self._client is not None:
            return self._client

        token = self._vault_token or os.environ.get("VAULT_TOKEN")

        if token:
            self._client = hvac.Client(url=self._vault_addr, token=token)
            logger.info("Vault client initialised with token auth (addr=%s).", self._vault_addr)
        else:
            role_id = os.environ.get("VAULT_ROLE_ID")
            secret_id = os.environ.get("VAULT_SECRET_ID")
            if role_id and secret_id:
                client = hvac.Client(url=self._vault_addr)
                client.auth.approle.login(role_id=role_id, secret_id=secret_id)
                self._client = client
                logger.info("Vault client initialised with AppRole auth (addr=%s).", self._vault_addr)
            else:
                raise RuntimeError(
                    "No Vault authentication credentials found. Set either "
                    "VAULT_TOKEN or both VAULT_ROLE_ID and VAULT_SECRET_ID "
                    "environment variables.",
                )

        return self._client

    def __repr__(self) -> str:
        return f"VaultSecretsProvider(scope={self._scope!r}, addr={self._vault_addr!r})"


# ---------------------------------------------------------------------------
# AzureKeyVaultProvider
# ---------------------------------------------------------------------------


class AzureKeyVaultProvider:
    """Secrets provider backed by Azure Key Vault.

    Uses ``azure.keyvault.secrets.SecretClient`` with
    ``azure.identity.DefaultAzureCredential`` for authentication — no
    credentials are hard-coded.

    The Azure Key Vault SDKs are *optional* dependencies — a clear
    error message is raised if they are missing.

    Args:
        scope: The Key Vault name (e.g. ``ml-keyvault-prod``).  The
            vault URL is constructed as
            ``https://{scope}.vault.azure.net/``.
    """

    def __init__(self, scope: str | None = None) -> None:
        if not scope:
            raise ValueError(
                "AzureKeyVaultProvider requires a scope (the Key Vault name), e.g. scope='ml-keyvault-prod'.",
            )
        self._vault_name = scope
        self._vault_url = f"https://{scope}.vault.azure.net/"
        self._client: Any = None

    @property
    def provider_name(self) -> str:
        """Canonical provider name."""
        return "azure_key_vault"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_secret(self, key: str) -> str | None:
        """Get a secret from Azure Key Vault.

        Args:
            key: The secret name.

        Returns:
            The secret value, or ``None`` if not found.
        """
        client = self._get_client()
        try:
            secret = client.get_secret(key)
            logger.debug("AzureKeyVaultProvider.get_secret(%s) → found", key)
            return secret.value
        except Exception:
            logger.exception("Failed to get secret '%s' from vault '%s'.", key, self._vault_name)
            return None

    def get_secrets(self, keys: list[str]) -> dict[str, str | None]:
        """Batch-get secrets from Azure Key Vault.

        Args:
            keys: List of secret names.

        Returns:
            Dictionary mapping each key to its value (or ``None``).
        """
        return {key: self.get_secret(key) for key in keys}

    def list_secrets(self) -> list[str]:
        """List all secret names in the Key Vault.

        Returns:
            Sorted list of secret names.
        """
        client = self._get_client()
        try:
            properties = client.list_properties_of_secrets()
            names = sorted(prop.name for prop in properties if prop.name)
            logger.debug("AzureKeyVaultProvider.list_secrets() → %d secrets", len(names))
            return names
        except Exception:
            logger.exception("Failed to list secrets from vault '%s'.", self._vault_name)
            return []

    def set_secret(self, key: str, value: str) -> None:
        """Set a secret in Azure Key Vault.

        Args:
            key: The secret name.
            value: The secret value.
        """
        client = self._get_client()
        client.set_secret(key, value)
        logger.info("AzureKeyVaultProvider: set '%s' in vault '%s'.", key, self._vault_name)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_client(self) -> Any:
        """Lazy-initialise and return the ``SecretClient``.

        Returns:
            An authenticated ``SecretClient`` instance.

        Raises:
            ImportError: If the Azure Key Vault SDK is not installed.
        """
        _require_azure_keyvault()

        if self._client is None:
            credential = DefaultAzureCredential()
            self._client = SecretClient(vault_url=self._vault_url, credential=credential)
            logger.info(
                "Azure Key Vault SecretClient initialised (vault=%s).",
                self._vault_url,
            )
        return self._client

    def __repr__(self) -> str:
        return f"AzureKeyVaultProvider(vault={self._vault_name!r})"


# ---------------------------------------------------------------------------
# AWSSecretsManagerProvider
# ---------------------------------------------------------------------------


class AWSSecretsManagerProvider:
    """Secrets provider backed by AWS Secrets Manager.

    Uses ``boto3.client('secretsmanager')`` with the default credential
    chain (environment variables, shared credentials file, IAM role,
    etc.).  No credentials are hard-coded.

    The ``boto3`` SDK is an *optional* dependency — a clear error message
    is raised if it is missing.

    AWS Secrets Manager stores each secret as a name→value pair.  When
    the stored value is a JSON blob, individual keys within the JSON are
    exposed transparently.

    Args:
        scope: Optional prefix filter for secret names.
        region_name: AWS region override.
    """

    def __init__(
        self,
        scope: str | None = None,
        region_name: str | None = None,
    ) -> None:
        self._scope = scope or ""
        self._region_name = region_name
        self._client: Any = None

    @property
    def provider_name(self) -> str:
        """Canonical provider name."""
        return "aws_secrets_manager"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_secret(self, key: str) -> str | None:
        """Get a secret from AWS Secrets Manager.

        If the secret value is a JSON string, the method first tries to
        parse it and return the value for *key* within the JSON.  If that
        fails (or there is no matching JSON key), the raw string value
        is returned.

        Args:
            key: The secret name (optionally prefixed by scope).

        Returns:
            The secret value, or ``None`` if not found.
        """
        client = self._get_client()
        full_key = f"{self._scope}{key}" if self._scope else key
        try:
            response = client.get_secret_value(SecretId=full_key)
            raw = response.get("SecretString")
            if raw is None:
                logger.debug("AWSSecretsManagerProvider: '%s' has no SecretString.", full_key)
                return None
            # Try parsing as JSON — return value for key inside blob
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict) and key in parsed:
                    logger.debug("AWSSecretsManagerProvider.get_secret(%s) → found (JSON key)", key)
                    return str(parsed[key])
            except (json.JSONDecodeError, TypeError):
                pass
            logger.debug("AWSSecretsManagerProvider.get_secret(%s) → found (raw)", full_key)
            return raw
        except Exception:
            logger.debug("AWSSecretsManagerProvider: secret '%s' not found.", full_key)
            return None

    def get_secrets(self, keys: list[str]) -> dict[str, str | None]:
        """Batch-get secrets from AWS Secrets Manager.

        Args:
            keys: List of secret names.

        Returns:
            Dictionary mapping each key to its value (or ``None``).
        """
        return {key: self.get_secret(key) for key in keys}

    def list_secrets(self) -> list[str]:
        """List secret names, optionally filtered by scope prefix.

        Returns:
            Sorted list of secret names.  If a scope prefix is set,
            only secrets whose names start with the prefix are included
            and the prefix is stripped from the returned names.
        """
        client = self._get_client()
        names: list[str] = []
        try:
            paginator = client.get_paginator("list_secrets")
            for page in paginator.paginate():
                for entry in page.get("SecretList", []):
                    name = entry.get("Name", "")
                    if self._scope and name.startswith(self._scope):
                        names.append(name[len(self._scope) :])
                    elif not self._scope:
                        names.append(name)
            logger.debug("AWSSecretsManagerProvider.list_secrets() → %d secrets", len(names))
        except Exception:
            logger.exception("Failed to list secrets from AWS Secrets Manager.")
        return sorted(names)

    def set_secret(self, key: str, value: str) -> None:
        """Create or update a secret in AWS Secrets Manager.

        Uses ``put_secret_value`` to update existing secrets or
        ``create_secret`` for new ones.

        Args:
            key: The secret name.
            value: The secret value.
        """
        client = self._get_client()
        full_key = f"{self._scope}{key}" if self._scope else key
        try:
            client.put_secret_value(SecretId=full_key, SecretString=value)
        except client.exceptions.ResourceNotFoundException:
            client.create_secret(Name=full_key, SecretString=value)
        logger.info("AWSSecretsManagerProvider: set '%s'.", full_key)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_client(self) -> Any:
        """Lazy-initialise and return the ``boto3`` Secrets Manager client.

        Returns:
            A ``boto3`` Secrets Manager client instance.

        Raises:
            ImportError: If ``boto3`` is not installed.
        """
        _require_boto3()

        if self._client is None:
            kwargs: dict[str, Any] = {}
            if self._region_name:
                kwargs["region_name"] = self._region_name
            self._client = boto3.client("secretsmanager", **kwargs)
            logger.info(
                "AWS Secrets Manager client initialised (region=%s).",
                self._region_name or "default",
            )
        return self._client

    def __repr__(self) -> str:
        return f"AWSSecretsManagerProvider(scope={self._scope!r}, region={self._region_name!r})"


# ---------------------------------------------------------------------------
# GCPSecretManagerProvider
# ---------------------------------------------------------------------------


class GCPSecretManagerProvider:
    """Secrets provider backed by GCP Secret Manager.

    Uses ``google.cloud.secretmanager.SecretManagerServiceClient`` with
    Application Default Credentials.  No credentials are hard-coded.

    The ``google-cloud-secret-manager`` SDK is an *optional* dependency
    — a clear error message is raised if it is missing.

    Secret resource names follow the pattern::

        projects / {project_id} / secrets / {secret_name} / versions / latest

    Args:
        scope: GCP project ID.
    """

    def __init__(self, scope: str | None = None) -> None:
        if not scope:
            raise ValueError(
                "GCPSecretManagerProvider requires a scope (the GCP project ID), e.g. scope='my-gcp-project'.",
            )
        self._project_id = scope
        self._client: Any = None

    @property
    def provider_name(self) -> str:
        """Canonical provider name."""
        return "gcp_secret_manager"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_secret(self, key: str) -> str | None:
        """Get a secret from GCP Secret Manager.

        Accesses the ``latest`` version of the secret.

        Args:
            key: The secret name.

        Returns:
            The secret value as a UTF-8 string, or ``None`` if not found.
        """
        client = self._get_client()
        name = f"projects/{self._project_id}/secrets/{key}/versions/latest"
        try:
            response = client.access_secret_version(request={"name": name})
            value = response.payload.data.decode("utf-8")
            logger.debug("GCPSecretManagerProvider.get_secret(%s) → found", key)
            return value
        except Exception:
            logger.debug("GCPSecretManagerProvider: secret '%s' not found.", key)
            return None

    def get_secrets(self, keys: list[str]) -> dict[str, str | None]:
        """Batch-get secrets from GCP Secret Manager.

        Args:
            keys: List of secret names.

        Returns:
            Dictionary mapping each key to its value (or ``None``).
        """
        return {key: self.get_secret(key) for key in keys}

    def list_secrets(self) -> list[str]:
        """List all secret names in the GCP project.

        Returns:
            Sorted list of secret names (short names, not full
            resource paths).
        """
        client = self._get_client()
        parent = f"projects/{self._project_id}"
        names: list[str] = []
        try:
            for secret in client.list_secrets(request={"parent": parent}):
                # secret.name is "projects/{project}/secrets/{name}"
                short_name = secret.name.rsplit("/", 1)[-1]
                names.append(short_name)
            logger.debug("GCPSecretManagerProvider.list_secrets() → %d secrets", len(names))
        except Exception:
            logger.exception(
                "Failed to list secrets from GCP project '%s'.",
                self._project_id,
            )
        return sorted(names)

    def set_secret(self, key: str, value: str) -> None:
        """Create or update a secret in GCP Secret Manager.

        If the secret does not exist, it is created first.  Then a new
        version with the given *value* is added.

        Args:
            key: The secret name.
            value: The secret value.
        """
        client = self._get_client()
        parent = f"projects/{self._project_id}"
        secret_path = f"{parent}/secrets/{key}"

        # Ensure the secret resource exists
        try:
            client.get_secret(request={"name": secret_path})
        except Exception:
            client.create_secret(
                request={
                    "parent": parent,
                    "secret_id": key,
                    "secret": {"replication": {"automatic": {}}},
                },
            )
            logger.info("GCPSecretManagerProvider: created secret '%s'.", key)

        # Add a new version
        client.add_secret_version(
            request={
                "parent": secret_path,
                "payload": {"data": value.encode("utf-8")},
            },
        )
        logger.info("GCPSecretManagerProvider: set '%s' in project '%s'.", key, self._project_id)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_client(self) -> Any:
        """Lazy-initialise and return the ``SecretManagerServiceClient``.

        Returns:
            A ``SecretManagerServiceClient`` instance.

        Raises:
            ImportError: If the GCP Secret Manager SDK is not installed.
        """
        _require_gcp_secret_manager()

        if self._client is None:
            self._client = secretmanager.SecretManagerServiceClient()
            logger.info(
                "GCP Secret Manager client initialised (project=%s).",
                self._project_id,
            )
        return self._client

    def __repr__(self) -> str:
        return f"GCPSecretManagerProvider(project={self._project_id!r})"


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

_PROVIDER_MAP: dict[str, type] = {
    "env": EnvSecretsProvider,
    "local": LocalSecretsProvider,
    "hashicorp_vault": VaultSecretsProvider,
    "azure_key_vault": AzureKeyVaultProvider,
    "aws_secrets_manager": AWSSecretsManagerProvider,
    "gcp_secret_manager": GCPSecretManagerProvider,
}


def get_secrets_provider(
    provider_name: str,
    scope: str | None = None,
    **kwargs: Any,
) -> SecretsProvider:
    """Factory function to obtain a ``SecretsProvider`` by name.

    Instantiates the appropriate provider class and passes *scope*
    plus any extra keyword arguments to its constructor.

    Args:
        provider_name: Name of the provider (e.g. ``env``,
            ``hashicorp_vault``, ``azure_key_vault``).
        scope: Provider-specific scope.  See each provider class for
            the semantics of this parameter.
        **kwargs: Additional keyword arguments forwarded to the
            provider constructor.

    Returns:
        An instantiated ``SecretsProvider``.

    Raises:
        ValueError: If the provider name is not recognised.

    Example::

        provider = get_secrets_provider("env", scope="ML_")
        provider.get_secret("API_KEY")  # reads ML_API_KEY from env
    """
    provider_cls = _PROVIDER_MAP.get(provider_name)
    if provider_cls is None:
        available = ", ".join(sorted(_PROVIDER_MAP.keys()))
        raise ValueError(
            f"Unknown secrets provider '{provider_name}'. Available providers: {available}.",
        )

    logger.info("Creating secrets provider '%s' (scope=%s).", provider_name, scope)
    return provider_cls(scope=scope, **kwargs)  # type: ignore[return-value]
