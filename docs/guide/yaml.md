# YAML Blocks

## Fenced YAML

Extract YAML from a fenced code block:

````python
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
````

!!! warning
    YAML support requires `pyyaml`. Install it with:

    ```bash
    pip install md2pydantic[yaml]
    ```

    An `ExtractionError` is raised at parse time if `pyyaml`
    is not installed.

!!! note
    `parse_yaml` returns a **single** model instance. It
    tries each YAML block in document order and returns the
    first one that validates.

## Inline YAML

Inline (unfenced) YAML is not supported. Only fenced
` ```yaml` blocks are detected.
