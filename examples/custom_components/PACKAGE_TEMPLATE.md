# Custom Component Package Template

This is a template for creating a flowyml component package.

## Structure

```
my-flowyml-components/
├── pyproject.toml
├── README.md
├── LICENSE
└── my_flowyml_components/
    ├── __init__.py
    ├── my_orchestrator.py
    └── my_artifact_store.py
```

## pyproject.toml

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "my-flowyml-components"
version = "0.1.0"
description = "Custom flowyml components"
authors = [{name = "Your Name", email = "you@example.com"}]
dependencies = [
    "flowyml>=0.1.0",
    # Your dependencies
]

# Register components via entry points
[project.entry-points."flowyml.stack_components"]
my_orchestrator = "my_flowyml_components.my_orchestrator:MyOrchestrator"
my_store = "my_flowyml_components.my_artifact_store:MyArtifactStore"
```

## Component Example

```python
# my_flowyml_components/my_orchestrator.py
from flowyml.stacks.components import Orchestrator
from flowyml.stacks.plugins import register_component

@register_component
class MyOrchestrator(Orchestrator):
    """My custom orchestrator."""

    def __init__(self, name="my_orch", **kwargs):
        super().__init__(name)
        # Your init

    def validate(self) -> bool:
        return True

    def run_pipeline(self, pipeline, **kwargs):
        # Your logic
        return "run_id"

    def get_run_status(self, run_id: str) -> str:
        return "SUCCESS"

    def to_dict(self):
        return {"type": "my_orchestrator"}
```

## Installation

```bash
# Development
pip install -e .

# From PyPI (after publishing)
pip install my-flowyml-components
```

## Usage

Components are auto-discovered after installation:

```yaml
# flowyml.yaml
stacks:
  my_stack:
    orchestrator:
      type: my_orchestrator
      # Your config
```

```bash
flowyml component list
# Will show: my_orchestrator, my_store
```

## Testing

```python
# tests/test_components.py
import unittest
from my_flowyml_components import MyOrchestrator

class TestMyOrchestrator(unittest.TestCase):
    def test_validate(self):
        orch = MyOrchestrator()
        self.assertTrue(orch.validate())
```

## Publishing

1. Build package:
```bash
python -m build
```

2. Upload to PyPI:
```bash
python -m twine upload dist/*
```

3. Users install:
```bash
pip install my-flowyml-components
```

4. Auto-available in flowyml!

## Community

Share your components:
- Create GitHub repo
- Add to flowyml community registry
- Tag with `flowyml-plugin`
