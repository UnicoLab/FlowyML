# Projects & Multi-Tenancy 🏢

Organize pipelines, runs, and artifacts into isolated projects for multi-tenant deployments.

## Overview ℹ️

The `Project` and `ProjectManager` classes provide:
- **Isolation**: Each project has its own metadata store and artifact storage
- **Organization**: Group related pipelines and runs together
- **Multi-tenancy**: Support multiple teams/clients in one deployment
- **Resource management**: Track pipelines, runs, and artifacts per project

## Quick Start 🚀

```python
from flowyml import Project

# Create a project
project = Project("recommendation_system")

# Create pipelines within the project
pipeline = project.create_pipeline("training_v1")

# Add steps and run
pipeline.add_step(load_data)
pipeline.add_step(train_model)
result = pipeline.run()

# Get project statistics
stats = project.get_stats()
print(f"Total runs: {stats['total_runs']}")
print(f"Total artifacts: {stats['total_artifacts']}")
```

## Project Management 🏗️

### Creating Projects

```python
from flowyml import ProjectManager

manager = ProjectManager()

# Create a new project
project = manager.create_project(
    "ml_platform",
    description="Main ML platform for product recommendations"
)

# List all projects
projects = manager.list_projects()
for proj in projects:
    print(f"- {proj['name']}: {proj['description']}")

# Get existing project
project = manager.get_project("ml_platform")
```

### Project Structure

Each project has its own directory structure:

```
projects/
└── my_project/
    ├── project.json          # Project metadata
    ├── runs/                 # Pipeline run data
    ├── artifacts/            # Stored artifacts
    │   └── cache/           # Artifact cache
    └── metadata.db          # SQLite metadata store
```

## Working with Projects 🛠️

### Creating Pipelines

```python
project = Project("analytics")

# Create multiple pipelines
etl_pipeline = project.create_pipeline("daily_etl")
reporting_pipeline = project.create_pipeline("weekly_reports")
ml_pipeline = project.create_pipeline("model_training")

# Each pipeline uses the project's metadata store
etl_pipeline.add_step(extract_data)
etl_pipeline.run()
```

### Querying Project Data

```python
# List all runs in the project
runs = project.list_runs()
for run in runs:
    print(f"{run['pipeline_name']}: {run['status']}")

# Filter runs by pipeline
training_runs = project.list_runs(pipeline_name="model_training")

# Get artifacts
artifacts = project.get_artifacts()
for artifact in artifacts:
    print(f"{artifact['name']}: {artifact['type']}")

# Filter by artifact type
models = project.get_artifacts(artifact_type="model")
```

### Project Statistics

```python
stats = project.get_stats()

print(f"""
Project: {project.name}
Created: {stats['created_at']}
Pipelines: {stats['total_pipelines']}
Runs: {stats['total_runs']}
Artifacts: {stats['total_artifacts']}
""")
```

## Multi-Tenant Architecture 🏘️

### Isolating Client Data

```python
# Setup for multiple clients
clients = ["acme_corp", "tech_startup", "enterprise_inc"]

for client in clients:
    # Each client gets their own project
    project = manager.create_project(
        client,
        description=f"ML pipelines for {client}"
    )

    # Create client-specific pipelines
    pipeline = project.create_pipeline("recommendation_engine")
    pipeline.add_step(load_client_data)  # Client-specific data
    pipeline.add_step(train_model)

    # Run in isolation
    result = pipeline.run()
```

### Resource Tracking

```python
def get_client_usage(client_name):
    project = manager.get_project(client_name)
    stats = project.get_stats()

    return {
        "client": client_name,
        "pipelines": stats['total_pipelines'],
        "runs": stats['total_runs'],
        "artifacts": stats['total_artifacts'],
        "storage_usage_mb": project.get_storage_usage()
    }

# Generate usage report
for client in clients:
    usage = get_client_usage(client)
    print(f"{client}: {usage['runs']} runs, {usage['storage_usage_mb']}MB")
```

## Best Practices 💡

### 1. Project Naming

```python
# Use descriptive, hierarchical names
project = Project("company_product_ml")

# Or organize by team/domain
project = Project("data_team_recommendations")
```

### 2. Pipeline Organization

```python
project = Project("sales_analytics")

# Group related pipelines
project.create_pipeline("etl_daily")
project.create_pipeline("etl_weekly")
project.create_pipeline("reporting_dashboard")
project.create_pipeline("forecasting_model")
```

### 3. Cleanup Old Data

```python
# Export project before cleanup
project.export_metadata("backup.json")

# List pipelines for review
pipelines = project.get_pipelines()

# Remove if needed (use with caution!)
# manager.delete_project("old_project", confirm=True)
```

## Integration Examples 🔌

### With Versioning

```python
from flowyml import VersionedPipeline

project = Project("ml_prod")

# Create versioned pipeline within project
pipeline = project.create_pipeline("training")
versioned = VersionedPipeline("training")
versioned.version = "v1.0.0"

# Use project's storage
versioned.runs_dir = project.runs_dir
versioned.metadata_store = project.metadata_store

versioned.add_step(train)
versioned.save_version()
versioned.run()
```

### With Scheduling

```python
from flowyml import PipelineScheduler

project = Project("automated_ml")
scheduler = PipelineScheduler()

def run_project_pipeline():
    pipeline = project.create_pipeline("daily_training")
    pipeline.add_step(train_model)
    return pipeline.run()

scheduler.schedule_daily(
    name=f"{project.name}_daily_run",
    pipeline_func=run_project_pipeline,
    hour=2
)
```

## API Reference 📚

### Project

**Constructor**:
```python
Project(
    name: str,
    description: str = "",
    projects_dir: str = ".flowyml/projects"
)
```

**Methods**:
- `create_pipeline(name: str, **kwargs) -> Pipeline` - Create pipeline in project
- `get_pipelines() -> List[str]` - List all pipeline names
- `list_runs(pipeline_name: Optional[str] = None, limit: int = 100) -> List[Dict]`
- `get_artifacts(artifact_type: Optional[str] = None, limit: int = 100) -> List[Dict]`
- `get_stats() -> Dict` - Get project statistics
- `export_metadata(path: str)` - Export project metadata

### ProjectManager

**Methods**:
- `create_project(name: str, description: str = "") -> Project` - Create new project
- `get_project(name: str) -> Optional[Project]` - Get existing project
- `list_projects() -> List[Dict]` - List all projects
- `delete_project(name: str, confirm: bool = False)` - Delete project

## FAQ ❓

**Q: Can I move a pipeline from one project to another?**
A: Currently, pipelines are tied to their project's metadata store. You would need to export/import the pipeline definition manually.

**Q: How do I backup a project?**
A: Use `project.export_metadata()` and copy the entire project directory from `.flowyml/projects/{project_name}/`.

**Q: What happens when I delete a project?**
A: All pipelines, runs, and artifacts associated with the project are removed. Always export metadata first!

**Q: Can projects share artifacts?**
A: No, projects are fully isolated by design. This ensures multi-tenant security and resource tracking.
