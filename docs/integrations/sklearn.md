# Scikit-Learn Integration 🧠

Classic ML pipelines made robust and reproducible.

> [!NOTE]
> **What you'll learn**: How to version and deploy sklearn models
>
> **Key insight**: Turn your notebook scripts into production pipelines.

## Why Scikit-Learn + flowyml?

- **Pipeline Versioning**: Version the entire preprocessing + model chain.
- **Model Registry**: Promote the best Random Forest to production.
- **Easy Serving**: Deploy sklearn models as APIs.

## 🧠 Pipeline Pattern

Return a `sklearn.pipeline.Pipeline` object for automatic serialization.

```python
from sklearn.pipeline import Pipeline as SkPipeline
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from flowyml import step

@step
def build_pipeline():
    return SkPipeline([
        ('scaler', StandardScaler()),
        ('rf', RandomForestClassifier())
    ])

@step
def train(pipeline, X, y):
    pipeline.fit(X, y)
    return pipeline
```
