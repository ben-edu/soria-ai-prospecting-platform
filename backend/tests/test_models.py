"""Tests for SQLModel metadata and expected tables."""

from sqlmodel import SQLModel

EXPECTED_TABLES = {
    "service_categories",
    "offers",
    "academy_categories",
    "academy_resources",
    "companies",
    "contacts",
    "opportunities",
    "opportunity_scores",
    "message_drafts",
    "follow_ups",
    "interactions",
    "compliance_events",
    "source_records",
}


def test_all_expected_tables_registered():
    """Verify SQLModel metadata contains all 13 expected tables."""
    registered = set(SQLModel.metadata.tables.keys())
    missing = EXPECTED_TABLES - registered
    assert not missing, f"Tables missing from metadata: {missing}"


def test_no_extra_tables():
    """Verify no unexpected tables are registered."""
    registered = set(SQLModel.metadata.tables.keys())
    extra = registered - EXPECTED_TABLES
    assert not extra, f"Unexpected tables in metadata: {extra}"


def test_table_columns_exist():
    """Verify key columns exist on each table."""
    tables = SQLModel.metadata.tables

    # service_categories
    sc = tables["service_categories"]
    assert "id" in sc.columns
    assert "name" in sc.columns
    assert "slug" in sc.columns
    assert "created_at" in sc.columns
    assert "updated_at" in sc.columns

    # offers
    off = tables["offers"]
    assert "category_id" in off.columns
    assert off.columns["category_id"].foreign_keys

    # contacts
    co = tables["contacts"]
    assert "company_id" in co.columns
    assert co.columns["company_id"].foreign_keys
