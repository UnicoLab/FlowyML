# 🛠️ Development Guide

This guide explains how to set up and work with Flowy in development mode.

## 📦 Installation for Development

### Option 1: Editable Install (Recommended)

This makes the `flowy` CLI command available while still allowing you to edit the code:

```bash
# Navigate to the repo root
cd /path/to/Flowy

# Install in editable mode
pip install -e .

# Or with extras
pip install -e ".[ui]"
pip install -e ".[all]"
```

Now you can use `flowy` commands:
```bash
flowy ui start
flowy --help
```

**Changes to the code are immediately reflected** - no need to reinstall!

### Option 2: Use Python Module (No Installation)

If you don't want to install the package, you can run CLI commands directly:

```bash
# Navigate to the repo root
cd /path/to/Flowy

# Run CLI via python -m
python -m flowy.cli.main --help

# Start UI server
python -m flowy.cli.main ui start

# Any other command
python -m flowy.cli.main ui status
```

### Option 3: Poetry (If Using Poetry)

```bash
# Install with poetry
poetry install

# Or with extras
poetry install --extras ui
poetry install --extras all

# Use flowy command
poetry run flowy ui start
```

---

## 🖥️ UI Development Setup

### Backend Development

```bash
# 1. Install in editable mode with UI extras
pip install -e ".[ui]"

# 2. Start the backend in dev mode (auto-reload)
flowy ui start --dev

# Or without installation:
python -m flowy.cli.main ui start --dev
```

The backend will run on http://localhost:8080 with auto-reload enabled.

### Frontend Development

```bash
# 1. Navigate to frontend directory
cd flowy/ui/frontend

# 2. Install Node dependencies
npm install

# 3. Start dev server with hot reload
npm run dev
```

The frontend dev server runs on http://localhost:5173 and proxies API calls to the backend on port 8080.

**Full Development Workflow:**

```bash
# Terminal 1: Backend (from repo root)
pip install -e ".[ui]"
flowy ui start --dev

# Terminal 2: Frontend (from repo root)
cd flowy/ui/frontend
npm run dev

# Terminal 3: Run pipelines (from repo root)
python examples/ui_integration_example.py
```

---

## 🧪 Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run with coverage
pytest --cov=flowy --cov-report=term-missing

# Run specific test file
pytest tests/test_pipeline.py

# Run with verbose output
pytest -v
```

---

## 📝 Code Quality

### Linting

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run ruff linter
ruff check flowy/

# Auto-fix issues
ruff check --fix flowy/

# Run mypy type checking
mypy flowy/
```

### Formatting

```bash
# Format with black
black flowy/

# Check formatting without changes
black --check flowy/
```

---

## 🔧 Common Development Tasks

### Adding a New CLI Command

1. Edit `flowy/cli/main.py`
2. Add your command using Click decorators
3. Test immediately (if using editable install)

```python
# flowy/cli/main.py

@cli.command()
@click.option('--example', help='Example option')
def mycommand(example: str):
    """My new command."""
    click.echo(f"Running with {example}")
```

```bash
# Test immediately
flowy mycommand --example test
```

### Adding a New API Endpoint

1. Edit `flowy/ui/backend/routers/` files
2. Add your endpoint
3. Restart backend (or use --dev for auto-reload)

```python
# flowy/ui/backend/routers/pipelines.py

@router.get("/my-endpoint")
async def my_endpoint():
    return {"status": "ok"}
```

```bash
# Test
curl http://localhost:8080/api/pipelines/my-endpoint
```

### Building Frontend

```bash
cd flowy/ui/frontend

# Development build (fast, not optimized)
npm run build

# Production build (optimized, minified)
npm run build

# Preview production build locally
npm run build
npm run preview
```

---

## 📂 Project Structure for Development

```
Flowy/
├── flowy/                  # Main package
│   ├── __init__.py
│   ├── cli/               # CLI commands
│   │   └── main.py        # Entry point for 'flowy' command
│   ├── core/              # Core pipeline logic
│   ├── ui/                # UI components
│   │   ├── backend/       # FastAPI backend
│   │   ├── frontend/      # React frontend
│   │   └── utils.py       # UI utilities
│   └── ...
├── tests/                 # Test suite
├── examples/              # Example scripts
├── pyproject.toml         # Package configuration
└── setup.py               # Setup script (if needed)
```

---

## 🐛 Debugging

### Debug the CLI

```bash
# Add breakpoints to flowy/cli/main.py
import pdb; pdb.set_trace()

# Run command
flowy ui start
```

### Debug the Backend

```bash
# Add breakpoints to flowy/ui/backend/main.py
import pdb; pdb.set_trace()

# Run with debugger
python -m pdb -m flowy.cli.main ui start
```

### Debug Frontend

1. Open browser DevTools (F12)
2. Use React DevTools extension
3. Check Console for errors
4. Use Network tab for API calls

---

## 🔄 Hot Reload

### Backend Hot Reload

```bash
# Start with --dev flag
flowy ui start --dev

# Now changes to Python files automatically reload the server
```

### Frontend Hot Reload

```bash
# Frontend automatically has HMR (Hot Module Replacement)
cd flowy/ui/frontend
npm run dev

# Changes to React files automatically update in browser
```

---

## 📦 Building for Distribution

### Build Python Package

```bash
# Install build tools
pip install build

# Build wheel and sdist
python -m build

# Output in dist/
# flowy-0.1.0-py3-none-any.whl
# flowy-0.1.0.tar.gz
```

### Build Frontend

```bash
cd flowy/ui/frontend

# Production build
npm run build

# Output in dist/ directory
```

### Create Release

```bash
# 1. Update version in pyproject.toml
# 2. Build package
python -m build

# 3. Build frontend
cd flowy/ui/frontend
npm run build
cd ../../..

# 4. Create git tag
git tag v0.1.0
git push --tags

# 5. Upload to PyPI (if publishing)
pip install twine
twine upload dist/*
```

---

## 🔍 Troubleshooting Development Issues

### Issue: `flowy` command not found

**Cause**: Package not installed in development mode

**Solution**:
```bash
# Option 1: Install in editable mode
pip install -e .

# Option 2: Use python -m
python -m flowy.cli.main ui start
```

### Issue: Changes not reflected

**Cause**: Not using editable install or need to restart

**Solution**:
```bash
# Use editable install
pip install -e ".[ui]"

# Or restart the server if using --dev
```

### Issue: Import errors

**Cause**: Dependencies not installed

**Solution**:
```bash
# Reinstall with all extras
pip install -e ".[all,dev]"
```

### Issue: Frontend fails to build

**Cause**: Node modules not installed or outdated

**Solution**:
```bash
cd flowy/ui/frontend
rm -rf node_modules package-lock.json
npm install
npm run build
```

---

## 💡 Development Tips

1. **Use Editable Install**: Always use `pip install -e .` for development
2. **Enable Dev Mode**: Use `--dev` flag for auto-reload
3. **Check Logs**: Look at terminal output for errors
4. **Use Type Hints**: Makes code clearer and mypy can catch errors
5. **Write Tests**: Add tests for new features
6. **Update Docs**: Update documentation when adding features

---

## 🎯 Quick Reference

```bash
# Setup
pip install -e ".[all,dev]"

# Backend dev
flowy ui start --dev

# Frontend dev
cd flowy/ui/frontend && npm run dev

# Tests
pytest

# Linting
ruff check flowy/
black flowy/

# Build frontend
cd flowy/ui/frontend && npm run build

# Run example
python examples/ui_integration_example.py
```

---

## 📚 Additional Resources

- [CLI Reference](CLI_REFERENCE.md)
- [UI Guide](UI_GUIDE.md)
- [Architecture](UI_ARCHITECTURE.md)
- [Contributing Guide](CONTRIBUTING.md) *(if exists)*

---

**Happy developing! 🚀**
