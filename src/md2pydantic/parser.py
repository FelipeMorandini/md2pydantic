"""Scanner module - identifies candidate structured blocks within Markdown text."""

from __future__ import annotations

import re

from md2pydantic.models import BlockType, CodeBlock, TableBlock

# --- Language hint mapping ---

_LANG_HINT_MAP: dict[str, BlockType] = {
    "json": BlockType.JSON,
    "yaml": BlockType.YAML,
    "yml": BlockType.YAML,
}

# --- Regex patterns ---

# Fenced code blocks: 3+ backticks, optional language hint, content,
# matching closing fence.
# Handles: extra backticks, trailing text after closing fence, mixed case hints
_FENCED_BLOCK_RE = re.compile(
    r"^[ ]{0,3}(?P<fence>`{3,})[^\S\n]*(?P<lang>[a-zA-Z0-9_-]*)[^\S\n]*\n"
    r"(?P<content>.*?)\n?"
    r"^[ ]{0,3}(?P=fence)[`]*[^\n]*(?:\n|$)",
    re.MULTILINE | re.DOTALL,
)

# Fallback for unclosed fenced blocks with a JSON/YAML hint: extract to EOF
_UNCLOSED_FENCED_RE = re.compile(
    r"^[ ]{0,3}(?P<fence>`{3,})[^\S\n]*(?P<lang>json|yaml|yml)[^\S\n]*\n"
    r"(?P<content>.+)",
    re.MULTILINE | re.DOTALL | re.IGNORECASE,
)


def scan_blocks(markdown: str) -> list[CodeBlock]:
    """Extract all candidate structured blocks from a Markdown string.

    Returns blocks ordered by their position in the source document.
    Fenced code blocks are extracted first; unfenced inline JSON is
    extracted from the remaining text to avoid duplicates.
    """
    # Normalize line endings
    text = markdown.replace("\r\n", "\n").replace("\r", "\n")

    # Collect (char_offset, CodeBlock) pairs for accurate source-order sorting
    block_pairs: list[tuple[int, CodeBlock]] = []
    claimed_spans: list[tuple[int, int]] = []

    # Phase 1: Fenced blocks (closed)
    for match in _FENCED_BLOCK_RE.finditer(text):
        # Always claim the span to prevent unclosed-fence fallback from
        # re-matching this region (e.g. empty or non-JSON/YAML blocks).
        claimed_spans.append((match.start(), match.end()))

        lang = match.group("lang").strip().lower()
        content = match.group("content")

        block_type = _normalize_lang_hint(lang) if lang else _infer_block_type(content)

        # Skip blocks that aren't JSON or YAML
        if block_type == BlockType.UNKNOWN:
            continue

        cleaned = _clean_content(content)
        if not cleaned:
            continue

        start_line = _line_number_at_offset(text, match.start())
        end_line = _line_number_at_offset(text, match.end() - 1)

        block_pairs.append(
            (
                match.start(),
                CodeBlock(
                    content=cleaned,
                    block_type=block_type,
                    fenced=True,
                    start_line=start_line,
                    end_line=end_line,
                ),
            )
        )

    # Phase 1b: Unclosed fenced blocks (fallback)
    for match in _UNCLOSED_FENCED_RE.finditer(text):
        if _overlaps(match.start(), match.end(), claimed_spans):
            continue

        lang = match.group("lang").strip().lower()
        content = match.group("content")
        block_type = _normalize_lang_hint(lang)

        cleaned = _clean_content(content)
        if not cleaned:
            continue

        start_line = _line_number_at_offset(text, match.start())
        end_line = _line_number_at_offset(text, match.end() - 1)

        block_pairs.append(
            (
                match.start(),
                CodeBlock(
                    content=cleaned,
                    block_type=block_type,
                    fenced=True,
                    start_line=start_line,
                    end_line=end_line,
                ),
            )
        )
        claimed_spans.append((match.start(), match.end()))

    # Phase 2: Unfenced JSON objects and arrays
    for open_char, close_char in [("[", "]"), ("{", "}")]:
        for start, end in _find_balanced_pairs(text, open_char, close_char):
            if _overlaps(start, end, claimed_spans):
                continue

            candidate = text[start:end]
            block_type = _infer_block_type(candidate)

            if block_type == BlockType.UNKNOWN:
                continue

            cleaned = _clean_content(candidate)
            if not cleaned:
                continue

            start_line = _line_number_at_offset(text, start)
            end_line = _line_number_at_offset(text, end - 1)

            block_pairs.append(
                (
                    start,
                    CodeBlock(
                        content=cleaned,
                        block_type=block_type,
                        fenced=False,
                        start_line=start_line,
                        end_line=end_line,
                    ),
                )
            )
            claimed_spans.append((start, end))

    # Sort by character offset for accurate source-order
    block_pairs.sort(key=lambda pair: pair[0])
    return [block for _, block in block_pairs]


def _normalize_lang_hint(hint: str) -> BlockType:
    """Map a fenced code block language hint to a BlockType."""
    return _LANG_HINT_MAP.get(hint.lower().strip(), BlockType.UNKNOWN)


def _infer_block_type(content: str) -> BlockType:
    """Heuristically determine whether content is JSON, YAML, or unknown."""
    stripped = content.strip()
    if not stripped:
        return BlockType.UNKNOWN
    if stripped.startswith(("{", "[")):
        return BlockType.JSON
    if re.search(r"^[a-zA-Z_][\w]*\s*:", stripped, re.MULTILINE):
        return BlockType.YAML
    return BlockType.UNKNOWN


def _clean_content(raw: str) -> str:
    """Strip leading/trailing blank lines and normalize whitespace."""
    lines = raw.split("\n")
    # Remove leading blank lines
    while lines and not lines[0].strip():
        lines.pop(0)
    # Remove trailing blank lines
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines:
        return ""
    return "\n".join(lines)


def _line_number_at_offset(text: str, offset: int) -> int:
    """Convert a character offset to a 0-based line number."""
    return text.count("\n", 0, offset)


def _overlaps(start: int, end: int, claimed: list[tuple[int, int]]) -> bool:
    """Check if a span overlaps with any claimed span."""
    return any(start < ce and end > cs for cs, ce in claimed)


_JSON_VALUE_START = frozenset("{[\"'-0123456789tfn")


def _find_balanced_pairs(
    text: str, open_char: str, close_char: str
) -> list[tuple[int, int]]:
    """Find all balanced delimiter pairs, returning (start, end) character offsets.

    Respects JSON string literals (skips delimiters inside double-quoted strings).
    For array detection, filters out Markdown links and non-JSON content.
    """
    results: list[tuple[int, int]] = []
    text_len = len(text)
    i = 0
    while i < text_len:
        if text[i] == open_char:
            # For arrays, apply heuristics to skip Markdown links
            if open_char == "[":
                # Find first non-whitespace char after [
                j = i + 1
                while j < text_len and text[j] in (" ", "\t", "\n", "\r"):
                    j += 1
                if j >= text_len or text[j] not in _JSON_VALUE_START:
                    i += 1
                    continue

            end = _find_closing(text, i, open_char, close_char)
            if end is not None:
                # Skip Markdown links: [text](url)
                if open_char == "[" and end + 1 < text_len and text[end + 1] == "(":
                    i = end + 1
                    continue
                results.append((i, end + 1))
                i = end + 1
            else:
                # No matching closer found — skip past this opener.
                # Jump ahead to avoid quadratic re-scanning.
                i += 1
        else:
            i += 1
    return results


def _find_closing(text: str, start: int, open_char: str, close_char: str) -> int | None:
    """Find the matching closing delimiter from start position.

    Handles nested delimiters and respects double-quoted string literals.
    """
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if escape:
            escape = False
            continue
        if ch == "\\" and in_string:
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == open_char:
            depth += 1
        elif ch == close_char:
            depth -= 1
            if depth == 0:
                return i
    return None


# --- Table scanning ---

# Separator row: cells of dashes with optional colons for alignment
_TABLE_SEP_RE = re.compile(r"^[ ]{0,3}\|?(?:[ ]*:?-+:?[ ]*\|)+[ ]*:?-+:?[ ]*\|?[ ]*$")

# Markdown heading
_HEADING_RE = re.compile(r"^#{1,6}[ \t]+(.+?)[ \t]*#*[ \t]*$")


def scan_tables(
    markdown: str,
    *,
    index: int | None = None,
    heading: str | None = None,
) -> list[TableBlock]:
    """Extract Markdown tables from a document.

    Args:
        markdown: The Markdown text to scan.
        index: If provided, return only the table at this 0-based index
            (applied after heading filtering, if any).
        heading: If provided, return only tables under headings matching
            this substring (case-insensitive).

    Returns:
        List of TableBlock instances in document order.
    """
    text = markdown.replace("\r\n", "\n").replace("\r", "\n")

    # Get fenced code block spans to exclude tables inside them
    fenced_spans: list[tuple[int, int]] = []
    for match in _FENCED_BLOCK_RE.finditer(text):
        fenced_spans.append((match.start(), match.end()))

    tables = _scan_all_tables(text, fenced_spans)

    if heading is not None:
        heading_lower = heading.lower()
        tables = [t for t in tables if t.heading and heading_lower in t.heading.lower()]

    if index is not None:
        if 0 <= index < len(tables):
            return [tables[index]]
        return []

    return tables


def _scan_all_tables(
    text: str, fenced_spans: list[tuple[int, int]]
) -> list[TableBlock]:
    """Detect all Markdown tables in the text, excluding fenced code blocks."""
    lines = text.split("\n")
    tables: list[TableBlock] = []

    # Pre-collect headings
    headings: list[tuple[int, str]] = []  # (line_number, heading_text)
    for i, line in enumerate(lines):
        m = _HEADING_RE.match(line.strip())
        if m:
            headings.append((i, m.group(1).strip()))

    # Pre-compute which lines fall inside fenced code blocks (O(1) lookup)
    fenced_lines: set[int] = set()
    for fs, fe in fenced_spans:
        start_ln = text.count("\n", 0, fs)
        end_ln = text.count("\n", 0, max(fe - 1, 0))
        fenced_lines.update(range(start_ln, end_ln + 1))

    i = 0
    while i < len(lines) - 1:
        # Check if this line is inside a fenced code block
        if i in fenced_lines:
            i += 1
            continue

        header_line = lines[i]
        sep_line = lines[i + 1]

        # Check: is this a header + separator pair?
        if not _has_pipe(header_line) or not _is_separator_row(sep_line):
            i += 1
            continue

        header_cols = _count_columns(header_line)
        sep_cols = _count_columns(sep_line)

        if header_cols != sep_cols or header_cols == 0:
            i += 1
            continue

        # Found a table start. Collect data rows.
        data_start = i + 2
        j = data_start
        while j < len(lines):
            row = lines[j]
            if not row.strip():  # Blank line terminates
                break
            if not _has_pipe(row):  # No pipe terminates
                break
            j += 1

        # Parse the table
        headers = _parse_table_row(header_line)
        # Normalize header count
        headers = headers[:header_cols]
        while len(headers) < header_cols:
            headers.append("")

        rows: list[tuple[str, ...]] = []
        for row_idx in range(data_start, j):
            cells = _parse_table_row(lines[row_idx])
            # Pad or truncate to match header count
            while len(cells) < header_cols:
                cells.append("")
            cells = cells[:header_cols]
            rows.append(tuple(cells))

        # Find preceding heading
        table_heading = _find_preceding_heading(headings, i)

        tables.append(
            TableBlock(
                headers=tuple(headers),
                rows=tuple(rows),
                heading=table_heading,
                start_line=i,
                end_line=j - 1 if j > data_start else i + 1,
            )
        )

        i = j  # Skip past the table

    return tables


def _is_separator_row(line: str) -> bool:
    """Check if a line is a valid Markdown table separator row."""
    return _TABLE_SEP_RE.match(line.strip()) is not None


def _has_pipe(line: str) -> bool:
    """Check if a line contains an unescaped pipe character."""
    stripped = line.strip()
    if not stripped:
        return False
    # Check for unescaped pipes
    i = 0
    while i < len(stripped):
        if stripped[i] == "\\" and i + 1 < len(stripped):
            i += 2  # Skip escaped character
            continue
        if stripped[i] == "|":
            return True
        i += 1
    return False


def _parse_table_row(line: str) -> list[str]:
    """Split a pipe-delimited row into stripped cell values.

    Handles escaped pipes (\\|) within cell content.
    """
    stripped = line.strip()

    # Replace escaped pipes with a placeholder unlikely to appear in input
    placeholder = "\x00\x01PIPE\x01\x00"
    cleaned = stripped.replace("\\|", placeholder)

    # Remove leading/trailing pipes
    if cleaned.startswith("|"):
        cleaned = cleaned[1:]
    if cleaned.endswith("|"):
        cleaned = cleaned[:-1]

    # Split on pipes and restore escaped pipes
    cells = [cell.strip().replace(placeholder, "|") for cell in cleaned.split("|")]
    return cells


def _count_columns(line: str) -> int:
    """Count the number of columns in a pipe-delimited row."""
    return len(_parse_table_row(line))


def _find_preceding_heading(
    headings: list[tuple[int, str]], table_line: int
) -> str | None:
    """Find the nearest heading before a table's start line."""
    result: str | None = None
    for line_no, text in headings:
        if line_no < table_line:
            result = text
        else:
            break
    return result
