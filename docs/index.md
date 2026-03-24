# md2pydantic

Extract structured data from messy Markdown into
[Pydantic v2](https://docs.pydantic.dev/) models.

Built for resilience against common LLM output quirks:
triple-backtick wrappers, trailing prose, incomplete tables,
malformed JSON, and more.

## Features

- **One-liner API** -- parse in a single call
- **Markdown tables** -- pipe-delimited tables to model lists
- **JSON blocks** -- fenced and inline, with recovery
- **YAML blocks** -- fenced YAML code blocks
- **Auto-detect** -- tries code blocks first, then tables
- **Bool coercion** -- Yes/No/Y/N/true/false/on/off
- **Null sentinels** -- N/A, NA, null, -, and empty cells
- **Table selection** -- filter by heading or index
- **Partial results** -- get valid rows even when some fail
- **Lightweight** -- only depends on `pydantic>=2.0`

## Installation

```bash
pip install md2pydantic
```

## Quick Taste

```python
from pydantic import BaseModel
from md2pydantic import MDConverter

class Product(BaseModel):
    name: str
    price: float
    in_stock: bool

md = """
| name   | price | in_stock |
|--------|-------|----------|
| Widget | 9.99  | Yes      |
| Gadget | 24.50 | No       |
"""

products = MDConverter(Product).parse_tables(md)
# [Product(name='Widget', price=9.99, in_stock=True),
#  Product(name='Gadget', price=24.5, in_stock=False)]
```

## Next Steps

- [Getting Started](getting-started.md) -- installation
  and a complete walkthrough
- [User Guide](guide/index.md) -- format-specific examples
- [API Reference](api.md) -- full method signatures
