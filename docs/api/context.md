# Context API 🧠

Access runtime information, parameters, and configuration within a step.

## Usage

```python
from flowyml import step, get_context

@step
def my_step():
    ctx = get_context()
    print(f"Running in pipeline: {ctx.pipeline_name}")
```

## Class `Context`

::: flowyml.core.context.Context
    options:
        show_root_heading: false
