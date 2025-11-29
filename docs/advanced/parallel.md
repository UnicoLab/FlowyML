# Parallel Execution 🚀

flowyml allows you to execute independent steps concurrently, slashing pipeline runtime by running tasks in parallel.

> [!NOTE]
> **What you'll learn**: How to run multiple steps at once to speed up execution
>
> **Key insight**: Most ML pipelines have independent branches (e.g., processing different datasets). Running them sequentially is a waste of time.

## Why Parallelism Matters

**Without parallelism**:
- **Slow execution**: Steps run one after another (A → B → C)
- **Idle resources**: CPU cores sit idle while one core works
- **Long feedback loops**: Waiting hours for independent tasks

**With flowyml parallelism**:
- **Faster results**: Run A, B, and C at the same time
- **Resource efficiency**: Utilize all CPU cores
- **Scalability**: Process 10x data in the same amount of time

## Enabling Parallelism

You can enable parallel execution by using the `ParallelExecutor`. It automatically detects independent steps in your DAG and runs them concurrently.

### Basic Usage

```python
from flowyml import Pipeline, ParallelExecutor, step

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

You can also parallelize work *within* a single step using standard Python libraries or flowyml's utilities.

```python
from flowyml.utils.parallel import parallel_map

@step
def batch_process(items):
    # Process items in parallel using a thread pool
    results = parallel_map(process_item, items, max_workers=8)
    return results
```

## Decision Guide: Execution Backends

| Backend | Best For | Why |
|---------|----------|-----|
| `process` (Default) | **CPU-bound tasks** | Bypasses Python's GIL. Good for data processing, training. |
| `thread` | **I/O-bound tasks** | Lightweight. Good for API calls, downloading files, DB queries. |

### When to use `process` (CPU)
- Data transformation (pandas, numpy)
- Image processing
- Model training (sklearn)

### When to use `thread` (I/O)
- Fetching data from APIs
- Uploading files to S3
- Querying databases

## Real-World Pattern: Batch Processing

Process a large dataset by splitting it into chunks and processing them in parallel.

```python
from flowyml import Pipeline, ParallelExecutor, step

@step
def process_chunk(chunk_path):
    # Heavy CPU work
    df = pd.read_csv(chunk_path)
    return df.mean()

pipeline = Pipeline("batch_processor")

# Add 10 parallel steps
for i in range(10):
    pipeline.add_step(
        process_chunk,
        name=f"chunk_{i}",
        params={"chunk_path": f"data/part_{i}.csv"}
    )

# Run with 4 processes
pipeline.run(executor=ParallelExecutor(max_workers=4, backend="process"))
```

> [!TIP]
> **Performance Tip**: Set `max_workers` to `cpu_count() - 1` to keep one core free for the system.
