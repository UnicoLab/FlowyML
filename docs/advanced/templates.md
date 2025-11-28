# Pipeline Templates 📋

Standardize your ML workflows with reusable templates. Define the "Golden Path" for your team.

> [!NOTE]
> **What you'll learn**: How to create reusable pipeline blueprints that enforce best practices
>
> **Key insight**: Don't copy-paste code. Use templates to ensure every project starts with the right structure, logging, and error handling.

## Why Templates Matter

**Without templates**:
- **Inconsistency**: Team A uses `pandas`, Team B uses `polars`, Team C writes raw SQL
- **Boilerplate**: Rewriting the same setup code for every new project
- **Maintenance nightmare**: Updating a best practice requires editing 50 repos

**With UniFlow templates**:
- **Standardization**: "Use the `training_template`" ensures everyone logs metrics the same way
- **Speed**: Start a new project in seconds, not hours
- **Governance**: Bake compliance checks into the base template

## 📋 Using Built-in Templates

UniFlow comes with several built-in templates for common ML patterns.

```python
from uniflow import create_from_template

# Create a standard training pipeline
pipeline = create_from_template(
    "ml_training",
    name="my_model_training",
    data_loader=my_loader,
    trainer=my_trainer,
    evaluator=my_evaluator
)
```

## 🛠 Creating Custom Templates

You can define your own templates by creating a function that returns a `Pipeline` object.

## Real-World Pattern: The "Golden Path" Template

Create a standard ETL pipeline that enforces your team's best practices (e.g., always validating data).

```python
from uniflow import Pipeline, step

def create_standard_etl(name, source_config, dest_config):
    """
    A template that enforces:
    1. Extraction
    2. Validation (Mandatory!)
    3. Loading
    """
    pipeline = Pipeline(name)

    @step
    def extract():
        return connect(source_config).read()

    @step
    def validate(data):
        # Enforce quality checks
        if data.null_count > 0:
            raise ValueError("Data quality check failed!")
        return data

    @step
    def load(data):
        connect(dest_config).write(data)

    pipeline.add_step(extract)
    pipeline.add_step(validate)
    pipeline.add_step(load)

    return pipeline
```

## 📦 Sharing Templates

Templates can be shared as Python packages or modules. This is excellent for platform teams who want to provide "golden paths" for data scientists.

```python
# In your internal library
from my_company.templates import standard_training_pipeline

pipeline = standard_training_pipeline(
    model_type="xgboost",
    target="churn"
)
```
