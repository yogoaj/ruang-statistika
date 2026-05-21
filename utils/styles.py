"""
utils/styles.py — Ruang Statistika v4.9
CSS terpusat, dipecah per concern untuk performa optimal.

Penggunaan di app.py:
    from utils.styles import inject_global_css, inject_login_css, inject_nav_highlight_css
    inject_global_css()          # sekali saat startup
    inject_login_css()           # hanya saat belum login
    inject_nav_highlight_css(active_idx)  # tiap rerun sidebar (ringan)
"""
from __future__ import annotations
import streamlit as st

# ── Design tokens ─────────────────────────────────────────────────────────────
NAVY    = "#0c2340"
NAVY2   = "#0f2d52"
BLUE    = "#185FA5"
BLUE2   = "#378add"
BLUE3   = "#1e73c8"
LIGHT   = "#b5d4f4"
MUTED   = "#7aabda"
MUTED2  = "#4a7aaa"
MUTED3  = "#2d5a87"
GREEN   = "#3b6d11"
GREEN2  = "#639922"
RED     = "#a32d2d"
INDIGO  = "#6366f1"
VIOLET  = "#8b5cf6"
AMBER   = "#ba7517"
BORDER  = "#d0e4f7"
BG_SOFT = "#f0f6ff"
BG_AI   = "#f0f4ff"
WHITE   = "#ffffff"


# ─────────────────────────────────────────────────────────────────────────────
# 1. GLOBAL CSS  — di-cache, hanya build sekali per sesi
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def _global_css() -> str:
    return f"""<style>
/* ── Font ── */
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:wght@300;400;500;600&display=swap');
html, body, [class*="css"] {{ font-family:'DM Sans',sans-serif; }}

/* ── Sidebar toggle: sembunyikan saat belum login ── */
body:not(.rs-logged-in) [data-testid="collapsedControl"],
body:not(.rs-logged-in) [data-testid="stSidebarCollapsedControl"] {{ display:none !important; }}

/* ══ SIDEBAR ════════════════════════════════════════════════════════════════ */
[data-testid="stSidebar"] {{
    background: {NAVY} !important;
    border-right: 1px solid rgba(255,255,255,.06) !important;
}}
[data-testid="stSidebar"] * {{ color: {MUTED} !important; }}
[data-testid="stSidebar"] .stMarkdown h1,
[data-testid="stSidebar"] .stMarkdown h2,
[data-testid="stSidebar"] .stMarkdown h3 {{ color: {WHITE} !important; }}

/* Group label */
.nav-group-label {{
    font-size:.6rem; font-weight:700; letter-spacing:.1em;
    text-transform:uppercase; color:{MUTED3} !important;
    padding:10px 4px 3px; margin-top:4px; display:block;
}}

/* Nav buttons */
[data-testid="stSidebar"] .stButton > button {{
    background: transparent !important; border: none !important;
    color: {MUTED} !important; text-align: left !important;
    padding: 5px 12px !important; border-radius: 0 !important;
    border-left: 2px solid transparent !important;
    font-size: .79rem !important; width: 100% !important;
    font-weight: 400 !important; margin: 0 !important;
    line-height: 1.4 !important; min-height: 0 !important;
    height: auto !important; transition: background .12s, color .12s !important;
}}
[data-testid="stSidebar"] .stButton > button:hover {{
    background: rgba(255,255,255,.05) !important;
    color: {LIGHT} !important;
    border-left-color: rgba(55,138,221,.3) !important;
}}
[data-testid="stSidebar"] .stButton > button:focus {{
    box-shadow: none !important; outline: none !important;
}}
[data-testid="stSidebar"] .stButton {{ margin-bottom:0 !important; margin-top:0 !important; }}
[data-testid="stSidebar"] .element-container {{ margin-bottom:0 !important; margin-top:0 !important; }}
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {{ gap:0 !important; }}

/* ══ KOMPONEN BERSAMA ════════════════════════════════════════════════════════ */

/* Hero header */
.rs-header {{
    background: linear-gradient(135deg, {NAVY} 0%, {BLUE} 100%);
    padding: 1.5rem 2rem; border-radius: 12px;
    margin-bottom: 1.25rem; position: relative; overflow: hidden;
    display: flex; align-items: center; gap: 20px;
}}
.rs-header::after {{
    content:''; position:absolute; right:-50px; top:-50px;
    width:180px; height:180px; border-radius:50%;
    background:rgba(255,255,255,.04); pointer-events:none;
}}
.rs-header-icon {{
    background: rgba(255,255,255,.1); border-radius:12px;
    width:56px; height:56px; display:flex; align-items:center;
    justify-content:center; flex-shrink:0; position:relative; z-index:1;
    font-size:28px; color:{WHITE};
}}
.rs-header h1 {{
    font-family:'DM Serif Display',serif;
    font-size:1.8rem; color:{WHITE}; margin:0 0 .2rem;
    position:relative; z-index:1;
}}
.rs-header p {{ color:#85b7eb; font-size:.82rem; margin:0; position:relative; z-index:1; }}
.rs-logo-link {{ text-decoration:none; color:{BLUE2} !important; font-size:.8rem; }}

/* Greeting bar */
.rs-greeting {{
    background: {NAVY}; border-radius:10px;
    padding:12px 18px; display:flex; align-items:center;
    justify-content:space-between; margin-bottom:14px;
}}
.rs-greeting-text {{ font-size:.92rem; color:{WHITE}; font-weight:600; }}
.rs-greeting-sub  {{ font-size:.75rem; color:{MUTED}; margin-top:1px; }}
.rs-greeting-badge {{
    background:rgba(255,255,255,.1); border-radius:6px;
    padding:4px 12px; font-size:.72rem; color:{LIGHT};
}}

/* Metric card */
.rs-metric {{
    background: var(--background-color, #f7faff);
    border: .5px solid {BORDER}; border-radius:8px;
    padding:12px 14px; text-align:center;
}}
.rs-metric-label {{
    font-size:.65rem; color:#5f8ab5; text-transform:uppercase;
    letter-spacing:.06em; margin-bottom:5px;
}}
.rs-metric-value {{ font-size:1.5rem; font-weight:600; color:{NAVY}; }}
.rs-metric-sub   {{ font-size:.65rem; color:{GREEN}; margin-top:2px; }}

/* Step card — 2 col layout */
.rs-step {{
    background: var(--background-color, #f7faff);
    border: .5px solid {BORDER}; border-radius:8px;
    padding:10px 12px; display:flex; align-items:flex-start; gap:10px;
}}
.rs-step-num {{
    background:{BLUE}; color:{WHITE};
    width:24px; height:24px; border-radius:50%;
    display:flex; align-items:center; justify-content:center;
    font-weight:600; font-size:.7rem; flex-shrink:0;
}}

/* Narasi / AI */
.rs-narasi {{
    background:#e6f1fb; border-left:3px solid {BLUE};
    border-radius:0 8px 8px 0; padding:.9rem 1.1rem;
    font-size:.88rem; color:{NAVY}; line-height:1.65; margin-top:.5rem;
}}
.rs-ai-narasi {{
    background: linear-gradient(135deg, {BG_AI} 0%, #e8f0fe 100%);
    border-left: 3px solid {INDIGO}; border-radius:0 8px 8px 0;
    padding:.9rem 1.1rem; font-size:.88rem; color:#1e1b4b;
    line-height:1.7; margin-top:.5rem;
}}
.rs-ai-badge {{
    display:inline-flex; align-items:center; gap:5px;
    background:linear-gradient(90deg,{INDIGO},{VIOLET});
    color:{WHITE}; font-size:.66rem; font-weight:600;
    letter-spacing:.06em; padding:2px 10px; border-radius:20px;
    margin-bottom:8px;
}}

/* Section typography */
.rs-section-title {{
    font-family:'DM Serif Display',serif; font-size:1.3rem;
    color:{NAVY}; margin-bottom:.2rem;
}}
.rs-section-sub {{ font-size:.8rem; color:#5f8ab5; margin-bottom:.9rem; }}

/* Badges */
.badge-valid     {{ background:#eaf3de; color:{GREEN};  padding:2px 10px; border-radius:20px; font-size:.75rem; font-weight:500; }}
.badge-invalid   {{ background:#fcebeb; color:{RED};    padding:2px 10px; border-radius:20px; font-size:.75rem; font-weight:500; }}
.badge-reliable  {{ background:#eaf3de; color:{GREEN};  padding:3px 12px; border-radius:20px; font-size:.8rem;  font-weight:600; }}
.badge-unreliable{{ background:#fcebeb; color:{RED};    padding:3px 12px; border-radius:20px; font-size:.8rem;  font-weight:600; }}
.pro-badge {{
    background:linear-gradient(90deg,{BLUE},{NAVY});
    color:{WHITE}; padding:3px 12px; border-radius:20px;
    font-size:.72rem; font-weight:600; letter-spacing:.04em;
}}
.pro-lock-badge {{
    background:linear-gradient(90deg,{INDIGO},{VIOLET});
    color:{WHITE}; padding:2px 8px; border-radius:10px;
    font-size:.62rem; font-weight:600; letter-spacing:.04em;
    margin-left:4px; vertical-align:middle;
}}

/* CTA wizard block */
.rs-cta-wizard {{
    background:#eef2ff; border:1px solid #c7d2fe;
    border-radius:10px; padding:14px 16px;
    display:grid; grid-template-columns:1fr auto; gap:16px; align-items:center;
}}
.rs-cta-title {{ font-size:.9rem; font-weight:600; color:#3730a3; margin-bottom:3px; }}
.rs-cta-desc  {{ font-size:.78rem; color:#4338ca; line-height:1.45; }}

/* Chat bubbles */
.chat-container {{
    max-height:420px; overflow-y:auto; padding:.5rem;
    background:#f7faff; border:.5px solid {BORDER};
    border-radius:10px; margin-bottom:1rem;
}}
.chat-bubble-user {{
    background:{BLUE}; color:{WHITE}; padding:.55rem .95rem;
    border-radius:14px 14px 3px 14px;
    margin:.4rem 0 .4rem 20%; font-size:.86rem; line-height:1.5;
}}
.chat-bubble-ai {{
    background:{WHITE}; border:.5px solid {BORDER}; color:{NAVY};
    padding:.55rem .95rem; border-radius:14px 14px 14px 3px;
    margin:.4rem 20% .4rem 0; font-size:.86rem; line-height:1.6;
}}
.chat-label {{ font-size:.68rem; color:#5f8ab5; margin-bottom:2px; letter-spacing:.04em; }}

/* Footer */
.rs-footer {{
    margin-top:3rem; padding-top:1.25rem;
    border-top:.5px solid #e0eaf5; text-align:center;
    font-size:.78rem; color:#999;
}}
.rs-footer a {{ color:{BLUE}; text-decoration:none; }}
.rs-footer a:hover {{ text-decoration:underline; }}
</style>"""


def inject_global_css() -> None:
    """Inject CSS global. Konten di-cache — aman dipanggil tiap rerun."""
    st.markdown(_global_css(), unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# 2. LOGIN CSS  — hanya diload saat halaman login
# ─────────────────────────────────────────────────────────────────────────────

_LOGIN_CSS: str = f"""<style>
.rs-footer {{ display:none; }}
header[data-testid="stHeader"] {{ display:none; }}
[data-testid="stSidebar"],
[data-testid="collapsedControl"],
[data-testid="stSidebarCollapsedControl"] {{ display:none !important; }}

[data-testid="stAppViewContainer"],
[data-testid="stApp"] {{
    background:linear-gradient(135deg,{NAVY} 0%,{NAVY2} 50%,{BLUE} 100%) !important;
}}
section[data-testid="stMain"] .block-container {{
    padding-top:5vh !important; max-width:440px !important;
    margin:0 auto !important;
    padding-left:1rem !important; padding-right:1rem !important;
    padding-bottom:3rem !important;
}}

/* Kartu */
.signin-card {{
    background:rgba(255,255,255,.09); backdrop-filter:blur(20px);
    -webkit-backdrop-filter:blur(20px);
    border:1px solid rgba(255,255,255,.14); border-radius:16px;
    overflow:hidden; box-shadow:0 8px 32px rgba(0,0,0,.3);
    width:100%; max-width:420px;
}}
.signin-card-header {{
    background:linear-gradient(135deg,{NAVY} 0%,{BLUE} 65%,{BLUE3} 100%);
    padding:22px 22px 18px; text-align:center;
    position:relative; overflow:hidden;
}}
.signin-card-header::before {{
    content:''; position:absolute; right:-40px; top:-40px;
    width:150px; height:150px; border-radius:50%;
    background:rgba(255,255,255,.05); pointer-events:none;
}}
.signin-card-header::after {{
    content:''; position:absolute; left:-25px; bottom:-40px;
    width:120px; height:120px; border-radius:50%;
    background:rgba(255,255,255,.04); pointer-events:none;
}}
.signin-header-logo {{
    position:relative; z-index:1; margin-bottom:10px;
    width:52px; height:52px; border-radius:12px;
    background:rgba(255,255,255,.1);
    display:flex; align-items:center; justify-content:center; margin:0 auto 10px;
}}
.signin-header-logo img {{
    width:34px; height:34px; object-fit:contain;
    filter:drop-shadow(0 2px 8px rgba(0,0,0,.2));
}}
.signin-header-title {{
    font-family:'DM Serif Display',serif; font-size:1.4rem;
    color:{WHITE}; letter-spacing:-.2px;
    position:relative; z-index:1; margin:0 0 4px;
}}
.signin-header-sub {{ font-size:.72rem; color:#85b7eb; position:relative; z-index:1; }}

/* Tab strip */
.signin-tab-row {{
    display:flex; border-bottom:1px solid rgba(255,255,255,.12);
    margin-bottom:1.2rem; gap:0;
}}
.signin-tab-row .stButton {{ flex:1; }}
.signin-tab-row .stButton > button {{
    background:transparent !important; border:none !important;
    border-bottom:2.5px solid transparent !important; border-radius:0 !important;
    color:rgba(255,255,255,.45) !important; font-size:.82rem !important;
    font-weight:500 !important; padding:8px 4px !important;
    width:100% !important; margin-bottom:-1px !important;
    transition:color .15s,border-color .15s !important;
}}
.signin-tab-row .stButton > button:hover {{
    color:rgba(255,255,255,.88) !important; background:transparent !important;
}}
.signin-tab-active .stButton > button {{
    color:{WHITE} !important; font-weight:700 !important;
    border-bottom-color:#F5B800 !important;
}}

/* Inputs */
section[data-testid="stMain"] .stTextInput label {{
    font-size:.72rem !important; font-weight:600 !important;
    color:rgba(255,255,255,.72) !important; margin-bottom:4px !important;
}}
section[data-testid="stMain"] .stTextInput input {{
    border:1.5px solid rgba(255,255,255,.22) !important;
    border-radius:8px !important; padding:9px 12px !important;
    font-size:.85rem !important;
    background:rgba(255,255,255,.11) !important;
    color:{NAVY} !important; -webkit-text-fill-color:{NAVY} !important;
    transition:border-color .15s,box-shadow .15s !important;
}}
section[data-testid="stMain"] .stTextInput input:focus {{
    border-color:rgba(255,255,255,.48) !important;
    background:rgba(255,255,255,.17) !important;
    box-shadow:0 0 0 3px rgba(255,255,255,.07) !important;
}}
section[data-testid="stMain"] .stTextInput input::placeholder {{
    color:rgba(255,255,255,.35) !important;
    -webkit-text-fill-color:rgba(255,255,255,.35) !important;
}}

/* Submit button */
section[data-testid="stMain"] .stForm [data-testid="stFormSubmitButton"] > button {{
    background:linear-gradient(135deg,{NAVY} 0%,{BLUE} 100%) !important;
    color:{WHITE} !important; border:none !important;
    border-radius:8px !important; padding:11px !important;
    font-size:.88rem !important; font-weight:600 !important;
    width:100% !important;
    transition:opacity .15s,box-shadow .15s !important;
    box-shadow:0 4px 14px rgba(24,95,165,.28) !important;
}}
section[data-testid="stMain"] .stForm [data-testid="stFormSubmitButton"] > button:hover {{
    opacity:.92 !important;
    box-shadow:0 6px 18px rgba(24,95,165,.36) !important;
}}

/* CTA Coba Gratis */
section[data-testid="stMain"] .stButton > button {{
    background:rgba(255,255,255,.09) !important;
    border:1.5px solid rgba(255,255,255,.22) !important;
    border-radius:8px !important; color:{WHITE} !important;
    font-size:.82rem !important; font-weight:600 !important;
    padding:8px !important; width:100% !important;
    transition:background .15s,border-color .15s !important;
}}
section[data-testid="stMain"] .stButton > button:hover {{
    background:rgba(255,255,255,.16) !important;
    border-color:rgba(255,255,255,.42) !important;
}}

/* Link buttons */
.signin-link-btn-right {{ text-align:right; margin-top:-2px; margin-bottom:6px; }}
.signin-link-btn-right .stButton > button {{
    background:transparent !important; border:none !important;
    color:{BLUE2} !important; font-size:.72rem !important;
    font-weight:500 !important; padding:0 !important;
    height:auto !important; min-height:0 !important; width:auto !important; float:right;
}}
.signin-link-btn-right .stButton > button:hover {{
    background:transparent !important; text-decoration:underline !important;
}}
.signin-link-btn .stButton > button {{
    background:transparent !important; border:none !important;
    color:{BLUE2} !important; font-size:.72rem !important; font-weight:600 !important;
    padding:2px 6px !important; height:auto !important; min-height:0 !important;
}}
.signin-link-btn .stButton > button:hover {{
    background:transparent !important; text-decoration:underline !important;
}}
.signin-link-btn-muted .stButton > button {{
    color:#7aa8cc !important; font-weight:400 !important; font-size:.7rem !important;
}}

/* Divider */
.signin-divider {{
    text-align:center; font-size:.7rem; color:rgba(255,255,255,.3);
    margin:8px 0; position:relative;
}}
.signin-divider::before,.signin-divider::after {{
    content:''; position:absolute; top:50%;
    width:38%; height:1px; background:rgba(255,255,255,.12);
}}
.signin-divider::before {{ left:0; }}
.signin-divider::after  {{ right:0; }}

/* Footer */
.signin-footer {{
    text-align:center; margin-top:10px;
    font-size:.72rem; color:#8aabcc;
}}
.signin-footer a {{ color:{BLUE2}; font-weight:600; text-decoration:none; }}
.signin-footer a:hover {{ text-decoration:underline; }}
.signin-page-footer {{
    text-align:center; margin-top:1.2rem;
    font-size:.7rem; color:#9ab5cc; line-height:1.7;
}}
.signin-page-footer a {{ color:{BLUE2}; text-decoration:none; font-weight:500; }}
.forgot-link {{ text-align:right; margin:-4px 0 10px; font-size:.72rem; }}
.forgot-link a {{ color:{BLUE2}; text-decoration:none; }}
.forgot-link a:hover {{ text-decoration:underline; }}
.activate-link {{ text-align:center; margin-top:8px; font-size:.7rem; color:#a0bcd8; }}
.activate-link a {{ color:#7aa8cc; text-decoration:none; }}
.activate-link a:hover {{ text-decoration:underline; }}
</style>"""


def inject_login_css() -> None:
    """Inject CSS halaman login. Panggil hanya saat belum login."""
    st.markdown(_LOGIN_CSS, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# 3. NAV HIGHLIGHT  — ringan ~15 baris, dipanggil tiap sidebar render
# ─────────────────────────────────────────────────────────────────────────────

def inject_nav_highlight_css(active_idx: int) -> None:
    """
    Highlight tombol nav aktif.
    Left-border accent + background — lebih 'pro' dari highlight kotak penuh.
    active_idx: indeks 0-based item dalam flat list menu.
    """
    st.markdown(f"""<style>
[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]
    > div:nth-child({active_idx + 1}) .stButton > button,
[data-testid="stSidebar"] div[data-testid="stVerticalBlockBorderWrapper"]
    > div:nth-child({active_idx + 1}) .stButton > button {{
    background: rgba(24,95,165,.25) !important;
    color: {WHITE} !important;
    font-weight: 500 !important;
    border-left-color: {BLUE2} !important;
}}
</style>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# 4. NAV LOCKED  — sidebar dikunci saat belum login
# ─────────────────────────────────────────────────────────────────────────────

_NAV_LOCKED_CSS: str = f"""<style>
[data-testid="stSidebar"] .stButton > button {{
    opacity: .28 !important;
    pointer-events: none !important;
    cursor: not-allowed !important;
}}
</style>
<div style='text-align:center;margin-top:8px;padding:6px 12px;
            background:rgba(12,35,64,.55);border-radius:8px;
            font-size:.7rem;color:{MUTED2};line-height:1.5;'>
    🔒 Selesaikan langkah awal<br>di halaman utama dulu
</div>"""


def inject_nav_locked_css() -> None:
    st.markdown(_NAV_LOCKED_CSS, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# 5. HELPER — render komponen beranda (greeting + header)
#    Dipindah dari app.py agar app.py tetap bersih dari inline HTML panjang.
# ─────────────────────────────────────────────────────────────────────────────

def render_greeting(user_name: str, is_pro: bool) -> None:
    """Render greeting bar. user_name boleh kosong (mode gratis)."""
    import datetime as _dt
    hour = _dt.datetime.now().hour
    salam = (
        "Selamat pagi"   if hour < 11 else
        "Selamat siang"  if hour < 15 else
        "Selamat sore"   if hour < 18 else
        "Selamat malam"
    )
    tier_badge = (
        "<span style='background:linear-gradient(90deg,#185FA5,#0c2340);"
        "color:#fff;font-size:.6rem;font-weight:600;letter-spacing:.04em;"
        "padding:2px 8px;border-radius:8px;margin-left:5px;'>PRO</span>"
        if is_pro else
        "<span style='background:rgba(255,255,255,.1);color:#85b7eb;"
        "font-size:.6rem;padding:2px 8px;border-radius:8px;margin-left:5px;'>GRATIS</span>"
    )
    # Fallback: mode gratis tanpa nama
    display_name = user_name if user_name else "Pengguna"
    greeting_text = f"{salam}, {display_name}! 👋" if user_name else f"{salam}! 👋"
    st.markdown(
        f"<div class='rs-greeting'>"
        f"<div>"
        f"<div class='rs-greeting-text'>{greeting_text}</div>"
        f"<div class='rs-greeting-sub'>Siap membantu analisis statistik Anda hari ini.</div>"
        f"</div>"
        f"<div class='rs-greeting-badge'>{tier_badge}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )


def render_hero_header() -> None:
    """Render hero header Ruang Statistika dengan ikon."""
    st.markdown("""
<div class="rs-header">
    <div class="rs-header-icon"><img src="https://i.imgur.com/RF4mzxf.png" width="36" height="36" style="object-fit:contain;filter:drop-shadow(0 2px 6px rgba(0,0,0,.2));" alt="Ruang Statistika logo"></div>
    <div>
        <h1 style="margin:0;font-size:1.8rem;">Ruang Statistika</h1>
        <p style="margin:0;opacity:.85;">
            AI-Powered Research &amp; Stats Reporting —
            Data Anda Berbicara, AI Menjelaskan
        </p>
    </div>
</div>""", unsafe_allow_html=True)


def render_metrics_row() -> None:
    """Render 4 metric card di baris atas beranda."""
    metrics = [
        ("Modul Analisis", "30+",  "Statistik lengkap"),
        ("AI Interpreter", "8×",   "Groq · Gemini · Claude"),
        ("Chat Analyst",   "💬",   "Tanya jawab data"),
        ("Export Laporan", "📄",   "Word / Markdown"),
    ]
    cols = st.columns(4)
    for col, (label, val, sub) in zip(cols, metrics):
        with col:
            st.markdown(
                f'<div class="rs-metric">'
                f'<div class="rs-metric-label">{label}</div>'
                f'<div class="rs-metric-value">{val}</div>'
                f'<div class="rs-metric-sub">{sub}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )


def render_steps_grid() -> None:
    """Render 5 langkah cara pakai dalam 2-col grid."""
    steps = [
        ("Wizard Analisis",       "Panduan 3 langkah pilih uji yang tepat"),
        ("Upload & Cleaning",     "CSV, Excel, SPSS, Stata — auto-bersihkan"),
        ("Compute (Opsional)",    "Skor komposit, recode, transformasi"),
        ("Jalankan Analisis",     "Modul terbuka otomatis dari Wizard"),
        ("Generate Laporan",      "Export .docx / .md — satu klik"),
    ]
    cols = st.columns(2)
    for i, (title, desc) in enumerate(steps, 1):
        with cols[(i - 1) % 2]:
            st.markdown(
                f'<div class="rs-step">'
                f'<div class="rs-step-num">{i}</div>'
                f'<div>'
                f'<div style="font-weight:500;color:#0c2340;font-size:.85rem;">{title}</div>'
                f'<div style="font-size:.76rem;color:#5f8ab5;margin-top:2px;line-height:1.4;">{desc}</div>'
                f'</div></div>',
                unsafe_allow_html=True,
            )


def render_cta_wizard(on_click_key: str = "cta_wizard_btn") -> bool:
    """
    Render CTA Wizard block. Return True jika tombol diklik.
    Contoh pemakaian:
        if render_cta_wizard():
            st.session_state.active_menu = "Wizard"
            st.rerun()
    """
    st.markdown(
        '<div class="rs-cta-wizard">'
        '<div class="rs-cta-title">🧭 Bingung pilih uji statistik?</div>'
        '<div class="rs-cta-desc">Jawab 3 pertanyaan singkat — Wizard akan '
        'merekomendasikan uji yang tepat dan langsung membuka modulnya.</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    return st.button(
        "🚀 Mulai Wizard",
        key=on_click_key,
        type="primary",
        use_container_width=True,
    )


def render_changelog() -> None:
    """Render changelog versi sebagai rs-ai-narasi yang lebih ringkas."""
    st.markdown("""
<div class="rs-ai-narasi">
<span class="rs-ai-badge">✨ v4.8 — Supabase Auth + Google OAuth</span><br/>
<b>v4.3:</b> Login berbasis nama pengguna &amp; nama peneliti di laporan tersedia<br/><br/>
<b>v4.2:</b> <b>Regresi, ANOVA, Regresi Logistik</b> gratis terbatas — analisis dasar tanpa
License Key. Fitur lanjutan (VIF, post-hoc, ROC, AI) tetap eksklusif Pro.<br/><br/>
<b>v4.2:</b> Generate Laporan gratis <b>1×/hari</b> (tanpa AI).
Pro: tak terbatas + narasi AI + grafik tertanam.<br/><br/>
<b>v4.2:</b> Web Scraping, Power Analysis, Compute Variabel, navigasi sidebar per kategori.<br/><br/>
<b>v4.1 (Pro):</b> Item-Total Statistics &amp; Alpha jika Item Dihapus — CITC,
α-if-deleted, inter-item correlation matrix.
</div>""", unsafe_allow_html=True)
