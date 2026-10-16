"""
app.py — AttendEase main Streamlit application entry point.

Run with:
    streamlit run app.py

For cross-device QR scanning (phone on same Wi-Fi):
    streamlit run app.py --server.address 0.0.0.0 --server.port 8501
    Then set QR_HOST in config.py to this machine's LAN IP.
"""

import streamlit as st

# Bootstrap: ensure DB exists and default admin is created before any page loads
import database as db
import auth

db.init_db()
auth.ensure_default_admin()

# Page config MUST be the first Streamlit call
import ui_components as ui
ui.setup_page()

from config import APP_NAME


# ---------------------------------------------------------------------------
# Page router
# ---------------------------------------------------------------------------

def get_page() -> str:
    """Determine the current page from query params or session state."""
    params = st.query_params
    if "page" in params:
        return params["page"]
    return st.session_state.get("current_page", "dashboard")


def set_page(name: str):
    st.session_state["current_page"] = name
    st.query_params["page"] = name


# ---------------------------------------------------------------------------
# Public pages (no auth required)
# ---------------------------------------------------------------------------

def page_login():
    """Login page — shown when no user is authenticated."""
    st.markdown(
        """
        <div class="login-container">
            <div class="login-logo">📋</div>
            <div class="login-title">AttendEase</div>
            <div class="login-subtitle">Smart Attendance Management System</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_l, col_c, col_r = st.columns([1, 1.2, 1])
    with col_c:
        with st.form("login_form"):
            st.markdown("### 🔐 Administrator Login")
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            submitted = st.form_submit_button("Login", use_container_width=True)

        if submitted:
            if not username or not password:
                st.error("Please enter both username and password.")
            elif auth.verify_admin(username, password):
                auth.login(username)
                st.success(f"Welcome back, {username}!")
                st.rerun()
            else:
                st.error("❌ Invalid username or password.")

        st.markdown(
            """
            <div style="text-align:center; margin-top:1.5rem; font-size:0.78rem; color:#475569;">
                Default credentials: <code>admin</code> / <code>admin123</code><br>
                Change your password immediately after first login.
            </div>
            """,
            unsafe_allow_html=True,
        )


def page_mark_attendance():
    """
    Public student-facing attendance submission form.
    Accessible via QR code URL: /?page=mark_attendance&token=XXX
    """
    st.markdown(
        """
        <div style="max-width:480px; margin: 2rem auto; text-align:center;">
            <div style="font-size:2.5rem;">📋</div>
            <h2 style="color:#f1f5f9;">Mark Your Attendance</h2>
            <p style="color:#94a3b8;">Enter your roll number to record your attendance.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    params = st.query_params
    token = params.get("token", "")

    if not token:
        st.error("⚠️ No session token in URL. Please scan the QR code again.")
        return

    from session_management import get_session_by_token, is_session_active
    session = get_session_by_token(token)

    if session is None:
        st.error("❌ Invalid or unknown attendance session.")
        return

    col_l, col_c, col_r = st.columns([1, 2, 1])
    with col_c:
        st.info(
            f"**Session:** {session['subject']}  \n"
            f"**Department:** {session['department']}  \n"
            f"**Date:** {session['session_date']}  \n"
            f"**Time:** {session['start_time']} – {session['expiry_time']}"
        )

        if session["status"] == "Closed":
            st.error("🔒 This session has been closed by the teacher.")
            return

        if not is_session_active(session):
            st.warning("⏰ This session is not currently active (may have expired or not yet started).")
            return

        with st.form("attendance_form"):
            roll = st.text_input(
                "Roll Number",
                placeholder="e.g. CS001",
                help="Enter the roll number as registered in the system.",
            ).strip().upper()
            submitted = st.form_submit_button("✅ Submit Attendance", use_container_width=True)

        if submitted:
            if not roll:
                st.error("Please enter your roll number.")
            else:
                from attendance import mark_attendance, AttendanceError
                try:
                    record = mark_attendance(token, roll)
                    st.success(
                        f"✅ **Attendance recorded successfully!**\n\n"
                        f"**Student:** {record['student_name']}  \n"
                        f"**Roll:** {record['roll_number']}  \n"
                        f"**Subject:** {record['subject']}  \n"
                        f"**Time:** {record['recorded_at']} UTC"
                    )
                    st.balloons()
                except AttendanceError as e:
                    st.error(f"❌ {e}")


# ---------------------------------------------------------------------------
# Protected pages
# ---------------------------------------------------------------------------

def page_dashboard():
    import plotly.express as px
    import pandas as pd
    from reports import (
        get_dashboard_metrics,
        get_attendance_trend,
        get_subject_attendance,
        get_present_absent_overview,
        get_low_attendance_students,
    )
    from config import LOW_ATTENDANCE_THRESHOLD

    ui.page_header("🏠 Dashboard", "Overview of attendance activity")
    metrics = get_dashboard_metrics()

    # ── Metric cards ─────────────────────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        ui.metric_card("👥", metrics["total_students"], "Total Students")
    with c2:
        ui.metric_card("📅", metrics["total_sessions"], "Total Sessions")
    with c3:
        ui.metric_card("✅", metrics["today_attendance"], "Today's Attendance")
    with c4:
        ui.metric_card("📈", f"{metrics['avg_attendance_pct']}%", "Avg Attendance")
    with c5:
        ui.metric_card("⚠️", metrics["low_attendance_count"], f"Below {LOW_ATTENDANCE_THRESHOLD}%")

    st.divider()

    # ── Charts row ───────────────────────────────────────────────────────
    col_left, col_right = st.columns([2, 1])

    with col_left:
        ui.section_header("📈 Attendance Trend (Last 30 Days)")
        trend_df = get_attendance_trend(30)
        if trend_df.empty:
            ui.empty_state("📊", "No attendance data yet", "Create sessions and record attendance to see trends.")
        else:
            fig = px.line(
                trend_df, x="session_date", y="present_count",
                markers=True,
                template="plotly_dark",
                color_discrete_sequence=["#3b82f6"],
                labels={"session_date": "Date", "present_count": "Students Present"},
            )
            fig.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font_color="#94a3b8",
                margin=dict(l=0, r=0, t=20, b=0),
            )
            st.plotly_chart(fig, use_container_width=True)

    with col_right:
        ui.section_header("🟢 Present vs Absent")
        pva = get_present_absent_overview()
        if pva.empty or pva["count"].sum() == 0:
            ui.empty_state("📊", "No data yet", "")
        else:
            fig2 = px.pie(
                pva, names="label", values="count",
                color="label",
                color_discrete_map={"Present": "#22c55e", "Absent": "#ef4444"},
                hole=0.45,
                template="plotly_dark",
            )
            fig2.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font_color="#94a3b8",
                margin=dict(l=0, r=0, t=20, b=0),
                legend=dict(orientation="h", yanchor="bottom", y=-0.2),
            )
            st.plotly_chart(fig2, use_container_width=True)

    # ── Subject-wise attendance ──────────────────────────────────────────
    ui.section_header("📚 Subject-wise Attendance")
    subj_df = get_subject_attendance()
    if subj_df.empty:
        ui.empty_state("📚", "No subject data yet", "")
    else:
        fig3 = px.bar(
            subj_df, x="subject", y="total_present",
            template="plotly_dark",
            color_discrete_sequence=["#6366f1"],
            labels={"subject": "Subject", "total_present": "Total Present"},
            text_auto=True,
        )
        fig3.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="#94a3b8",
            margin=dict(l=0, r=0, t=20, b=0),
        )
        st.plotly_chart(fig3, use_container_width=True)

    # ── Low attendance table ─────────────────────────────────────────────
    ui.section_header(f"⚠️ Students Below {LOW_ATTENDANCE_THRESHOLD}% Attendance")
    low_list = get_low_attendance_students(LOW_ATTENDANCE_THRESHOLD)
    if not low_list:
        st.success("✅ All students are above the attendance threshold.")
    else:
        import pandas as pd
        low_df = pd.DataFrame(low_list)[[
            "roll_number", "full_name", "department",
            "total_sessions", "sessions_attended", "attendance_pct"
        ]]
        low_df.columns = ["Roll No.", "Name", "Department", "Total Sessions", "Attended", "Attendance %"]
        st.dataframe(
            low_df.style.applymap(
                lambda v: "color: #f97316; font-weight: bold;"
                if isinstance(v, (int, float)) and v < LOW_ATTENDANCE_THRESHOLD else "",
                subset=["Attendance %"],
            ),
            use_container_width=True,
            hide_index=True,
        )


def page_students():
    import sqlite3
    from student_management import (
        add_student, get_all_students, update_student,
        delete_student, get_departments, count_students,
        get_student_by_id
    )
    import pandas as pd

    ui.page_header("👥 Student Management", "Add, edit, search, and manage student records")

    tab_list, tab_add = st.tabs(["📋 All Students", "➕ Add Student"])

    # ── Tab: All students ─────────────────────────────────────────────────
    with tab_list:
        col_search, col_dept, col_count = st.columns([3, 2, 1])
        with col_search:
            search = st.text_input("🔍 Search by name or roll number", key="stu_search")
        with col_dept:
            depts = ["All Departments"] + get_departments()
            dept_filter = st.selectbox("Department", depts, key="stu_dept")
        with col_count:
            st.metric("Total Students", count_students())

        dept_q = "" if dept_filter == "All Departments" else dept_filter
        students = get_all_students(department=dept_q, search=search)

        if not students:
            ui.empty_state("👥", "No students found", "Add students using the 'Add Student' tab.")
        else:
            df = pd.DataFrame(students)[[
                "student_id", "roll_number", "full_name", "department", "email", "registered_at"
            ]]
            df.columns = ["Student ID", "Roll No.", "Full Name", "Department", "Email", "Registered At"]
            st.dataframe(df, use_container_width=True, hide_index=True)

            st.divider()
            ui.section_header("✏️ Edit / Delete Student")
            student_options = {
                f"{s['roll_number']} — {s['full_name']}": s["id"] for s in students
            }
            chosen = st.selectbox("Select student to edit/delete", list(student_options.keys()), key="stu_select")
            if chosen:
                pk = student_options[chosen]
                stu = get_student_by_id(pk)
                if stu:
                    with st.form("edit_student_form"):
                        c1, c2 = st.columns(2)
                        with c1:
                            new_roll = st.text_input("Roll Number *", value=stu["roll_number"])
                            new_name = st.text_input("Full Name *", value=stu["full_name"])
                        with c2:
                            new_dept = st.text_input("Department *", value=stu["department"])
                            new_email = st.text_input("Email", value=stu.get("email", ""))

                        col_save, col_del = st.columns(2)
                        with col_save:
                            save = st.form_submit_button("💾 Save Changes", use_container_width=True)
                        with col_del:
                            delete = st.form_submit_button("🗑️ Delete Student", use_container_width=True)

                    if save:
                        try:
                            update_student(pk, new_roll, new_name, new_dept, new_email)
                            st.success("✅ Student updated successfully.")
                            st.rerun()
                        except ValueError as e:
                            st.error(f"❌ {e}")

                    if delete:
                        try:
                            delete_student(pk)
                            st.success("🗑️ Student deleted.")
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error(
                                "❌ Cannot delete this student — they have existing attendance records. "
                                "Delete the attendance records first, or deactivate the student instead."
                            )

    # ── Tab: Add student ──────────────────────────────────────────────────
    with tab_add:
        with st.form("add_student_form"):
            st.markdown("### ➕ Register New Student")
            c1, c2 = st.columns(2)
            with c1:
                roll   = st.text_input("Roll Number *", placeholder="e.g. CS001")
                name   = st.text_input("Full Name *",   placeholder="e.g. Priya Sharma")
            with c2:
                dept   = st.text_input("Department *", placeholder="e.g. Computer Science")
                email  = st.text_input("Email (optional)", placeholder="student@college.edu")

            submitted = st.form_submit_button("➕ Add Student", use_container_width=True)

        if submitted:
            try:
                stu = add_student(roll, name, dept, email)
                st.success(
                    f"✅ Student **{stu['full_name']}** registered with ID `{stu['student_id']}`."
                )
            except ValueError as e:
                st.error(f"❌ {e}")


def page_sessions():
    import os
    from datetime import date, time, timedelta
    from session_management import (
        create_session, get_all_sessions, close_session,
        reopen_session, generate_qr_image, build_attendance_url,
        get_session_by_id,
    )
    from attendance import get_attendance_for_session
    from student_management import get_departments
    import pandas as pd

    ui.page_header("📅 Session Management", "Create and manage attendance sessions")

    tab_list, tab_create = st.tabs(["📋 All Sessions", "➕ Create Session"])

    # ── Tab: All sessions ─────────────────────────────────────────────────
    with tab_list:
        col_dept, col_status = st.columns(2)
        with col_dept:
            depts_all = ["All Departments"] + get_departments()
            dept_f = st.selectbox("Filter by Department", depts_all, key="sess_dept")
        with col_status:
            status_f = st.selectbox("Filter by Status", ["All", "Active", "Closed"], key="sess_status")

        d_q  = "" if dept_f   == "All Departments" else dept_f
        s_q  = "" if status_f == "All"             else status_f
        sessions = get_all_sessions(department=d_q, status=s_q)

        if not sessions:
            ui.empty_state("📅", "No sessions found", "Create a session using the 'Create Session' tab.")
        else:
            for sess in sessions:
                with st.expander(
                    f"📅 {sess['session_date']}  |  {sess['subject']}  —  {sess['department']}  "
                    f"[{sess['status']}]",
                    expanded=False,
                ):
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.markdown(f"**Subject:** {sess['subject']}")
                        st.markdown(f"**Department:** {sess['department']}")
                        st.markdown(f"**Date:** {sess['session_date']}")
                    with c2:
                        st.markdown(f"**Start:** {sess['start_time']}")
                        st.markdown(f"**Expiry:** {sess['expiry_time']}")
                        st.markdown(f"**Status:** {sess['status']}")
                    with c3:
                        st.markdown(f"**Created by:** {sess['created_by']}")
                        st.markdown(f"**Token:** `{sess['session_token'][:12]}…`")

                    # QR code
                    qr_path = os.path.join(
                        "assets", f"qr_{sess['session_token'][:12]}.png"
                    )
                    if os.path.exists(qr_path):
                        col_qr, col_url = st.columns([1, 2])
                        with col_qr:
                            st.image(qr_path, width=200, caption="Scan to mark attendance")
                        with col_url:
                            url = build_attendance_url(sess["session_token"])
                            st.markdown(f"**Attendance URL:**")
                            st.code(url)
                            st.markdown(
                                "_Students on the same network can open this URL or scan the QR code._"
                            )
                    else:
                        st.warning("QR image not found. Regenerating…")
                        try:
                            generate_qr_image(sess["session_token"])
                            st.rerun()
                        except Exception as e:
                            st.error(f"Could not generate QR: {e}")

                    # Control buttons
                    btn_col1, btn_col2 = st.columns(2)
                    with btn_col1:
                        if sess["status"] == "Active":
                            if st.button("🔒 Close Session", key=f"close_{sess['id']}"):
                                close_session(sess["id"])
                                st.success("Session closed.")
                                st.rerun()
                        else:
                            if st.button("🔓 Reopen Session", key=f"open_{sess['id']}"):
                                reopen_session(sess["id"])
                                st.success("Session reopened.")
                                st.rerun()

                    # Attendance records for this session
                    with btn_col2:
                        if st.button("👁️ View Attendance", key=f"view_{sess['id']}"):
                            st.session_state[f"show_att_{sess['id']}"] = True

                    if st.session_state.get(f"show_att_{sess['id']}", False):
                        records = get_attendance_for_session(sess["id"])
                        if not records:
                            st.info("No attendance records yet for this session.")
                        else:
                            rdf = pd.DataFrame(records)[[
                                "roll_number", "full_name", "department", "recorded_at"
                            ]]
                            rdf.columns = ["Roll No.", "Name", "Department", "Marked At (UTC)"]
                            st.dataframe(rdf, use_container_width=True, hide_index=True)
                            st.caption(f"Total present: **{len(records)}**")

    # ── Tab: Create session ───────────────────────────────────────────────
    with tab_create:
        with st.form("create_session_form"):
            st.markdown("### ➕ New Attendance Session")
            c1, c2 = st.columns(2)
            with c1:
                dept  = st.text_input("Department *", placeholder="e.g. Computer Science")
                subj  = st.text_input("Subject *",    placeholder="e.g. Data Structures")
            with c2:
                today = date.today()
                sess_date  = st.date_input("Session Date *", value=today)
                start_time = st.time_input("Start Time *",  value=time(9, 0))
                expiry_time = st.time_input("Expiry Time *", value=time(10, 0))

            submitted = st.form_submit_button("🚀 Create Session & Generate QR", use_container_width=True)

        if submitted:
            if not dept or not subj:
                st.error("Department and Subject are required.")
            elif expiry_time <= start_time:
                st.error("Expiry time must be after start time.")
            else:
                try:
                    sess = create_session(
                        department=dept,
                        subject=subj,
                        session_date=sess_date,
                        start_time=start_time,
                        expiry_time=expiry_time,
                        created_by=auth.current_user(),
                    )
                    qr_path = generate_qr_image(sess["session_token"])
                    st.success(f"✅ Session created! Token: `{sess['session_token'][:16]}…`")

                    col_qr, col_info = st.columns([1, 2])
                    with col_qr:
                        st.image(qr_path, width=250, caption="Scan to mark attendance")
                    with col_info:
                        url = build_attendance_url(sess["session_token"])
                        st.markdown("**Attendance URL (for manual entry):**")
                        st.code(url)
                        st.info(
                            "💡 Share this QR code or URL with students.  \n"
                            "For cross-device access, set `QR_HOST` in `config.py` to your LAN IP "
                            "and run: `streamlit run app.py --server.address 0.0.0.0`"
                        )
                    st.rerun()
                except ValueError as e:
                    st.error(f"❌ {e}")
                except Exception as e:
                    st.error(f"❌ Unexpected error: {e}")


def page_attendance():
    from attendance import get_all_attendance
    from student_management import get_departments
    import pandas as pd

    ui.page_header("✅ Attendance Records", "Browse and search all attendance entries")

    # Filters
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        depts_all = ["All Departments"] + get_departments()
        dept_f = st.selectbox("Department", depts_all, key="att_dept")
    with col2:
        subj_f = st.text_input("Subject", key="att_subj", placeholder="Filter by subject")
    with col3:
        from_d = st.date_input("From Date", value=None, key="att_from")
    with col4:
        to_d = st.date_input("To Date",   value=None, key="att_to")

    d_q = "" if dept_f == "All Departments" else dept_f
    from_s = from_d.isoformat() if from_d else ""
    to_s   = to_d.isoformat()   if to_d   else ""

    records = get_all_attendance(
        department=d_q, subject=subj_f, from_date=from_s, to_date=to_s
    )

    if not records:
        ui.empty_state("✅", "No attendance records match the current filters", "")
    else:
        df = pd.DataFrame(records)[[
            "roll_number", "full_name", "department",
            "subject", "session_date", "start_time", "recorded_at"
        ]]
        df.columns = [
            "Roll No.", "Name", "Department",
            "Subject", "Session Date", "Start Time", "Marked At (UTC)"
        ]
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.caption(f"Showing **{len(records)}** records")

        # CSV export
        from reports import export_attendance_csv
        csv_bytes = export_attendance_csv(
            department=d_q, subject=subj_f, from_date=from_s, to_date=to_s
        )
        st.download_button(
            "⬇️ Export to CSV",
            data=csv_bytes,
            file_name="attendance_records.csv",
            mime="text/csv",
        )


def page_reports():
    import plotly.express as px
    import pandas as pd
    from reports import (
        get_student_attendance_summary,
        get_session_attendance_counts,
        export_student_summary_csv,
        export_attendance_csv,
    )
    from student_management import get_departments
    from config import LOW_ATTENDANCE_THRESHOLD

    ui.page_header("📊 Reports & Analytics", "Detailed attendance analytics and exports")

    tab_student, tab_session, tab_export = st.tabs([
        "👤 Per-Student Report", "📅 Per-Session Report", "⬇️ Export"
    ])

    # ── Per-student ───────────────────────────────────────────────────────
    with tab_student:
        col_dept, col_thresh = st.columns(2)
        with col_dept:
            depts_all = ["All Departments"] + get_departments()
            dept_f = st.selectbox("Department", depts_all, key="rpt_dept")
        with col_thresh:
            threshold = st.slider(
                "Low Attendance Threshold (%)", 50, 95,
                int(LOW_ATTENDANCE_THRESHOLD), key="rpt_thresh"
            )

        d_q = "" if dept_f == "All Departments" else dept_f
        summaries = get_student_attendance_summary(department=d_q)

        if not summaries:
            ui.empty_state("👤", "No student data yet", "")
        else:
            df = pd.DataFrame(summaries)
            df_display = df[[
                "roll_number", "full_name", "department",
                "total_sessions", "sessions_attended", "attendance_pct"
            ]].copy()
            df_display.columns = ["Roll No.", "Name", "Department", "Total", "Attended", "Att. %"]
            df_display["Status"] = df_display["Att. %"].apply(
                lambda x: "⚠️ Low" if x < threshold else "✅ OK"
            )

            st.dataframe(df_display, use_container_width=True, hide_index=True)

            # Attendance distribution chart
            ui.section_header("📊 Attendance Distribution")
            fig = px.histogram(
                df, x="attendance_pct", nbins=20,
                template="plotly_dark",
                color_discrete_sequence=["#3b82f6"],
                labels={"attendance_pct": "Attendance %", "count": "Students"},
                title="Student Attendance Distribution",
            )
            fig.add_vline(
                x=threshold, line_dash="dash", line_color="#ef4444",
                annotation_text=f"Threshold ({threshold}%)",
                annotation_position="top right"
            )
            fig.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font_color="#94a3b8",
            )
            st.plotly_chart(fig, use_container_width=True)

    # ── Per-session ───────────────────────────────────────────────────────
    with tab_session:
        counts = get_session_attendance_counts()
        if not counts:
            ui.empty_state("📅", "No session data yet", "")
        else:
            df_s = pd.DataFrame(counts)[[
                "session_date", "subject", "department",
                "present_count", "absent_count", "status"
            ]]
            df_s.columns = ["Date", "Subject", "Department", "Present", "Absent", "Status"]
            st.dataframe(df_s, use_container_width=True, hide_index=True)

            ui.section_header("📊 Present vs Absent per Session")
            df_melt = pd.melt(
                df_s.assign(Session=df_s["Date"] + " | " + df_s["Subject"]),
                id_vars="Session", value_vars=["Present", "Absent"],
                var_name="Status_", value_name="Count"
            )
            fig2 = px.bar(
                df_melt, x="Session", y="Count", color="Status_",
                barmode="group",
                template="plotly_dark",
                color_discrete_map={"Present": "#22c55e", "Absent": "#ef4444"},
            )
            fig2.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font_color="#94a3b8",
                xaxis_tickangle=-30,
            )
            st.plotly_chart(fig2, use_container_width=True)

    # ── Export ────────────────────────────────────────────────────────────
    with tab_export:
        ui.section_header("⬇️ Export Reports")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Student Attendance Summary**")
            thresh2 = st.slider("Threshold for 'Below' flag", 50, 95, int(LOW_ATTENDANCE_THRESHOLD), key="exp_thresh")
            summary_csv = export_student_summary_csv(thresh2)
            st.download_button(
                "⬇️ Download Student Summary CSV",
                data=summary_csv,
                file_name="student_attendance_summary.csv",
                mime="text/csv",
            )

        with col2:
            st.markdown("**Filtered Attendance Records**")
            dept_exp = st.text_input("Department (leave blank for all)", key="exp_dept")
            subj_exp = st.text_input("Subject (leave blank for all)", key="exp_subj")
            from_exp = st.date_input("From Date", value=None, key="exp_from")
            to_exp   = st.date_input("To Date",   value=None, key="exp_to")
            att_csv = export_attendance_csv(
                department=dept_exp,
                subject=subj_exp,
                from_date=from_exp.isoformat() if from_exp else "",
                to_date=to_exp.isoformat()   if to_exp   else "",
            )
            st.download_button(
                "⬇️ Download Attendance Records CSV",
                data=att_csv,
                file_name="attendance_records.csv",
                mime="text/csv",
            )


def page_settings():
    from auth import change_password, current_user, list_admins, create_admin

    ui.page_header("⚙️ Settings", "Manage administrator accounts and application settings")

    tab_pw, tab_admin, tab_about = st.tabs(["🔑 Change Password", "👤 Admin Accounts", "ℹ️ About"])

    with tab_pw:
        user = current_user()
        with st.form("change_pw_form"):
            st.markdown(f"### Change password for **{user}**")
            new_pw  = st.text_input("New Password", type="password")
            new_pw2 = st.text_input("Confirm New Password", type="password")
            submitted = st.form_submit_button("Update Password", use_container_width=True)
        if submitted:
            if not new_pw or not new_pw2:
                st.error("Please fill in both fields.")
            elif new_pw != new_pw2:
                st.error("Passwords do not match.")
            else:
                try:
                    change_password(user, new_pw)
                    st.success("✅ Password updated. Please log in again.")
                    from auth import logout
                    logout()
                    st.rerun()
                except ValueError as e:
                    st.error(f"❌ {e}")

    with tab_admin:
        ui.section_header("Current Administrators")
        admins = list_admins()
        import pandas as pd
        df_admins = pd.DataFrame(admins)[["id", "username", "full_name", "created_at"]]
        df_admins.columns = ["ID", "Username", "Full Name", "Created At"]
        st.dataframe(df_admins, use_container_width=True, hide_index=True)

        st.divider()
        ui.section_header("Add New Administrator")
        with st.form("add_admin_form"):
            new_uname = st.text_input("Username")
            new_fname = st.text_input("Full Name")
            new_pass  = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Add Admin", use_container_width=True)
        if submitted:
            try:
                ok = create_admin(new_uname, new_pass, new_fname)
                if ok:
                    st.success(f"✅ Administrator '{new_uname}' created.")
                else:
                    st.error(f"Username '{new_uname}' already exists.")
            except ValueError as e:
                st.error(f"❌ {e}")

    with tab_about:
        from config import APP_NAME, APP_SUBTITLE, APP_VERSION
        st.markdown(
            f"""
            ## {APP_NAME}
            **{APP_SUBTITLE}**

            | | |
            |---|---|
            | **Version** | {APP_VERSION} |
            | **Database** | SQLite (attendease.db) |
            | **Framework** | Streamlit |
            | **Language** | Python 3 |
            | **Timezone** | Asia/Kolkata (IST) |

            ### ⚠️ Security Notice
            This is a prototype system. QR code attendance records the roll number entered by the student but does **not** verify physical presence or identity. Additional authentication (biometric, college ID scan, etc.) would be required in a production system.

            ### 📚 Default Credentials
            Username: `admin` | Password: `admin123`  
            **Change immediately after first login.**
            """
        )


# ---------------------------------------------------------------------------
# Main routing logic
# ---------------------------------------------------------------------------

def main():
    # Handle the public mark-attendance page (QR scan target)
    params = st.query_params
    if params.get("page") == "mark_attendance":
        page_mark_attendance()
        return

    # Everything else requires authentication
    if not auth.is_authenticated():
        page_login()
        return

    # Authenticated: render sidebar and route to the selected page
    current_page = st.session_state.get("current_page", "dashboard")
    selected = ui.render_sidebar(current_page)

    page_map = {
        "dashboard":  page_dashboard,
        "students":   page_students,
        "sessions":   page_sessions,
        "attendance": page_attendance,
        "reports":    page_reports,
        "settings":   page_settings,
    }

    st.session_state["current_page"] = selected
    page_fn = page_map.get(selected, page_dashboard)
    page_fn()


if __name__ == "__main__":
    main()
