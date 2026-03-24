"""Internal models for md2pydantic."""

from __future__ import annotations

from enum import Enum
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T", bound=BaseModel)


class BlockType(str, Enum):
    """Type of structured block detected in Markdown."""

    JSON = "json"
    YAML = "yaml"
    TABLE = "table"
    UNKNOWN = "unknown"


class CodeBlock(BaseModel):
    """A candidate structured block extracted from Markdown."""

    model_config = ConfigDict(frozen=True)

    content: str
    block_type: BlockType
    fenced: bool
    start_line: int
    end_line: int


class TableBlock(BaseModel):
    """A Markdown table extracted from a document."""

    model_config = ConfigDict(frozen=True)

    headers: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]
    heading: str | None
    start_line: int
    end_line: int


class TransformResult(BaseModel):
    """Result of transforming a code block into a Python data structure."""

    model_config = ConfigDict(frozen=True)

    data: dict[str, Any] | list[Any] | None
    error: str | None
    raw_content: str
    block_type: BlockType


class FieldError(BaseModel):
    """A single field-level validation error."""

    model_config = ConfigDict(frozen=True)

    field: str
    message: str
    input_value: Any
    error_type: str


class ValidationResult(BaseModel, Generic[T]):
    """Result of validating a dict against a Pydantic model."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    data: T | None
    errors: tuple[FieldError, ...]
    raw_input: dict[str, Any]


class BlockLocation(BaseModel):
    """Source location of a code block in the original markdown."""

    model_config = ConfigDict(frozen=True)

    start_line: int
    end_line: int
    block_type: BlockType
    block_index: int


class RowLocation(BaseModel):
    """Source location of a table row in the original markdown."""

    model_config = ConfigDict(frozen=True)

    table_index: int
    row_index: int
    table_heading: str | None
    start_line: int


class TransformError(BaseModel):
    """Error from the transform phase (JSON/YAML parsing failed)."""

    model_config = ConfigDict(frozen=True)

    phase: Literal["transform"] = "transform"
    message: str
    location: BlockLocation
    raw_content: str


class ModelValidationError(BaseModel):
    """Error from the validation phase (Pydantic rejected the data)."""

    model_config = ConfigDict(frozen=True)

    phase: Literal["validate"] = "validate"
    field_errors: tuple[FieldError, ...]
    location: BlockLocation | RowLocation
    raw_input: dict[str, Any]


ExtractionErrorDetail = TransformError | ModelValidationError


class PartialResult(BaseModel, Generic[T]):
    """Contains both successfully parsed items and errors from failed items."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    data: list[T]
    errors: list[ExtractionErrorDetail]

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0


class MD2PydanticError(Exception):
    """Base exception for md2pydantic."""


class ExtractionError(MD2PydanticError):
    """Raised when structured data cannot be extracted or validated."""

    def __init__(
        self,
        message: str,
        errors: list[ExtractionErrorDetail] | None = None,
    ) -> None:
        super().__init__(message)
        self.errors: list[ExtractionErrorDetail] = errors or []

    def __str__(self) -> str:
        parts = [self.args[0]]
        for i, err in enumerate(self.errors, 1):
            if isinstance(err, TransformError):
                parts.append(
                    f"  [{i}] Transform error at lines "
                    f"{err.location.start_line}-{err.location.end_line}: "
                    f"{err.message}"
                )
            elif isinstance(err, ModelValidationError):
                loc = err.location
                if isinstance(loc, RowLocation):
                    loc_str = f"table {loc.table_index}, row {loc.row_index}"
                else:
                    loc_str = f"block at lines {loc.start_line}-{loc.end_line}"
                field_msgs = "; ".join(
                    f"{fe.field}: {fe.message}" for fe in err.field_errors
                )
                parts.append(f"  [{i}] Validation error in {loc_str}: {field_msgs}")
        return "\n".join(parts)
