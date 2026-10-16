
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
# All timestamps are stored in UTC and displayed in the configured timezone.
LOCAL_TIMEZONE = "Asia/Kolkata"  # IST — UTC+05:30

# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------
SESSION_KEY_USER = "authenticated_user"
MIN_PASSWORD_LENGTH = 6

# ---------------------------------------------------------------------------
# Attendance rules
# ---------------------------------------------------------------------------
LOW_ATTENDANCE_THRESHOLD = 75.0  # percent

# ---------------------------------------------------------------------------
# Application URL and QR code settings
# ---------------------------------------------------------------------------
# Set APP_BASE_URL in the environment to override this URL.
# Production: https://attendease-123.streamlit.app
# Local development: http://localhost:8501

APP_BASE_URL = os.getenv(
    "APP_BASE_URL",
    "https://attendease-123.streamlit.app"
).rstrip("/")

# Retain these constants for any existing local-development code.
QR_HOST = "localhost"
QR_PORT = 8501

# Use this base URL when generating attendance links and QR codes.
QR_BASE_URL = APP_BASE_URL

# ---------------------------------------------------------------------------
# Sample-data guard
# ---------------------------------------------------------------------------
SAMPLE_DATA_SENTINEL = "SAMPLE_DATA_LOADED_V1"
