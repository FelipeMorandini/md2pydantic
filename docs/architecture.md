# Architecture

md2pydantic follows a **Seek, Clean, Validate** pipeline.
Each stage is handled by a dedicated module.

## Pipeline

```
Markdown input
    │
    ▼
┌──────────┐
│ Scanner  │  Identify candidate blocks
└────┬─────┘
     │
     ▼
┌──────────────┐
│ Transformer  │  Convert to Python dicts
└────┬─────────┘
     │
     ▼
┌───────────┐
│ Validator │  Validate against Pydantic model
└────┬──────┘
     │
     ▼
Typed model instances
```

## Stage 1: Scanner

**Module:** `parser.py`

Uses regex and heuristics to identify candidate blocks
within the Markdown input:

- Fenced code blocks (` ```json `, ` ```yaml `)
- Inline JSON objects (`{...}`)
- Pipe-delimited Markdown tables

Handles LLM-specific quirks like unclosed fences, trailing
prose, extra backticks, tilde fences (`~~~`), and nested
structures.

**Output:** `CodeBlock` or `TableBlock` objects with content
and source location metadata.

## Stage 2: Transformer

**Module:** `transformers.py`

Converts raw extracted content into Python dictionaries:

- **JSON blocks** -- parses JSON with recovery for trailing
  commas, single quotes, unquoted keys, and truncated
  output
- **YAML blocks** -- parses YAML via `pyyaml`
- **Tables** -- converts rows to dicts using headers as keys

Also performs pre-processing: boolean word mapping
(Yes/No to True/False) and null sentinel replacement.

**Output:** Python `dict` objects ready for Pydantic.

## Stage 3: Validator

**Module:** `validators.py`

Passes dictionaries to the user-defined Pydantic v2 model.
Leverages Pydantic's native type coercion (str to int, str
to float, str to datetime, etc.).

Returns either a validated model instance or structured
error details with field-level information.

**Output:** `ValidationResult` with typed data or errors.

## Orchestrator

**Module:** `converter.py`

`MDConverter` is the public API that orchestrates the full
pipeline. It is the only class users interact with
directly.

## Module Map

| Module            | Role                          |
|-------------------|-------------------------------|
| `converter.py`    | Public API (`MDConverter`)    |
| `parser.py`       | Block detection and scanning  |
| `transformers.py` | Raw content to Python dicts   |
| `validators.py`   | Pydantic model validation     |
| `models.py`       | Internal types and exceptions |
