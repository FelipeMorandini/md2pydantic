"""Integration tests for the scanner with realistic LLM output samples.

These tests exercise the full scan_blocks pipeline against messy Markdown
strings that real LLMs (ChatGPT, Claude, etc.) commonly produce.
"""

from __future__ import annotations

from md2pydantic.models import BlockType
from md2pydantic.parser import scan_blocks


class TestChatGPTStyleJsonInBackticks:
    """ChatGPT-style response with JSON inside fenced backticks."""

    MARKDOWN = (
        "Here's the data you requested:\n"
        "\n"
        "```json\n"
        '{"name": "Alice", "age": 30}\n'
        "```\n"
        "\n"
        "I hope this helps!"
    )

    def test_extracts_single_block(self) -> None:
        blocks = scan_blocks(self.MARKDOWN)
        assert len(blocks) == 1

    def test_block_type_is_json(self) -> None:
        blocks = scan_blocks(self.MARKDOWN)
        assert blocks[0].block_type == BlockType.JSON

    def test_block_is_fenced(self) -> None:
        blocks = scan_blocks(self.MARKDOWN)
        assert blocks[0].fenced is True

    def test_content_is_valid_json_string(self) -> None:
        import json

        blocks = scan_blocks(self.MARKDOWN)
        parsed = json.loads(blocks[0].content)
        assert parsed == {"name": "Alice", "age": 30}

    def test_surrounding_prose_not_included(self) -> None:
        blocks = scan_blocks(self.MARKDOWN)
        assert "Here's" not in blocks[0].content
        assert "hope" not in blocks[0].content


class TestMultipleCodeBlocksJsonAndYaml:
    """LLM response containing both a JSON and a YAML fenced block."""

    MARKDOWN = (
        "# Results\n"
        "\n"
        "Here is the JSON output:\n"
        "\n"
        "```json\n"
        '{"id": 1, "status": "active"}\n'
        "```\n"
        "\n"
        "And here is the YAML configuration:\n"
        "\n"
        "```yaml\n"
        "database:\n"
        "  host: localhost\n"
        "  port: 5432\n"
        "```\n"
        "\n"
        "Let me know if you need anything else."
    )

    def test_extracts_two_blocks(self) -> None:
        blocks = scan_blocks(self.MARKDOWN)
        assert len(blocks) == 2

    def test_first_block_is_json(self) -> None:
        blocks = scan_blocks(self.MARKDOWN)
        assert blocks[0].block_type == BlockType.JSON

    def test_second_block_is_yaml(self) -> None:
        blocks = scan_blocks(self.MARKDOWN)
        assert blocks[1].block_type == BlockType.YAML

    def test_json_content_parseable(self) -> None:
        import json

        blocks = scan_blocks(self.MARKDOWN)
        parsed = json.loads(blocks[0].content)
        assert parsed["id"] == 1
        assert parsed["status"] == "active"

    def test_yaml_content_preserved(self) -> None:
        blocks = scan_blocks(self.MARKDOWN)
        assert "host: localhost" in blocks[1].content
        assert "port: 5432" in blocks[1].content

    def test_blocks_ordered_by_position(self) -> None:
        blocks = scan_blocks(self.MARKDOWN)
        assert blocks[0].start_line < blocks[1].start_line


class TestTrailingTextAfterClosingFence:
    """LLM response where trailing text appears after the closing fence."""

    MARKDOWN = '```json\n{"key": "value"}\n``` (end of response)\n'

    def test_extracts_one_block(self) -> None:
        blocks = scan_blocks(self.MARKDOWN)
        assert len(blocks) == 1

    def test_content_is_clean_json(self) -> None:
        import json

        blocks = scan_blocks(self.MARKDOWN)
        parsed = json.loads(blocks[0].content)
        assert parsed == {"key": "value"}

    def test_trailing_text_not_in_content(self) -> None:
        blocks = scan_blocks(self.MARKDOWN)
        assert "end of response" not in blocks[0].content

    def test_block_is_fenced(self) -> None:
        blocks = scan_blocks(self.MARKDOWN)
        assert blocks[0].fenced is True


class TestInlineJsonEmbeddedInProse:
    """LLM response with JSON object embedded directly in prose (no fences)."""

    MARKDOWN = 'The result is {"name": "Bob", "active": true} as expected.'

    def test_extracts_inline_json(self) -> None:
        blocks = scan_blocks(self.MARKDOWN)
        assert len(blocks) == 1

    def test_block_type_is_json(self) -> None:
        blocks = scan_blocks(self.MARKDOWN)
        assert blocks[0].block_type == BlockType.JSON

    def test_block_is_not_fenced(self) -> None:
        blocks = scan_blocks(self.MARKDOWN)
        assert blocks[0].fenced is False

    def test_content_is_valid_json(self) -> None:
        import json

        blocks = scan_blocks(self.MARKDOWN)
        parsed = json.loads(blocks[0].content)
        assert parsed == {"name": "Bob", "active": True}


class TestExtraBackticks:
    """LLM response using four backticks instead of three."""

    MARKDOWN = '````json\n{"tool": "md2pydantic", "version": "0.1.0"}\n````\n'

    def test_extracts_block_with_extra_backticks(self) -> None:
        blocks = scan_blocks(self.MARKDOWN)
        assert len(blocks) == 1

    def test_block_type_is_json(self) -> None:
        blocks = scan_blocks(self.MARKDOWN)
        assert blocks[0].block_type == BlockType.JSON

    def test_content_is_valid_json(self) -> None:
        import json

        blocks = scan_blocks(self.MARKDOWN)
        parsed = json.loads(blocks[0].content)
        assert parsed["tool"] == "md2pydantic"
        assert parsed["version"] == "0.1.0"

    def test_block_is_fenced(self) -> None:
        blocks = scan_blocks(self.MARKDOWN)
        assert blocks[0].fenced is True


class TestComplexNestedJson:
    """LLM response with a large nested JSON containing arrays and objects."""

    MARKDOWN = (
        "Here is the full user record:\n"
        "\n"
        "```json\n"
        "{\n"
        '  "user": {\n'
        '    "id": 42,\n'
        '    "name": "Charlie",\n'
        '    "email": "charlie@example.com",\n'
        '    "roles": ["admin", "editor"],\n'
        '    "preferences": {\n'
        '      "theme": "dark",\n'
        '      "notifications": {\n'
        '        "email": true,\n'
        '        "sms": false\n'
        "      }\n"
        "    },\n"
        '    "addresses": [\n'
        "      {\n"
        '        "type": "home",\n'
        '        "city": "Springfield",\n'
        '        "zip": "62704"\n'
        "      },\n"
        "      {\n"
        '        "type": "work",\n'
        '        "city": "Shelbyville",\n'
        '        "zip": "62565"\n'
        "      }\n"
        "    ]\n"
        "  }\n"
        "}\n"
        "```\n"
        "\n"
        "This contains all the nested data."
    )

    def test_extracts_single_block(self) -> None:
        blocks = scan_blocks(self.MARKDOWN)
        assert len(blocks) == 1

    def test_content_parses_to_nested_structure(self) -> None:
        import json

        blocks = scan_blocks(self.MARKDOWN)
        parsed = json.loads(blocks[0].content)
        user = parsed["user"]
        assert user["id"] == 42
        assert user["name"] == "Charlie"
        assert "admin" in user["roles"]
        assert user["preferences"]["notifications"]["email"] is True
        assert len(user["addresses"]) == 2
        assert user["addresses"][1]["city"] == "Shelbyville"

    def test_block_type_is_json(self) -> None:
        blocks = scan_blocks(self.MARKDOWN)
        assert blocks[0].block_type == BlockType.JSON


class TestMixedProseAndMultipleJsonBlocks:
    """Document with prose, multiple JSON blocks, and other content."""

    MARKDOWN = (
        "# API Response Summary\n"
        "\n"
        "The first endpoint returned:\n"
        "\n"
        "```json\n"
        '{"endpoint": "/users", "count": 3}\n'
        "```\n"
        "\n"
        "Meanwhile, the second endpoint had this output:\n"
        "\n"
        "```json\n"
        '{"endpoint": "/orders", "count": 15, "status": "ok"}\n'
        "```\n"
        "\n"
        "Both endpoints are stable and returning correct data.\n"
        "\n"
        "Note: the error rate was only 0.01% across both.\n"
    )

    def test_extracts_two_json_blocks(self) -> None:
        blocks = scan_blocks(self.MARKDOWN)
        assert len(blocks) == 2

    def test_both_blocks_are_json(self) -> None:
        blocks = scan_blocks(self.MARKDOWN)
        assert all(b.block_type == BlockType.JSON for b in blocks)

    def test_first_block_content(self) -> None:
        import json

        blocks = scan_blocks(self.MARKDOWN)
        parsed = json.loads(blocks[0].content)
        assert parsed["endpoint"] == "/users"

    def test_second_block_content(self) -> None:
        import json

        blocks = scan_blocks(self.MARKDOWN)
        parsed = json.loads(blocks[1].content)
        assert parsed["endpoint"] == "/orders"
        assert parsed["count"] == 15

    def test_prose_not_in_any_block(self) -> None:
        blocks = scan_blocks(self.MARKDOWN)
        for block in blocks:
            assert "stable" not in block.content
            assert "error rate" not in block.content


class TestYmlLanguageHint:
    """YAML block using 'yml' hint instead of 'yaml'."""

    MARKDOWN = "```yml\nname: test\nversion: 1\n```\n"

    def test_extracts_yaml_block(self) -> None:
        blocks = scan_blocks(self.MARKDOWN)
        assert len(blocks) == 1
        assert blocks[0].block_type == BlockType.YAML


class TestUnfencedJsonArray:
    """Inline JSON array embedded in prose.

    The scanner extracts the whole array as a single block.
    """

    MARKDOWN = 'The items are [{"id": 1}, {"id": 2}] in the list.'

    def test_extracts_array_as_single_block(self) -> None:
        blocks = scan_blocks(self.MARKDOWN)
        assert len(blocks) == 1

    def test_block_is_json(self) -> None:
        blocks = scan_blocks(self.MARKDOWN)
        assert blocks[0].block_type == BlockType.JSON

    def test_array_is_parseable(self) -> None:
        import json

        blocks = scan_blocks(self.MARKDOWN)
        parsed = json.loads(blocks[0].content)
        ids = sorted(item["id"] for item in parsed)
        assert ids == [1, 2]


class TestEmptyCodeBlockSkipped:
    """A fenced block with only whitespace content should be filtered out."""

    MARKDOWN = "```json\n\n```\n"

    def test_empty_block_filtered_out(self) -> None:
        blocks = scan_blocks(self.MARKDOWN)
        assert len(blocks) == 0


class TestNonJsonCodeBlockIgnored:
    """Python code block should be ignored by the scanner."""

    MARKDOWN = "```python\nprint('hello')\n```\n"

    def test_no_blocks_extracted(self) -> None:
        blocks = scan_blocks(self.MARKDOWN)
        assert len(blocks) == 0


class TestUnclosedFencedBlock:
    """LLM response where the closing fence is missing entirely."""

    MARKDOWN = (
        "Here is the data:\n"
        "\n"
        "```json\n"
        '{"incomplete": true, "reason": "LLM stopped early"}\n'
    )

    def test_extracts_block_from_unclosed_fence(self) -> None:
        blocks = scan_blocks(self.MARKDOWN)
        assert len(blocks) == 1

    def test_content_is_parseable_json(self) -> None:
        import json

        blocks = scan_blocks(self.MARKDOWN)
        parsed = json.loads(blocks[0].content)
        assert parsed["incomplete"] is True


class TestLineNumbersAreReasonable:
    """Verify that start_line and end_line reflect document position."""

    MARKDOWN = 'Line zero\nLine one\n```json\n{"a": 1}\n```\nLine five\n'

    def test_start_line_after_preamble(self) -> None:
        blocks = scan_blocks(self.MARKDOWN)
        assert len(blocks) == 1
        # The fence starts at line 2 (0-indexed)
        assert blocks[0].start_line == 2

    def test_end_line_at_or_after_closing_fence(self) -> None:
        blocks = scan_blocks(self.MARKDOWN)
        # Closing fence is at line 4
        assert blocks[0].end_line >= 4
