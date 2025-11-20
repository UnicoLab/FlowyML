"""Project initialization CLI commands."""

from pathlib import Path
from typing import Optional


TEMPLATES = {
    "basic": {
        "description": "Basic Flowy project structure",
        "files": {
            "pipelines/__init__.py": "",
            "pipelines/training_pipeline.py": """\"\"\"Example training pipeline.\"\"\"

from flowy import Pipeline, step, context

# Define context
ctx = context(
    learning_rate=0.001,
    batch_size=32,
    epochs=10
)


@step(outputs=["data/processed"])
def load_data():
    \"\"\"Load and preprocess data.\"\"\"
    # Your data loading logic here
    print("Loading data...")
    data = {"samples": 1000, "features": 10}
    return data


@step(inputs=["data/processed"], outputs=["model/trained"])
def train_model(data, learning_rate, epochs):
    \"\"\"Train the model.\"\"\"
    print(f"Training model with lr={learning_rate}, epochs={epochs}")
    # Your training logic here
    model = {"accuracy": 0.95, "loss": 0.05}
    return model


@step(inputs=["model/trained"], outputs=["metrics/evaluation"])
def evaluate_model(model):
    \"\"\"Evaluate the trained model.\"\"\"
    print("Evaluating model...")
    metrics = {"test_accuracy": 0.93, "test_loss": 0.07}
    return metrics


# Create pipeline
def create_pipeline():
    pipeline = Pipeline("training_pipeline", context=ctx)
    pipeline.add_step(load_data)
    pipeline.add_step(train_model)
    pipeline.add_step(evaluate_model)
    return pipeline


if __name__ == "__main__":
    pipeline = create_pipeline()
    result = pipeline.run()
    print(f"\\nPipeline completed successfully!")
    print(f"Results: {result.outputs}")
""",
            "README.md": """# {project_name}

A Flowy ML pipeline project.

## Getting Started

1. Install dependencies:
```bash
pip install flowy
```

2. Run the pipeline:
```bash
flowy run training_pipeline
# or
python pipelines/training_pipeline.py
```

3. View results:
```bash
flowy ui start
```

## Project Structure

```
{project_name}/
├── pipelines/           # Pipeline definitions
│   └── training_pipeline.py
├── flowy.yaml          # Project configuration
└── README.md
```

## Learn More

- [Flowy Documentation](https://code.claude.com/docs/flowy)
- [Examples](https://github.com/anthropics/flowy/examples)
""",
            "flowy.yaml": """# Flowy project configuration

name: {project_name}
version: "0.1.0"

# Stack configuration
stack:
  default: local

# Execution settings
execution:
  max_parallel_steps: 4
  enable_caching: true

# Experiment tracking
tracking:
  auto_log_params: true
  auto_log_metrics: true
  auto_log_artifacts: true
""",
            ".gitignore": """.flowy/
*.pyc
__pycache__/
.ipynb_checkpoints/
*.egg-info/
dist/
build/
.DS_Store
""",
        },
    },
    "pytorch": {
        "description": "PyTorch ML project template",
        "files": {
            "pipelines/__init__.py": "",
            "pipelines/training_pipeline.py": """\"\"\"PyTorch training pipeline.\"\"\"

from flowy import Pipeline, step, context
import torch
import torch.nn as nn


ctx = context(
    learning_rate=0.001,
    batch_size=64,
    epochs=10,
    device="cuda" if torch.cuda.is_available() else "cpu"
)


class SimpleModel(nn.Module):
    def __init__(self, input_dim, hidden_dim, output_dim):
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, output_dim)
        )

    def forward(self, x):
        return self.network(x)


@step(outputs=["data/train", "data/val"])
def prepare_data():
    \"\"\"Prepare training and validation datasets.\"\"\"
    # Your data preparation logic here
    print("Preparing PyTorch datasets...")
    return {"train_size": 8000}, {"val_size": 2000}


@step(inputs=["data/train", "data/val"], outputs=["model/trained"])
def train_model(train_data, val_data, learning_rate, epochs, device):
    \"\"\"Train PyTorch model.\"\"\"
    print(f"Training on {device}...")

    model = SimpleModel(input_dim=10, hidden_dim=64, output_dim=2)
    model = model.to(device)

    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)

    for epoch in range(epochs):
        # Training loop here
        print(f"Epoch {epoch+1}/{epochs}")

    return model


def create_pipeline():
    pipeline = Pipeline("pytorch_training", context=ctx)
    pipeline.add_step(prepare_data)
    pipeline.add_step(train_model)
    return pipeline


if __name__ == "__main__":
    pipeline = create_pipeline()
    result = pipeline.run()
    print("\\nTraining complete!")
""",
            "requirements.txt": """flowy
torch>=2.0.0
numpy
""",
        },
    },
}


def init_project(name: str, template: str, directory: Path) -> None:
    """Initialize a new Flowy project.

    Args:
        name: Project name
        template: Template to use (basic, pytorch, tensorflow, sklearn)
        directory: Directory to create project in
    """
    if template not in TEMPLATES:
        raise ValueError(f"Unknown template: {template}. Choose from: {', '.join(TEMPLATES.keys())}")

    # Create project directory
    directory.mkdir(parents=True, exist_ok=True)

    # Get template files
    template_data = TEMPLATES[template]
    files = template_data["files"]

    # Create files from template
    for file_path, content in files.items():
        full_path = directory / file_path

        # Create parent directories
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Format content with project name
        formatted_content = content.replace("{project_name}", name)

        # Write file
        with open(full_path, 'w') as f:
            f.write(formatted_content)

    # Create .flowy directory
    (directory / ".flowy").mkdir(exist_ok=True)
    (directory / ".flowy" / "artifacts").mkdir(exist_ok=True)
    (directory / ".flowy" / "cache").mkdir(exist_ok=True)
    (directory / ".flowy" / "runs").mkdir(exist_ok=True)


def list_templates() -> dict:
    """List available project templates.

    Returns:
        Dictionary of template names and descriptions
    """
    return {name: data["description"] for name, data in TEMPLATES.items()}
