"""tests/test_auth.py — Authentication unit tests."""

import pytest
import auth


def test_hash_and_verify():
    """Hashed password should verify correctly."""
    h = auth.hash_password("mypassword")
    assert auth.verify_password("mypassword", h) is True


def test_wrong_password_fails():
    h = auth.hash_password("correct")
    assert auth.verify_password("wrong", h) is False


def test_create_admin_success():
    ok = auth.create_admin("testadmin_auth", "testpass1", "Test Admin")
    assert ok is True


def test_create_admin_duplicate_fails():
    auth.create_admin("dup_admin", "pass123", "Dup")
    result = auth.create_admin("dup_admin", "pass123", "Dup")
    assert result is False


def test_create_admin_short_password_raises():
    with pytest.raises(ValueError, match="at least"):
        auth.create_admin("newadmin_short", "ab", "Short PW")


def test_verify_admin_correct():
    auth.create_admin("verify_test", "securepass", "Verify")
    assert auth.verify_admin("verify_test", "securepass") is True


def test_verify_admin_wrong_password():
    auth.create_admin("verify_test2", "correct_pw", "Verify2")
    assert auth.verify_admin("verify_test2", "wrong_pw") is False


def test_verify_admin_nonexistent():
    assert auth.verify_admin("nobody_here_xyz", "anypassword") is False


def test_get_admin_returns_no_hash():
    auth.create_admin("get_test", "password1", "Get Test")
    admin = auth.get_admin("get_test")
    assert admin is not None
    assert "password_hash" not in admin
    assert admin["username"] == "get_test"


def test_ensure_default_admin_idempotent():
    """Calling ensure_default_admin twice must not raise."""
    auth.ensure_default_admin()
    auth.ensure_default_admin()


def test_change_password():
    auth.create_admin("changepw_user", "oldpass1", "Change PW")
    auth.change_password("changepw_user", "newpass1")
    assert auth.verify_admin("changepw_user", "newpass1") is True
    assert auth.verify_admin("changepw_user", "oldpass1") is False
