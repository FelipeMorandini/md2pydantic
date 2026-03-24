# Contributing to md2pydantic

Thanks for your interest in contributing!

## Development Setup

```bash
git clone https://github.com/FelipeMorandini/md2pydantic.git
cd md2pydantic
uv sync --extra dev
```

This installs all dependencies including dev tools (pytest, ruff, mypy, pyyaml).

## Running Checks

```bash
uv run pytest              # run all tests
uv run ruff check .        # lint
uv run ruff format .       # auto-format
uv run mypy src/md2pydantic  # type check
```

All checks must pass before submitting a PR.

## Branch Conventions

- `feat/<description>` -- new features
- `fix/<description>` -- bug fixes
- `chore/<description>` -- maintenance, CI, tooling
- `docs/<description>` -- documentation only

## Pull Request Process

1. Create a feature branch from `main`
2. Make your changes with tests
3. Ensure all checks pass (`pytest`, `ruff`, `mypy`)
4. Open a PR targeting `main`
5. CI runs automatically (lint, type check, test across Python 3.10-3.13)
6. Copilot review is requested automatically

## Code Style

- Python 3.10+ syntax (`X | Y` unions, etc.)
- Type hints on all functions (mypy strict mode)
- Line length: 88 characters (ruff enforced)
- Import sorting: isort via ruff

## Project Architecture

The library follows a **Seek, Clean, Validate** pipeline:

- **`parser.py`** (Scanner) -- regex/heuristics to find blocks in Markdown
- **`transformers.py`** (Transformer) -- clean and convert blocks to dicts
- **`validators.py`** (Validator) -- pre-process and validate against Pydantic models
- **`converter.py`** (MDConverter) -- public API orchestrating the pipeline
- **`models.py`** -- data models, exceptions, and type definitions

## Reporting Issues

Use [GitHub Issues](https://github.com/FelipeMorandini/md2pydantic/issues) for bug reports and feature requests.
