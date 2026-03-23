"""Integration tests for the scan_tables → table_to_dicts pipeline."""

from __future__ import annotations

import textwrap

from md2pydantic.parser import scan_blocks, scan_tables
from md2pydantic.transformers import table_to_dataframe, table_to_dicts, tables_to_dicts


class TestFullPipelineMarkdownToDicts:
    """Parse a realistic LLM response with a table, then convert to dicts."""

    def test_realistic_llm_response(self) -> None:
        md = textwrap.dedent("""\
            Here is the data you requested:

            | Name   | Age | City       |
            |--------|-----|------------|
            | Alice  | 30  | New York   |
            | Bob    | 25  | London     |
            | Charlie| 40  | Tokyo      |

            Let me know if you need anything else!
        """)

        tables = scan_tables(md)
        assert len(tables) == 1

        dicts = table_to_dicts(tables[0])

        assert len(dicts) == 3
        assert dicts[0] == {"Name": "Alice", "Age": "30", "City": "New York"}
        assert dicts[1] == {"Name": "Bob", "Age": "25", "City": "London"}
        assert dicts[2] == {"Name": "Charlie", "Age": "40", "City": "Tokyo"}


class TestPipelineWithHeadingFilter:
    """Scenario 2: Use scan_tables with heading filter, verify only correct table."""

    def test_heading_filter_selects_correct_table(self) -> None:
        md = textwrap.dedent("""\
            ## Users

            | Name  | Role    |
            |-------|---------|
            | Alice | Admin   |
            | Bob   | Editor  |

            ## Products

            | Product | Price |
            |---------|-------|
            | Widget  | 9.99  |
            | Gadget  | 19.99 |
        """)

        tables = scan_tables(md, heading="Products")
        assert len(tables) == 1

        dicts = table_to_dicts(tables[0])

        assert len(dicts) == 2
        assert dicts[0] == {"Product": "Widget", "Price": "9.99"}
        assert dicts[1] == {"Product": "Gadget", "Price": "19.99"}

    def test_heading_filter_no_match_returns_empty(self) -> None:
        md = textwrap.dedent("""\
            ## Users

            | Name  | Role  |
            |-------|-------|
            | Alice | Admin |
        """)

        tables = scan_tables(md, heading="Products")
        assert len(tables) == 0


class TestMultipleTablesPipeline:
    """Scenario 3: Parse doc with 2 tables, use tables_to_dicts."""

    def test_two_tables_converted_correctly(self) -> None:
        md = textwrap.dedent("""\
            ## Employees

            | Name  | Department |
            |-------|------------|
            | Alice | Engineering|
            | Bob   | Marketing  |

            ## Projects

            | Project | Status    |
            |---------|-----------|
            | Alpha   | Active    |
            | Beta    | Completed |
            | Gamma   | Planned   |
        """)

        tables = scan_tables(md)
        assert len(tables) == 2

        all_dicts = tables_to_dicts(tables)

        assert len(all_dicts) == 2
        assert len(all_dicts[0]) == 2
        assert len(all_dicts[1]) == 3

        assert all_dicts[0][0] == {"Name": "Alice", "Department": "Engineering"}
        assert all_dicts[0][1] == {"Name": "Bob", "Department": "Marketing"}

        assert all_dicts[1][0] == {"Project": "Alpha", "Status": "Active"}
        assert all_dicts[1][1] == {"Project": "Beta", "Status": "Completed"}
        assert all_dicts[1][2] == {"Project": "Gamma", "Status": "Planned"}


class TestEmptyCellsThroughPipeline:
    """Scenario 4: Table with empty cells produces None values in output dicts."""

    def test_empty_cells_become_none(self) -> None:
        md = textwrap.dedent("""\
            | Name  | Email          | Phone |
            |-------|----------------|-------|
            | Alice | alice@test.com |       |
            | Bob   |                | 555   |
            |       | carol@test.com | 123   |
        """)

        tables = scan_tables(md)
        assert len(tables) == 1

        dicts = table_to_dicts(tables[0])

        assert len(dicts) == 3
        assert dicts[0] == {"Name": "Alice", "Email": "alice@test.com", "Phone": None}
        assert dicts[1] == {"Name": "Bob", "Email": None, "Phone": "555"}
        assert dicts[2] == {"Name": None, "Email": "carol@test.com", "Phone": "123"}


class TestMessyLLMTableThroughPipeline:
    """Scenario 5: Table with inconsistent formatting produces clean dicts."""

    def test_inconsistent_spacing_and_alignment(self) -> None:
        md = textwrap.dedent("""\
            Sure! Here's that table:

            |Name|  Age  |City|
            |---|---|---|
            |  Alice  |30|  New York  |
            |Bob|  25  |London|

            Hope that helps!
        """)

        tables = scan_tables(md)
        assert len(tables) == 1

        dicts = table_to_dicts(tables[0])

        assert len(dicts) == 2
        assert dicts[0] == {"Name": "Alice", "Age": "30", "City": "New York"}
        assert dicts[1] == {"Name": "Bob", "Age": "25", "City": "London"}

    def test_extra_whitespace_in_separator(self) -> None:
        md = textwrap.dedent("""\
            | Fruit  |  Count  |
            | ------ | ------- |
            | Apple  |  5      |
            | Banana |  12     |
        """)

        tables = scan_tables(md)
        assert len(tables) == 1

        dicts = table_to_dicts(tables[0])

        assert dicts[0] == {"Fruit": "Apple", "Count": "5"}
        assert dicts[1] == {"Fruit": "Banana", "Count": "12"}


class TestPipelineWithPandas:
    """Scenario 6: scan_tables → table_to_dataframe produces correct DataFrame."""

    def test_table_to_dataframe(self) -> None:
        __import__("pytest").importorskip("pandas")

        md = textwrap.dedent("""\
            | Name  | Age | Score |
            |-------|-----|-------|
            | Alice | 30  | 95.5  |
            | Bob   | 25  | 87.0  |
        """)

        tables = scan_tables(md)
        assert len(tables) == 1

        df = table_to_dataframe(tables[0])

        assert list(df.columns) == ["Name", "Age", "Score"]
        assert len(df) == 2
        assert df.iloc[0]["Name"] == "Alice"
        assert df.iloc[0]["Age"] == "30"
        assert df.iloc[1]["Name"] == "Bob"
        assert df.iloc[1]["Score"] == "87.0"

    def test_dataframe_with_empty_cells(self) -> None:
        __import__("pytest").importorskip("pandas")

        md = textwrap.dedent("""\
            | X | Y |
            |---|---|
            | a |   |
            |   | b |
        """)

        tables = scan_tables(md)
        df = table_to_dataframe(tables[0])

        assert df.iloc[0]["X"] == "a"
        assert df.iloc[0]["Y"] is None
        assert df.iloc[1]["X"] is None
        assert df.iloc[1]["Y"] == "b"


class TestTableMixedWithJSONBlocks:
    """Scenario 7: Verify scan_tables and scan_blocks each find their blocks."""

    def test_table_and_json_coexist(self) -> None:
        md = textwrap.dedent("""\
            Here is a JSON config:

            ```json
            {"key": "value", "count": 42}
            ```

            And here is a summary table:

            | Metric   | Value |
            |----------|-------|
            | Accuracy | 0.95  |
            | Loss     | 0.12  |

            That's all the data.
        """)

        # scan_blocks finds the JSON block
        blocks = scan_blocks(md)
        assert len(blocks) == 1
        assert "key" in blocks[0].content
        assert blocks[0].block_type.value == "json"

        # scan_tables finds the table
        tables = scan_tables(md)
        assert len(tables) == 1
        assert tables[0].headers == ("Metric", "Value")

        # table_to_dicts converts correctly
        dicts = table_to_dicts(tables[0])
        assert len(dicts) == 2
        assert dicts[0] == {"Metric": "Accuracy", "Value": "0.95"}
        assert dicts[1] == {"Metric": "Loss", "Value": "0.12"}

    def test_multiple_json_blocks_and_table(self) -> None:
        md = textwrap.dedent("""\
            ```json
            {"a": 1}
            ```

            | Col1 | Col2 |
            |------|------|
            | x    | y    |

            ```yaml
            b: 2
            ```
        """)

        blocks = scan_blocks(md)
        assert len(blocks) == 2

        tables = scan_tables(md)
        assert len(tables) == 1

        dicts = table_to_dicts(tables[0])
        assert dicts == [{"Col1": "x", "Col2": "y"}]
