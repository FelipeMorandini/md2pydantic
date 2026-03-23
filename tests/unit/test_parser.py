"""Unit tests for the Scanner (parser.py) — Issue #2.

Covers fenced code block extraction, unfenced inline JSON detection,
language hint inference, LLM quirk handling, and edge cases.
"""

from __future__ import annotations

import textwrap

import pytest

from md2pydantic.models import BlockType, CodeBlock
from md2pydantic.parser import scan_blocks

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _single(blocks: list[CodeBlock]) -> CodeBlock:
    """Assert exactly one block was returned and return it."""
    assert len(blocks) == 1, f"Expected 1 block, got {len(blocks)}"
    return blocks[0]


# ---------------------------------------------------------------------------
# Fenced blocks with language hints
# ---------------------------------------------------------------------------


class TestFencedJsonBlock:
    """Standard ```json fenced code blocks."""

    def test_basic_json_block(self) -> None:
        md = textwrap.dedent("""\
            ```json
            {"name": "Alice", "age": 30}
            ```
        """)
        block = _single(scan_blocks(md))
        assert block.block_type == BlockType.JSON
        assert block.fenced is True
        assert '"name": "Alice"' in block.content

    def test_multiline_json_block(self) -> None:
        md = textwrap.dedent("""\
            ```json
            {
              "key": "value",
              "number": 42
            }
            ```
        """)
        block = _single(scan_blocks(md))
        assert block.block_type == BlockType.JSON
        assert '"key": "value"' in block.content
        assert '"number": 42' in block.content


class TestFencedYamlBlock:
    """Standard ```yaml and ```yml fenced code blocks."""

    def test_yaml_hint(self) -> None:
        md = textwrap.dedent("""\
            ```yaml
            name: Alice
            age: 30
            ```
        """)
        block = _single(scan_blocks(md))
        assert block.block_type == BlockType.YAML
        assert block.fenced is True
        assert "name: Alice" in block.content

    def test_yml_hint(self) -> None:
        md = textwrap.dedent("""\
            ```yml
            items:
              - one
              - two
            ```
        """)
        block = _single(scan_blocks(md))
        assert block.block_type == BlockType.YAML


class TestMixedCaseHints:
    """Language hints with non-lowercase casing."""

    @pytest.mark.parametrize("hint", ["JSON", "Json", "jSoN"])
    def test_json_mixed_case(self, hint: str) -> None:
        md = f"```{hint}\n" '{"key": "value"}\n' "```\n"
        block = _single(scan_blocks(md))
        assert block.block_type == BlockType.JSON

    @pytest.mark.parametrize("hint", ["YAML", "Yaml", "YML", "Yml"])
    def test_yaml_mixed_case(self, hint: str) -> None:
        md = f"```{hint}\n" "name: test\n" "```\n"
        block = _single(scan_blocks(md))
        assert block.block_type == BlockType.YAML


class TestExtraBackticks:
    """Fences with more than three backticks."""

    def test_four_backticks(self) -> None:
        md = "````json\n" '{"a": 1}\n' "````\n"
        block = _single(scan_blocks(md))
        assert block.block_type == BlockType.JSON

    def test_five_backticks(self) -> None:
        md = "`````json\n" '{"a": 1}\n' "`````\n"
        block = _single(scan_blocks(md))
        assert block.block_type == BlockType.JSON


class TestTrailingTextAfterFence:
    """Trailing prose after the closing fence should not break extraction."""

    def test_trailing_text_after_closing_fence(self) -> None:
        md = textwrap.dedent("""\
            ```json
            {"key": "value"}
            ``` some trailing text here
        """)
        block = _single(scan_blocks(md))
        assert block.block_type == BlockType.JSON
        assert '"key": "value"' in block.content
        assert "trailing" not in block.content


class TestLeadingTrailingBlankLines:
    """Blank lines inside a fenced block should be stripped from content."""

    def test_leading_blank_lines_stripped(self) -> None:
        md = "```json\n\n\n" '{"a": 1}\n' "```\n"
        block = _single(scan_blocks(md))
        assert block.content.startswith("{")

    def test_trailing_blank_lines_stripped(self) -> None:
        md = "```json\n" '{"a": 1}\n\n\n' "```\n"
        block = _single(scan_blocks(md))
        assert block.content.endswith("}")


class TestMultipleFencedBlocks:
    """Multiple fenced blocks in one document."""

    def test_two_json_blocks(self) -> None:
        md = textwrap.dedent("""\
            ```json
            {"first": 1}
            ```

            Some prose in between.

            ```json
            {"second": 2}
            ```
        """)
        blocks = scan_blocks(md)
        assert len(blocks) == 2
        assert '"first"' in blocks[0].content
        assert '"second"' in blocks[1].content

    def test_json_and_yaml_blocks(self) -> None:
        md = textwrap.dedent("""\
            ```json
            {"a": 1}
            ```

            ```yaml
            b: 2
            ```
        """)
        blocks = scan_blocks(md)
        assert len(blocks) == 2
        assert blocks[0].block_type == BlockType.JSON
        assert blocks[1].block_type == BlockType.YAML


# ---------------------------------------------------------------------------
# Fenced blocks without language hints (type inference)
# ---------------------------------------------------------------------------


class TestFencedNoHintInference:
    """Fenced blocks with no language hint — type should be inferred."""

    def test_infer_json_from_content(self) -> None:
        md = "```\n" '{"inferred": true}\n' "```\n"
        block = _single(scan_blocks(md))
        assert block.block_type == BlockType.JSON
        assert block.fenced is True

    def test_infer_yaml_from_content(self) -> None:
        md = "```\n" "name: inferred\n" "status: ok\n" "```\n"
        block = _single(scan_blocks(md))
        assert block.block_type == BlockType.YAML
        assert block.fenced is True


# ---------------------------------------------------------------------------
# Unfenced inline JSON
# ---------------------------------------------------------------------------


class TestUnfencedInlineJson:
    """Inline JSON objects and arrays found outside fenced blocks."""

    def test_simple_inline_object(self) -> None:
        md = 'Here is some data: {"key": "value"} and then more prose.'
        block = _single(scan_blocks(md))
        assert block.block_type == BlockType.JSON
        assert block.fenced is False
        assert '"key": "value"' in block.content

    def test_nested_objects(self) -> None:
        md = 'Nested: {"a": {"b": 1}} end.'
        block = _single(scan_blocks(md))
        assert block.block_type == BlockType.JSON
        assert '{"b": 1}' in block.content

    def test_json_with_braces_in_strings(self) -> None:
        md = 'Data: {"text": "use {braces} here"} done.'
        block = _single(scan_blocks(md))
        assert block.block_type == BlockType.JSON
        assert "{braces}" in block.content

    def test_json_array_inline(self) -> None:
        md = 'Array: [{"key": "value"}] end.'
        block = _single(scan_blocks(md))
        assert block.block_type == BlockType.JSON
        assert block.fenced is False

    def test_multiple_inline_objects(self) -> None:
        md = 'First: {"a": 1} middle text {"b": 2} end.'
        blocks = scan_blocks(md)
        assert len(blocks) == 2
        assert blocks[0].block_type == BlockType.JSON
        assert blocks[1].block_type == BlockType.JSON


# ---------------------------------------------------------------------------
# LLM quirks
# ---------------------------------------------------------------------------


class TestLlmQuirks:
    """Common LLM output quirks the scanner should handle."""

    def test_trailing_text_after_closing_fence(self) -> None:
        md = textwrap.dedent("""\
            ```json
            {"key": "value"}
            ``` Here is an explanation of the output.
        """)
        block = _single(scan_blocks(md))
        assert block.block_type == BlockType.JSON
        assert "explanation" not in block.content

    def test_extra_backticks_on_fences(self) -> None:
        md = "````json\n" '{"key": "value"}\n' "````\n"
        block = _single(scan_blocks(md))
        assert block.block_type == BlockType.JSON

    def test_unclosed_fenced_block_with_json_hint(self) -> None:
        md = textwrap.dedent("""\
            ```json
            {"key": "value"}
        """)
        block = _single(scan_blocks(md))
        assert block.block_type == BlockType.JSON
        assert '"key": "value"' in block.content

    def test_unclosed_fenced_block_with_yaml_hint(self) -> None:
        md = textwrap.dedent("""\
            ```yaml
            name: Alice
            age: 30
        """)
        block = _single(scan_blocks(md))
        assert block.block_type == BlockType.YAML
        assert "name: Alice" in block.content

    def test_empty_fenced_block_filtered_out(self) -> None:
        md = "```json\n\n```\n"
        blocks = scan_blocks(md)
        assert len(blocks) == 0

    def test_whitespace_only_fenced_block_filtered_out(self) -> None:
        md = "```json\n   \n\n```\n"
        blocks = scan_blocks(md)
        assert len(blocks) == 0


# ---------------------------------------------------------------------------
# Overlap and ordering
# ---------------------------------------------------------------------------


class TestOverlapAndOrdering:
    """Fenced JSON should not be double-extracted as inline; order is preserved."""

    def test_no_double_extraction(self) -> None:
        md = textwrap.dedent("""\
            ```json
            {"inside": "fence"}
            ```
        """)
        blocks = scan_blocks(md)
        assert len(blocks) == 1
        assert blocks[0].fenced is True

    def test_fenced_and_inline_no_double(self) -> None:
        md = textwrap.dedent("""\
            ```json
            {"fenced": true}
            ```

            Also here: {"inline": true}
        """)
        blocks = scan_blocks(md)
        assert len(blocks) == 2
        assert blocks[0].fenced is True
        assert blocks[1].fenced is False

    def test_blocks_returned_in_source_order(self) -> None:
        md = textwrap.dedent("""\
            ```yaml
            first: 1
            ```

            {"second": 2}

            ```json
            {"third": 3}
            ```
        """)
        blocks = scan_blocks(md)
        assert len(blocks) == 3
        assert blocks[0].block_type == BlockType.YAML
        assert blocks[1].block_type == BlockType.JSON
        assert blocks[1].fenced is False
        assert blocks[2].block_type == BlockType.JSON
        assert blocks[2].fenced is True

    def test_start_line_increases_monotonically(self) -> None:
        md = textwrap.dedent("""\
            ```json
            {"a": 1}
            ```

            {"b": 2}

            ```yaml
            c: 3
            ```
        """)
        blocks = scan_blocks(md)
        for i in range(1, len(blocks)):
            assert blocks[i].start_line > blocks[i - 1].start_line


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge conditions: line endings, ignored languages, empty input."""

    def test_windows_line_endings(self) -> None:
        md = "```json\r\n{\"key\": \"value\"}\r\n```\r\n"
        block = _single(scan_blocks(md))
        assert block.block_type == BlockType.JSON
        assert '"key": "value"' in block.content

    def test_python_fenced_block_ignored(self) -> None:
        md = textwrap.dedent("""\
            ```python
            print("hello")
            ```
        """)
        blocks = scan_blocks(md)
        assert len(blocks) == 0

    @pytest.mark.parametrize("lang", ["python", "go", "rust", "bash", "sql", "html"])
    def test_non_json_yaml_language_ignored(self, lang: str) -> None:
        md = f"```{lang}\n" "some code\n" "```\n"
        blocks = scan_blocks(md)
        assert len(blocks) == 0

    def test_empty_input(self) -> None:
        blocks = scan_blocks("")
        assert blocks == []

    def test_no_blocks_in_plain_prose(self) -> None:
        md = "This is just plain text with no structured data at all."
        blocks = scan_blocks(md)
        assert blocks == []

    def test_only_whitespace_input(self) -> None:
        blocks = scan_blocks("   \n\n  \n")
        assert blocks == []

    def test_backslash_before_brace_in_prose(self) -> None:
        """A backslash before { in prose should not prevent detection."""
        md = r'Text \{"key": "value"} end.'
        blocks = scan_blocks(md)
        assert len(blocks) == 1
        assert blocks[0].block_type == BlockType.JSON

    def test_markdown_link_not_detected_as_json(self) -> None:
        """Markdown links [text](url) should not be detected as JSON arrays."""
        md = "Check [this link](https://example.com) for details."
        blocks = scan_blocks(md)
        assert blocks == []

    def test_markdown_link_with_json_start_chars(self) -> None:
        """Markdown links starting with t/f/n should not match."""
        md = "See [the docs](https://example.com) and [notes](url)."
        blocks = scan_blocks(md)
        assert blocks == []

    def test_indented_fenced_block(self) -> None:
        """CommonMark allows up to 3 spaces of indentation before fences."""
        md = "   ```json\n   {\"key\": \"value\"}\n   ```\n"
        block = _single(scan_blocks(md))
        assert block.block_type == BlockType.JSON

    def test_space_between_fence_and_hint(self) -> None:
        """Space between backticks and language hint should be accepted."""
        md = "``` json\n{\"key\": \"value\"}\n```\n"
        block = _single(scan_blocks(md))
        assert block.block_type == BlockType.JSON
