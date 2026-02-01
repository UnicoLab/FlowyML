.PHONY: help install install-dev install-ui clean test test-unit test-integration test-coverage \
        backend-dev backend-start frontend-dev frontend-build frontend-install \
        ui-dev ui-start ui-stop ui-status all-dev setup lint format check \
        cache-clear cache-stats init run docker-build docker-up docker-down docker-logs docker-clean

# Variables
POETRY := poetry
PYTHON := $(POETRY) run python
PYTEST := $(POETRY) run pytest
flowyml := $(POETRY) run flowyml
BACKEND_DIR := flowyml/ui/backend
FRONTEND_DIR := flowyml/ui/frontend

# Default target
help: ## Show this help message
	@echo "FlowyML - Available Make Targets"
	@echo "================================="
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# =============================================================================
# Docker Stack Management
# =============================================================================

docker-build: ## Build Docker images for backend and frontend
	docker compose build

docker-build-clean: ## Build Docker images without cache
	docker compose build --no-cache

docker-up: ## Start Docker stack (backend + frontend)
	docker compose up -d

docker-down: ## Stop Docker stack
	docker compose down

docker-logs: ## View Docker logs
	docker compose logs -f

docker-clean: ## Stop Docker stack and clean volumes
	docker compose down -v --remove-orphans
	docker system prune -f
	rm -rf .flowyml/metadata.db .flowyml/artifacts

docker-restart: ## Restart Docker stack
	docker compose restart

docker-ps: ## Show running Docker containers
	docker compose ps

# =============================================================================
# Setup and Installation
# =============================================================================

install: ## Install flowyml package
	$(POETRY) install

install-dev: ## Install development dependencies
	$(POETRY) install --with dev

install-ui: ## Install with UI dependencies
	$(POETRY) install --extras ui

install-all: ## Install all dependencies including extras
	$(POETRY) install --all-extras

setup: install-dev frontend-install ## Complete setup (install + frontend deps)
	@echo "✅ Setup complete!"

# =============================================================================
# Frontend
# =============================================================================

frontend-install: ## Install frontend dependencies
	cd $(FRONTEND_DIR) && npm install

frontend-dev: ## Start frontend development server
	cd $(FRONTEND_DIR) && npm run dev

frontend-build: ## Build frontend for production
	cd $(FRONTEND_DIR) && npm run build

# =============================================================================
# Backend
# =============================================================================

backend-dev: ## Start backend development server (with auto-reload)
	cd $(BACKEND_DIR) && $(POETRY) run uvicorn main:app --reload --host 0.0.0.0 --port 8080

backend-start: ## Start backend production server
	cd $(BACKEND_DIR) && $(POETRY) run uvicorn main:app --host 0.0.0.0 --port 8080

# =============================================================================
# FlowyML CLI Commands
# =============================================================================

ui-start: ## Start flowyml UI server
	$(flowyml) ui start --open-browser

ui-dev: ## Start UI in development mode
	$(flowyml) ui start --dev --open-browser

ui-stop: ## Stop flowyml UI server
	$(flowyml) ui stop

ui-status: ## Check UI server status
	$(flowyml) ui status

init: ## Initialize a new flowyml project
	$(flowyml) init

run: ## Run a pipeline (usage: make run PIPELINE=my_pipeline)
	$(flowyml) run $(PIPELINE)

cache-stats: ## Show cache statistics
	$(flowyml) cache stats

cache-clear: ## Clear cache
	$(flowyml) cache clear

config: ## Show current configuration
	$(flowyml) config

experiments: ## List experiments
	$(flowyml) experiment list

stacks: ## List available stacks
	$(flowyml) stack list

# =============================================================================
# Testing
# =============================================================================

test: ## Run all tests (with parallel execution)
	$(PYTEST) tests/ -v -n auto

test-unit: ## Run unit tests only (with parallel execution)
	$(PYTEST) tests/ -v -k "not integration" -n auto

test-integration: ## Run integration tests only
	$(PYTEST) tests/test_integration.py tests/test_api_integration.py -v

test-coverage: ## Run tests with coverage report (parallel execution)
	$(PYTEST) tests/ --cov=flowyml --cov-report=html --cov-report=term -n auto

test-fast: ## Run tests without coverage (faster, parallel execution)
	$(PYTEST) tests/ -v --tb=short -n auto

test-serial: ## Run tests serially (no parallel execution) - useful for debugging
	$(PYTEST) tests/ -v

# =============================================================================
# Code Quality
# =============================================================================

lint: ## Run linters
	@echo "Running ruff..."
	-$(POETRY) run ruff check flowyml --fix
	@echo "Running mypy..."
	-$(POETRY) run mypy flowyml --ignore-missing-imports

format: ## Format code with black
	$(POETRY) run black flowyml tests examples --line-length=100

format-check: ## Check code formatting
	$(POETRY) run black flowyml tests examples --check --line-length=100

check: format-check lint ## Run all code quality checks

# =============================================================================
# Cleaning
# =============================================================================

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

clean-all: clean clean-frontend docker-clean ## Clean everything including Docker
	$(POETRY) env remove --all || true
	@echo "✅ Cleaned everything"

# =============================================================================
# Documentation
# =============================================================================

docs-serve: ## Serve documentation locally
	$(POETRY) run mkdocs serve

docs-build: ## Build documentation
	$(POETRY) run mkdocs build

# =============================================================================
# Examples
# =============================================================================

run-demo: ## Run the complete demo
	$(PYTHON) examples/complete_demo.py

run-examples: ## Run all examples
	@for file in examples/*.py; do \
		echo "Running $$file..."; \
		$(PYTHON) $$file; \
	done

# =============================================================================
# Database
# =============================================================================

db-clean: ## Clean database and metadata
	rm -rf .flowyml
	@echo "✅ Cleaned database and metadata"

# =============================================================================
# Development workflow shortcuts
# =============================================================================

dev: ui-dev ## Alias for ui-dev (start UI in dev mode)

build: frontend-build install ## Build everything

quick-test: test-fast ## Alias for test-fast

all-dev: docker-up ## Start full stack with Docker
	@echo "✅ Docker stack running!"
	@echo "Backend: http://localhost:8080"
	@echo "Frontend: http://localhost:80"


local-deploy: ## Start full local stack (App, DB, Observability)
	@echo "🚀 Starting FlowyML local stack..."
	docker compose up -d
	@echo ""
	@echo "✅ FlowyML local stack is running!"
	@echo ""
	@echo "📊 Services:"
	@echo "   Frontend:   http://localhost:80"
	@echo "   Backend:    http://localhost:8080"
	@echo "   API Docs:   http://localhost:8080/docs"
	@echo "   Grafana:    http://localhost:3001 (admin/admin)"
	@echo "   Prometheus: http://localhost:9090"
	@echo ""
	@echo "Run 'make docker-logs' to view logs"
	@echo "Run 'make local-stop' to stop the stack"

local-stop: docker-down ## Stop local stack
	@echo "🛑 FlowyML local stack stopped."

local-health: ## Check health of local stack services
	@echo "🔍 Checking service health..."
	@echo ""
	@curl -sf http://localhost:8080/api/health && echo "✅ Backend:  healthy" || echo "❌ Backend:  unhealthy"
	@curl -sf http://localhost:80 > /dev/null && echo "✅ Frontend: healthy" || echo "❌ Frontend: unhealthy"
	@curl -sf http://localhost:9090/-/healthy > /dev/null && echo "✅ Prometheus: healthy" || echo "❌ Prometheus: unhealthy"
	@curl -sf http://localhost:3001/api/health > /dev/null && echo "✅ Grafana: healthy" || echo "❌ Grafana: unhealthy"

local-test: ## Run a test pipeline against the local stack
	@echo "Running local stack health check..."
	@curl -s http://localhost:8080/api/health | python3 -m json.tool || echo "Backend not responding"
	@echo "Test completed."

# =============================================================================
# CI/CD
# =============================================================================

ci: check test-coverage ## Run CI pipeline (checks + tests with coverage)

# =============================================================================
# Poetry helpers
# =============================================================================

poetry-update: ## Update poetry dependencies
	$(POETRY) update

poetry-lock: ## Lock poetry dependencies
	$(POETRY) lock

poetry-show: ## Show installed packages
	$(POETRY) show

poetry-shell: ## Open poetry shell
	$(POETRY) shell

# =============================================================================
# Info
# =============================================================================

info: ## Show project information
	@echo "FlowyML Project Information"
	@echo "============================"
	@echo "Python version:  $$(python --version)"
	@echo "Poetry version:  $$(poetry --version)"
	@echo "Node version:    $$(node --version 2>/dev/null || echo 'Not installed')"
	@echo "NPM version:     $$(npm --version 2>/dev/null || echo 'Not installed')"
	@echo "Docker version:  $$(docker --version 2>/dev/null || echo 'Not installed')"
	@echo ""
	@echo "Project structure:"
	@echo "  Backend:  $(BACKEND_DIR)"
	@echo "  Frontend: $(FRONTEND_DIR)"
	@echo "  Tests:    tests/"
	@echo "  Examples: examples/"
	@echo ""
	@echo "Docker stack:"
	@docker-compose ps 2>/dev/null || echo "  Not running"

version: ## Show flowyml version
	$(flowyml) --version

# =============================================================================
# Infrastructure & Deployment
# =============================================================================

# Variables for deployment
GCP_PROJECT ?= $(shell gcloud config get-value project)
GCP_REGION ?= us-central1
AWS_REGION ?= us-east-1
IMAGE_TAG ?= latest

infra-init-gcp: ## Initialize Terraform for GCP
	cd infra/gcp && terraform init

infra-plan-gcp: ## Plan Terraform for GCP
	cd infra/gcp && terraform plan \
		-var="project_id=$(GCP_PROJECT)" \
		-var="region=$(GCP_REGION)" \
		-var="backend_image=gcr.io/$(GCP_PROJECT)/flowyml-backend:$(IMAGE_TAG)" \
		-var="frontend_image=gcr.io/$(GCP_PROJECT)/flowyml-frontend:$(IMAGE_TAG)" \
		-var="db_password=$(DB_PASSWORD)"

infra-apply-gcp: ## Apply Terraform for GCP
	cd infra/gcp && terraform apply -auto-approve \
		-var="project_id=$(GCP_PROJECT)" \
		-var="region=$(GCP_REGION)" \
		-var="backend_image=gcr.io/$(GCP_PROJECT)/flowyml-backend:$(IMAGE_TAG)" \
		-var="frontend_image=gcr.io/$(GCP_PROJECT)/flowyml-frontend:$(IMAGE_TAG)" \
		$(if $(wildcard infra/gcp/terraform.tfvars.secret),-var-file="terraform.tfvars.secret",-var="db_password=$(DB_PASSWORD)")

docker-push-gcp: ## Build and push images to GCR
	gcloud auth configure-docker
	docker build -f Dockerfile -t gcr.io/$(GCP_PROJECT)/flowyml-backend:$(IMAGE_TAG) .
	docker build -f flowyml/ui/frontend/Dockerfile -t gcr.io/$(GCP_PROJECT)/flowyml-frontend:$(IMAGE_TAG) flowyml/ui/frontend
	docker push gcr.io/$(GCP_PROJECT)/flowyml-backend:$(IMAGE_TAG)
	docker push gcr.io/$(GCP_PROJECT)/flowyml-frontend:$(IMAGE_TAG)

deploy-gcp: docker-push-gcp infra-init-gcp infra-apply-gcp ## Full deployment to GCP

infra-init-aws: ## Initialize Terraform for AWS
	cd infra/aws && terraform init

infra-plan-aws: ## Plan Terraform for AWS
	cd infra/aws && terraform plan \
		-var="region=$(AWS_REGION)" \
		-var="backend_image=$(AWS_ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com/flowyml-backend:$(IMAGE_TAG)" \
		-var="frontend_image=$(AWS_ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com/flowyml-frontend:$(IMAGE_TAG)" \
		-var="db_password=$(DB_PASSWORD)"

infra-apply-aws: ## Apply Terraform for AWS
	cd infra/aws && terraform apply -auto-approve \
		-var="region=$(AWS_REGION)" \
		-var="backend_image=$(AWS_ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com/flowyml-backend:$(IMAGE_TAG)" \
		-var="frontend_image=$(AWS_ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com/flowyml-frontend:$(IMAGE_TAG)" \
		$(if $(wildcard infra/aws/terraform.tfvars.secret),-var-file="terraform.tfvars.secret",-var="db_password=$(DB_PASSWORD)")

docker-push-aws: ## Build and push images to ECR
	aws ecr get-login-password --region $(AWS_REGION) | docker login --username AWS --password-stdin $(AWS_ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com
	docker build -f Dockerfile -t $(AWS_ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com/flowyml-backend:$(IMAGE_TAG) .
	docker build -f flowyml/ui/frontend/Dockerfile -t $(AWS_ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com/flowyml-frontend:$(IMAGE_TAG) flowyml/ui/frontend
	docker push $(AWS_ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com/flowyml-backend:$(IMAGE_TAG)
	docker push $(AWS_ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com/flowyml-frontend:$(IMAGE_TAG)

deploy-aws: docker-push-aws infra-init-aws infra-apply-aws ## Full deployment to AWS
