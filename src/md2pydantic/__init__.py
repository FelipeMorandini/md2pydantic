"""md2pydantic - Extract structured data from Markdown into Pydantic v2 models."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("md2pydantic")
except PackageNotFoundError:
    __version__ = "0+unknown"

__all__ = [
    "ExtractionError",
    "FieldError",
    "MD2PydanticError",
    "MDConverter",
    "PartialResult",
    "__version__",
]

from md2pydantic.converter import MDConverter
from md2pydantic.models import (
    ExtractionError,
    FieldError,
    MD2PydanticError,
    PartialResult,
)
