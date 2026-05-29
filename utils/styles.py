"""
utils/styles.py — Ruang Statistika v5.0
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
# Core palette — refined navy + slate + electric blue
NAVY    = "#0a1628"
NAVY2   = "#0d1f3c"
NAVY3   = "#112244"
BLUE    = "#1565C0"
BLUE2   = "#2196F3"
BLUE3   = "#42A5F5"
BLUE4   = "#90CAF9"
LIGHT   = "#BBDEFB"
MUTED   = "#78909C"
MUTED2  = "#546E7A"
MUTED3  = "#37474F"
SLATE   = "#64748b"
SLATE2  = "#94a3b8"
GREEN   = "#2E7D32"
GREEN2  = "#43A047"
GREEN3  = "#A5D6A7"
RED     = "#C62828"
RED2    = "#EF5350"
INDIGO  = "#3F51B5"
VIOLET  = "#7C3AED"
AMBER   = "#F57F17"
AMBER2  = "#FFB300"
TEAL    = "#00897B"
BORDER  = "#E3EBF6"
BORDER2 = "#CBD5E1"
BG_SOFT = "#F8FAFD"
BG_AI   = "#EEF2FF"
BG_CARD = "#FFFFFF"
WHITE   = "#ffffff"
SHADOW  = "rgba(10, 22, 40, 0.08)"
SHADOW2 = "rgba(10, 22, 40, 0.14)"


# ─────────────────────────────────────────────────────────────────────────────
# 1. GLOBAL CSS  — di-cache, hanya build sekali per sesi
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def _global_css() -> str:
    return f"""<style>
/* ── Fonts ── */
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600;700&family=Plus+Jakarta+Sans:wght@300;400;500;600;700&family=DM+Serif+Display:ital@0;1&display=swap');

:root {{
    --font-display: 'DM Serif Display', Georgia, serif;
    --font-body: 'Plus Jakarta Sans', 'Sora', sans-serif;
    --nav-bg: {NAVY};
    --nav-border: rgba(255,255,255,.05);
    --nav-text: #94A3B8;
    --nav-text-hover: #E2E8F0;
    --nav-active-bg: rgba(33,150,243,.12);
    --nav-active-border: {BLUE2};
    --nav-active-text: #F0F9FF;
    --accent: {BLUE2};
    --accent2: {BLUE3};
    --radius-sm: 6px;
    --radius-md: 10px;
    --radius-lg: 16px;
    --radius-xl: 20px;
    --shadow-sm: 0 1px 3px {SHADOW}, 0 1px 2px {SHADOW};
    --shadow-md: 0 4px 12px {SHADOW}, 0 2px 6px {SHADOW};
    --shadow-lg: 0 10px 30px {SHADOW2}, 0 4px 12px {SHADOW};
    --shadow-card: 0 2px 8px rgba(10,22,40,.07), 0 0 0 1px rgba(10,22,40,.04);
    --transition: 200ms cubic-bezier(0.4, 0, 0.2, 1);
}}

html, body, [class*="css"] {{
    font-family: var(--font-body) !important;
    -webkit-font-smoothing: antialiased;
    text-rendering: optimizeLegibility;
}}

/* Scrollbar styling */
::-webkit-scrollbar {{ width: 5px; height: 5px; }}
::-webkit-scrollbar-track {{ background: transparent; }}
::-webkit-scrollbar-thumb {{ background: rgba(100,116,139,.3); border-radius: 10px; }}
::-webkit-scrollbar-thumb:hover {{ background: rgba(100,116,139,.5); }}

/* ── Sidebar toggle: sembunyikan saat belum login ── */
body:not(.rs-logged-in) [data-testid="collapsedControl"],
body:not(.rs-logged-in) [data-testid="stSidebarCollapsedControl"] {{ display:none !important; }}

/* ══ SIDEBAR ════════════════════════════════════════════════════════════════ */
[data-testid="stSidebar"] {{
    background: {NAVY} !important;
    border-right: 1px solid rgba(255,255,255,.05) !important;
}}
[data-testid="stSidebar"] * {{ color: var(--nav-text) !important; }}
[data-testid="stSidebar"] .stMarkdown h1,
[data-testid="stSidebar"] .stMarkdown h2,
[data-testid="stSidebar"] .stMarkdown h3 {{ color: {WHITE} !important; }}

/* Sidebar scrollbar */
[data-testid="stSidebar"]::-webkit-scrollbar {{ width: 3px; }}
[data-testid="stSidebar"]::-webkit-scrollbar-thumb {{ background: rgba(255,255,255,.1); }}

/* Group label */
.nav-group-label {{
    font-size: .6rem;
    font-weight: 700;
    letter-spacing: .1em;
    text-transform: uppercase;
    color: rgba(148,163,184,.45) !important;
    padding: 14px 14px 4px;
    margin: 0;
    display: block;
}}

/* Nav buttons */
[data-testid="stSidebar"] .stButton > button {{
    background: transparent !important;
    border: none !important;
    color: var(--nav-text) !important;
    text-align: left !important;
    padding: 6px 14px 6px 16px !important;
    border-radius: 0 !important;
    border-left: 2px solid transparent !important;
    font-size: .8rem !important;
    width: 100% !important;
    font-weight: 400 !important;
    margin: 0 !important;
    line-height: 1.5 !important;
    min-height: 0 !important;
    height: auto !important;
    letter-spacing: .01em !important;
    transition: all var(--transition) !important;
}}
[data-testid="stSidebar"] .stButton > button:hover {{
    background: rgba(255,255,255,.05) !important;
    color: var(--nav-text-hover) !important;
    border-left-color: rgba(33,150,243,.4) !important;
    padding-left: 18px !important;
}}
[data-testid="stSidebar"] .stButton > button:focus {{
    box-shadow: none !important;
    outline: none !important;
}}
[data-testid="stSidebar"] .stButton {{ margin-bottom:0 !important; margin-top:0 !important; }}
[data-testid="stSidebar"] .element-container {{ margin-bottom:0 !important; margin-top:0 !important; }}
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {{ gap:0 !important; }}

/* Sidebar divider */
[data-testid="stSidebar"] hr {{
    border: none !important;
    border-top: 1px solid rgba(255,255,255,.06) !important;
    margin: 8px 14px !important;
}}

/* Sidebar selectbox */
[data-testid="stSidebar"] .stSelectbox label {{
    font-size: .68rem !important;
    font-weight: 600 !important;
    letter-spacing: .06em !important;
    text-transform: uppercase !important;
    color: rgba(148,163,184,.55) !important;
}}
[data-testid="stSidebar"] .stSelectbox > div > div {{
    background: rgba(255,255,255,.05) !important;
    border: 1px solid rgba(255,255,255,.1) !important;
    border-radius: var(--radius-sm) !important;
    color: #CBD5E1 !important;
    font-size: .8rem !important;
}}

/* Sidebar text inputs */
[data-testid="stSidebar"] .stTextInput label {{
    font-size: .68rem !important;
    font-weight: 600 !important;
    letter-spacing: .06em !important;
    text-transform: uppercase !important;
    color: rgba(148,163,184,.55) !important;
}}
[data-testid="stSidebar"] .stTextInput input {{
    background: rgba(255,255,255,.05) !important;
    border: 1px solid rgba(255,255,255,.1) !important;
    border-radius: var(--radius-sm) !important;
    color: #CBD5E1 !important;
    font-size: .8rem !important;
}}
[data-testid="stSidebar"] .stTextInput input:focus {{
    border-color: rgba(33,150,243,.5) !important;
    box-shadow: 0 0 0 3px rgba(33,150,243,.08) !important;
}}

/* Sidebar sliders */
[data-testid="stSidebar"] .stSlider label {{
    font-size: .68rem !important;
    font-weight: 600 !important;
    letter-spacing: .06em !important;
    text-transform: uppercase !important;
    color: rgba(148,163,184,.55) !important;
}}

/* Sidebar number input */
[data-testid="stSidebar"] .stNumberInput label {{
    font-size: .68rem !important;
    font-weight: 600 !important;
    letter-spacing: .06em !important;
    text-transform: uppercase !important;
    color: rgba(148,163,184,.55) !important;
}}
[data-testid="stSidebar"] .stNumberInput input {{
    background: rgba(255,255,255,.05) !important;
    border: 1px solid rgba(255,255,255,.1) !important;
    border-radius: var(--radius-sm) !important;
    color: #CBD5E1 !important;
    font-size: .8rem !important;
}}

/* ══ MAIN CONTENT AREA ═══════════════════════════════════════════════════════ */
section[data-testid="stMain"] .block-container {{
    padding-top: 1.5rem !important;
    padding-bottom: 3rem !important;
    max-width: 1100px !important;
}}

/* ══ KOMPONEN BERSAMA ════════════════════════════════════════════════════════ */

/* Hero header — more refined with subtle mesh gradient */
.rs-header {{
    background: linear-gradient(135deg, {NAVY3} 0%, {NAVY2} 30%, {BLUE} 100%);
    padding: 1.75rem 2rem;
    border-radius: var(--radius-lg);
    margin-bottom: 1.5rem;
    position: relative;
    overflow: hidden;
    display: flex;
    align-items: center;
    gap: 20px;
    box-shadow: 0 4px 24px rgba(10,22,40,.25), 0 0 0 1px rgba(255,255,255,.06);
}}
.rs-header::before {{
    content:'';
    position:absolute;
    left: -60px; bottom: -80px;
    width: 220px; height: 220px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(33,150,243,.15) 0%, transparent 70%);
    pointer-events: none;
}}
.rs-header::after {{
    content:'';
    position:absolute;
    right: -60px; top: -60px;
    width: 240px; height: 240px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(255,255,255,.06) 0%, transparent 70%);
    pointer-events: none;
}}
/* Subtle grid texture */
.rs-header .rs-header-texture {{
    position: absolute;
    inset: 0;
    background-image:
        linear-gradient(rgba(255,255,255,.025) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,.025) 1px, transparent 1px);
    background-size: 32px 32px;
    pointer-events: none;
}}
.rs-header-icon {{
    background: rgba(255,255,255,.1);
    backdrop-filter: blur(8px);
    border: 1px solid rgba(255,255,255,.15);
    border-radius: var(--radius-md);
    width: 60px; height: 60px;
    display: flex; align-items: center; justify-content: center;
    flex-shrink: 0;
    position: relative; z-index: 1;
    font-size: 28px; color:{WHITE};
    box-shadow: 0 2px 10px rgba(0,0,0,.2);
}}
.rs-header h1 {{
    font-family: var(--font-display);
    font-size: 1.9rem;
    color: {WHITE};
    margin: 0 0 .25rem;
    position: relative; z-index: 1;
    letter-spacing: -.02em;
    text-shadow: 0 1px 8px rgba(0,0,0,.2);
}}
.rs-header p {{
    color: rgba(187,222,251,.8);
    font-size: .82rem;
    margin: 0;
    position: relative; z-index: 1;
    font-weight: 400;
    letter-spacing: .01em;
}}
.rs-logo-link {{ text-decoration:none; color:{BLUE3} !important; font-size:.8rem; }}

/* Greeting bar — glass morphism style */
.rs-greeting {{
    background: linear-gradient(135deg, {NAVY2} 0%, {NAVY3} 100%);
    border: 1px solid rgba(255,255,255,.07);
    border-radius: var(--radius-md);
    padding: 14px 20px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 1rem;
    box-shadow: var(--shadow-sm);
}}
.rs-greeting-text {{ font-size: .9rem; color: {WHITE}; font-weight: 600; letter-spacing: -.01em; }}
.rs-greeting-sub  {{ font-size: .74rem; color: {SLATE2}; margin-top: 2px; }}
.rs-greeting-badge {{
    background: linear-gradient(135deg, {AMBER2}, {AMBER});
    border-radius: var(--radius-sm);
    padding: 4px 12px;
    font-size: .7rem;
    color: #1a1000;
    font-weight: 800;
    letter-spacing: .04em;
    box-shadow: 0 2px 8px rgba(255,179,0,.35);
}}

/* Metric card — glass card style */
.rs-metric {{
    background: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: var(--radius-md);
    padding: 16px 18px;
    text-align: center;
    transition: transform var(--transition), box-shadow var(--transition), border-color var(--transition);
    box-shadow: var(--shadow-card);
    position: relative;
    overflow: hidden;
}}
.rs-metric::before {{
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, {BLUE}, {BLUE3});
    opacity: 0;
    transition: opacity var(--transition);
}}
.rs-metric:hover {{
    transform: translateY(-3px);
    box-shadow: var(--shadow-md);
    border-color: {BORDER2};
}}
.rs-metric:hover::before {{ opacity: 1; }}
.rs-metric-label {{
    font-size: .68rem;
    color: {SLATE};
    text-transform: uppercase;
    letter-spacing: .08em;
    margin-bottom: 8px;
    font-weight: 600;
}}
.rs-metric-value {{
    font-size: 1.6rem;
    font-weight: 700;
    color: {NAVY};
    letter-spacing: -.03em;
    line-height: 1;
}}
.rs-metric-sub {{ font-size: .72rem; color: {SLATE}; margin-top: 6px; font-weight: 400; }}

/* Step card — clean numbered list */
.rs-step-full {{
    margin-bottom: 8px;
}}
.rs-step {{
    background: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: var(--radius-md);
    padding: 14px 16px;
    display: flex;
    align-items: flex-start;
    gap: 12px;
    transition: transform var(--transition), box-shadow var(--transition);
    box-shadow: var(--shadow-card);
    margin-bottom: 8px;
}}
.rs-step:hover {{
    transform: translateY(-1px);
    box-shadow: var(--shadow-md);
}}
.rs-step-num {{
    background: linear-gradient(135deg, {BLUE}, {BLUE3});
    color: {WHITE};
    width: 26px; height: 26px;
    border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    font-weight: 700;
    font-size: .7rem;
    flex-shrink: 0;
    box-shadow: 0 2px 6px rgba(33,150,243,.3);
}}
.rs-step-title {{
    font-weight: 600;
    color: {NAVY};
    font-size: .85rem;
    letter-spacing: -.01em;
}}
.rs-step-desc {{
    font-size: .76rem;
    color: {SLATE};
    margin-top: 3px;
    line-height: 1.45;
}}
[data-theme="dark"] .rs-step-title {{ color: #E2E8F0 !important; }}
[data-theme="dark"] .rs-step-desc  {{ color: #94A3B8 !important; }}

/* Narasi / AI blocks */
.rs-narasi {{
    background: linear-gradient(135deg, #EFF6FF 0%, #EEF2FF 100%);
    border-left: 3px solid {BLUE};
    border-radius: 0 var(--radius-md) var(--radius-md) 0;
    padding: 1rem 1.2rem;
    font-size: .88rem;
    color: {NAVY};
    line-height: 1.7;
    margin-top: .5rem;
    box-shadow: var(--shadow-sm);
}}
.rs-ai-narasi {{
    background: linear-gradient(135deg, {BG_AI} 0%, #E8F5FF 100%);
    border-left: 3px solid {INDIGO};
    border-radius: 0 var(--radius-md) var(--radius-md) 0;
    padding: 1rem 1.2rem;
    font-size: .88rem;
    color: #1E1B4B;
    line-height: 1.75;
    margin-top: .5rem;
    box-shadow: var(--shadow-sm);
}}
.rs-ai-badge {{
    display: inline-flex;
    align-items: center;
    gap: 5px;
    background: linear-gradient(135deg, {INDIGO}, {VIOLET});
    color: {WHITE};
    font-size: .64rem;
    font-weight: 700;
    letter-spacing: .08em;
    padding: 3px 10px;
    border-radius: 20px;
    margin-bottom: 10px;
    text-transform: uppercase;
    box-shadow: 0 2px 8px rgba(99,102,241,.25);
}}

/* Section typography */
.rs-section-title {{
    font-family: var(--font-display);
    font-size: 1.4rem;
    color: {NAVY};
    margin-bottom: .25rem;
    letter-spacing: -.02em;
}}
.rs-section-sub {{ font-size: .8rem; color: {SLATE}; margin-bottom: 1rem; }}

/* Badges */
.badge-valid     {{ background: #ECFDF5; color: {GREEN}; border: 1px solid #A7F3D0; padding: 3px 10px; border-radius: 20px; font-size: .73rem; font-weight: 600; }}
.badge-invalid   {{ background: #FEF2F2; color: {RED};   border: 1px solid #FECACA; padding: 3px 10px; border-radius: 20px; font-size: .73rem; font-weight: 600; }}
.badge-reliable  {{ background: #ECFDF5; color: {GREEN}; border: 1px solid #A7F3D0; padding: 3px 12px; border-radius: 20px; font-size: .78rem; font-weight: 600; }}
.badge-unreliable{{ background: #FEF2F2; color: {RED};   border: 1px solid #FECACA; padding: 3px 12px; border-radius: 20px; font-size: .78rem; font-weight: 600; }}
.pro-badge {{
    background: linear-gradient(135deg, {BLUE}, {NAVY});
    color: {WHITE};
    padding: 3px 12px;
    border-radius: 20px;
    font-size: .7rem;
    font-weight: 700;
    letter-spacing: .06em;
    box-shadow: 0 2px 6px rgba(21,101,192,.25);
}}
.pro-lock-badge {{
    background: linear-gradient(135deg, {INDIGO}, {VIOLET});
    color: {WHITE};
    padding: 2px 8px;
    border-radius: 10px;
    font-size: .62rem;
    font-weight: 700;
    letter-spacing: .06em;
    margin-left: 4px;
    vertical-align: middle;
    box-shadow: 0 1px 4px rgba(99,102,241,.25);
}}

/* CTA wizard block */
.rs-cta-wizard {{
    background: linear-gradient(135deg, #EEF2FF 0%, #E8F0FE 100%);
    border: 1px solid #C7D2FE;
    border-radius: var(--radius-md);
    padding: 20px 22px 16px;
    display: block;
    box-shadow: 0 2px 8px rgba(99,102,241,.08);
    margin-bottom: 10px;
}}
.rs-cta-title {{ font-size: .92rem; font-weight: 700; color: #3730A3; margin-bottom: 5px; letter-spacing: -.01em; }}
.rs-cta-desc  {{ font-size: .78rem; color: #4338CA; line-height: 1.55; margin-bottom: 0; }}

/* Chat bubbles */
.chat-container {{
    max-height: 420px;
    overflow-y: auto;
    padding: .75rem;
    background: {BG_SOFT};
    border: 1px solid {BORDER};
    border-radius: var(--radius-md);
    margin-bottom: 1rem;
    -webkit-mask-image: linear-gradient(to bottom, transparent 0%, black 5%, black 95%, transparent 100%);
    mask-image: linear-gradient(to bottom, transparent 0%, black 5%, black 95%, transparent 100%);
}}
.chat-bubble-user {{
    background: linear-gradient(135deg, {BLUE}, {BLUE3});
    color: {WHITE};
    padding: .6rem 1rem;
    border-radius: 14px 14px 4px 14px;
    margin: .5rem 0 .5rem 25%;
    font-size: .86rem;
    line-height: 1.55;
    box-shadow: 0 2px 8px rgba(33,150,243,.2);
}}
.chat-bubble-ai {{
    background: {BG_CARD};
    border: 1px solid {BORDER};
    color: {NAVY};
    padding: .6rem 1rem;
    border-radius: 14px 14px 14px 4px;
    margin: .5rem 25% .5rem 0;
    font-size: .86rem;
    line-height: 1.6;
    box-shadow: var(--shadow-card);
}}
.chat-label {{ font-size: .67rem; color: {SLATE}; margin-bottom: 3px; letter-spacing: .04em; font-weight: 600; text-transform: uppercase; }}

/* ══ TABLES ══════════════════════════════════════════════════════════════════ */
.stDataFrame {{
    border-radius: var(--radius-md) !important;
    overflow: hidden !important;
    box-shadow: var(--shadow-card) !important;
    border: 1px solid {BORDER} !important;
}}

/* ══ EXPANDERS ═══════════════════════════════════════════════════════════════ */
[data-testid="stExpander"] {{
    border: 1px solid {BORDER} !important;
    border-radius: var(--radius-md) !important;
    box-shadow: var(--shadow-card) !important;
    overflow: hidden !important;
    background: {BG_CARD} !important;
}}
[data-testid="stExpander"] summary {{
    font-weight: 600 !important;
    font-size: .88rem !important;
    color: {NAVY} !important;
    padding: 10px 16px !important;
    background: {BG_CARD} !important;
}}
/* Expander body wrapper */
[data-testid="stExpander"] > div[data-testid="stExpanderDetails"] {{
    background: {BG_CARD} !important;
    padding: 4px 16px 14px !important;
}}
/* Expander detail inner block */
[data-testid="stExpander"] [data-testid="stVerticalBlock"] {{
    background: {BG_CARD} !important;
}}
/* Text inside expander — targeted, tidak merusak internal Streamlit widgets */
[data-testid="stExpander"] p,
[data-testid="stExpander"] td,
[data-testid="stExpander"] th,
[data-testid="stExpander"] li,
[data-testid="stExpander"] label {{
    color: {NAVY} !important;
}}
/* Tables inside expander */
[data-testid="stExpander"] table {{
    background: {BG_CARD} !important;
    border-collapse: collapse !important;
    width: 100% !important;
}}
[data-testid="stExpander"] thead tr {{
    background: {BG_SOFT} !important;
    border-bottom: 2px solid {BORDER} !important;
}}
[data-testid="stExpander"] thead th {{
    background: {BG_SOFT} !important;
    color: {NAVY} !important;
    font-weight: 600 !important;
    font-size: .8rem !important;
    padding: 8px 12px !important;
    text-align: left !important;
}}
[data-testid="stExpander"] tbody tr {{
    border-bottom: 1px solid {BORDER} !important;
    background: {BG_CARD} !important;
}}
[data-testid="stExpander"] tbody tr:nth-child(even) {{
    background: {BG_SOFT} !important;
}}
[data-testid="stExpander"] tbody td {{
    color: {NAVY} !important;
    font-size: .82rem !important;
    padding: 7px 12px !important;
    background: transparent !important;
}}
/* Markdown inside expander */
[data-testid="stExpander"] .stMarkdown p,
[data-testid="stExpander"] .stMarkdown span,
[data-testid="stExpander"] .stMarkdown li,
[data-testid="stExpander"] .stMarkdown h1,
[data-testid="stExpander"] .stMarkdown h2,
[data-testid="stExpander"] .stMarkdown h3,
[data-testid="stExpander"] .stMarkdown h4 {{
    color: {NAVY} !important;
}}

/* ══ ALERTS / INFO / SUCCESS / ERROR ═════════════════════════════════════════ */
[data-testid="stAlert"] {{
    border-radius: var(--radius-md) !important;
    border-width: 1px !important;
    font-size: .85rem !important;
}}

/* ══ TABS ════════════════════════════════════════════════════════════════════ */
[data-baseweb="tab-list"] {{
    gap: 4px !important;
    background: transparent !important;
    border-bottom: 1px solid {BORDER} !important;
    padding-bottom: 0 !important;
}}
[data-baseweb="tab"] {{
    border-radius: var(--radius-sm) var(--radius-sm) 0 0 !important;
    font-size: .84rem !important;
    font-weight: 500 !important;
    padding: 8px 16px !important;
    color: {SLATE} !important;
    background: transparent !important;
    border: none !important;
    transition: color var(--transition), background var(--transition) !important;
}}
[data-baseweb="tab"]:hover {{
    color: {NAVY} !important;
    background: rgba(10,22,40,.04) !important;
}}
[aria-selected="true"][data-baseweb="tab"] {{
    color: {BLUE} !important;
    font-weight: 600 !important;
    background: transparent !important;
    border-bottom: 2px solid {BLUE} !important;
}}

/* ══ PRIMARY BUTTONS ═════════════════════════════════════════════════════════ */
[data-testid="stMain"] .stButton > button[kind="primary"],
[data-testid="stMain"] .stButton > button[data-testid*="primary"] {{
    background: linear-gradient(135deg, {BLUE} 0%, {BLUE3} 100%) !important;
    color: {WHITE} !important;
    border: none !important;
    border-radius: var(--radius-sm) !important;
    font-weight: 600 !important;
    font-size: .86rem !important;
    letter-spacing: .01em !important;
    box-shadow: 0 2px 10px rgba(33,150,243,.3) !important;
    transition: all var(--transition) !important;
}}
[data-testid="stMain"] .stButton > button[kind="primary"]:hover {{
    box-shadow: 0 4px 16px rgba(33,150,243,.4) !important;
    transform: translateY(-1px) !important;
}}

/* ══ METRICS (native) ════════════════════════════════════════════════════════ */
[data-testid="stMetricValue"] {{
    font-size: 1.7rem !important;
    font-weight: 700 !important;
    letter-spacing: -.03em !important;
    color: {NAVY} !important;
}}

/* Footer */
.rs-footer {{
    margin-top: 3rem;
    padding-top: 1.5rem;
    border-top: 1px solid {BORDER};
    text-align: center;
    font-size: .76rem;
    color: {SLATE2};
}}
.rs-footer a {{ color: {BLUE}; text-decoration: none; font-weight: 500; }}
.rs-footer a:hover {{ color: {BLUE2}; text-decoration: underline; }}
.rs-footer b {{ color: {NAVY}; }}

/* ══ DARK MODE OVERRIDES ═════════════════════════════════════════════════════
   Streamlit dark mode menggunakan [data-theme="dark"] pada root element.
   Semua override di sini membalikkan light-only styles di atas.
   ═══════════════════════════════════════════════════════════════════════════ */
[data-theme="dark"] {{
    --bg-card-dm:   #111e35;
    --bg-soft-dm:   #0d1728;
    --border-dm:    rgba(255,255,255,.08);
    --border2-dm:   rgba(255,255,255,.14);
    --text-primary-dm: #E2E8F0;
    --text-muted-dm:   #94A3B8;
    --text-navy-dm:    #CBD5E1;
}}

/* ── Metric cards ── */
[data-theme="dark"] .rs-metric {{
    background: var(--bg-card-dm) !important;
    border-color: var(--border-dm) !important;
    box-shadow: 0 2px 8px rgba(0,0,0,.3), 0 0 0 1px rgba(255,255,255,.04) !important;
}}
[data-theme="dark"] .rs-metric:hover {{
    border-color: var(--border2-dm) !important;
    box-shadow: 0 8px 24px rgba(0,0,0,.4) !important;
}}
[data-theme="dark"] .rs-metric-label {{ color: var(--text-muted-dm) !important; }}
[data-theme="dark"] .rs-metric-value {{ color: #F1F5F9 !important; }}
[data-theme="dark"] .rs-metric-sub   {{ color: var(--text-muted-dm) !important; }}

/* ── Step cards ── */
[data-theme="dark"] .rs-step {{
    background: var(--bg-card-dm) !important;
    border-color: var(--border-dm) !important;
    box-shadow: 0 2px 8px rgba(0,0,0,.3), 0 0 0 1px rgba(255,255,255,.04) !important;
}}
[data-theme="dark"] .rs-step:hover {{
    box-shadow: 0 6px 20px rgba(0,0,0,.4) !important;
}}

/* ── Narasi / AI blocks ── */
[data-theme="dark"] .rs-narasi {{
    background: linear-gradient(135deg, rgba(21,101,192,.18) 0%, rgba(63,81,181,.15) 100%) !important;
    border-left-color: {BLUE3} !important;
    color: #CBD5E1 !important;
    box-shadow: none !important;
}}
[data-theme="dark"] .rs-ai-narasi {{
    background: linear-gradient(135deg, rgba(63,81,181,.18) 0%, rgba(21,101,192,.14) 100%) !important;
    border-left-color: #818CF8 !important;
    color: #C7D2FE !important;
    box-shadow: none !important;
}}

/* ── CTA Wizard block ── */
[data-theme="dark"] .rs-cta-wizard {{
    background: linear-gradient(135deg, rgba(55,48,163,.25) 0%, rgba(37,99,235,.2) 100%) !important;
    border-color: rgba(99,102,241,.35) !important;
    box-shadow: 0 2px 12px rgba(99,102,241,.12) !important;
}}
[data-theme="dark"] .rs-cta-title {{ color: #A5B4FC !important; }}
[data-theme="dark"] .rs-cta-desc  {{ color: #818CF8 !important; }}

/* ── Section typography ── */
[data-theme="dark"] .rs-section-title {{ color: #E2E8F0 !important; }}
[data-theme="dark"] .rs-section-sub   {{ color: #94A3B8 !important; }}

/* ── Greeting bar ── */
[data-theme="dark"] .rs-greeting-sub {{ color: #64748B !important; }}

/* ── Expanders ── */
[data-theme="dark"] [data-testid="stExpander"] {{
    background: var(--bg-card-dm) !important;
    border-color: var(--border-dm) !important;
}}
[data-theme="dark"] [data-testid="stExpander"] summary {{
    background: var(--bg-card-dm) !important;
    color: #E2E8F0 !important;
}}
[data-theme="dark"] [data-testid="stExpander"] > div[data-testid="stExpanderDetails"] {{
    background: var(--bg-card-dm) !important;
}}
[data-theme="dark"] [data-testid="stExpander"] [data-testid="stVerticalBlock"] {{
    background: var(--bg-card-dm) !important;
}}
[data-theme="dark"] [data-testid="stExpander"] p,
[data-theme="dark"] [data-testid="stExpander"] td,
[data-theme="dark"] [data-testid="stExpander"] th,
[data-theme="dark"] [data-testid="stExpander"] li,
[data-theme="dark"] [data-testid="stExpander"] label,
[data-theme="dark"] [data-testid="stExpander"] .stMarkdown p,
[data-theme="dark"] [data-testid="stExpander"] .stMarkdown span,
[data-theme="dark"] [data-testid="stExpander"] .stMarkdown li,
[data-theme="dark"] [data-testid="stExpander"] .stMarkdown h1,
[data-theme="dark"] [data-testid="stExpander"] .stMarkdown h2,
[data-theme="dark"] [data-testid="stExpander"] .stMarkdown h3,
[data-theme="dark"] [data-testid="stExpander"] .stMarkdown h4 {{
    color: #CBD5E1 !important;
}}
[data-theme="dark"] [data-testid="stExpander"] table {{
    background: var(--bg-card-dm) !important;
}}
[data-theme="dark"] [data-testid="stExpander"] thead tr {{
    background: var(--bg-soft-dm) !important;
    border-bottom-color: var(--border-dm) !important;
}}
[data-theme="dark"] [data-testid="stExpander"] thead th {{
    background: var(--bg-soft-dm) !important;
    color: #E2E8F0 !important;
}}
[data-theme="dark"] [data-testid="stExpander"] tbody tr {{
    border-bottom-color: var(--border-dm) !important;
    background: var(--bg-card-dm) !important;
}}
[data-theme="dark"] [data-testid="stExpander"] tbody tr:nth-child(even) {{
    background: var(--bg-soft-dm) !important;
}}
[data-theme="dark"] [data-testid="stExpander"] tbody td {{
    color: #CBD5E1 !important;
}}

/* ── Tabs ── */
[data-theme="dark"] [data-baseweb="tab"] {{
    color: #64748B !important;
}}
[data-theme="dark"] [data-baseweb="tab"]:hover {{
    color: #CBD5E1 !important;
    background: rgba(255,255,255,.05) !important;
}}
[data-theme="dark"] [aria-selected="true"][data-baseweb="tab"] {{
    color: {BLUE3} !important;
    border-bottom-color: {BLUE3} !important;
}}
[data-theme="dark"] [data-baseweb="tab-list"] {{
    border-bottom-color: rgba(255,255,255,.08) !important;
}}

/* ── DataFrames ── */
[data-theme="dark"] .stDataFrame {{
    border-color: var(--border-dm) !important;
}}

/* ── Native metric values ── */
[data-theme="dark"] [data-testid="stMetricValue"] {{
    color: #F1F5F9 !important;
}}

/* ── Chat bubbles ── */
[data-theme="dark"] .chat-container {{
    background: var(--bg-soft-dm) !important;
    border-color: var(--border-dm) !important;
}}
[data-theme="dark"] .chat-bubble-ai {{
    background: var(--bg-card-dm) !important;
    border-color: var(--border-dm) !important;
    color: #CBD5E1 !important;
}}
[data-theme="dark"] .chat-label {{ color: #64748B !important; }}

/* ── Footer ── */
[data-theme="dark"] .rs-footer {{
    border-top-color: rgba(255,255,255,.07) !important;
    color: #475569 !important;
}}
[data-theme="dark"] .rs-footer b {{ color: #CBD5E1 !important; }}

/* ── Badges ── */
[data-theme="dark"] .badge-valid {{
    background: rgba(46,125,50,.2) !important;
    color: #86EFAC !important;
    border-color: rgba(134,239,172,.2) !important;
}}
[data-theme="dark"] .badge-invalid {{
    background: rgba(198,40,40,.2) !important;
    color: #FCA5A5 !important;
    border-color: rgba(252,165,165,.2) !important;
}}
[data-theme="dark"] .badge-reliable {{
    background: rgba(46,125,50,.2) !important;
    color: #86EFAC !important;
    border-color: rgba(134,239,172,.2) !important;
}}
[data-theme="dark"] .badge-unreliable {{
    background: rgba(198,40,40,.2) !important;
    color: #FCA5A5 !important;
    border-color: rgba(252,165,165,.2) !important;
}}
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

/* ── Page background — deep space gradient ── */
[data-testid="stAppViewContainer"],
[data-testid="stApp"] {{
    background: linear-gradient(145deg, {NAVY} 0%, #0d1f3c 45%, #122a50 70%, #0e2244 100%) !important;
    position: relative;
}}
[data-testid="stAppViewContainer"]::before {{
    content: '';
    position: fixed;
    inset: 0;
    background-image:
        radial-gradient(ellipse at 20% 40%, rgba(33,150,243,.08) 0%, transparent 50%),
        radial-gradient(ellipse at 80% 70%, rgba(99,102,241,.06) 0%, transparent 50%),
        radial-gradient(ellipse at 50% 10%, rgba(255,255,255,.02) 0%, transparent 40%);
    pointer-events: none;
    z-index: 0;
}}
/* Subtle dot grid texture */
[data-testid="stAppViewContainer"]::after {{
    content: '';
    position: fixed;
    inset: 0;
    background-image: radial-gradient(rgba(255,255,255,.04) 1px, transparent 1px);
    background-size: 24px 24px;
    pointer-events: none;
    z-index: 0;
}}

section[data-testid="stMain"] .block-container {{
    padding-top: 6vh !important;
    max-width: 440px !important;
    margin: 0 auto !important;
    padding-left: 1rem !important;
    padding-right: 1rem !important;
    padding-bottom: 3rem !important;
    position: relative;
    z-index: 1;
}}

/* ── Login Card ── */
.signin-card {{
    background: rgba(255,255,255,.06);
    backdrop-filter: blur(24px) saturate(1.4);
    -webkit-backdrop-filter: blur(24px) saturate(1.4);
    border: 1px solid rgba(255,255,255,.1);
    border-radius: 20px;
    overflow: hidden;
    box-shadow:
        0 20px 60px rgba(0,0,0,.4),
        0 0 0 1px rgba(255,255,255,.04),
        inset 0 1px 0 rgba(255,255,255,.1);
    width: 100%;
    max-width: 440px;
}}

/* Card header */
.signin-card-header {{
    background: linear-gradient(135deg, {NAVY} 0%, {NAVY3} 40%, {BLUE} 100%);
    padding: 28px 24px 22px;
    text-align: center;
    position: relative;
    overflow: hidden;
}}
.signin-card-header::before {{
    content: '';
    position: absolute;
    right: -50px; top: -50px;
    width: 180px; height: 180px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(33,150,243,.15) 0%, transparent 70%);
    pointer-events: none;
}}
.signin-card-header::after {{
    content: '';
    position: absolute;
    left: -30px; bottom: -50px;
    width: 150px; height: 150px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(255,255,255,.04) 0%, transparent 70%);
    pointer-events: none;
}}
/* Grid lines on header */
.signin-card-header .header-grid {{
    position: absolute;
    inset: 0;
    background-image:
        linear-gradient(rgba(255,255,255,.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,.03) 1px, transparent 1px);
    background-size: 28px 28px;
    pointer-events: none;
}}
.signin-header-logo {{
    position: relative; z-index: 1;
    width: 56px; height: 56px;
    border-radius: 14px;
    background: rgba(255,255,255,.12);
    backdrop-filter: blur(8px);
    border: 1px solid rgba(255,255,255,.18);
    display: flex; align-items: center; justify-content: center;
    margin: 0 auto 12px;
    box-shadow: 0 4px 14px rgba(0,0,0,.2), 0 0 0 1px rgba(255,255,255,.08);
}}
.signin-header-logo img {{
    width: 36px; height: 36px;
    object-fit: contain;
    filter: drop-shadow(0 2px 8px rgba(0,0,0,.3));
}}
.signin-header-title {{
    font-family: 'DM Serif Display', Georgia, serif;
    font-size: 1.5rem;
    color: {WHITE};
    letter-spacing: -.02em;
    position: relative; z-index: 1;
    margin: 0 0 5px;
    text-shadow: 0 1px 8px rgba(0,0,0,.3);
}}
.signin-header-sub {{
    font-size: .73rem;
    color: rgba(187,222,251,.75);
    position: relative; z-index: 1;
    letter-spacing: .02em;
    font-weight: 400;
}}

/* Card body */
.signin-card-body {{
    padding: 20px 22px 22px;
}}

/* Tab strip */
.signin-tab-row {{
    display: flex;
    border-bottom: 1px solid rgba(255,255,255,.1);
    margin-bottom: 1.4rem;
    gap: 0;
}}
.signin-tab-row .stButton {{ flex: 1; }}
.signin-tab-row .stButton > button {{
    background: transparent !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    border-radius: 0 !important;
    color: rgba(255,255,255,.4) !important;
    font-size: .83rem !important;
    font-weight: 500 !important;
    padding: 10px 4px !important;
    width: 100% !important;
    margin-bottom: -1px !important;
    letter-spacing: .01em !important;
    transition: color .2s, border-color .2s !important;
}}
.signin-tab-row .stButton > button:hover {{
    color: rgba(255,255,255,.8) !important;
    background: transparent !important;
}}
.signin-tab-active .stButton > button {{
    color: {WHITE} !important;
    font-weight: 700 !important;
    border-bottom-color: {BLUE2} !important;
}}

/* Form inputs */
section[data-testid="stMain"] .stTextInput label {{
    font-size: .7rem !important;
    font-weight: 600 !important;
    color: rgba(255,255,255,.6) !important;
    letter-spacing: .06em !important;
    text-transform: uppercase !important;
    margin-bottom: 5px !important;
}}
section[data-testid="stMain"] .stTextInput input {{
    border: 1.5px solid rgba(255,255,255,.15) !important;
    border-radius: var(--radius-sm) !important;
    padding: 10px 13px !important;
    font-size: .86rem !important;
    background: rgba(255,255,255,.07) !important;
    color: {WHITE} !important;
    -webkit-text-fill-color: {WHITE} !important;
    caret-color: {BLUE2} !important;
    transition: border-color .2s, box-shadow .2s !important;
    letter-spacing: .01em !important;
}}
section[data-testid="stMain"] .stTextInput input:focus {{
    border-color: rgba(33,150,243,.7) !important;
    background: rgba(13,31,60,.85) !important;
    box-shadow: 0 0 0 3px rgba(33,150,243,.15) !important;
    color: {WHITE} !important;
    -webkit-text-fill-color: {WHITE} !important;
    caret-color: {BLUE2} !important;
    outline: none !important;
}}
/* Paksa dark background saat browser autocomplete fill */
section[data-testid="stMain"] .stTextInput input:focus-within {{
    background: rgba(13,31,60,.85) !important;
}}
section[data-testid="stMain"] .stTextInput input:-webkit-autofill,
section[data-testid="stMain"] .stTextInput input:-webkit-autofill:hover,
section[data-testid="stMain"] .stTextInput input:-webkit-autofill:focus {{
    -webkit-text-fill-color: {WHITE} !important;
    -webkit-box-shadow: 0 0 0 1000px rgba(13,31,60,.85) inset !important;
    caret-color: {WHITE} !important;
}}
section[data-testid="stMain"] .stTextInput input::placeholder {{
    color: rgba(255,255,255,.3) !important;
    -webkit-text-fill-color: rgba(255,255,255,.3) !important;
}}

/* Submit button */
section[data-testid="stMain"] .stForm [data-testid="stFormSubmitButton"] > button {{
    background: linear-gradient(135deg, {BLUE} 0%, {BLUE3} 100%) !important;
    color: {WHITE} !important;
    border: none !important;
    border-radius: var(--radius-sm) !important;
    padding: 11px !important;
    font-size: .88rem !important;
    font-weight: 600 !important;
    width: 100% !important;
    letter-spacing: .02em !important;
    transition: opacity .2s, box-shadow .2s, transform .2s !important;
    box-shadow: 0 4px 16px rgba(33,150,243,.35) !important;
}}
section[data-testid="stMain"] .stForm [data-testid="stFormSubmitButton"] > button:hover {{
    opacity: .92 !important;
    box-shadow: 0 6px 20px rgba(33,150,243,.45) !important;
    transform: translateY(-1px) !important;
}}

/* CTA buttons */
section[data-testid="stMain"] .stButton > button {{
    background: rgba(255,255,255,.08) !important;
    border: 1.5px solid rgba(255,255,255,.15) !important;
    border-radius: var(--radius-sm) !important;
    color: {WHITE} !important;
    font-size: .83rem !important;
    font-weight: 500 !important;
    padding: 9px !important;
    width: 100% !important;
    letter-spacing: .01em !important;
    transition: background .2s, border-color .2s !important;
}}
section[data-testid="stMain"] .stButton > button:hover {{
    background: rgba(255,255,255,.14) !important;
    border-color: rgba(255,255,255,.3) !important;
}}

/* Link buttons */
.signin-link-btn-right {{ text-align:right; margin-top:-2px; margin-bottom:6px; }}
.signin-link-btn-right .stButton > button {{
    background: transparent !important;
    border: none !important;
    color: {BLUE3} !important;
    font-size: .72rem !important;
    font-weight: 500 !important;
    padding: 0 !important;
    height: auto !important;
    min-height: 0 !important;
    width: auto !important;
    float: right;
    letter-spacing: .01em !important;
}}
.signin-link-btn-right .stButton > button:hover {{
    background: transparent !important;
    text-decoration: underline !important;
}}
.signin-link-btn .stButton > button {{
    background: transparent !important;
    border: none !important;
    color: {BLUE3} !important;
    font-size: .72rem !important;
    font-weight: 600 !important;
    padding: 2px 6px !important;
    height: auto !important;
    min-height: 0 !important;
    letter-spacing: .01em !important;
}}
.signin-link-btn .stButton > button:hover {{
    background: transparent !important;
    text-decoration: underline !important;
}}
.signin-link-btn-muted .stButton > button {{
    color: rgba(148,163,184,.7) !important;
    font-weight: 400 !important;
    font-size: .7rem !important;
}}

/* Divider */
.signin-divider {{
    text-align: center;
    font-size: .68rem;
    color: rgba(255,255,255,.25);
    margin: 10px 0;
    position: relative;
    letter-spacing: .08em;
    text-transform: uppercase;
    font-weight: 600;
}}
.signin-divider::before, .signin-divider::after {{
    content: '';
    position: absolute;
    top: 50%;
    width: 38%;
    height: 1px;
    background: rgba(255,255,255,.1);
}}
.signin-divider::before {{ left: 0; }}
.signin-divider::after  {{ right: 0; }}

/* Footer */
.signin-footer {{
    text-align: center;
    margin-top: 12px;
    font-size: .72rem;
    color: rgba(148,163,184,.6);
}}
.signin-footer a {{ color: {BLUE3}; font-weight: 600; text-decoration: none; }}
.signin-footer a:hover {{ text-decoration: underline; }}
.signin-page-footer {{
    text-align: center;
    margin-top: 1.5rem;
    font-size: .7rem;
    color: rgba(148,163,184,.45);
    line-height: 1.8;
}}
.signin-page-footer a {{ color: rgba(66,165,245,.7); text-decoration: none; font-weight: 500; }}

/* Alerts inside login */
section[data-testid="stMain"] [data-testid="stAlert"] {{
    border-radius: var(--radius-sm) !important;
    font-size: .82rem !important;
}}

.forgot-link {{ text-align:right; margin:-4px 0 10px; font-size:.72rem; }}
.forgot-link a {{ color:{BLUE3}; text-decoration:none; }}
.forgot-link a:hover {{ text-decoration:underline; }}
.activate-link {{ text-align:center; margin-top:8px; font-size:.7rem; color:rgba(148,163,184,.5); }}
.activate-link a {{ color:rgba(100,153,204,.8); text-decoration:none; }}
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
    background: rgba(33,150,243,.1) !important;
    color: #E0F2FE !important;
    font-weight: 600 !important;
    border-left-color: {BLUE2} !important;
    letter-spacing: .01em !important;
    padding-left: 18px !important;
}}
</style>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# 4. NAV LOCKED  — sidebar dikunci saat belum login
# ─────────────────────────────────────────────────────────────────────────────

_NAV_LOCKED_CSS: str = f"""<style>
[data-testid="stSidebar"] .stButton > button {{
    opacity: .22 !important;
    pointer-events: none !important;
    cursor: not-allowed !important;
}}
</style>
<div style='margin:10px 14px 4px;padding:10px 12px;
            background:rgba(255,255,255,.04);
            border:1px solid rgba(255,255,255,.07);
            border-radius:8px;
            font-size:.7rem;color:rgba(100,116,139,.7);line-height:1.6;text-align:center;'>
    🔒 Selesaikan langkah awal<br>di halaman utama dulu
</div>"""


def inject_nav_locked_css() -> None:
    st.markdown(_NAV_LOCKED_CSS, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# 5. HELPER — render komponen beranda (greeting + header)
# ─────────────────────────────────────────────────────────────────────────────

def render_greeting(user_name: str, is_pro: bool) -> None:
    """Render greeting bar. user_name boleh kosong (mode gratis)."""
    import datetime as _dt
    import zoneinfo

    tz_wib = zoneinfo.ZoneInfo("Asia/Jakarta")
    hour = _dt.datetime.now(tz_wib).hour
    salam = (
        "Selamat pagi"   if hour < 11 else
        "Selamat siang"  if hour < 15 else
        "Selamat sore"   if hour < 18 else
        "Selamat malam"
    )
    tier_badge = (
        "<span style='background:linear-gradient(135deg,#FFB300,#F57F17);"
        "color:#1a1000;font-size:.62rem;font-weight:800;letter-spacing:.06em;"
        "padding:2px 9px;border-radius:5px;margin-left:7px;"
        "box-shadow:0 2px 8px rgba(255,179,0,.35);vertical-align:middle;'>✦ PRO</span>"
        if is_pro else ""
    )
    display_name = user_name if user_name else "Pengguna"
    greeting_text = f"{salam}, {display_name}! 👋" if user_name else f"{salam}! 👋"
    st.markdown(
        f"<div class='rs-greeting'>"
        f"<div>"
        f"<div class='rs-greeting-text'>{greeting_text}{tier_badge}</div>"
        f"<div class='rs-greeting-sub'>Siap membantu analisis statistik Anda hari ini.</div>"
        f"</div>"
        f"</div>",
        unsafe_allow_html=True,
    )


def render_hero_header() -> None:
    """Render hero header Ruang Statistika dengan ikon."""
    st.markdown("""
<div class="rs-header">
    <div class="rs-header-texture"></div>
    <div class="rs-header-icon">
        <img src="https://i.imgur.com/RF4mzxf.png" width="36" height="36"
             style="object-fit:contain;filter:drop-shadow(0 2px 8px rgba(0,0,0,.25));" alt="logo">
    </div>
    <div>
        <h1 style="margin:0;">Ruang Statistika</h1>
        <p style="margin:0;">
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
    # Render pasangan 2 kolom, item terakhir full-width jika ganjil
    pairs = [(steps[i], steps[i+1] if i+1 < len(steps) else None)
             for i in range(0, len(steps), 2)]
    for pair_idx, (left, right) in enumerate(pairs):
        base_num = pair_idx * 2 + 1
        if right is None:
            # Satu item terakhir — full width
            i, (title, desc) = base_num, left
            st.markdown(
                f'<div class="rs-step rs-step-full">'
                f'<div class="rs-step-num">{i}</div>'
                f'<div>'
                f'<div class="rs-step-title">{title}</div>'
                f'<div class="rs-step-desc">{desc}</div>'
                f'</div></div>',
                unsafe_allow_html=True,
            )
        else:
            cols = st.columns(2)
            for ci, (i, (title, desc)) in enumerate([(base_num, left), (base_num+1, right)]):
                with cols[ci]:
                    st.markdown(
                        f'<div class="rs-step">'
                        f'<div class="rs-step-num">{i}</div>'
                        f'<div>'
                        f'<div class="rs-step-title">{title}</div>'
                        f'<div class="rs-step-desc">{desc}</div>'
                        f'</div></div>',
                        unsafe_allow_html=True,
                    )


def render_cta_wizard(on_click_key: str = "cta_wizard_btn") -> bool:
    """
    Render CTA Wizard block. Return True jika tombol diklik.
    """
    st.markdown(
        '<div class="rs-cta-wizard">'
        '<div>'
        '<div class="rs-cta-title">🧭 Bingung pilih uji statistik?</div>'
        '<div class="rs-cta-desc">Jawab 3 sampai 4 pertanyaan singkat dan Wizard akan '
        'merekomendasikan uji yang tepat dan langsung membuka modulnya.</div>'
        '</div>'
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
