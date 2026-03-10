# Map Tasks

Map tasks let you distribute work across a typed collection with automatic parallelism, per-item retries, and partial failure tolerance.

## Basic Usage

```python
from flowyml import map_task

@map_task(concurrency=4, retries=2, min_success_ratio=0.9)
def process_record(record: dict) -> dict:
    return transform(record)

# Use in pipeline
pipeline.add_step(process_record, inputs=["raw_records"], outputs=["processed"])
```

## Configuration

| Parameter | Default | Description |
|---|---|---|
| `concurrency` | 4 | Maximum parallel workers |
| `retries` | 0 | Per-item retry count |
| `retry_delay` | 1.0 | Base delay between retries (seconds) |
| `min_success_ratio` | 1.0 | Minimum ratio of items that must succeed |
| `fail_fast` | False | Stop all processing on first failure |
| `timeout_per_item` | None | Optional per-item timeout (seconds) |

## Partial Failure Tolerance

Set `min_success_ratio` below `1.0` to allow some items to fail:

```python
@map_task(concurrency=8, min_success_ratio=0.95)
def process_document(doc: str) -> str:
    # 5% of documents can fail without failing the pipeline
    return analyze(doc)
```

## Result Inspection

```python
result = process_documents(my_docs)

print(f"Success: {result.successes}/{result.total}")
print(f"Success ratio: {result.success_ratio:.1%}")
print(f"Failed indices: {list(result.errors.keys())}")
print(f"Successful results: {result.successful_results}")
```
