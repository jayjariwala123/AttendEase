"""tests/test_students.py — Student management unit tests."""

import pytest
import sqlite3
import student_management as sm


# ── Helpers ───────────────────────────────────────────────────────────────

def _unique_roll(prefix="TST"):
    import uuid
    return prefix + uuid.uuid4().hex[:4].upper()


# ── Create ────────────────────────────────────────────────────────────────

def test_add_student_success():
    roll = _unique_roll("ADD")
    stu = sm.add_student(roll, "Test Student", "Test Dept", "t@t.com")
    assert stu["roll_number"] == roll
    assert stu["full_name"] == "Test Student"
    assert stu["student_id"].startswith("STU-")


def test_add_student_missing_roll_raises():
    with pytest.raises(ValueError, match="Roll number"):
        sm.add_student("", "Name Here", "Dept")


def test_add_student_missing_name_raises():
    with pytest.raises(ValueError, match="Full name"):
        sm.add_student(_unique_roll(), "", "Dept")


def test_add_student_missing_dept_raises():
    with pytest.raises(ValueError, match="Department"):
        sm.add_student(_unique_roll(), "Name", "")


def test_duplicate_roll_raises():
    roll = _unique_roll("DUP")
    sm.add_student(roll, "First", "Dept")
    with pytest.raises(ValueError, match="Roll number"):
        sm.add_student(roll, "Second", "Dept")


# ── Read ──────────────────────────────────────────────────────────────────

def test_get_student_by_roll():
    roll = _unique_roll("GET")
    sm.add_student(roll, "Fetch Me", "FetchDept")
    stu = sm.get_student_by_roll(roll)
    assert stu is not None
    assert stu["full_name"] == "Fetch Me"


def test_get_student_by_roll_case_insensitive():
    roll = _unique_roll("CASE")
    sm.add_student(roll, "Case Test", "Dept")
    stu = sm.get_student_by_roll(roll.lower())
    assert stu is not None


def test_get_nonexistent_student():
    assert sm.get_student_by_roll("XXXX9999") is None


def test_get_all_students_returns_list():
    result = sm.get_all_students()
    assert isinstance(result, list)


def test_search_by_name():
    roll = _unique_roll("SRCH")
    sm.add_student(roll, "UniqueNameXYZ", "SearchDept")
    results = sm.get_all_students(search="UniqueNameXYZ")
    assert any(r["roll_number"] == roll for r in results)


def test_filter_by_department():
    roll = _unique_roll("FLT")
    sm.add_student(roll, "FilterStudent", "FilterDept999")
    results = sm.get_all_students(department="FilterDept999")
    assert all(r["department"] == "FilterDept999" for r in results)
    assert any(r["roll_number"] == roll for r in results)


# ── Update ────────────────────────────────────────────────────────────────

def test_update_student_success():
    roll = _unique_roll("UPD")
    stu = sm.add_student(roll, "Old Name", "OldDept")
    new_roll = _unique_roll("NEWROLL")
    sm.update_student(stu["id"], new_roll, "New Name", "NewDept", "new@email.com")
    updated = sm.get_student_by_roll(new_roll)
    assert updated["full_name"] == "New Name"


def test_update_duplicate_roll_raises():
    roll1 = _unique_roll("U1")
    roll2 = _unique_roll("U2")
    sm.add_student(roll1, "First",  "Dept")
    stu2 = sm.add_student(roll2, "Second", "Dept")
    with pytest.raises(ValueError, match="already used"):
        sm.update_student(stu2["id"], roll1, "Second", "Dept")


# ── Delete ────────────────────────────────────────────────────────────────

def test_delete_student_success():
    roll = _unique_roll("DEL")
    stu = sm.add_student(roll, "Delete Me", "DelDept")
    sm.delete_student(stu["id"])
    assert sm.get_student_by_roll(roll) is None


def test_delete_nonexistent_does_not_raise():
    """Deleting a non-existent PK should not raise."""
    sm.delete_student(999999)


def test_count_students():
    count = sm.count_students()
    assert isinstance(count, int)
    assert count >= 0
