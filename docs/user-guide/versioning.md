# Pipeline Versioning 🔄

Track changes to your pipelines like you track code with Git.

> [!NOTE]
> **What you'll learn**: How to version your pipelines and compare changes over time
>
> **Key insight**: "What changed between v1 and v2?" is a question you'll ask every week. Versioning answers it instantly.

## Why Versioning Matters

**Without versioning**:
- **No audit trail**: "Who changed the data loader last month?"
- **Risky deployments**: You don't know what changed
- **Lost history**: Can't rollback to a working version

**With flowyml versioning**:
- **Full history**: See exactly what changed and when
- **Safe releases**: Compare new version with production before deploying
- **Easy rollback**: Restore a previous version instantly

## When to Version

| Scenario | Action |
|----------|--------|
| **Before deploying to production** | Always save a version |
| **After adding/removing steps** | Save with descriptive metadata |
| **Major logic changes** | Bump version number (v1.0 → v2.0) |
| **Daily experiments** | Not necessary—only version what you'll deploy |

## Overview ℹ️

The `VersionedPipeline` class provides:
- Save pipeline versions with metadata
- Compare versions to see what changed
- Track pipeline evolution over time
- Maintain a history of pipeline configurations

## Basic Usage 🚀

```python
from flowyml import VersionedPipeline, step

# Create a versioned pipeline
pipeline = VersionedPipeline("training_pipeline")
pipeline.version = "v1.0.0"

# Add steps
@step(outputs=["data"])
def load_data():
    return load_from_source()

@step(inputs=["data"], outputs=["model"])
def train(data):
    return train_model(data)

pipeline.add_step(load_data)
pipeline.add_step(train)

# Save the version
pipeline.save_version(metadata={"description": "Initial training pipeline"})
```

## Comparing Versions 🔍

```python
# Make changes to the pipeline
@step(inputs=["model"], outputs=["metrics"])
def evaluate(model):
    return evaluate_model(model)

pipeline.add_step(evaluate)
pipeline.version = "v1.1.0"
pipeline.save_version(metadata={"description": "Added evaluation step"})

# Compare versions
diff = pipeline.compare_with("v1.0.0")
print(diff)
# Output:
# {
#   'current_version': 'v1.1.0',
#   'compared_to': 'v1.0.0',
#   'added_steps': ['evaluate'],
#   'removed_steps': [],
#   'modified_steps': [],
#   'step_order_changed': True,
#   'context_changes': {...}
# }

# Display comparison in readable format
pipeline.display_comparison("v1.0.0")
```

## Listing Versions 📋

```python
# Get all saved versions
versions = pipeline.list_versions()
print(versions)  # ['v1.0.0', 'v1.1.0']

# Get specific version details
version_info = pipeline.get_version("v1.0.0")
print(version_info.steps)
print(version_info.created_at)
print(version_info.metadata)
```

## Version Storage 💾

Versions are stored as JSON files in `.flowyml/versions/{pipeline_name}/` by default. You can customize the storage location:

```python
pipeline = VersionedPipeline(
    "my_pipeline",
    versions_dir="/custom/path/versions"
)
```

## Best Practices 💡

### 1. Use Semantic Versioning

```python
pipeline.version = "v1.0.0"  # Major.Minor.Patch
```

### 2. Add Descriptive Metadata

```python
pipeline.save_version(metadata={
    "description": "Added data validation step",
    "author": "data-team"impact": "improved data quality",
    "breaking_changes": False
})
```

### 3. Compare Before Deploying

```python
# Always compare with production version before deploying
if pipeline.version != "v1.0.0":  # production version
    diff = pipeline.compare_with("v1.0.0")
    if diff['removed_steps'] or diff['modified_steps']:
        print("⚠️ Breaking changes detected!")
        pipeline.display_comparison("v1.0.0")
```

## Advanced Features ⚡

### Hash-Based Change Detection

The versioning system uses content hashing to detect changes in step implementations:

```python
# Same step name, different implementation
@step(outputs=["data"])
def load_data():
    # Modified implementation
    return load_from_new_source()  # Changed!

pipeline.save_version()
# Will detect that load_data was modified
```

### Context Parameter Tracking

Changes to context parameters are automatically tracked:

```python
from flowyml import context

ctx1 = context(learning_rate=0.001)
pipeline = VersionedPipeline("training", context=ctx1)
pipeline.save_version()

# Change context
ctx2 = context(learning_rate=0.01)  # Changed!
pipeline.context = ctx2
pipeline.save_version()

diff = pipeline.compare_with(previous_version)
# Will show context_changes
```

## Integration with CI/CD 🚀

```python
# In your CI pipeline
def verify_version_changes():
    pipeline = VersionedPipeline.load("production_pipeline")

    # Get current production version
    prod_version = get_production_version()

    # Compare
    diff = pipeline.compare_with(prod_version)

    # Enforce policies
    if diff['removed_steps']:
        raise ValueError("Cannot remove steps in minor version update")

    if diff['modified_steps']:
        # Require integration tests
        run_integration_tests()

    return diff
```

## API Reference 📚

### VersionedPipeline

**Constructor**:
```python
VersionedPipeline(
    name: str,
    version: str = "v0.1.0",
    versions_dir: str = ".flowyml/versions"
)
```

**Methods**:
- `save_version(metadata: Optional[Dict] = None)` - Save current version
- `list_versions() -> List[str]` - List all saved versions
- `get_version(version: str) -> PipelineVersion` - Get version details
- `compare_with(other_version: str) -> Dict` - Compare with another version
- `display_comparison(other_version: str)` - Pretty print comparison
- `run(*args, **kwargs)` - Run the pipeline (inherited from Pipeline)

### PipelineVersion

**Attributes**:
- `version: str` - Version identifier
- `pipeline_name: str` - Pipeline name
- `created_at: str` - Creation timestamp
- `steps: List[str]` - List of step names
- `step_hashes: Dict[str, str]` - Step content hashes
- `context_params: Dict` - Context parameters
- `metadata: Dict` - Custom metadata
