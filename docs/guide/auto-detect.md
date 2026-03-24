# Auto-Detect

## Usage

The `parse()` method automatically detects the format of
structured data in the Markdown input:

```python
from pydantic import BaseModel
from md2pydantic import MDConverter

class Item(BaseModel):
    name: str
    quantity: int

result = MDConverter(Item).parse(markdown)
```

## Detection Priority

`parse()` follows this order:

1. **Code blocks** (JSON and YAML) -- scanned first because
   fenced blocks are a stronger signal of structure.
2. **Tables** -- used as a fallback when no code blocks
   match the model.

Within code blocks, all blocks are tried in document order.
The first block that validates against the model wins.

## Return Type

The return type depends on the detected format:

| Detected format | Return type |
|----------------|-------------|
| JSON object    | `T` (single instance) |
| YAML object    | `T` (single instance) |
| JSON array     | `list[T]` |
| YAML array     | `list[T]` |
| Markdown table | `list[T]` |

## When to Use `parse()` vs Specific Methods

Use `parse()` when:

- You do not know the format in advance
- The input could be either a code block or a table

Use `parse_tables()`, `parse_json()`, or `parse_yaml()`
when:

- You know the exact format and want to enforce it
- You need table-specific parameters like `heading` or
  `index`
- You want a predictable return type (`list[T]` for tables,
  `T` for code blocks)
