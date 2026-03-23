"""Unit tests for the validator module (validators.py) — Issue #6.

Covers validate_dict, validate_dicts, and _preprocess_dict with
success cases, failure cases, null sentinel coercion, and bool coercion.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

import pytest
from pydantic import BaseModel

from md2pydantic.models import FieldError
from md2pydantic.validators import _preprocess_dict, validate_dict, validate_dicts

# ---------------------------------------------------------------------------
# Test Pydantic models
# ---------------------------------------------------------------------------


class PersonModel(BaseModel):
    name: str
    age: int
    city: str


class CoercionModel(BaseModel):
    age: int
    price: float
    active: bool


class DateModel(BaseModel):
    name: str
    created_at: datetime


class OptionalModel(BaseModel):
    name: str
    nickname: str | None = None
    score: int | None = None


class OptionalBoolModel(BaseModel):
    name: str
    active: bool | None = None


class BoolVariantsModel(BaseModel):
    flag: bool


class MixedModel(BaseModel):
    name: str
    age: int
    active: bool
    score: float | None = None


# ---------------------------------------------------------------------------
# validate_dict — success cases
# ---------------------------------------------------------------------------


class TestValidateDictSuccess:
    """Tests for validate_dict with valid data."""

    def test_basic_dict_validates_to_model(self) -> None:
        data = {"name": "Alice", "age": 30, "city": "New York"}
        result = validate_dict(data, PersonModel)
        assert result.data is not None
        assert result.data.name == "Alice"
        assert result.data.age == 30
        assert result.data.city == "New York"
        assert result.errors == ()

    def test_numeric_string_coercion_int(self) -> None:
        data = {"age": "30", "price": 9.99, "active": True}
        result = validate_dict(data, CoercionModel)
        assert result.data is not None
        assert result.data.age == 30
        assert isinstance(result.data.age, int)

    def test_numeric_string_coercion_float(self) -> None:
        data = {"age": 30, "price": "9.99", "active": True}
        result = validate_dict(data, CoercionModel)
        assert result.data is not None
        assert result.data.price == 9.99
        assert isinstance(result.data.price, float)

    def test_bool_coercion_yes(self) -> None:
        data = {"age": 30, "price": 9.99, "active": "Yes"}
        result = validate_dict(data, CoercionModel)
        assert result.data is not None
        assert result.data.active is True

    def test_bool_coercion_no(self) -> None:
        data = {"age": 30, "price": 9.99, "active": "No"}
        result = validate_dict(data, CoercionModel)
        assert result.data is not None
        assert result.data.active is False

    @pytest.mark.parametrize("value", ["yes", "YES", "y", "Y", "on"])
    def test_bool_coercion_true_variants(self, value: str) -> None:
        data = {"flag": value}
        result = validate_dict(data, BoolVariantsModel)
        assert result.data is not None
        assert result.data.flag is True

    @pytest.mark.parametrize("value", ["no", "NO", "n", "N", "off"])
    def test_bool_coercion_false_variants(self, value: str) -> None:
        data = {"flag": value}
        result = validate_dict(data, BoolVariantsModel)
        assert result.data is not None
        assert result.data.flag is False

    def test_date_string_coercion(self) -> None:
        data = {"name": "Alice", "created_at": "2024-01-01"}
        result = validate_dict(data, DateModel)
        assert result.data is not None
        assert isinstance(result.data.created_at, datetime)
        assert result.data.created_at.year == 2024
        assert result.data.created_at.month == 1
        assert result.data.created_at.day == 1

    def test_optional_field_with_none_value(self) -> None:
        data = {"name": "Alice", "nickname": None, "score": None}
        result = validate_dict(data, OptionalModel)
        assert result.data is not None
        assert result.data.nickname is None
        assert result.data.score is None
        assert result.errors == ()

    def test_optional_field_missing_uses_default(self) -> None:
        data = {"name": "Alice"}
        result = validate_dict(data, OptionalModel)
        assert result.data is not None
        assert result.data.name == "Alice"
        assert result.data.nickname is None
        assert result.data.score is None


# ---------------------------------------------------------------------------
# validate_dict — failure cases
# ---------------------------------------------------------------------------


class TestValidateDictFailure:
    """Tests for validate_dict with invalid data."""

    def test_invalid_data_produces_errors(self) -> None:
        data = {"name": "Alice", "age": "not_a_number", "city": "NY"}
        result = validate_dict(data, PersonModel)
        assert result.data is None
        assert len(result.errors) > 0

    def test_field_error_has_correct_attributes(self) -> None:
        data = {"name": "Alice", "age": "abc", "city": "NY"}
        result = validate_dict(data, PersonModel)
        assert result.data is None
        assert len(result.errors) >= 1
        err = result.errors[0]
        assert isinstance(err, FieldError)
        assert err.field == "age"
        assert err.message != ""
        assert err.input_value == "abc"
        assert err.error_type != ""

    def test_multiple_field_errors(self) -> None:
        # name missing (required), age non-numeric, city wrong type
        data_bad = {"age": "abc", "city": 999}
        result = validate_dict(data_bad, PersonModel)
        assert result.data is None
        assert len(result.errors) >= 2

    def test_non_coercible_value(self) -> None:
        data = {"age": "abc", "price": "xyz", "active": "Yes"}
        result = validate_dict(data, CoercionModel)
        assert result.data is None
        assert any(e.field == "age" for e in result.errors)
        assert any(e.field == "price" for e in result.errors)

    def test_raw_input_preserved_on_failure(self) -> None:
        data = {"name": "Alice", "age": "abc", "city": "NY"}
        result = validate_dict(data, PersonModel)
        assert result.raw_input == data


# ---------------------------------------------------------------------------
# validate_dict — null sentinel coercion
# ---------------------------------------------------------------------------


class TestValidateDictNullSentinels:
    """Tests for null sentinel coercion in validate_dict."""

    def test_empty_string_to_none_for_optional(self) -> None:
        data = {"name": "Alice", "nickname": "", "score": None}
        result = validate_dict(data, OptionalModel)
        assert result.data is not None
        assert result.data.nickname is None

    def test_na_to_none_for_optional(self) -> None:
        data = {"name": "Alice", "nickname": "N/A"}
        result = validate_dict(data, OptionalModel)
        assert result.data is not None
        assert result.data.nickname is None

    def test_null_string_to_none_for_optional(self) -> None:
        data = {"name": "Alice", "nickname": "null"}
        result = validate_dict(data, OptionalModel)
        assert result.data is not None
        assert result.data.nickname is None

    def test_dash_to_none_for_optional(self) -> None:
        data = {"name": "Alice", "nickname": "-"}
        result = validate_dict(data, OptionalModel)
        assert result.data is not None
        assert result.data.nickname is None

    def test_na_on_non_optional_field_left_as_is(self) -> None:
        data = {"name": "N/A", "age": 30, "city": "NY"}
        result = validate_dict(data, PersonModel)
        # name is a required str field — "N/A" should remain as-is
        assert result.data is not None
        assert result.data.name == "N/A"

    def test_na_on_optional_bool_field_is_none_not_bool(self) -> None:
        data = {"name": "Alice", "active": "N/A"}
        result = validate_dict(data, OptionalBoolModel)
        assert result.data is not None
        # Should be None, not mapped to a bool value
        assert result.data.active is None


# ---------------------------------------------------------------------------
# validate_dicts
# ---------------------------------------------------------------------------


class TestValidateDicts:
    """Tests for validate_dicts (list of dicts)."""

    def test_all_valid(self) -> None:
        dicts = [
            {"name": "Alice", "age": 30, "city": "NY"},
            {"name": "Bob", "age": 25, "city": "London"},
        ]
        results = validate_dicts(dicts, PersonModel)
        assert len(results) == 2
        assert all(r.data is not None for r in results)
        assert all(r.errors == () for r in results)

    def test_mixed_valid_invalid(self) -> None:
        dicts = [
            {"name": "Alice", "age": 30, "city": "NY"},
            {"name": "Bob", "age": "abc", "city": "London"},
            {"name": "Charlie", "age": 35, "city": "Paris"},
        ]
        results = validate_dicts(dicts, PersonModel)
        assert len(results) == 3
        assert results[0].data is not None
        assert results[1].data is None
        assert len(results[1].errors) > 0
        assert results[2].data is not None

    def test_empty_list(self) -> None:
        results = validate_dicts([], PersonModel)
        assert results == []


# ---------------------------------------------------------------------------
# _preprocess_dict (test directly)
# ---------------------------------------------------------------------------


class TestPreprocessDict:
    """Tests for _preprocess_dict private function."""

    def test_bool_fields_get_yes_no_converted(self) -> None:
        data = {"age": 30, "price": 9.99, "active": "Yes"}
        result = _preprocess_dict(data, CoercionModel)
        assert result["active"] is True

    def test_non_bool_string_field_with_yes_not_touched(self) -> None:
        data = {"name": "Yes", "age": 30, "city": "NY"}
        result = _preprocess_dict(data, PersonModel)
        # "name" is a str field, so "Yes" should NOT be converted to True
        assert result["name"] == "Yes"

    def test_none_values_skipped(self) -> None:
        data = {"name": "Alice", "nickname": None}
        result = _preprocess_dict(data, OptionalModel)
        assert result["nickname"] is None

    def test_non_string_values_skipped(self) -> None:
        data = {"age": 30, "price": 9.99, "active": True}
        result = _preprocess_dict(data, CoercionModel)
        # Non-string values should pass through unchanged
        assert result["age"] == 30
        assert result["price"] == 9.99
        assert result["active"] is True


# ---------------------------------------------------------------------------
# Additional edge cases
# ---------------------------------------------------------------------------


class NestedAddress(BaseModel):
    street: str
    city: str


class NestedModel(BaseModel):
    name: str
    address: NestedAddress


class MultiUnionModel(BaseModel):
    value: str | int | None = None


class ListBoolModel(BaseModel):
    name: str
    flags: list[bool]


class TestEdgeCases:
    """Edge cases for the validator."""

    def test_empty_dict_produces_errors(self) -> None:
        result = validate_dict({}, PersonModel)
        assert result.data is None
        assert len(result.errors) > 0
        error_fields = {e.field for e in result.errors}
        assert "name" in error_fields
        assert "age" in error_fields

    def test_extra_keys_ignored_by_default(self) -> None:
        data = {"name": "Alice", "age": "30", "city": "NY", "extra": "val"}
        result = validate_dict(data, PersonModel)
        assert result.data is not None
        assert result.data.name == "Alice"

    def test_nested_model_validates(self) -> None:
        data = {
            "name": "Alice",
            "address": {"street": "123 Main", "city": "NYC"},
        }
        result = validate_dict(data, NestedModel)
        assert result.data is not None
        assert result.data.address.city == "NYC"

    def test_list_field_passed_through(self) -> None:
        data = {"name": "Alice", "flags": [True, False]}
        result = validate_dict(data, ListBoolModel)
        assert result.data is not None
        assert result.data.flags == [True, False]

    def test_multi_union_optional_null_sentinel(self) -> None:
        data = {"value": "N/A"}
        result = validate_dict(data, MultiUnionModel)
        assert result.data is not None
        assert result.data.value is None

    def test_multi_union_non_sentinel_kept(self) -> None:
        data = {"value": "hello"}
        result = validate_dict(data, MultiUnionModel)
        assert result.data is not None
        assert result.data.value == "hello"

    def test_literal_none_not_coerced(self) -> None:
        """The word 'none' is NOT a null sentinel (removed as too aggressive)."""
        data = {"name": "test", "nickname": "none"}
        result = validate_dict(data, OptionalModel)
        assert result.data is not None
        assert result.data.nickname == "none"

    def test_annotated_bool_field_coercion(self) -> None:
        """Annotated[bool, ...] fields should still get Yes/No coercion."""
        from pydantic import Field

        class AnnotatedModel(BaseModel):
            name: str
            active: Annotated[bool, Field(description="Is active")]

        data = {"name": "Alice", "active": "Yes"}
        result = validate_dict(data, AnnotatedModel)
        assert result.data is not None
        assert result.data.active is True

    def test_annotated_optional_null_sentinel(self) -> None:
        """Annotated[str | None, ...] fields should get null sentinel coercion."""
        from pydantic import Field

        class AnnotatedOptModel(BaseModel):
            name: str
            note: Annotated[str | None, Field(description="A note")] = None

        data = {"name": "Alice", "note": "N/A"}
        result = validate_dict(data, AnnotatedOptModel)
        assert result.data is not None
        assert result.data.note is None

    def test_raw_input_is_copy(self) -> None:
        """raw_input should be a copy, not a reference to the original dict."""
        data = {"name": "Alice", "age": "30", "city": "NY"}
        result = validate_dict(data, PersonModel)
        data["name"] = "MUTATED"
        assert result.raw_input["name"] == "Alice"
