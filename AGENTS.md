# AGENTS.md

## Writing Style

- Do not use em dashes (—) or double hyphens (--). Restructure sentences instead.
- Do not use local/inline imports unless required for performance constraints or circular imports. All imports go at the top of the file.

## Code Style

- 2-space indentation
- Google-style docstrings
- Always run `make format` before committing

## Project

- adk-redis is a Python package integrating Google ADK with Redis
- Uses `uv` for package management
- Run `make check` to format, lint, type-check, and test

