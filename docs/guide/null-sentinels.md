# Null Sentinels

md2pydantic recognizes common placeholder values in table
cells and converts them to `None` for optional fields.

## Example

```python
from pydantic import BaseModel
from md2pydantic import MDConverter

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

## Recognized Sentinels

The following values are treated as `None`:

| Sentinel | Example cell |
|----------|-------------|
| Empty    | `\|  \|`      |
| `N/A`    | `\| N/A \|`  |
| `NA`     | `\| NA \|`   |
| `null`   | `\| null \|` |
| `-`      | `\| - \|`    |
| `--`     | `\| -- \|`  |

Matching is **case-insensitive**: `n/a`, `N/A`, `Null`,
and `NULL` are all treated the same.

!!! warning
    The target field **must** be `Optional` (e.g.,
    `float | None = None`). If a sentinel value appears
    in a required field, Pydantic will raise a validation
    error.
