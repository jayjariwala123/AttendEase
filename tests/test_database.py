"""tests/test_database.py — Database initialisation tests."""

import sqlite3
import pytest
import database as db


def test_tables_exist():
    """All four tables should be created by init_db."""
    tables = [r["name"] for r in db.fetchall(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )]
    for expected in ["administrators", "students", "attendance_sessions",
                     "attendance_records", "app_meta"]:
        assert expected in tables, f"Table '{expected}' not found"


def test_foreign_keys_enabled():
    """PRAGMA foreign_keys should be ON (returns 1)."""
    row = db.fetchone("PRAGMA foreign_keys")
    assert row[0] == 1, "Foreign keys are not enabled"


def test_fetchone_returns_none_for_missing():
    row = db.fetchone("SELECT id FROM students WHERE id = 99999")
    assert row is None


def test_fetchall_returns_list():
    result = db.fetchall("SELECT name FROM sqlite_master WHERE type='table'")
    assert isinstance(result, list)


def test_meta_set_and_get():
    db.set_meta("test_key", "test_value")
    val = db.get_meta("test_key")
    assert val == "test_value"


def test_meta_overwrite():
    db.set_meta("overwrite_key", "first")
    db.set_meta("overwrite_key", "second")
    assert db.get_meta("overwrite_key") == "second"
