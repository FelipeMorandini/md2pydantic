"""Tests for the hardening batch fixes (#19, #20, #21, #23, #24, #28).

Each section covers a specific fix. Integration tests at the bottom exercise
multiple fixes together through realistic LLM output scenarios.
"""

from __future__ import annotations

from pydantic import BaseModel

from md2pydantic.converter import MDConverter
from md2pydantic.models import BlockType, CodeBlock
from md2pydantic.parser import (
    _infer_block_type,
    _parse_table_row,
    scan_blocks,
    scan_tables,
)
from md2pydantic.transformers import _recover_truncated_json, json_block_to_dict

# =====================================================================
# #19 — Unfenced false positive reduction
# =====================================================================


class TestUnfencedFalsePositiveReduction:
    """Brace pairs without \" or : inside should NOT be extracted as JSON."""

    def test_template_placeholder_not_extracted(self):
        """'{name}' in prose has no \" or : -> skip."""
        md = "Hello {name}, welcome!"
        blocks = scan_blocks(md)
        assert len(blocks) == 0

    def test_set_notation_not_extracted(self):
        """'{x, y, z}' in prose has no \" or : -> skip."""
        md = "The set {x, y, z} is finite."
        blocks = scan_blocks(md)
        assert len(blocks) == 0

    def test_json_object_with_quotes_still_extracted(self):
        """'{"key": "value"}' has \" inside -> extracted."""
        md = 'Here is some data: {"key": "value"}'
        blocks = scan_blocks(md)
        assert len(blocks) == 1
        assert blocks[0].block_type == BlockType.JSON

    def test_yaml_like_braces_with_colon_still_extracted(self):
        """'{key: value}' has : inside -> extracted."""
        md = "Config is {key: value}"
        blocks = scan_blocks(md)
        assert len(blocks) == 1


# =====================================================================
# #20 — YAML inference improvement
# =====================================================================


class TestYamlInferenceImprovement:
    """Hint-less fenced blocks should not misidentify URLs or CSS as YAML."""

    def test_url_not_detected_as_yaml(self):
        """Block with 'https://example.com' contains :// -> NOT YAML."""
        md = "```\nhttps://example.com\n```"
        blocks = scan_blocks(md)
        # Should not be detected as YAML (or anything useful)
        yaml_blocks = [b for b in blocks if b.block_type == BlockType.YAML]
        assert len(yaml_blocks) == 0

    def test_css_no_space_after_colon_not_yaml(self):
        """'display:flex' has no space after colon -> NOT YAML."""
        result = _infer_block_type("display:flex")
        assert result == BlockType.UNKNOWN

    def test_proper_yaml_still_detected(self):
        """'name: Alice' (space after colon) -> detected as YAML."""
        md = "```\nname: Alice\n```"
        blocks = scan_blocks(md)
        yaml_blocks = [b for b in blocks if b.block_type == BlockType.YAML]
        assert len(yaml_blocks) == 1

    def test_yaml_with_url_value_not_detected(self):
        """Block with 'key: value\\nurl: https://x.com' has :// -> NOT YAML."""
        content = "key: value\nurl: https://x.com"
        result = _infer_block_type(content)
        assert result == BlockType.UNKNOWN


# =====================================================================
# #21 — Unclosed fence trailing fence stripping
# =====================================================================


class TestUnclosedFenceTrailingFenceStripping:
    """Shorter fences inside unclosed blocks should be stripped."""

    def test_four_backtick_with_three_backtick_close(self):
        """4-backtick fence with 3-backtick close strips the shorter fence."""
        md = '````json\n{"a": 1}\n```'
        blocks = scan_blocks(md)
        assert len(blocks) == 1
        assert "```" not in blocks[0].content
        assert '"a": 1' in blocks[0].content

    def test_regular_unclosed_three_backtick(self):
        """Regular unclosed 3-backtick fence: content unchanged."""
        md = '```json\n{"b": 2}'
        blocks = scan_blocks(md)
        assert len(blocks) == 1
        assert '"b": 2' in blocks[0].content


# =====================================================================
# #23 — Double-backslash-before-pipe
# =====================================================================


class TestDoubleBackslashBeforePipe:
    """Table row parsing with escaped backslashes and pipes."""

    def test_double_backslash_pipe_three_cells(self):
        r"""'| a \\| b | c |' -> 3 cells: 'a \', 'b', 'c'."""
        cells = _parse_table_row("| a \\\\| b | c |")
        assert cells == ["a \\", "b", "c"]

    def test_single_backslash_pipe_escapes(self):
        r"""'| a \| b | c |' -> 2 cells: 'a | b', 'c'."""
        cells = _parse_table_row("| a \\| b | c |")
        assert cells == ["a | b", "c"]

    def test_normal_row_no_backslashes(self):
        """'| a | b |' -> 2 cells: 'a', 'b'."""
        cells = _parse_table_row("| a | b |")
        assert cells == ["a", "b"]


# =====================================================================
# #24 — Tilde fence support
# =====================================================================


class TestTildeFenceSupport:
    """Tilde-fenced code blocks should be extracted like backtick fences."""

    def test_tilde_json_block(self):
        """~~~json ... ~~~ -> extracted as JSON."""
        md = '~~~json\n{"a": 1}\n~~~'
        blocks = scan_blocks(md)
        assert len(blocks) == 1
        assert blocks[0].block_type == BlockType.JSON
        assert blocks[0].fenced is True

    def test_tilde_yaml_block(self):
        """~~~yaml ... ~~~ -> extracted as YAML."""
        md = "~~~yaml\nkey: val\n~~~"
        blocks = scan_blocks(md)
        assert len(blocks) == 1
        assert blocks[0].block_type == BlockType.YAML

    def test_mixed_backtick_and_tilde(self):
        """Both backtick and tilde fences in same doc -> both extracted."""
        md = '```json\n{"a": 1}\n```\n\n~~~json\n{"b": 2}\n~~~'
        blocks = scan_blocks(md)
        assert len(blocks) == 2
        assert blocks[0].block_type == BlockType.JSON
        assert blocks[1].block_type == BlockType.JSON

    def test_tilde_inside_backtick_not_double_extracted(self):
        """Tilde inside backtick: claimed span prevents double extraction."""
        md = '```\n~~~json\n{"a": 1}\n~~~\n```'
        blocks = scan_blocks(md)
        # Outer backtick fence claims span; inner tilde not extracted.
        # No lang hint + ~~~ content = not JSON/YAML.
        json_blocks = [b for b in blocks if b.block_type == BlockType.JSON]
        assert len(json_blocks) == 0

    def test_table_inside_tilde_fence_not_detected(self):
        """Table inside tilde fence -> NOT detected by scan_tables."""
        md = "~~~\n| a | b |\n| - | - |\n| 1 | 2 |\n~~~"
        tables = scan_tables(md)
        assert len(tables) == 0


# =====================================================================
# #28 — Truncated JSON backslash recovery
# =====================================================================


class TestTruncatedJsonBackslashRecovery:
    """Truncated JSON ending with backslash should be recovered."""

    def test_trailing_backslash_in_string(self):
        r"""Truncated JSON string ending with backslash is recovered."""
        # The JSON string value ends with a literal backslash
        recovered = _recover_truncated_json('{"key": "val\\')
        import json
        data = json.loads(recovered)
        assert data["key"] == "val\\"

    def test_normal_truncated_string_still_works(self):
        """'{"key": "value' -> recovered normally (no trailing backslash)."""
        recovered = _recover_truncated_json('{"key": "value')
        import json
        data = json.loads(recovered)
        assert data["key"] == "value"

    def test_backslash_recovery_via_transformer(self):
        r"""Full pipeline: json_block_to_dict handles trailing backslash."""
        block = CodeBlock(
            content='{"key": "val\\',
            block_type=BlockType.JSON,
            fenced=True,
            start_line=0,
            end_line=0,
        )
        result = json_block_to_dict(block)
        assert result.data is not None
        assert "key" in result.data


# =====================================================================
# Integration tests — realistic LLM output exercising multiple fixes
# =====================================================================


class Item(BaseModel):
    name: str
    value: int


class Config(BaseModel):
    host: str
    port: int


class TestIntegrationMultipleFixesTogether:
    """Realistic LLM outputs that exercise several hardening fixes at once."""

    def test_llm_output_with_prose_braces_and_tilde_fence(self):
        """LLM output with template placeholders (#19) and tilde fence (#24).

        The {name} and {items} in prose should be ignored, while the tilde-fenced
        JSON block should be extracted.
        """
        md = (
            "Here is the config for {service_name}:\n\n"
            "The set of fields is {host, port}.\n\n"
            '~~~json\n{"host": "localhost", "port": 8080}\n~~~\n\n'
            "That should work!"
        )
        result = MDConverter(Config).parse_json(md)
        assert result.host == "localhost"
        assert result.port == 8080

    def test_llm_truncated_json_with_backslash_in_unclosed_four_backtick(self):
        """4-backtick unclosed fence (#21) + truncated JSON backslash (#28).

        The 4-backtick fence is unclosed, contains truncated JSON with a trailing
        backslash. The shorter ``` at the end should be stripped (#21), and the
        JSON should be recovered (#28).
        """
        md = (
            "Here is the file path:\n\n"
            '````json\n{"key": "val\\\n```'
        )
        blocks = scan_blocks(md)
        assert len(blocks) == 1
        # The ``` line should have been stripped from content
        assert "```" not in blocks[0].content
        # The transformer should recover the truncated JSON
        result = json_block_to_dict(blocks[0])
        assert result.data is not None
        assert "key" in result.data

    def test_llm_mixed_fences_table_and_false_positives(self):
        """Mixed fences, table with escaped pipes, prose braces.

        Exercises #19, #20, #23, #24 together.
        """
        md = (
            "The variables are {x, y}.\n\n"
            "## Data\n\n"
            '```json\n[{"name": "alpha", "value": 1}]\n```\n\n'
            "## Config\n\n"
            "~~~yaml\nhost: localhost\nport: 3000\n~~~\n\n"
            "## Table\n\n"
            "| name | value |\n"
            "| --- | --- |\n"
            "| beta | 2 |\n"
            "| ga\\\\|mma | 3 |\n"
        )
        # Prose braces {x, y} should not be extracted (#19)
        blocks = scan_blocks(md)
        json_blocks = [b for b in blocks if b.block_type == BlockType.JSON]
        yaml_blocks = [b for b in blocks if b.block_type == BlockType.YAML]
        assert len(json_blocks) == 1
        assert len(yaml_blocks) == 1

        # Table with escaped pipes (#23)
        tables = scan_tables(md)
        assert len(tables) == 1
        # Row with \\| should split into 'ga\' and 'mma' as separate cells
        row_with_escape = tables[0].rows[1]
        assert row_with_escape[0] == "ga\\"
        # 'mma' ends up either as second cell value or merged — verify 3 cells parsed
        cells = _parse_table_row("| ga\\\\|mma | 3 |")
        assert cells == ["ga\\", "mma", "3"]
