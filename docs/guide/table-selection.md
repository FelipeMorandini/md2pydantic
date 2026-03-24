# Table Selection

When a Markdown document contains multiple tables, you can
select specific ones using the `heading` and `index`
parameters.

## Filter by Heading

Use `heading=` to select tables that appear under a matching
Markdown heading:

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

current = MDConverter(User).parse_tables(
    markdown, heading="Current Staff"
)
# [User(name='Alice', age=30, active=True)]

former = MDConverter(User).parse_tables(
    markdown, heading="Former Staff"
)
# [User(name='Bob', age=25, active=False),
#  User(name='Eve', age=35, active=False)]
```

Heading matching is **case-insensitive** and supports
**substring** matches. For example, `heading="current"`
would also match the heading `## Current Staff`.

## Filter by Index

Use `index=` to select a table by its 0-based position:

```python
first_table = MDConverter(User).parse_tables(
    markdown, index=0
)
second_table = MDConverter(User).parse_tables(
    markdown, index=1
)
```

!!! note
    When both `heading` and `index` are provided, the
    heading filter is applied first, then the index selects
    among the filtered results. So `heading="Staff",
    index=0` returns the first table under any heading
    containing "Staff".
