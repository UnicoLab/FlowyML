# PyTorch Integration 🔥

Dynamic neural networks, orchestrated by flowyml.

> [!NOTE]
> **What you'll learn**: How to manage PyTorch training loops and models with automatic metadata extraction
>
> **Key insight**: flowyml automatically extracts model architecture, parameters, and device info so you can focus on the gradients.

## Why PyTorch + flowyml?

- **Auto-Extracted Metadata**: Parameters, layers, device, dtype—all captured automatically.
- **Custom Materializers**: Save/load models and DataLoaders automatically.
- **Reproducibility**: Track random seeds and hyperparameters.
- **Distributed Training**: Scale to multi-GPU easily.

## 🎯 Model.from_pytorch() Convenience Method

The easiest way to create Model assets with full metadata extraction:

```python
import torch
import torch.nn as nn
from flowyml import Model

class MyNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc1 = nn.Linear(10, 64)
        self.fc2 = nn.Linear(64, 1)

    def forward(self, x):
        x = torch.relu(self.fc1(x))
        return self.fc2(x)

model = MyNet()

# 🎯 Use convenience method for full extraction
model_asset = Model.from_pytorch(
    model,
    name="my_model",
    # Optional: pass training history if you tracked it manually
    training_history={"epochs": [1,2,3], "loss": [0.5, 0.3, 0.1]},
)

# Access auto-extracted properties
print(f"Framework: {model_asset.framework}")  # 'pytorch'
print(f"Parameters: {model_asset.parameters:,}")  # Total param count
print(f"Trainable: {model_asset.trainable_parameters:,}")
print(f"Layers: {model_asset.num_layers}")
print(f"Layer Types: {model_asset.layer_types}")  # ['Linear', 'ReLU', ...]
print(f"Device: {model_asset.metadata.properties.get('device')}")  # 'cpu' or 'cuda:0'
print(f"Training Mode: {model_asset.metadata.properties.get('training_mode')}")
```

## 🔥 Training Pattern

Wrap your training loop in a step and return a Model asset:

```python
import torch
from flowyml import step, Model

@step
def train(dataloader, model, epochs):
    optimizer = torch.optim.Adam(model.parameters())
    history = {"epochs": [], "train_loss": []}

    for epoch in range(epochs):
        epoch_loss = 0
        for batch in dataloader:
            optimizer.zero_grad()
            loss = model(batch)
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item()

        history["epochs"].append(epoch + 1)
        history["train_loss"].append(epoch_loss / len(dataloader))

    # Return a Model asset with auto-extracted metadata
    return Model.from_pytorch(
        model,
        name="trained_model",
        training_history=history,
    )
```

## 💾 Saving Models

flowyml automatically uses `torch.save` when you return a `nn.Module`.

```python
# In your materializer config (auto-detected usually)
# It saves state_dict or full model based on preference
```

## 🔧 Auto-Extracted Properties

The following properties are automatically extracted from PyTorch models:

| Property | Description |
|----------|-------------|
| `framework` | Always `'pytorch'` |
| `parameters` | Total parameter count |
| `trainable_parameters` | Parameters with `requires_grad=True` |
| `frozen_parameters` | Parameters with `requires_grad=False` |
| `architecture` | Model class name |
| `model_class` | Class name |
| `num_layers` | Number of modules |
| `layer_types` | List of module types |
| `num_tensors` | Number of tensors in state_dict |
| `tensor_shapes_sample` | Sample of tensor shapes |
| `training_mode` | True if `model.training` |
| `device` | Device (cpu, cuda:0, etc.) |
| `dtype` | Data type (torch.float32, etc.) |
