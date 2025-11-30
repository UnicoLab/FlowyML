# Keras Training History - Example

This notebook demonstrates how to use FlowyML's enhanced Keras callback to automatically track and visualize training history.

## Setup

```python
import numpy as np
from tensorflow import keras
from tensorflow.keras import layers
from flowyml.integrations.keras import FlowymlKerasCallback

# Generate synthetic data
def generate_data(samples=1000):
    X = np.random.randn(samples, 20)
    y = (X[:, 0] + X[:, 1] > 0).astype(int)
    return X, y

X_train, y_train = generate_data(1000)
X_val, y_val = generate_data(200)
```

## Create a Simple Model

```python
model = keras.Sequential([
    layers.Dense(64, activation='relu', input_shape=(20,)),
    layers.Dropout(0.3),
    layers.Dense(32, activation='relu'),
    layers.Dropout(0.3),
    layers.Dense(1, activation='sigmoid')
])

model.compile(
    optimizer='adam',
    loss='binary_crossentropy',
    metrics=['accuracy']
)
```

## Train with FlowyML Callback

```python
# Create the callback - that's all you need!
flowyml_callback = FlowymlKerasCallback(
    experiment_name="keras-demo",
    project="my-project",
    run_name="binary-classifier-v1",
    auto_log_history=True  # Automatically tracks training history
)

# Train the model
history = model.fit(
    X_train, y_train,
    validation_data=(X_val, y_val),
    epochs=50,
    batch_size=32,
    callbacks=[flowyml_callback],  # Add the callback
    verbose=1
)
```

## What Happens Automatically

The callback automatically:
1. ✅ **Tracks all metrics** per epoch (loss, accuracy, val_loss, val_accuracy)
2. ✅ **Saves model** with complete training history attached
3. ✅ **Logs to experiment** for comparison
4. ✅ **Captures model architecture** as artifact

## View in UI

1. Go to http://localhost:3000/projects/my-project
2. Navigate to **Structure** tab
3. Find your run and expand the tree
4. Click on the `model-binary-classifier-v1` artifact
5. **See beautiful training history graphs!**

## Advanced: Custom Metrics

```python
# Add custom metrics
import tensorflow.keras.backend as K

def f1_score(y_true, y_pred):
    true_positives = K.sum(K.round(K.clip(y_true * y_pred, 0, 1)))
    possible_positives = K.sum(K.round(K.clip(y_true, 0, 1)))
    predicted_positives = K.sum(K.round(K.clip(y_pred, 0, 1)))
    precision = true_positives / (predicted_positives + K.epsilon())
    recall = true_positives / (possible_positives + K.epsilon())
    return 2*((precision*recall)/(precision+recall+K.epsilon()))

model.compile(
    optimizer='adam',
    loss='binary_crossentropy',
    metrics=['accuracy', f1_score]  # Custom metric
)

flowyml_callback = FlowymlKerasCallback(
    experiment_name="keras-demo",
    project="my-project",
    auto_log_history=True
)

history = model.fit(
    X_train, y_train,
    validation_data=(X_val, y_val),
    epochs=50,
    callbacks=[flowyml_callback]
)

# The callback automatically captures your custom 'f1_score' metric too!
```

## Disable Auto-Logging (Optional)

If you need manual control:

```python
callback = FlowymlKerasCallback(
    experiment_name="keras-demo",
    project="my-project",
    auto_log_history=False  # Disable automatic history tracking
)
```

## What Gets Stored

The training_history field in the artifact metadata looks like:

```json
{
  "epochs": [1, 2, 3, ..., 50],
  "train_loss": [0.693, 0.612, 0.580, ...],
  "train_accuracy": [0.501, 0.625, 0.701, ...],
  "val_loss": [0.701, 0.625, 0.595, ...],
  "val_accuracy": [0.490, 0.615, 0.690, ...],
  "f1_score": [0.48, 0.61, 0.68, ...]  // Custom metrics included!
}
```

This format is automatically recognized by the FlowyML UI and rendered as interactive charts.

## Next Steps

- Try with your own datasets and models
- Compare multiple runs in the experiments view
- Use different optimizers and see the impact on training curves
- Share your training history visualizations with your team!
