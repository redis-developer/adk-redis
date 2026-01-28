.PHONY: install dev test lint format type-check clean build publish check

# Install package
install:
	uv pip install -e .

# Install with dev dependencies
dev:
	uv pip install -e ".[all,dev]"

# Run tests
test:
	uv run pytest

# Run tests with coverage
test-cov:
	uv run pytest --cov=adk_redis --cov-report=html --cov-report=term

# Run linting
lint:
	uv run ruff check src tests examples

# Format code (Google ADK-Python style: pyink + isort)
format:
	uv run isort src tests examples
	uv run pyink src tests examples

# Check formatting without making changes
format-check:
	uv run isort --check-only src tests examples
	uv run pyink --check src tests examples

# Type checking (strict mode)
type-check:
	uv run mypy src

# Run all checks (format, lint, type-check, test)
check: format-check lint type-check test

# Clean build artifacts
clean:
	rm -rf build dist *.egg-info .pytest_cache .mypy_cache .ruff_cache htmlcov
	find . -type d -name __pycache__ -exec rm -rf {} +

# Build package
build: clean
	uv build

# Publish to PyPI
publish: build
	uv publish
