"""
tests/conftest.py — Shared pytest fixtures for AttendEase tests.

All tests use a temporary in-memory (or temp-file) database so they never
touch the production data/attendease.db file.
"""

import os
import tempfile
import pytest

# Patch DATABASE_PATH to a temp file BEFORE any module imports it
@pytest.fixture(scope="session", autouse=True)
def temp_db(tmp_path_factory):
    """Create a fresh temporary database for the entire test session."""
    tmp_dir = tmp_path_factory.mktemp("data")
    db_path = str(tmp_dir / "test_attendease.db")

    # Monkey-patch before importing anything that uses DATABASE_PATH
    import config
    config.DATABASE_PATH = db_path
    # Also patch ASSETS_DIR so QR images go to /tmp
    assets_dir = str(tmp_dir / "assets")
    os.makedirs(assets_dir, exist_ok=True)
    config.ASSETS_DIR = assets_dir

    # Now it is safe to init
    import database as db
    db.init_db()

    yield db_path
