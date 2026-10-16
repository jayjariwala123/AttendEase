"""
student_management.py — CRUD operations for the students table.

All functions use parameterised queries (via database.py helpers) to prevent
SQL injection.  Business-level validation is performed here so Streamlit pages
stay thin.
"""

import logging
import uuid
from datetime import datetime, timezone

import database as db

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _generate_student_id() -> str:
    """Generate a short, unique student ID like 'STU-A1B2C3'."""
    return "STU-" + uuid.uuid4().hex[:6].upper()


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

def add_student(
    roll_number: str,
    full_name: str,
    department: str,
    email: str = "",
    student_id: str = "",
) -> dict:
    """
    Insert a new student record.

    Returns the newly created student as a dict.
    Raises ValueError on invalid or duplicate inputs.
    """
    roll_number = roll_number.strip().upper()
    full_name = full_name.strip()
    department = department.strip()
    email = email.strip()

    # --- Validation ---
    if not roll_number:
        raise ValueError("Roll number is required.")
    if not full_name:
        raise ValueError("Full name is required.")
    if not department:
        raise ValueError("Department / class is required.")

    # Auto-generate ID if not provided
    if not student_id:
        student_id = _generate_student_id()
        # Extremely unlikely collision guard
        for _ in range(5):
            if not db.fetchone(
                "SELECT id FROM students WHERE student_id = ?", (student_id,)
            ):
                break
            student_id = _generate_student_id()

    # Duplicate checks
    if db.fetchone("SELECT id FROM students WHERE student_id = ?", (student_id,)):
        raise ValueError(f"Student ID '{student_id}' already exists.")
    if db.fetchone(
        "SELECT id FROM students WHERE roll_number = ?", (roll_number,)
    ):
        raise ValueError(f"Roll number '{roll_number}' already exists.")

    registered_at = _now_utc_iso()
    db.execute(
        """
        INSERT INTO students (student_id, roll_number, full_name, department, email, registered_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (student_id, roll_number, full_name, department, email, registered_at),
    )
    logger.info("Student added: %s (%s)", full_name, roll_number)
    return get_student_by_roll(roll_number)


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------

def get_all_students(department: str = "", search: str = "") -> list[dict]:
    """
    Return all students, optionally filtered by department and/or a search term
    that matches against full_name or roll_number.
    """
    conditions = []
    params: list = []

    if department:
        conditions.append("department = ?")
        params.append(department)
    if search:
        conditions.append("(full_name LIKE ? OR roll_number LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%"])

    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    sql = f"""
        SELECT id, student_id, roll_number, full_name, department, email, registered_at
        FROM students {where}
        ORDER BY department, roll_number
    """
    return [dict(r) for r in db.fetchall(sql, tuple(params))]


def get_student_by_id(student_pk: int) -> dict | None:
    """Return a student by their integer primary key."""
    row = db.fetchone(
        "SELECT id, student_id, roll_number, full_name, department, email, registered_at "
        "FROM students WHERE id = ?",
        (student_pk,),
    )
    return dict(row) if row else None


def get_student_by_roll(roll_number: str) -> dict | None:
    """Return a student by roll number (case-insensitive)."""
    row = db.fetchone(
        "SELECT id, student_id, roll_number, full_name, department, email, registered_at "
        "FROM students WHERE roll_number = ?",
        (roll_number.strip().upper(),),
    )
    return dict(row) if row else None


def get_student_by_student_id(student_id: str) -> dict | None:
    """Return a student by the application-level student_id field."""
    row = db.fetchone(
        "SELECT id, student_id, roll_number, full_name, department, email, registered_at "
        "FROM students WHERE student_id = ?",
        (student_id,),
    )
    return dict(row) if row else None


def get_departments() -> list[str]:
    """Return a sorted list of unique department names."""
    rows = db.fetchall("SELECT DISTINCT department FROM students ORDER BY department")
    return [r["department"] for r in rows]


def count_students() -> int:
    """Return the total number of registered students."""
    row = db.fetchone("SELECT COUNT(*) AS cnt FROM students")
    return row["cnt"] if row else 0


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------

def update_student(
    student_pk: int,
    roll_number: str,
    full_name: str,
    department: str,
    email: str = "",
) -> None:
    """
    Update an existing student's mutable fields.
    Raises ValueError on validation failures or duplicate roll numbers.
    """
    roll_number = roll_number.strip().upper()
    full_name = full_name.strip()
    department = department.strip()
    email = email.strip()

    if not roll_number:
        raise ValueError("Roll number is required.")
    if not full_name:
        raise ValueError("Full name is required.")
    if not department:
        raise ValueError("Department / class is required.")

    # Check roll number clash with OTHER students
    conflict = db.fetchone(
        "SELECT id FROM students WHERE roll_number = ? AND id != ?",
        (roll_number, student_pk),
    )
    if conflict:
        raise ValueError(f"Roll number '{roll_number}' is already used by another student.")

    db.execute(
        """
        UPDATE students
        SET roll_number = ?, full_name = ?, department = ?, email = ?
        WHERE id = ?
        """,
        (roll_number, full_name, department, email, student_pk),
    )
    logger.info("Student pk=%s updated.", student_pk)


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

def delete_student(student_pk: int) -> None:
    """
    Delete a student record.

    Note: Foreign-key ON DELETE RESTRICT is set on attendance_records, so this
    will raise an IntegrityError if the student has existing attendance records.
    Callers should catch sqlite3.IntegrityError and present a user-friendly message.
    """
    db.execute("DELETE FROM students WHERE id = ?", (student_pk,))
    logger.info("Student pk=%s deleted.", student_pk)
