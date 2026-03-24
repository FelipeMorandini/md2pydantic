"""Integration tests for structured error reporting (Issue #8)."""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from md2pydantic import ExtractionError, MDConverter, PartialResult
from md2pydantic.models import (
    BlockLocation,
    ModelValidationError,
    RowLocation,
    TransformError,
)

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


# ---------------------------------------------------------------------------
# 1. Table with mixed valid/invalid rows (partial=True)
# ---------------------------------------------------------------------------


class TestTableMixedRowsPartialTrue:
    """partial=True returns PartialResult with valid data and errors."""

    def test_partial_result_contains_valid_rows_and_errors(self) -> None:
        md = """\
| name  | age       | active |
|-------|-----------|--------|
| Alice | 30        | Yes    |
| Bob   | not-a-num | No     |
| Carol | 25        | Yes    |
"""
        result = MDConverter(User).parse_tables(md, partial=True)

        assert isinstance(result, PartialResult)
        # Alice and Carol should validate successfully
        assert len(result.data) == 2
        assert result.data[0].name == "Alice"
        assert result.data[1].name == "Carol"

        # Bob's row should produce a ModelValidationError
        assert result.has_errors
        assert len(result.errors) == 1
        err = result.errors[0]
        assert isinstance(err, ModelValidationError)
        assert err.phase == "validate"

        # Location should be a RowLocation pointing at the bad row
        loc = err.location
        assert isinstance(loc, RowLocation)
        assert loc.table_index == 0
        assert loc.row_index == 1  # Bob is the second row (0-indexed)

        # Field errors should mention the 'age' field
        field_names = [fe.field for fe in err.field_errors]
        assert "age" in field_names

        # raw_input should contain the original values
        assert err.raw_input["name"] == "Bob"
        assert err.raw_input["age"] == "not-a-num"


# ---------------------------------------------------------------------------
# 2. Table with mixed rows (partial=False, default)
# ---------------------------------------------------------------------------


class TestTableMixedRowsPartialFalse:
    """Default mode: valid rows returned, invalid rows silently dropped."""

    def test_default_mode_returns_only_valid_rows(self) -> None:
        md = """\
| name  | age       | active |
|-------|-----------|--------|
| Alice | 30        | Yes    |
| Bob   | not-a-num | No     |
| Carol | 25        | Yes    |
"""
        result = MDConverter(User).parse_tables(md)

        # Only valid rows returned as a plain list
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0].name == "Alice"
        assert result[1].name == "Carol"

    def test_default_mode_all_invalid_raises(self) -> None:
        md = """\
| name  | age       | active |
|-------|-----------|--------|
| Bob   | not-a-num | No     |
| Eve   | also-bad  | Yes    |
"""
        with pytest.raises(ExtractionError, match="No table rows matched"):
            MDConverter(User).parse_tables(md)


# ---------------------------------------------------------------------------
# 3. JSON block parse failure -> TransformError with BlockLocation
# ---------------------------------------------------------------------------


class TestJsonBlockParseFailure:
    """Fenced block with unparseable content produces TransformError."""

    def test_unparseable_json_raises_with_transform_error(self) -> None:
        md = """\
Here is some config:

```json
this is not json at all {{{{
totally broken content @@##
```

Nothing else here.
"""
        with pytest.raises(ExtractionError) as exc_info:
            MDConverter(ServerConfig).parse_json(md)

        err = exc_info.value
        assert len(err.errors) >= 1

        transform_err = err.errors[0]
        assert isinstance(transform_err, TransformError)
        assert transform_err.phase == "transform"
        assert transform_err.message  # has a non-empty message

        # Location should be a BlockLocation
        loc = transform_err.location
        assert isinstance(loc, BlockLocation)
        assert loc.block_index == 0
        assert loc.start_line >= 1
        assert loc.end_line > loc.start_line

        # raw_content should contain the original block content
        assert "this is not json at all" in transform_err.raw_content


# ---------------------------------------------------------------------------
# 4. JSON block validation failure -> ModelValidationError with BlockLocation
# ---------------------------------------------------------------------------


class TestJsonBlockValidationFailure:
    """Valid JSON that doesn't match the model produces ModelValidationError."""

    def test_valid_json_wrong_schema_raises_with_validation_error(self) -> None:
        md = """\
```json
{
    "name": "Alice",
    "favorite_color": "blue",
    "score": 42
}
```
"""
        with pytest.raises(ExtractionError) as exc_info:
            MDConverter(ServerConfig).parse_json(md)

        err = exc_info.value
        assert len(err.errors) >= 1

        val_err = err.errors[0]
        assert isinstance(val_err, ModelValidationError)
        assert val_err.phase == "validate"

        # Location should be a BlockLocation
        loc = val_err.location
        assert isinstance(loc, BlockLocation)
        assert loc.block_index == 0

        # Field errors should mention missing required fields
        field_names = {fe.field for fe in val_err.field_errors}
        assert "host" in field_names or "port" in field_names

        # raw_input should contain the parsed JSON
        assert val_err.raw_input["name"] == "Alice"


# ---------------------------------------------------------------------------
# 5. str(ExtractionError) is human-readable
# ---------------------------------------------------------------------------


class TestExtractionErrorString:
    """ExtractionError string representation contains useful diagnostics."""

    def test_str_contains_field_names_and_messages_for_table(self) -> None:
        md = """\
| name  | age       | active |
|-------|-----------|--------|
| Bob   | not-a-num | No     |
"""
        with pytest.raises(ExtractionError) as exc_info:
            MDConverter(User).parse_tables(md)

        error_str = str(exc_info.value)
        # Should contain the main message
        assert "No table rows matched" in error_str
        # Should contain a numbered error detail
        assert "[1]" in error_str
        # Should mention the field name
        assert "age" in error_str
        # Should mention the location (table/row)
        assert "table" in error_str.lower()
        assert "row" in error_str.lower()

    def test_str_contains_line_numbers_for_json_block(self) -> None:
        md = """\
Some text

```json
this is not valid json
```
"""
        with pytest.raises(ExtractionError) as exc_info:
            MDConverter(ServerConfig).parse_json(md)

        error_str = str(exc_info.value)
        # Should mention "lines" for block-level errors
        assert "lines" in error_str.lower() or "line" in error_str.lower()
        # Should contain some error detail
        assert "[1]" in error_str

    def test_str_validation_error_for_json_block(self) -> None:
        md = """\
```json
{"host": "localhost", "port": "not-a-port", "debug": "not-bool"}
```
"""
        with pytest.raises(ExtractionError) as exc_info:
            MDConverter(ServerConfig).parse_json(md)

        error_str = str(exc_info.value)
        # Should mention "block at lines"
        assert "block at lines" in error_str
        # Should mention field names
        assert "port" in error_str


# ---------------------------------------------------------------------------
# 6. parse() with partial=True on tables (auto-detect)
# ---------------------------------------------------------------------------


class TestParseAutoDetectPartial:
    """parse() with partial=True auto-detects tables and returns PartialResult."""

    def test_parse_partial_on_table_returns_partial_result(self) -> None:
        md = """\
| name  | age       | active |
|-------|-----------|--------|
| Alice | 30        | Yes    |
| Bob   | not-a-num | No     |
"""
        result = MDConverter(User).parse(md, partial=True)

        assert isinstance(result, PartialResult)
        assert len(result.data) == 1
        assert result.data[0].name == "Alice"
        assert result.has_errors
        assert len(result.errors) == 1

        err = result.errors[0]
        assert isinstance(err, ModelValidationError)
        loc = err.location
        assert isinstance(loc, RowLocation)

    def test_parse_partial_no_data_returns_empty_partial(self) -> None:
        md = "Just plain text, nothing structured."
        result = MDConverter(User).parse(md, partial=True)

        assert isinstance(result, PartialResult)
        assert len(result.data) == 0


# ---------------------------------------------------------------------------
# 7. Multiple tables with errors
# ---------------------------------------------------------------------------


class TestMultipleTablesWithErrors:
    """Two tables, one valid one invalid, captured in PartialResult."""

    def test_multiple_tables_mixed_validity(self) -> None:
        md = """\
## Good Team

| name  | age | active |
|-------|-----|--------|
| Alice | 30  | Yes    |
| Carol | 25  | Yes    |

## Bad Team

| name  | age       | active |
|-------|-----------|--------|
| Bob   | not-a-num | No     |
| Eve   | also-bad  | No     |
"""
        result = MDConverter(User).parse_tables(md, partial=True)

        assert isinstance(result, PartialResult)

        # Good Team rows should validate
        assert len(result.data) == 2
        assert result.data[0].name == "Alice"
        assert result.data[1].name == "Carol"

        # Bad Team rows should produce errors
        assert result.has_errors
        assert len(result.errors) == 2

        # Verify errors reference the correct table
        for err in result.errors:
            assert isinstance(err, ModelValidationError)
            loc = err.location
            assert isinstance(loc, RowLocation)
            assert loc.table_index == 1  # second table (0-indexed)

        # Verify the row indices within the second table
        row_indices = sorted(e.location.row_index for e in result.errors)
        assert row_indices == [0, 1]

    def test_multiple_tables_both_have_mixed_rows(self) -> None:
        md = """\
## Team A

| name  | age       | active |
|-------|-----------|--------|
| Alice | 30        | Yes    |
| Bad1  | not-a-num | No     |

## Team B

| name  | age       | active |
|-------|-----------|--------|
| Bad2  | also-bad  | Yes    |
| Carol | 25        | Yes    |
"""
        result = MDConverter(User).parse_tables(md, partial=True)

        assert isinstance(result, PartialResult)
        # Alice and Carol should validate
        assert len(result.data) == 2
        names = {r.name for r in result.data}
        assert names == {"Alice", "Carol"}

        # Two errors, one from each table
        assert len(result.errors) == 2
        table_indices = {e.location.table_index for e in result.errors}
        assert table_indices == {0, 1}
