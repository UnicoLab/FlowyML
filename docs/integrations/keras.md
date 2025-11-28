# Keras Integration

UniFlow provides seamless integration with Keras and TensorFlow, offering automatic experiment tracking, model versioning, and artifact management.

## 🧠 UniFlowKerasCallback

The core of the integration is the `UniFlowKerasCallback`. It automatically logs metrics, parameters, and model checkpoints during training.

### Basic Usage

```python
import tensorflow as tf
from uniflow.integrations.keras import UniFlowKerasCallback

# Define model
model = tf.keras.Sequential([
    tf.keras.layers.Dense(10, input_shape=(5,))
])
model.compile(optimizer='adam', loss='mse')

# Train with callback
model.fit(
    x_train, y_train,
    epochs=10,
    callbacks=[
        UniFlowKerasCallback(
            experiment_name="keras_demo",
            log_model=True
        )
    ]
)
```

### Features

- **Metric Logging**: Automatically logs `loss`, `accuracy`, and any other metrics defined in `compile()`.
- **Parameter Logging**: Logs `epochs`, `batch_size`, `optimizer` config, and model architecture.
- **Model Checkpointing**: Saves the model to the artifact store at the end of training or every epoch.
- **TensorBoard Support**: Compatible with standard TensorBoard logging.

## 📦 Model Management

Models trained with the callback are automatically registered in UniFlow's Model Registry.

```python
from uniflow import ModelRegistry

registry = ModelRegistry()
model_artifact = registry.get_model("keras_demo", version="latest")

# Load the model back
loaded_model = model_artifact.load()
```
