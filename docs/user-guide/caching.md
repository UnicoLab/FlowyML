# Caching ⚡

UniFlow features an intelligent caching system designed to save time and resources by avoiding redundant computations. If a step has been executed before with the same code and inputs, UniFlow can retrieve the result from the cache instead of re-running the step.

## How Caching Works

When a step is about to run, UniFlow calculates a **Cache Key**. This key is typically a hash of:
1.  The step's function code (source code hash).
2.  The step's input arguments (input hash).
3.  The step's name.

If a valid entry for this key exists in the cache store, the step is skipped, and the cached output is returned.

## Configuration ⚙️

### Enabling/Disabling Caching

You can control caching at the pipeline level or the step level.

**Pipeline Level:**
```python
@pipeline(enable_cache=True)  # Default is True
def my_pipeline():
    ...
```

**Step Level:**
```python
@step(cache=False)  # Disable caching for this step
def always_run():
    ...
```

### Caching Strategies

The `@step` decorator accepts a `cache` argument to define the strategy:

- `"code_hash"` (Default): Invalidates cache if the function code changes OR inputs change.
- `"input_hash"`: Invalidates cache ONLY if inputs change. Useful if you change code comments or formatting but logic remains same (though use with caution).
- `False`: Never cache. Always run.
- **Callable**: You can pass a custom function to generate the cache key.

```python
@step(cache="input_hash")
def stable_step(data):
    ...
```

## Managing the Cache 🧹

### Cache Location
By default, the cache is stored in `.uniflow/cache` (SQLite + pickled objects). You can configure this path in `uniflow.yaml`.

### Clearing the Cache

You can clear the cache using the CLI:

```bash
# Clear everything
uniflow cache clear

# Clear for a specific pipeline
uniflow cache clear --pipeline my_pipeline

# Clear old entries
uniflow cache clear --days 30
```

## When to Disable Caching? 🤔

!!! warning "Disable Caching When..."
    - **Non-deterministic steps**: If your step produces random output (and you don't fix the seed).
    - **External side effects**: If your step writes to a database or sends an email.
    - **Debugging**: When you want to force a re-run to inspect logs.
