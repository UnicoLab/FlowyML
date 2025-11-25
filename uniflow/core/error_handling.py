"""Error handling utilities for robust pipeline execution."""

import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, List, Optional, Type
from enum import Enum


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failures exceed threshold, rejecting requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""

    failure_threshold: int = 5
    """Number of failures before opening circuit"""

    timeout: float = 60
    """Time to wait before trying again (seconds)"""

    recovery_timeout: float = 300
    """Time to wait before fully closing circuit (seconds)"""

    expected_exceptions: List[Type[Exception]] = field(default_factory=lambda: [Exception])
    """Exceptions that trigger circuit breaker"""


class CircuitBreaker:
    """Circuit breaker pattern implementation.

    Prevents cascading failures by failing fast when a service is down.

    Example:
        ```python
        @step(circuit_breaker=CircuitBreaker(failure_threshold=3, timeout=60))
        def call_api(url):
            return requests.get(url).json()
        ```
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: float = 60,
        recovery_timeout: float = 300,
        expected_exceptions: Optional[List[Type[Exception]]] = None,
    ):
        """Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            timeout: Seconds to wait before trying again
            recovery_timeout: Seconds to wait before fully closing circuit
            expected_exceptions: Exceptions that trigger the breaker
        """
        self.config = CircuitBreakerConfig(
            failure_threshold=failure_threshold,
            timeout=timeout,
            recovery_timeout=recovery_timeout,
            expected_exceptions=expected_exceptions or [Exception],
        )

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.success_count = 0

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Call function with circuit breaker protection.

        Args:
            func: Function to call
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            CircuitOpenError: If circuit is open
        """
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
            else:
                raise CircuitOpenError(
                    f"Circuit breaker is open. Wait {self.config.timeout}s before retry."
                )

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result

        except Exception as e:
            if self._is_expected_exception(e):
                self._on_failure()
            raise

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.last_failure_time is None:
            return True

        time_since_failure = (datetime.now() - self.last_failure_time).total_seconds()
        return time_since_failure >= self.config.timeout

    def _is_expected_exception(self, exception: Exception) -> bool:
        """Check if exception should trigger circuit breaker."""
        return any(isinstance(exception, exc_type) for exc_type in self.config.expected_exceptions)

    def _on_success(self) -> None:
        """Handle successful call."""
        self.failure_count = 0

        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            # Fully close circuit after successful recovery period
            if (
                self.last_failure_time
                and (datetime.now() - self.last_failure_time).total_seconds()
                >= self.config.recovery_timeout
            ):
                self.state = CircuitState.CLOSED
                self.success_count = 0

    def _on_failure(self) -> None:
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.failure_count >= self.config.failure_threshold:
            self.state = CircuitState.OPEN

    def reset(self) -> None:
        """Reset circuit breaker to closed state."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None


class CircuitOpenError(Exception):
    """Exception raised when circuit breaker is open."""

    pass


@dataclass
class FallbackConfig:
    """Configuration for fallback handler."""

    fallback_func: Callable
    """Fallback function to call on error"""

    fallback_on: List[Type[Exception]] = field(default_factory=lambda: [Exception])
    """Exceptions that trigger fallback"""

    max_fallback_attempts: int = 1
    """Maximum number of fallback attempts"""


class FallbackHandler:
    """Fallback handler for graceful degradation.

    Example:
        ```python
        @step(fallback=lambda: load_cached_data(), fallback_on=[TimeoutError])
        def fetch_live_data():
            return requests.get(url).json()
        ```
    """

    def __init__(
        self,
        fallback_func: Callable,
        fallback_on: Optional[List[Type[Exception]]] = None,
        max_attempts: int = 1,
    ):
        """Initialize fallback handler.

        Args:
            fallback_func: Function to call as fallback
            fallback_on: Exceptions that trigger fallback
            max_attempts: Maximum fallback attempts
        """
        self.config = FallbackConfig(
            fallback_func=fallback_func,
            fallback_on=fallback_on or [Exception],
            max_fallback_attempts=max_attempts,
        )
        self.fallback_attempts = 0

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Call function with fallback protection.

        Args:
            func: Primary function to call
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result or fallback result
        """
        try:
            return func(*args, **kwargs)

        except Exception as e:
            if self._should_fallback(e):
                if self.fallback_attempts < self.config.max_fallback_attempts:
                    self.fallback_attempts += 1
                    return self.config.fallback_func()
            raise

    def _should_fallback(self, exception: Exception) -> bool:
        """Check if exception should trigger fallback."""
        return any(isinstance(exception, exc_type) for exc_type in self.config.fallback_on)

    def reset(self) -> None:
        """Reset fallback attempts counter."""
        self.fallback_attempts = 0


class ExponentialBackoff:
    """Exponential backoff retry strategy.

    Example:
        ```python
        from uniflow import step, retry, ExponentialBackoff

        @step(
            retry=retry(
                max_attempts=5,
                backoff=ExponentialBackoff(initial=1, max=60, multiplier=2),
                on=[NetworkError, TimeoutError]
            )
        )
        def fetch_data():
            return api.get_data()
        ```
    """

    def __init__(
        self,
        initial: float = 1.0,
        max: float = 60.0,
        multiplier: float = 2.0,
        jitter: bool = True,
    ):
        """Initialize exponential backoff.

        Args:
            initial: Initial delay in seconds
            max: Maximum delay in seconds
            multiplier: Backoff multiplier
            jitter: Add random jitter to delays
        """
        self.initial = initial
        self.max = max
        self.multiplier = multiplier
        self.jitter = jitter
        self.attempt = 0

    def get_delay(self) -> float:
        """Get delay for current attempt.

        Returns:
            Delay in seconds
        """
        delay = min(self.initial * (self.multiplier ** self.attempt), self.max)

        if self.jitter:
            import random

            delay = delay * (0.5 + random.random())

        self.attempt += 1
        return delay

    def reset(self) -> None:
        """Reset attempt counter."""
        self.attempt = 0


@dataclass
class RetryConfig:
    """Configuration for retry logic."""

    max_attempts: int = 3
    """Maximum number of retry attempts"""

    backoff: Optional[ExponentialBackoff] = None
    """Backoff strategy"""

    retry_on: List[Type[Exception]] = field(default_factory=lambda: [Exception])
    """Exceptions to retry on"""

    not_retry_on: List[Type[Exception]] = field(default_factory=list)
    """Exceptions NOT to retry on"""


def retry(
    max_attempts: int = 3,
    backoff: Optional[ExponentialBackoff] = None,
    on: Optional[List[Type[Exception]]] = None,
    not_on: Optional[List[Type[Exception]]] = None,
) -> RetryConfig:
    """Create retry configuration.

    Args:
        max_attempts: Maximum retry attempts
        backoff: Backoff strategy
        on: Exceptions to retry on
        not_on: Exceptions not to retry on

    Returns:
        RetryConfig instance
    """
    return RetryConfig(
        max_attempts=max_attempts,
        backoff=backoff or ExponentialBackoff(),
        retry_on=on or [Exception],
        not_retry_on=not_on or [],
    )


def execute_with_retry(
    func: Callable, retry_config: RetryConfig, *args, **kwargs
) -> Any:
    """Execute function with retry logic.

    Args:
        func: Function to execute
        retry_config: Retry configuration
        *args: Positional arguments
        **kwargs: Keyword arguments

    Returns:
        Function result

    Raises:
        Last exception if all retries fail
    """
    last_exception = None

    for attempt in range(retry_config.max_attempts):
        try:
            return func(*args, **kwargs)

        except Exception as e:
            # Don't retry if in not_retry_on list
            if any(isinstance(e, exc_type) for exc_type in retry_config.not_retry_on):
                raise

            # Only retry if in retry_on list
            if not any(isinstance(e, exc_type) for exc_type in retry_config.retry_on):
                raise

            last_exception = e

            # Don't sleep on last attempt
            if attempt < retry_config.max_attempts - 1:
                if retry_config.backoff:
                    delay = retry_config.backoff.get_delay()
                    time.sleep(delay)

    # All retries failed
    if last_exception:
        raise last_exception
    else:
        raise RuntimeError("Retry failed with no exception captured")


@dataclass
class OnFailureConfig:
    """Configuration for failure handling."""

    action: str = "log"
    """Action to take (log, email, slack, webhook)"""

    recipients: List[str] = field(default_factory=list)
    """Recipients for notifications"""

    include_logs: bool = True
    """Include logs in notification"""

    include_traceback: bool = True
    """Include full traceback"""


def on_failure(
    action: str = "log",
    recipients: Optional[List[str]] = None,
    include_logs: bool = True,
    include_traceback: bool = True,
) -> OnFailureConfig:
    """Create failure handling configuration.

    Args:
        action: Action to take on failure
        recipients: Recipients for notifications
        include_logs: Include logs in notification
        include_traceback: Include full traceback

    Returns:
        OnFailureConfig instance
    """
    return OnFailureConfig(
        action=action,
        recipients=recipients or [],
        include_logs=include_logs,
        include_traceback=include_traceback,
    )
