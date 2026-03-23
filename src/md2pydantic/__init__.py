"""md2pydantic - Extract structured data from Markdown into Pydantic v2 models."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("md2pydantic")
except PackageNotFoundError:
    __version__ = "0+unknown"

__all__ = [
    "MDConverter",
    "__version__",
]

from md2pydantic.models import MDConverter
