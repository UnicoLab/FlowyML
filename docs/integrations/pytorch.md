# PyTorch Integration 🔥

Dynamic neural networks, orchestrated by UniFlow.

> [!NOTE]
> **What you'll learn**: How to manage PyTorch training loops and models
>
> **Key insight**: UniFlow handles the artifacts so you can focus on the gradients.

## Why PyTorch + UniFlow?

- **Custom Materializers**: Save/load models and DataLoaders automatically.
- **Reproducibility**: Track random seeds and hyperparameters.
- **Distributed Training**: Scale to multi-GPU easily.

## 🔥 Training Pattern

Wrap your training loop in a step.

```python
import torch
from uniflow import step

@step
def train(dataloader, model, epochs):
    optimizer = torch.optim.Adam(model.parameters())

    for epoch in range(epochs):
        for batch in dataloader:
            optimizer.zero_grad()
            loss = model(batch)
            loss.backward()
            optimizer.step()

    return model
```

## 💾 Saving Models

UniFlow automatically uses `torch.save` when you return a `nn.Module`.

```python
# In your materializer config (auto-detected usually)
# It saves state_dict or full model based on preference
```
