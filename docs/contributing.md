<div class="hero-section" markdown>

## 🤝 Contributing to FlowyML

We welcome contributions of all kinds — from bug reports and documentation improvements to new features and integrations. FlowyML is built by the community, for the community.

<span class="feature-badge">🐛 Bug Reports</span>
<span class="feature-badge">📝 Documentation</span>
<span class="feature-badge">✨ Features</span>
<span class="feature-badge">🧪 Testing</span>

</div>

## Development Setup 🛠️

### Prerequisites
- Python 3.8+
- Node.js 16+ (for UI development)
- Poetry (recommended) or pip

### Setting up the Environment

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/UnicoLab/FlowyML.git
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

## Commit Messages 💬

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add new evaluation scorer for toxicity
fix: resolve cache invalidation on context change
docs: update getting-started guide with new API
refactor: simplify step execution engine
test: add integration tests for GCP stack
chore: update dependencies
```

!!! tip "Good Commit Messages"
    - Use the imperative mood: "add feature" not "added feature"
    - Keep the subject line under 72 characters
    - Reference issues: `fix: resolve #123 cache invalidation bug`

---

## 📍 What's Next?

<div class="header-grid" markdown>

<div class="header-card" markdown>
### 🏗️ Architecture
Understand how FlowyML is structured internally.

[Architecture →](architecture.md)
</div>

<div class="header-card" markdown>
### 🔌 Creating Plugins
Build custom plugins and components.

[Plugin Guide →](plugins/creating-plugins.md)
</div>

<div class="header-card" markdown>
### 📚 API Reference
Full API documentation for all modules.

[API Docs →](api/core.md)
</div>

</div>
