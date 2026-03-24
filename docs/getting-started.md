# Getting Started

## Requirements

- Python 3.10 or later
- Pydantic v2

## Installation

=== "pip"

    ```bash
    pip install md2pydantic
    ```

=== "uv"

    ```bash
    uv add md2pydantic
    ```

### Optional Extras

```bash
pip install md2pydantic[yaml]    # YAML support (pyyaml)
pip install md2pydantic[pandas]  # DataFrame conversion
```

## Complete Example

Define a Pydantic model whose field names match the table
headers exactly (case-sensitive):

```python
from pydantic import BaseModel
from md2pydantic import MDConverter

class Product(BaseModel):
    name: str
    price: float
    in_stock: bool

markdown = """
Here are the products currently available:

| name       | price | in_stock |
|------------|-------|----------|
| Widget     | 9.99  | Yes      |
| Gadget     | 24.50 | No       |
| Doohickey  | 3.75  | Yes      |
"""

products = MDConverter(Product).parse_tables(markdown)
```

## Understanding the Output

`parse_tables` returns a `list` of validated model instances,
one per table row:

```python
for p in products:
    print(f"{p.name}: ${p.price} (in stock: {p.in_stock})")

# Widget: $9.99 (in stock: True)
# Gadget: $24.5 (in stock: False)
# Doohickey: $3.75 (in stock: True)
```

Type coercion happens automatically:

- `"9.99"` (string in Markdown) becomes `9.99` (`float`)
- `"Yes"` / `"No"` become `True` / `False` (`bool`)

Pydantic handles numeric coercion. md2pydantic handles
boolean word mapping before passing data to Pydantic.

## Next Steps

- [Markdown Tables](guide/tables.md) -- table parsing details
- [JSON Blocks](guide/json.md) -- extract JSON from Markdown
- [YAML Blocks](guide/yaml.md) -- extract YAML from Markdown
- [Auto-Detect](guide/auto-detect.md) -- let md2pydantic
  choose the format
- [Error Handling](guide/error-handling.md) -- handle
  extraction failures
