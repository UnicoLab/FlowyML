# Contributing to flowyml 🤝

We welcome contributions to flowyml! Whether it's reporting a bug, improving documentation, or adding a new feature, your help is appreciated.

## Development Setup 🛠️

### Prerequisites
- Python 3.8+
- Node.js 16+ (for UI development)
- Poetry (recommended) or pip

### Setting up the Environment

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/flowyml-ai/flowyml.git
    cd flowyml
    ```

2.  **Install dependencies**:
    ```bash
    # Using pip
    pip install -e ".[dev,ui]"

    # Using poetry
    poetry install --with dev,ui
    ```

3.  **Install pre-commit hooks**:
    ```bash
    pre-commit install
    ```

## UI Development 🖥️

The UI consists of a FastAPI backend and a React frontend.

### Running in Development Mode

1.  **Start the Backend**:
    ```bash
    # In one terminal
    flowyml ui start --dev
    ```
    This starts the FastAPI server on port 8000 with auto-reload.

2.  **Start the Frontend**:
    ```bash
    # In another terminal
    cd flowyml/ui/frontend
    npm install
    npm run dev
    ```
    This starts the Vite dev server on port 5173 with Hot Module Replacement (HMR).

The frontend proxies API requests to the backend at `http://localhost:8000`.

### Building for Production 📦

To build the frontend for production distribution:

```bash
cd flowyml/ui/frontend
npm run build
```

This generates static assets in `flowyml/ui/frontend/dist`, which are served by the Python backend in production mode.

## Testing 🧪

### Running Tests

Run the full test suite:

```bash
pytest
```

Run specific tests:

```bash
pytest tests/test_core.py
```

### Writing Tests

- Place unit tests in the `tests/` directory.
- Use the `BaseTestCase` class for tests that require a temporary directory or isolated configuration.
- Ensure all new features have accompanying tests.

## Code Style 🎨

We follow PEP 8 and use `black` for formatting.

```bash
# Format code
black flowyml tests

# Check style
flake8 flowyml tests
```

## Pull Request Process 🔀

1.  Fork the repository.
2.  Create a feature branch (`git checkout -b feature/amazing-feature`).
3.  Commit your changes.
4.  Push to the branch.
5.  Open a Pull Request.

## Documentation 📝

Documentation is built with MkDocs.

```bash
# Serve documentation locally
mkdocs serve
```

Update documentation in the `docs/` directory for any API changes.
