"""Unit tests for the MDConverter public API (Issue #7).

Covers parse_tables, parse_json, parse_yaml, parse (auto-detect),
and the exception hierarchy.
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Test models
# ---------------------------------------------------------------------------


class User(BaseModel):
    name: str
    age: int
    active: bool


class Item(BaseModel):
    title: str
    price: int


class Config(BaseModel):
    host: str
    port: int
    debug: bool


# ---------------------------------------------------------------------------
# parse_tables
# ---------------------------------------------------------------------------


class TestParseTablesBasic:
    """Basic table extraction through the full pipeline."""

    def test_basic_table_returns_model_instances(self) -> None:
        from md2pydantic import MDConverter

        md = (
            "| name | age | active |\n"
            "| --- | --- | --- |\n"
            "| Alice | 30 | Yes |\n"
            "| Bob | 25 | No |\n"
        )
        results = MDConverter(User).parse_tables(md)
        assert len(results) == 2
        assert results[0].name == "Alice"
        assert results[0].age == 30
        assert results[0].active is True
        assert results[1].name == "Bob"
        assert results[1].age == 25
        assert results[1].active is False

    def test_bool_coercion_yes_no(self) -> None:
        from md2pydantic import MDConverter

        md = (
            "| name | age | active |\n"
            "| --- | --- | --- |\n"
            "| Alice | 1 | Yes |\n"
            "| Bob | 2 | No |\n"
        )
        results = MDConverter(User).parse_tables(md)
        assert results[0].active is True
        assert results[1].active is False

    def test_numeric_string_coercion(self) -> None:
        from md2pydantic import MDConverter

        md = "| title | price |\n| --- | --- |\n| Widget | 42 |\n"
        results = MDConverter(Item).parse_tables(md)
        assert results[0].price == 42
        assert isinstance(results[0].price, int)

    def test_index_selects_specific_table(self) -> None:
        from md2pydantic import MDConverter

        md = (
            "| title | price |\n"
            "| --- | --- |\n"
            "| First | 10 |\n"
            "\n"
            "| title | price |\n"
            "| --- | --- |\n"
            "| Second | 20 |\n"
        )
        results = MDConverter(Item).parse_tables(md, index=1)
        assert len(results) == 1
        assert results[0].title == "Second"

    def test_heading_filters_by_heading(self) -> None:
        from md2pydantic import MDConverter

        md = (
            "## Prices\n"
            "| title | price |\n"
            "| --- | --- |\n"
            "| Gadget | 99 |\n"
            "\n"
            "## Inventory\n"
            "| title | price |\n"
            "| --- | --- |\n"
            "| Other | 50 |\n"
        )
        results = MDConverter(Item).parse_tables(md, heading="Prices")
        assert len(results) == 1
        assert results[0].title == "Gadget"

    def test_no_tables_raises_extraction_error(self) -> None:
        from md2pydantic import ExtractionError, MDConverter

        with pytest.raises(ExtractionError, match="No tables found"):
            MDConverter(Item).parse_tables("Just some plain text.")

    def test_no_rows_validate_raises_extraction_error_with_errors(self) -> None:
        from md2pydantic import ExtractionError, MDConverter

        # price must be int; "not_a_number" won't coerce
        md = "| title | price |\n| --- | --- |\n| Thing | not_a_number |\n"
        with pytest.raises(ExtractionError) as exc_info:
            MDConverter(Item).parse_tables(md)
        assert len(exc_info.value.errors) > 0

    def test_multiple_tables_returns_all_rows(self) -> None:
        from md2pydantic import MDConverter

        md = (
            "| title | price |\n"
            "| --- | --- |\n"
            "| A | 1 |\n"
            "\n"
            "| title | price |\n"
            "| --- | --- |\n"
            "| B | 2 |\n"
            "| C | 3 |\n"
        )
        results = MDConverter(Item).parse_tables(md)
        assert len(results) == 3
        titles = [r.title for r in results]
        assert titles == ["A", "B", "C"]


# ---------------------------------------------------------------------------
# parse_json
# ---------------------------------------------------------------------------


class TestParseJson:
    """JSON block extraction and validation."""

    def test_fenced_json_block_returns_model(self) -> None:
        from md2pydantic import MDConverter

        md = (
            "Here is the config:\n"
            "```json\n"
            '{"host": "localhost", "port": 8080, "debug": true}\n'
            "```\n"
        )
        result = MDConverter(Config).parse_json(md)
        assert result.host == "localhost"
        assert result.port == 8080
        assert result.debug is True

    def test_multiple_json_blocks_returns_first_valid(self) -> None:
        from md2pydantic import MDConverter

        md = (
            "```json\n"
            '{"title": "wrong model"}\n'
            "```\n"
            "\n"
            "```json\n"
            '{"host": "example.com", "port": 443, "debug": false}\n'
            "```\n"
        )
        # First block doesn't match Config (missing port, debug), second does
        result = MDConverter(Config).parse_json(md)
        assert result.host == "example.com"
        assert result.port == 443

    def test_no_json_blocks_raises_extraction_error(self) -> None:
        from md2pydantic import ExtractionError, MDConverter

        with pytest.raises(ExtractionError, match="No JSON"):
            MDConverter(Config).parse_json("No code blocks here.")

    def test_invalid_json_raises_extraction_error(self) -> None:
        from md2pydantic import ExtractionError, MDConverter

        md = "```json\n{this is not valid json at all\n```\n"
        with pytest.raises(ExtractionError):
            MDConverter(Config).parse_json(md)

    def test_json_with_trailing_commas_cleaned(self) -> None:
        from md2pydantic import MDConverter

        md = '```json\n{"host": "localhost", "port": 3000, "debug": true,}\n```\n'
        result = MDConverter(Config).parse_json(md)
        assert result.host == "localhost"
        assert result.port == 3000

    def test_json_array_with_objects_returns_first(self) -> None:
        from md2pydantic import MDConverter

        md = (
            "```json\n"
            '[{"host": "a.com", "port": 80, "debug": true},'
            ' {"host": "b.com", "port": 443, "debug": false}]\n'
            "```\n"
        )
        result = MDConverter(Config).parse_json(md)
        assert result.host == "a.com"
        assert result.port == 80


# ---------------------------------------------------------------------------
# parse_yaml
# ---------------------------------------------------------------------------


class TestParseYaml:
    """YAML block extraction and validation."""

    def test_fenced_yaml_block_returns_model(self) -> None:
        from md2pydantic import MDConverter

        md = "```yaml\nhost: localhost\nport: 9090\ndebug: true\n```\n"
        result = MDConverter(Config).parse_yaml(md)
        assert result.host == "localhost"
        assert result.port == 9090
        assert result.debug is True

    def test_no_yaml_blocks_raises_extraction_error(self) -> None:
        from md2pydantic import ExtractionError, MDConverter

        with pytest.raises(ExtractionError, match="No YAML"):
            MDConverter(Config).parse_yaml("No YAML here.")


# ---------------------------------------------------------------------------
# parse (auto-detect)
# ---------------------------------------------------------------------------


class TestParseAutoDetect:
    """Auto-detect format with the generic parse() method."""

    def test_markdown_with_json_returns_single_model(self) -> None:
        from md2pydantic import MDConverter

        md = (
            "Some text\n"
            "```json\n"
            '{"host": "auto.com", "port": 5000, "debug": false}\n'
            "```\n"
        )
        result = MDConverter(Config).parse(md)
        assert isinstance(result, Config)
        assert result.host == "auto.com"

    def test_markdown_with_table_returns_list(self) -> None:
        from md2pydantic import MDConverter

        md = "| title | price |\n| --- | --- |\n| Thingy | 5 |\n"
        result = MDConverter(Item).parse(md)
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].title == "Thingy"

    def test_markdown_with_both_prefers_code_blocks(self) -> None:
        from md2pydantic import MDConverter

        md = (
            "```json\n"
            '{"host": "preferred.com", "port": 1234, "debug": true}\n'
            "```\n"
            "\n"
            "| host | port | debug |\n"
            "| --- | --- | --- |\n"
            "| table.com | 80 | No |\n"
        )
        result = MDConverter(Config).parse(md)
        # Code block is preferred, so we get a single model, not a list
        assert isinstance(result, Config)
        assert result.host == "preferred.com"

    def test_code_block_fails_falls_back_to_table(self) -> None:
        """When code blocks don't match the model, parse() falls back to tables."""
        from md2pydantic import MDConverter

        md = (
            '```json\n{"completely": "wrong", "schema": true}\n```\n'
            "\n"
            "| title | price |\n"
            "| --- | --- |\n"
            "| Fallback | 99 |\n"
        )
        result = MDConverter(Item).parse(md)
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].title == "Fallback"

    def test_no_structured_data_raises_extraction_error(self) -> None:
        from md2pydantic import ExtractionError, MDConverter

        with pytest.raises(ExtractionError, match="No structured data"):
            MDConverter(Config).parse("Nothing useful here.")

    def test_json_array_returns_list_of_models(self) -> None:
        from md2pydantic import MDConverter

        md = (
            '```json\n[{"title": "X", "price": 10}, {"title": "Y", "price": 20}]\n```\n'
        )
        result = MDConverter(Item).parse(md)
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0].title == "X"
        assert result[1].title == "Y"


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------


class TestExceptionHierarchy:
    """Verify the exception class relationships."""

    def test_extraction_error_is_subclass_of_md2pydantic_error(self) -> None:
        from md2pydantic.models import ExtractionError, MD2PydanticError

        assert issubclass(ExtractionError, MD2PydanticError)

    def test_extraction_error_has_errors_attribute(self) -> None:
        from md2pydantic.models import ExtractionError

        err = ExtractionError("test", errors=[{"detail": "bad"}])
        assert err.errors == [{"detail": "bad"}]

    def test_extraction_error_default_errors_is_empty_list(self) -> None:
        from md2pydantic.models import ExtractionError

        err = ExtractionError("test")
        assert err.errors == []
