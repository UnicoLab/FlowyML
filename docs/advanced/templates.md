# 📋 Pipeline Templates

!!! info "What you'll learn"
    How to create reusable pipeline blueprints that enforce best practices. Don't copy-paste code — use templates so every project starts right.

Standardize your ML workflows with reusable templates. Define the "Golden Path" for your team and eliminate boilerplate.

---

## Why Templates Matter

| Without Templates | With Templates |
|---|---|
| Inconsistency across teams | Standardized pipeline structure |
| Rewriting setup code for every project | Start a new project in seconds |
| Updating a best practice requires editing 50 repos | Update the template once |
| No governance | Bake compliance checks into the blueprint |

---

## 📋 Using Built-in Templates

FlowyML comes with several built-in templates for common ML patterns:

```python
from flowyml import create_from_template, list_templates

# See what's available
for name, info in list_templates().items():
    print(f"  {name}: {info['description']}")

# Create a standard training pipeline from template
pipeline = create_from_template(
    "ml_training",
    name="my_model_training",
    data_loader=my_loader,
    trainer=my_trainer,
    evaluator=my_evaluator,
)
pipeline.run()
```

### Available Templates

| Template | Description | Steps Included |
|---|---|---|
| `ml_training` | Standard ML training pipeline | Load → Preprocess → Train → Evaluate → Log |
| `etl` | Extract-Transform-Load pipeline | Extract → Validate → Transform → Load |
| `inference` | Batch inference pipeline | Load Model → Load Data → Predict → Save |

---

## 🛠 Creating Custom Templates

Templates are just functions that build and return a `Pipeline`:

```python
from flowyml import Pipeline, step

def create_standard_etl(name: str, source_config: dict, dest_config: dict) -> Pipeline:
    """
    Golden Path ETL template — enforces:
    1. Extraction from source
    2. Mandatory validation
    3. Transformation
    4. Loading to destination
    """
    pipeline = Pipeline(name)

    @step(outputs=["raw_data"])
    def extract():
        return connect(source_config).read()

    @step(inputs=["raw_data"], outputs=["validated_data"])
    def validate(raw_data):
        if raw_data.isnull().sum().sum() > 0:
            raise ValueError("Data quality check failed: null values detected!")
        return raw_data

    @step(inputs=["validated_data"], outputs=["transformed_data"])
    def transform(validated_data):
        return apply_transformations(validated_data)

    @step(inputs=["transformed_data"])
    def load(transformed_data):
        connect(dest_config).write(transformed_data)

    pipeline.add_step(extract)
    pipeline.add_step(validate)
    pipeline.add_step(transform)
    pipeline.add_step(load)

    return pipeline

# Usage
pipeline = create_standard_etl(
    "daily_etl",
    source_config={"type": "postgres", "table": "events"},
    dest_config={"type": "bigquery", "dataset": "analytics"},
)
pipeline.run()
```

---

## Real-World Example: ML Training Template

```python
from flowyml import Pipeline, step, approval

def create_training_template(
    name: str,
    model_type: str = "xgboost",
    require_approval: bool = True,
) -> Pipeline:
    """Company-standard ML training pipeline."""
    pipeline = Pipeline(name)

    @step(outputs=["features", "target"])
    def load_and_split():
        data = load_latest_data()
        return data.drop("target"), data["target"]

    @step(outputs=["model"])
    def train(features, target):
        model = get_model(model_type)
        model.fit(features, target)
        return model

    @step(outputs=["metrics"])
    def evaluate(model, features, target):
        preds = model.predict(features)
        return compute_metrics(target, preds)

    pipeline.add_step(load_and_split)
    pipeline.add_step(train)
    pipeline.add_step(evaluate)

    if require_approval:
        pipeline.add_step(approval(
            name="deployment_gate",
            approver="ml-team",
        ))

    return pipeline
```

---

## 📦 Sharing Templates

Distribute templates as Python packages for your organization:

```python
# my_company/ml_templates/__init__.py

from .training import create_training_template
from .etl import create_standard_etl
from .inference import create_batch_inference

__all__ = [
    "create_training_template",
    "create_standard_etl",
    "create_batch_inference",
]
```

```python
# Usage in any project
from my_company.ml_templates import create_training_template

pipeline = create_training_template(
    "churn_model",
    model_type="xgboost",
    require_approval=True,
)
```

---

## Best Practices

!!! tip "Templates as governance"
    Bake compliance checks (data validation, bias auditing) into templates. If it's in the template, every project gets it for free.

!!! tip "Keep templates configurable"
    Accept model type, data source, and feature engineering as parameters. Don't hardcode — make templates flexible enough for different use cases.

!!! warning "Version your templates"
    When you update a template, existing pipelines don't automatically update. Use semantic versioning for your template package.
