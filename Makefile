.PHONY: help install install-dev test coverage lint format type-check security clean build docs

help:
	@echo "OpenDental Query Tool - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  install          Install package in production mode"
	@echo "  install-dev      Install package with development dependencies"
	@echo ""
	@echo "Testing:"
	@echo "  test             Run all tests"
	@echo "  test-unit        Run unit tests only"
	@echo "  test-integration Run integration tests only"
	@echo "  coverage         Run tests with coverage report"
	@echo ""
	@echo "Code Quality:"
	@echo "  lint             Run ruff linter"
	@echo "  format           Format code with black"
	@echo "  format-check     Check code formatting without changes"
	@echo "  type-check       Run mypy type checker"
	@echo "  security         Run bandit security scanner"
	@echo "  quality          Run all code quality checks"
	@echo ""
	@echo "Build:"
	@echo "  clean            Remove build artifacts"
	@echo "  build            Build distribution packages"
	@echo "  build-exe        Build standalone executable with PyInstaller"
	@echo "  docs             Generate documentation"
	@echo ""
	@echo "Utilities:"
	@echo "  pre-commit       Install pre-commit hooks"
	@echo "  update-deps      Update requirements files"

# Installation
install:
	pip install -e .

install-dev:
	pip install -r requirements/dev.txt
	pip install -e .

# Testing
test:
	pytest tests/ -v

test-unit:
	pytest tests/unit/ -v

test-integration:
	pytest tests/integration/ -v

coverage:
	pytest tests/ --cov=opendental_query --cov-report=html --cov-report=term
	@echo "Coverage report: htmlcov/index.html"

# Code Quality
lint:
	ruff check src/ tests/

lint-fix:
	ruff check --fix src/ tests/

format:
	black src/ tests/

format-check:
	black --check src/ tests/

type-check:
	mypy src/

security:
	bandit -c pyproject.toml -r src/

quality: format-check lint type-check security
	@echo "All quality checks passed!"

# Build
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf coverage.xml
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete
	find . -type f -name '*.pyo' -delete

build: clean
	python -m build
	twine check dist/*

build-exe:
	python packaging/pyinstaller/build.py

docs:
	@echo "Documentation is in docs/ directory"
	@echo "  - README.md"
	@echo "  - SECURITY.md"
	@echo "  - API_REFERENCE.md"
	@echo "  - TROUBLESHOOTING.md"
	@echo "  - CONTRIBUTING.md"

# Utilities
pre-commit:
	pre-commit install
	@echo "Pre-commit hooks installed!"

update-deps:
	pip-compile requirements/base.in -o requirements/base.txt
	pip-compile requirements/dev.in -o requirements/dev.txt
	pip-compile requirements/test.in -o requirements/test.txt
