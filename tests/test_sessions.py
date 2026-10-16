"""tests/test_sessions.py — Attendance session management tests."""

import pytest
from datetime import date, time, timedelta
import session_management as sm


def _make_session(**kwargs):
    defaults = dict(
        department="TestDept",
        subject="TestSubject",
        session_date=date.today(),
        start_time=time(0, 0),
        expiry_time=time(23, 59),
        created_by="admin",
    )
    defaults.update(kwargs)
    return sm.create_session(**defaults)


# ── Create ────────────────────────────────────────────────────────────────

def test_create_session_success():
    sess = _make_session()
    assert sess is not None
    assert sess["status"] == "Active"
    assert len(sess["session_token"]) > 10


def test_create_session_generates_unique_tokens():
    s1 = _make_session()
    s2 = _make_session()
    assert s1["session_token"] != s2["session_token"]


def test_create_session_expiry_before_start_raises():
    with pytest.raises(ValueError, match="Expiry time"):
        _make_session(start_time=time(11, 0), expiry_time=time(10, 0))


def test_create_session_missing_department_raises():
    with pytest.raises(ValueError, match="Department"):
        _make_session(department="")


def test_create_session_missing_subject_raises():
    with pytest.raises(ValueError, match="Subject"):
        _make_session(subject="")


# ── Read ──────────────────────────────────────────────────────────────────

def test_get_session_by_token():
    sess = _make_session(subject="ReadTest")
    found = sm.get_session_by_token(sess["session_token"])
    assert found is not None
    assert found["subject"] == "ReadTest"


def test_get_session_by_invalid_token():
    assert sm.get_session_by_token("nonexistent_token_xyz") is None


def test_get_all_sessions_returns_list():
    result = sm.get_all_sessions()
    assert isinstance(result, list)


# ── Status helpers ────────────────────────────────────────────────────────

def test_active_session_in_window_is_active():
    sess = _make_session(start_time=time(0, 0), expiry_time=time(23, 59))
    assert sm.is_session_active(sess) is True


def test_closed_session_is_not_active():
    sess = _make_session()
    sm.close_session(sess["id"])
    updated = sm.get_session_by_id(sess["id"])
    assert sm.is_session_active(updated) is False


def test_expired_session_is_not_active():
    """A session from yesterday should not be active today."""
    yesterday = date.today() - timedelta(days=1)
    sess = _make_session(session_date=yesterday, start_time=time(9,0), expiry_time=time(10,0))
    assert sm.is_session_active(sess) is False


# ── Close / Reopen ────────────────────────────────────────────────────────

def test_close_session():
    sess = _make_session()
    sm.close_session(sess["id"])
    updated = sm.get_session_by_id(sess["id"])
    assert updated["status"] == "Closed"


def test_reopen_session():
    sess = _make_session()
    sm.close_session(sess["id"])
    sm.reopen_session(sess["id"])
    updated = sm.get_session_by_id(sess["id"])
    assert updated["status"] == "Active"


# ── QR URL ────────────────────────────────────────────────────────────────

def test_build_attendance_url_contains_token():
    url = sm.build_attendance_url("abc123token")
    assert "abc123token" in url
    assert url.startswith("http")
