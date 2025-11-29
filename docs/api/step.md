# Step API 👣

Steps are the building blocks of flowyml pipelines.

## Usage

```python
from flowyml import step

@step(cache=True)
def my_step(data):
    return process(data)
```

## Decorator `@step`

::: flowyml.core.step.step
    options:
        show_root_heading: false

## Class `Step`

::: flowyml.core.step.Step
    options:
        show_root_heading: false
