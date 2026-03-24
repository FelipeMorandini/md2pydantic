"""Unit tests for structured error reporting (Issue #8).

Covers ExtractionError str representation, TransformError, ModelValidationError,
PartialResult, and the partial parameter on parse_tables / parse / _parse_code_blocks.
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from md2pydantic.converter import MDConverter
from md2pydantic.models import (
    BlockLocation,
    BlockType,
    ExtractionError,
    FieldError,
    ModelValidationError,
    PartialResult,
    RowLocation,
    TransformError,
)

# ---------------------------------------------------------------------------
# Test models
# ---------------------------------------------------------------------------


class Person(BaseModel):
    name: str
    age: int


class StrictItem(BaseModel):
    title: str
    price: int


# ---------------------------------------------------------------------------
# ExtractionError
# ---------------------------------------------------------------------------


class TestExtractionErrorStr:
    """ExtractionError.__str__ formats messages correctly."""

    def test_str_includes_message_when_no_errors(self) -> None:
        err = ExtractionError("Something went wrong")
        assert str(err) == "Something went wrong"

    def test_str_includes_transform_error_with_line_numbers(self) -> None:
        te = TransformError(
            message="Invalid JSON",
            location=BlockLocation(
                start_line=5, end_line=10, block_type=BlockType.JSON, block_index=0
            ),
            raw_content='{"bad json',
        )
        err = ExtractionError("Parse failed", errors=[te])
        s = str(err)
        assert "Parse failed" in s
        assert "Transform error" in s
        assert "5-10" in s
        assert "Invalid JSON" in s

    def test_str_includes_validation_error_with_row_location(self) -> None:
        ve = ModelValidationError(
            field_errors=(
                FieldError(
                    field="age",
                    message="value is not a valid integer",
                    input_value="abc",
                    error_type="int_parsing",
                ),
            ),
            location=RowLocation(
                table_index=0,
                row_index=2,
                table_heading="Users",
                start_line=3,
            ),
            raw_input={"name": "Alice", "age": "abc"},
        )
        err = ExtractionError("Validation failed", errors=[ve])
        s = str(err)
        assert "Validation error" in s
        assert "table 0" in s
        assert "'Users'" in s
        assert "row 2" in s
        assert "age" in s

    def test_str_includes_validation_error_with_block_location(self) -> None:
        ve = ModelValidationError(
            field_errors=(
                FieldError(
                    field="price",
                    message="value is not a valid integer",
                    input_value="free",
                    error_type="int_parsing",
                ),
            ),
            location=BlockLocation(
                start_line=1, end_line=3, block_type=BlockType.JSON, block_index=0
            ),
            raw_input={"title": "Widget", "price": "free"},
        )
        err = ExtractionError("Block validation failed", errors=[ve])
        s = str(err)
        assert "Validation error" in s
        assert "block at lines 1-3" in s
        assert "price" in s

    def test_str_handles_multiple_mixed_errors(self) -> None:
        te = TransformError(
            message="Bad YAML",
            location=BlockLocation(
                start_line=1, end_line=5, block_type=BlockType.YAML, block_index=0
            ),
            raw_content="not: [valid",
        )
        ve = ModelValidationError(
            field_errors=(
                FieldError(
                    field="name",
                    message="required",
                    input_value=None,
                    error_type="missing",
                ),
            ),
            location=RowLocation(
                table_index=0,
                row_index=0,
                table_heading=None,
                start_line=10,
            ),
            raw_input={"age": "30"},
        )
        err = ExtractionError("Multiple failures", errors=[te, ve])
        s = str(err)
        assert "[1]" in s
        assert "[2]" in s
        assert "Transform error" in s
        assert "Validation error" in s

    def test_errors_is_list_of_extraction_error_detail(self) -> None:
        te = TransformError(
            message="fail",
            location=BlockLocation(
                start_line=1, end_line=2, block_type=BlockType.JSON, block_index=0
            ),
            raw_content="{}",
        )
        err = ExtractionError("msg", errors=[te])
        assert isinstance(err.errors, list)
        for e in err.errors:
            assert isinstance(e, (TransformError, ModelValidationError))


# ---------------------------------------------------------------------------
# TransformError
# ---------------------------------------------------------------------------


class TestTransformError:
    """TransformError model properties."""

    def test_has_correct_phase(self) -> None:
        te = TransformError(
            message="broken",
            location=BlockLocation(
                start_line=1, end_line=5, block_type=BlockType.JSON, block_index=0
            ),
            raw_content="not json",
        )
        assert te.phase == "transform"

    def test_carries_block_location(self) -> None:
        loc = BlockLocation(
            start_line=10, end_line=20, block_type=BlockType.YAML, block_index=2
        )
        te = TransformError(
            message="parse error",
            location=loc,
            raw_content="bad yaml",
        )
        assert te.location.start_line == 10
        assert te.location.end_line == 20
        assert te.location.block_type == BlockType.YAML
        assert te.location.block_index == 2

    def test_carries_message_and_raw_content(self) -> None:
        te = TransformError(
            message="Unexpected token",
            location=BlockLocation(
                start_line=1, end_line=3, block_type=BlockType.JSON, block_index=0
            ),
            raw_content="{bad}",
        )
        assert te.message == "Unexpected token"
        assert te.raw_content == "{bad}"


# ---------------------------------------------------------------------------
# ModelValidationError
# ---------------------------------------------------------------------------


class TestModelValidationError:
    """ModelValidationError model properties."""

    def test_has_correct_phase(self) -> None:
        ve = ModelValidationError(
            field_errors=(
                FieldError(
                    field="age",
                    message="not int",
                    input_value="x",
                    error_type="int_parsing",
                ),
            ),
            location=BlockLocation(
                start_line=1, end_line=3, block_type=BlockType.JSON, block_index=0
            ),
            raw_input={"age": "x"},
        )
        assert ve.phase == "validate"

    def test_can_have_block_location(self) -> None:
        loc = BlockLocation(
            start_line=5, end_line=8, block_type=BlockType.JSON, block_index=1
        )
        ve = ModelValidationError(
            field_errors=(),
            location=loc,
            raw_input={},
        )
        assert isinstance(ve.location, BlockLocation)
        assert ve.location.start_line == 5

    def test_can_have_row_location(self) -> None:
        loc = RowLocation(
            table_index=1, row_index=3, table_heading="People", start_line=15
        )
        ve = ModelValidationError(
            field_errors=(),
            location=loc,
            raw_input={},
        )
        assert isinstance(ve.location, RowLocation)
        assert ve.location.table_index == 1
        assert ve.location.row_index == 3
        assert ve.location.table_heading == "People"

    def test_carries_field_errors_and_raw_input(self) -> None:
        fe = FieldError(
            field="name", message="required", input_value=None, error_type="missing"
        )
        ve = ModelValidationError(
            field_errors=(fe,),
            location=RowLocation(
                table_index=0, row_index=0, table_heading=None, start_line=1
            ),
            raw_input={"age": "30"},
        )
        assert len(ve.field_errors) == 1
        assert ve.field_errors[0].field == "name"
        assert ve.raw_input == {"age": "30"}


# ---------------------------------------------------------------------------
# PartialResult
# ---------------------------------------------------------------------------


class TestPartialResult:
    """PartialResult model properties."""

    def test_has_errors_returns_true_when_errors_exist(self) -> None:
        te = TransformError(
            message="fail",
            location=BlockLocation(
                start_line=1, end_line=2, block_type=BlockType.JSON, block_index=0
            ),
            raw_content="{}",
        )
        pr: PartialResult[Person] = PartialResult(data=[], errors=[te])
        assert pr.has_errors is True

    def test_has_errors_returns_false_when_no_errors(self) -> None:
        p = Person(name="Alice", age=30)
        pr: PartialResult[Person] = PartialResult(data=[p], errors=[])
        assert pr.has_errors is False

    def test_data_contains_valid_items(self) -> None:
        p1 = Person(name="Alice", age=30)
        p2 = Person(name="Bob", age=25)
        pr: PartialResult[Person] = PartialResult(data=[p1, p2], errors=[])
        assert len(pr.data) == 2
        assert pr.data[0].name == "Alice"
        assert pr.data[1].name == "Bob"

    def test_errors_contains_typed_error_details(self) -> None:
        te = TransformError(
            message="bad",
            location=BlockLocation(
                start_line=1, end_line=2, block_type=BlockType.JSON, block_index=0
            ),
            raw_content="x",
        )
        ve = ModelValidationError(
            field_errors=(),
            location=RowLocation(
                table_index=0, row_index=0, table_heading=None, start_line=1
            ),
            raw_input={},
        )
        pr: PartialResult[Person] = PartialResult(data=[], errors=[te, ve])
        assert len(pr.errors) == 2
        assert isinstance(pr.errors[0], TransformError)
        assert isinstance(pr.errors[1], ModelValidationError)


# ---------------------------------------------------------------------------
# parse_tables with partial=True
# ---------------------------------------------------------------------------


class TestParseTablesPartialTrue:
    """parse_tables(partial=True) returns PartialResult."""

    def test_all_valid_rows(self) -> None:
        md = "| name | age |\n| --- | --- |\n| Alice | 30 |\n| Bob | 25 |\n"
        result = MDConverter(Person).parse_tables(md, partial=True)
        assert isinstance(result, PartialResult)
        assert len(result.data) == 2
        assert result.has_errors is False

    def test_mixed_valid_and_invalid_rows(self) -> None:
        md = "| name | age |\n| --- | --- |\n| Alice | 30 |\n| Bob | not_a_number |\n"
        result = MDConverter(Person).parse_tables(md, partial=True)
        assert isinstance(result, PartialResult)
        assert len(result.data) == 1
        assert result.data[0].name == "Alice"
        assert len(result.errors) == 1
        assert result.has_errors is True

    def test_all_invalid_rows(self) -> None:
        md = "| name | age |\n| --- | --- |\n| Alice | not_int |\n| Bob | also_bad |\n"
        result = MDConverter(Person).parse_tables(md, partial=True)
        assert isinstance(result, PartialResult)
        assert len(result.data) == 0
        assert len(result.errors) == 2
        assert result.has_errors is True

    def test_errors_are_model_validation_error_with_row_location(self) -> None:
        md = "| name | age |\n| --- | --- |\n| Alice | bad |\n"
        result = MDConverter(Person).parse_tables(md, partial=True)
        assert len(result.errors) == 1
        err = result.errors[0]
        assert isinstance(err, ModelValidationError)
        assert isinstance(err.location, RowLocation)
        assert err.location.table_index == 0
        assert err.location.row_index == 0

    def test_error_row_location_second_table(self) -> None:
        md = (
            "| name | age |\n"
            "| --- | --- |\n"
            "| Alice | 30 |\n"
            "\n"
            "| name | age |\n"
            "| --- | --- |\n"
            "| Bob | bad |\n"
        )
        result = MDConverter(Person).parse_tables(md, partial=True)
        assert len(result.data) == 1
        assert len(result.errors) == 1
        err = result.errors[0]
        assert isinstance(err, ModelValidationError)
        assert isinstance(err.location, RowLocation)
        assert err.location.table_index == 1
        assert err.location.row_index == 0


# ---------------------------------------------------------------------------
# parse_tables with partial=False (default)
# ---------------------------------------------------------------------------


class TestParseTablesPartialFalse:
    """parse_tables(partial=False) returns list[T] or raises."""

    def test_all_valid_returns_list(self) -> None:
        md = "| name | age |\n| --- | --- |\n| Alice | 30 |\n"
        result = MDConverter(Person).parse_tables(md)
        assert isinstance(result, list)
        assert not isinstance(result, PartialResult)
        assert len(result) == 1
        assert result[0].name == "Alice"

    def test_no_tables_raises_extraction_error(self) -> None:
        with pytest.raises(ExtractionError, match="No tables found"):
            MDConverter(Person).parse_tables("Just plain text.")

    def test_no_valid_rows_raises_extraction_error_with_typed_errors(self) -> None:
        md = "| name | age |\n| --- | --- |\n| Alice | not_int |\n"
        with pytest.raises(ExtractionError) as exc_info:
            MDConverter(Person).parse_tables(md)
        err = exc_info.value
        assert len(err.errors) > 0
        assert isinstance(err.errors[0], ModelValidationError)


# ---------------------------------------------------------------------------
# parse with partial=True
# ---------------------------------------------------------------------------


class TestParsePartialTrue:
    """parse(partial=True) returns PartialResult for table content."""

    def test_returns_partial_result_for_table(self) -> None:
        md = "| name | age |\n| --- | --- |\n| Alice | 30 |\n| Bob | bad |\n"
        result = MDConverter(Person).parse(md, partial=True)
        assert isinstance(result, PartialResult)
        assert len(result.data) == 1
        assert result.data[0].name == "Alice"
        assert result.has_errors is True

    def test_returns_partial_result_for_json(self) -> None:
        md = '```json\n{"name": "Alice", "age": 30}\n```\n'
        result = MDConverter(Person).parse(md, partial=True)
        assert isinstance(result, PartialResult)
        assert len(result.data) == 1
        assert result.data[0].name == "Alice"


# ---------------------------------------------------------------------------
# _parse_code_blocks error typing
# ---------------------------------------------------------------------------


class TestParseCodeBlocksErrorTyping:
    """_parse_code_blocks produces typed errors in ExtractionError."""

    def test_json_parse_failure_has_transform_error(self) -> None:
        md = "```json\n{this is totally broken json\n```\n"
        with pytest.raises(ExtractionError) as exc_info:
            MDConverter(Person).parse_json(md)
        err = exc_info.value
        assert len(err.errors) > 0
        te = err.errors[0]
        assert isinstance(te, TransformError)
        assert te.phase == "transform"

    def test_validation_failure_has_model_validation_error(self) -> None:
        md = '```json\n{"name": "Alice", "age": "not_a_number"}\n```\n'
        with pytest.raises(ExtractionError) as exc_info:
            MDConverter(Person).parse_json(md)
        err = exc_info.value
        assert len(err.errors) > 0
        ve = err.errors[0]
        assert isinstance(ve, ModelValidationError)
        assert ve.phase == "validate"

    def test_errors_have_block_location_with_line_numbers(self) -> None:
        md = 'Some intro text\n```json\n{"name": "Alice", "age": "bad"}\n```\n'
        with pytest.raises(ExtractionError) as exc_info:
            MDConverter(Person).parse_json(md)
        err = exc_info.value
        assert len(err.errors) > 0
        loc = err.errors[0].location
        assert isinstance(loc, BlockLocation)
        assert loc.start_line >= 1
        assert loc.end_line >= loc.start_line
        assert loc.block_type == BlockType.JSON
        assert loc.block_index == 0

    def test_transform_error_has_block_location(self) -> None:
        md = "```json\n{totally broken\n```\n"
        with pytest.raises(ExtractionError) as exc_info:
            MDConverter(Person).parse_json(md)
        err = exc_info.value
        te = next(e for e in err.errors if isinstance(e, TransformError))
        assert isinstance(te.location, BlockLocation)
        assert te.location.block_type == BlockType.JSON
        assert te.location.block_index == 0
        assert te.location.start_line >= 0
        assert te.location.end_line >= te.location.start_line
