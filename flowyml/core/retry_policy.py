"""Retry policies for orchestrators."""

from dataclasses import dataclass
from typing import TYPE_CHECKING
from flowyml.core.error_handling import RetryConfig, ExponentialBackoff, execute_with_retry

if TYPE_CHECKING:
    from flowyml.core.pipeline import Pipeline


@dataclass
class OrchestratorRetryPolicy:
    """Retry policy for orchestrator-level failures.

    This handles retries at the orchestrator level (entire pipeline runs),
    distinct from step-level retries.
    """

    max_attempts: int = 3
    """Maximum number of pipeline retry attempts"""

    initial_delay: float = 60.0
    """Initial delay between retries in seconds"""

    max_delay: float = 600.0
    """Maximum delay between retries in seconds"""

    multiplier: float = 2.0
    """Backoff multiplier for exponential backoff"""

    retry_on_status: list[str] = None
    """Retry on specific execution statuses (e.g., ['FAILED', 'STOPPED'])"""

    def __post_init__(self):
        if self.retry_on_status is None:
            self.retry_on_status = ["FAILED"]

    def to_retry_config(self) -> RetryConfig:
        """Convert to RetryConfig for execute_with_retry."""
        backoff = ExponentialBackoff(
            initial=self.initial_delay,
            max_delay=self.max_delay,
            multiplier=self.multiplier,
            jitter=True,
        )

        return RetryConfig(
            max_attempts=self.max_attempts,
            backoff=backoff,
            retry_on=[Exception],  # Catch all exceptions
            not_retry_on=[KeyboardInterrupt],  # Don't retry on manual interruption
        )


def with_retry(orchestrator_method):
    """Decorator to add retry logic to orchestrator methods.

    Usage:
        @with_retry
        def run_pipeline(self, pipeline, ...):
            ...
    """

    def wrapper(self, pipeline: "Pipeline", *args, retry_policy: OrchestratorRetryPolicy | None = None, **kwargs):
        if retry_policy is None:
            # No retry policy, execute normally
            return orchestrator_method(self, pipeline, *args, **kwargs)

        # Execute with retry
        retry_config = retry_policy.to_retry_config()
        return execute_with_retry(
            orchestrator_method,
            retry_config,
            self,
            pipeline,
            *args,
            **kwargs,
        )

    return wrapper
