"""Transformer module.

Converts raw extracted formats into Python dictionaries and
(optionally) pandas DataFrames.
"""

from __future__ import annotations

import json
import re
from typing import Any

from md2pydantic.models import BlockType, CodeBlock, TableBlock, TransformResult


def table_to_dicts(table: TableBlock) -> list[dict[str, str | None]]:
    """Convert a TableBlock into a list of dictionaries.

    Each row becomes a dictionary mapping header names to cell values.
    Empty cells are mapped to None.

    Args:
        table: A TableBlock extracted by scan_tables.

    Returns:
        List of dictionaries, one per data row.
    """
    headers = table.headers
    result: list[dict[str, str | None]] = []
    for row in table.rows:
        record: dict[str, str | None] = {}
        for key, value in zip(headers, row, strict=False):
            record[key] = value if value != "" else None
        result.append(record)
    return result


def tables_to_dicts(
    tables: list[TableBlock],
) -> list[list[dict[str, str | None]]]:
    """Convert multiple TableBlocks into lists of dictionaries.

    Args:
        tables: List of TableBlock instances from scan_tables.

    Returns:
        List of lists, one inner list per table.
    """
    return [table_to_dicts(t) for t in tables]


def table_to_dataframe(table: TableBlock) -> Any:
    """Convert a TableBlock into a pandas DataFrame.

    Requires pandas to be installed. Install with:
        pip install md2pydantic[pandas]

    Args:
        table: A TableBlock extracted by scan_tables.

    Returns:
        A pandas DataFrame with headers as column names.

    Raises:
        ImportError: If pandas is not installed.
    """
    try:
        import pandas as _pd  # type: ignore[import-untyped]
    except ImportError:
        raise ImportError(
            "pandas is required for table_to_dataframe. "
            "Install it with: pip install md2pydantic[pandas]"
        ) from None

    rows = [[value if value != "" else None for value in row] for row in table.rows]
    return _pd.DataFrame(data=rows, columns=list(table.headers))


# ---------------------------------------------------------------------------
# JSON / YAML block transformers
# ---------------------------------------------------------------------------


def json_block_to_dict(block: CodeBlock) -> TransformResult:
    """Parse a JSON CodeBlock into a Python data structure.

    Applies cleaning heuristics for common LLM output issues:
    trailing commas, single quotes, unquoted keys, truncated JSON.
    Only dict and list results are accepted; scalar JSON values
    (strings, numbers, booleans, null) return an error.
    """
    content = block.content
    if not content.strip():
        return TransformResult(
            data=None,
            error="Empty content",
            raw_content=content,
            block_type=block.block_type,
        )

    def _try_parse(text: str) -> TransformResult | None:
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return None
        if isinstance(data, (dict, list)):
            return TransformResult(
                data=data,
                error=None,
                raw_content=content,
                block_type=block.block_type,
            )
        return TransformResult(
            data=None,
            error=f"JSON parsed to scalar type ({type(data).__name__}),"
            " expected dict or list",
            raw_content=content,
            block_type=block.block_type,
        )

    # Phase 1: Try parsing as-is
    result = _try_parse(content)
    if result is not None:
        return result

    # Phase 2: Clean common syntax issues and retry
    cleaned = _fix_json(content)
    result = _try_parse(cleaned)
    if result is not None:
        return result

    # Phase 3: Attempt half-JSON recovery
    recovered = _recover_truncated_json(cleaned)
    result = _try_parse(recovered)
    if result is not None:
        return result

    return TransformResult(
        data=None,
        error="JSON parse failed after recovery",
        raw_content=content,
        block_type=block.block_type,
    )


def yaml_block_to_dict(block: CodeBlock) -> TransformResult:
    """Parse a YAML CodeBlock into a Python data structure.

    Requires PyYAML. Install with: pip install md2pydantic[yaml]
    """
    content = block.content
    if not content.strip():
        return TransformResult(
            data=None,
            error="Empty content",
            raw_content=content,
            block_type=block.block_type,
        )

    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError:
        return TransformResult(
            data=None,
            error=(
                "PyYAML is required for YAML parsing. "
                "Install with: pip install md2pydantic[yaml]"
            ),
            raw_content=content,
            block_type=block.block_type,
        )

    try:
        data = yaml.safe_load(content)
        if isinstance(data, (dict, list)):
            return TransformResult(
                data=data,
                error=None,
                raw_content=content,
                block_type=block.block_type,
            )
        # yaml.safe_load can return scalars (str, int, etc.) — wrap or error
        return TransformResult(
            data=None,
            error=(
                "YAML parsed to scalar type"
                f" ({type(data).__name__}), expected dict or list"
            ),
            raw_content=content,
            block_type=block.block_type,
        )
    except Exception as e:
        return TransformResult(
            data=None,
            error=f"YAML parse failed: {e}",
            raw_content=content,
            block_type=block.block_type,
        )


def block_to_dict(block: CodeBlock) -> TransformResult:
    """Parse a CodeBlock into a Python data structure.

    Dispatches to json_block_to_dict or yaml_block_to_dict based on
    block_type. For UNKNOWN blocks, tries JSON first, then YAML.
    """
    if block.block_type == BlockType.JSON:
        return json_block_to_dict(block)
    if block.block_type == BlockType.YAML:
        return yaml_block_to_dict(block)
    # UNKNOWN: try JSON first, then YAML
    result = json_block_to_dict(block)
    if result.data is not None:
        return result
    return yaml_block_to_dict(block)


def blocks_to_dicts(blocks: list[CodeBlock]) -> list[TransformResult]:
    """Parse multiple CodeBlocks into Python data structures."""
    return [block_to_dict(b) for b in blocks]


# ---------------------------------------------------------------------------
# Private JSON cleaning helpers
# ---------------------------------------------------------------------------


def _fix_json(content: str) -> str:
    """Apply all JSON cleaning heuristics in sequence."""
    result = content
    result = _remove_trailing_commas(result)
    result = _single_to_double_quotes(result)
    result = _quote_unquoted_keys(result)
    return result


def _remove_trailing_commas(content: str) -> str:
    """Remove trailing commas before closing braces/brackets.

    String-aware: only removes commas outside quoted strings.
    """
    chars = list(content)
    result_chars: list[str] = []
    in_string = False
    escape = False
    i = 0
    length = len(chars)

    while i < length:
        ch = chars[i]

        if escape:
            result_chars.append(ch)
            escape = False
            i += 1
            continue

        if ch == "\\":
            result_chars.append(ch)
            if in_string:
                escape = True
            i += 1
            continue

        if ch == '"':
            in_string = not in_string
            result_chars.append(ch)
            i += 1
            continue

        if not in_string and ch == ",":
            # Look ahead: is the next non-whitespace a } or ]?
            j = i + 1
            while j < length and chars[j] in (" ", "\t", "\n", "\r"):
                j += 1
            if j < length and chars[j] in ("}", "]"):
                # Skip this trailing comma
                i += 1
                continue

        result_chars.append(ch)
        i += 1

    return "".join(result_chars)


def _single_to_double_quotes(content: str) -> str:
    """Replace single quotes with double quotes for JSON strings.

    Uses a state machine to avoid replacing apostrophes inside
    already-double-quoted strings.
    """
    chars = list(content)
    in_double = False
    in_single = False
    escape = False
    i = 0
    while i < len(chars):
        ch = chars[i]
        if escape:
            escape = False
            i += 1
            continue
        if ch == "\\":
            escape = True
            i += 1
            continue
        if ch == '"' and not in_single:
            in_double = not in_double
            i += 1
            continue
        if ch == "'" and not in_double:
            if not in_single:
                # Opening single quote — replace with double
                chars[i] = '"'
                in_single = True
            else:
                # Closing single quote — replace with double
                chars[i] = '"'
                in_single = False
            i += 1
            continue
        i += 1
    result = "".join(chars)
    # After converting single→double quotes, any \' escapes inside
    # now-double-quoted strings are invalid JSON. Replace \' with just '
    result = result.replace("\\'", "'")
    return result


def _quote_unquoted_keys(content: str) -> str:
    """Add double quotes around unquoted JSON keys.

    String-aware: skips content inside double-quoted strings to avoid
    corrupting values that contain word-colon patterns.
    """
    result: list[str] = []
    i = 0
    in_string = False
    escape = False
    length = len(content)

    while i < length:
        ch = content[i]

        if escape:
            result.append(ch)
            escape = False
            i += 1
            continue

        if ch == "\\":
            result.append(ch)
            if in_string:
                escape = True
            i += 1
            continue

        if ch == '"':
            in_string = not in_string
            result.append(ch)
            i += 1
            continue

        if in_string:
            result.append(ch)
            i += 1
            continue

        # Outside strings: check for unquoted key pattern
        if ch in ("{", ",", "\n"):
            result.append(ch)
            i += 1
            # Skip whitespace
            while i < length and content[i] in (" ", "\t", "\n", "\r"):
                result.append(content[i])
                i += 1
            # Check for bare identifier followed by colon
            if i < length and (content[i].isalpha() or content[i] == "_"):
                j = i
                while j < length and (content[j].isalnum() or content[j] == "_"):
                    j += 1
                # Skip whitespace after identifier
                k = j
                while k < length and content[k] in (" ", "\t"):
                    k += 1
                if (
                    k < length
                    and content[k] == ":"
                    and content[i:j]
                    not in (
                        "true",
                        "false",
                        "null",
                    )
                ):
                    # It's an unquoted key — quote it
                    result.append('"')
                    result.append(content[i:j])
                    result.append('"')
                    i = j
                    continue
            continue

        result.append(ch)
        i += 1

    return "".join(result)


def _recover_truncated_json(content: str) -> str:
    """Attempt to close truncated JSON by appending missing delimiters.

    Tracks open brackets/braces (respecting string literals) and
    appends closing delimiters in LIFO order.
    """
    # Track unclosed delimiters
    stack: list[str] = []
    in_string = False
    escape = False

    for ch in content:
        if escape:
            escape = False
            continue
        if ch == "\\":
            if in_string:
                escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            stack.append("}")
        elif ch == "[":
            stack.append("]")
        elif ch in ("}", "]") and stack and stack[-1] == ch:
            stack.pop()

    if not stack:
        return content

    # Strip trailing incomplete tokens (comma, colon, whitespace)
    stripped = content.rstrip()
    stripped = re.sub(r"[,:\s]+$", "", stripped)

    # If we're in an unclosed string, close it first
    if in_string:
        # If the string ends with a backslash, it would escape our closing quote
        if stripped.endswith("\\"):
            stripped += "\\"
        stripped += '"'

    # Cap recovery depth
    if len(stack) > 50:
        return content

    # Close in reverse order (LIFO)
    closing = "".join(reversed(stack))
    return stripped + closing
