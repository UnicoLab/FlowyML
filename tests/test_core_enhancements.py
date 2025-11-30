"""Tests for ExecutionStatus and SubmissionResult."""

import pytest
from flowyml.core.execution_status import ExecutionStatus
from flowyml.core.submission_result import SubmissionResult


class TestExecutionStatus:
    """Test ExecutionStatus enum."""

    def test_status_values(self):
        """Test all status values exist."""
        assert ExecutionStatus.INITIALIZING == "initializing"
        assert ExecutionStatus.PROVISIONING == "provisioning"
        assert ExecutionStatus.RUNNING == "running"
        assert ExecutionStatus.COMPLETED == "completed"
        assert ExecutionStatus.FAILED == "failed"
        assert ExecutionStatus.STOPPED == "stopped"
        assert ExecutionStatus.CANCELLED == "cancelled"

    def test_is_finished(self):
        """Test is_finished property."""
        assert ExecutionStatus.COMPLETED.is_finished
        assert ExecutionStatus.FAILED.is_finished
        assert ExecutionStatus.STOPPED.is_finished
        assert ExecutionStatus.CANCELLED.is_finished

        assert not ExecutionStatus.RUNNING.is_finished
        assert not ExecutionStatus.INITIALIZING.is_finished
        assert not ExecutionStatus.PROVISIONING.is_finished

    def test_is_successful(self):
        """Test is_successful property."""
        assert ExecutionStatus.COMPLETED.is_successful
        assert ExecutionStatus.CACHED.is_successful

        assert not ExecutionStatus.FAILED.is_successful
        assert not ExecutionStatus.RUNNING.is_successful

    def test_is_failed(self):
        """Test is_failed property."""
        assert ExecutionStatus.FAILED.is_failed
        assert ExecutionStatus.STOPPED.is_failed
        assert ExecutionStatus.CANCELLED.is_failed

        assert not ExecutionStatus.COMPLETED.is_failed
        assert not ExecutionStatus.RUNNING.is_failed


class TestSubmissionResult:
    """Test SubmissionResult class."""

    def test_creation(self):
        """Test creating a submission result."""
        result = SubmissionResult(job_id="test-job-123")
        assert result.job_id == "test-job-123"
        assert result.wait_for_completion is None
        assert result.metadata == {}

    def test_with_metadata(self):
        """Test submission result with metadata."""
        metadata = {"platform": "aws", "region": "us-west-2"}
        result = SubmissionResult(
            job_id="test-job-456",
            metadata=metadata,
        )
        assert result.metadata == metadata

    def test_with_wait_function(self):
        """Test submission result with wait function."""
        completed = {"status": False}

        def wait_fn():
            completed["status"] = True

        result = SubmissionResult(
            job_id="test-job-789",
            wait_for_completion=wait_fn,
        )

        result.wait()
        assert completed["status"] is True

    def test_wait_without_function(self):
        """Test wait raises error without wait function."""
        result = SubmissionResult(job_id="test-job-000")

        with pytest.raises(RuntimeError, match="no wait function provided"):
            result.wait()
