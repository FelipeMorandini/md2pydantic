# Markdown Tables

## Basic Usage

```python
from pydantic import BaseModel
from md2pydantic import MDConverter

class User(BaseModel):
    name: str
    age: int
    active: bool

markdown = """
| name  | age | active |
|-------|-----|--------|
| Alice | 30  | Yes    |
| Bob   | 25  | No     |
"""

users = MDConverter(User).parse_tables(markdown)
# [User(name='Alice', age=30, active=True),
#  User(name='Bob', age=25, active=False)]
```

!!! note
    `parse_tables` always returns a **list** of model
    instances, even if the table has only one row.

## Header-to-Field Mapping

Table headers are mapped to model fields by exact name
match. The mapping is **case-sensitive**: a header `Name`
will not match a field named `name`.

```
| name | age |    <-- must match field names exactly
|------|-----|
| ...  | ... |
```

## Bool Coercion

md2pydantic maps common boolean words to `True`/`False`
before passing data to Pydantic. The mapping is
case-insensitive:

| Input values          | Result  |
|-----------------------|---------|
| Yes, Y, true, on, 1  | `True`  |
| No, N, false, off, 0  | `False` |

This only applies to fields typed as `bool`.

## Whitespace Handling

Leading and trailing whitespace in cell values is stripped
automatically. This means `| Alice |` and `|Alice|` both
produce `"Alice"`.

## Surrounding Prose

md2pydantic ignores prose before and after the table. LLM
output like this works fine:

```markdown
Here are the results I found:

| name  | age |
|-------|-----|
| Alice | 30  |

Let me know if you need anything else!
```
