"""
init_sample_data.py — Inserts clearly labelled FICTIONAL demo records.

Run ONCE manually:
    python init_sample_data.py

The script checks for a sentinel value in the app_meta table and exits
without inserting anything if the data has already been loaded.

All names, roll numbers, and other data are invented for demonstration only.
"""

import sys
from datetime import date, time, timedelta, datetime, timezone

import database as db
from database import get_meta, set_meta
from student_management import add_student
from session_management import create_session, generate_qr_image, close_session
from attendance import mark_attendance, AttendanceError
from auth import ensure_default_admin
from config import SAMPLE_DATA_SENTINEL


def load_sample_data():
    db.init_db()
    ensure_default_admin()

    if get_meta(SAMPLE_DATA_SENTINEL):
        print("Sample data has already been loaded. Exiting.")
        sys.exit(0)

    print("Loading sample data…")

    # ── Students ──────────────────────────────────────────────────────────
    students_data = [
        ("CS001", "Aarav Mehta",     "Computer Science", "aarav@example.com"),
        ("CS002", "Priya Sharma",    "Computer Science", "priya@example.com"),
        ("CS003", "Rohan Patel",     "Computer Science", "rohan@example.com"),
        ("CS004", "Sneha Gupta",     "Computer Science", "sneha@example.com"),
        ("CS005", "Arjun Nair",      "Computer Science", "arjun@example.com"),
        ("CS006", "Kavya Reddy",     "Computer Science", "kavya@example.com"),
        ("CS007", "Vikram Singh",    "Computer Science", "vikram@example.com"),
        ("CS008", "Ananya Joshi",    "Computer Science", "ananya@example.com"),
        ("IT001", "Rahul Verma",     "Information Technology", "rahul@example.com"),
        ("IT002", "Pooja Desai",     "Information Technology", "pooja@example.com"),
        ("IT003", "Karan Malhotra",  "Information Technology", "karan@example.com"),
        ("IT004", "Neha Kapoor",     "Information Technology", "neha@example.com"),
        ("EC001", "Suresh Kumar",    "Electronics",     "suresh@example.com"),
        ("EC002", "Divya Krishnan",  "Electronics",     "divya@example.com"),
        ("EC003", "Amit Bose",       "Electronics",     "amit@example.com"),
    ]

    student_map = {}  # roll -> student dict
    for roll, name, dept, email in students_data:
        try:
            s = add_student(roll, name, dept, email)
            student_map[roll] = s
            print(f"  Added student: {roll} — {name}")
        except ValueError as e:
            print(f"  Skipped {roll}: {e}")

    # ── Sessions (past closed sessions + one active today) ─────────────────
    today = date.today()
    sessions_data = [
        # (dept, subject, date_offset, start, end, attendees_rolls)
        ("Computer Science", "Data Structures",  -6, time(9,0),  time(10,0),
         ["CS001","CS002","CS003","CS004","CS005","CS006"]),
        ("Computer Science", "Algorithms",        -5, time(10,0), time(11,0),
         ["CS001","CS002","CS004","CS005","CS007","CS008"]),
        ("Computer Science", "Database Systems",  -4, time(11,0), time(12,0),
         ["CS001","CS003","CS005","CS006","CS007","CS008"]),
        ("Computer Science", "Data Structures",   -3, time(9,0),  time(10,0),
         ["CS001","CS002","CS003","CS005","CS006","CS007","CS008"]),
        ("Computer Science", "Algorithms",        -2, time(10,0), time(11,0),
         ["CS001","CS002","CS003","CS004","CS005","CS006"]),
        ("Information Technology", "Web Dev",     -4, time(9,0),  time(10,0),
         ["IT001","IT002","IT003"]),
        ("Information Technology", "Web Dev",     -2, time(9,0),  time(10,0),
         ["IT001","IT002","IT003","IT004"]),
        ("Electronics", "Digital Circuits",       -3, time(11,0), time(12,0),
         ["EC001","EC002"]),
        ("Electronics", "Digital Circuits",       -1, time(11,0), time(12,0),
         ["EC001","EC002","EC003"]),
    ]

    for dept, subj, day_offset, start_t, end_t, attendees in sessions_data:
        sess_date = today + timedelta(days=day_offset)
        try:
            sess = create_session(
                department=dept,
                subject=subj,
                session_date=sess_date,
                start_time=start_t,
                expiry_time=end_t,
                created_by="admin",
            )
            # Generate QR
            try:
                generate_qr_image(sess["session_token"])
            except Exception as qr_e:
                print(f"  QR generation warning: {qr_e}")

            # Close past sessions so they don't interfere with active-check
            close_session(sess["id"])

            # Directly insert attendance records bypassing time window
            # (since these are historical records)
            for roll in attendees:
                stu = student_map.get(roll)
                if not stu:
                    continue
                try:
                    db.execute(
                        "INSERT OR IGNORE INTO attendance_records(session_id, student_id, recorded_at) "
                        "VALUES (?, ?, ?)",
                        (sess["id"], stu["id"],
                         datetime.combine(sess_date, start_t, tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
                    )
                except Exception as e:
                    print(f"  Attendance insert warning: {e}")

            print(f"  Added session: {dept} / {subj} on {sess_date}")
        except Exception as e:
            print(f"  Session error: {e}")

    # ── Today's active session for live demo ──────────────────────────────
    try:
        live_sess = create_session(
            department="Computer Science",
            subject="Operating Systems",
            session_date=today,
            start_time=time(0, 0),
            expiry_time=time(23, 59),
            created_by="admin",
        )
        try:
            generate_qr_image(live_sess["session_token"])
        except Exception:
            pass
        print(f"  Created LIVE demo session (token: {live_sess['session_token'][:12]}…)")
    except Exception as e:
        print(f"  Live session warning: {e}")

    # ── Mark sentinel ─────────────────────────────────────────────────────
    set_meta(SAMPLE_DATA_SENTINEL, "true")
    print("\n✅ Sample data loaded successfully.")
    print("   Run `streamlit run app.py` to start the application.")


if __name__ == "__main__":
    load_sample_data()
