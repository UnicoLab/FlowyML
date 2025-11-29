# Performance Optimization

Tools and techniques for optimizing pipeline performance.

## Overview

flowyml provides several performance optimization utilities:
- **Lazy Evaluation**: Defer computations until needed
- **Parallel Execution**: Run steps concurrently
- **Incremental Computation**: Recompute only what changed
- **GPU Management**: Efficient GPU resource allocation
- **DataFrame Optimization**: Reduce memory usage

## Lazy Evaluation

Defer expensive computations until their results are actually needed.

```python
from flowyml.utils.performance import LazyValue, lazy_property

# Lazy value
expensive_data = LazyValue(lambda: load_huge_dataset())

# Not loaded yet!
print("Created lazy value")

# Loaded only when accessed
data = expensive_data.value  # Triggers loading

# Subsequent accesses use cached value
data2 = expensive_data.value  # Instant!
```

### Lazy Properties

```python
class DataProcessor:
    def __init__(self, path):
        self.path = path

    @lazy_property
    def data(self):
        """Loaded only when first accessed."""
        print("Loading data...")
        return pd.read_csv(self.path)

    @lazy_property
    def statistics(self):
        """Computed only when needed."""
        print("Computing statistics...")
        return self.data.describe()

processor = DataProcessor("data.csv")
# Nothing loaded yet!

stats = processor.statistics  # Triggers data loading + computation
stats2 = processor.statistics  # Uses cached value
```

## Parallel Execution

Execute independent steps concurrently for faster pipelines.

```python
from flowyml.utils.performance import ParallelExecutor

executor = ParallelExecutor(max_workers=4)

# Execute multiple functions in parallel
results = executor.map(
    func=process_chunk,
    iterables=[[chunk1], [chunk2], [chunk3], [chunk4]]
)

# Or execute different functions
futures = {
    'data1': executor.submit(load_dataset, 'data1.csv'),
    'data2': executor.submit(load_dataset, 'data2.csv'),
    'model': executor.submit(load_model, 'model.pkl')
}

# Wait for all to complete
results = executor.wait_all(futures)
```

### Parallel Pipeline Steps

```python
from flowyml import Pipeline, step

@step(outputs=["chunk1"])
def process_chunk1(data):
    return process(data[:1000])

@step(outputs=["chunk2"])
def process_chunk2(data):
    return process(data[1000:2000])

@step(outputs=["chunk3"])
def process_chunk3(data):
    return process(data[2000:])

# These steps can run in parallel (no dependencies)
pipeline = Pipeline("parallel_processing")
pipeline.add_step(process_chunk1)
pipeline.add_step(process_chunk2)
pipeline.add_step(process_chunk3)

# Enable parallel execution
executor = ParallelExecutor(max_workers=3)
result = pipeline.run(executor=executor)
```

## Incremental Computation

Recompute only what changed, not everything.

```python
from flowyml.utils.performance import IncrementalComputation

# Track dependencies
inc = IncrementalComputation()

# Register computations
inc.register("load_data", lambda: load_csv("data.csv"))
inc.register("clean_data", lambda: clean(inc.get("load_data")), deps=["load_data"])
inc.register("train_model", lambda: train(inc.get("clean_data")), deps=["clean_data"])

# Compute all
results = inc.compute_all()

# Update source data
update_csv("data.csv")

# Mark as changed
inc.invalidate("load_data")

# Only load_data + dependent steps recompute
results = inc.compute_all()  # clean_data and train_model also rerun
```

### Dependency Tracking

```python
# Complex dependency graph
inc = IncrementalComputation()

inc.register("A", compute_a)
inc.register("B", compute_b)
inc.register("C", lambda: compute_c(inc.get("A"), inc.get("B")), deps=["A", "B"])
inc.register("D", lambda: compute_d(inc.get("C")), deps=["C"])

# If A changes, C and D recompute (but not B)
inc.invalidate("A")
inc.compute_all()
```

## GPU Resource Management

Efficiently manage GPU memory and allocation.

```python
from flowyml.utils.performance import GPUResourceManager

gpu = GPUResourceManager()

# Check availability
if gpu.is_available():
    print(f"GPUs available: {gpu.get_device_count()}")

    #Get current usage
    usage = gpu.get_memory_usage(device=0)
    print(f"GPU 0: {usage['used_mb']}/{usage['total_mb']} MB")

# Auto-select best GPU
device = gpu.get_best_device()
print(f"Using GPU: {device}")

# Allocate tensors
import torch
tensor = torch.randn(1000, 1000).to(device)

# Monitor usage
gpu.print_memory_summary()
```

### Automatic GPU Selection

```python
@step(outputs=["model"])
def train_on_best_gpu(data):
    gpu = GPUResourceManager()
    device = gpu.get_best_device()  # Least loaded GPU

    model = Model().to(device)
    model.fit(data)
    return model
```

## DataFrame Optimization

Reduce pandas DataFrame memory usage.

```python
from flowyml.utils.performance import optimize_dataframe

# Original DataFrame
df = pd.read_csv("large_file.csv")
print(f"Original: {df.memory_usage(deep=True).sum() / 1024**2:.1f} MB")

# Optimize
df_optimized = optimize_dataframe(df)
print(f"Optimized: {df_optimized.memory_usage(deep=True).sum() / 1024**2:.1f} MB")

# Typical savings: 50-80%!
```

### Optimization Techniques

```python
# Manual optimization
df['category_col'] = df['category_col'].astype('category')  # String → Category
df['int_col'] = df['int_col'].astype('int32')  # int64 → int32
df['float_col'] = pd.to_numeric(df['float_col'], downcast='float')  # float64 → float32
```

## Batch Processing

Process large datasets in batches.

```python
from flowyml.utils.performance import batch_iterator

# Process in batches
for batch in batch_iterator(large_dataset, batch_size=1000):
    process_batch(batch)

# With progress tracking
from tqdm import tqdm

for batch in tqdm(batch_iterator(large_dataset, batch_size=1000)):
    process_batch(batch)
```

## Best Practices

### 1. Profile Before Optimizing

```python
import time

@step(outputs=["result"])
def slow_step(data):
    start = time.time()
    result = expensive_operation(data)
    print(f"⏱️ Took {time.time() - start:.2f}s")
    return result

# Find the bottleneck first!
```

### 2. Use Lazy Loading for Large Data

```python
class Pipeline:
    def __init__(self):
        # Don't load immediately
        self.data = LazyValue(lambda: load_huge_dataset())

    def process(self):
        # Load only when needed
        return process(self.data.value)
```

### 3. Parallelize Independent Steps

```python
# ✅ Good - independent steps
@step(outputs=["A"])
def compute_a():
    ...

@step(outputs=["B"])
def compute_b():
    ...

# Can run in parallel!

# ❌ Bad - sequential dependency
@step(inputs=["A"], outputs=["B"])
def compute_b(a):
    ...

# Must run after A
```

### 4. Batch for Memory Efficiency

```python
# ❌ Bad - loads everything
data = pd.read_csv("huge_file.csv")
process(data)  # OOM!

# ✅ Good - process in batches
for chunk in pd.read_csv("huge_file.csv", chunksize=10000):
    process(chunk)
```

### 5. Monitor GPU Usage

```python
gpu = GPUResourceManager()

# Before training
print(f"Free memory: {gpu.get_free_memory(0)} MB")

# Train
model.fit(data)

# After training
print(f"Free memory: {gpu.get_free_memory(0)} MB")

# Clean up if needed
if gpu.get_free_memory(0) < 1000:  # < 1GB
    torch.cuda.empty_cache()
```

## Performance Patterns

### Pattern 1: Lazy + Cache

```python
from functools import lru_cache

class DataPipeline:
    @lazy_property
    @lru_cache(maxsize=1)
    def processed_data(self):
        # Loaded and cached lazily
        data = self.load_data()
        return self.process(data)
```

### Pattern 2: Parallel + Batch

```python
from flowyml.utils.performance import ParallelExecutor, batch_iterator

executor = ParallelExecutor(max_workers=4)

# Process batches in parallel
batches = list(batch_iterator(dataset, batch_size=1000))
results = executor.map(process_batch, [[b] for b in batches])
```

### Pattern 3: Incremental + Cache

```python
from flowyml.utils.performance import IncrementalComputation
from flowyml import SmartCache

cache = SmartCache(ttl_seconds=3600)
inc = IncrementalComputation()

def cached_compute(key):
    cached = cache.get(key)
    if cached:
        return cached

    result = expensive_computation()
    cache.set(key, result)
    return result

inc.register("step1", lambda: cached_compute("step1"))
```

## API Reference

### LazyValue

```python
LazyValue(fn: Callable)
```

**Properties**:
- `value` - Gets computed value (computes on first access)

### ParallelExecutor

```python
ParallelExecutor(max_workers: int = None)
```

**Methods**:
- `submit(fn, *args, **kwargs) -> Future`
- `map(fn, iterables) -> List`
- `wait_all(futures: Dict) -> Dict`

### IncrementalComputation

```python
IncrementalComputation()
```

**Methods**:
- `register(name, fn, deps=None)`
- `compute(name) -> Any`
- `compute_all() -> Dict`
- `invalidate(name)`
- `get(name) -> Any`

### GPUResourceManager

```python
GPUResourceManager()
```

**Methods**:
- `is_available() -> bool`
- `get_device_count() -> int`
- `get_best_device() -> str`
- `get_memory_usage(device) -> Dict`
- `get_free_memory(device) -> int`
- `print_memory_summary()`

### optimize_dataframe

```python
optimize_dataframe(df: pd.DataFrame) -> pd.DataFrame
```

### batch_iterator

```python
batch_iterator(iterable, batch_size: int)
```

## Benchmarks

### Lazy Evaluation

```python
# Without lazy
start = time.time()
data1 = load_data()  # 5s
data2 = load_data()  # 5s
# Might not use data2!
print(f"Time: {time.time()-start}s")  # 10s

# With lazy
start = time.time()
data1 = LazyValue(load_data)
data2 = LazyValue(load_data)  # Instant
print(f"Time: {time.time()-start}s")  # 0s
```

### Parallel Execution

```python
# Sequential
for item in items:  # 100 items, 0.1s each
    process(item)
# Total: 10s

# Parallel (4 workers)
executor.map(process, [[i] for i in items])
# Total: 2.5s (4x faster!)
```

### DataFrame Optimization

Typical memory reduction:
- int columns: 50% (int64 → int32)
- float columns: 50% (float64 → float32)
- string columns: 80% (object → category)

Overall: **50-80% memory savings**
