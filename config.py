"""
config.py — Application-wide configuration constants for AttendEase.

All tuneable values live here so the rest of the codebase stays free of
magic numbers and hard-coded strings.
"""

import os

# ---------------------------------------------------------------------------
# Application metadata
# ---------------------------------------------------------------------------
APP_NAME = "AttendEase"
APP_SUBTITLE = "Smart Attendance Management System"
APP_VERSION = "1.0.0"

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

# Ensure directories exist at import time (safe to call repeatedly)
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(ASSETS_DIR, exist_ok=True)

DATABASE_PATH = os.path.join(DATA_DIR, "attendease.db")

# ---------------------------------------------------------------------------
# Timezone
# ---------------------------------------------------------------------------
# The application stores all timestamps in UTC (ISO-8601 strings) and
# displays them in the LOCAL_TIMEZONE when presenting to the user.
# Change this value to match the server's location.
LOCAL_TIMEZONE = "Asia/Kolkata"  # IST — UTC+05:30

# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------
# Session state key used to store the logged-in admin's username.
SESSION_KEY_USER = "authenticated_user"
# Minimum password length enforced on the "change password" form.
MIN_PASSWORD_LENGTH = 6

# ---------------------------------------------------------------------------
# Attendance rules
# ---------------------------------------------------------------------------
# Students with an attendance percentage below this threshold are flagged.
LOW_ATTENDANCE_THRESHOLD = 75.0  # percent

# ---------------------------------------------------------------------------
# QR code settings
# ---------------------------------------------------------------------------
# The host shown inside the generated QR code URL.
# ‣ For local testing on the same machine, keep "localhost".
# ‣ For cross-device testing (phone on the same Wi-Fi), replace with the
#   host machine's LAN IP, e.g. "192.168.1.10".
# ‣ The port must match the --server.port passed to `streamlit run`.
QR_HOST = "localhost"
QR_PORT = 8501

# ---------------------------------------------------------------------------
# Sample-data guard
# ---------------------------------------------------------------------------
# The seeder (init_sample_data.py) writes this sentinel to the DB so it
# never inserts duplicate demo records on a second run.
SAMPLE_DATA_SENTINEL = "SAMPLE_DATA_LOADED_V1"
