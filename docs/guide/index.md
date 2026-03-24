# User Guide

md2pydantic supports three input formats, each with a
dedicated parsing method.

## Markdown Tables

Pipe-delimited tables are parsed row-by-row into a list of
model instances. Headers become field names.

See [Markdown Tables](tables.md).

## JSON Blocks

Fenced (` ```json `) and inline `{...}` JSON blocks are
extracted and validated. Includes recovery for common LLM
quirks like trailing commas and unquoted keys.

See [JSON Blocks](json.md).

## YAML Blocks

Fenced (` ```yaml `) blocks are extracted and validated.
Requires the `pyyaml` dependency.

See [YAML Blocks](yaml.md).

## Auto-Detect

The `parse()` method tries code blocks first, then falls
back to tables. Use it when you do not know the format
in advance.

See [Auto-Detect](auto-detect.md).

## Additional Topics

- [Table Selection](table-selection.md) -- filter tables
  by heading or index
- [Null Sentinels](null-sentinels.md) -- handle missing
  values gracefully
- [Error Handling](error-handling.md) -- structured error
  reporting
- [Partial Results](partial-results.md) -- get valid rows
  even when some fail
