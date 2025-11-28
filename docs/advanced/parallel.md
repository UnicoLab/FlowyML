# Parallel Execution 🚀

UniFlow allows you to execute independent steps concurrently, significantly reducing the total execution time of your pipelines. This is particularly useful for tasks like data processing, hyperparameter tuning, or running multiple models in parallel.

## 🚀 Enabling Parallelism

You can enable parallel execution by using the `ParallelExecutor`.

### Basic Usage

```python
from uniflow import Pipeline, ParallelExecutor, step

@step
def process_chunk(chunk_id):
    # Simulate work
    return f"processed_{chunk_id}"

pipeline = Pipeline("parallel_processing")

# Add multiple independent steps
for i in range(5):
    pipeline.add_step(process_chunk, name=f"chunk_{i}", params={"chunk_id": i})

# Configure executor
executor = ParallelExecutor(max_workers=4)

# Run pipeline with executor
pipeline.run(executor=executor)
```

### In-Step Parallelism

You can also parallelize work *within* a single step using standard Python libraries or UniFlow's utilities.

```python
from uniflow.utils.parallel import parallel_map

@step
def batch_process(items):
    # Process items in parallel using a thread pool
    results = parallel_map(process_item, items, max_workers=8)
    return results
```

## ⚙️ Configuration

The `ParallelExecutor` supports several configuration options:

- `max_workers`: Maximum number of concurrent threads/processes.
- `backend`: Execution backend (`thread` or `process`). Use `process` for CPU-bound tasks and `thread` for I/O-bound tasks.

```python
executor = ParallelExecutor(
    max_workers=8,
    backend="process"
)
```

## ⚠️ Considerations

- **Shared Resources**: Be careful when accessing shared resources (databases, files) from parallel steps.
- **Global Interpreter Lock (GIL)**: For CPU-intensive tasks in Python, use the `process` backend to bypass the GIL.
