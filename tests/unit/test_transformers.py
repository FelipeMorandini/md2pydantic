"""Unit tests for the transformer module (transformers.py) — Issues #4 and #5.

Covers table_to_dicts, tables_to_dicts, table_to_dataframe,
json_block_to_dict, yaml_block_to_dict, block_to_dict, blocks_to_dicts,
and private JSON cleaning helpers.
"""

from __future__ import annotations

import json

import pytest

from md2pydantic.models import BlockType, CodeBlock, TableBlock, TransformResult
from md2pydantic.transformers import (
    _quote_unquoted_keys,
    _recover_truncated_json,
    _remove_trailing_commas,
    _single_to_double_quotes,
    block_to_dict,
    blocks_to_dicts,
    json_block_to_dict,
    table_to_dataframe,
    table_to_dicts,
    tables_to_dicts,
    yaml_block_to_dict,
)

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


# ---------------------------------------------------------------------------
# Helpers for JSON/YAML tests
# ---------------------------------------------------------------------------


def _make_code_block(
    content: str,
    block_type: BlockType = BlockType.JSON,
    *,
    fenced: bool = True,
    start_line: int = 0,
    end_line: int = 0,
) -> CodeBlock:
    """Build a CodeBlock for testing."""
    return CodeBlock(
        content=content,
        block_type=block_type,
        fenced=fenced,
        start_line=start_line,
        end_line=end_line,
    )


# ---------------------------------------------------------------------------
# json_block_to_dict
# ---------------------------------------------------------------------------


class TestJsonBlockToDict:
    """Tests for json_block_to_dict."""

    def test_well_formed_object(self) -> None:
        block = _make_code_block('{"name": "Alice", "age": 30}')
        result = json_block_to_dict(block)
        assert result.data == {"name": "Alice", "age": 30}
        assert result.error is None

    def test_well_formed_array(self) -> None:
        block = _make_code_block('[{"a": 1}, {"a": 2}]')
        result = json_block_to_dict(block)
        assert result.data == [{"a": 1}, {"a": 2}]
        assert result.error is None

    def test_trailing_commas(self) -> None:
        block = _make_code_block('{"a": 1, "b": 2,}')
        result = json_block_to_dict(block)
        assert result.data == {"a": 1, "b": 2}
        assert result.error is None

    def test_single_quotes(self) -> None:
        block = _make_code_block("{'key': 'value'}")
        result = json_block_to_dict(block)
        assert result.data == {"key": "value"}
        assert result.error is None

    def test_unquoted_keys(self) -> None:
        block = _make_code_block('{name: "Alice", age: 30}')
        result = json_block_to_dict(block)
        assert result.data == {"name": "Alice", "age": 30}
        assert result.error is None

    def test_mixed_issues(self) -> None:
        block = _make_code_block("{name: 'Alice', age: 30,}")
        result = json_block_to_dict(block)
        assert result.data == {"name": "Alice", "age": 30}
        assert result.error is None

    def test_truncated_json_simple(self) -> None:
        block = _make_code_block('{"name": "Alice", "age": 30')
        result = json_block_to_dict(block)
        assert result.data == {"name": "Alice", "age": 30}
        assert result.error is None

    def test_truncated_nested(self) -> None:
        block = _make_code_block('{"users": [{"name": "Alice"')
        result = json_block_to_dict(block)
        assert result.data == {"users": [{"name": "Alice"}]}
        assert result.error is None

    def test_empty_content(self) -> None:
        block = _make_code_block("")
        result = json_block_to_dict(block)
        assert result.data is None
        assert result.error == "Empty content"

    def test_whitespace_only_content(self) -> None:
        block = _make_code_block("   \n  \t  ")
        result = json_block_to_dict(block)
        assert result.data is None
        assert result.error == "Empty content"

    def test_completely_unparseable(self) -> None:
        block = _make_code_block("this is not json at all !!!")
        result = json_block_to_dict(block)
        assert result.data is None
        assert result.error is not None
        assert "JSON parse failed" in result.error

    def test_raw_content_preserved(self) -> None:
        raw = '{"a": 1, "b": 2,}'
        block = _make_code_block(raw)
        result = json_block_to_dict(block)
        assert result.raw_content == raw

    def test_block_type_preserved(self) -> None:
        block = _make_code_block('{"a": 1}', BlockType.JSON)
        result = json_block_to_dict(block)
        assert result.block_type == BlockType.JSON

    def test_trailing_comma_in_array(self) -> None:
        block = _make_code_block("[1, 2, 3,]")
        result = json_block_to_dict(block)
        assert result.data == [1, 2, 3]
        assert result.error is None

    def test_scalar_null_rejected(self) -> None:
        block = _make_code_block("null")
        result = json_block_to_dict(block)
        assert result.data is None
        assert result.error is not None
        assert "scalar" in result.error

    def test_scalar_boolean_rejected(self) -> None:
        block = _make_code_block("true")
        result = json_block_to_dict(block)
        assert result.data is None
        assert result.error is not None

    def test_scalar_number_rejected(self) -> None:
        block = _make_code_block("42")
        result = json_block_to_dict(block)
        assert result.data is None
        assert result.error is not None

    def test_scalar_string_rejected(self) -> None:
        block = _make_code_block('"hello"')
        result = json_block_to_dict(block)
        assert result.data is None
        assert result.error is not None

    def test_comma_inside_string_not_removed(self) -> None:
        """Trailing comma inside a string value should not be removed."""
        block = _make_code_block('{"msg": ",}"}')
        result = json_block_to_dict(block)
        assert result.data == {"msg": ",}"}


# ---------------------------------------------------------------------------
# yaml_block_to_dict
# ---------------------------------------------------------------------------


class TestYamlBlockToDict:
    """Tests for yaml_block_to_dict."""

    @pytest.fixture(autouse=True)
    def _skip_without_pyyaml(self) -> None:
        pytest.importorskip("yaml")

    def test_simple_key_value(self) -> None:
        block = _make_code_block("name: Alice\nage: 30\n", BlockType.YAML)
        result = yaml_block_to_dict(block)
        assert result.data == {"name": "Alice", "age": 30}
        assert result.error is None

    def test_nested_yaml(self) -> None:
        content = "user:\n  name: Alice\n  address:\n    city: NY\n"
        block = _make_code_block(content, BlockType.YAML)
        result = yaml_block_to_dict(block)
        assert result.data == {"user": {"name": "Alice", "address": {"city": "NY"}}}
        assert result.error is None

    def test_yaml_list(self) -> None:
        content = "- Alice\n- Bob\n- Charlie\n"
        block = _make_code_block(content, BlockType.YAML)
        result = yaml_block_to_dict(block)
        assert result.data == ["Alice", "Bob", "Charlie"]
        assert result.error is None

    def test_yaml_scalar_returns_error(self) -> None:
        block = _make_code_block("just a string", BlockType.YAML)
        result = yaml_block_to_dict(block)
        assert result.data is None
        assert result.error is not None
        assert "scalar" in result.error

    def test_invalid_yaml(self) -> None:
        content = ":\n  - :\n    - : : :\n  {{{"
        block = _make_code_block(content, BlockType.YAML)
        result = yaml_block_to_dict(block)
        assert result.data is None
        assert result.error is not None

    def test_empty_content(self) -> None:
        block = _make_code_block("", BlockType.YAML)
        result = yaml_block_to_dict(block)
        assert result.data is None
        assert result.error == "Empty content"

    def test_block_type_preserved(self) -> None:
        block = _make_code_block("key: val\n", BlockType.YAML)
        result = yaml_block_to_dict(block)
        assert result.block_type == BlockType.YAML

    def test_raw_content_preserved(self) -> None:
        raw = "key: val\n"
        block = _make_code_block(raw, BlockType.YAML)
        result = yaml_block_to_dict(block)
        assert result.raw_content == raw


# ---------------------------------------------------------------------------
# block_to_dict
# ---------------------------------------------------------------------------


class TestBlockToDict:
    """Tests for block_to_dict dispatch logic."""

    @pytest.fixture(autouse=True)
    def _skip_without_pyyaml(self) -> None:
        pytest.importorskip("yaml")

    def test_json_block_dispatches_to_json(self) -> None:
        block = _make_code_block('{"x": 1}', BlockType.JSON)
        result = block_to_dict(block)
        assert result.data == {"x": 1}
        assert result.error is None

    def test_yaml_block_dispatches_to_yaml(self) -> None:
        block = _make_code_block("x: 1\n", BlockType.YAML)
        result = block_to_dict(block)
        assert result.data == {"x": 1}
        assert result.error is None

    def test_unknown_block_tries_json_first(self) -> None:
        block = _make_code_block('{"x": 1}', BlockType.UNKNOWN)
        result = block_to_dict(block)
        assert result.data == {"x": 1}
        assert result.error is None

    def test_unknown_block_falls_back_to_yaml(self) -> None:
        block = _make_code_block("x: 1\ny: 2\n", BlockType.UNKNOWN)
        result = block_to_dict(block)
        assert result.data == {"x": 1, "y": 2}
        assert result.error is None


# ---------------------------------------------------------------------------
# blocks_to_dicts
# ---------------------------------------------------------------------------


class TestBlocksToDicts:
    """Tests for blocks_to_dicts."""

    def test_multiple_blocks(self) -> None:
        blocks = [
            _make_code_block('{"a": 1}', BlockType.JSON),
            _make_code_block('{"b": 2}', BlockType.JSON),
        ]
        results = blocks_to_dicts(blocks)
        assert len(results) == 2
        assert results[0].data == {"a": 1}
        assert results[1].data == {"b": 2}

    def test_empty_list(self) -> None:
        results = blocks_to_dicts([])
        assert results == []

    def test_mixed_success_and_failure(self) -> None:
        blocks = [
            _make_code_block('{"a": 1}', BlockType.JSON),
            _make_code_block("not json", BlockType.JSON),
        ]
        results = blocks_to_dicts(blocks)
        assert len(results) == 2
        assert results[0].data == {"a": 1}
        assert results[0].error is None
        assert results[1].data is None
        assert results[1].error is not None

    def test_returns_transform_result_instances(self) -> None:
        blocks = [_make_code_block('{"a": 1}', BlockType.JSON)]
        results = blocks_to_dicts(blocks)
        assert isinstance(results[0], TransformResult)


# ---------------------------------------------------------------------------
# Private helpers: _remove_trailing_commas
# ---------------------------------------------------------------------------


class TestRemoveTrailingCommas:
    """Tests for _remove_trailing_commas."""

    def test_trailing_comma_before_brace(self) -> None:
        assert _remove_trailing_commas('{"a": 1,}') == '{"a": 1}'

    def test_trailing_comma_before_bracket(self) -> None:
        assert _remove_trailing_commas("[1, 2,]") == "[1, 2]"

    def test_trailing_comma_with_whitespace(self) -> None:
        # Comma removed, whitespace preserved — still valid JSON
        result = _remove_trailing_commas('{"a": 1,  }')
        assert json.loads(result) == {"a": 1}
        assert "," not in result.split("1")[1].split("}")[0]

    def test_trailing_comma_with_newline(self) -> None:
        # Comma removed, newline preserved — still valid JSON
        result = _remove_trailing_commas('{"a": 1,\n}')
        assert json.loads(result) == {"a": 1}

    def test_no_trailing_comma_unchanged(self) -> None:
        original = '{"a": 1}'
        assert _remove_trailing_commas(original) == original

    def test_multiple_trailing_commas(self) -> None:
        result = _remove_trailing_commas('{"a": [1, 2,], "b": 3,}')
        assert result == '{"a": [1, 2], "b": 3}'

    def test_empty_string(self) -> None:
        assert _remove_trailing_commas("") == ""


# ---------------------------------------------------------------------------
# Private helpers: _single_to_double_quotes
# ---------------------------------------------------------------------------


class TestSingleToDoubleQuotes:
    """Tests for _single_to_double_quotes."""

    def test_basic_replacement(self) -> None:
        assert _single_to_double_quotes("{'a': 'b'}") == '{"a": "b"}'

    def test_already_double_quotes_unchanged(self) -> None:
        original = '{"a": "b"}'
        assert _single_to_double_quotes(original) == original

    def test_mixed_quotes(self) -> None:
        result = _single_to_double_quotes("""{'a': "b"}""")
        assert result == '{"a": "b"}'

    def test_empty_string(self) -> None:
        assert _single_to_double_quotes("") == ""

    def test_escaped_backslash_in_string(self) -> None:
        result = _single_to_double_quotes("{'a': 'b\\\\'}")
        # The escaped backslash should not affect quote handling
        assert '"a"' in result

    def test_nested_single_quotes(self) -> None:
        result = _single_to_double_quotes("{'key': 'value'}")
        assert result == '{"key": "value"}'

    def test_escaped_apostrophe_produces_valid_json(self) -> None:
        """Escaped apostrophe \\' in single-quoted string should become valid."""
        result = _single_to_double_quotes("{'key': 'it\\'s a test'}")
        # Should produce valid JSON (\\' replaced with just ')
        parsed = json.loads(result)
        assert parsed == {"key": "it's a test"}


# ---------------------------------------------------------------------------
# Private helpers: _quote_unquoted_keys
# ---------------------------------------------------------------------------


class TestQuoteUnquotedKeys:
    """Tests for _quote_unquoted_keys."""

    def test_basic_unquoted_key(self) -> None:
        result = _quote_unquoted_keys('{name: "Alice"}')
        assert '"name":' in result

    def test_multiple_unquoted_keys(self) -> None:
        result = _quote_unquoted_keys('{name: "Alice", age: 30}')
        assert '"name":' in result
        assert '"age":' in result

    def test_already_quoted_keys_unchanged(self) -> None:
        original = '{"name": "Alice"}'
        result = _quote_unquoted_keys(original)
        # Should still have exactly the quoted key
        assert '"name":' in result

    def test_underscore_key(self) -> None:
        result = _quote_unquoted_keys('{first_name: "Alice"}')
        assert '"first_name":' in result

    def test_key_with_digits(self) -> None:
        result = _quote_unquoted_keys('{item2: "val"}')
        assert '"item2":' in result

    def test_empty_string(self) -> None:
        assert _quote_unquoted_keys("") == ""

    def test_key_after_newline(self) -> None:
        content = '{\nname: "Alice",\nage: 30\n}'
        result = _quote_unquoted_keys(content)
        assert '"name":' in result
        assert '"age":' in result

    def test_does_not_corrupt_string_values_with_colon(self) -> None:
        """Values containing word:pattern inside strings must not be quoted."""
        content = '{"msg": "hello name: fake", "real": 1}'
        result = _quote_unquoted_keys(content)
        # The string value should be preserved unchanged
        assert json.loads(result) == {"msg": "hello name: fake", "real": 1}

    def test_does_not_corrupt_url_in_string(self) -> None:
        content = '{"url": "https://example.com"}'
        result = _quote_unquoted_keys(content)
        assert json.loads(result) == {"url": "https://example.com"}


# ---------------------------------------------------------------------------
# Private helpers: _recover_truncated_json
# ---------------------------------------------------------------------------


class TestRecoverTruncatedJson:
    """Tests for _recover_truncated_json."""

    def test_missing_closing_brace(self) -> None:
        result = _recover_truncated_json('{"a": 1')
        assert result.endswith("}")
        assert result.count("{") == result.count("}")

    def test_missing_closing_bracket(self) -> None:
        result = _recover_truncated_json("[1, 2, 3")
        assert result.endswith("]")

    def test_nested_missing_closers(self) -> None:
        result = _recover_truncated_json('{"users": [{"name": "Alice"')
        # Should close with }]}
        assert result.endswith("}]}")

    def test_already_balanced(self) -> None:
        original = '{"a": 1}'
        assert _recover_truncated_json(original) == original

    def test_truncated_after_comma(self) -> None:
        result = _recover_truncated_json('{"a": 1,')
        # Should strip trailing comma and close
        assert result.endswith("}")

    def test_truncated_after_colon(self) -> None:
        result = _recover_truncated_json('{"a":')
        # Should strip trailing colon and close
        assert result.endswith("}")

    def test_empty_string(self) -> None:
        assert _recover_truncated_json("") == ""

    def test_deeply_nested(self) -> None:
        content = '{"a": {"b": {"c": [1, 2'
        result = _recover_truncated_json(content)
        # 3 open braces + 1 open bracket → closes as ]}}}
        import json

        parsed = json.loads(result)
        assert parsed == {"a": {"b": {"c": [1, 2]}}}

    def test_truncated_inside_string_value(self) -> None:
        # Truncated in the middle of a string value
        result = _recover_truncated_json('{"name": "Ali')
        # Should close the string and the object
        assert result.endswith('"}')
