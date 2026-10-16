"""tests/test_attendance.py — Attendance recording and validation tests."""

import pytest
from datetime import date, time, timedelta
import database as db
import student_management as sm
import session_management as sess_mgmt
from attendance import mark_attendance, AttendanceError, get_attendance_for_session


def _make_student(roll=None, dept="AttDept"):
    import uuid
    r = roll or ("ATT" + uuid.uuid4().hex[:4].upper())
    return sm.add_student(r, f"Student {r}", dept)


def _make_active_session(dept="AttDept"):
    return sess_mgmt.create_session(
        department=dept,
        subject="AttSubject",
        session_date=date.today(),
        start_time=time(0, 0),
        expiry_time=time(23, 59),
        created_by="admin",
    )


# ── Happy path ────────────────────────────────────────────────────────────

def test_mark_attendance_success():
    stu = _make_student()
    sess = _make_active_session()
    record = mark_attendance(sess["session_token"], stu["roll_number"])
    assert record["roll_number"] == stu["roll_number"]
    assert record["subject"] == "AttSubject"


# ── Invalid roll number ───────────────────────────────────────────────────

def test_invalid_roll_raises():
    sess = _make_active_session()
    with pytest.raises(AttendanceError, match="not registered"):
        mark_attendance(sess["session_token"], "NONEXISTENT_ROLL_XYZ")


# ── Invalid token ─────────────────────────────────────────────────────────

def test_invalid_token_raises():
    stu = _make_student()
    with pytest.raises(AttendanceError, match="Invalid or unknown"):
        mark_attendance("totally_fake_token_xxxx", stu["roll_number"])


# ── Duplicate attendance ──────────────────────────────────────────────────

def test_duplicate_attendance_raises():
    stu = _make_student()
    sess = _make_active_session()
    mark_attendance(sess["session_token"], stu["roll_number"])
    with pytest.raises(AttendanceError, match="already been recorded"):
        mark_attendance(sess["session_token"], stu["roll_number"])


# ── Closed session ────────────────────────────────────────────────────────

def test_closed_session_raises():
    stu = _make_student()
    sess = _make_active_session()
    sess_mgmt.close_session(sess["id"])
    with pytest.raises(AttendanceError, match="closed"):
        mark_attendance(sess["session_token"], stu["roll_number"])


# ── Expired session (yesterday) ───────────────────────────────────────────

def test_expired_session_raises():
    stu = _make_student()
    yesterday = date.today() - timedelta(days=1)
    expired = sess_mgmt.create_session(
        department="AttDept",
        subject="OldSubject",
        session_date=yesterday,
        start_time=time(9, 0),
        expiry_time=time(10, 0),
        created_by="admin",
    )
    with pytest.raises(AttendanceError, match="not currently active"):
        mark_attendance(expired["session_token"], stu["roll_number"])


# ── Get attendance for session ────────────────────────────────────────────

def test_get_attendance_for_session():
    stu1 = _make_student()
    stu2 = _make_student()
    sess = _make_active_session()
    mark_attendance(sess["session_token"], stu1["roll_number"])
    mark_attendance(sess["session_token"], stu2["roll_number"])
    records = get_attendance_for_session(sess["id"])
    rolls = [r["roll_number"] for r in records]
    assert stu1["roll_number"] in rolls
    assert stu2["roll_number"] in rolls


def test_get_attendance_empty_session():
    sess = _make_active_session()
    records = get_attendance_for_session(sess["id"])
    assert records == []
