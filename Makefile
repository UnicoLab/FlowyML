.PHONY: help install install-dev install-ui clean test test-unit test-integration test-coverage \
        backend-dev backend-start frontend-dev frontend-build frontend-install \
        ui-dev ui-start ui-stop ui-status all-dev setup lint format check \
        cache-clear cache-stats init run

# Variables
POETRY := poetry
PYTHON := $(POETRY) run python
PYTEST := $(POETRY) run pytest
UNIFLOW := $(POETRY) run uniflow
BACKEND_DIR := uniflow/ui/backend
FRONTEND_DIR := uniflow/ui/frontend

# Default target
help: ## Show this help message
	@echo "UniFlow - Available Make Targets"
	@echo "================================="
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Setup and Installation
install: ## Install UniFlow package
	$(POETRY) install

install-dev: ## Install development dependencies
	$(POETRY) install --with dev

install-ui: ## Install with UI dependencies
	$(POETRY) install --extras ui

setup: install-dev frontend-install ## Complete setup (install + frontend deps)
	@echo "✅ Setup complete!"

# Frontend
frontend-install: ## Install frontend dependencies
	cd $(FRONTEND_DIR) && npm install

frontend-dev: ## Start frontend development server
	cd $(FRONTEND_DIR) && npm run dev

frontend-build: ## Build frontend for production
	cd $(FRONTEND_DIR) && npm run build

# Backend
backend-dev: ## Start backend development server (with auto-reload)
	cd $(BACKEND_DIR) && $(POETRY) run uvicorn main:app --reload --host 0.0.0.0 --port 8000

backend-start: ## Start backend production server
	cd $(BACKEND_DIR) && $(POETRY) run uvicorn main:app --host 0.0.0.0 --port 8000

# UniFlow CLI Commands
ui-start: ## Start UniFlow UI server 
	$(UNIFLOW) ui start --open-browser

ui-dev: ## Start UI in development mode
	$(UNIFLOW) ui start --dev --open-browser

ui-stop: ## Stop UniFlow UI server
	$(UNIFLOW) ui stop

ui-status: ## Check UI server status
	$(UNIFLOW) ui status

init: ## Initialize a new UniFlow project
	$(UNIFLOW) init

run: ## Run a pipeline (usage: make run PIPELINE=my_pipeline)
	$(UNIFLOW) run $(PIPELINE)

cache-stats: ## Show cache statistics
	$(UNIFLOW) cache stats

cache-clear: ## Clear cache
	$(UNIFLOW) cache clear

config: ## Show current configuration
	$(UNIFLOW) config

experiments: ## List experiments
	$(UNIFLOW) experiment list

stacks: ## List available stacks
	$(UNIFLOW) stack list

# Testing
test: ## Run all tests
	$(PYTEST) tests/ -v

test-unit: ## Run unit tests only
	$(PYTEST) tests/ -v -k "not integration"

test-integration: ## Run integration tests only
	$(PYTEST) tests/test_integration.py tests/test_api_integration.py -v

test-coverage: ## Run tests with coverage report
	$(PYTEST) tests/ --cov=uniflow --cov-report=html --cov-report=term

test-fast: ## Run tests without coverage (faster)
	$(PYTEST) tests/ -v --tb=short

# Code Quality
lint: ## Run linters
	@echo "Running ruff..."
	-$(POETRY) run ruff check uniflow --fix
	@echo "Running mypy..."
	-$(POETRY) run mypy uniflow --ignore-missing-imports

format: ## Format code with black
	$(POETRY) run black uniflow tests examples --line-length=100

format-check: ## Check code formatting
	$(POETRY) run black uniflow tests examples --check --line-length=100

check: format-check lint ## Run all code quality checks

# Cleaning
clean: ## Clean build artifacts and caches
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	rm -rf build dist .coverage
	@echo "✅ Cleaned build artifacts and caches"

clean-frontend: ## Clean frontend build artifacts
	cd $(FRONTEND_DIR) && rm -rf node_modules dist .vite
	@echo "✅ Cleaned frontend artifacts"

clean-all: clean clean-frontend ## Clean everything
	$(POETRY) env remove --all || true
	@echo "✅ Cleaned everything including poetry env"

# Documentation
docs-serve: ## Serve documentation locally
	$(POETRY) run mkdocs serve

docs-build: ## Build documentation
	$(POETRY) run mkdocs build

# Examples
run-demo: ## Run the complete demo
	$(PYTHON) examples/complete_demo.py

run-examples: ## Run all examples
	@for file in examples/*.py; do \
		echo "Running $$file..."; \
		$(PYTHON) $$file; \
	done

# Database
db-clean: ## Clean database and metadata
	rm -rf .uniflow
	@echo "✅ Cleaned database and metadata"

# Development workflow shortcuts
dev: ui-dev ## Alias for ui-dev (start UI in dev mode)

build: frontend-build install ## Build everything

quick-test: test-fast ## Alias for test-fast

# CI/CD
ci: check test-coverage ## Run CI pipeline (checks + tests with coverage)

# Poetry helpers
poetry-update: ## Update poetry dependencies
	$(POETRY) update

poetry-lock: ## Lock poetry dependencies
	$(POETRY) lock

poetry-show: ## Show installed packages
	$(POETRY) show

poetry-shell: ## Open poetry shell
	$(POETRY) shell

# Info
info: ## Show project information
	@echo "UniFlow Project Information"
	@echo "============================"
	@echo "Python version:  $$(python --version)"
	@echo "Poetry version:  $$(poetry --version)"
	@echo "Node version:    $$(node --version 2>/dev/null || echo 'Not installed')"
	@echo "NPM version:     $$(npm --version 2>/dev/null || echo 'Not installed')"
	@echo ""
	@echo "Project structure:"
	@echo "  Backend:  $(BACKEND_DIR)"
	@echo "  Frontend: $(FRONTEND_DIR)"
	@echo "  Tests:    tests/"
	@echo "  Examples: examples/"
	@echo ""
	@echo "Installed packages:"
	@$(POETRY) show --tree | head -20

version: ## Show UniFlow version
	$(UNIFLOW) --version
