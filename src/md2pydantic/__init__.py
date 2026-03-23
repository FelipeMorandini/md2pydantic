"""md2pydantic - Extract structured data from Markdown into Pydantic v2 models."""

from importlib.metadata import version

__version__ = version("md2pydantic")

__all__ = [
    "MDConverter",
    "__version__",
]

from md2pydantic.models import MDConverter
