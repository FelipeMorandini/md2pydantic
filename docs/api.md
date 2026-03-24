# API Reference

## MDConverter

```python
from md2pydantic import MDConverter
```

### `MDConverter(model)`

Create a converter bound to a Pydantic v2 `BaseModel`
subclass.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `model` | `type[T]` | A Pydantic `BaseModel` subclass |

**Raises:**

- `TypeError` -- if `model` is not a `BaseModel` subclass

---

### `parse_tables(markdown, *, index=None, heading=None, partial=False)`

Extract Markdown tables and return validated model instances.

**Parameters:**

| Parameter  | Type            | Default | Description |
|------------|-----------------|---------|-------------|
| `markdown` | `str`           | --      | Markdown text to parse |
| `index`    | `int \| None`   | `None`  | 0-based table index (applied after heading filter) |
| `heading`  | `str \| None`   | `None`  | Substring to match against table headings (case-insensitive) |
| `partial`  | `bool`          | `False` | Return `PartialResult` instead of raising on failure |

**Returns:**

- `list[T]` when `partial=False`
- `PartialResult[T]` when `partial=True`

**Raises:**

- `ExtractionError` -- no tables found or no rows validate
  (only when `partial=False`)

---

### `parse_json(markdown)`

Extract a JSON code block and return a validated model.
Tries each JSON block in document order, returning the
first that validates.

**Parameters:**

| Parameter  | Type  | Description |
|------------|-------|-------------|
| `markdown` | `str` | Markdown text to parse |

**Returns:** `T` (single model instance)

**Raises:**

- `ExtractionError` -- no JSON blocks found or none
  validate

---

### `parse_yaml(markdown)`

Extract a YAML code block and return a validated model.
Tries each YAML block in document order, returning the
first that validates.

**Parameters:**

| Parameter  | Type  | Description |
|------------|-------|-------------|
| `markdown` | `str` | Markdown text to parse |

**Returns:** `T` (single model instance)

**Raises:**

- `ExtractionError` -- no YAML blocks found or none
  validate
- `ImportError` -- if `pyyaml` is not installed

---

### `parse(markdown, *, partial=False)`

Auto-detect format and parse structured data. Tries code
blocks (JSON/YAML) first, then falls back to tables.

**Parameters:**

| Parameter  | Type   | Default | Description |
|------------|--------|---------|-------------|
| `markdown` | `str`  | --      | Markdown text to parse |
| `partial`  | `bool` | `False` | Return `PartialResult` instead of raising on failure |

**Returns:**

- `T` for a single code block match (when `partial=False`)
- `list[T]` for table or JSON array match
  (when `partial=False`)
- `PartialResult[T]` when `partial=True`

**Raises:**

- `ExtractionError` -- no structured data found or none
  validates (only when `partial=False`)

---

## Exceptions

```python
from md2pydantic import (
    ExtractionError,
    MD2PydanticError,
)
```

### `MD2PydanticError`

Base exception for all md2pydantic errors. Inherits from
`Exception`.

### `ExtractionError`

Raised when structured data cannot be extracted or
validated. Inherits from `MD2PydanticError`.

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `errors` | `list[TransformError \| ModelValidationError]` | Typed error details with source locations |

Calling `str()` on an `ExtractionError` produces a
numbered, human-readable summary.

---

## Result Types

```python
from md2pydantic import PartialResult, FieldError
```

### `PartialResult[T]`

Contains both successfully parsed items and errors.

| Attribute    | Type | Description |
|--------------|------|-------------|
| `data`       | `list[T]` | Valid model instances |
| `errors`     | `list[TransformError \| ModelValidationError]` | Errors from failed items |
| `has_errors` | `bool` (property) | `True` if any items failed |

### `FieldError`

A single field-level validation error.

| Attribute     | Type  | Description |
|---------------|-------|-------------|
| `field`       | `str` | Field name that failed |
| `message`     | `str` | Pydantic error message |
| `input_value` | `Any` | Value that was rejected |
| `error_type`  | `str` | Pydantic error type string |

### `TransformError`

Error from the transform phase (JSON/YAML parsing failed).

| Attribute     | Type            | Description |
|---------------|-----------------|-------------|
| `phase`       | `"transform"`   | Always `"transform"` |
| `message`     | `str`           | Error description |
| `location`    | `BlockLocation` | Source location |
| `raw_content` | `str`           | Original block text |

### `ModelValidationError`

Error from the validation phase (Pydantic rejected data).

| Attribute      | Type | Description |
|----------------|------|-------------|
| `phase`        | `"validate"` | Always `"validate"` |
| `field_errors` | `tuple[FieldError, ...]` | Per-field errors |
| `location`     | `BlockLocation \| RowLocation` | Source location |
| `raw_input`    | `dict[str, Any]` | Dict passed to Pydantic |
