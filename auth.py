"""
auth.py — Authentication helpers for AttendEase.

Responsibilities
----------------
* Hash and verify passwords using Werkzeug's PBKDF2-SHA256 implementation.
* Manage the Streamlit session-state login flag.
* Provide functions to create, fetch, and update administrator records.
* Enforce input validation rules.

Password storage
----------------
Passwords are NEVER stored in plain text.  The hash produced by
`werkzeug.security.generate_password_hash` encodes the algorithm, salt, and
digest so Werkzeug can verify it transparently in the future.
"""

import logging
from werkzeug.security import generate_password_hash, check_password_hash
import streamlit as st

import database as db
from config import SESSION_KEY_USER, MIN_PASSWORD_LENGTH

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Password utilities
# ---------------------------------------------------------------------------

def hash_password(plain: str) -> str:
    """Return a salted PBKDF2-SHA256 hash of *plain*."""
    return generate_password_hash(plain, method="pbkdf2:sha256", salt_length=16)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True when *plain* matches *hashed*."""
    return check_password_hash(hashed, plain)


# ---------------------------------------------------------------------------
# Administrator management
# ---------------------------------------------------------------------------

def admin_exists(username: str) -> bool:
    """Return True if *username* is present in the administrators table."""
    row = db.fetchone(
        "SELECT id FROM administrators WHERE username = ?", (username,)
    )
    return row is not None


def create_admin(username: str, plain_password: str, full_name: str = "") -> bool:
    """
    Create a new administrator.

    Returns True on success, False if the username already exists.
    Raises ValueError for invalid inputs.
    """
    username = username.strip()
    if not username:
        raise ValueError("Username cannot be empty.")
    if len(plain_password) < MIN_PASSWORD_LENGTH:
        raise ValueError(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
        )
    if admin_exists(username):
        return False

    pw_hash = hash_password(plain_password)
    db.execute(
        "INSERT INTO administrators(username, password_hash, full_name) VALUES (?, ?, ?)",
        (username, pw_hash, full_name.strip()),
    )
    logger.info("Administrator '%s' created.", username)
    return True


def verify_admin(username: str, plain_password: str) -> bool:
    """
    Return True when *username* exists and *plain_password* matches the stored hash.
    Does NOT raise — always returns bool.
    """
    row = db.fetchone(
        "SELECT password_hash FROM administrators WHERE username = ?",
        (username.strip(),),
    )
    if row is None:
        return False
    return verify_password(plain_password, row["password_hash"])


def change_password(username: str, new_plain: str) -> None:
    """Update the password hash for *username*. Raises ValueError for invalid input."""
    if len(new_plain) < MIN_PASSWORD_LENGTH:
        raise ValueError(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
        )
    pw_hash = hash_password(new_plain)
    db.execute(
        "UPDATE administrators SET password_hash = ? WHERE username = ?",
        (pw_hash, username),
    )
    logger.info("Password updated for '%s'.", username)


def get_admin(username: str) -> dict | None:
    """Return a dict with admin info (no password hash) or None."""
    row = db.fetchone(
        "SELECT id, username, full_name, created_at FROM administrators WHERE username = ?",
        (username,),
    )
    return dict(row) if row else None


def list_admins() -> list[dict]:
    """Return all admins (without password hashes)."""
    rows = db.fetchall(
        "SELECT id, username, full_name, created_at FROM administrators ORDER BY id"
    )
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Streamlit session-state helpers
# ---------------------------------------------------------------------------

def login(username: str) -> None:
    """Mark the user as authenticated in Streamlit session state."""
    st.session_state[SESSION_KEY_USER] = username


def logout() -> None:
    """Clear the authenticated user from Streamlit session state."""
    st.session_state.pop(SESSION_KEY_USER, None)


def current_user() -> str | None:
    """Return the currently authenticated username or None."""
    return st.session_state.get(SESSION_KEY_USER)


def is_authenticated() -> bool:
    """Return True if a user is currently logged in."""
    return current_user() is not None


def require_auth() -> None:
    """
    Stop the current Streamlit page if no user is logged in.
    Call this at the top of every protected page.
    """
    if not is_authenticated():
        st.error("🔒 Please log in to access this page.")
        st.stop()


# ---------------------------------------------------------------------------
# First-run initialisation
# ---------------------------------------------------------------------------

def ensure_default_admin() -> None:
    """
    Create the default administrator account if no admin accounts exist yet.

    Default credentials (change immediately after first login):
        Username : admin
        Password : admin123

    The password is hashed — it is NEVER stored in plain text.
    """
    rows = db.fetchall("SELECT id FROM administrators LIMIT 1")
    if not rows:
        create_admin("admin", "admin123", "Default Administrator")
        logger.warning(
            "Default admin created with username='admin' and password='admin123'. "
            "Change this password immediately after first login."
        )
