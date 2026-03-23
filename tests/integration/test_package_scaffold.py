"""Integration tests for md2pydantic project scaffolding (Issue #1).

Verifies the package installs correctly, the public API surface is accessible,
MDConverter works with real Pydantic v2 models, and the py.typed marker exists.
"""

from __future__ import annotations

import importlib
import pathlib
import sys

from pydantic import BaseModel

import md2pydantic
from md2pydantic import MDConverter

# ---------------------------------------------------------------------------
# 1. Package importability
# ---------------------------------------------------------------------------


class TestPackageImport:
    """Verify the package installs and is importable."""

    def test_import_md2pydantic(self) -> None:
        """The top-level package is importable."""
        mod = importlib.import_module("md2pydantic")
        assert mod is not None

    def test_package_is_on_sys_modules(self) -> None:
        """After import, md2pydantic appears in sys.modules."""
        assert "md2pydantic" in sys.modules

    def test_submodules_importable(self) -> None:
        """Internal submodules (models, parser, transformers) are importable."""
        for name in ("models", "parser", "transformers"):
            mod = importlib.import_module(f"md2pydantic.{name}")
            assert mod is not None


# ---------------------------------------------------------------------------
# 2. Public API surface
# ---------------------------------------------------------------------------


class TestPublicAPI:
    """Verify the public API exports are present and correct."""

    def test_mdconverter_exported(self) -> None:
        """MDConverter is accessible via `from md2pydantic import MDConverter`."""
        assert MDConverter is not None

    def test_version_exported(self) -> None:
        """__version__ is accessible at the package level."""
        from importlib.metadata import version

        assert hasattr(md2pydantic, "__version__")
        assert isinstance(md2pydantic.__version__, str)
        assert md2pydantic.__version__ == version("md2pydantic")

    def test_all_exports(self) -> None:
        """__all__ lists the expected public names."""
        assert hasattr(md2pydantic, "__all__")
        assert "MDConverter" in md2pydantic.__all__
        assert "__version__" in md2pydantic.__all__

    def test_mdconverter_is_class(self) -> None:
        """MDConverter is a class (not a function or module)."""
        assert isinstance(MDConverter, type)


# ---------------------------------------------------------------------------
# 3. MDConverter instantiation with Pydantic v2 BaseModel
# ---------------------------------------------------------------------------


class TestMDConverterInstantiation:
    """Verify MDConverter can be instantiated with Pydantic v2 models."""

    def test_instantiate_with_simple_model(self) -> None:
        """MDConverter accepts a simple Pydantic BaseModel subclass."""

        class Item(BaseModel):
            name: str
            price: float

        converter = MDConverter(Item)
        assert converter.model is Item

    def test_instantiate_with_nested_model(self) -> None:
        """MDConverter accepts a Pydantic model with nested models."""

        class Address(BaseModel):
            street: str
            city: str

        class Person(BaseModel):
            name: str
            age: int
            address: Address

        converter = MDConverter(Person)
        assert converter.model is Person

    def test_instantiate_with_optional_fields(self) -> None:
        """MDConverter accepts a model with optional/default fields."""

        class Config(BaseModel):
            enabled: bool = True
            label: str | None = None
            count: int = 0

        converter = MDConverter(Config)
        assert converter.model is Config

    def test_model_attribute_stored(self) -> None:
        """The model passed to MDConverter is stored on the instance."""

        class Dummy(BaseModel):
            x: int

        converter = MDConverter(Dummy)
        assert converter.model is Dummy


# ---------------------------------------------------------------------------
# 4. py.typed marker
# ---------------------------------------------------------------------------


class TestPyTypedMarker:
    """Verify the py.typed marker file exists for PEP 561 compliance."""

    def test_py_typed_exists(self) -> None:
        """py.typed marker file is present in the package directory."""
        package_dir = pathlib.Path(md2pydantic.__file__).parent
        py_typed = package_dir / "py.typed"
        assert py_typed.exists(), f"py.typed not found at {py_typed}"

    def test_py_typed_is_file(self) -> None:
        """py.typed is a regular file (not a directory or symlink)."""
        package_dir = pathlib.Path(md2pydantic.__file__).parent
        py_typed = package_dir / "py.typed"
        assert py_typed.is_file()
