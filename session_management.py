
"""
session_management.py — Attendance session CRUD and QR-code generation.

Each attendance session has a unique random token embedded in the QR-code URL.
The token lets the student-facing form identify the session without exposing
internal database IDs.

Timezone handling
-----------------
* session_date is stored as a YYYY-MM-DD string in the local timezone.
* start_time / expiry_time are stored as HH:MM strings in the local timezone.
* created_at is stored as a UTC ISO-8601 string.
* Expiry is evaluated by comparing the current local time against expiry_time
  on the stored session_date.
"""

import logging
import secrets
import os
from datetime import datetime, date, time
from urllib.parse import urlencode

import qrcode
from PIL import Image

import database as db
from config import ASSETS_DIR, QR_BASE_URL, LOCAL_TIMEZONE

logger = logging.getLogger(__name__)

# Try to use zoneinfo (Python 3.9+), fall back to pytz.
try:
    from zoneinfo import ZoneInfo

    _TZ = ZoneInfo(LOCAL_TIMEZONE)

    def _local_now() -> datetime:
        return datetime.now(_TZ)

except ImportError:
    import pytz

    _TZ = pytz.timezone(LOCAL_TIMEZONE)

    def _local_now() -> datetime:
        return datetime.now(_TZ)


# ---------------------------------------------------------------------------
# Token + QR helpers
# ---------------------------------------------------------------------------

def _generate_token() -> str:
    """Return a cryptographically random URL-safe token."""
    return secrets.token_urlsafe(24)


def build_attendance_url(token: str) -> str:
    """
    Construct the attendance submission URL.

    Production:
        https://attendease-123.streamlit.app/?page=mark_attendance&token=...

    Local development can be configured using APP_BASE_URL in config.py
    or the APP_BASE_URL environment variable.
    """
    params = urlencode({
        "page": "mark_attendance",
        "token": token,
    })

    return f"{QR_BASE_URL}/?{params}"


def generate_qr_image(token: str) -> str:
    """
    Generate a QR-code PNG for the given token and save it to ASSETS_DIR.
    Returns the absolute file path of the saved image.
    """
    url = build_attendance_url(token)

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )

    qr.add_data(url)
    qr.make(fit=True)

    img: Image.Image = qr.make_image(
        fill_color="#1e3a5f",
        back_color="white",
    )

    filename = f"qr_{token[:12]}.png"
    filepath = os.path.join(ASSETS_DIR, filename)

    img.save(filepath)

    logger.info("QR code saved to %s", filepath)

    return filepath


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

def create_session(
    department: str,
    subject: str,
    session_date: date,
    start_time: time,
    expiry_time: time,
    created_by: str,
) -> dict:
    """
    Create an attendance session and return it as a dictionary.
    Raises ValueError on validation failures.
    """
    department = department.strip()
    subject = subject.strip()

    if not department:
        raise ValueError("Department is required.")

    if not subject:
        raise ValueError("Subject is required.")

    if expiry_time <= start_time:
        raise ValueError("Expiry time must be after start time.")

    token = _generate_token()

    # Collision guard.
    for _ in range(5):
        if not db.fetchone(
            "SELECT id FROM attendance_sessions WHERE session_token = ?",
            (token,),
        ):
            break

        token = _generate_token()

    db.execute(
        """
        INSERT INTO attendance_sessions
            (session_token, department, subject, session_date,
             start_time, expiry_time, status, created_by)
        VALUES (?, ?, ?, ?, ?, ?, 'Active', ?)
        """,
        (
            token,
            department,
            subject,
            session_date.isoformat(),
            start_time.strftime("%H:%M"),
            expiry_time.strftime("%H:%M"),
            created_by,
        ),
    )

    logger.info(
        "Session created: %s / %s on %s by %s",
        department,
        subject,
        session_date,
        created_by,
    )

    return get_session_by_token(token)


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------

def get_all_sessions(
    department: str = "",
    status: str = "",
) -> list[dict]:
    """Return sessions filtered by optional department and/or status."""
    conditions = []
    params: list = []

    if department:
        conditions.append("department = ?")
        params.append(department)

    if status:
        conditions.append("status = ?")
        params.append(status)

    where = "WHERE " + " AND ".join(conditions) if conditions else ""

    sql = f"""
        SELECT id, session_token, department, subject, session_date,
               start_time, expiry_time, status, created_by, created_at
        FROM attendance_sessions {where}
        ORDER BY session_date DESC, start_time DESC
    """

    return [dict(r) for r in db.fetchall(sql, tuple(params))]


def get_session_by_token(token: str) -> dict | None:
    """Return a session dictionary for the given token, or None."""
    row = db.fetchone(
        """
        SELECT id, session_token, department, subject, session_date,
               start_time, expiry_time, status, created_by, created_at
        FROM attendance_sessions
        WHERE session_token = ?
        """,
        (token,),
    )

    return dict(row) if row else None


def get_session_by_id(session_pk: int) -> dict | None:
    """Return a session dictionary for the given primary key, or None."""
    row = db.fetchone(
        """
        SELECT id, session_token, department, subject, session_date,
               start_time, expiry_time, status, created_by, created_at
        FROM attendance_sessions
        WHERE id = ?
        """,
        (session_pk,),
    )

    return dict(row) if row else None


def count_sessions() -> int:
    """Return the total number of sessions."""
    row = db.fetchone(
        "SELECT COUNT(*) AS cnt FROM attendance_sessions"
    )

    return row["cnt"] if row else 0


def get_todays_sessions() -> list[dict]:
    """Return sessions whose session_date is today in the local timezone."""
    today = _local_now().date().isoformat()

    rows = db.fetchall(
        """
        SELECT *
        FROM attendance_sessions
        WHERE session_date = ?
        ORDER BY start_time
        """,
        (today,),
    )

    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Status helpers
# ---------------------------------------------------------------------------

def is_session_active(session: dict) -> bool:
    """
    Return True when the session is Active and the current local time falls
    within the session's scheduled start and expiry times.
    """
    if session["status"] != "Active":
        return False

    now = _local_now()

    try:
        sess_date = date.fromisoformat(session["session_date"])

        exp_h, exp_m = map(
            int, session["expiry_time"].split(":")
        )

        start_h, start_m = map(
            int, session["start_time"].split(":")
        )

        session_start = datetime.combine(
            sess_date,
            time(start_h, start_m),
            tzinfo=_TZ,
        )

        session_expiry = datetime.combine(
            sess_date,
            time(exp_h, exp_m),
            tzinfo=_TZ,
        )

    except Exception:
        return False

    return session_start <= now <= session_expiry


# ---------------------------------------------------------------------------
# Update / Close
# ---------------------------------------------------------------------------

def close_session(session_pk: int) -> None:
    """Mark a session as Closed."""
    db.execute(
        "UPDATE attendance_sessions SET status = 'Closed' WHERE id = ?",
        (session_pk,),
    )

    logger.info("Session pk=%s closed.", session_pk)


def reopen_session(session_pk: int) -> None:
    """Reopen a Closed session (admin override)."""
    db.execute(
        "UPDATE attendance_sessions SET status = 'Active' WHERE id = ?",
        (session_pk,),
    )

    logger.info("Session pk=%s reopened.", session_pk)
