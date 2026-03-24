# Supported Formats

## Overview

| Format          | Method           | Fenced | Inline | Recovery |
|-----------------|------------------|--------|--------|----------|
| Markdown tables | `parse_tables()` | --     | Yes    | Padded/truncated columns |
| JSON            | `parse_json()`   | Yes    | Yes    | Trailing commas, single quotes, unquoted keys, truncated JSON |
| YAML            | `parse_yaml()`   | Yes    | --     | --       |
| Auto-detect     | `parse()`        | Yes    | Yes    | All of the above |

## Markdown Tables

Pipe-delimited tables with a header row and separator row.
Surrounding prose is ignored. The parser handles:

- Extra whitespace in cells
- Missing or extra trailing pipes
- Padded or truncated columns (mismatched column counts)

## JSON

Both fenced (` ```json `) and inline `{...}` blocks are
detected. Recovery features fix common LLM quirks:

- **Trailing commas** -- `{"a": 1,}` becomes `{"a": 1}`
- **Single quotes** -- `{'a': 1}` becomes `{"a": 1}`
- **Unquoted keys** -- `{a: 1}` becomes `{"a": 1}`
- **Truncated JSON** -- `{"a": 1` gets its closing bracket

## YAML

Only fenced (` ```yaml `) blocks are supported. Inline
YAML is not detected due to ambiguity with plain prose.

Requires the `pyyaml` package:

```bash
pip install md2pydantic[yaml]
```

## Auto-Detect

The `parse()` method tries formats in this order:

1. Code blocks (JSON and YAML) -- higher confidence signal
2. Markdown tables -- fallback

The first block that validates against the target model is
returned.
