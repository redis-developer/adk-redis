# Contributing to adk-redis

Thank you for your interest in contributing to adk-redis! This document provides
guidelines and information for contributors.

## Development Setup

### Prerequisites

- Python 3.10 or higher
- [uv](https://docs.astral.sh/uv/) package manager

### Quick Start

```bash
# Clone the repository
git clone https://github.com/redis/adk-redis.git
cd adk-redis

# Install dependencies (including dev dependencies)
make dev

# Run all checks (format, lint, type-check, test)
make check
```

### Available Commands

| Command | Description |
|---------|-------------|
| `make dev` | Install all dependencies including dev extras |
| `make format` | Format code with pyink and isort |
| `make format-check` | Check formatting without making changes |
| `make lint` | Run ruff linter |
| `make type-check` | Run mypy type checker |
| `make test` | Run pytest test suite |
| `make check` | Run all checks (format-check, lint, type-check, test) |
| `make clean` | Remove build artifacts |

## Coding Style

This project follows **Google Python Style Guide** conventions, matching the
[ADK-Python core](https://github.com/google/adk-python) project.

### Formatting

- **Formatter**: [pyink](https://github.com/google/pyink) (Google's fork of black)
- **Import sorter**: [isort](https://pycqa.github.io/isort/) with Google profile
- **Line length**: 80 characters
- **Indentation**: 2 spaces (Google standard)
- **Quotes**: Majority quotes (uses whichever style is more common in the file)

### Type Hints

Use modern Python 3.10+ type hint syntax:

```python
# Preferred (Python 3.10+)
def process(items: list[str], config: Config | None = None) -> dict[str, Any]:
    ...

# Avoid (legacy typing module)
from typing import Dict, List, Optional, Union
def process(items: List[str], config: Optional[Config] = None) -> Dict[str, Any]:
    ...
```

**Type hint guidelines:**

| Legacy | Modern (use this) |
|--------|-------------------|
| `Optional[X]` | `X \| None` |
| `Union[X, Y]` | `X \| Y` |
| `List[X]` | `list[X]` |
| `Dict[K, V]` | `dict[K, V]` |
| `Tuple[X, Y]` | `tuple[X, Y]` |
| `Set[X]` | `set[X]` |

For `Callable` and `Coroutine`, import from `collections.abc`:

```python
from collections.abc import Callable, Coroutine
```

### Imports

Follow Google-style single-line imports:

```python
# Standard library
import logging
import time
from functools import cached_property
from typing import TYPE_CHECKING
from typing import Any
from typing import Literal

# Third-party
from google.adk.memory.base_memory_service import BaseMemoryService
from pydantic import BaseModel
from pydantic import Field

# Local
from adk_redis.memory._utils import extract_text_from_event
```

Use `TYPE_CHECKING` for imports only needed for type hints:

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from google.adk.sessions.session import Session
```

### Docstrings

Use Google-style docstrings:

```python
def search_memory(
    self, *, app_name: str, user_id: str, query: str
) -> SearchMemoryResponse:
    """Search for memories using semantic matching.

    Performs semantic search against long-term memory with optional
    recency boosting.

    Args:
        app_name: The application name (used as namespace).
        user_id: The user ID to filter memories.
        query: The search query for semantic matching.

    Returns:
        SearchMemoryResponse containing matching MemoryEntry objects.

    Raises:
        ValueError: If query is empty.
    """
```

### Logging

Use the `adk_redis.` prefix for logger names:

```python
import logging

logger = logging.getLogger("adk_redis." + __name__)
```

## Type Checking

This project uses **strict mypy** configuration matching ADK-Python core:

```toml
[tool.mypy]
python_version = "3.10"
strict = true
disable_error_code = ["import-not-found", "import-untyped", "unused-ignore"]
plugins = ["pydantic.mypy"]
```

Run type checking with:

```bash
make type-check
```

## Testing

Tests are written using pytest with pytest-asyncio for async tests.

```bash
# Run all tests
make test

# Run specific test file
uv run pytest tests/tools/test_vector_search.py -v

# Run with coverage
uv run pytest --cov=adk_redis --cov-report=term-missing
```

## Pull Request Process

1. Fork the repository and create a feature branch
2. Make your changes following the coding style guidelines
3. Ensure all checks pass: `make check`
4. Write or update tests as needed
5. Update documentation if applicable
6. Submit a pull request with a clear description

## License

By contributing to adk-redis, you agree that your contributions will be
licensed under the Apache License 2.0.
