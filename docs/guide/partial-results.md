# Partial Results

By default, `parse_tables` raises `ExtractionError` if
**no** rows validate. But when some rows are valid and
others are not, all valid rows are still returned.

Use `partial=True` when you want access to **both** the
valid rows and the errors for invalid rows.

## Usage

```python
from pydantic import BaseModel
from md2pydantic import MDConverter, PartialResult

class User(BaseModel):
    name: str
    age: int
    active: bool

markdown = """
| name  | age     | active |
|-------|---------|--------|
| Alice | 30      | Yes    |
| Bob   | unknown | No     |
| Carol | 28      | Yes    |
"""

result = MDConverter(User).parse_tables(
    markdown, partial=True
)
```

## The PartialResult Object

`PartialResult` contains:

- `result.data` -- list of valid model instances
- `result.errors` -- list of `TransformError` or
  `ModelValidationError` objects
- `result.has_errors` -- `True` if any rows failed

```python
print(len(result.data))    # 2 (Alice and Carol)
print(result.has_errors)   # True (Bob failed)

for err in result.errors:
    print(err)
```

## When to Use Partial Results

Partial results are useful when:

- You are processing LLM output that may contain some
  invalid rows mixed with valid data
- You want to log errors without losing the good data
- You need to report which specific rows failed and why

## Supported Methods

`partial=True` is supported on:

- `parse_tables()` -- errors are per-row
- `parse()` -- errors are per-block or per-row depending
  on the detected format

!!! note
    `parse_json()` and `parse_yaml()` do not support
    `partial` because they return a single model instance.
    Use `parse(partial=True)` if you need partial-result
    semantics with code blocks.
