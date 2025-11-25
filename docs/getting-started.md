# Getting Started with UniFlow 🚀

Welcome to UniFlow! This guide will help you set up your environment and build your first machine learning pipeline in minutes.

## Installation 📦

UniFlow requires Python 3.8 or higher.

### Basic Installation

```bash
pip install uniflow
```

### Full Installation (Recommended)

Includes UI support and common ML dependencies:

```bash
pip install "uniflow[all]"
```

## Your First Project 📁

Let's create a new project using the CLI.

```bash
uniflow init my-first-project
cd my-first-project
```

This creates a directory structure like this:

```
my-first-project/
├── uniflow.yaml
├── README.md
├── requirements.txt
└── src/
    └── pipeline.py
```

## Creating a Pipeline 🧪

Open `src/pipeline.py` and replace its content with this simple example:

```python
from uniflow import pipeline, step, context

# 1. Define a Step
@step
def fetch_data():
    print("Fetching data...")
    return [1, 2, 3, 4, 5]

# 2. Define another Step with inputs
@step(inputs=["data"])
def process_data(data):
    print(f"Processing {len(data)} items...")
    return [x * 2 for x in data]

# 3. Define the Pipeline
@pipeline
def my_first_pipeline():
    # Connect steps
    data = fetch_data()
    result = process_data(data)
    return result

if __name__ == "__main__":
    # 4. Run it!
    run = my_first_pipeline()
    
    if run.success:
        print(f"Pipeline finished successfully!")
        print(f"Result: {run.result}")
    else:
        print(f"Pipeline failed: {run.error}")
```

## Running the Pipeline ▶️

Execute the script:

```bash
python src/pipeline.py
```

You should see output indicating the steps are executing.

## Visualizing with the UI 🖥️

Now, let's see your pipeline in the UniFlow UI.

1.  Start the UI server:
    ```bash
    uniflow ui start
    ```

2.  Open your browser to `http://localhost:8080`.

3.  Run your pipeline again (in a separate terminal):
    ```bash
    python src/pipeline.py
    ```

4.  Watch the dashboard! You'll see your pipeline appear, steps execute in real-time, and you can inspect the inputs and outputs.

## Next Steps 📚

- **[User Guide](user-guide/pipelines.md)**: Learn about advanced pipeline features.
- **[Steps & Decorators](user-guide/steps.md)**: Master step configuration.
- **[Context & Parameters](user-guide/context.md)**: Manage configuration easily.
- **[Assets](user-guide/artifacts.md)**: Work with datasets and models.
