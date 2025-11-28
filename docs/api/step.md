# Step API 👣

Steps are the building blocks of UniFlow pipelines.

## Usage

```python
from uniflow import step

@step(cache=True)
def my_step(data):
    return process(data)
```

## Decorator `@step`

::: uniflow.core.step.step
    options:
        show_root_heading: false

## Class `Step`

::: uniflow.core.step.Step
    options:
        show_root_heading: false
