"""Integration tests for MDConverter — the one-liner public API."""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from md2pydantic import ExtractionError, MDConverter

# ---------------------------------------------------------------------------
# Shared test models
# ---------------------------------------------------------------------------


class User(BaseModel):
    name: str
    age: int
    active: bool


class ServerConfig(BaseModel):
    host: str
    port: int
    debug: bool


class Product(BaseModel):
    name: str
    price: float
    in_stock: bool


class Employee(BaseModel):
    name: str
    department: str
    salary: float | None = None
    email: str | None = None


# ---------------------------------------------------------------------------
# 1. Spec example — Alice/Bob table with Yes/No booleans
# ---------------------------------------------------------------------------


class TestSpecExampleTable:
    """The canonical example from the project spec."""

    def test_alice_bob_table(self) -> None:
        md = """
| name  | age | active |
|-------|-----|--------|
| Alice | 30  | Yes    |
| Bob   | 25  | No     |
"""
        users = MDConverter(User).parse_tables(md)

        assert len(users) == 2

        assert users[0].name == "Alice"
        assert users[0].age == 30
        assert users[0].active is True

        assert users[1].name == "Bob"
        assert users[1].age == 25
        assert users[1].active is False

    def test_result_types_are_model_instances(self) -> None:
        md = """
| name  | age | active |
|-------|-----|--------|
| Alice | 30  | Yes    |
"""
        users = MDConverter(User).parse_tables(md)
        assert isinstance(users[0], User)


# ---------------------------------------------------------------------------
# 2. JSON block from ChatGPT-style response
# ---------------------------------------------------------------------------


class TestJsonBlock:
    """JSON fenced code blocks embedded in LLM prose."""

    def test_chatgpt_style_json_response(self) -> None:
        md = """\
Sure! Here is the server configuration you requested:

```json
{
    "host": "localhost",
    "port": 8080,
    "debug": true
}
```

Let me know if you need anything else!
"""
        config = MDConverter(ServerConfig).parse_json(md)

        assert config.host == "localhost"
        assert config.port == 8080
        assert config.debug is True

    def test_json_block_returns_model_instance(self) -> None:
        md = """
```json
{"host": "0.0.0.0", "port": 443, "debug": false}
```
"""
        config = MDConverter(ServerConfig).parse_json(md)
        assert isinstance(config, ServerConfig)


# ---------------------------------------------------------------------------
# 3. YAML block from LLM response
# ---------------------------------------------------------------------------


class TestYamlBlock:
    """YAML fenced code blocks embedded in LLM prose."""

    def test_yaml_block_parsing(self) -> None:
        md = """\
Here's the configuration in YAML format:

```yaml
host: api.example.com
port: 443
debug: false
```

This should work for your production setup.
"""
        config = MDConverter(ServerConfig).parse_yaml(md)

        assert config.host == "api.example.com"
        assert config.port == 443
        assert config.debug is False

    def test_yaml_with_yml_fence(self) -> None:
        md = """
```yml
host: staging.example.com
port: 8443
debug: true
```
"""
        config = MDConverter(ServerConfig).parse_yaml(md)
        assert config.host == "staging.example.com"
        assert config.debug is True


# ---------------------------------------------------------------------------
# 4. Auto-detect with parse()
# ---------------------------------------------------------------------------


class TestAutoDetect:
    """parse() auto-detects the format and returns the correct type."""

    def test_parse_auto_detects_json(self) -> None:
        md = """
```json
{"host": "localhost", "port": 3000, "debug": true}
```
"""
        result = MDConverter(ServerConfig).parse(md)
        # JSON block returns a single model instance
        assert isinstance(result, ServerConfig)
        assert result.port == 3000

    def test_parse_auto_detects_yaml(self) -> None:
        md = """
```yaml
host: localhost
port: 5000
debug: false
```
"""
        result = MDConverter(ServerConfig).parse(md)
        assert isinstance(result, ServerConfig)
        assert result.port == 5000

    def test_parse_auto_detects_table(self) -> None:
        md = """
| name  | age | active |
|-------|-----|--------|
| Carol | 40  | Yes    |
"""
        result = MDConverter(User).parse(md)
        # Table returns a list
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].name == "Carol"

    def test_parse_prefers_code_block_over_table(self) -> None:
        """When both JSON and table are present, JSON wins (more precise)."""
        md = """
```json
{"host": "from-json", "port": 9999, "debug": true}
```

| host      | port | debug |
|-----------|------|-------|
| from-table| 1111 | No    |
"""
        result = MDConverter(ServerConfig).parse(md)
        # Code blocks take priority
        assert isinstance(result, ServerConfig)
        assert result.host == "from-json"
        assert result.port == 9999


# ---------------------------------------------------------------------------
# 5. Table with heading selection
# ---------------------------------------------------------------------------


class TestHeadingSelection:
    """parse_tables with heading filter selects the right table."""

    def test_select_table_by_heading(self) -> None:
        md = """
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
        current = MDConverter(User).parse_tables(md, heading="Current Staff")
        assert len(current) == 1
        assert current[0].name == "Alice"

        former = MDConverter(User).parse_tables(md, heading="Former Staff")
        assert len(former) == 2
        assert former[0].name == "Bob"
        assert former[1].name == "Eve"

    def test_heading_filter_is_case_insensitive(self) -> None:
        md = """
## Team Members

| name  | age | active |
|-------|-----|--------|
| Alice | 30  | Yes    |
"""
        result = MDConverter(User).parse_tables(md, heading="team members")
        assert len(result) == 1
        assert result[0].name == "Alice"

    def test_heading_filter_substring_match(self) -> None:
        md = """
## Team Members

| name  | age | active |
|-------|-----|--------|
| Alice | 30  | Yes    |
"""
        result = MDConverter(User).parse_tables(md, heading="Team")
        assert len(result) == 1


# ---------------------------------------------------------------------------
# 6. Messy LLM JSON with trailing commas
# ---------------------------------------------------------------------------


class TestMessyJson:
    """JSON with common LLM syntax errors — trailing commas, etc."""

    def test_trailing_comma_in_json(self) -> None:
        md = """
```json
{
    "host": "localhost",
    "port": 8080,
    "debug": true,
}
```
"""
        config = MDConverter(ServerConfig).parse_json(md)
        assert config.host == "localhost"
        assert config.port == 8080
        assert config.debug is True

    def test_single_quotes_in_json(self) -> None:
        md = """
```json
{
    'host': 'localhost',
    'port': 3000,
    'debug': false
}
```
"""
        config = MDConverter(ServerConfig).parse_json(md)
        assert config.host == "localhost"
        assert config.port == 3000

    def test_unquoted_keys_in_json(self) -> None:
        md = """
```json
{
    host: "localhost",
    port: 5000,
    debug: true
}
```
"""
        config = MDConverter(ServerConfig).parse_json(md)
        assert config.host == "localhost"
        assert config.port == 5000


# ---------------------------------------------------------------------------
# 7. Table with N/A and empty cells
# ---------------------------------------------------------------------------


class TestNullAndEmptyCells:
    """Empty cells and null sentinels become None for optional fields."""

    def test_empty_cells_become_none(self) -> None:
        md = """
| name  | department  | salary | email |
|-------|-------------|--------|-------|
| Alice | Engineering | 95000  |       |
"""
        employees = MDConverter(Employee).parse_tables(md)
        assert len(employees) == 1
        assert employees[0].name == "Alice"
        assert employees[0].salary == 95000.0
        assert employees[0].email is None

    def test_na_becomes_none(self) -> None:
        md = """
| name | department | salary | email        |
|------|------------|--------|--------------|
| Bob  | Marketing  | N/A    | bob@test.com |
"""
        employees = MDConverter(Employee).parse_tables(md)
        assert len(employees) == 1
        assert employees[0].name == "Bob"
        assert employees[0].salary is None
        assert employees[0].email == "bob@test.com"

    def test_dash_becomes_none(self) -> None:
        md = """
| name  | department | salary | email |
|-------|------------|--------|-------|
| Carol | Sales      | -      | -     |
"""
        employees = MDConverter(Employee).parse_tables(md)
        assert employees[0].salary is None
        assert employees[0].email is None


# ---------------------------------------------------------------------------
# 8. Error case — no data found
# ---------------------------------------------------------------------------


class TestErrorCases:
    """ExtractionError raised when no structured data is found."""

    def test_plain_text_raises_extraction_error_on_parse_tables(self) -> None:
        md = "This is just some plain text with no tables or code blocks."
        with pytest.raises(ExtractionError, match="No tables found"):
            MDConverter(User).parse_tables(md)

    def test_plain_text_raises_extraction_error_on_parse_json(self) -> None:
        md = "Just a paragraph of prose, nothing structured here."
        with pytest.raises(ExtractionError, match="No JSON blocks found"):
            MDConverter(User).parse_json(md)

    def test_plain_text_raises_extraction_error_on_parse_yaml(self) -> None:
        md = "Nothing but plain text."
        with pytest.raises(ExtractionError, match="No YAML blocks found"):
            MDConverter(User).parse_yaml(md)

    def test_plain_text_raises_extraction_error_on_parse(self) -> None:
        md = "No structured data anywhere in this document."
        with pytest.raises(ExtractionError, match="No structured data found"):
            MDConverter(User).parse(md)

    def test_extraction_error_is_subclass_of_md2pydantic_error(self) -> None:
        from md2pydantic.models import MD2PydanticError

        with pytest.raises(MD2PydanticError):
            MDConverter(User).parse_tables("plain text")

    def test_heading_filter_no_match_raises(self) -> None:
        md = """
## Users

| name  | age | active |
|-------|-----|--------|
| Alice | 30  | Yes    |
"""
        with pytest.raises(ExtractionError, match="No tables found"):
            MDConverter(User).parse_tables(md, heading="Nonexistent Section")
