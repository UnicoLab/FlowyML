# Pipeline Templates 📋

Templates allow you to define reusable pipeline structures that can be instantiated with different parameters or step implementations. This promotes standardization and reduces code duplication across teams.

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

```python
from uniflow import Pipeline

def create_etl_pipeline(name, source, destination):
    pipeline = Pipeline(name)

    @step
    def extract():
        return source.read()

    @step
    def transform(data):
        return data.clean()

    @step
    def load(data):
        destination.write(data)

    pipeline.add_step(extract)
    pipeline.add_step(transform)
    pipeline.add_step(load)

    return pipeline

# Instantiate
pipeline = create_etl_pipeline(
    "daily_etl",
    source=PostgresSource(...),
    destination=S3Destination(...)
)
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
