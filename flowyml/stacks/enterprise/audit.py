"""Audit metadata for enterprise pipeline runs.

Provides ``AuditRecord`` (a Pydantic model) and ``AuditStore`` (a
filesystem-backed persistence layer) for recording, querying, and
exporting audit trails of every pipeline execution.

Each run is persisted as a JSON file under ``<audit_dir>/<run_id>.json``,
making it trivial to ship audit data to external systems (ELK, Splunk,
Azure Monitor, etc.).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from collections.abc import Callable

import yaml
from pydantic import BaseModel, ConfigDict, Field

from flowyml.stacks.enterprise.execution import ExecutionContext

logger = logging.getLogger(__name__)

__all__ = [
    "AuditRecord",
    "AuditStore",
]


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


class AuditRecord(BaseModel):
    """Immutable audit record for a single pipeline run.

    Captures the full provenance chain — stack identity, digest, source
    registry, policy status, user, timestamps, and produced artifacts.

    Attributes:
        run_id: Unique run identifier.
        project: Project name.
        pipeline: Pipeline name.
        environment: Deployment environment.
        stack_name: Resolved stack name.
        stack_version: Resolved stack version.
        stack_digest: SHA-256 digest of the stack definition.
        source_registry: URI of the source registry.
        source_commit: Git commit, if applicable.
        user: User or service account identity.
        started_at: ISO 8601 timestamp when the run started.
        finished_at: ISO 8601 timestamp when the run finished.
        status: Run status string (``pending``, ``succeeded``, …).
        artifacts: List of produced artifact descriptors.
        policy_status: Overall policy evaluation outcome.
        policy_results: Per-rule policy results.
    """

    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(..., description="Unique run identifier.")
    project: str = Field(..., description="Project name.")
    pipeline: str = Field(..., description="Pipeline name.")
    environment: str = Field(default="local", description="Deployment environment.")
    stack_name: str = Field(..., description="Resolved stack name.")
    stack_version: str = Field(..., description="Resolved stack version.")
    stack_digest: str = Field(..., description="SHA-256 digest of the stack.")
    source_registry: str | None = Field(
        default=None,
        description="URI of the registry source.",
    )
    source_commit: str | None = Field(
        default=None,
        description="Git commit hash, if applicable.",
    )
    user: str | None = Field(default=None, description="User identity.")
    started_at: str = Field(..., description="ISO 8601 start timestamp.")
    finished_at: str | None = Field(
        default=None,
        description="ISO 8601 finish timestamp.",
    )
    status: str = Field(default="pending", description="Run status.")
    artifacts: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Produced artifact descriptors.",
    )
    policy_status: str = Field(
        default="not_checked",
        description="Overall policy evaluation outcome.",
    )
    policy_results: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Per-rule policy check results.",
    )


# ---------------------------------------------------------------------------
# Persistence layer
# ---------------------------------------------------------------------------


class AuditStore:
    """Filesystem-backed store for ``AuditRecord`` objects.

    Records are persisted as individual JSON files under
    ``<audit_dir>/<run_id>.json``.  An optional ``on_audit`` hook can be
    provided to forward records to external systems in real time.

    Args:
        audit_dir: Directory for audit JSON files.
    """

    def __init__(self, audit_dir: str = ".flowyml/audit") -> None:
        self._audit_dir = Path(audit_dir)
        self.on_audit: Callable[[AuditRecord], None] | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record(
        self,
        context: ExecutionContext,
        status: str = "pending",
    ) -> AuditRecord:
        """Create and persist an ``AuditRecord`` from an ``ExecutionContext``.

        Args:
            context: The execution context for the run.
            status: Initial run status.

        Returns:
            The persisted ``AuditRecord``.
        """
        policy_status = "not_checked"
        policy_results_dicts: list[dict[str, Any]] = []

        if context.policy_results:
            policy_results_dicts = [pr.model_dump(mode="json") for pr in context.policy_results]
            failed = any(pr.get("status") == "failed" for pr in policy_results_dicts)
            policy_status = "failed" if failed else "passed"

        audit = AuditRecord(
            run_id=context.run_id,
            project=context.project_name,
            pipeline=context.pipeline_name,
            environment=context.environment,
            stack_name=context.stack.name,
            stack_version=context.stack.version,
            stack_digest=context.stack_digest,
            user=context.user,
            started_at=datetime.now(timezone.utc).isoformat(),
            status=status,
            policy_status=policy_status,
            policy_results=policy_results_dicts,
        )

        self._persist(audit)

        if self.on_audit is not None:
            try:
                self.on_audit(audit)
            except Exception as exc:
                logger.warning("on_audit hook raised: %s", exc)

        logger.info("Audit record created for run '%s'.", audit.run_id)
        return audit

    def update(
        self,
        run_id: str,
        status: str,
        finished_at: str | None = None,
        artifacts: list[dict[str, Any]] | None = None,
    ) -> None:
        """Update an existing audit record.

        Args:
            run_id: Run identifier.
            status: New status value.
            finished_at: Optional ISO 8601 finish timestamp.
            artifacts: Optional list of artifact descriptors to append.

        Raises:
            FileNotFoundError: If the audit record does not exist.
        """
        audit = self.get(run_id)
        if audit is None:
            raise FileNotFoundError(
                f"Audit record not found for run_id='{run_id}'.",
            )

        audit.status = status

        if finished_at is not None:
            audit.finished_at = finished_at
        elif status in ("succeeded", "failed", "cancelled"):
            audit.finished_at = datetime.now(timezone.utc).isoformat()

        if artifacts is not None:
            audit.artifacts.extend(artifacts)

        self._persist(audit)
        logger.debug("Audit record updated for run '%s' → %s.", run_id, status)

    def get(self, run_id: str) -> AuditRecord | None:
        """Retrieve an audit record by run ID.

        Args:
            run_id: The run identifier.

        Returns:
            ``AuditRecord`` or ``None`` if not found.
        """
        path = self._record_path(run_id)
        if not path.exists():
            return None

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return AuditRecord.model_validate(data)
        except Exception as exc:
            logger.warning(
                "Failed to load audit record '%s': %s",
                run_id,
                exc,
            )
            return None

    def list_records(self, limit: int = 50) -> list[AuditRecord]:
        """List recent audit records, sorted by start time descending.

        Args:
            limit: Maximum number of records to return.

        Returns:
            List of ``AuditRecord`` objects.
        """
        if not self._audit_dir.exists():
            return []

        records: list[AuditRecord] = []
        json_files = sorted(
            self._audit_dir.glob("*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        for path in json_files[:limit]:
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                records.append(AuditRecord.model_validate(data))
            except Exception as exc:
                logger.warning("Skipping corrupt audit file '%s': %s", path, exc)

        return records

    def export(self, run_id: str, format: str = "json") -> str:
        """Export an audit record as a serialised string.

        Args:
            run_id: The run identifier.
            format: Output format — ``json`` or ``yaml``.

        Returns:
            Serialised audit record string.

        Raises:
            FileNotFoundError: If the record does not exist.
            ValueError: If the format is unsupported.
        """
        audit = self.get(run_id)
        if audit is None:
            raise FileNotFoundError(
                f"Audit record not found for run_id='{run_id}'.",
            )

        data = audit.model_dump(mode="json", exclude_none=True)

        if format == "json":
            return json.dumps(data, indent=2, ensure_ascii=False)

        if format == "yaml":
            return yaml.safe_dump(
                data,
                sort_keys=False,
                default_flow_style=False,
                allow_unicode=True,
            )

        raise ValueError(
            f"Unsupported export format '{format}'. Use 'json' or 'yaml'.",
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _record_path(self, run_id: str) -> Path:
        """Return the filesystem path for a run's audit file.

        Args:
            run_id: The run identifier.

        Returns:
            ``Path`` object.
        """
        return self._audit_dir / f"{run_id}.json"

    def _persist(self, audit: AuditRecord) -> None:
        """Write an audit record to disk as JSON.

        Args:
            audit: The record to persist.
        """
        self._audit_dir.mkdir(parents=True, exist_ok=True)
        path = self._record_path(audit.run_id)
        data = audit.model_dump(mode="json", exclude_none=True)
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def __repr__(self) -> str:
        return f"AuditStore(audit_dir='{self._audit_dir}')"
