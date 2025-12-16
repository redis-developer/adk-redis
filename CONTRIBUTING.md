# Contributing to RedisVL ADK

Thank you for your interest in contributing to RedisVL ADK!

## Development Setup

1. Clone the repository:
```bash
git clone https://github.com/redis-applied-ai/redisvl-adk-agents.git
cd redisvl-adk-agents
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install development dependencies:
```bash
pip install -e ".[dev]"
```

4. Start Redis Stack:
```bash
docker run -d -p 6379:6379 redis/redis-stack:latest
```

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=redisvl_adk --cov-report=html

# Run specific test file
pytest tests/unit/test_memory.py
```

## Code Quality

```bash
# Format code
black .
isort .

# Lint
ruff check .

# Type check
mypy redisvl_adk
```

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and linting
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## Code Style

- Follow PEP 8
- Use type hints
- Write docstrings for all public functions/classes
- Keep functions focused and small
- Write tests for new features

## Questions?

Open an issue or reach out on [Redis Discord](https://discord.gg/redis).
