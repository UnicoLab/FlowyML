# Artifact Catalog

Centralized artifact discovery, versioning, tagging, and lineage tracking. Works in both local and remote deployments.

## Quick Start

```python
from flowyml import ArtifactCatalog

catalog = ArtifactCatalog()  # Auto-selects local or remote backend

# Register an artifact
artifact_id = catalog.register(
    name="fraud_detector_v2",
    artifact_type="Model",
    source_step="train_model",
    source_run_id="run-abc-123",
    source_pipeline="fraud_detection",
    tags={"stage": "staging", "team": "fraud"},
)

# Search and discover
models = catalog.search("fraud")
recent = catalog.list(artifact_type="Model", limit=10)

# Tag for promotion
catalog.tag(artifact_id, stage="production")

# Trace lineage
lineage = catalog.get_lineage(artifact_id)
print(lineage["parents"])   # What inputs produced this
print(lineage["children"])  # What downstream consumed this
```

## Backend Selection

The catalog auto-selects its backend:

| Condition | Backend | Storage |
|---|---|---|
| Default (no config) | `LocalCatalogBackend` | SQLite file (`.flowyml/catalog.db`) |
| Stack has `catalog_endpoint` | `RemoteCatalogBackend` | FlowyML API server |
| `FLOWYML_CATALOG_ENDPOINT` env var set | `RemoteCatalogBackend` | FlowyML API server |

### Local Development

Zero config — works out of the box:

```python
catalog = ArtifactCatalog()  # Uses local SQLite
```

### Remote/Production

Set via stack or environment:

```bash
export FLOWYML_CATALOG_ENDPOINT=https://flowyml.example.com/api/v1/catalog
export FLOWYML_CATALOG_API_KEY=your-api-key
```

### Explicit Backend

```python
from flowyml.storage.catalog import LocalCatalogBackend, RemoteCatalogBackend

# Force local
catalog = ArtifactCatalog(backend=LocalCatalogBackend("/path/to/db"))

# Force remote
catalog = ArtifactCatalog(backend=RemoteCatalogBackend("https://api.example.com"))
```

## Content-Hash Deduplication

Pass `data` to `register()` — the catalog computes a SHA-256 hash and warns if a duplicate exists:

```python
catalog.register(
    name="training_features",
    artifact_type="Dataset",
    data=my_dataframe,  # Content is hashed
)
```

## Lineage Tracking

Register parent→child relationships:

```python
# Register dataset
ds_id = catalog.register(name="features", artifact_type="Dataset")

# Register model with lineage
model_id = catalog.register(
    name="classifier",
    artifact_type="Model",
    parent_ids=[ds_id],  # Links to parent dataset
)

# Query lineage
lineage = catalog.get_lineage(model_id)
```
