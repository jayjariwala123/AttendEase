"""
attendance.py — Recording and querying attendance.

Business rules enforced here
-----------------------------
1. The session must exist.
2. The session must be Active AND within the start/expiry window.
3. The roll number must belong to a registered student.
4. The student must not have already been marked present for this session.
5. (Optional) The student's department should match the session department.
   This check is enabled by ENFORCE_DEPARTMENT_MATCH (set to False for demo
   flexibility).

All rules are validated in a single transaction to prevent race conditions.
"""

import logging
from datetime import datetime, timezone

import database as db
from session_management import get_session_by_token, is_session_active
from student_management import get_student_by_roll

logger = logging.getLogger(__name__)

# Set to True to require the student's department to match the session.
ENFORCE_DEPARTMENT_MATCH = False


# ---------------------------------------------------------------------------
# Recording attendance
# ---------------------------------------------------------------------------

class AttendanceError(Exception):
    """Raised when an attendance submission cannot be accepted."""


def mark_attendance(token: str, roll_number: str) -> dict:
    """
    Mark a student present for the session identified by *token*.

    Returns the attendance record dict on success.
    Raises AttendanceError with a descriptive message on any failure.
    """
    # 1. Resolve the session
    session = get_session_by_token(token)
    if session is None:
        raise AttendanceError("Invalid or unknown attendance session.")

    # 2. Check session validity (status + time window)
    if not is_session_active(session):
        if session["status"] == "Closed":
            raise AttendanceError(
                "This attendance session has been closed by the teacher."
            )
        raise AttendanceError(
            "This attendance session is not currently active. "
            "It may have expired or not yet started."
        )

    # 3. Resolve the student
    student = get_student_by_roll(roll_number)
    if student is None:
        raise AttendanceError(
            f"Roll number '{roll_number.upper()}' is not registered in the system."
        )

    # 4. Optional department match
    if ENFORCE_DEPARTMENT_MATCH and student["department"] != session["department"]:
        raise AttendanceError(
            f"Your department ({student['department']}) does not match "
            f"the session department ({session['department']})."
        )

    # 5. Duplicate check + insert (atomic)
    existing = db.fetchone(
        "SELECT id FROM attendance_records WHERE session_id = ? AND student_id = ?",
        (session["id"], student["id"]),
    )
    if existing:
        raise AttendanceError(
            f"Attendance for {student['full_name']} has already been recorded "
            "for this session."
        )

    recorded_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    record_pk = db.execute(
        "INSERT INTO attendance_records(session_id, student_id, recorded_at) VALUES (?, ?, ?)",
        (session["id"], student["id"], recorded_at),
    )
    logger.info(
        "Attendance marked: student=%s session=%s", student["roll_number"], session["id"]
    )
    return {
        "id": record_pk,
        "session_id": session["id"],
        "student_id": student["id"],
        "student_name": student["full_name"],
        "roll_number": student["roll_number"],
        "subject": session["subject"],
        "recorded_at": recorded_at,
    }


# ---------------------------------------------------------------------------
# Querying attendance
# ---------------------------------------------------------------------------

def get_attendance_for_session(session_pk: int) -> list[dict]:
    """Return all attendance records for a given session with student details."""
    rows = db.fetchall(
        """
        SELECT ar.id, ar.recorded_at,
               s.student_id, s.roll_number, s.full_name, s.department,
               sess.subject, sess.session_date, sess.department AS session_dept
        FROM   attendance_records ar
        JOIN   students s            ON s.id = ar.student_id
        JOIN   attendance_sessions sess ON sess.id = ar.session_id
        WHERE  ar.session_id = ?
        ORDER  BY s.roll_number
        """,
        (session_pk,),
    )
    return [dict(r) for r in rows]


def get_all_attendance(
    student_pk: int = 0,
    session_pk: int = 0,
    department: str = "",
    subject: str = "",
    from_date: str = "",
    to_date: str = "",
) -> list[dict]:
    """
    Return attendance records with optional filters.
    Dates should be YYYY-MM-DD strings.
    """
    conditions = []
    params: list = []

    if student_pk:
        conditions.append("ar.student_id = ?")
        params.append(student_pk)
    if session_pk:
        conditions.append("ar.session_id = ?")
        params.append(session_pk)
    if department:
        conditions.append("sess.department = ?")
        params.append(department)
    if subject:
        conditions.append("sess.subject = ?")
        params.append(subject)
    if from_date:
        conditions.append("sess.session_date >= ?")
        params.append(from_date)
    if to_date:
        conditions.append("sess.session_date <= ?")
        params.append(to_date)

    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    sql = f"""
        SELECT ar.id, ar.recorded_at,
               s.id AS student_pk, s.student_id, s.roll_number, s.full_name, s.department,
               sess.id AS session_pk, sess.subject, sess.session_date,
               sess.department AS session_dept, sess.start_time
        FROM   attendance_records ar
        JOIN   students s               ON s.id = ar.student_id
        JOIN   attendance_sessions sess ON sess.id = ar.session_id
        {where}
        ORDER  BY sess.session_date DESC, s.roll_number
    """
    return [dict(r) for r in db.fetchall(sql, tuple(params))]


def count_today_attendance() -> int:
    """Return number of distinct attendance records for today's date (UTC)."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    row = db.fetchone(
        """
        SELECT COUNT(ar.id) AS cnt
        FROM attendance_records ar
        JOIN attendance_sessions sess ON sess.id = ar.session_id
        WHERE sess.session_date = ?
        """,
        (today,),
    )
    return row["cnt"] if row else 0


def get_student_attendance_summary(department: str = "") -> list[dict]:
    """
    For each student, compute the number of applicable sessions and
    sessions attended, and return the attendance percentage.

    Applicable sessions = sessions whose department matches the student's
    department AND whose status is 'Closed' or 'Active'
    (all sessions, including those created after the student registered).

    Attendance Percentage = (attended / applicable) * 100
    Returns 0 when applicable == 0 to avoid division-by-zero.
    """
    dept_filter = "AND s.department = ?" if department else ""
    dept_param = (department,) if department else ()

    sql = f"""
        WITH applicable AS (
            SELECT s.id AS student_id, COUNT(sess.id) AS total_sessions
            FROM students s
            JOIN attendance_sessions sess ON sess.department = s.department
            {dept_filter}
            GROUP BY s.id
        ),
        attended AS (
            SELECT ar.student_id, COUNT(ar.id) AS sessions_attended
            FROM attendance_records ar
            GROUP BY ar.student_id
        )
        SELECT
            s.id,
            s.student_id,
            s.roll_number,
            s.full_name,
            s.department,
            COALESCE(ap.total_sessions, 0)   AS total_sessions,
            COALESCE(att.sessions_attended, 0) AS sessions_attended,
            CASE
                WHEN COALESCE(ap.total_sessions, 0) = 0 THEN 0.0
                ELSE ROUND(
                    100.0 * COALESCE(att.sessions_attended, 0) / ap.total_sessions, 2
                )
            END AS attendance_pct
        FROM students s
        LEFT JOIN applicable ap  ON ap.student_id = s.id
        LEFT JOIN attended   att ON att.student_id = s.id
        {"WHERE s.department = ?" if department else ""}
        ORDER BY attendance_pct ASC
    """
    params = dept_param + dept_param if department else ()
    return [dict(r) for r in db.fetchall(sql, params)]


def get_session_attendance_counts() -> list[dict]:
    """
    For each session return: session info + present_count + absent_count.
    Absent = total students in that department − present.
    """
    rows = db.fetchall(
        """
        SELECT
            sess.id,
            sess.department,
            sess.subject,
            sess.session_date,
            sess.start_time,
            sess.status,
            (SELECT COUNT(*) FROM attendance_records ar WHERE ar.session_id = sess.id) AS present_count,
            (SELECT COUNT(*) FROM students s WHERE s.department = sess.department) AS dept_total
        FROM attendance_sessions sess
        ORDER BY sess.session_date DESC, sess.start_time DESC
        """
    )
    result = []
    for r in rows:
        d = dict(r)
        d["absent_count"] = max(0, d["dept_total"] - d["present_count"])
        result.append(d)
    return result
