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
    """Verify __version__ is a valid semver string."""

    def test_version_is_semver(self) -> None:
        from md2pydantic import __version__

        # Semver: MAJOR.MINOR.PATCH with optional pre-release / build metadata
        pattern = r"^\d+\.\d+\.\d+([a-zA-Z0-9.+-]*)$"
        assert re.match(pattern, __version__), (
            f"__version__ '{__version__}' is not valid semver"
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

    def test_instantiate_with_plain_class(self) -> None:
        """MDConverter currently accepts type[Any], so a plain class should work."""
        from md2pydantic import MDConverter

        class PlainClass:
            pass

        converter = MDConverter(PlainClass)
        assert converter.model is PlainClass

    def test_model_reference_is_not_copied(self) -> None:
        """The stored reference should be the exact same object, not a copy."""
        from md2pydantic import MDConverter

        converter = MDConverter(SampleModel)
        assert converter.model is SampleModel
        assert id(converter.model) == id(SampleModel)

    def test_parse_tables_raises_not_implemented(self) -> None:
        """parse_tables is stubbed and should raise NotImplementedError."""
        from md2pydantic import MDConverter

        converter = MDConverter(SampleModel)
        with pytest.raises(NotImplementedError):
            converter.parse_tables("| col1 | col2 |\n| --- | --- |\n| a | b |")


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

        assert len(md2pydantic.__all__) == 2

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

    def test_models_exports_mdconverter(self) -> None:
        from md2pydantic.models import MDConverter

        assert MDConverter is not None
