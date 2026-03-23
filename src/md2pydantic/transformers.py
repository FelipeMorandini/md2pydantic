"""Transformer module.

Converts raw extracted formats into Python dictionaries and
(optionally) pandas DataFrames.
"""

from __future__ import annotations

from typing import Any

from md2pydantic.models import TableBlock


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
