"""Submission result for async pipeline execution."""

from typing import Any, Optional
from collections.abc import Callable


class SubmissionResult:
    """Result of submitting a pipeline run to an orchestrator.

    This class enables async execution patterns where the orchestrator
    submits the pipeline and returns immediately, optionally providing
    a way to wait for completion.
    """

    def __init__(
        self,
        job_id: str,
        wait_for_completion: Optional[Callable[[], None]] = None,
        metadata: Optional[dict[str, Any]] = None,
    ):
        """Initialize a submission result.

        Args:
            job_id: The remote job/run identifier.
            wait_for_completion: Optional function to block until pipeline completes.
            metadata: Optional metadata about the submission.
        """
        self.job_id = job_id
        self.wait_for_completion = wait_for_completion
        self.metadata = metadata or {}

    def wait(self, timeout: Optional[int] = None) -> None:
        """Wait for the pipeline run to complete.

        Args:
            timeout: Optional timeout in seconds. If None, waits indefinitely.

        Raises:
            RuntimeError: If no wait_for_completion function was provided.
            TimeoutError: If timeout is exceeded.
        """
        if not self.wait_for_completion:
            raise RuntimeError(
                f"Cannot wait for job {self.job_id}: no wait function provided",
            )

        # TODO: Add timeout support
        if timeout:
            import warnings

            warnings.warn("Timeout parameter not yet implemented", UserWarning, stacklevel=2)

        self.wait_for_completion()
