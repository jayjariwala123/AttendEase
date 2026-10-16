"""
ui_components.py — Reusable Streamlit UI building blocks for AttendEase.

Keeping visual components here prevents code duplication across pages and makes
the design easy to update in one place.
"""

import streamlit as st
from config import APP_NAME, APP_SUBTITLE, LOW_ATTENDANCE_THRESHOLD


# ---------------------------------------------------------------------------
# Page configuration (call once at the very top of app.py)
# ---------------------------------------------------------------------------

def setup_page():
    st.set_page_config(
        page_title=APP_NAME,
        page_icon="📋",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    _inject_css()


# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------

def _inject_css():
    st.markdown(
        """
        <style>
        /* ── Google Font ────────────────────────────────────────────── */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

        html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

        /* ── App background ─────────────────────────────────────────── */
        .stApp { background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); }

        /* ── Sidebar ────────────────────────────────────────────────── */
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0f172a 0%, #1e3a5f 100%) !important;
            border-right: 1px solid rgba(255,255,255,0.08);
        }
        section[data-testid="stSidebar"] * { color: #e2e8f0 !important; }

        /* ── Metric cards ───────────────────────────────────────────── */
        .metric-card {
            background: linear-gradient(135deg, #1e293b 0%, #243447 100%);
            border: 1px solid rgba(59,130,246,0.25);
            border-radius: 16px;
            padding: 1.5rem 1.8rem;
            text-align: center;
            box-shadow: 0 4px 24px rgba(0,0,0,0.3);
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .metric-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 8px 32px rgba(59,130,246,0.2);
        }
        .metric-value {
            font-size: 2.4rem;
            font-weight: 800;
            background: linear-gradient(90deg, #60a5fa, #38bdf8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .metric-label {
            font-size: 0.85rem;
            color: #94a3b8;
            margin-top: 0.3rem;
            font-weight: 500;
            letter-spacing: 0.05em;
            text-transform: uppercase;
        }
        .metric-icon { font-size: 1.8rem; margin-bottom: 0.5rem; }

        /* ── Section headers ────────────────────────────────────────── */
        .section-header {
            font-size: 1.4rem;
            font-weight: 700;
            color: #f1f5f9;
            border-left: 4px solid #3b82f6;
            padding-left: 0.75rem;
            margin: 1.5rem 0 1rem 0;
        }

        /* ── Page title ─────────────────────────────────────────────── */
        .page-title {
            font-size: 2rem;
            font-weight: 800;
            color: #f8fafc;
            margin-bottom: 0.25rem;
        }
        .page-subtitle {
            font-size: 0.95rem;
            color: #64748b;
            margin-bottom: 1.5rem;
        }

        /* ── Buttons ────────────────────────────────────────────────── */
        .stButton > button {
            background: linear-gradient(135deg, #2563eb, #1d4ed8);
            color: #fff !important;
            border: none;
            border-radius: 10px;
            font-weight: 600;
            padding: 0.5rem 1.5rem;
            transition: all 0.2s;
        }
        .stButton > button:hover {
            background: linear-gradient(135deg, #3b82f6, #2563eb);
            box-shadow: 0 4px 16px rgba(59,130,246,0.4);
            transform: translateY(-1px);
        }

        /* ── Inputs ─────────────────────────────────────────────────── */
        .stTextInput > div > div > input,
        .stSelectbox > div > div,
        .stDateInput > div > div > input,
        .stTimeInput > div > div > input {
            background: #1e293b !important;
            border: 1px solid rgba(59,130,246,0.3) !important;
            border-radius: 8px !important;
            color: #f1f5f9 !important;
        }
        .stTextInput > div > div > input:focus {
            border-color: #3b82f6 !important;
            box-shadow: 0 0 0 2px rgba(59,130,246,0.2) !important;
        }

        /* ── DataFrames / Tables ────────────────────────────────────── */
        .stDataFrame { border-radius: 12px; overflow: hidden; }

        /* ── Alert boxes ────────────────────────────────────────────── */
        .stAlert { border-radius: 10px; }

        /* ── Divider ────────────────────────────────────────────────── */
        hr { border-color: rgba(255,255,255,0.08) !important; }

        /* ── Form container ─────────────────────────────────────────── */
        .form-card {
            background: #1e293b;
            border: 1px solid rgba(59,130,246,0.2);
            border-radius: 16px;
            padding: 2rem;
            margin: 1rem 0;
        }

        /* ── Status badge ───────────────────────────────────────────── */
        .badge-active {
            background: rgba(34,197,94,0.15);
            color: #22c55e;
            border: 1px solid #22c55e;
            border-radius: 999px;
            padding: 2px 10px;
            font-size: 0.78rem;
            font-weight: 600;
        }
        .badge-closed {
            background: rgba(239,68,68,0.15);
            color: #ef4444;
            border: 1px solid #ef4444;
            border-radius: 999px;
            padding: 2px 10px;
            font-size: 0.78rem;
            font-weight: 600;
        }

        /* ── Low attendance warning ──────────────────────────────────── */
        .low-attendance {
            color: #f97316;
            font-weight: 700;
        }

        /* ── Login page ─────────────────────────────────────────────── */
        .login-container {
            max-width: 420px;
            margin: 4rem auto;
            background: linear-gradient(135deg, #1e293b, #243447);
            border: 1px solid rgba(59,130,246,0.25);
            border-radius: 20px;
            padding: 2.5rem;
            box-shadow: 0 20px 60px rgba(0,0,0,0.5);
        }
        .login-logo {
            text-align: center;
            font-size: 3rem;
            margin-bottom: 0.5rem;
        }
        .login-title {
            text-align: center;
            font-size: 1.6rem;
            font-weight: 800;
            color: #f1f5f9;
        }
        .login-subtitle {
            text-align: center;
            font-size: 0.85rem;
            color: #64748b;
            margin-bottom: 2rem;
        }

        /* ── QR card ────────────────────────────────────────────────── */
        .qr-card {
            background: white;
            border-radius: 16px;
            padding: 1rem;
            display: inline-block;
            box-shadow: 0 4px 24px rgba(0,0,0,0.4);
        }

        /* ── Scrollbar ──────────────────────────────────────────────── */
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: #0f172a; }
        ::-webkit-scrollbar-thumb { background: #334155; border-radius: 3px; }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Layout helpers
# ---------------------------------------------------------------------------

def page_header(title: str, subtitle: str = ""):
    st.markdown(f'<p class="page-title">{title}</p>', unsafe_allow_html=True)
    if subtitle:
        st.markdown(f'<p class="page-subtitle">{subtitle}</p>', unsafe_allow_html=True)


def section_header(text: str):
    st.markdown(f'<p class="section-header">{text}</p>', unsafe_allow_html=True)


def metric_card(icon: str, value, label: str):
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-icon">{icon}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-label">{label}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def status_badge(status: str) -> str:
    css = "badge-active" if status == "Active" else "badge-closed"
    return f'<span class="{css}">{status}</span>'


def render_sidebar(current_page: str) -> str:
    """
    Render the navigation sidebar.
    Returns the selected page name.
    """
    from auth import current_user

    with st.sidebar:
        st.markdown(
            """
            <div style="text-align:center; padding: 1rem 0;">
                <div style="font-size:2.5rem;">📋</div>
                <div style="font-size:1.3rem; font-weight:800; color:#f1f5f9;">AttendEase</div>
                <div style="font-size:0.75rem; color:#64748b; margin-top:0.2rem;">Smart Attendance Management</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.divider()

        pages = {
            "🏠 Dashboard": "dashboard",
            "👥 Students": "students",
            "📅 Sessions": "sessions",
            "✅ Attendance": "attendance",
            "📊 Reports": "reports",
            "⚙️ Settings": "settings",
        }

        selected = st.radio(
            "Navigation",
            list(pages.keys()),
            index=list(pages.values()).index(current_page) if current_page in pages.values() else 0,
            label_visibility="collapsed",
        )

        st.divider()

        user = current_user()
        if user:
            st.markdown(
                f"""
                <div style="text-align:center; padding:0.5rem 0;">
                    <div style="font-size:1.5rem;">👤</div>
                    <div style="font-size:0.85rem; color:#94a3b8;">Logged in as</div>
                    <div style="font-size:0.95rem; font-weight:600; color:#60a5fa;">{user}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("🚪 Logout", use_container_width=True, key="sidebar_logout"):
                from auth import logout
                logout()
                st.rerun()

    return pages[selected]


def empty_state(icon: str, message: str, hint: str = ""):
    st.markdown(
        f"""
        <div style="text-align:center; padding: 3rem; color:#475569;">
            <div style="font-size:3rem;">{icon}</div>
            <div style="font-size:1.1rem; font-weight:600; margin:0.5rem 0;">{message}</div>
            <div style="font-size:0.85rem; color:#334155;">{hint}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def confirm_dialog(key: str, label: str) -> bool:
    """
    Render a checkbox-style confirmation guard.
    Returns True only when the checkbox is checked.
    """
    return st.checkbox(f"✅ {label}", key=key)
