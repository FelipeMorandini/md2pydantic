# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-03-24

### Added

- `MDConverter` public API with `parse_tables()`, `parse_json()`, `parse_yaml()`, and `parse()` methods
- Markdown table parsing with pipe-delimited format, heading/index selection
- JSON block extraction (fenced and inline) with recovery for trailing commas, single quotes, unquoted keys, and truncated JSON
- YAML block extraction (fenced, requires pyyaml)
- Auto-detect format with `parse()`
- Yes/No/Y/N/true/false/on/off boolean coercion for bool fields
- Null sentinel handling (empty, N/A, NA, null, -, em-dash) for optional fields
- `ExtractionError` and `MD2PydanticError` exception classes
- Python 3.10, 3.11, 3.12, 3.13 support
- Full type annotations (mypy strict mode)
- GitHub Actions CI/CD with automated PyPI publishing

[0.1.0]: https://github.com/FelipeMorandini/md2pydantic/releases/tag/v0.1.0
