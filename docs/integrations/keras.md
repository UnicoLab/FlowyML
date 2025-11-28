# Keras Integration 🧠

Deep learning for humans, orchestrated by UniFlow.

> [!NOTE]
> **What you'll learn**: How to track Keras training runs automatically
>
> **Key insight**: Add one callback, get full experiment tracking for free.

## Why Keras + UniFlow?

- **Zero-Boilerplate Tracking**: No need to write `log_metric` loops.
- **Model Versioning**: Every `model.fit()` produces a versioned artifact.
- **Reproducibility**: Capture exact hyperparameters and architecture.

## 🧠 UniFlowKerasCallback

The core of the integration is the `UniFlowKerasCallback`. It automatically logs metrics, parameters, and model checkpoints during training.

### Real-World Pattern: Auto-Tracking

```python
import tensorflow as tf
from uniflow.integrations.keras import UniFlowKerasCallback
from uniflow import step

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
            UniFlowKerasCallback(
                experiment_name="mnist_classifier",
                log_model=True  # Auto-save to artifact store
            )
        ]
    )

    return model
```

## 📦 Model Management

Models trained with the callback are automatically registered in UniFlow's Model Registry.

```python
from uniflow import ModelRegistry

# Load the latest champion
registry = ModelRegistry()
model = registry.get_model("mnist_classifier", version="latest").load()
```
