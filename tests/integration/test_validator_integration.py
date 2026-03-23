"""Integration tests for the full scan → transform → validate pipeline."""

from __future__ import annotations

from pydantic import BaseModel

from md2pydantic.parser import scan_blocks, scan_tables
from md2pydantic.transformers import block_to_dict, table_to_dicts
from md2pydantic.validators import validate_dict, validate_dicts

# --- Test models ---


class User(BaseModel):
    Name: str
    Age: int
    Active: bool


class UserOptional(BaseModel):
    Name: str
    Age: int | None = None
    Active: bool | None = None


class Product(BaseModel):
    name: str
    price: float
    in_stock: bool


# --- 1. Table → model with bool coercion ---


def test_table_to_model_with_bool_coercion():
    """Parse a markdown table, transform to dicts, validate against User model.

    Verifies that 'Yes'/'No' strings are coerced to True/False for bool fields,
    and that string→int coercion works for Age.
    """
    md = (
        "| Name  | Age | Active |\n"
        "|-------|-----|--------|\n"
        "| Alice | 30  | Yes    |\n"
        "| Bob   | 25  | No     |\n"
    )

    tables = scan_tables(md)
    assert len(tables) == 1

    dicts = table_to_dicts(tables[0])
    assert len(dicts) == 2

    results = validate_dicts(dicts, User)
    assert len(results) == 2

    # Both rows should validate successfully
    for r in results:
        assert r.data is not None
        assert r.errors == ()

    alice = results[0].data
    assert alice.Name == "Alice"
    assert alice.Age == 30
    assert alice.Active is True

    bob = results[1].data
    assert bob.Name == "Bob"
    assert bob.Age == 25
    assert bob.Active is False


# --- 2. JSON block → model ---


def test_json_block_to_model():
    """Parse a fenced JSON block, transform via block_to_dict, validate against model.

    Verifies type coercion from JSON native types (string price → float).
    """
    md = (
        "Here is the product data:\n"
        "\n"
        "```json\n"
        '{"name": "Widget", "price": "9.99", "in_stock": true}\n'
        "```\n"
    )

    blocks = scan_blocks(md)
    assert len(blocks) == 1

    transform = block_to_dict(blocks[0])
    assert transform.data is not None
    assert transform.error is None

    result = validate_dict(transform.data, Product)
    assert result.data is not None
    assert result.errors == ()
    assert result.data.name == "Widget"
    assert result.data.price == 9.99
    assert result.data.in_stock is True


# --- 3. Table with empty cells → Optional fields ---


def test_table_with_empty_cells():
    """Empty cells in a table map to None for Optional fields."""
    md = (
        "| Name  | Age | Active |\n"
        "|-------|-----|--------|\n"
        "| Alice | 30  | Yes    |\n"
        "| Bob   |     |        |\n"
    )

    tables = scan_tables(md)
    assert len(tables) == 1

    dicts = table_to_dicts(tables[0])
    assert len(dicts) == 2

    # Empty cells become None in the transformer
    assert dicts[1]["Age"] is None
    assert dicts[1]["Active"] is None

    results = validate_dicts(dicts, UserOptional)
    assert len(results) == 2

    # Both should validate since Age and Active are Optional
    for r in results:
        assert r.data is not None
        assert r.errors == ()

    alice = results[0].data
    assert alice.Name == "Alice"
    assert alice.Age == 30
    assert alice.Active is True

    bob = results[1].data
    assert bob.Name == "Bob"
    assert bob.Age is None
    assert bob.Active is None


# --- 4. Table with N/A values → None for optional fields ---


def test_table_with_na_values():
    """'N/A' in table cells should be coerced to None for Optional fields."""
    md = (
        "| Name    | Age | Active |\n"
        "|---------|-----|--------|\n"
        "| Alice   | 30  | Yes    |\n"
        "| Charlie | N/A | N/A    |\n"
    )

    tables = scan_tables(md)
    assert len(tables) == 1

    dicts = table_to_dicts(tables[0])
    assert len(dicts) == 2

    # N/A is still a string at the transformer level
    assert dicts[1]["Age"] == "N/A"
    assert dicts[1]["Active"] == "N/A"

    results = validate_dicts(dicts, UserOptional)
    assert len(results) == 2

    for r in results:
        assert r.data is not None
        assert r.errors == ()

    alice = results[0].data
    assert alice.Name == "Alice"
    assert alice.Age == 30
    assert alice.Active is True

    charlie = results[1].data
    assert charlie.Name == "Charlie"
    assert charlie.Age is None
    assert charlie.Active is None


# --- 5. Mixed valid/invalid rows → partial success ---


def test_mixed_valid_and_invalid_rows():
    """Table with some valid and some invalid rows.

    Valid rows produce data; invalid rows produce errors.
    Uses the strict User model (non-optional int Age) so 'not_a_number'
    fails validation.
    """
    md = (
        "| Name  | Age          | Active |\n"
        "|-------|--------------|--------|\n"
        "| Alice | 30           | Yes    |\n"
        "| Bob   | not_a_number | No     |\n"
        "| Carol | 28           | Yes    |\n"
    )

    tables = scan_tables(md)
    assert len(tables) == 1

    dicts = table_to_dicts(tables[0])
    assert len(dicts) == 3

    results = validate_dicts(dicts, User)
    assert len(results) == 3

    # Alice: valid
    assert results[0].data is not None
    assert results[0].errors == ()
    assert results[0].data.Name == "Alice"
    assert results[0].data.Age == 30

    # Bob: invalid (Age cannot be parsed to int)
    assert results[1].data is None
    assert len(results[1].errors) > 0
    # The error should reference the Age field
    age_errors = [e for e in results[1].errors if e.field == "Age"]
    assert len(age_errors) > 0

    # Carol: valid
    assert results[2].data is not None
    assert results[2].errors == ()
    assert results[2].data.Name == "Carol"
    assert results[2].data.Age == 28


# --- 6. Multiple tables validated against the same model ---


def test_multiple_tables_same_model():
    """Two tables in the same document, both validated against User model."""
    md = (
        "## Team A\n"
        "\n"
        "| Name  | Age | Active |\n"
        "|-------|-----|--------|\n"
        "| Alice | 30  | Yes    |\n"
        "\n"
        "## Team B\n"
        "\n"
        "| Name | Age | Active |\n"
        "|------|-----|--------|\n"
        "| Bob  | 25  | No     |\n"
        "| Eve  | 22  | Yes    |\n"
    )

    tables = scan_tables(md)
    assert len(tables) == 2

    # Validate each table independently
    all_results = []
    for table in tables:
        dicts = table_to_dicts(table)
        results = validate_dicts(dicts, User)
        all_results.append(results)

    # Table 1 (Team A): 1 row
    assert len(all_results[0]) == 1
    assert all_results[0][0].data is not None
    assert all_results[0][0].data.Name == "Alice"
    assert all_results[0][0].data.Age == 30
    assert all_results[0][0].data.Active is True

    # Table 2 (Team B): 2 rows
    assert len(all_results[1]) == 2
    assert all_results[1][0].data is not None
    assert all_results[1][0].data.Name == "Bob"
    assert all_results[1][0].data.Age == 25
    assert all_results[1][0].data.Active is False

    assert all_results[1][1].data is not None
    assert all_results[1][1].data.Name == "Eve"
    assert all_results[1][1].data.Age == 22
    assert all_results[1][1].data.Active is True
