# Scikit-Learn Integration 🧠

Classic ML pipelines made robust and reproducible.

> [!NOTE]
> **What you'll learn**: How to version and deploy sklearn models with automatic metadata extraction
>
> **Key insight**: Turn your notebook scripts into production pipelines with full hyperparameter tracking.

## Why Scikit-Learn + flowyml?

- **Auto-Extracted Metadata**: Hyperparameters, feature importance, coefficients—all captured automatically.
- **Pipeline Versioning**: Version the entire preprocessing + model chain.
- **Model Registry**: Promote the best Random Forest to production.
- **Easy Serving**: Deploy sklearn models as APIs.

## 🎯 Model.from_sklearn() Convenience Method

The easiest way to create Model assets with full metadata extraction:

```python
from sklearn.ensemble import RandomForestClassifier
from flowyml import Model

# Train your model
rf = RandomForestClassifier(n_estimators=100, max_depth=10)
rf.fit(X_train, y_train)

# 🎯 Use convenience method for full extraction
model_asset = Model.from_sklearn(
    rf,
    name="random_forest_classifier",
)

# Access auto-extracted properties
print(f"Framework: {model_asset.framework}")  # 'sklearn'
print(f"Class: {model_asset.metadata.properties.get('model_class')}")  # 'RandomForestClassifier'
print(f"Is Fitted: {model_asset.metadata.properties.get('is_fitted')}")  # True

# Hyperparameters auto-extracted!
print(f"Hyperparameters: {model_asset.hyperparameters}")
# {'n_estimators': 100, 'max_depth': 10, 'criterion': 'gini', ...}

# Feature importance (for tree-based models)
print(f"Has Feature Importance: {model_asset.metadata.properties.get('has_feature_importances')}")
print(f"Num Features: {model_asset.metadata.properties.get('num_features')}")
```

## 🧠 Pipeline Pattern

Return a `sklearn.pipeline.Pipeline` object for automatic serialization:

```python
from sklearn.pipeline import Pipeline as SkPipeline
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from flowyml import step, Model

@step
def build_pipeline():
    return SkPipeline([
        ('scaler', StandardScaler()),
        ('rf', RandomForestClassifier(n_estimators=100))
    ])

@step
def train(pipeline, X, y):
    pipeline.fit(X, y)

    # Return a Model asset with auto-extracted metadata
    return Model.from_sklearn(
        pipeline,
        name="trained_pipeline",
    )
```

## 🔧 Auto-Extracted Properties

The following properties are automatically extracted from sklearn models:

| Property | Description |
|----------|-------------|
| `framework` | Always `'sklearn'` |
| `model_class` | Class name (RandomForestClassifier, etc.) |
| `architecture` | Same as model_class |
| `hyperparameters` | All model hyperparameters |
| `is_fitted` | Whether model has been fitted |
| `has_feature_importances` | True for tree-based models |
| `num_features` | Number of features (if fitted) |
| `n_features_in` | Number of input features |
| `n_estimators` | For ensemble models |
| `num_estimators_fitted` | Actual estimators fitted |
| `max_depth` | For tree-based models |
| `num_classes` | For classifiers |
| `classes` | Class labels (for classifiers) |
| `coef_shape` | Coefficient shape (for linear models) |
| `intercept` | Intercept (for linear models) |

## 🌳 Supported Model Types

Full auto-extraction works for all sklearn estimators:

- **Classifiers**: RandomForest, GradientBoosting, SVM, LogisticRegression, etc.
- **Regressors**: RandomForest, Ridge, Lasso, ElasticNet, etc.
- **Transformers**: StandardScaler, PCA, etc.
- **Ensembles**: VotingClassifier, StackingClassifier, etc.
- **Pipelines**: sklearn.pipeline.Pipeline
