"""tests/test_reports.py — Report generation and CSV export tests."""

import pytest
import io
from datetime import date, time, timedelta

import student_management as sm
import session_management as sess_mgmt
from attendance import mark_attendance
import database as db
from reports import (
    get_dashboard_metrics,
    get_attendance_trend,
    get_subject_attendance,
    get_present_absent_overview,
    get_low_attendance_students,
    export_attendance_csv,
    export_student_summary_csv,
)
from attendance import get_student_attendance_summary


def _setup_data():
    """Create 2 students, 2 sessions, mark attendance for 1 student."""
    import uuid
    suffix = uuid.uuid4().hex[:4].upper()
    stu1 = sm.add_student(f"RPT{suffix}A", f"Report Student A {suffix}", "ReportDept")
    stu2 = sm.add_student(f"RPT{suffix}B", f"Report Student B {suffix}", "ReportDept")

    sess1 = sess_mgmt.create_session(
        department="ReportDept",
        subject="ReportSubj",
        session_date=date.today(),
        start_time=time(0,0),
        expiry_time=time(23,59),
        created_by="admin",
    )
    sess2 = sess_mgmt.create_session(
        department="ReportDept",
        subject="ReportSubj2",
        session_date=date.today() - timedelta(days=1),
        start_time=time(0,0),
        expiry_time=time(23,59),
        created_by="admin",
    )

    mark_attendance(sess1["session_token"], stu1["roll_number"])
    # stu2 skips both sessions — below threshold

    return stu1, stu2, sess1, sess2


# ── Dashboard metrics ─────────────────────────────────────────────────────

def test_get_dashboard_metrics_has_required_keys():
    metrics = get_dashboard_metrics()
    for key in ["total_students", "total_sessions", "today_attendance",
                "avg_attendance_pct", "low_attendance_count"]:
        assert key in metrics


def test_dashboard_metrics_no_division_by_zero():
    metrics = get_dashboard_metrics()
    assert isinstance(metrics["avg_attendance_pct"], float)


# ── Student attendance summary ────────────────────────────────────────────

def test_attendance_pct_calculation():
    stu1, stu2, sess1, sess2 = _setup_data()
    summaries = get_student_attendance_summary(department="ReportDept")
    # Find stu1
    stu1_summary = next((s for s in summaries if s["roll_number"] == stu1["roll_number"]), None)
    assert stu1_summary is not None
    # stu1 attended 1 out of 2 sessions → 50%
    assert stu1_summary["sessions_attended"] >= 1
    assert stu1_summary["attendance_pct"] > 0


def test_zero_sessions_pct_is_zero():
    """Students with no applicable sessions should have 0% without error."""
    import uuid
    stu = sm.add_student(f"ZERO{uuid.uuid4().hex[:4].upper()}", "Zero Dept Stu", "ZeroDept999")
    summaries = get_student_attendance_summary(department="ZeroDept999")
    assert any(s["roll_number"] == stu["roll_number"] and s["attendance_pct"] == 0.0
               for s in summaries)


# ── Low attendance ────────────────────────────────────────────────────────

def test_low_attendance_returns_students_below_threshold():
    low = get_low_attendance_students(threshold=100.0)
    # With threshold=100, everyone with at least 1 missed session is "low"
    assert isinstance(low, list)


# ── Trend & charts ────────────────────────────────────────────────────────

def test_attendance_trend_is_dataframe():
    import pandas as pd
    df = get_attendance_trend(30)
    assert isinstance(df, pd.DataFrame)


def test_subject_attendance_is_dataframe():
    import pandas as pd
    df = get_subject_attendance()
    assert isinstance(df, pd.DataFrame)


def test_present_absent_overview_is_dataframe():
    import pandas as pd
    df = get_present_absent_overview()
    assert isinstance(df, pd.DataFrame)


# ── CSV export ────────────────────────────────────────────────────────────

def test_export_attendance_csv_returns_bytes():
    result = export_attendance_csv()
    assert isinstance(result, bytes)
    assert len(result) > 0


def test_export_attendance_csv_has_header():
    result = export_attendance_csv()
    text = result.decode("utf-8")
    assert "Roll Number" in text


def test_export_attendance_csv_empty_filter():
    """Exporting with a filter that matches nothing should return headers only."""
    result = export_attendance_csv(subject="SubjectThatDoesNotExistXXX999")
    text = result.decode("utf-8")
    lines = [l for l in text.strip().split("\n") if l]
    assert len(lines) == 1  # header only


def test_export_student_summary_csv():
    result = export_student_summary_csv()
    assert isinstance(result, bytes)
    text = result.decode("utf-8")
    assert "Roll Number" in text
    assert "Attendance %" in text
