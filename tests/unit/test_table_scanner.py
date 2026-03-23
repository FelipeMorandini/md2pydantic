"""Unit tests for the table scanner (parser.py scan_tables) — Issue #3.

Covers table detection, formatting variations, multiple tables,
index/heading selection, edge cases, and helper functions.
"""

from __future__ import annotations

import textwrap

from md2pydantic.models import TableBlock
from md2pydantic.parser import (
    _has_pipe,
    _is_separator_row,
    _parse_table_row,
    scan_tables,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _single(tables: list[TableBlock]) -> TableBlock:
    """Assert exactly one table was returned and return it."""
    assert len(tables) == 1, f"Expected 1 table, got {len(tables)}"
    return tables[0]


# ---------------------------------------------------------------------------
# Basic table detection
# ---------------------------------------------------------------------------


class TestBasicTableDetection:
    """Standard well-formed Markdown tables."""

    def test_standard_table_three_cols_two_rows(self) -> None:
        md = textwrap.dedent("""\
            | Name  | Age | City     |
            |-------|-----|----------|
            | Alice | 30  | New York |
            | Bob   | 25  | London   |
        """)
        table = _single(scan_tables(md))
        assert table.headers == ("Name", "Age", "City")
        assert len(table.rows) == 2
        assert table.rows[0] == ("Alice", "30", "New York")
        assert table.rows[1] == ("Bob", "25", "London")

    def test_headers_extracted_correctly(self) -> None:
        md = textwrap.dedent("""\
            | First | Second | Third |
            |-------|--------|-------|
            | a     | b      | c     |
        """)
        table = _single(scan_tables(md))
        assert table.headers == ("First", "Second", "Third")

    def test_cell_values_stripped_of_whitespace(self) -> None:
        md = textwrap.dedent("""\
            |  Name  |   Age   |   City   |
            |--------|---------|----------|
            |  Alice |   30    |  NYC     |
        """)
        table = _single(scan_tables(md))
        assert table.headers == ("Name", "Age", "City")
        assert table.rows[0] == ("Alice", "30", "NYC")


# ---------------------------------------------------------------------------
# Formatting variations
# ---------------------------------------------------------------------------


class TestFormattingVariations:
    """Tables with non-standard pipe/spacing formatting."""

    def test_missing_leading_pipes(self) -> None:
        md = textwrap.dedent("""\
            Name | Age |
            -----|-----|
            Alice | 30 |
        """)
        table = _single(scan_tables(md))
        assert table.headers == ("Name", "Age")
        assert table.rows[0] == ("Alice", "30")

    def test_missing_trailing_pipes(self) -> None:
        md = textwrap.dedent("""\
            | Name | Age
            |------|----
            | Alice | 30
        """)
        table = _single(scan_tables(md))
        assert table.headers == ("Name", "Age")
        assert table.rows[0] == ("Alice", "30")

    def test_missing_both_leading_and_trailing_pipes(self) -> None:
        md = textwrap.dedent("""\
            Name | Age
            -----|----
            Alice | 30
        """)
        table = _single(scan_tables(md))
        assert table.headers == ("Name", "Age")
        assert table.rows[0] == ("Alice", "30")

    def test_inconsistent_spacing(self) -> None:
        md = textwrap.dedent("""\
            |Name|  Age  |City|
            |---|---|---|
            |Alice|30|NYC|
        """)
        table = _single(scan_tables(md))
        assert table.headers == ("Name", "Age", "City")
        assert table.rows[0] == ("Alice", "30", "NYC")

    def test_alignment_markers_center(self) -> None:
        md = textwrap.dedent("""\
            | Name  | Age | City   |
            |:-----:|:---:|:------:|
            | Alice | 30  | NYC    |
        """)
        table = _single(scan_tables(md))
        assert table.headers == ("Name", "Age", "City")
        assert table.rows[0] == ("Alice", "30", "NYC")

    def test_alignment_markers_right(self) -> None:
        md = textwrap.dedent("""\
            | Name  | Age | City   |
            |------:|----:|-------:|
            | Alice | 30  | NYC    |
        """)
        table = _single(scan_tables(md))
        assert len(table.rows) == 1

    def test_alignment_markers_left(self) -> None:
        md = textwrap.dedent("""\
            | Name  | Age | City   |
            |:------|:----|:-------|
            | Alice | 30  | NYC    |
        """)
        table = _single(scan_tables(md))
        assert len(table.rows) == 1

    def test_single_column_table_not_detected(self) -> None:
        """Single-column tables are not detected — the separator regex
        requires at least one internal pipe (i.e., 2+ columns)."""
        md = textwrap.dedent("""\
            | Name  |
            |-------|
            | Alice |
            | Bob   |
        """)
        tables = scan_tables(md)
        assert tables == []

    def test_minimal_separator_single_col_not_detected(self) -> None:
        """A minimal single-column separator is not matched by the regex."""
        md = textwrap.dedent("""\
            | A |
            |-|
            | x |
        """)
        tables = scan_tables(md)
        assert tables == []

    def test_two_column_minimal_separator(self) -> None:
        """Minimal two-column separator works."""
        md = textwrap.dedent("""\
            | A | B |
            |-|-|
            | x | y |
        """)
        table = _single(scan_tables(md))
        assert table.headers == ("A", "B")
        assert table.rows[0] == ("x", "y")


# ---------------------------------------------------------------------------
# Multiple tables
# ---------------------------------------------------------------------------


class TestMultipleTables:
    """Documents containing multiple tables."""

    def test_three_tables_count_and_order(self) -> None:
        md = textwrap.dedent("""\
            | A | B |
            |---|---|
            | 1 | 2 |

            | C | D |
            |---|---|
            | 3 | 4 |

            | E | F |
            |---|---|
            | 5 | 6 |
        """)
        tables = scan_tables(md)
        assert len(tables) == 3
        assert tables[0].headers == ("A", "B")
        assert tables[1].headers == ("C", "D")
        assert tables[2].headers == ("E", "F")
        # Verify ordering by start_line
        assert tables[0].start_line < tables[1].start_line < tables[2].start_line

    def test_tables_under_different_headings(self) -> None:
        md = textwrap.dedent("""\
            ## Users

            | Name  | Age |
            |-------|-----|
            | Alice | 30  |

            ## Products

            | Item  | Price |
            |-------|-------|
            | Book  | 10    |
        """)
        tables = scan_tables(md)
        assert len(tables) == 2
        assert tables[0].heading == "Users"
        assert tables[1].heading == "Products"


# ---------------------------------------------------------------------------
# Index selection
# ---------------------------------------------------------------------------


class TestIndexSelection:
    """Selecting tables by 0-based index."""

    _MD = textwrap.dedent("""\
        | A | B |
        |---|---|
        | 1 | 2 |

        | C | D |
        |---|---|
        | 3 | 4 |

        | E | F |
        |---|---|
        | 5 | 6 |
    """)

    def test_index_zero_returns_first(self) -> None:
        tables = scan_tables(self._MD, index=0)
        assert len(tables) == 1
        assert tables[0].headers == ("A", "B")

    def test_index_one_returns_second(self) -> None:
        tables = scan_tables(self._MD, index=1)
        assert len(tables) == 1
        assert tables[0].headers == ("C", "D")

    def test_index_out_of_range_returns_empty(self) -> None:
        tables = scan_tables(self._MD, index=99)
        assert tables == []


# ---------------------------------------------------------------------------
# Heading selection
# ---------------------------------------------------------------------------


class TestHeadingSelection:
    """Selecting tables by heading text."""

    _MD = textwrap.dedent("""\
        ## Users

        | Name  | Age |
        |-------|-----|
        | Alice | 30  |

        ## Product Data

        | Item  | Price |
        |-------|-------|
        | Book  | 10    |

        ## Summary

        | Total | Count |
        |-------|-------|
        | 40    | 2     |
    """)

    def test_exact_heading_match(self) -> None:
        tables = scan_tables(self._MD, heading="Users")
        assert len(tables) == 1
        assert tables[0].headers == ("Name", "Age")

    def test_case_insensitive_heading(self) -> None:
        tables = scan_tables(self._MD, heading="users")
        assert len(tables) == 1
        assert tables[0].headers == ("Name", "Age")

    def test_substring_heading_match(self) -> None:
        tables = scan_tables(self._MD, heading="Product")
        assert len(tables) == 1
        assert tables[0].headers == ("Item", "Price")

    def test_no_heading_match_returns_empty(self) -> None:
        tables = scan_tables(self._MD, heading="Nonexistent")
        assert tables == []

    def test_combined_heading_and_index(self) -> None:
        md = textwrap.dedent("""\
            ## Data

            | A | B |
            |---|---|
            | 1 | 2 |

            ## Data Section

            | C | D |
            |---|---|
            | 3 | 4 |

            ## Other

            | E | F |
            |---|---|
            | 5 | 6 |
        """)
        # heading="Data" matches both "Data" and "Data Section"
        tables = scan_tables(md, heading="Data")
        assert len(tables) == 2

        # Combined: heading="Data" + index=1 -> second matching table
        tables = scan_tables(md, heading="Data", index=1)
        assert len(tables) == 1
        assert tables[0].headers == ("C", "D")


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge conditions for table scanning."""

    def test_table_inside_fenced_code_block_not_detected(self) -> None:
        md = textwrap.dedent("""\
            ```
            | Name  | Age |
            |-------|-----|
            | Alice | 30  |
            ```
        """)
        tables = scan_tables(md)
        assert tables == []

    def test_table_inside_json_fenced_block_not_detected(self) -> None:
        md = textwrap.dedent("""\
            ```json
            | Name  | Age |
            |-------|-----|
            | Alice | 30  |
            ```
        """)
        tables = scan_tables(md)
        assert tables == []

    def test_table_inside_unclosed_fenced_block_not_detected(self) -> None:
        md = textwrap.dedent("""\
            ```
            | Name  | Age |
            |-------|-----|
            | Alice | 30  |
        """)
        tables = scan_tables(md)
        assert tables == []

    def test_table_inside_unclosed_json_fenced_block_not_detected(self) -> None:
        md = textwrap.dedent("""\
            ```json
            | Name  | Age |
            |-------|-----|
            | Alice | 30  |
        """)
        tables = scan_tables(md)
        assert tables == []

    def test_empty_cells(self) -> None:
        md = textwrap.dedent("""\
            | A | B | C |
            |---|---|---|
            |   | value |   |
        """)
        table = _single(scan_tables(md))
        assert table.rows[0] == ("", "value", "")

    def test_escaped_pipes_in_cells(self) -> None:
        md = textwrap.dedent("""\
            | Expression | Result |
            |------------|--------|
            | a \\| b     | true   |
        """)
        table = _single(scan_tables(md))
        assert table.rows[0] == ("a | b", "true")

    def test_short_rows_padded_with_empty_strings(self) -> None:
        md = textwrap.dedent("""\
            | A | B | C |
            |---|---|---|
            | 1 |
        """)
        table = _single(scan_tables(md))
        # The short row should be padded to match header count
        assert len(table.rows[0]) == 3
        assert table.rows[0][0] == "1"
        assert table.rows[0][1] == ""
        assert table.rows[0][2] == ""

    def test_extra_cells_in_data_rows_truncated(self) -> None:
        md = textwrap.dedent("""\
            | A | B |
            |---|---|
            | 1 | 2 | 3 | 4 |
        """)
        table = _single(scan_tables(md))
        assert len(table.rows[0]) == 2
        assert table.rows[0] == ("1", "2")

    def test_blank_line_terminates_table(self) -> None:
        md = textwrap.dedent("""\
            | A | B |
            |---|---|
            | 1 | 2 |

            This is not part of the table.

            | C | D |
        """)
        tables = scan_tables(md)
        assert len(tables) == 1
        assert tables[0].rows == (("1", "2"),)

    def test_windows_line_endings(self) -> None:
        md = "| A | B |\r\n|---|---|\r\n| 1 | 2 |\r\n"
        table = _single(scan_tables(md))
        assert table.headers == ("A", "B")
        assert table.rows[0] == ("1", "2")

    def test_empty_input(self) -> None:
        tables = scan_tables("")
        assert tables == []

    def test_no_tables_in_prose(self) -> None:
        md = "This is just plain text with no tables at all."
        tables = scan_tables(md)
        assert tables == []

    def test_table_with_zero_data_rows(self) -> None:
        md = textwrap.dedent("""\
            | A | B |
            |---|---|
        """)
        table = _single(scan_tables(md))
        assert table.headers == ("A", "B")
        assert table.rows == ()

    def test_table_embedded_in_prose(self) -> None:
        md = textwrap.dedent("""\
            Here is some introductory text about the data.

            | Name  | Age |
            |-------|-----|
            | Alice | 30  |

            And here is some concluding text after the table.
        """)
        table = _single(scan_tables(md))
        assert table.headers == ("Name", "Age")
        assert table.rows[0] == ("Alice", "30")

    def test_heading_attribute_is_none_without_heading(self) -> None:
        md = textwrap.dedent("""\
            | A | B |
            |---|---|
            | 1 | 2 |
        """)
        table = _single(scan_tables(md))
        assert table.heading is None

    def test_start_and_end_line_populated(self) -> None:
        md = textwrap.dedent("""\
            Some text.

            | A | B |
            |---|---|
            | 1 | 2 |
            | 3 | 4 |
        """)
        table = _single(scan_tables(md))
        # Table starts at line 2 (0-based: "Some text." is 0, blank is 1)
        assert table.start_line == 2
        assert table.end_line >= table.start_line


# ---------------------------------------------------------------------------
# Helper function: _is_separator_row
# ---------------------------------------------------------------------------


class TestIsSeparatorRow:
    """Direct tests for the _is_separator_row helper."""

    def test_standard_separator(self) -> None:
        assert _is_separator_row("|---|---|---|") is True

    def test_separator_with_colons_center(self) -> None:
        assert _is_separator_row("|:---:|:---:|") is True

    def test_separator_with_colons_right(self) -> None:
        assert _is_separator_row("|---:|---:|") is True

    def test_separator_with_colons_left(self) -> None:
        assert _is_separator_row("|:---|:---|") is True

    def test_separator_no_leading_pipe(self) -> None:
        assert _is_separator_row("---|---") is True

    def test_separator_no_trailing_pipe(self) -> None:
        assert _is_separator_row("|---|---") is True

    def test_separator_with_spaces(self) -> None:
        assert _is_separator_row("| --- | --- |") is True

    def test_minimal_separator_single_col_not_matched(self) -> None:
        """Single-column minimal separator doesn't match the regex
        (requires at least one internal pipe between dash groups)."""
        assert _is_separator_row("|-|") is False

    def test_minimal_separator_two_cols(self) -> None:
        assert _is_separator_row("|-|-|") is True

    def test_long_dashes(self) -> None:
        assert _is_separator_row("|------------|--------|") is True

    def test_not_separator_no_dashes(self) -> None:
        assert _is_separator_row("| a | b |") is False

    def test_not_separator_text_content(self) -> None:
        assert _is_separator_row("| Name | Age |") is False

    def test_not_separator_empty_string(self) -> None:
        assert _is_separator_row("") is False

    def test_not_separator_only_pipes(self) -> None:
        assert _is_separator_row("|||") is False

    def test_single_column_separator_not_matched(self) -> None:
        """Single-column separator doesn't match (regex needs 2+ columns)."""
        assert _is_separator_row("|---|") is False


# ---------------------------------------------------------------------------
# Helper function: _parse_table_row
# ---------------------------------------------------------------------------


class TestParseTableRow:
    """Direct tests for the _parse_table_row helper."""

    def test_standard_row(self) -> None:
        result = _parse_table_row("| Alice | 30 | NYC |")
        assert result == ["Alice", "30", "NYC"]

    def test_no_leading_pipe(self) -> None:
        result = _parse_table_row("Alice | 30 | NYC |")
        assert result == ["Alice", "30", "NYC"]

    def test_no_trailing_pipe(self) -> None:
        result = _parse_table_row("| Alice | 30 | NYC")
        assert result == ["Alice", "30", "NYC"]

    def test_no_pipes_on_either_end(self) -> None:
        result = _parse_table_row("Alice | 30 | NYC")
        assert result == ["Alice", "30", "NYC"]

    def test_escaped_pipe(self) -> None:
        result = _parse_table_row("| a \\| b | c |")
        assert result == ["a | b", "c"]

    def test_empty_cells(self) -> None:
        result = _parse_table_row("|  | value |  |")
        assert result == ["", "value", ""]

    def test_single_cell(self) -> None:
        result = _parse_table_row("| hello |")
        assert result == ["hello"]

    def test_whitespace_stripped(self) -> None:
        result = _parse_table_row("|  lots of space  |   more   |")
        assert result == ["lots of space", "more"]


# ---------------------------------------------------------------------------
# Helper function: _has_pipe
# ---------------------------------------------------------------------------


class TestHasPipe:
    """Direct tests for the _has_pipe helper."""

    def test_line_with_pipe(self) -> None:
        assert _has_pipe("| hello |") is True

    def test_line_without_pipe(self) -> None:
        assert _has_pipe("hello world") is False

    def test_empty_string(self) -> None:
        assert _has_pipe("") is False

    def test_whitespace_only(self) -> None:
        assert _has_pipe("   ") is False

    def test_escaped_pipe_only(self) -> None:
        assert _has_pipe("hello \\| world") is False

    def test_escaped_and_unescaped_pipe(self) -> None:
        assert _has_pipe("hello \\| world | end") is True

    def test_pipe_at_start(self) -> None:
        assert _has_pipe("| value") is True

    def test_pipe_at_end(self) -> None:
        assert _has_pipe("value |") is True
