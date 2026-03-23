"""Integration tests for table scanning with realistic LLM output samples.

These tests exercise the full scan_tables pipeline against messy Markdown
strings that real LLMs (ChatGPT, Claude, etc.) commonly produce, including
tables with inconsistent formatting, mixed content, and edge cases.
"""

from __future__ import annotations

from md2pydantic.parser import scan_blocks, scan_tables


class TestChatGPTStyleDataTable:
    """ChatGPT-style response with a data table wrapped in prose."""

    MARKDOWN = (
        "Here's the user data you requested:\n"
        "\n"
        "| Name | Age | Active |\n"
        "|---|---|---|\n"
        "| Alice | 30 | Yes |\n"
        "| Bob | 25 | No |\n"
        "\n"
        "Let me know if you need anything else!"
    )

    def test_extracts_single_table(self) -> None:
        tables = scan_tables(self.MARKDOWN)
        assert len(tables) == 1

    def test_headers_match(self) -> None:
        tables = scan_tables(self.MARKDOWN)
        assert tables[0].headers == ("Name", "Age", "Active")

    def test_row_count(self) -> None:
        tables = scan_tables(self.MARKDOWN)
        assert len(tables[0].rows) == 2

    def test_first_row_values(self) -> None:
        tables = scan_tables(self.MARKDOWN)
        assert tables[0].rows[0] == ("Alice", "30", "Yes")

    def test_second_row_values(self) -> None:
        tables = scan_tables(self.MARKDOWN)
        assert tables[0].rows[1] == ("Bob", "25", "No")

    def test_prose_not_in_table(self) -> None:
        tables = scan_tables(self.MARKDOWN)
        all_cells = [cell for row in tables[0].rows for cell in row]
        assert "Here's" not in " ".join(all_cells)
        assert "anything else" not in " ".join(all_cells)


class TestMultipleTablesUnderHeadings:
    """LLM response with multiple tables under different headings."""

    MARKDOWN = (
        "## Users\n"
        "\n"
        "| Name | Role |\n"
        "|---|---|\n"
        "| Alice | Admin |\n"
        "\n"
        "## Products\n"
        "\n"
        "| Name | Price |\n"
        "|---|---|\n"
        "| Widget | 9.99 |\n"
    )

    def test_extracts_two_tables(self) -> None:
        tables = scan_tables(self.MARKDOWN)
        assert len(tables) == 2

    def test_first_table_heading_is_users(self) -> None:
        tables = scan_tables(self.MARKDOWN)
        assert tables[0].heading == "Users"

    def test_second_table_heading_is_products(self) -> None:
        tables = scan_tables(self.MARKDOWN)
        assert tables[1].heading == "Products"

    def test_filter_by_heading_users(self) -> None:
        tables = scan_tables(self.MARKDOWN, heading="Users")
        assert len(tables) == 1
        assert tables[0].headers == ("Name", "Role")

    def test_filter_by_heading_products(self) -> None:
        tables = scan_tables(self.MARKDOWN, heading="Products")
        assert len(tables) == 1
        assert tables[0].headers == ("Name", "Price")

    def test_filter_by_heading_case_insensitive(self) -> None:
        tables = scan_tables(self.MARKDOWN, heading="users")
        assert len(tables) == 1
        assert tables[0].heading == "Users"

    def test_first_table_data(self) -> None:
        tables = scan_tables(self.MARKDOWN)
        assert tables[0].rows[0] == ("Alice", "Admin")

    def test_second_table_data(self) -> None:
        tables = scan_tables(self.MARKDOWN)
        assert tables[1].rows[0] == ("Widget", "9.99")

    def test_tables_ordered_by_position(self) -> None:
        tables = scan_tables(self.MARKDOWN)
        assert tables[0].start_line < tables[1].start_line


class TestTableMixedWithJsonCodeBlock:
    """Document with both a JSON code block and a table."""

    MARKDOWN = (
        "Here is the config:\n"
        "\n"
        "```json\n"
        '{"setting": "enabled"}\n'
        "```\n"
        "\n"
        "And here are the results:\n"
        "\n"
        "| Metric | Value |\n"
        "|---|---|\n"
        "| Latency | 42ms |\n"
        "| Throughput | 1000rps |\n"
    )

    def test_table_scanner_finds_one_table(self) -> None:
        tables = scan_tables(self.MARKDOWN)
        assert len(tables) == 1

    def test_table_headers(self) -> None:
        tables = scan_tables(self.MARKDOWN)
        assert tables[0].headers == ("Metric", "Value")

    def test_table_rows(self) -> None:
        tables = scan_tables(self.MARKDOWN)
        assert len(tables[0].rows) == 2
        assert tables[0].rows[0] == ("Latency", "42ms")
        assert tables[0].rows[1] == ("Throughput", "1000rps")

    def test_code_block_scanner_finds_json(self) -> None:
        blocks = scan_blocks(self.MARKDOWN)
        assert len(blocks) == 1
        assert blocks[0].block_type.value == "json"

    def test_table_not_inside_code_block(self) -> None:
        tables = scan_tables(self.MARKDOWN)
        blocks = scan_blocks(self.MARKDOWN)
        # The table should start after the code block ends
        assert tables[0].start_line > blocks[0].end_line


class TestMessyLLMTableFormatting:
    """Table with inconsistent formatting: extra spaces and alignment markers."""

    MARKDOWN = (
        "| Name    |   Age |  City       |\n"
        "| :------ | ----: | :---------: |\n"
        "|  Alice  |   30  |  New York   |\n"
        "|Bob|25|London|\n"
    )

    def test_extracts_single_table(self) -> None:
        tables = scan_tables(self.MARKDOWN)
        assert len(tables) == 1

    def test_headers_stripped(self) -> None:
        tables = scan_tables(self.MARKDOWN)
        assert tables[0].headers == ("Name", "Age", "City")

    def test_row_count(self) -> None:
        tables = scan_tables(self.MARKDOWN)
        assert len(tables[0].rows) == 2

    def test_cells_stripped_of_whitespace(self) -> None:
        tables = scan_tables(self.MARKDOWN)
        assert tables[0].rows[0] == ("Alice", "30", "New York")
        assert tables[0].rows[1] == ("Bob", "25", "London")


class TestTableWithEmptyCellsAndEscapedPipes:
    """Table containing empty cells and escaped pipe characters."""

    MARKDOWN = (
        "| Command | Description | Notes |\n"
        "|---|---|---|\n"
        "| ls | List files | |\n"
        "| echo \\| grep | Pipe example | uses \\| char |\n"
        "| cd | Change dir | basic |\n"
    )

    def test_extracts_single_table(self) -> None:
        tables = scan_tables(self.MARKDOWN)
        assert len(tables) == 1

    def test_row_count(self) -> None:
        tables = scan_tables(self.MARKDOWN)
        assert len(tables[0].rows) == 3

    def test_empty_cell_preserved(self) -> None:
        tables = scan_tables(self.MARKDOWN)
        # First data row has an empty Notes cell
        assert tables[0].rows[0] == ("ls", "List files", "")

    def test_escaped_pipe_in_cell(self) -> None:
        tables = scan_tables(self.MARKDOWN)
        # Escaped pipes should be restored as literal pipes
        assert tables[0].rows[1][0] == "echo | grep"
        assert tables[0].rows[1][2] == "uses | char"

    def test_normal_row_after_escaped_pipes(self) -> None:
        tables = scan_tables(self.MARKDOWN)
        assert tables[0].rows[2] == ("cd", "Change dir", "basic")


class TestLargeTableManyRows:
    """Table with 12 rows to verify all are extracted correctly."""

    ROWS: tuple[tuple[str, str, str], ...] = (
        ("Alice", "30", "Engineer"),
        ("Bob", "25", "Designer"),
        ("Charlie", "35", "Manager"),
        ("Diana", "28", "Analyst"),
        ("Eve", "32", "Developer"),
        ("Frank", "40", "Director"),
        ("Grace", "27", "Intern"),
        ("Hank", "45", "VP"),
        ("Iris", "29", "Consultant"),
        ("Jack", "33", "Architect"),
        ("Karen", "31", "Lead"),
        ("Leo", "26", "Tester"),
    )

    MARKDOWN = "| Name | Age | Role |\n|---|---|---|\n" + "".join(
        f"| {name} | {age} | {role} |\n" for name, age, role in ROWS
    )

    def test_extracts_single_table(self) -> None:
        tables = scan_tables(self.MARKDOWN)
        assert len(tables) == 1

    def test_all_rows_extracted(self) -> None:
        tables = scan_tables(self.MARKDOWN)
        assert len(tables[0].rows) == 12

    def test_first_row(self) -> None:
        tables = scan_tables(self.MARKDOWN)
        assert tables[0].rows[0] == ("Alice", "30", "Engineer")

    def test_last_row(self) -> None:
        tables = scan_tables(self.MARKDOWN)
        assert tables[0].rows[11] == ("Leo", "26", "Tester")

    def test_all_rows_match_source_data(self) -> None:
        tables = scan_tables(self.MARKDOWN)
        for i, expected in enumerate(self.ROWS):
            assert tables[0].rows[i] == expected, f"Row {i} mismatch"


class TestTableImmediatelyAfterHeading:
    """Table immediately following a heading with no blank line in between."""

    MARKDOWN = "## Results\n| col1 | col2 |\n|---|---|\n| a | b |\n"

    def test_extracts_single_table(self) -> None:
        tables = scan_tables(self.MARKDOWN)
        assert len(tables) == 1

    def test_heading_association(self) -> None:
        tables = scan_tables(self.MARKDOWN)
        assert tables[0].heading == "Results"

    def test_headers(self) -> None:
        tables = scan_tables(self.MARKDOWN)
        assert tables[0].headers == ("col1", "col2")

    def test_data_row(self) -> None:
        tables = scan_tables(self.MARKDOWN)
        assert tables[0].rows[0] == ("a", "b")


class TestTableInsideFencedCodeBlockExcluded:
    """A table inside a fenced code block should not be detected as a table."""

    MARKDOWN = (
        "Here is an example table in a code block:\n"
        "\n"
        "```\n"
        "| Header1 | Header2 |\n"
        "|---|---|\n"
        "| val1 | val2 |\n"
        "```\n"
        "\n"
        "And here is a real table:\n"
        "\n"
        "| Real | Table |\n"
        "|---|---|\n"
        "| data1 | data2 |\n"
    )

    def test_only_real_table_extracted(self) -> None:
        tables = scan_tables(self.MARKDOWN)
        assert len(tables) == 1

    def test_extracted_table_is_real_one(self) -> None:
        tables = scan_tables(self.MARKDOWN)
        assert tables[0].headers == ("Real", "Table")
        assert tables[0].rows[0] == ("data1", "data2")


class TestIndexParameter:
    """Verify the index parameter selects the correct table."""

    MARKDOWN = "| A | B |\n|---|---|\n| 1 | 2 |\n\n| C | D |\n|---|---|\n| 3 | 4 |\n"

    def test_index_zero_returns_first_table(self) -> None:
        tables = scan_tables(self.MARKDOWN, index=0)
        assert len(tables) == 1
        assert tables[0].headers == ("A", "B")

    def test_index_one_returns_second_table(self) -> None:
        tables = scan_tables(self.MARKDOWN, index=1)
        assert len(tables) == 1
        assert tables[0].headers == ("C", "D")

    def test_out_of_range_index_returns_empty(self) -> None:
        tables = scan_tables(self.MARKDOWN, index=99)
        assert len(tables) == 0
