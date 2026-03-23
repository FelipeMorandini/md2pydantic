"""Smoke test to verify the package imports correctly."""

from importlib.metadata import version


def test_import() -> None:
    from md2pydantic import MDConverter, __version__

    assert __version__ == version("md2pydantic")
    assert MDConverter is not None
