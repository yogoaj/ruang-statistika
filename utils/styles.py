"""
utils/styles.py — Ruang Statistika v5.0
CSS terpusat, dipecah per concern untuk performa optimal.
Enterprise SaaS UI Edition — High-Precision Statistical Platform Styling.
"""
from __future__ import annotations
import streamlit as st

# ── Konstanta Palet Warna (Dipertahankan penuh untuk kompatibilitas modul) ───
NAVY    = "#0B1120"
NAVY2   = "#0F172A"
NAVY3   = "#1E293B"
BLUE    = "#1D4ED8"
BLUE2   = "#2563EB"
BLUE3   = "#3B82F6"
BLUE4   = "#93C5FD"
LIGHT   = "#DBEAFE"
MUTED   = "#64748B"
MUTED2  = "#475569"
MUTED3  = "#334155"
SLATE   = "#64748B"
SLATE2  = "#94A3B8"
GREEN   = "#059669"
GREEN2  = "#10B981"
GREEN3  = "#A7F3D0"
RED     = "#DC2626"
RED2    = "#EF4444"
INDIGO  = "#4F46E5"
VIOLET  = "#7C3AED"
AMBER   = "#D97706"
AMBER2  = "#F59E0B"
TEAL    = "#0D9488"
BORDER  = "#E2E8F0"
BORDER2 = "#CBD5E1"
BG_SOFT = "#F8FAFC"
BG_AI   = "#EEF2FF"
BG_CARD = "#FFFFFF"
WHITE   = "#FFFFFF"
SHADOW  = "rgba(15, 23, 42, 0.06)"
SHADOW2 = "rgba(15, 23, 42, 0.12)"


@st.cache_data(show_spinner=False)
def _global_css() -> str:
    return f"""<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@500;600;700&family=DM+Serif+Display:ital@0;1&display=swap');

:root {{
    --font-display: 'Plus Jakarta Sans', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    --font-body: 'Plus Jakarta Sans', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    --font-mono: 'JetBrains Mono', monospace;
    --nav-bg: {NAVY};
    --nav-border: rgba(255, 255, 255, 0.07);
    --nav-text: #94A3B8;
    --nav-text-hover: #F8FAFC;
    --nav-active-bg: rgba(37, 99, 235, 0.16);
    --nav-active-border: {BLUE3};
    --nav-active-text: #FFFFFF;
    --accent: {BLUE2};
    --accent2: {BLUE3};
    --radius-sm: 8px;
    --radius-md: 12px;
    --radius-lg: 16px;
    --radius-xl: 22px;
    --shadow-sm: 0 1px 2px 0 rgba(15, 23, 42, 0.04), 0 1px 3px 0 rgba(15, 23, 42, 0.06);
    --shadow-md: 0 4px 6px -1px rgba(15, 23, 42, 0.07), 0 2px 4px -2px rgba(15, 23, 42, 0.05);
    --shadow-lg: 0 12px 24px -4px rgba(15, 23, 42, 0.10), 0 4px 8px -2px rgba(15, 23, 42, 0.05);
    --shadow-card: 0 1px 3px rgba(15, 23, 42, 0.05), 0 0 0 1px rgba(15, 23, 42, 0.04);
    --transition: 180ms cubic-bezier(0.16, 1, 0.3, 1);
}}

html, body, [class*="css"] {{
    font-family: var(--font-body) !important;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    text-rendering: optimizeLegibility;
}}

/* ── Custom Scrollbar ── */
::-webkit-scrollbar {{ width: 6px; height: 6px; }}
::-webkit-scrollbar-track {{ background: transparent; }}
::-webkit-scrollbar-thumb {{ background: rgba(100, 116, 139, 0.28); border-radius: 999px; }}
::-webkit-scrollbar-thumb:hover {{ background: rgba(100, 116, 139, 0.48); }}

body:not(.rs-logged-in) [data-testid="collapsedControl"],
body:not(.rs-logged-in) [data-testid="stSidebarCollapsedControl"] {{ display: none !important; }}

/* ══════════════════════════════════════════════════════════════════════════
   SIDEBAR NAVIGATION & CONTROLS
   ══════════════════════════════════════════════════════════════════════════ */
[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, #090E1A 0%, #0F172A 100%) !important;
    border-right: 1px solid rgba(255, 255, 255, 0.07) !important;
}}
[data-testid="stSidebar"] * {{ color: var(--nav-text) !important; }}
[data-testid="stSidebar"] .stMarkdown h1,
[data-testid="stSidebar"] .stMarkdown h2,
[data-testid="stSidebar"] .stMarkdown h3 {{ color: {WHITE} !important; }}
[data-testid="stSidebar"]::-webkit-scrollbar {{ width: 4px; }}
[data-testid="stSidebar"]::-webkit-scrollbar-thumb {{ background: rgba(255, 255, 255, 0.12); border-radius: 999px; }}

.nav-group-label {{
    font-size: 0.63rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.09em !important;
    text-transform: uppercase !important;
    color: #64748B !important;
    padding: 16px 12px 6px !important;
    margin: 0 !important;
    display: flex !important;
    align-items: center !important;
}}

[data-testid="stSidebar"] .stButton > button {{
    background: transparent !important;
    border: 1px solid transparent !important;
    color: #94A3B8 !important;
    text-align: left !important;
    justify-content: flex-start !important;
    padding: 7px 12px !important;
    border-radius: 8px !important;
    font-size: 0.81rem !important;
    width: 100% !important;
    font-weight: 500 !important;
    margin: 1px 0 !important;
    line-height: 1.45 !important;
    min-height: 36px !important;
    height: auto !important;
    letter-spacing: -0.005em !important;
    transition: all var(--transition) !important;
    box-shadow: none !important;
}}
[data-testid="stSidebar"] .stButton > button p {{
    font-size: 0.81rem !important;
    font-weight: inherit !important;
    color: inherit !important;
    margin: 0 !important;
}}
[data-testid="stSidebar"] .stButton > button:hover {{
    background: rgba(255, 255, 255, 0.055) !important;
    color: #F8FAFC !important;
    border-color: rgba(255, 255, 255, 0.06) !important;
    transform: translateX(2px) !important;
}}
[data-testid="stSidebar"] .stButton > button:focus {{
    box-shadow: none !important;
    outline: none !important;
}}

/* Tombol Logout di Sidebar */
[data-testid="stSidebar"] .st-key-btn_logout button {{
    background: rgba(239, 68, 68, 0.08) !important;
    border: 1px solid rgba(239, 68, 68, 0.22) !important;
    color: #FCA5A5 !important;
    justify-content: center !important;
    text-align: center !important;
    font-weight: 600 !important;
    font-size: 0.76rem !important;
    margin-top: 6px !important;
    min-height: 32px !important;
    padding: 5px 10px !important;
}}
[data-testid="stSidebar"] .st-key-btn_logout button:hover {{
    background: rgba(239, 68, 68, 0.16) !important;
    border-color: rgba(239, 68, 68, 0.4) !important;
    color: #FEE2E2 !important;
    transform: none !important;
}}

[data-testid="stSidebar"] .stButton {{ margin-bottom: 0 !important; margin-top: 0 !important; }}
[data-testid="stSidebar"] .element-container {{ margin-bottom: 0 !important; margin-top: 0 !important; }}
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {{ gap: 2px !important; }}
[data-testid="stSidebar"] hr {{
    border: none !important;
    border-top: 1px solid rgba(255, 255, 255, 0.07) !important;
    margin: 12px 4px !important;
}}

/* Input & Select di Sidebar */
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stTextInput label,
[data-testid="stSidebar"] .stSlider label,
[data-testid="stSidebar"] .stNumberInput label {{
    font-size: 0.68rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.05em !important;
    text-transform: uppercase !important;
    color: #94A3B8 !important;
    margin-bottom: 4px !important;
}}
[data-testid="stSidebar"] .stSelectbox > div > div,
[data-testid="stSidebar"] .stTextInput input,
[data-testid="stSidebar"] .stNumberInput input {{
    background: rgba(15, 23, 42, 0.65) !important;
    border: 1px solid rgba(255, 255, 255, 0.12) !important;
    border-radius: 8px !important;
    color: #F1F5F9 !important;
    font-size: 0.8rem !important;
    transition: border-color var(--transition), box-shadow var(--transition) !important;
}}
[data-testid="stSidebar"] .stSelectbox > div > div:hover,
[data-testid="stSidebar"] .stTextInput input:hover,
[data-testid="stSidebar"] .stNumberInput input:hover {{
    border-color: rgba(255, 255, 255, 0.22) !important;
}}
[data-testid="stSidebar"] .stTextInput input:focus,
[data-testid="stSidebar"] .stNumberInput input:focus {{
    border-color: {BLUE3} !important;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.18) !important;
}}

/* ══════════════════════════════════════════════════════════════════════════
   MAIN CONTAINER & HERO HEADER
   ══════════════════════════════════════════════════════════════════════════ */
section[data-testid="stMain"] .block-container {{
    padding-top: 1.75rem !important;
    padding-bottom: 3.5rem !important;
    max-width: 1140px !important;
}}

.rs-header {{
    background: linear-gradient(135deg, #090E1A 0%, #0F172A 45%, #1E3A8A 100%);
    padding: 2rem 2.25rem;
    border-radius: var(--radius-lg);
    margin-bottom: 1.5rem;
    position: relative;
    overflow: hidden;
    display: flex;
    align-items: center;
    gap: 22px;
    border: 1px solid rgba(255, 255, 255, 0.08);
    box-shadow: 0 12px 32px -4px rgba(9, 14, 26, 0.28), inset 0 1px 0 rgba(255, 255, 255, 0.1);
}}
.rs-header::before {{
    content: '';
    position: absolute;
    left: -80px;
    bottom: -100px;
    width: 280px;
    height: 280px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(59, 130, 246, 0.22) 0%, transparent 70%);
    pointer-events: none;
}}
.rs-header::after {{
    content: '';
    position: absolute;
    right: -60px;
    top: -80px;
    width: 300px;
    height: 300px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(99, 102, 241, 0.18) 0%, transparent 70%);
    pointer-events: none;
}}
.rs-header .rs-header-texture {{
    position: absolute;
    inset: 0;
    background-image:
        linear-gradient(rgba(255, 255, 255, 0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255, 255, 255, 0.03) 1px, transparent 1px);
    background-size: 28px 28px;
    mask-image: radial-gradient(ellipse at center, black 40%, transparent 90%);
    -webkit-mask-image: radial-gradient(ellipse at center, black 40%, transparent 90%);
    pointer-events: none;
}}
.rs-header-icon {{
    background: linear-gradient(135deg, rgba(255, 255, 255, 0.14), rgba(255, 255, 255, 0.05));
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid rgba(255, 255, 255, 0.18);
    border-radius: 14px;
    width: 64px;
    height: 64px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    position: relative;
    z-index: 1;
    font-size: 28px;
    color: {WHITE};
    box-shadow: 0 8px 20px rgba(0, 0, 0, 0.25), inset 0 1px 0 rgba(255, 255, 255, 0.2);
}}
.rs-header h1 {{
    font-family: var(--font-display) !important;
    font-size: 1.85rem !important;
    font-weight: 800 !important;
    color: {WHITE} !important;
    margin: 0 0 0.3rem !important;
    position: relative;
    z-index: 1;
    letter-spacing: -0.03em !important;
    line-height: 1.2 !important;
}}
.rs-header p {{
    color: #BFDBFE !important;
    font-size: 0.86rem !important;
    margin: 0 !important;
    position: relative;
    z-index: 1;
    font-weight: 400 !important;
    letter-spacing: 0.005em !important;
    line-height: 1.5 !important;
}}
.rs-logo-link {{ text-decoration: none; color: {BLUE3} !important; font-size: 0.8rem; }}

/* ══════════════════════════════════════════════════════════════════════════
   GREETING BAR, METRICS & WORKFLOW STEPS
   ══════════════════════════════════════════════════════════════════════════ */
.rs-greeting {{
    background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: var(--radius-md);
    padding: 14px 20px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 1rem;
    box-shadow: var(--shadow-sm);
}}
.rs-greeting-text {{
    font-size: 0.92rem;
    color: #F8FAFC;
    font-weight: 600;
    letter-spacing: -0.015em;
    display: flex;
    align-items: center;
    gap: 8px;
}}
.rs-greeting-sub {{
    font-size: 0.76rem;
    color: #94A3B8;
    margin-top: 2px;
}}
.rs-greeting-badge {{
    background: linear-gradient(135deg, #FBBF24, #D97706);
    border-radius: 6px;
    padding: 4px 12px;
    font-size: 0.68rem;
    color: #0F172A;
    font-weight: 800;
    letter-spacing: 0.05em;
    box-shadow: 0 2px 10px rgba(245, 158, 11, 0.35);
}}

/* Metric Cards */
.rs-metric {{
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: var(--radius-md);
    padding: 18px 16px;
    text-align: left;
    transition: transform var(--transition), box-shadow var(--transition), border-color var(--transition);
    position: relative;
    overflow: hidden;
    box-shadow: var(--shadow-sm);
}}
.rs-metric::before {{
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
    background: linear-gradient(90deg, {BLUE}, {BLUE3}, {INDIGO});
}}
.rs-metric:hover {{
    transform: translateY(-3px);
    border-color: #CBD5E1;
    box-shadow: var(--shadow-lg);
}}
.rs-metric-label {{
    font-size: 0.68rem;
    color: #64748B;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 8px;
    font-weight: 700;
}}
.rs-metric-value {{
    font-family: var(--font-display);
    font-size: 1.75rem;
    font-weight: 800;
    color: #0F172A;
    letter-spacing: -0.03em;
    line-height: 1.1;
    font-variant-numeric: tabular-nums;
}}
.rs-metric-sub {{
    font-size: 0.74rem;
    color: #64748B;
    margin-top: 6px;
    font-weight: 500;
}}

/* Steps Grid */
.rs-step-full {{ margin-bottom: 10px; }}
.rs-step {{
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-left: 3.5px solid {BLUE2};
    border-radius: var(--radius-md);
    padding: 15px 18px;
    display: flex;
    align-items: flex-start;
    gap: 14px;
    transition: transform var(--transition), box-shadow var(--transition), border-color var(--transition);
    margin-bottom: 10px;
    box-shadow: var(--shadow-sm);
}}
.rs-step:hover {{
    transform: translateY(-2px);
    border-color: #BFDBFE;
    border-left-color: {BLUE};
    box-shadow: var(--shadow-md);
}}
.rs-step-num {{
    background: linear-gradient(135deg, {BLUE}, {BLUE3});
    color: {WHITE};
    width: 28px;
    height: 28px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: var(--font-mono);
    font-weight: 700;
    font-size: 0.74rem;
    flex-shrink: 0;
    box-shadow: 0 2px 8px rgba(37, 99, 235, 0.28);
}}
.rs-step-title {{
    font-weight: 700;
    color: #0F172A;
    font-size: 0.87rem;
    letter-spacing: -0.01em;
}}
.rs-step-desc {{
    font-size: 0.78rem;
    color: #475569;
    margin-top: 3px;
    line-height: 1.5;
}}

/* ══════════════════════════════════════════════════════════════════════════
   NARRATIVE CARDS, BADGES & CALLOUTS
   ══════════════════════════════════════════════════════════════════════════ */
.rs-narasi {{
    background: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-left: 4px solid {BLUE2};
    border-radius: var(--radius-md);
    padding: 1.15rem 1.35rem;
    font-size: 0.88rem;
    line-height: 1.72;
    color: #0F172A;
    margin-top: 0.6rem;
    box-shadow: var(--shadow-sm);
}}
.rs-ai-narasi {{
    background: linear-gradient(135deg, #EEF2FF 0%, #F5F3FF 100%);
    border: 1px solid #C7D2FE;
    border-left: 4px solid {INDIGO};
    border-radius: var(--radius-md);
    padding: 1.15rem 1.35rem;
    font-size: 0.88rem;
    line-height: 1.75;
    color: #1E1B4B;
    margin-top: 0.6rem;
    box-shadow: var(--shadow-sm);
}}
.rs-ai-badge {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: linear-gradient(135deg, {INDIGO}, {VIOLET});
    color: {WHITE};
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    padding: 4px 11px;
    border-radius: 999px;
    margin-bottom: 10px;
    text-transform: uppercase;
    box-shadow: 0 2px 8px rgba(79, 70, 229, 0.28);
}}

.rs-section-title {{
    font-family: var(--font-display) !important;
    font-size: 1.45rem !important;
    font-weight: 800 !important;
    color: #0F172A;
    margin-bottom: 0.25rem;
    letter-spacing: -0.025em;
}}
.rs-section-sub {{
    font-size: 0.83rem;
    color: #64748B;
    margin-bottom: 1.15rem;
    line-height: 1.5;
}}

.badge-valid      {{ background: #ECFDF5; color: #047857; border: 1px solid #A7F3D0; padding: 3px 10px; border-radius: 999px; font-size: 0.72rem; font-weight: 600; }}
.badge-invalid    {{ background: #FEF2F2; color: #B91C1C; border: 1px solid #FECACA; padding: 3px 10px; border-radius: 999px; font-size: 0.72rem; font-weight: 600; }}
.badge-reliable   {{ background: #ECFDF5; color: #047857; border: 1px solid #A7F3D0; padding: 3px 12px; border-radius: 999px; font-size: 0.76rem; font-weight: 600; }}
.badge-unreliable {{ background: #FEF2F2; color: #B91C1C; border: 1px solid #FECACA; padding: 3px 12px; border-radius: 999px; font-size: 0.76rem; font-weight: 600; }}

.pro-badge {{
    background: linear-gradient(135deg, {BLUE}, {NAVY2});
    color: {WHITE};
    padding: 3px 12px;
    border-radius: 999px;
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    box-shadow: 0 2px 6px rgba(29, 78, 216, 0.25);
}}
.pro-lock-badge {{
    background: linear-gradient(135deg, {INDIGO}, {VIOLET});
    color: {WHITE};
    padding: 2px 8px;
    border-radius: 999px;
    font-size: 0.62rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    margin-left: 5px;
    vertical-align: middle;
    box-shadow: 0 1px 4px rgba(79, 70, 229, 0.25);
}}

.rs-hint-bar {{
    background: rgba(37, 99, 235, 0.08);
    border: 1px solid rgba(59, 130, 246, 0.25);
    border-radius: var(--radius-md);
    padding: 12px 16px;
    font-size: 0.83rem;
    color: #1E40AF;
    margin: 10px 0;
    line-height: 1.6;
}}

.rs-cta-wizard {{
    background: linear-gradient(135deg, rgba(37, 99, 235, 0.08) 0%, rgba(79, 70, 229, 0.08) 100%);
    border: 1px solid rgba(99, 102, 241, 0.28);
    border-radius: var(--radius-md);
    padding: 20px 22px;
    display: block;
    margin-bottom: 10px;
    box-shadow: var(--shadow-sm);
}}
.rs-cta-title {{
    font-size: 0.96rem;
    font-weight: 700;
    color: #1E3A8A;
    margin-bottom: 5px;
    letter-spacing: -0.015em;
}}
.rs-cta-desc {{
    font-size: 0.81rem;
    color: #334155;
    line-height: 1.55;
    margin-bottom: 0;
}}

/* ══════════════════════════════════════════════════════════════════════════
   CHAT INTERFACE & DATA TABLES
   ══════════════════════════════════════════════════════════════════════════ */
.chat-container {{
    max-height: 440px;
    overflow-y: auto;
    padding: 1rem;
    background: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: var(--radius-md);
    margin-bottom: 1rem;
}}
.chat-bubble-user {{
    background: linear-gradient(135deg, {BLUE}, {BLUE3});
    color: {WHITE};
    padding: 0.7rem 1.05rem;
    border-radius: 14px 14px 4px 14px;
    margin: 0.5rem 0 0.5rem 22%;
    font-size: 0.86rem;
    line-height: 1.55;
    box-shadow: 0 2px 8px rgba(37, 99, 235, 0.2);
}}
.chat-bubble-ai {{
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    color: #0F172A;
    padding: 0.7rem 1.05rem;
    border-radius: 14px 14px 14px 4px;
    margin: 0.5rem 22% 0.5rem 0;
    font-size: 0.86rem;
    line-height: 1.6;
    box-shadow: var(--shadow-sm);
}}
.chat-label {{
    font-size: 0.66rem;
    color: #64748B;
    margin-bottom: 3px;
    letter-spacing: 0.05em;
    font-weight: 700;
    text-transform: uppercase;
}}

.stDataFrame {{
    border-radius: var(--radius-md) !important;
    overflow: hidden !important;
    box-shadow: var(--shadow-sm) !important;
    border: 1px solid {BORDER} !important;
}}

/* ══════════════════════════════════════════════════════════════════════════
   EXPANDERS, TABS, BUTTONS & METRICS
   ══════════════════════════════════════════════════════════════════════════ */
[data-testid="stExpander"] {{
    border: 1px solid {BORDER} !important;
    border-radius: var(--radius-md) !important;
    box-shadow: var(--shadow-sm) !important;
    overflow: hidden !important;
    background: {BG_CARD} !important;
    transition: border-color var(--transition) !important;
}}
[data-testid="stExpander"]:hover {{
    border-color: {BORDER2} !important;
}}
[data-testid="stExpander"] summary {{
    font-weight: 600 !important;
    font-size: 0.87rem !important;
    color: #0F172A !important;
    padding: 12px 16px !important;
    background: {BG_CARD} !important;
}}
[data-testid="stExpander"] > div[data-testid="stExpanderDetails"] {{
    background: {BG_CARD} !important;
    padding: 6px 18px 16px !important;
    border-top: 1px solid {BG_SOFT} !important;
}}
[data-testid="stExpander"] [data-testid="stVerticalBlock"] {{ background: {BG_CARD} !important; }}
[data-testid="stExpander"] p,
[data-testid="stExpander"] td,
[data-testid="stExpander"] th,
[data-testid="stExpander"] li,
[data-testid="stExpander"] label {{ color: #0F172A !important; }}
[data-testid="stExpander"] table {{
    background: {BG_CARD} !important;
    border-collapse: collapse !important;
    width: 100% !important;
    border-radius: 8px !important;
    overflow: hidden !important;
}}
[data-testid="stExpander"] thead tr {{
    background: {BG_SOFT} !important;
    border-bottom: 2px solid {BORDER} !important;
}}
[data-testid="stExpander"] thead th {{
    background: {BG_SOFT} !important;
    color: #0F172A !important;
    font-weight: 700 !important;
    font-size: 0.78rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.04em !important;
    padding: 10px 12px !important;
    text-align: left !important;
}}
[data-testid="stExpander"] tbody tr {{
    border-bottom: 1px solid {BORDER} !important;
    background: {BG_CARD} !important;
}}
[data-testid="stExpander"] tbody tr:nth-child(even) {{ background: {BG_SOFT} !important; }}
[data-testid="stExpander"] tbody td {{
    color: #1E293B !important;
    font-size: 0.82rem !important;
    padding: 8px 12px !important;
    background: transparent !important;
}}
[data-testid="stExpander"] .stMarkdown p,
[data-testid="stExpander"] .stMarkdown span,
[data-testid="stExpander"] .stMarkdown li,
[data-testid="stExpander"] .stMarkdown h1,
[data-testid="stExpander"] .stMarkdown h2,
[data-testid="stExpander"] .stMarkdown h3,
[data-testid="stExpander"] .stMarkdown h4 {{ color: #0F172A !important; }}

[data-testid="stAlert"] {{
    border-radius: var(--radius-md) !important;
    border-width: 1px !important;
    font-size: 0.85rem !important;
}}

/* Tabs */
[data-baseweb="tab-list"] {{
    gap: 6px !important;
    background: transparent !important;
    border-bottom: 1px solid {BORDER} !important;
    padding-bottom: 0 !important;
}}
[data-baseweb="tab"] {{
    border-radius: var(--radius-sm) var(--radius-sm) 0 0 !important;
    font-size: 0.84rem !important;
    font-weight: 600 !important;
    padding: 9px 16px !important;
    color: {SLATE} !important;
    background: transparent !important;
    border: none !important;
    transition: all var(--transition) !important;
}}
[data-baseweb="tab"]:hover {{
    color: #0F172A !important;
    background: rgba(15, 23, 42, 0.035) !important;
}}
[aria-selected="true"][data-baseweb="tab"] {{
    color: {BLUE2} !important;
    font-weight: 700 !important;
    background: rgba(37, 99, 235, 0.05) !important;
    border-bottom: 2.5px solid {BLUE2} !important;
}}

/* Primary Button */
[data-testid="stMain"] .stButton > button[kind="primary"],
[data-testid="stMain"] .stButton > button[data-testid*="primary"] {{
    background: linear-gradient(135deg, {BLUE} 0%, {BLUE3} 100%) !important;
    color: {WHITE} !important;
    border: 1px solid rgba(255, 255, 255, 0.12) !important;
    border-radius: var(--radius-sm) !important;
    font-weight: 600 !important;
    font-size: 0.86rem !important;
    padding: 0.55rem 1.15rem !important;
    letter-spacing: -0.005em !important;
    box-shadow: 0 4px 12px rgba(37, 99, 235, 0.25), inset 0 1px 0 rgba(255, 255, 255, 0.15) !important;
    transition: all var(--transition) !important;
}}
[data-testid="stMain"] .stButton > button[kind="primary"]:hover {{
    box-shadow: 0 6px 18px rgba(37, 99, 235, 0.36) !important;
    transform: translateY(-1px) !important;
    filter: brightness(1.05) !important;
}}

/* Secondary Button in Main Content */
[data-testid="stMain"] .stButton > button:not([kind="primary"]) {{
    background: {BLUE2} !important;
    color: {WHITE} !important;
    border: 1px solid {BLUE3} !important;
    border-radius: var(--radius-sm) !important;
    font-size: 0.83rem !important;
    font-weight: 600 !important;
    padding: 0.5rem 1rem !important;
    box-shadow: 0 2px 6px rgba(37, 99, 235, 0.18) !important;
    transition: all var(--transition) !important;
}}
[data-testid="stMain"] .stButton > button:not([kind="primary"]):hover {{
    background: {BLUE} !important;
    color: {WHITE} !important;
    border-color: {BLUE2} !important;
    box-shadow: 0 4px 12px rgba(37, 99, 235, 0.28) !important;
    transform: translateY(-1px) !important;
}}

[data-testid="stMetricValue"] {{
    font-family: var(--font-display) !important;
    font-size: 1.7rem !important;
    font-weight: 800 !important;
    letter-spacing: -0.03em !important;
    color: #0F172A !important;
    font-variant-numeric: tabular-nums !important;
}}

.rs-footer {{
    margin-top: 3.5rem;
    padding-top: 1.5rem;
    border-top: 1px solid rgba(148, 163, 184, 0.18);
    text-align: center;
    font-size: 0.76rem;
    color: {SLATE};
    line-height: 1.7;
}}
.rs-footer a {{ color: {BLUE2}; text-decoration: none; font-weight: 600; }}
.rs-footer a:hover {{ color: {BLUE}; text-decoration: underline; }}
.rs-footer b {{ color: #334155; }}

/* ══════════════════════════════════════════════════════════════════════════
   LIGHT MODE OVERRIDES
   ══════════════════════════════════════════════════════════════════════════ */
body.rs-light .rs-metric,
[data-theme="light"] .rs-metric {{ background: {BG_CARD} !important; border-color: {BORDER} !important; box-shadow: var(--shadow-card) !important; }}
body.rs-light .rs-metric-label,
[data-theme="light"] .rs-metric-label {{ color: {SLATE} !important; }}
body.rs-light .rs-metric-value,
[data-theme="light"] .rs-metric-value {{ color: #0F172A !important; }}
body.rs-light .rs-metric-sub,
[data-theme="light"] .rs-metric-sub   {{ color: {SLATE} !important; }}
body.rs-light .rs-metric:hover,
[data-theme="light"] .rs-metric:hover {{ border-color: {BORDER2} !important; box-shadow: var(--shadow-md) !important; }}

body.rs-light .rs-step,
[data-theme="light"] .rs-step {{ background: {BG_CARD} !important; border-color: {BORDER} !important; box-shadow: var(--shadow-card) !important; }}
body.rs-light .rs-step:hover,
[data-theme="light"] .rs-step:hover {{ border-color: #93C5FD !important; box-shadow: var(--shadow-md) !important; }}
body.rs-light .rs-step-title,
[data-theme="light"] .rs-step-title {{ color: #0F172A !important; }}
body.rs-light .rs-step-desc,
[data-theme="light"] .rs-step-desc  {{ color: #475569 !important; }}

body.rs-light .rs-narasi,
[data-theme="light"] .rs-narasi {{ background: linear-gradient(135deg, #F8FAFC 0%, #EFF6FF 100%) !important; color: #0F172A !important; box-shadow: var(--shadow-sm) !important; }}
body.rs-light .rs-ai-narasi,
[data-theme="light"] .rs-ai-narasi {{ background: linear-gradient(135deg, {BG_AI} 0%, #F5F3FF 100%) !important; color: #1E1B4B !important; box-shadow: var(--shadow-sm) !important; }}

body.rs-light .rs-cta-wizard,
[data-theme="light"] .rs-cta-wizard {{
    background: linear-gradient(135deg, #EFF6FF 0%, #EEF2FF 100%) !important;
    border-color: #BFDBFE !important;
    box-shadow: 0 2px 10px rgba(37, 99, 235, 0.08) !important;
}}
body.rs-light .rs-cta-title,
[data-theme="light"] .rs-cta-title {{ color: #1E3A8A !important; }}
body.rs-light .rs-cta-desc,
[data-theme="light"] .rs-cta-desc  {{ color: #1E40AF !important; }}

body.rs-light .rs-hint-bar,
[data-theme="light"] .rs-hint-bar {{
    background: #EFF6FF !important;
    border-color: #BFDBFE !important;
    color: #1E3A8A !important;
}}

body.rs-light .rs-section-title,
[data-theme="light"] .rs-section-title {{ color: #0F172A !important; }}
body.rs-light .rs-section-sub,
[data-theme="light"] .rs-section-sub   {{ color: {SLATE} !important; }}

body.rs-light .rs-footer,
[data-theme="light"] .rs-footer {{ border-top-color: {BORDER} !important; color: {SLATE} !important; }}
body.rs-light .rs-footer b,
[data-theme="light"] .rs-footer b {{ color: #0F172A !important; }}

/* ══════════════════════════════════════════════════════════════════════════
   DARK MODE OVERRIDES
   ══════════════════════════════════════════════════════════════════════════ */
body.rs-dark .rs-metric,
[data-theme="dark"] .rs-metric {{ background: #111C33 !important; border-color: rgba(255, 255, 255, 0.08) !important; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25) !important; }}
body.rs-dark .rs-metric-label,
[data-theme="dark"] .rs-metric-label {{ color: #94A3B8 !important; }}
body.rs-dark .rs-metric-value,
[data-theme="dark"] .rs-metric-value {{ color: #F8FAFC !important; }}
body.rs-dark .rs-metric-sub,
[data-theme="dark"] .rs-metric-sub   {{ color: #94A3B8 !important; }}

body.rs-dark .rs-step,
[data-theme="dark"] .rs-step {{ background: #111C33 !important; border-color: rgba(255, 255, 255, 0.08) !important; border-left-color: {BLUE3} !important; }}
body.rs-dark .rs-step:hover,
[data-theme="dark"] .rs-step:hover {{ background: #162340 !important; border-color: rgba(59, 130, 246, 0.35) !important; }}
body.rs-dark .rs-step-title,
[data-theme="dark"] .rs-step-title {{ color: #F1F5F9 !important; }}
body.rs-dark .rs-step-desc,
[data-theme="dark"] .rs-step-desc  {{ color: #94A3B8 !important; }}

body.rs-dark .rs-narasi,
[data-theme="dark"] .rs-narasi {{ background: rgba(30, 58, 138, 0.22) !important; border-color: rgba(59, 130, 246, 0.2) !important; border-left-color: {BLUE3} !important; color: #E2E8F0 !important; }}
body.rs-dark .rs-ai-narasi,
[data-theme="dark"] .rs-ai-narasi {{ background: rgba(49, 46, 129, 0.24) !important; border-color: rgba(99, 102, 241, 0.24) !important; border-left-color: #818CF8 !important; color: #E0E7FF !important; }}

body.rs-dark .rs-cta-wizard,
[data-theme="dark"] .rs-cta-wizard {{ background: linear-gradient(135deg, rgba(30, 58, 138, 0.3) 0%, rgba(49, 46, 129, 0.28) 100%) !important; border-color: rgba(99, 102, 241, 0.35) !important; }}
body.rs-dark .rs-cta-title,
[data-theme="dark"] .rs-cta-title {{ color: #BFDBFE !important; }}
body.rs-dark .rs-cta-desc,
[data-theme="dark"] .rs-cta-desc  {{ color: #93C5FD !important; }}

body.rs-dark .rs-hint-bar,
[data-theme="dark"] .rs-hint-bar {{ background: rgba(30, 58, 138, 0.25) !important; border-color: rgba(59, 130, 246, 0.32) !important; color: #BFDBFE !important; }}

body.rs-dark .rs-section-title,
[data-theme="dark"] .rs-section-title {{ color: #F8FAFC !important; }}
body.rs-dark .rs-section-sub,
[data-theme="dark"] .rs-section-sub   {{ color: #94A3B8 !important; }}

body.rs-dark .rs-footer,
[data-theme="dark"] .rs-footer {{ border-top-color: rgba(255, 255, 255, 0.08) !important; color: #64748B !important; }}
body.rs-dark .rs-footer b,
[data-theme="dark"] .rs-footer b {{ color: #CBD5E1 !important; }}

body.rs-dark [data-testid="stExpander"],
[data-theme="dark"] [data-testid="stExpander"] {{ background: #111C33 !important; border-color: rgba(255, 255, 255, 0.09) !important; }}
body.rs-dark [data-testid="stExpander"] summary,
[data-theme="dark"] [data-testid="stExpander"] summary {{ background: #111C33 !important; color: #F1F5F9 !important; }}
body.rs-dark [data-testid="stExpander"] > div[data-testid="stExpanderDetails"],
[data-theme="dark"] [data-testid="stExpander"] > div[data-testid="stExpanderDetails"] {{ background: #111C33 !important; border-top-color: rgba(255, 255, 255, 0.06) !important; }}
body.rs-dark [data-testid="stExpander"] [data-testid="stVerticalBlock"],
[data-theme="dark"] [data-testid="stExpander"] [data-testid="stVerticalBlock"] {{ background: #111C33 !important; }}
body.rs-dark [data-testid="stExpander"] p,
body.rs-dark [data-testid="stExpander"] td,
body.rs-dark [data-testid="stExpander"] th,
body.rs-dark [data-testid="stExpander"] li,
body.rs-dark [data-testid="stExpander"] label,
body.rs-dark [data-testid="stExpander"] .stMarkdown p,
body.rs-dark [data-testid="stExpander"] .stMarkdown span,
body.rs-dark [data-testid="stExpander"] .stMarkdown li,
body.rs-dark [data-testid="stExpander"] .stMarkdown h1,
body.rs-dark [data-testid="stExpander"] .stMarkdown h2,
body.rs-dark [data-testid="stExpander"] .stMarkdown h3,
body.rs-dark [data-testid="stExpander"] .stMarkdown h4,
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
[data-theme="dark"] [data-testid="stExpander"] .stMarkdown h4 {{ color: #E2E8F0 !important; }}
body.rs-dark [data-testid="stExpander"] table,
[data-theme="dark"] [data-testid="stExpander"] table {{ background: #111C33 !important; }}
body.rs-dark [data-testid="stExpander"] thead tr,
[data-theme="dark"] [data-testid="stExpander"] thead tr {{ background: #0B1324 !important; border-bottom-color: rgba(255, 255, 255, 0.1) !important; }}
body.rs-dark [data-testid="stExpander"] thead th,
[data-theme="dark"] [data-testid="stExpander"] thead th {{ background: #0B1324 !important; color: #F8FAFC !important; }}
body.rs-dark [data-testid="stExpander"] tbody tr,
[data-theme="dark"] [data-testid="stExpander"] tbody tr {{ background: #111C33 !important; border-bottom-color: rgba(255, 255, 255, 0.06) !important; }}
body.rs-dark [data-testid="stExpander"] tbody tr:nth-child(even),
[data-theme="dark"] [data-testid="stExpander"] tbody tr:nth-child(even) {{ background: #0E172B !important; }}
body.rs-dark [data-testid="stExpander"] tbody td,
[data-theme="dark"] [data-testid="stExpander"] tbody td {{ color: #CBD5E1 !important; }}

body.rs-dark [data-baseweb="tab"],
[data-theme="dark"] [data-baseweb="tab"] {{ color: #94A3B8 !important; }}
body.rs-dark [data-baseweb="tab"]:hover,
[data-theme="dark"] [data-baseweb="tab"]:hover {{ color: #F1F5F9 !important; background: rgba(255, 255, 255, 0.05) !important; }}
body.rs-dark [aria-selected="true"][data-baseweb="tab"],
[data-theme="dark"] [aria-selected="true"][data-baseweb="tab"] {{ color: #60A5FA !important; border-bottom-color: #60A5FA !important; background: rgba(59, 130, 246, 0.1) !important; }}
body.rs-dark [data-baseweb="tab-list"],
[data-theme="dark"] [data-baseweb="tab-list"] {{ border-bottom-color: rgba(255, 255, 255, 0.08) !important; }}

body.rs-dark .stDataFrame,
[data-theme="dark"] .stDataFrame {{ border-color: rgba(255, 255, 255, 0.08) !important; }}
body.rs-dark [data-testid="stMetricValue"],
[data-theme="dark"] [data-testid="stMetricValue"] {{ color: #F8FAFC !important; }}
body.rs-dark .chat-container,
[data-theme="dark"] .chat-container {{ background: #0B1324 !important; border-color: rgba(255, 255, 255, 0.08) !important; }}
body.rs-dark .chat-bubble-ai,
[data-theme="dark"] .chat-bubble-ai {{ background: #111C33 !important; border-color: rgba(255, 255, 255, 0.08) !important; color: #E2E8F0 !important; }}
body.rs-dark .chat-label,
[data-theme="dark"] .chat-label {{ color: #94A3B8 !important; }}

body.rs-dark .badge-valid,
[data-theme="dark"] .badge-valid {{ background: rgba(16, 185, 129, 0.18) !important; color: #6EE7B7 !important; border-color: rgba(110, 231, 183, 0.25) !important; }}
body.rs-dark .badge-invalid,
[data-theme="dark"] .badge-invalid {{ background: rgba(239, 68, 68, 0.18) !important; color: #FCA5A5 !important; border-color: rgba(252, 165, 165, 0.25) !important; }}
body.rs-dark .badge-reliable,
[data-theme="dark"] .badge-reliable {{ background: rgba(16, 185, 129, 0.18) !important; color: #6EE7B7 !important; border-color: rgba(110, 231, 183, 0.25) !important; }}
body.rs-dark .badge-unreliable,
[data-theme="dark"] .badge-unreliable {{ background: rgba(239, 68, 68, 0.18) !important; color: #FCA5A5 !important; border-color: rgba(252, 165, 165, 0.25) !important; }}

[data-theme="dark"] [data-testid="stExpander"] .rs-narasi,
body.rs-dark [data-testid="stExpander"] .rs-narasi {{
    background: rgba(30, 58, 138, 0.22) !important;
    border-left-color: {BLUE3} !important;
    color: #E2E8F0 !important;
}}
[data-theme="dark"] [data-testid="stExpander"] .rs-narasi b,
[data-theme="dark"] [data-testid="stExpander"] .rs-narasi strong,
body.rs-dark [data-testid="stExpander"] .rs-narasi b,
body.rs-dark [data-testid="stExpander"] .rs-narasi strong {{
    color: #F8FAFC !important;
}}
[data-theme="dark"] [data-testid="stExpander"] .rs-narasi span,
body.rs-dark [data-testid="stExpander"] .rs-narasi span {{
    color: {BLUE4} !important;
}}
</style>"""


def inject_global_css() -> None:
    """Inject CSS global. Konten di-cache — aman dipanggil tiap rerun."""
    st.markdown(_global_css(), unsafe_allow_html=True)
    st.markdown("""<script>
(function() {
    function applyThemeClass() {
        try {
            var isDark = null;
            try {
                var stored = localStorage.getItem('streamlit:theme');
                if (!stored) stored = localStorage.getItem('stTheme');
                if (stored) {
                    var parsed = JSON.parse(stored);
                    var base = (parsed.base || parsed.theme || '').toLowerCase();
                    if (base === 'dark')  { isDark = true; }
                    if (base === 'light') { isDark = false; }
                }
            } catch(e) {}
            if (isDark === null) {
                try {
                    var bodyColor = window.getComputedStyle(document.body).color;
                    var cm = bodyColor.replace(/\\s/g,'').match(/rgb[a]?\\((\\d+),(\\d+),(\\d+)/);
                    if (cm) {
                        var lum = 0.299*parseInt(cm[1]) + 0.587*parseInt(cm[2]) + 0.114*parseInt(cm[3]);
                        isDark = lum > 128;
                    }
                } catch(e) {}
            }
            if (isDark === null) {
                try {
                    var targets = [
                        document.querySelector('.stApp'),
                        document.querySelector('[data-testid="stApp"]'),
                        document.querySelector('body')
                    ];
                    for (var i = 0; i < targets.length; i++) {
                        if (!targets[i]) continue;
                        var bg = window.getComputedStyle(targets[i]).backgroundColor;
                        var bm = bg.replace(/\\s/g,'').match(/rgb[a]?\\((\\d+),(\\d+),(\\d+)/);
                        if (!bm) continue;
                        var r=parseInt(bm[1]),g=parseInt(bm[2]),b=parseInt(bm[3]);
                        if (r===0&&g===0&&b===0) continue;
                        var lum2 = 0.299*r + 0.587*g + 0.114*b;
                        isDark = lum2 < 128;
                        break;
                    }
                } catch(e) {}
            }
            if (isDark === null) {
                isDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            }
            document.body.classList.remove('rs-light','rs-dark');
            document.body.classList.add(isDark ? 'rs-dark' : 'rs-light');
        } catch(e) {}
    }
    applyThemeClass();
    setTimeout(applyThemeClass, 200);
    setTimeout(applyThemeClass, 600);
    setTimeout(applyThemeClass, 1200);
    setTimeout(applyThemeClass, 2500);
    var origSetItem = localStorage.setItem.bind(localStorage);
    try {
        localStorage.setItem = function(k, v) {
            origSetItem(k, v);
            if (k === 'streamlit:theme' || k === 'stTheme') { setTimeout(applyThemeClass, 50); }
        };
    } catch(e) {}
    var obs = new MutationObserver(applyThemeClass);
    obs.observe(document.documentElement, { attributes: true });
})();
</script>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# LOGIN PAGE CSS — UNIFIED GLASSMORPHIC AUTH CARD
# ══════════════════════════════════════════════════════════════════════════════
_LOGIN_CSS: str = f"""<style>
.rs-footer {{ display: none; }}
header[data-testid="stHeader"] {{ display: none; }}
[data-testid="stSidebar"],
[data-testid="collapsedControl"],
[data-testid="stSidebarCollapsedControl"] {{ display: none !important; }}

[data-testid="stAppViewContainer"],
[data-testid="stApp"] {{
    background: radial-gradient(circle at 15% 20%, #172554 0%, #090E1A 52%, #060A12 100%) !important;
    position: relative;
}}
[data-testid="stAppViewContainer"]::before {{
    content: '';
    position: fixed;
    inset: 0;
    background-image:
        radial-gradient(ellipse at 20% 30%, rgba(37, 99, 235, 0.14) 0%, transparent 50%),
        radial-gradient(ellipse at 80% 75%, rgba(79, 70, 229, 0.12) 0%, transparent 50%);
    pointer-events: none;
    z-index: 0;
}}
[data-testid="stAppViewContainer"]::after {{
    content: '';
    position: fixed;
    inset: 0;
    background-image:
        linear-gradient(rgba(255, 255, 255, 0.025) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255, 255, 255, 0.025) 1px, transparent 1px);
    background-size: 32px 32px;
    mask-image: radial-gradient(ellipse at center, black 35%, transparent 85%);
    -webkit-mask-image: radial-gradient(ellipse at center, black 35%, transparent 85%);
    pointer-events: none;
    z-index: 0;
}}

/* Unified Auth Card Container */
section[data-testid="stMain"] .block-container {{
    margin-top: 4.5vh !important;
    margin-bottom: 4vh !important;
    max-width: 440px !important;
    margin-left: auto !important;
    margin-right: auto !important;
    padding: 0 1.75rem 1.85rem !important;
    background: rgba(15, 23, 42, 0.72) !important;
    backdrop-filter: blur(24px) saturate(1.5) !important;
    -webkit-backdrop-filter: blur(24px) saturate(1.5) !important;
    border: 1px solid rgba(255, 255, 255, 0.11) !important;
    border-radius: 22px !important;
    box-shadow:
        0 25px 60px -12px rgba(0, 0, 0, 0.65),
        0 0 0 1px rgba(255, 255, 255, 0.05),
        inset 0 1px 0 rgba(255, 255, 255, 0.12) !important;
    position: relative;
    z-index: 1;
}}

.signin-card {{
    margin: 0 -1.75rem 1.25rem !important;
    border-radius: 21px 21px 0 0 !important;
    overflow: hidden;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}}
.signin-card-header {{
    background: linear-gradient(135deg, #090E1A 0%, #1E293B 45%, #1D4ED8 100%);
    padding: 30px 24px 24px;
    text-align: center;
    position: relative;
    overflow: hidden;
}}
.signin-card-header::before {{
    content: '';
    position: absolute;
    right: -40px;
    top: -40px;
    width: 180px;
    height: 180px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(59, 130, 246, 0.25) 0%, transparent 70%);
    pointer-events: none;
}}
.signin-header-logo {{
    position: relative;
    z-index: 1;
    width: 58px;
    height: 58px;
    border-radius: 16px;
    background: rgba(255, 255, 255, 0.12);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.22);
    display: flex;
    align-items: center;
    justify-content: center;
    margin: 0 auto 14px;
    box-shadow: 0 8px 20px rgba(0, 0, 0, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.2);
}}
.signin-header-logo img {{
    width: 34px;
    height: 34px;
    object-fit: contain;
    filter: drop-shadow(0 2px 8px rgba(0, 0, 0, 0.3));
}}
.signin-header-title {{
    font-family: var(--font-display);
    font-size: 1.5rem;
    font-weight: 800;
    color: {WHITE};
    letter-spacing: -0.025em;
    position: relative;
    z-index: 1;
    margin: 0 0 4px;
}}
.signin-header-sub {{
    font-size: 0.76rem;
    color: #BFDBFE;
    position: relative;
    z-index: 1;
    letter-spacing: 0.01em;
    font-weight: 400;
}}
.signin-card-body {{ padding: 20px 22px 22px; }}

/* Segmented Control Tab Row */
.signin-tab-row {{
    display: flex;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    margin-bottom: 1.25rem;
    gap: 0;
}}
.signin-tab-row .stButton {{ flex: 1; }}
.signin-tab-row .stButton > button {{
    background: rgba(255, 255, 255, 0.03) !important;
    border: 1px solid rgba(255, 255, 255, 0.07) !important;
    border-bottom: 2px solid transparent !important;
    border-radius: 8px 8px 0 0 !important;
    color: #94A3B8 !important;
    font-size: 0.83rem !important;
    font-weight: 600 !important;
    padding: 9px 6px !important;
    width: 100% !important;
    margin-bottom: -1px !important;
    transition: all var(--transition) !important;
    box-shadow: none !important;
}}
.signin-tab-row .stButton > button:hover {{
    color: #F8FAFC !important;
    background: rgba(255, 255, 255, 0.06) !important;
}}
.signin-tab-active .stButton > button {{
    background: rgba(37, 99, 235, 0.15) !important;
    color: {WHITE} !important;
    font-weight: 700 !important;
    border-color: rgba(59, 130, 246, 0.25) !important;
    border-bottom: 2.5px solid {BLUE3} !important;
}}

/* Form Container & Inputs */
section[data-testid="stMain"] [data-testid="stForm"] {{
    border: none !important;
    padding: 0 !important;
    background: transparent !important;
}}
section[data-testid="stMain"] .stTextInput label {{
    font-size: 0.7rem !important;
    font-weight: 600 !important;
    color: #CBD5E1 !important;
    letter-spacing: 0.05em !important;
    text-transform: uppercase !important;
    margin-bottom: 4px !important;
}}
section[data-testid="stMain"] .stTextInput input,
section[data-testid="stMain"] .stTextInput input[type="text"],
section[data-testid="stMain"] .stTextInput input[type="password"],
section[data-testid="stMain"] .stTextInput input[type="email"] {{
    border: 1px solid rgba(255, 255, 255, 0.16) !important;
    border-radius: 10px !important;
    padding: 10px 14px !important;
    font-size: 0.86rem !important;
    background: rgba(9, 14, 26, 0.65) !important;
    background-color: rgba(9, 14, 26, 0.65) !important;
    color: {WHITE} !important;
    -webkit-text-fill-color: {WHITE} !important;
    caret-color: {BLUE3} !important;
    transition: all var(--transition) !important;
    box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.35) !important;
}}
section[data-testid="stMain"] .stTextInput div[data-baseweb="input"],
section[data-testid="stMain"] .stTextInput div[data-baseweb="base-input"],
section[data-testid="stMain"] .stTextInput [data-testid="textInputRootElement"] {{
    background: transparent !important;
    border-color: transparent !important;
}}
section[data-testid="stMain"] .stTextInput input:focus {{
    border-color: {BLUE3} !important;
    background: rgba(9, 14, 26, 0.88) !important;
    background-color: rgba(9, 14, 26, 0.88) !important;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2), inset 0 1px 2px rgba(0, 0, 0, 0.35) !important;
    color: {WHITE} !important;
    -webkit-text-fill-color: {WHITE} !important;
    outline: none !important;
}}
section[data-testid="stMain"] .stTextInput input:-webkit-autofill,
section[data-testid="stMain"] .stTextInput input:-webkit-autofill:hover,
section[data-testid="stMain"] .stTextInput input:-webkit-autofill:focus {{
    -webkit-text-fill-color: {WHITE} !important;
    -webkit-box-shadow: 0 0 0 1000px #0B1324 inset !important;
    caret-color: {WHITE} !important;
}}
section[data-testid="stMain"] .stTextInput input::placeholder {{
    color: rgba(148, 163, 184, 0.5) !important;
    -webkit-text-fill-color: rgba(148, 163, 184, 0.5) !important;
}}

/* Submit & Secondary Buttons in Auth */
section[data-testid="stMain"] .stForm [data-testid="stFormSubmitButton"] > button {{
    background: linear-gradient(135deg, {BLUE} 0%, {BLUE3} 100%) !important;
    color: {WHITE} !important;
    border: 1px solid rgba(255, 255, 255, 0.14) !important;
    border-radius: 10px !important;
    padding: 11px !important;
    font-size: 0.88rem !important;
    font-weight: 700 !important;
    width: 100% !important;
    margin-top: 4px !important;
    letter-spacing: 0.01em !important;
    transition: all var(--transition) !important;
    box-shadow: 0 4px 16px rgba(37, 99, 235, 0.38), inset 0 1px 0 rgba(255, 255, 255, 0.2) !important;
}}
section[data-testid="stMain"] .stForm [data-testid="stFormSubmitButton"] > button:hover {{
    box-shadow: 0 6px 22px rgba(37, 99, 235, 0.5) !important;
    transform: translateY(-1px) !important;
    filter: brightness(1.06) !important;
}}
section[data-testid="stMain"] .stButton > button {{
    background: rgba(255, 255, 255, 0.06) !important;
    border: 1px solid rgba(255, 255, 255, 0.14) !important;
    border-radius: 10px !important;
    color: #F1F5F9 !important;
    font-size: 0.83rem !important;
    font-weight: 600 !important;
    padding: 9px 12px !important;
    width: 100% !important;
    box-shadow: none !important;
    transition: all var(--transition) !important;
}}
section[data-testid="stMain"] .stButton > button:hover {{
    background: rgba(255, 255, 255, 0.11) !important;
    border-color: rgba(255, 255, 255, 0.25) !important;
    transform: translateY(-1px) !important;
}}

/* Auth Text Links */
.signin-link-btn-right {{ text-align: right; margin-top: 2px; margin-bottom: 6px; }}
.signin-link-btn-right .stButton > button {{
    background: transparent !important;
    border: none !important;
    color: #60A5FA !important;
    font-size: 0.74rem !important;
    font-weight: 600 !important;
    padding: 0 !important;
    height: auto !important;
    min-height: 0 !important;
    width: auto !important;
    float: right;
    box-shadow: none !important;
}}
.signin-link-btn-right .stButton > button:hover {{
    background: transparent !important;
    text-decoration: underline !important;
    transform: none !important;
}}
.signin-link-btn .stButton > button {{
    background: transparent !important;
    border: none !important;
    color: #60A5FA !important;
    font-size: 0.75rem !important;
    font-weight: 600 !important;
    padding: 4px 6px !important;
    height: auto !important;
    min-height: 0 !important;
    box-shadow: none !important;
}}
.signin-link-btn .stButton > button:hover {{
    background: rgba(59, 130, 246, 0.08) !important;
    text-decoration: underline !important;
    transform: none !important;
}}
.signin-link-btn-muted .stButton > button {{
    color: #94A3B8 !important;
    font-weight: 500 !important;
    font-size: 0.74rem !important;
}}

.signin-divider {{
    text-align: center;
    font-size: 0.68rem;
    color: #64748B;
    margin: 14px 0;
    position: relative;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    font-weight: 700;
}}
.signin-divider::before, .signin-divider::after {{
    content: '';
    position: absolute;
    top: 50%;
    width: 38%;
    height: 1px;
    background: rgba(255, 255, 255, 0.09);
}}
.signin-divider::before {{ left: 0; }}
.signin-divider::after  {{ right: 0; }}

.signin-footer {{
    text-align: center;
    margin-top: 14px;
    margin-bottom: 4px;
    font-size: 0.74rem;
    color: #94A3B8;
}}
.signin-footer a {{ color: #60A5FA; font-weight: 600; text-decoration: none; }}
.signin-footer a:hover {{ text-decoration: underline; }}

.signin-page-footer {{
    text-align: center;
    margin-top: 1.4rem;
    padding-top: 1rem;
    border-top: 1px solid rgba(255, 255, 255, 0.07);
    font-size: 0.71rem;
    color: #64748B;
    line-height: 1.7;
}}
.signin-page-footer a {{ color: #60A5FA; text-decoration: none; font-weight: 600; }}
.signin-page-footer a:hover {{ text-decoration: underline; }}
section[data-testid="stMain"] [data-testid="stAlert"] {{ border-radius: 10px !important; font-size: 0.82rem !important; }}
.forgot-link {{ text-align: right; margin: -4px 0 10px; font-size: 0.72rem; }}
.forgot-link a {{ color: {BLUE3}; text-decoration: none; }}
.forgot-link a:hover {{ text-decoration: underline; }}
.activate-link {{ text-align: center; margin-top: 8px; font-size: 0.7rem; color: rgba(148, 163, 184, 0.5); }}
.activate-link a {{ color: rgba(100, 153, 204, 0.8); text-decoration: none; }}
.activate-link a:hover {{ text-decoration: underline; }}
</style>"""


def inject_login_css() -> None:
    """Inject CSS halaman login. Panggil hanya saat belum login."""
    st.markdown(_LOGIN_CSS, unsafe_allow_html=True)


def inject_nav_highlight_css(active_idx: int) -> None:
    """Highlight tombol nav aktif. active_idx: indeks 0-based item dalam flat list menu."""
    active_menu = st.session_state.get("active_menu", "Beranda")
    safe_key = active_menu.replace(" ", "_")
    st.markdown(f"""<style>
[data-testid="stSidebar"] .st-key-nav_{safe_key} .stButton > button,
[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]
    > div:nth-child({active_idx + 1}) .stButton > button {{
    background: linear-gradient(90deg, rgba(37, 99, 235, 0.22) 0%, rgba(37, 99, 235, 0.08) 100%) !important;
    color: #FFFFFF !important;
    font-weight: 700 !important;
    border: 1px solid rgba(59, 130, 246, 0.32) !important;
    border-left: 3px solid {BLUE3} !important;
    box-shadow: 0 2px 10px rgba(37, 99, 235, 0.15) !important;
}}
[data-testid="stSidebar"] .st-key-nav_{safe_key} .stButton > button p {{
    color: #FFFFFF !important;
    font-weight: 700 !important;
}}
</style>""", unsafe_allow_html=True)


_NAV_LOCKED_CSS: str = f"""<style>
[data-testid="stSidebar"] .stButton > button {{
    opacity: 0.25 !important;
    pointer-events: none !important;
    cursor: not-allowed !important;
}}
</style>
<div style='margin:10px 8px 6px;padding:12px 14px;
            background:rgba(255,255,255,0.03);
            border:1px solid rgba(255,255,255,0.08);
            border-radius:10px;
            font-size:0.72rem;color:#94A3B8;line-height:1.6;text-align:center;'>
    🔒 Selesaikan langkah awal<br>di halaman utama dulu
</div>"""


def inject_nav_locked_css() -> None:
    st.markdown(_NAV_LOCKED_CSS, unsafe_allow_html=True)


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
        "<span style='background:linear-gradient(135deg,#FBBF24,#D97706);"
        "color:#0F172A;font-size:.63rem;font-weight:800;letter-spacing:.06em;"
        "padding:3px 10px;border-radius:999px;margin-left:8px;"
        "box-shadow:0 2px 8px rgba(245,158,11,.35);vertical-align:middle;'>✦ PRO ACCESS</span>"
        if is_pro else
        "<span style='background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.14);"
        "color:#CBD5E1;font-size:.62rem;font-weight:600;letter-spacing:.05em;"
        "padding:2px 9px;border-radius:999px;margin-left:8px;vertical-align:middle;'>FREE EDITION</span>"
    )
    display_name = user_name if user_name else "Pengguna"
    greeting_text = f"{salam}, {display_name}! 👋" if user_name else f"{salam}! 👋"
    st.markdown(
        f"<div class='rs-greeting'>"
        f"<div>"
        f"<div class='rs-greeting-text'>{greeting_text}{tier_badge}</div>"
        f"<div class='rs-greeting-sub'>Siap membantu analisis statistik Anda hari ini.</div>"
        f"</div>"
        f"<div style='display:flex;align-items:center;gap:6px;font-size:.72rem;color:#94A3B8;font-weight:500;'>"
        f"<span style='width:8px;height:8px;border-radius:50%;background:#10B981;box-shadow:0 0 8px #10B981;display:inline-block;'></span>"
        f"Engine Ready"
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
        <img src="https://i.imgur.com/RF4mzxf.png" width="38" height="38"
             style="object-fit:contain;filter:drop-shadow(0 2px 8px rgba(0,0,0,.3));" alt="logo">
    </div>
    <div style="flex:1;min-width:0;position:relative;z-index:1;">
        <div style="display:inline-flex;align-items:center;gap:6px;background:rgba(59,130,246,.18);
                    border:1px solid rgba(96,165,250,.3);border-radius:999px;padding:2px 10px;
                    font-size:.65rem;font-weight:700;color:#93C5FD;letter-spacing:.06em;
                    text-transform:uppercase;margin-bottom:8px;">
            Statistical Intelligence Suite &middot; v4.8
        </div>
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
    pairs = [(steps[i], steps[i+1] if i+1 < len(steps) else None)
             for i in range(0, len(steps), 2)]
    for pair_idx, (left, right) in enumerate(pairs):
        base_num = pair_idx * 2 + 1
        if right is None:
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
    """Render CTA Wizard block. Return True jika tombol diklik."""
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
