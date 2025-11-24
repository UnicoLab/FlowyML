# 🚀 Flowy Quick Start Cheat Sheet

## Installation

```bash
# From PyPI (when published)
pip install "flowy[ui]"

# From source (development)
git clone <repo>
cd flowy
pip install -e ".[ui]"  # Makes 'flowy' command available
```

## ⚠️ Common Issue: `command not found: flowy`

```bash
# Solution 1: Install in editable mode
pip install -e ".[ui]"

# Solution 2: Run without installing
python -m flowy.cli.main ui start
```

## UI Setup (One-Time)

```bash
# 1. Install UI dependencies
pip install -e ".[ui]"

# 2. Build frontend
cd flowy/ui/frontend
npm install && npm run build
cd ../../..

# 3. Start UI
flowy ui start --open-browser
```

## Common Commands

```bash
# UI Management
flowy ui start              # Start UI server
flowy ui start --dev        # Dev mode (auto-reload)
flowy ui start -o           # Start and open browser
flowy ui status             # Check if running

# Run Pipelines
flowy run my_pipeline       # Run pipeline
python my_pipeline.py       # Or run Python directly

# Experiments
flowy experiment list       # List experiments
flowy cache stats           # View cache stats
flowy config                # Show configuration
```

## Development Workflow

```bash
# Terminal 1: Backend
pip install -e ".[ui]"
flowy ui start --dev

# Terminal 2: Frontend (optional)
cd flowy/ui/frontend
npm run dev

# Terminal 3: Run code
python examples/ui_integration_example.py
```

## Helpful Links

- **UI Guide**: [UI_GUIDE.md](UI_GUIDE.md)
- **CLI Reference**: [CLI_REFERENCE.md](CLI_REFERENCE.md)
- **Development**: [DEVELOPMENT.md](DEVELOPMENT.md)
- **Troubleshooting**: [README.md#troubleshooting](README.md#troubleshooting)

## Quick Example

```python
from flowy import Pipeline, step, context
from flowy.ui import is_ui_running, get_ui_url

# Check UI status
if is_ui_running():
    print(f"UI: {get_ui_url()}")

# Define pipeline
ctx = context(learning_rate=0.001, epochs=10)

@step(outputs=["model"])
def train(learning_rate: float, epochs: int):
    return {"accuracy": 0.95}

pipeline = Pipeline("demo", context=ctx)
pipeline.add_step(train)
result = pipeline.run()
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `command not found: flowy` | `pip install -e ".[ui]"` |
| UI shows "Frontend not built" | `cd flowy/ui/frontend && npm run build` |
| Port 8080 in use | `flowy ui start --port 8081` |
| Changes not reflected | Use `--dev` flag or restart |

---

**Get the full guides for detailed information!**
