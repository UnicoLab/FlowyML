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

verify-deployment: ## Verify the remote deployment
	@echo "🔍 Verifying deployment..."
	@terraform -chdir=infra/gcp output -raw app_url > .deploy_url
	@export FLOWYML_REMOTE_URL=$$(cat .deploy_url) && python scripts/test_deployment.py
	@rm .deploy_url

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
# Auto-detect GCP Project from secrets file, fallback to gcloud config
GCP_SECRET_FILE := infra/gcp/terraform.tfvars.secret
# Try to extract project_id from secret file, otherwise use gcloud config
GCP_PROJECT ?= $(shell if [ -f $(GCP_SECRET_FILE) ]; then grep 'project_id' $(GCP_SECRET_FILE) | head -n 1 | cut -d '"' -f 2; else gcloud config get-value project 2>/dev/null; fi)
GCP_REGION ?= europe-west1
AWS_REGION ?= us-east-1
IMAGE_TAG ?= latest
APP_NAME ?= flowyml

# Artifact Registry Config (Defined early for expansion)
ARTIFACT_REGISTRY_HOST = $(GCP_REGION)-docker.pkg.dev
ARTIFACT_REGISTRY_REPO = $(ARTIFACT_REGISTRY_HOST)/$(GCP_PROJECT)/$(APP_NAME)

# Check if GCP_PROJECT is set
check-gcp-project:
	@if [ -z "$(GCP_PROJECT)" ]; then \
		echo "❌ Error: GCP_PROJECT is not set."; \
		echo "   Please run 'make gcp-setup-secrets' and edit the file,"; \
		echo "   OR set it explicitly: make deploy-gcp GCP_PROJECT=my-project"; \
		exit 1; \
	fi
	@echo "✅ Using GCP Project: $(GCP_PROJECT)"

# =============================================================================
# GCP Deployment Commands (Watchtower Compatible)
# =============================================================================

# Service Configuration
# Service Configuration
GCP_SERVICE = $(APP_NAME)
GCP_IMAGE = $(ARTIFACT_REGISTRY_REPO)/flowyml:$(IMAGE_TAG)
TERRAFORM_DIR = infra/gcp
ADMIN_USER ?= admin
ADMIN_PASSWORD ?= flowyml
API_TOKEN ?= change-me-secure-token

# Robust Authentication Check
# Ensures both gcloud (for docker) and application-default (for terraform) are active
gcp-auth-check: check-gcp-project
	@echo "🔐 Checking GCP authentication..."
	@gcloud auth print-access-token > /dev/null 2>&1 || (echo "⚠️  gcloud auth expired, re-authenticating..." && gcloud auth login)
	@gcloud auth application-default print-access-token > /dev/null 2>&1 || (echo "⚠️  Application default credentials expired, re-authenticating..." && gcloud auth application-default login)
	@CURRENT_PROJECT=$$(gcloud config get-value project 2>/dev/null); \
	if [ "$$CURRENT_PROJECT" != "$(GCP_PROJECT)" ]; then \
		echo "⚠️  Switching gcloud to project $(GCP_PROJECT)..."; \
		gcloud config set project $(GCP_PROJECT); \
	fi
	@echo "✅ GCP authentication OK (project: $(GCP_PROJECT))"

# Full GCP login (opens browser — use when auth is expired)
gcp-login: check-gcp-project
	@echo "🔑 Authenticating with GCP (opens browser)..."
	gcloud auth login
	gcloud auth application-default login
	gcloud config set project $(GCP_PROJECT)
	@echo "✅ Authenticated. You can now run deployment commands."

# Build Unified Docker Image
gcp-build: check-gcp-project
	@echo "🏗️  Building Docker image for GCP..."
	docker build --platform linux/amd64 -f Dockerfile -t $(ARTIFACT_REGISTRY_REPO)/flowyml:$(IMAGE_TAG) .
	@echo "✅ Image built: $(ARTIFACT_REGISTRY_REPO)/flowyml:$(IMAGE_TAG)"

# Push to Artifact Registry
gcp-push: gcp-auth-check
	@echo "📤 Pushing image to GCP Artifact Registry..."
	gcloud auth configure-docker $(ARTIFACT_REGISTRY_HOST) --quiet
	gcloud services enable artifactregistry.googleapis.com --quiet
	-gcloud artifacts repositories create $(APP_NAME) --repository-format=docker --location=$(GCP_REGION) --description="FlowyML Docker repository" --quiet 2>/dev/null || true
	docker push $(GCP_IMAGE)
	@echo "✅ Image pushed: $(GCP_IMAGE)"

# Deploy infrastructure via Terraform
gcp-infra-up: gcp-auth-check
	@echo "🏗️  Applying Terraform infrastructure..."
	cd $(TERRAFORM_DIR) && terraform init && terraform apply -auto-approve \
		-var="project_id=$(GCP_PROJECT)" \
		-var="region=$(GCP_REGION)" \
		-var="app_name=$(APP_NAME)" \
		-var="container_image=$(GCP_IMAGE)" \
		$(if $(wildcard infra/gcp/terraform.tfvars.secret),-var-file="terraform.tfvars.secret",-var="db_password=$(DB_PASSWORD)" -var="admin_user=$(ADMIN_USER)" -var="admin_password=$(ADMIN_PASSWORD)" -var="api_token=$(API_TOKEN)")

# Plan infrastructure changes
gcp-plan: gcp-auth-check
	@echo "📋 Terraform plan..."
	cd $(TERRAFORM_DIR) && terraform plan \
		-var="project_id=$(GCP_PROJECT)" \
		-var="region=$(GCP_REGION)" \
		-var="app_name=$(APP_NAME)" \
		-var="container_image=$(GCP_IMAGE)" \
		$(if $(wildcard infra/gcp/terraform.tfvars.secret),-var-file="terraform.tfvars.secret",-var="db_password=$(DB_PASSWORD)" -var="admin_user=$(ADMIN_USER)" -var="admin_password=$(ADMIN_PASSWORD)" -var="api_token=$(API_TOKEN)")

# Destroy infrastructure
gcp-infra-down: gcp-auth-check
	@echo "⚠️  WARNING: This will destroy all GCP infrastructure!"
	@read -p "Are you sure? Type 'yes' to confirm: " confirm && \
	if [ "$$confirm" = "yes" ]; then \
		cd $(TERRAFORM_DIR) && terraform destroy -auto-approve \
		-var="project_id=$(GCP_PROJECT)" \
		-var="region=$(GCP_REGION)" \
		-var="app_name=$(APP_NAME)" \
		-var="container_image=$(GCP_IMAGE)" \
		$(if $(wildcard infra/gcp/terraform.tfvars.secret),-var-file="terraform.tfvars.secret",-var="db_password=$(DB_PASSWORD)" -var="admin_user=$(ADMIN_USER)" -var="admin_password=$(ADMIN_PASSWORD)" -var="api_token=$(API_TOKEN)"); \
	else \
		echo "Cancelled."; \
	fi

# Deployment Status
gcp-status: gcp-auth-check
	@echo ""
	@echo "╔══════════════════════════════════════════════════════════════════════╗"
	@echo "║                   🚀 FLOWYML GCP STATUS                               ║"
	@echo "╠══════════════════════════════════════════════════════════════════════╣"
	@echo "║                                                                      ║"
	@gcloud run services describe $(GCP_SERVICE) --region $(GCP_REGION) --format "value(status.conditions[0].status,status.conditions[0].message)" 2>/dev/null | while read status msg; do \
		printf "║  Status: %-60s ║\n" "$$status - $$msg"; \
	done
	@echo "║                                                                      ║"
	@echo "╠══════════════════════════════════════════════════════════════════════╣"
	@echo "║  🌐 URL:                                                             ║"
	@printf "║  %-68s ║\n" "$$(gcloud run services describe $(GCP_SERVICE) --region $(GCP_REGION) --format 'value(status.url)' 2>/dev/null)"
	@echo "║                                                                      ║"
	@echo "╚══════════════════════════════════════════════════════════════════════╝"
	@echo ""

# Logs
gcp-logs: gcp-auth-check
	@echo "📜 Streaming Cloud Run logs (Ctrl+C to exit)..."
	gcloud run services logs read $(GCP_SERVICE) --region $(GCP_REGION) --limit 100

# Full Deployment Workflow
gcp-deploy: gcp-build gcp-push gcp-infra-up gcp-status ## Full deployment to GCP

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

# =============================================================================
# Cost & Traffic Audit
# =============================================================================

flowyml-traffic-audit: gcp-auth-check ## 🔍 Audit who's calling the service
	@echo "🔍 FlowyML Traffic Audit (last 7 days)..."
	@echo ""
	@echo "═══ Top Callers by IP ═══"
	@gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="$(GCP_SERVICE)"' \
		--project=$(GCP_PROJECT) --limit=500 \
		--format='value(httpRequest.remoteIp)' 2>/dev/null | sort | uniq -c | sort -rn | head -20
	@echo ""
	@echo "═══ Top Paths ═══"
	@gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="$(GCP_SERVICE)"' \
		--project=$(GCP_PROJECT) --limit=500 \
		--format='value(httpRequest.requestUrl)' 2>/dev/null | sort | uniq -c | sort -rn | head -20
	@echo ""
	@echo "═══ Top User Agents ═══"
	@gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="$(GCP_SERVICE)"' \
		--project=$(GCP_PROJECT) --limit=500 \
		--format='value(httpRequest.userAgent)' 2>/dev/null | sort | uniq -c | sort -rn | head -10
	@echo ""
	@echo "═══ Recent Requests (last 20) ═══"
	@gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="$(GCP_SERVICE)"' \
		--project=$(GCP_PROJECT) --limit=20 \
		--format='table(timestamp,httpRequest.requestMethod,httpRequest.requestUrl,httpRequest.status,httpRequest.remoteIp)' 2>/dev/null

flowyml-cost-report: gcp-auth-check ## 💰 Show Cloud Run cost-relevant info
	@echo "💰 FlowyML Cost Report..."
	@echo ""
	@echo "═══ Cloud Run Instance Status ═══"
	@gcloud run services describe $(GCP_SERVICE) --region $(GCP_REGION) \
		--format='table(spec.template.spec.containerConcurrency,spec.template.metadata.annotations)' 2>/dev/null
	@echo ""
	@echo "═══ Active Revisions ═══"
	@gcloud run revisions list --service $(GCP_SERVICE) --region $(GCP_REGION) \
		--format='table(name,active,scaling.minInstanceCount,scaling.maxInstanceCount)' --limit=5 2>/dev/null

cost-audit: gcp-auth-check ## 📊 Full GCP cost audit (copy to AI context)
	@chmod +x scripts/cost-audit.sh
	@GCP_PROJECT=$(GCP_PROJECT) GCP_REGION=$(GCP_REGION) GCP_SERVICE=$(GCP_SERVICE) scripts/cost-audit.sh
