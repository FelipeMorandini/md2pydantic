"""Validator module - validates dicts against Pydantic v2 models with type coercion."""

from __future__ import annotations

import types
from typing import Annotated, Any, TypeVar, Union, get_args, get_origin

from pydantic import BaseModel, ValidationError

from md2pydantic.models import FieldError, ValidationResult

T = TypeVar("T", bound=BaseModel)

# --- Coercion constants ---

_BOOL_TRUE: frozenset[str] = frozenset({"yes", "y", "true", "1", "on"})
_BOOL_FALSE: frozenset[str] = frozenset({"no", "n", "false", "0", "off"})
_NULL_SENTINELS: frozenset[str] = frozenset({"n/a", "na", "null", "-", "—", ""})


def validate_dict(
    data: dict[str, Any],
    model: type[T],
) -> ValidationResult[T]:
    """Validate a single dict against a Pydantic BaseModel.

    Pre-processes the dict to handle common LLM output patterns:
    - "Yes"/"No" → bool for bool fields
    - Empty strings and null sentinels ("N/A", "-") → None for optional fields

    Pydantic handles natively: str→int, str→float, str→datetime.
    """
    preprocessed = _preprocess_dict(data, model)
    try:
        instance = model.model_validate(preprocessed)
        return ValidationResult(
            data=instance,
            errors=(),
            raw_input=dict(data),
        )
    except ValidationError as e:
        field_errors = tuple(
            FieldError(
                field=".".join(str(loc) for loc in err["loc"]),
                message=err["msg"],
                input_value=err.get("input"),
                error_type=err["type"],
            )
            for err in e.errors()
        )
        return ValidationResult(
            data=None,
            errors=field_errors,
            raw_input=dict(data),
        )


def validate_dicts(
    data: list[dict[str, Any]],
    model: type[T],
) -> list[ValidationResult[T]]:
    """Validate a list of dicts against a Pydantic BaseModel.

    Returns one ValidationResult per dict.
    """
    return [validate_dict(d, model) for d in data]


def _preprocess_dict(
    data: dict[str, Any],
    model: type[BaseModel],
) -> dict[str, Any]:
    """Pre-process a dict for Pydantic validation.

    Applies coercion rules based on the target model's field types:
    - Null sentinels → None for optional fields
    - Yes/No variants → True/False for bool fields
    """
    result = dict(data)  # shallow copy

    for field_name, field_info in model.model_fields.items():
        if field_name not in result:
            continue
        value = result[field_name]
        if not isinstance(value, str):
            continue

        annotation = field_info.annotation
        if annotation is None:
            continue

        # Unwrap Annotated[X, ...] to get the base type
        annotation = _unwrap_annotated(annotation)

        is_opt = _is_optional(annotation)
        inner = _unwrap_optional(annotation) if is_opt else annotation

        # Null sentinel check (must come before bool check)
        if is_opt and value.strip().lower() in _NULL_SENTINELS:
            result[field_name] = None
            continue

        # Bool coercion
        if _is_bool_type(inner):
            lowered = value.strip().lower()
            if lowered in _BOOL_TRUE:
                result[field_name] = True
            elif lowered in _BOOL_FALSE:
                result[field_name] = False

    return result


def _unwrap_annotated(annotation: Any) -> Any:
    """Unwrap Annotated[X, ...] to get the base type X."""
    if get_origin(annotation) is Annotated:
        args = get_args(annotation)
        if args:
            return args[0]
    return annotation


def _is_optional(annotation: Any) -> bool:
    """Check if a type annotation is Optional (X | None or Optional[X])."""
    origin = get_origin(annotation)

    # Handle types.UnionType (Python 3.10+ X | Y syntax)
    if origin is types.UnionType:
        return type(None) in get_args(annotation)

    # Handle typing.Optional / typing.Union from typing module
    if origin is Union:
        return type(None) in get_args(annotation)

    return False


def _unwrap_optional(annotation: Any) -> Any:
    """Extract the non-None type from an Optional annotation."""
    args = get_args(annotation)
    non_none = [a for a in args if a is not type(None)]
    return non_none[0] if len(non_none) == 1 else annotation


def _is_bool_type(annotation: Any) -> bool:
    """Check if a type annotation is bool."""
    return annotation is bool
