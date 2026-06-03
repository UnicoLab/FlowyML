"""Tests for the StackLockManager."""

import copy

import pytest

from flowyml.stacks.enterprise.exceptions import StackLockError
from flowyml.stacks.enterprise.lock import LockVerificationResult, StackLockManager
from flowyml.stacks.enterprise.models import StackDefinition


class TestStackLockManager:
    """StackLockManager locking and verification."""

    def test_lock_creates_file(self, sample_stack, tmp_path):
        """Locking a stack persists a lock file to disk."""
        lock_file = tmp_path / "flowyml.lock"
        mgr = StackLockManager(lock_path=str(lock_file), project_name="test-project")

        mgr.lock("test_cpu_stack", sample_stack, source_uri="local://")
        assert lock_file.exists(), "Lock file should be created on disk"

    def test_lock_verify_passes(self, sample_stack, tmp_path):
        """Verifying an unchanged stack returns status='verified'."""
        lock_file = tmp_path / "flowyml.lock"
        mgr = StackLockManager(lock_path=str(lock_file), project_name="test-project")

        mgr.lock("test_cpu_stack", sample_stack, source_uri="local://")
        result = mgr.verify_stack("test_cpu_stack", sample_stack)

        assert result.status == "verified", "Unchanged stack should verify successfully"
        assert result.expected_digest == result.actual_digest

    def test_lock_verify_detects_modification(self, sample_stack, sample_stack_dict, tmp_path):
        """Verifying a modified stack returns status='modified'."""
        lock_file = tmp_path / "flowyml.lock"
        mgr = StackLockManager(lock_path=str(lock_file), project_name="test-project")

        mgr.lock("test_cpu_stack", sample_stack, source_uri="local://")

        # Create a modified version of the stack
        modified_dict = copy.deepcopy(sample_stack_dict)
        modified_dict["metadata"]["version"] = "2.0.0"
        modified_stack = StackDefinition.from_dict(modified_dict)

        result = mgr.verify_stack("test_cpu_stack", modified_stack)
        assert result.status == "modified", "Modified stack should be detected"
        assert result.expected_digest != result.actual_digest

    def test_lock_is_locked(self, sample_stack, tmp_path):
        """is_locked() returns True for locked stacks, False otherwise."""
        lock_file = tmp_path / "flowyml.lock"
        mgr = StackLockManager(lock_path=str(lock_file), project_name="test-project")

        assert not mgr.is_locked("test_cpu_stack"), "Stack should not be locked initially"

        mgr.lock("test_cpu_stack", sample_stack, source_uri="local://")
        assert mgr.is_locked("test_cpu_stack"), "Stack should be locked after lock()"
        assert not mgr.is_locked("other_stack"), "Unlocked stack should return False"

    def test_lock_update(self, sample_stack, sample_stack_dict, tmp_path):
        """update() overwrites an existing lock entry without raising."""
        lock_file = tmp_path / "flowyml.lock"
        mgr = StackLockManager(lock_path=str(lock_file), project_name="test-project")

        mgr.lock("test_cpu_stack", sample_stack, source_uri="local://")
        original_digest = mgr.get_locked_digest("test_cpu_stack")

        # Create a modified version and update
        modified_dict = copy.deepcopy(sample_stack_dict)
        modified_dict["metadata"]["version"] = "2.0.0"
        modified_stack = StackDefinition.from_dict(modified_dict)

        # update() should NOT raise even though the stack is already locked
        mgr.update("test_cpu_stack", modified_stack, source_uri="local://v2")
        new_digest = mgr.get_locked_digest("test_cpu_stack")

        assert new_digest != original_digest, "Digest should change after update"

    def test_lock_multiple_stacks(self, sample_stack, azureml_stack, tmp_path):
        """Multiple stacks can be locked independently."""
        lock_file = tmp_path / "flowyml.lock"
        mgr = StackLockManager(lock_path=str(lock_file), project_name="test-project")

        mgr.lock("stack_a", sample_stack, source_uri="local://")
        mgr.lock("stack_b", azureml_stack, source_uri="azureml://")

        assert mgr.is_locked("stack_a"), "stack_a should be locked"
        assert mgr.is_locked("stack_b"), "stack_b should be locked"

        results = mgr.verify()
        assert len(results) == 2, "verify() should return one result per locked stack"
        assert all(r.status == "verified" for r in results)
