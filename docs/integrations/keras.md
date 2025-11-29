# Keras Integration 🧠

Deep learning for humans, orchestrated by flowyml.

> [!NOTE]
> **What you'll learn**: How to track Keras training runs automatically
>
> **Key insight**: Add one callback, get full experiment tracking for free.

## Why Keras + flowyml?

- **Zero-Boilerplate Tracking**: No need to write `log_metric` loops.
- **Model Versioning**: Every `model.fit()` produces a versioned artifact.
- **Reproducibility**: Capture exact hyperparameters and architecture.

## 🧠 flowymlKerasCallback

The core of the integration is the `flowymlKerasCallback`. It automatically logs metrics, parameters, and model checkpoints during training.

### Real-World Pattern: Auto-Tracking

```python
import tensorflow as tf
from flowyml.integrations.keras import flowymlKerasCallback
from flowyml import step

@step
def train_model(x_train, y_train):
    model = tf.keras.Sequential([
        tf.keras.layers.Dense(128, activation='relu'),
        tf.keras.layers.Dense(10, activation='softmax')
    ])

    model.compile(optimizer='adam', loss='sparse_categorical_crossentropy')

    # Just add the callback!
    model.fit(
        x_train, y_train,
        epochs=10,
        callbacks=[
            flowymlKerasCallback(
                experiment_name="mnist_classifier",
                log_model=True  # Auto-save to artifact store
            )
        ]
    )

    return model
```

## 📦 Model Management

Models trained with the callback are automatically registered in flowyml's Model Registry.

```python
from flowyml import ModelRegistry

# Load the latest champion
registry = ModelRegistry()
model = registry.get_model("mnist_classifier", version="latest").load()
```
