"""Integration tests for the scan_tables → table_to_dicts pipeline
and the scan_blocks → block_to_dict/blocks_to_dicts pipeline."""

from __future__ import annotations

import textwrap

from md2pydantic.models import BlockType
from md2pydantic.parser import scan_blocks, scan_tables
from md2pydantic.transformers import (
    block_to_dict,
    blocks_to_dicts,
    table_to_dataframe,
    table_to_dicts,
    tables_to_dicts,
)


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


# ---------------------------------------------------------------------------
# scan_blocks → block_to_dict / blocks_to_dicts integration tests
# ---------------------------------------------------------------------------


class TestFencedJSONInLLMResponse:
    """Scenario 1: Fenced JSON block surrounded by prose."""

    def test_fenced_json_extracted_and_parsed(self) -> None:
        md = textwrap.dedent("""\
            Sure, here is the configuration you asked for:

            ```json
            {"name": "Alice", "age": 30, "active": true}
            ```

            Let me know if you need anything else!
        """)

        blocks = scan_blocks(md)
        assert len(blocks) == 1
        assert blocks[0].block_type == BlockType.JSON
        assert blocks[0].fenced is True

        result = block_to_dict(blocks[0])
        assert result.error is None
        assert result.data == {"name": "Alice", "age": 30, "active": True}
        assert result.block_type == BlockType.JSON


class TestFencedYAMLInLLMResponse:
    """Scenario 2: Fenced YAML block surrounded by prose."""

    def test_fenced_yaml_extracted_and_parsed(self) -> None:
        md = textwrap.dedent("""\
            Here is your YAML config:

            ```yaml
            database:
              host: localhost
              port: 5432
              name: mydb
            debug: true
            ```

            That should work for your setup.
        """)

        blocks = scan_blocks(md)
        assert len(blocks) == 1
        assert blocks[0].block_type == BlockType.YAML
        assert blocks[0].fenced is True

        result = block_to_dict(blocks[0])
        assert result.error is None
        assert result.data == {
            "database": {"host": "localhost", "port": 5432, "name": "mydb"},
            "debug": True,
        }
        assert result.block_type == BlockType.YAML


class TestMessyJSONTrailingCommas:
    """Scenario 3: Fenced JSON with trailing commas gets cleaned and parsed."""

    def test_trailing_commas_cleaned(self) -> None:
        md = textwrap.dedent("""\
            ```json
            {"a": 1, "b": 2,}
            ```
        """)

        blocks = scan_blocks(md)
        assert len(blocks) == 1

        result = block_to_dict(blocks[0])
        assert result.error is None
        assert result.data == {"a": 1, "b": 2}

    def test_nested_trailing_commas(self) -> None:
        md = textwrap.dedent("""\
            ```json
            {"items": [1, 2, 3,], "meta": {"count": 3,},}
            ```
        """)

        blocks = scan_blocks(md)
        assert len(blocks) == 1

        result = block_to_dict(blocks[0])
        assert result.error is None
        assert result.data == {"items": [1, 2, 3], "meta": {"count": 3}}


class TestInlineJSONInProse:
    """Scenario 4: Bare JSON object embedded in prose text."""

    def test_inline_json_detected_and_parsed(self) -> None:
        md = textwrap.dedent("""\
            The result is {"key": "value", "count": 42} and that's it.
        """)

        blocks = scan_blocks(md)
        assert len(blocks) == 1
        assert blocks[0].fenced is False
        assert blocks[0].block_type == BlockType.JSON

        result = block_to_dict(blocks[0])
        assert result.error is None
        assert result.data == {"key": "value", "count": 42}


class TestMultipleMixedBlocks:
    """Both JSON and YAML blocks parsed via blocks_to_dicts."""

    def test_json_and_yaml_both_parsed(self) -> None:
        md = textwrap.dedent("""\
            Here is some JSON:

            ```json
            {"status": "ok", "code": 200}
            ```

            And here is some YAML:

            ```yaml
            server:
              host: 0.0.0.0
              port: 8080
            ```

            That covers both formats.
        """)

        blocks = scan_blocks(md)
        assert len(blocks) == 2

        results = blocks_to_dicts(blocks)
        assert len(results) == 2

        # First block: JSON
        assert results[0].error is None
        assert results[0].data == {"status": "ok", "code": 200}
        assert results[0].block_type == BlockType.JSON

        # Second block: YAML
        assert results[1].error is None
        assert results[1].data == {"server": {"host": "0.0.0.0", "port": 8080}}
        assert results[1].block_type == BlockType.YAML


class TestTruncatedJSONRecovery:
    """Scenario 6: Fenced JSON with missing closing braces is recovered."""

    def test_missing_closing_braces_recovered(self) -> None:
        md = textwrap.dedent("""\
            ```json
            {"user": {"name": "Alice", "address": {"city": "NYC"
            ```
        """)

        blocks = scan_blocks(md)
        assert len(blocks) == 1

        result = block_to_dict(blocks[0])
        assert result.error is None
        assert result.data is not None
        # The recovery should produce a valid nested structure
        assert result.data["user"]["name"] == "Alice"
        assert result.data["user"]["address"]["city"] == "NYC"

    def test_missing_closing_bracket_recovered(self) -> None:
        md = textwrap.dedent("""\
            ```json
            {"items": [1, 2, 3
            ```
        """)

        blocks = scan_blocks(md)
        assert len(blocks) == 1

        result = block_to_dict(blocks[0])
        assert result.error is None
        assert result.data is not None
        assert result.data["items"] == [1, 2, 3]


class TestInvalidContentError:
    """Unparseable fenced block returns error in TransformResult."""

    def test_unparseable_json_returns_error(self) -> None:
        md = textwrap.dedent("""\
            ```json
            this is not json at all @@@ !!!
            ```
        """)

        blocks = scan_blocks(md)
        # The scanner may or may not detect this as a JSON block depending on
        # content heuristics, but if it's labeled json it should be attempted.
        # Since the lang hint is "json", scan_blocks should pick it up.
        assert len(blocks) == 1
        assert blocks[0].block_type == BlockType.JSON

        result = block_to_dict(blocks[0])
        assert result.data is None
        assert result.error is not None
        assert "parse failed" in result.error.lower() or "error" in result.error.lower()
        assert result.raw_content == blocks[0].content

    def test_unparseable_yaml_returns_error(self) -> None:
        md = textwrap.dedent("""\
            ```yaml
            : : : [[[invalid
            ```
        """)

        blocks = scan_blocks(md)
        assert len(blocks) == 1
        assert blocks[0].block_type == BlockType.YAML

        result = block_to_dict(blocks[0])
        assert result.data is None
        assert result.error is not None
