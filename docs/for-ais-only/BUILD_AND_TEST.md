# Build and Test

## Prerequisites

- Python 3.10 or newer (`requires-python = ">=3.10"`).
- `uv` (https://docs.astral.sh/uv/).
- For unit tests, `fakeredis` and mocked clients suffice; no Redis
  needed.
- For `tests/integration/`, a real Redis 8.4+ with the RediSearch module
  reachable at `$REDIS_URL` (default `redis://localhost:6399`). Spin one
  up with `make redis-up`. Integration tests skip cleanly when no
  reachable server is found.
- For end-to-end memory paths, the Agent Memory Server is convenient;
  the memory unit tests use a fake AMS client.

## Make targets

```
make install          uv sync (project + dev deps)
make dev              install + pre-commit hooks
make format           pyink + isort (apply)
make format-check     pyink + isort (check only)
make lint             ruff check
make lint-fix         ruff check --fix
make type-check       mypy
make test             pytest (unit + integration)
make test-unit        pytest, skipping tests/integration
make test-integration pytest tests/integration (needs Redis at $REDIS_URL)
make redis-up         docker run redis:8.4 on :6399 (integration target)
make redis-down       stop and remove the integration container
make test-cov         pytest with coverage
make check            format-check + lint + type-check + test
make build            wheel + sdist
make publish          publish to PyPI (release flow)
make clean            remove caches and build artifacts
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

When changing a cache provider:

```
uv run pytest tests/cache/ -x -vv
```

When running integration tests (real Redis on `:6399`):

```
make redis-up
REDIS_URL=redis://localhost:6399 make test-integration
make redis-down
```

When verifying re-exports after a refactor:

```
uv run pytest tests/test_imports.py -vv
```
