# Error Handling & Retries 🛡️

Build self-healing pipelines that recover from failures automatically.

> [!NOTE]
> **What you'll learn**: How to make pipelines resilient to network blips, API timeouts, and transient errors
>
> **Key insight**: In distributed systems, failure is inevitable. Your pipeline should handle it, not crash.

## Why Robustness Matters

**Without error handling**:
- **Fragile pipelines**: One network timeout kills the whole job
- **Manual restarts**: Waking up at 3 AM to click "retry"
- **Data loss**: Partial failures leave data in inconsistent states

**With flowyml resilience**:
- **Self-healing**: Transient errors are retried automatically
- **Fail-fast**: Circuit breakers stop cascading failures
- **Graceful degradation**: Fallbacks provide default values when services fail

## Decision Guide: Resilience Patterns

| Pattern | Use When | Example |
|---------|----------|---------|
| **Retry** | **Transient errors**: Network blips, rate limits | API timeout, 503 error |
| **Circuit Breaker** | **System outages**: Service is down hard | Database down, API 500 loop |
| **Fallback** | **Critical path**: Must continue even if step fails | Use cached data if live API fails |

## 🔄 Retries

Automatically retry failed steps with configurable backoff strategies.

### Real-World Pattern: The Flaky API

Handle APIs that randomly fail or rate limit you.

```python
from flowyml import step, retry, ExponentialBackoff

@step(
    retry=retry(
        max_attempts=5,
        backoff=ExponentialBackoff(initial=1.0, multiplier=2.0),
        on=[NetworkError, TimeoutError, RateLimitError]
    )
)
def fetch_data():
    # Attempt 1: Fail
    # Wait 1s...
    # Attempt 2: Fail
    # Wait 2s...
    # Attempt 3: Success!
    return api.get_data()
```

## 🔌 Circuit Breakers

Prevent cascading failures by "opening the circuit" when a service is down, failing fast instead of waiting for timeouts.

```python
from flowyml import step, CircuitBreaker

@step(
    circuit_breaker=CircuitBreaker(
        failure_threshold=3,
        timeout=60  # Wait 60s before trying again
    )
)
def call_unstable_api():
    return external_service.call()
```

## 🛡️ Fallbacks

Define a fallback function to execute when a step fails, ensuring the pipeline can continue.

```python
def load_cached_data():
    return cache.get("latest_data")

@step(
    fallback=load_cached_data,
    fallback_on=[TimeoutError]
)
def fetch_live_data():
    return api.get_live_data()
```

## 🚨 Failure Handlers

Configure actions to take when a step fails (e.g., send alerts).

```python
from flowyml import step, on_failure

@step(
    on_failure=on_failure(
        action="slack",
        recipients=["#ml-alerts"],
        include_logs=True
    )
)
def critical_step():
    # ...
```
