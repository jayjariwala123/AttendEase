"""
database.py — Database initialisation, connection management, and schema for
AttendEase.

Design decisions
----------------
* A single SQLite file is stored at config.DATABASE_PATH and is created once.
  Streamlit reruns do NOT recreate the database; the init function uses
  IF NOT EXISTS guards and is idempotent.
* Foreign-key enforcement is enabled on every new connection via PRAGMA.
* All queries in helper functions use parameterised statements to prevent SQL
  injection.
* Transactions are used where multiple related writes must be atomic.
"""

import sqlite3
import logging
from contextlib import contextmanager
from config import DATABASE_PATH

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Connection helper
# ---------------------------------------------------------------------------

@contextmanager
def get_connection():
    """
    Yield a SQLite connection with foreign keys enabled and WAL journal mode.
    The connection is committed and closed automatically.
    On error, the transaction is rolled back and the exception is re-raised.
    """
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row          # rows accessible by column name
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Schema definition
# ---------------------------------------------------------------------------

_SCHEMA_SQL = """
-- ============================================================
-- Table: administrators
-- ============================================================
CREATE TABLE IF NOT EXISTS administrators (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT    NOT NULL,
    full_name     TEXT,
    created_at    TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

-- ============================================================
-- Table: students
-- ============================================================
CREATE TABLE IF NOT EXISTS students (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id      TEXT    NOT NULL UNIQUE,
    roll_number     TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    full_name       TEXT    NOT NULL,
    department      TEXT    NOT NULL,
    email           TEXT,
    registered_at   TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_students_department ON students(department);
CREATE INDEX IF NOT EXISTS idx_students_roll ON students(roll_number);

-- ============================================================
-- Table: attendance_sessions
-- ============================================================
CREATE TABLE IF NOT EXISTS attendance_sessions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_token   TEXT    NOT NULL UNIQUE,
    department      TEXT    NOT NULL,
    subject         TEXT    NOT NULL,
    session_date    TEXT    NOT NULL,   -- YYYY-MM-DD
    start_time      TEXT    NOT NULL,   -- HH:MM (24-hr, local timezone)
    expiry_time     TEXT    NOT NULL,   -- HH:MM (24-hr, local timezone)
    status          TEXT    NOT NULL DEFAULT 'Active'
                            CHECK(status IN ('Active', 'Closed')),
    created_by      TEXT    NOT NULL,   -- admin username
    created_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_sessions_department ON attendance_sessions(department);
CREATE INDEX IF NOT EXISTS idx_sessions_date       ON attendance_sessions(session_date);
CREATE INDEX IF NOT EXISTS idx_sessions_token      ON attendance_sessions(session_token);

-- ============================================================
-- Table: attendance_records
-- ============================================================
CREATE TABLE IF NOT EXISTS attendance_records (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id    INTEGER NOT NULL REFERENCES attendance_sessions(id) ON DELETE RESTRICT,
    student_id    INTEGER NOT NULL REFERENCES students(id)            ON DELETE RESTRICT,
    recorded_at   TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    UNIQUE (session_id, student_id)   -- prevents duplicate attendance
);

CREATE INDEX IF NOT EXISTS idx_records_session  ON attendance_records(session_id);
CREATE INDEX IF NOT EXISTS idx_records_student  ON attendance_records(student_id);

-- ============================================================
-- Table: app_meta  (key-value store for application flags)
-- ============================================================
CREATE TABLE IF NOT EXISTS app_meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);
"""


def init_db() -> None:
    """
    Create all tables and indexes if they do not yet exist.
    Safe to call on every application start.
    """
    with get_connection() as conn:
        conn.executescript(_SCHEMA_SQL)
    logger.info("Database initialised at %s", DATABASE_PATH)


# ---------------------------------------------------------------------------
# Generic helpers used across modules
# ---------------------------------------------------------------------------

def fetchall(sql: str, params: tuple = ()) -> list[sqlite3.Row]:
    """Execute a SELECT and return all rows."""
    with get_connection() as conn:
        cur = conn.execute(sql, params)
        return cur.fetchall()


def fetchone(sql: str, params: tuple = ()) -> sqlite3.Row | None:
    """Execute a SELECT and return the first row or None."""
    with get_connection() as conn:
        cur = conn.execute(sql, params)
        return cur.fetchone()


def execute(sql: str, params: tuple = ()) -> int:
    """
    Execute an INSERT / UPDATE / DELETE.
    Returns the lastrowid for INSERT statements, else rowcount.
    """
    with get_connection() as conn:
        cur = conn.execute(sql, params)
        return cur.lastrowid or cur.rowcount


def execute_many(sql: str, params_list: list[tuple]) -> None:
    """Execute a statement for each parameter tuple (batch insert/update)."""
    with get_connection() as conn:
        conn.executemany(sql, params_list)


def get_meta(key: str) -> str | None:
    """Retrieve a value from the app_meta table."""
    row = fetchone("SELECT value FROM app_meta WHERE key = ?", (key,))
    return row["value"] if row else None


def set_meta(key: str, value: str) -> None:
    """Insert or replace a key-value pair in app_meta."""
    execute(
        "INSERT OR REPLACE INTO app_meta(key, value) VALUES (?, ?)",
        (key, value),
    )
