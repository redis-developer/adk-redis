# Build and Test

## Prerequisites

- Python 3.10 or newer (`requires-python = ">=3.10"`).
- `uv` (https://docs.astral.sh/uv/).
- For end-to-end paths, a running Redis 8 instance and Agent Memory
  Server are convenient; the unit tests use `fakeredis` and a fake AMS
  client where possible.

## Make targets

```
make install        uv sync (project + dev deps)
make dev            install + pre-commit hooks
make format         ruff format (apply)
make format-check   ruff format --check
make lint           ruff lint
make lint-fix       ruff lint --fix
make type-check     mypy
make test           pytest
make test-cov       pytest with coverage
make check          format-check + lint + type-check + test
make build          wheel + sdist
make publish        publish to PyPI (release flow)
make clean          remove caches and build artifacts
```

`make check` is the canonical pre-commit gate.

## Coverage policy

The project tracks coverage with `make test-cov` (writes `coverage.xml`
and `htmlcov/`). New code in `sessions/`, `memory/`, and `tools/`
should ship with tests in the matching subdirectory under `tests/`.

## Running a single test

```
uv run pytest tests/sessions/test_working_memory.py::<test_name> -vv
uv run pytest tests/tools/test_vector_search.py -vv
```

## Building the docs

The Makefile does not (yet) include docs targets. Build directly with
Sphinx:

```
uv pip install -r docs/requirements.txt
uv run sphinx-build -W -b html docs docs/_build/html
python -m http.server -d docs/_build/html 8000
```

The Python package reference under `docs/api/python/` uses
`sphinx.ext.autosummary` with `:recursive:`. If you add a new top-level
module under `src/adk_redis/`, list it in `docs/api/python/index.rst`.

The build should complete with zero warnings. `-W` is required so that
any warning fails the build.

## CI gates (target state)

- `make check` on every PR.
- `sphinx-build -W` on every PR.

## Fast iteration loops

When changing the working-memory session service:

```
uv run pytest tests/sessions/ -x -vv
```

When changing the long-term memory service or memory tools:

```
uv run pytest tests/memory/ -x -vv
```

When changing a search tool:

```
uv run pytest tests/tools/ -x -vv
```

When verifying re-exports after a refactor:

```
uv run pytest tests/test_imports.py -vv
```
