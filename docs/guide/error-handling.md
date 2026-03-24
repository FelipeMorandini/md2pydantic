# Error Handling

## ExtractionError

When md2pydantic cannot extract valid data, it raises
`ExtractionError`:

```python
from md2pydantic import MDConverter, ExtractionError

try:
    result = MDConverter(MyModel).parse_tables(
        "no tables here"
    )
except ExtractionError as e:
    print(e)         # Human-readable summary
    print(e.errors)  # List of typed error details
```

`ExtractionError` is raised when:

- No structured data is found in the input
- Structured data is found but none validates against
  the model

## The `.errors` Attribute

Each entry in `e.errors` is one of two types:

### TransformError

Raised during the parsing phase when raw content cannot be
converted to a Python dictionary. Contains:

- `phase` -- always `"transform"`
- `message` -- description of what went wrong
- `location` -- `BlockLocation` with line numbers
- `raw_content` -- the original block text

### ModelValidationError

Raised during the validation phase when Pydantic rejects
the data. Contains:

- `phase` -- always `"validate"`
- `field_errors` -- tuple of `FieldError` objects
- `location` -- `BlockLocation` or `RowLocation`
- `raw_input` -- the dict that was passed to Pydantic

Each `FieldError` has:

- `field` -- the field name that failed
- `message` -- Pydantic's error message
- `input_value` -- the value that was rejected
- `error_type` -- Pydantic's error type string

## Exception Hierarchy

```
Exception
  └── MD2PydanticError
        └── ExtractionError
```

You can catch `MD2PydanticError` to handle all library
exceptions, or `ExtractionError` for extraction-specific
failures.

## Human-Readable Output

Calling `str()` on an `ExtractionError` produces a
numbered summary:

```
No table rows matched the model
  [1] Validation error in table 0, row 0: age: Input
      should be a valid integer; active: Input should
      be a valid boolean
```
