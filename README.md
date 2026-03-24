# md2pydantic

[![PyPI](https://img.shields.io/pypi/v/md2pydantic)](https://pypi.org/project/md2pydantic/)
[![Python Versions](https://img.shields.io/pypi/pyversions/md2pydantic)](https://pypi.org/project/md2pydantic/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://github.com/FelipeMorandini/md2pydantic/blob/main/LICENSE)
[![CI](https://github.com/FelipeMorandini/md2pydantic/actions/workflows/ci.yml/badge.svg)](https://github.com/FelipeMorandini/md2pydantic/actions/workflows/ci.yml)

Extract structured data from messy Markdown into [Pydantic v2](https://docs.pydantic.dev/) models.

Built for resilience against common LLM output quirks: triple-backtick wrappers, trailing prose, incomplete tables, malformed JSON, and more. One line of code turns chaotic Markdown into validated, typed Python objects.

## Features

- **One-liner API** -- `MDConverter(Model).parse_tables(md)` gets you started in one line
- **Markdown tables** -- pipe-delimited tables become lists of Pydantic models
- **JSON blocks** -- fenced and inline JSON, with recovery for trailing commas, single quotes, unquoted keys, and truncated output
- **YAML blocks** -- fenced YAML code blocks (requires `pyyaml`)
- **Auto-detect** -- `parse()` tries code blocks first, then tables
- **Yes/No bool coercion** -- `"Yes"`, `"No"`, `"Y"`, `"N"`, `"true"`, `"false"`, `"on"`, `"off"` all map to `bool`
- **Null sentinel handling** -- empty cells, `"N/A"`, `"NA"`, `"null"`, `"-"`, `"—"` become `None` for optional fields
- **Table selection** -- filter tables by heading or index in multi-table documents
- **LLM-resilient** -- handles unclosed code fences, trailing prose, extra backticks, and nested structures
- **Pydantic v2 native** -- leverages Pydantic's own type coercion (str to int, str to float, str to datetime, etc.)
- **Lightweight** -- only dependency is `pydantic>=2.0.0`

## Installation

```bash
pip install md2pydantic
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv add md2pydantic
```

**Optional extras:**

```bash
pip install md2pydantic[yaml]    # YAML block support (pyyaml)
pip install md2pydantic[pandas]  # DataFrame conversion (pandas)
```

Requires Python 3.10+.

## Quick Start

### Parse a Markdown Table

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
"""

products = MDConverter(Product).parse_tables(markdown)
# [Product(name='Widget', price=9.99, in_stock=True),
#  Product(name='Gadget', price=24.5, in_stock=False)]
```

Pydantic handles the `str` to `float` coercion. md2pydantic handles `"Yes"` / `"No"` to `bool`.

### Parse a JSON Block

```python
from pydantic import BaseModel
from md2pydantic import MDConverter

class ServerConfig(BaseModel):
    host: str
    port: int
    debug: bool

markdown = '''Sure! Here is the server configuration:

```json
{
    "host": "localhost",
    "port": 8080,
    "debug": true,
}
```

Let me know if you need anything else!
'''

config = MDConverter(ServerConfig).parse_json(markdown)
# ServerConfig(host='localhost', port=8080, debug=True)
```

Notice the trailing comma after `true` -- md2pydantic fixes that automatically.

### Parse a YAML Block

```python
from pydantic import BaseModel
from md2pydantic import MDConverter

class ServerConfig(BaseModel):
    host: str
    port: int
    debug: bool

markdown = '''Here is your config:

```yaml
host: api.example.com
port: 443
debug: false
```
'''

config = MDConverter(ServerConfig).parse_yaml(markdown)
# ServerConfig(host='api.example.com', port=443, debug=False)
```

Requires `pyyaml`: install with `pip install md2pydantic[yaml]`.

### Auto-Detect Format

```python
from md2pydantic import MDConverter

# parse() tries JSON/YAML code blocks first, then falls back to tables
result = MDConverter(ServerConfig).parse(markdown)
```

Returns a single model instance for code blocks, or a `list` for tables and JSON arrays.

### Select Tables by Heading

When a document contains multiple tables, filter by the preceding Markdown heading:

```python
from pydantic import BaseModel
from md2pydantic import MDConverter

class User(BaseModel):
    name: str
    age: int
    active: bool

markdown = """
## Current Staff

| name  | age | active |
|-------|-----|--------|
| Alice | 30  | Yes    |

## Former Staff

| name  | age | active |
|-------|-----|--------|
| Bob   | 25  | No     |
| Eve   | 35  | No     |
"""

current = MDConverter(User).parse_tables(markdown, heading="Current Staff")
# [User(name='Alice', age=30, active=True)]

former = MDConverter(User).parse_tables(markdown, heading="Former Staff")
# [User(name='Bob', age=25, active=False), User(name='Eve', age=35, active=False)]
```

Heading matching is case-insensitive and supports substring matches. You can also select by index with `index=0`.

### Handle Null Sentinels

Empty cells and common null placeholders become `None` for optional fields:

```python
class Employee(BaseModel):
    name: str
    department: str
    salary: float | None = None

markdown = """
| name  | department  | salary |
|-------|-------------|--------|
| Alice | Engineering | 95000  |
| Bob   | Marketing   | N/A    |
| Carol | Sales       | -      |
"""

employees = MDConverter(Employee).parse_tables(markdown)
# employees[0].salary == 95000.0
# employees[1].salary is None  (from "N/A")
# employees[2].salary is None  (from "-")
```

Recognized null sentinels: `""` (empty), `"N/A"`, `"NA"`, `"null"`, `"-"`, `"—"`. Matching is case-insensitive.

### Error Handling

```python
from md2pydantic import MDConverter, ExtractionError

try:
    result = MDConverter(MyModel).parse_tables("no tables here")
except ExtractionError as e:
    print(e)            # "No tables found in markdown"
    print(e.errors)     # [] or list of field-level validation errors
```

`ExtractionError` is raised when:
- No structured data is found in the input
- Structured data is found but none of it validates against the model

`ExtractionError` inherits from `MD2PydanticError`, so you can catch either.

## Supported Formats

| Format | Method | Fenced | Inline | Recovery |
|--------|--------|--------|--------|----------|
| Markdown tables | `parse_tables()` | -- | Yes | Padded/truncated columns |
| JSON | `parse_json()` | Yes | Yes | Trailing commas, single quotes, unquoted keys, truncated JSON |
| YAML | `parse_yaml()` | Yes | -- | -- |
| Auto-detect | `parse()` | Yes | Yes | All of the above |

## API Reference

### `MDConverter(model)`

Create a converter bound to a Pydantic v2 `BaseModel` subclass.

```python
converter = MDConverter(MyModel)
```

#### `converter.parse_tables(markdown, *, index=None, heading=None) -> list[T]`

Extract Markdown tables and return validated model instances (one per row).

- `index` -- only parse the table at this 0-based position (applied after heading filter)
- `heading` -- only parse tables under headings matching this substring (case-insensitive)
- Raises `ExtractionError` if no tables are found or no rows validate

#### `converter.parse_json(markdown) -> T`

Extract a JSON code block and return a single validated model instance. Tries each JSON block in document order, returning the first that validates.

- Raises `ExtractionError` if no JSON blocks are found or none validate

#### `converter.parse_yaml(markdown) -> T`

Extract a YAML code block and return a single validated model instance.

- Raises `ExtractionError` if no YAML blocks are found or none validate
- Requires `pyyaml` (`pip install md2pydantic[yaml]`)

#### `converter.parse(markdown) -> T | list[T]`

Auto-detect format. Tries code blocks (JSON/YAML) first, then tables.

- Raises `ExtractionError` if no structured data is found or none validates

### Exceptions

| Exception | Parent | Description |
|-----------|--------|-------------|
| `MD2PydanticError` | `Exception` | Base exception for the library |
| `ExtractionError` | `MD2PydanticError` | No data found or validation failed. Has `.errors` attribute. |

## How It Works

md2pydantic follows a **Seek, Clean, Validate** pipeline:

1. **Scanner** -- Uses regex and heuristics to identify candidate blocks (JSON, YAML, Markdown tables) within the input. Handles triple-backtick enclosures, unclosed fences, and trailing prose.

2. **Transformer** -- Converts raw blocks into Python dictionaries. Fixes malformed JSON (trailing commas, single quotes, unquoted keys, truncated output). Converts table rows into dicts using headers as keys.

3. **Validator** -- Passes dictionaries to your Pydantic model. Pre-processes Yes/No booleans and null sentinels before handing off to Pydantic's native coercion engine.

## Development

```bash
git clone https://github.com/FelipeMorandini/md2pydantic.git
cd md2pydantic
uv sync --extra dev

uv run pytest              # run tests
uv run ruff check .        # lint
uv run ruff format .       # format
uv run mypy src/md2pydantic  # type check
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for more details.

## License

[MIT](LICENSE)
