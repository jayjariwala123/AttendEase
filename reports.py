"""
reports.py — Attendance reporting and CSV export.

All report functions return plain Python dicts/lists so they can be consumed
by both the Streamlit UI and the test suite without importing Streamlit.
"""

import io
import logging
from datetime import datetime, timezone

import pandas as pd

import database as db
from attendance import (
    get_all_attendance,
    get_student_attendance_summary,
    get_session_attendance_counts,
)
from config import LOW_ATTENDANCE_THRESHOLD

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Dashboard summary metrics
# ---------------------------------------------------------------------------

def get_dashboard_metrics() -> dict:
    """
    Return a dict with top-level metrics for the dashboard:
        total_students, total_sessions, today_attendance,
        avg_attendance_pct, low_attendance_count
    """
    total_students = db.fetchone("SELECT COUNT(*) AS c FROM students")["c"]
    total_sessions = db.fetchone("SELECT COUNT(*) AS c FROM attendance_sessions")["c"]

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    today_attendance = db.fetchone(
        """
        SELECT COUNT(ar.id) AS c
        FROM attendance_records ar
        JOIN attendance_sessions sess ON sess.id = ar.session_id
        WHERE sess.session_date = ?
        """,
        (today,),
    )["c"]

    summaries = get_student_attendance_summary()
    if summaries:
        avg_pct = round(
            sum(s["attendance_pct"] for s in summaries) / len(summaries), 2
        )
    else:
        avg_pct = 0.0

    low_count = sum(
        1 for s in summaries
        if s["total_sessions"] > 0 and s["attendance_pct"] < LOW_ATTENDANCE_THRESHOLD
    )

    return {
        "total_students": total_students,
        "total_sessions": total_sessions,
        "today_attendance": today_attendance,
        "avg_attendance_pct": avg_pct,
        "low_attendance_count": low_count,
    }


# ---------------------------------------------------------------------------
# Chart data
# ---------------------------------------------------------------------------

def get_attendance_trend(days: int = 30) -> pd.DataFrame:
    """
    Return a DataFrame with columns [session_date, present_count] for the
    last *days* days, suitable for a line chart.
    """
    rows = db.fetchall(
        """
        SELECT sess.session_date, COUNT(ar.id) AS present_count
        FROM attendance_sessions sess
        LEFT JOIN attendance_records ar ON ar.session_id = sess.id
        WHERE sess.session_date >= date('now', ? || ' days')
        GROUP BY sess.session_date
        ORDER BY sess.session_date
        """,
        (f"-{days}",),
    )
    if not rows:
        return pd.DataFrame(columns=["session_date", "present_count"])
    return pd.DataFrame([dict(r) for r in rows])


def get_subject_attendance() -> pd.DataFrame:
    """
    Return a DataFrame with columns [subject, avg_pct] showing average
    attendance percentage per subject.
    """
    rows = db.fetchall(
        """
        SELECT
            sess.subject,
            COUNT(DISTINCT sess.id)  AS total_sessions,
            COUNT(ar.id)             AS total_present
        FROM attendance_sessions sess
        LEFT JOIN attendance_records ar ON ar.session_id = sess.id
        GROUP BY sess.subject
        ORDER BY sess.subject
        """
    )
    results = []
    for r in rows:
        d = dict(r)
        if d["total_sessions"] > 0:
            # Rough subject-level avg: present across all sessions / total capacity
            dept_students = db.fetchone(
                "SELECT COUNT(*) AS c FROM students s "
                "JOIN attendance_sessions sess ON sess.department = s.department "
                "WHERE sess.subject = ? LIMIT 1",
                (d["subject"],),
            )
            dept_c = dept_students["c"] if dept_students else 1
            avg = round(100.0 * d["total_present"] / max(d["total_sessions"] * (dept_c or 1), 1), 2)
        else:
            avg = 0.0
        results.append({"subject": d["subject"], "avg_pct": avg,
                         "total_sessions": d["total_sessions"], "total_present": d["total_present"]})
    return pd.DataFrame(results) if results else pd.DataFrame(
        columns=["subject", "avg_pct", "total_sessions", "total_present"]
    )


def get_present_absent_overview() -> pd.DataFrame:
    """
    Return a DataFrame with overall present vs absent totals across all sessions.
    """
    counts = get_session_attendance_counts()
    if not counts:
        return pd.DataFrame(columns=["label", "count"])
    total_present = sum(c["present_count"] for c in counts)
    total_absent  = sum(c["absent_count"]  for c in counts)
    return pd.DataFrame([
        {"label": "Present", "count": total_present},
        {"label": "Absent",  "count": total_absent},
    ])


def get_low_attendance_students(threshold: float = LOW_ATTENDANCE_THRESHOLD) -> list[dict]:
    """Return students whose attendance_pct is below *threshold*."""
    summaries = get_student_attendance_summary()
    return [
        s for s in summaries
        if s["total_sessions"] > 0 and s["attendance_pct"] < threshold
    ]


# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------

def export_attendance_csv(
    department: str = "",
    subject: str = "",
    from_date: str = "",
    to_date: str = "",
) -> bytes:
    """
    Build and return a CSV byte-string of filtered attendance records.
    Returns an empty CSV (headers only) when no records match.
    """
    records = get_all_attendance(
        department=department,
        subject=subject,
        from_date=from_date,
        to_date=to_date,
    )
    columns = [
        "roll_number", "full_name", "department",
        "subject", "session_date", "start_time", "recorded_at",
    ]
    if records:
        df = pd.DataFrame(records)[columns]
        # Rename to human-friendly headers
        df.columns = [
            "Roll Number", "Student Name", "Department",
            "Subject", "Session Date", "Session Start", "Marked At (UTC)",
        ]
    else:
        df = pd.DataFrame(columns=[
            "Roll Number", "Student Name", "Department",
            "Subject", "Session Date", "Session Start", "Marked At (UTC)",
        ])

    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue().encode("utf-8")


def export_student_summary_csv(threshold: float = LOW_ATTENDANCE_THRESHOLD) -> bytes:
    """Return a CSV byte-string of per-student attendance summaries."""
    summaries = get_student_attendance_summary()
    if summaries:
        df = pd.DataFrame(summaries)[[
            "roll_number", "full_name", "department",
            "total_sessions", "sessions_attended", "attendance_pct",
        ]]
        df.columns = [
            "Roll Number", "Student Name", "Department",
            "Total Sessions", "Sessions Attended", "Attendance %",
        ]
        df["Below Threshold"] = df["Attendance %"] < threshold
    else:
        df = pd.DataFrame(columns=[
            "Roll Number", "Student Name", "Department",
            "Total Sessions", "Sessions Attended", "Attendance %", "Below Threshold",
        ])

    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue().encode("utf-8")
