# Keras Integration 🧠

Deep learning for humans, orchestrated by flowyml.

> [!NOTE]
> **What you'll learn**: How to track Keras training runs automatically with zero boilerplate
>
> **Key insight**: Add one callback, get full experiment tracking, training history visualization, and auto-extracted model metadata for free.

## Why Keras + flowyml?

- **Zero-Boilerplate Tracking**: No need to write `log_metric` loops.
- **Auto-Extracted Metadata**: Framework, parameters, layers, optimizer—all captured automatically.
- **Training History Visualization**: Interactive charts in the UI for loss, accuracy, and all metrics.
- **Model Versioning**: Every `model.fit()` produces a versioned artifact.
- **Reproducibility**: Capture exact hyperparameters and architecture.

## 🧠 FlowymlKerasCallback

The core of the integration is the `FlowymlKerasCallback`. It automatically logs metrics, parameters, and model checkpoints during training.

### Real-World Pattern: Auto-Tracking

```python
import keras
from flowyml.integrations.keras import FlowymlKerasCallback
from flowyml import step, Model

@step
def train_model(x_train, y_train):
    model = keras.Sequential([
        keras.layers.Dense(128, activation='relu'),
        keras.layers.Dense(10, activation='softmax')
    ])

    model.compile(
        optimizer='adam',
        loss='sparse_categorical_crossentropy',
        metrics=['accuracy']  # All metrics automatically tracked!
    )

    # Just add the callback!
    callback = FlowymlKerasCallback(
        experiment_name="mnist_classifier",
        log_model=True  # Auto-save to artifact store
    )

    model.fit(
        x_train, y_train,
        epochs=10,
        callbacks=[callback]
    )

    # 🎯 Use convenience method for full extraction
    return Model.from_keras(
        model,
        name="mnist_classifier",
        callback=callback,  # Auto-extracts training_history!
    )
```

## 🎯 Model.from_keras() Convenience Method

The `Model.from_keras()` method provides the easiest way to create Model assets with full metadata extraction:

```python
from flowyml import Model
from flowyml.integrations.keras import FlowymlKerasCallback

# Train with callback
callback = FlowymlKerasCallback(experiment_name="demo")
model.fit(X, y, callbacks=[callback])

# Create asset with full auto-extraction
model_asset = Model.from_keras(
    model,
    name="my_model",
    callback=callback,  # Training history auto-extracted!
    # Additional custom properties (optional)
    custom_param="value",
)

# Access auto-extracted properties
print(f"Framework: {model_asset.framework}")  # 'keras'
print(f"Parameters: {model_asset.parameters:,}")  # Total param count
print(f"Layers: {model_asset.num_layers}")
print(f"Layer Types: {model_asset.layer_types}")  # ['Dense', 'Dropout', ...]
print(f"Optimizer: {model_asset.optimizer}")  # 'Adam'
print(f"Learning Rate: {model_asset.learning_rate}")
print(f"Loss Function: {model_asset.loss_function}")  # 'mse'
print(f"Metrics: {model_asset.metrics}")  # ['loss', 'accuracy']

# Training info from callback
training_info = model_asset.get_training_info()
print(f"Epochs Trained: {training_info['epochs_trained']}")
print(f"Final Loss: {training_info['final_train_loss']:.4f}")
print(f"Final Val Loss: {training_info['final_val_loss']:.4f}")
```

## 📊 Training History Visualization

When you use `FlowymlKerasCallback`, your training history is automatically visualized in the FlowyML UI:

- **Interactive charts** for loss, accuracy, and all compiled metrics
- **Per-epoch values** with hover tooltips
- **Log/linear scale toggle** for better visualization
- **Show/hide individual metrics** by clicking the legend
- **Zoom and pan** for detailed analysis

All metrics passed to `model.compile(metrics=[...])` are automatically captured—no configuration needed!

## 📦 Model Management

Models trained with the callback are automatically registered in flowyml's Model Registry.

```python
from flowyml import ModelRegistry

# Load the latest champion
registry = ModelRegistry()
model = registry.get_model("mnist_classifier", version="latest").load()
```

## 🔧 Auto-Extracted Properties

The following properties are automatically extracted from Keras models:

| Property | Description |
|----------|-------------|
| `framework` | Always `'keras'` |
| `parameters` | Total parameter count |
| `trainable_parameters` | Trainable parameters |
| `architecture` | Model name |
| `model_class` | Class name (Sequential, Functional, etc.) |
| `num_layers` | Number of layers |
| `layer_types` | List of layer types |
| `input_shape` | Model input shape |
| `output_shape` | Model output shape |
| `optimizer` | Optimizer name (Adam, SGD, etc.) |
| `learning_rate` | Learning rate value |
| `loss_function` | Loss function name |
| `metrics` | List of compiled metrics |
| `is_compiled` | Whether model is compiled |
| `is_built` | Whether model is built |
