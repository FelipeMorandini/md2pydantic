"""Internal models and the MDConverter public API entry point."""

from __future__ import annotations

from typing import Any


class MDConverter:
    """Main entry point for md2pydantic.

    Usage::

        result = MDConverter(MyModel).parse_tables(markdown_string)
    """

    def __init__(self, model: type[Any]) -> None:
        self.model = model

    def parse_tables(self, markdown: str) -> list[Any]:
        """Extract tables from markdown and return validated model instances."""
        raise NotImplementedError
