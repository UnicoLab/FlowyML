"""Execution status tracking for pipeline runs."""

from enum import Enum


class ExecutionStatus(str, Enum):
    """Status of a pipeline or step execution."""

    # Pre-execution states
    INITIALIZING = "initializing"
    PROVISIONING = "provisioning"

    # Active execution states
    RUNNING = "running"

    # Terminal success states
    COMPLETED = "completed"
    CACHED = "cached"

    # Terminal failure states
    FAILED = "failed"
    STOPPED = "stopped"
    CANCELLED = "cancelled"

    # Intermediate states
    STOPPING = "stopping"
    CANCELLING = "cancelling"

    @property
    def is_finished(self) -> bool:
        """Check if execution is in a terminal state."""
        return self in {
            ExecutionStatus.COMPLETED,
            ExecutionStatus.CACHED,
            ExecutionStatus.FAILED,
            ExecutionStatus.STOPPED,
            ExecutionStatus.CANCELLED,
        }

    @property
    def is_successful(self) -> bool:
        """Check if execution completed successfully."""
        return self in {ExecutionStatus.COMPLETED, ExecutionStatus.CACHED}

    @property
    def is_failed(self) -> bool:
        """Check if execution failed."""
        return self in {
            ExecutionStatus.FAILED,
            ExecutionStatus.STOPPED,
            ExecutionStatus.CANCELLED,
        }
