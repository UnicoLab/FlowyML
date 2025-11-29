# TensorFlow Integration 🤖

Production-grade TensorFlow pipelines.

> [!NOTE]
> **What you'll learn**: How to manage TF graphs and SavedModels
>
> **Key insight**: Enterprise-scale TF management.

## Why TensorFlow + flowyml?

- **SavedModel Support**: First-class support for TF SavedModel format.
- **TFX Compatibility**: Integrate with TFX components.
- **Serving**: Easy export to TensorFlow Serving.

## 🤖 Training Step

```python
import tensorflow as tf
from flowyml import step

@step
def train_tf_model(dataset):
    model = tf.keras.Sequential([...])

    # flowyml tracks this execution
    model.fit(dataset, epochs=5)

    return model
```

## 💾 Artifacts

flowyml saves TF models as `SavedModel` directories, preserving the graph and weights.
