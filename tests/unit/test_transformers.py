"""Unit tests for the transformer module (transformers.py) — Issue #4.

Covers table_to_dicts, tables_to_dicts, and table_to_dataframe.
"""

from __future__ import annotations

import pytest

from md2pydantic.models import TableBlock
from md2pydantic.transformers import table_to_dataframe, table_to_dicts, tables_to_dicts

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_table(
    headers: tuple[str, ...],
    rows: tuple[tuple[str, ...], ...],
    *,
    heading: str | None = None,
    start_line: int = 0,
    end_line: int = 0,
) -> TableBlock:
    """Build a TableBlock for testing."""
    return TableBlock(
        headers=headers,
        rows=rows,
        heading=heading,
        start_line=start_line,
        end_line=end_line,
    )


# ---------------------------------------------------------------------------
# table_to_dicts
# ---------------------------------------------------------------------------


class TestTableToDicts:
    """Tests for table_to_dicts conversion."""

    def test_basic_three_cols_two_rows(self) -> None:
        table = _make_table(
            headers=("Name", "Age", "City"),
            rows=(
                ("Alice", "30", "New York"),
                ("Bob", "25", "London"),
            ),
        )
        result = table_to_dicts(table)
        assert result == [
            {"Name": "Alice", "Age": "30", "City": "New York"},
            {"Name": "Bob", "Age": "25", "City": "London"},
        ]

    def test_empty_cells_map_to_none(self) -> None:
        table = _make_table(
            headers=("A", "B", "C"),
            rows=(("", "value", ""),),
        )
        result = table_to_dicts(table)
        assert result == [{"A": None, "B": "value", "C": None}]

    def test_all_empty_row_all_none(self) -> None:
        table = _make_table(
            headers=("X", "Y", "Z"),
            rows=(("", "", ""),),
        )
        result = table_to_dicts(table)
        assert result == [{"X": None, "Y": None, "Z": None}]

    def test_zero_data_rows_empty_list(self) -> None:
        table = _make_table(
            headers=("A", "B"),
            rows=(),
        )
        result = table_to_dicts(table)
        assert result == []

    def test_single_column_table(self) -> None:
        table = _make_table(
            headers=("Only",),
            rows=(("one",), ("two",)),
        )
        result = table_to_dicts(table)
        assert result == [{"Only": "one"}, {"Only": "two"}]

    def test_single_row_table(self) -> None:
        table = _make_table(
            headers=("A", "B", "C"),
            rows=(("1", "2", "3"),),
        )
        result = table_to_dicts(table)
        assert len(result) == 1
        assert result[0] == {"A": "1", "B": "2", "C": "3"}

    def test_duplicate_header_names_last_value_wins(self) -> None:
        table = _make_table(
            headers=("Col", "Col", "Col"),
            rows=(("first", "second", "third"),),
        )
        result = table_to_dicts(table)
        # zip iterates left-to-right; later assignments overwrite earlier ones
        assert result == [{"Col": "third"}]

    def test_empty_header_name_used_as_key(self) -> None:
        table = _make_table(
            headers=("", "B"),
            rows=(("val1", "val2"),),
        )
        result = table_to_dicts(table)
        assert result == [{"": "val1", "B": "val2"}]

    def test_large_table_ten_plus_rows(self) -> None:
        rows = tuple((str(i), f"name_{i}") for i in range(15))
        table = _make_table(
            headers=("ID", "Name"),
            rows=rows,
        )
        result = table_to_dicts(table)
        assert len(result) == 15
        assert result[0] == {"ID": "0", "Name": "name_0"}
        assert result[14] == {"ID": "14", "Name": "name_14"}

    def test_stripped_values_passthrough(self) -> None:
        """Headers and values are already stripped by the scanner.
        Verify the transformer passes them through as-is."""
        table = _make_table(
            headers=("Name", "City"),
            rows=(("Alice", "New York"),),
        )
        result = table_to_dicts(table)
        assert result[0]["Name"] == "Alice"
        assert result[0]["City"] == "New York"


# ---------------------------------------------------------------------------
# tables_to_dicts
# ---------------------------------------------------------------------------


class TestTablesToDicts:
    """Tests for tables_to_dicts (multiple tables)."""

    def test_multiple_tables_correct_nested_lists(self) -> None:
        t1 = _make_table(headers=("A", "B"), rows=(("1", "2"),))
        t2 = _make_table(headers=("X", "Y"), rows=(("a", "b"), ("c", "d")))
        result = tables_to_dicts([t1, t2])
        assert len(result) == 2
        assert result[0] == [{"A": "1", "B": "2"}]
        assert result[1] == [
            {"X": "a", "Y": "b"},
            {"X": "c", "Y": "d"},
        ]

    def test_empty_table_list_returns_empty(self) -> None:
        result = tables_to_dicts([])
        assert result == []

    def test_mix_of_tables_with_different_column_counts(self) -> None:
        t1 = _make_table(headers=("A",), rows=(("1",),))
        t2 = _make_table(headers=("X", "Y", "Z"), rows=(("a", "b", "c"),))
        t3 = _make_table(headers=("P", "Q"), rows=(("p1", "q1"),))
        result = tables_to_dicts([t1, t2, t3])
        assert len(result) == 3
        assert result[0] == [{"A": "1"}]
        assert result[1] == [{"X": "a", "Y": "b", "Z": "c"}]
        assert result[2] == [{"P": "p1", "Q": "q1"}]


# ---------------------------------------------------------------------------
# table_to_dataframe
# ---------------------------------------------------------------------------


class TestTableToDataframe:
    """Tests for table_to_dataframe (requires pandas)."""

    @pytest.fixture(autouse=True)
    def _skip_without_pandas(self) -> None:
        pytest.importorskip("pandas")

    def test_basic_conversion(self) -> None:
        import pandas as pd

        table = _make_table(
            headers=("Name", "Age"),
            rows=(("Alice", "30"), ("Bob", "25")),
        )
        df = table_to_dataframe(table)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert df.iloc[0]["Name"] == "Alice"
        assert df.iloc[1]["Age"] == "25"

    def test_empty_cells_become_none(self) -> None:
        table = _make_table(
            headers=("A", "B"),
            rows=(("val", ""), ("", "val2")),
        )
        df = table_to_dataframe(table)
        assert df.iloc[0]["B"] is None
        assert df.iloc[1]["A"] is None

    def test_column_names_match_headers(self) -> None:
        table = _make_table(
            headers=("First", "Second", "Third"),
            rows=(("a", "b", "c"),),
        )
        df = table_to_dataframe(table)
        assert list(df.columns) == ["First", "Second", "Third"]

    def test_zero_rows_empty_dataframe_with_correct_columns(self) -> None:
        import pandas as pd

        table = _make_table(
            headers=("X", "Y"),
            rows=(),
        )
        df = table_to_dataframe(table)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0
        assert list(df.columns) == ["X", "Y"]


# ---------------------------------------------------------------------------
# Import error and edge cases
# ---------------------------------------------------------------------------


class TestTableToDataframeImportError:
    """Test that table_to_dataframe raises ImportError without pandas."""

    def test_import_error_message(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import builtins

        real_import = builtins.__import__

        def mock_import(name: str, *args: object, **kwargs: object) -> object:
            if name == "pandas":
                raise ImportError("No module named 'pandas'")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)
        table = _make_table(headers=("A",), rows=(("1",),))
        with pytest.raises(ImportError, match="pandas is required"):
            table_to_dataframe(table)


class TestScannerGuaranteesEqualLengths:
    """Verify that the scanner guarantees row lengths match header count.

    The transformer uses zip(strict=False), which is safe because the scanner
    pads short rows and truncates long rows. This test documents that contract.
    """

    def test_scanner_pads_short_rows(self) -> None:
        from md2pydantic.parser import scan_tables

        md = "| A | B | C |\n|---|---|---|\n| only_one |\n"
        tables = scan_tables(md)
        assert len(tables) == 1
        row = tables[0].rows[0]
        assert len(row) == len(tables[0].headers)

    def test_transformer_with_scanner_output(self) -> None:
        from md2pydantic.parser import scan_tables

        md = "| A | B | C |\n|---|---|---|\n| only_one |\n"
        tables = scan_tables(md)
        result = table_to_dicts(tables[0])
        assert len(result) == 1
        assert set(result[0].keys()) == {"A", "B", "C"}
