"""Internal models for md2pydantic."""

from __future__ import annotations

from enum import Enum
from typing import Any, Generic, TypeVar

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


class MD2PydanticError(Exception):
    """Base exception for md2pydantic."""


class ExtractionError(MD2PydanticError):
    """Raised when structured data cannot be extracted or validated."""

    def __init__(self, message: str, errors: list[Any] | None = None) -> None:
        super().__init__(message)
        self.errors = errors or []
