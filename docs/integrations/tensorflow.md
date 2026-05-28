---
title: TensorFlow Integration — FlowyML
description: "Integrate TensorFlow and tf.keras models with SavedModel support, auto-properties, and production-ready serving."
---

<div class="hero-section" markdown>

## 📈 TensorFlow Integration

Integrate TensorFlow and tf.keras models with SavedModel support, auto-properties, and production-ready serving.

<span class="feature-badge">💾 SavedModel</span>
<span class="feature-badge">🔄 Auto-Properties</span>
<span class="feature-badge">🚀 TF Serving</span>

</div>

# 🤖 TensorFlow Integration

!!! info "What you'll learn"
    How to manage TensorFlow models, graphs, and SavedModels with FlowyML's enterprise-scale pipeline infrastructure.

Production-grade TensorFlow pipelines with automatic artifact tracking, model versioning, and SavedModel support.

---

## Why TensorFlow + FlowyML?

| Feature | Benefit |
|---|---|
| **SavedModel Support** | First-class TF SavedModel format handling |
| **TFX Compatibility** | Integrate with TFX components |
| **Serving** | Easy export to TensorFlow Serving |
| **GPU Management** | Automatic GPU allocation via FlowyML resources |

---

## 🤖 Training Step

```python
import tensorflow as tf
from flowyml import step

@step(outputs=["model"])
def train_tf_model(dataset):
    model = tf.keras.Sequential([
        tf.keras.layers.Dense(128, activation="relu"),
        tf.keras.layers.Dropout(0.2),
        tf.keras.layers.Dense(10, activation="softmax"),
    ])

    model.compile(
        optimizer="adam",
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )

    # FlowyML tracks this execution
    history = model.fit(dataset["x_train"], dataset["y_train"], epochs=10, validation_split=0.2)

    return model
```

---

## 💾 SavedModel Artifacts

FlowyML saves TF models as `SavedModel` directories, preserving the graph, weights, and signatures:

```python
@step(outputs=["model_path"])
def export_model(model):
    path = "/tmp/my_model"
    model.save(path)  # SavedModel format
    return path

@step
def load_and_predict(model_path, test_data):
    model = tf.keras.models.load_model(model_path)
    predictions = model.predict(test_data)
    return predictions
```

---

## 📊 Logging Training History

Capture and log Keras training metrics:

```python
@step(outputs=["model", "metrics"])
def train_with_metrics(data):
    model = build_model()
    history = model.fit(data["x"], data["y"], epochs=20, validation_split=0.2)

    metrics = {
        "final_accuracy": history.history["accuracy"][-1],
        "final_val_accuracy": history.history["val_accuracy"][-1],
        "final_loss": history.history["loss"][-1],
    }

    return model, metrics
```

---

## 🚀 TensorFlow Serving Export

Export models in a format ready for TF Serving:

```python
@step
def export_for_serving(model, version: int = 1):
    export_path = f"/models/my_model/{version}"
    tf.saved_model.save(model, export_path)
    print(f"Model exported to {export_path}")
```

---

## Best Practices

!!! tip "Use mixed precision"
    Enable `tf.keras.mixed_precision.set_global_policy('mixed_float16')` for faster GPU training.

!!! tip "SavedModel over HDF5"
    Always use `model.save("path/")` (SavedModel) instead of `model.save("model.h5")` — SavedModel is the standard and preserves custom layers.

!!! warning "Memory management"
    Use `tf.config.experimental.set_memory_growth(gpu, True)` to avoid TF allocating all GPU memory upfront.

---

## 🚀 What's Next?

<div class="header-grid" markdown>

<div class="header-card" markdown>

### 🧠 Keras Integration
Use the FlowyML Keras callback for automatic training history tracking and visualization.

[Explore →](keras.md)

</div>

<div class="header-card" markdown>

### 🔥 PyTorch Integration
Integrate PyTorch models with auto-extracted metadata and state dict handling.

[Learn more →](pytorch.md)

</div>

<div class="header-card" markdown>

### 🚀 Deployment
Deploy your TensorFlow models to production with FlowyML's deployment tools.

[View Guide →](../deployment.md)

</div>

</div>
