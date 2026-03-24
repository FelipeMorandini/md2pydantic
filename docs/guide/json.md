# JSON Blocks

## Fenced JSON

Extract JSON from a fenced code block:

````python
from pydantic import BaseModel
from md2pydantic import MDConverter

class ServerConfig(BaseModel):
    host: str
    port: int
    debug: bool

markdown = '''Here is the config:

```json
{
    "host": "localhost",
    "port": 8080,
    "debug": true
}
```
'''

config = MDConverter(ServerConfig).parse_json(markdown)
# ServerConfig(host='localhost', port=8080, debug=True)
````

!!! note
    `parse_json` returns a **single** model instance, not
    a list. It tries each JSON block in document order and
    returns the first one that validates.

## Inline JSON

md2pydantic also detects inline (unfenced) JSON objects:

```python
markdown = """
The server config is {"host": "localhost", "port": 8080,
"debug": true} as specified.
"""

config = MDConverter(ServerConfig).parse_json(markdown)
```

## Recovery Features

LLM output often contains malformed JSON. md2pydantic
attempts to fix these issues automatically:

| Issue              | Example                | Recovery          |
|--------------------|------------------------|-------------------|
| Trailing commas    | `{"a": 1,}`           | Comma removed     |
| Single quotes      | `{'a': 1}`            | Replaced with `"` |
| Unquoted keys      | `{host: "localhost"}`  | Keys quoted       |
| Truncated JSON     | `{"a": 1, "b": 2`     | Brackets closed   |

!!! tip
    Recovery is best-effort. If the JSON is too malformed
    to salvage, an `ExtractionError` is raised.
