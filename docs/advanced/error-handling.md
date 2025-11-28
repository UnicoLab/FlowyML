# Error Handling & Retries 🛡️

Building robust pipelines requires handling failures gracefully. UniFlow provides advanced error handling mechanisms like Retries, Circuit Breakers, and Fallbacks.

## 🔄 Retries

Automatically retry failed steps with configurable backoff strategies.

### Exponential Backoff

```python
from uniflow import step, retry, ExponentialBackoff

@step(
    retry=retry(
        max_attempts=5,
        backoff=ExponentialBackoff(initial=1.0, multiplier=2.0),
        on=[NetworkError, TimeoutError]
    )
)
def fetch_data():
    # This will be retried up to 5 times on network errors
    return api.get_data()
```

## 🔌 Circuit Breakers

Prevent cascading failures by "opening the circuit" when a service is down, failing fast instead of waiting for timeouts.

```python
from uniflow import step, CircuitBreaker

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
from uniflow import step, on_failure

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
