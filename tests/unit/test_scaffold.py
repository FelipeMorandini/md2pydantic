"""Unit tests for the project scaffolding (Issue #1).

Covers version format, MDConverter instantiation, __all__ exports,
and module importability.
"""

from __future__ import annotations

import re

import pytest
from pydantic import BaseModel


class SampleModel(BaseModel):
    """A minimal Pydantic model used for testing."""

    name: str
    value: int


class TestVersionFormat:
    """Verify __version__ is a valid PEP 440-style version string."""

    def test_version_is_pep440_compliant(self) -> None:
        from md2pydantic import __version__

        # Basic PEP 440-compatible version: MAJOR.MINOR.PATCH with optional suffix
        pattern = r"^\d+\.\d+\.\d+([a-zA-Z0-9.+-]*)$"
        assert re.match(pattern, __version__), (
            f"__version__ '{__version__}' is not a valid PEP 440 version string"
        )

    def test_version_matches_pyproject(self) -> None:
        from importlib.metadata import version

        from md2pydantic import __version__

        assert __version__ == version("md2pydantic")


class TestMDConverterInstantiation:
    """Verify MDConverter can be created and stores the model reference."""

    def test_instantiate_with_basemodel_subclass(self) -> None:
        from md2pydantic import MDConverter

        converter = MDConverter(SampleModel)
        assert converter is not None

    def test_stores_model_reference(self) -> None:
        from md2pydantic import MDConverter

        converter = MDConverter(SampleModel)
        assert converter.model is SampleModel

    def test_model_reference_is_not_copied(self) -> None:
        """The stored reference should be the exact same object, not a copy."""
        from md2pydantic import MDConverter

        converter = MDConverter(SampleModel)
        assert converter.model is SampleModel
        assert id(converter.model) == id(SampleModel)

    def test_parse_tables_extracts_data(self) -> None:
        """parse_tables extracts table rows into model instances."""
        from md2pydantic import MDConverter

        converter = MDConverter(SampleModel)
        results = converter.parse_tables(
            "| name | value |\n| --- | --- |\n| alice | 1 |"
        )
        assert len(results) == 1
        assert results[0].name == "alice"
        assert results[0].value == 1


class TestAllExports:
    """Verify __all__ lists exactly the expected public API."""

    def test_all_contains_mdconverter(self) -> None:
        import md2pydantic

        assert "MDConverter" in md2pydantic.__all__

    def test_all_contains_version(self) -> None:
        import md2pydantic

        assert "__version__" in md2pydantic.__all__

    def test_all_has_expected_length(self) -> None:
        import md2pydantic

        assert len(md2pydantic.__all__) == 6

    def test_all_entries_are_resolvable(self) -> None:
        """Every name in __all__ should be an actual attribute of the package."""
        import md2pydantic

        for name in md2pydantic.__all__:
            assert hasattr(md2pydantic, name), (
                f"__all__ lists '{name}' but it is not an attribute of md2pydantic"
            )


class TestModuleImports:
    """Verify all expected submodules are importable."""

    @pytest.mark.parametrize(
        "module_name",
        ["md2pydantic.parser", "md2pydantic.transformers", "md2pydantic.models"],
    )
    def test_submodule_importable(self, module_name: str) -> None:
        import importlib

        mod = importlib.import_module(module_name)
        assert mod is not None

    def test_parser_is_a_module(self) -> None:
        import types

        import md2pydantic.parser as parser

        assert isinstance(parser, types.ModuleType)

    def test_transformers_is_a_module(self) -> None:
        import types

        import md2pydantic.transformers as transformers

        assert isinstance(transformers, types.ModuleType)

    def test_converter_module_exports_mdconverter(self) -> None:
        from md2pydantic.converter import MDConverter

        assert MDConverter is not None
