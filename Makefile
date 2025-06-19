# Makefile for RAG Demo Project
# 新入社員向け社内文書検索RAGアプリケーション

.PHONY: help install install-dev clean lint format type-check test test-cov security run docs pre-commit

# Default target
help: ## Show this help message
	@echo "RAG Demo Project - Available Commands:"
	@echo "======================================"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Installation
install: ## Install production dependencies
	pip install -r requirements.txt

install-dev: ## Install development dependencies
	pip install -r requirements.txt
	pip install -r requirements-dev.txt
	pre-commit install

# Environment Management
clean: ## Clean up cache and temporary files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	rm -rf build/ dist/ .coverage htmlcov/ .tox/

# Code Quality
lint: ## Run linting (flake8)
	flake8 .

format: ## Format code (black + isort)
	black .
	isort .

format-check: ## Check if code formatting is correct
	black --check .
	isort --check-only .

type-check: ## Run type checking (mypy)
	mypy .

# Testing
test: ## Run tests
	pytest

test-cov: ## Run tests with coverage
	pytest --cov=. --cov-report=html --cov-report=term-missing

test-fast: ## Run tests (excluding slow tests)
	pytest -m "not slow"

# Security
security: ## Run security checks
	bandit -r . -x tests/
	safety check

# Application
run: ## Run Streamlit application
	streamlit run streamlit_app.py

run-debug: ## Run Streamlit application in debug mode
	streamlit run streamlit_app.py --logger.level=debug

# Documentation
docs: ## Generate documentation
	sphinx-build -b html docs docs/_build/html

docs-serve: ## Serve documentation locally
	python -m http.server 8000 --directory docs/_build/html

# Development Tools
pre-commit: ## Run pre-commit hooks on all files
	pre-commit run --all-files

pre-commit-update: ## Update pre-commit hooks
	pre-commit autoupdate

deps-check: ## Check for dependency updates
	pip list --outdated

deps-tree: ## Show dependency tree
	pipdeptree

# Quality Assurance (All checks)
qa: format-check lint type-check security test ## Run all quality assurance checks

# CI/CD Simulation
ci: clean install-dev qa ## Simulate CI/CD pipeline locally

# Project Setup
setup: clean install-dev pre-commit ## Initial project setup
	@echo "🎉 Project setup complete!"
	@echo "Run 'make run' to start the application"

# Development Workflow
dev: format lint type-check test-fast ## Quick development workflow

# Production Preparation
prod-check: clean install qa test-cov security ## Production readiness check
	@echo "✅ Production readiness check complete!"

# Version Information
version: ## Show version information
	@echo "Python: $$(python --version)"
	@echo "Pip: $$(pip --version)"
	@echo "Streamlit: $$(streamlit version)"
	@echo "Project: RAG Demo v0.1.0"