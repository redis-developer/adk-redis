.PHONY: install dev test test-unit test-integration redis-up redis-down lint lint-fix format type-check clean build publish check

# Install package
install:
	uv pip install -e .

# Install with dev dependencies
dev:
	uv pip install -e ".[all,dev]"

# Run all tests
test:
	uv run pytest

# Run unit tests only (skip integration)
test-unit:
	uv run pytest --ignore=tests/integration

# Run integration tests. Requires Redis 8.4+ at $$REDIS_URL (default redis://localhost:6399)
test-integration:
	uv run pytest tests/integration

# Spin up (or reuse) a Redis 8.4 container on :6399 for integration tests
redis-up:
	@if docker ps -a --format '{{.Names}}' | grep -q '^adk-redis-it$$'; then \
		docker start adk-redis-it >/dev/null && echo "Reusing existing adk-redis-it container"; \
	else \
		docker run -d --name adk-redis-it -p 6399:6379 redis:8.4 >/dev/null && echo "Started adk-redis-it on :6399"; \
	fi

# Stop and remove the integration Redis container
redis-down:
	@docker rm -f adk-redis-it >/dev/null 2>&1 || true
	@echo "adk-redis-it removed"

# Run tests with coverage
test-cov:
	uv run pytest --cov=adk_redis --cov-report=html --cov-report=term

# Run linting
lint:
	uv run ruff check src tests examples

# Fix linting errors automatically
lint-fix:
	uv run ruff check --fix --unsafe-fixes src tests examples

# Format code (Google ADK-Python style: pyink + isort)
# Note: pyink must run first, then isort, to avoid conflicts
format:
	uv run pyink src tests examples
	uv run isort src tests examples

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
