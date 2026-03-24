# md2pydantic

Extract structured data from messy Markdown strings into [Pydantic v2](https://docs.pydantic.dev/) models.

Built for resilience against common LLM output quirks: triple-backtick wrappers, trailing prose, incomplete tables, malformed JSON, and more.

> **Status:** Early development (pre-alpha). Core functionality works. See [Issues](https://github.com/felipemorandini/md2pydantic/issues) for the roadmap.

## Installation

```bash
# With uv
uv add md2pydantic

# With pip
pip install md2pydantic
```

Requires Python 3.10+.

## Usage

### Tables

```python
from pydantic import BaseModel
from md2pydantic import MDConverter

class Product(BaseModel):
    name: str
    price: float
    in_stock: bool

markdown = """
| name       | price | in_stock |
|------------|-------|----------|
| Widget     | 9.99  | Yes      |
| Gadget     | 24.50 | No       |
"""

products = MDConverter(Product).parse_tables(markdown)
# [Product(name='Widget', price=9.99, in_stock=True),
#  Product(name='Gadget', price=24.5, in_stock=False)]
```

### JSON

```python
from md2pydantic import MDConverter

markdown = '''Here is the config:
```json
{"host": "localhost", "port": 8080, "debug": true}
```
'''

config = MDConverter(Config).parse_json(markdown)
```

### Auto-detect

```python
result = MDConverter(MyModel).parse(markdown)  # tries JSON/YAML, then tables
```

## Development

```bash
# Install with dev dependencies
uv sync --extra dev

# Run tests
uv run pytest

# Lint & format
uv run ruff check .
uv run ruff format .

# Type check
uv run mypy src/md2pydantic
```

## License

MIT
