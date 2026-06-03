"""Tests for the audit subsystem."""

import json
from datetime import datetime, timezone

import pytest
import yaml

from flowyml.stacks.enterprise.audit import AuditRecord, AuditStore
from flowyml.stacks.enterprise.execution import ExecutionContext


def _make_execution_context(sample_stack, run_id="run-001"):
    """Helper to create an ExecutionContext from a sample stack."""
    return ExecutionContext(
        project_name="test-project",
        pipeline_name="test-pipeline",
        run_id=run_id,
        stack=sample_stack,
        stack_digest=sample_stack.compute_digest(),
    )


class TestAuditRecord:
    """AuditRecord construction."""

    def test_audit_record_creation(self):
        """AuditRecord can be created directly with required fields."""
        record = AuditRecord(
            run_id="test-run-001",
            project="test-project",
            pipeline="test-pipeline",
            stack_name="test_cpu_stack",
            stack_version="1.0.0",
            stack_digest="sha256:abc123",
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        assert record.run_id == "test-run-001"
        assert record.project == "test-project"
        assert record.status == "pending", "Default status should be 'pending'"
        assert record.policy_status == "not_checked"


class TestAuditStore:
    """AuditStore persistence and retrieval."""

    def test_audit_store_record_and_get(self, sample_stack, tmp_path):
        """Recording an audit creates a file; get() retrieves it."""
        store = AuditStore(audit_dir=str(tmp_path / "audit"))
        context = _make_execution_context(sample_stack, run_id="run-001")

        audit = store.record(context)
        assert audit.run_id == "run-001"
        assert audit.stack_name == "test_cpu_stack"

        # Retrieve
        retrieved = store.get("run-001")
        assert retrieved is not None, "get() should find the persisted record"
        assert retrieved.run_id == "run-001"
        assert retrieved.project == "test-project"

    def test_audit_store_list_records(self, sample_stack, tmp_path):
        """list_records() returns all recorded audits."""
        store = AuditStore(audit_dir=str(tmp_path / "audit"))

        store.record(_make_execution_context(sample_stack, run_id="run-001"))
        store.record(_make_execution_context(sample_stack, run_id="run-002"))

        records = store.list_records()
        assert len(records) == 2, f"Expected 2 records, got {len(records)}"

    def test_audit_store_export_json(self, sample_stack, tmp_path):
        """export(format='json') returns valid JSON."""
        store = AuditStore(audit_dir=str(tmp_path / "audit"))
        store.record(_make_execution_context(sample_stack, run_id="run-json"))

        exported = store.export("run-json", format="json")
        data = json.loads(exported)
        assert data["run_id"] == "run-json", "Exported JSON should contain run_id"
        assert data["stack_name"] == "test_cpu_stack"

    def test_audit_store_export_yaml(self, sample_stack, tmp_path):
        """export(format='yaml') returns valid YAML."""
        store = AuditStore(audit_dir=str(tmp_path / "audit"))
        store.record(_make_execution_context(sample_stack, run_id="run-yaml"))

        exported = store.export("run-yaml", format="yaml")
        data = yaml.safe_load(exported)
        assert data["run_id"] == "run-yaml", "Exported YAML should contain run_id"
        assert data["pipeline"] == "test-pipeline"
