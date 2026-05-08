"""
Ruang Statistika — Automated Research & Stats Reporting
Oleh: Yogo Aryo Jatmiko | yogoaj.github.io
Versi: 4.5 Pro — Supabase Auth (Sign In / Sign Up / Forgot Password)

Entry point: routing menu, sidebar, shared CSS & state.
Setiap modul di modules/ bertanggung jawab atas halaman-nya sendiri.
"""

import warnings
import streamlit as st
import streamlit.components.v1 as components

warnings.filterwarnings("ignore")

# ── Supabase: restore session ────────────────────────────────────────────────
# Dipanggil SEBELUM apapun di-render, termasuk sidebar
from utils.supabase_auth import restore_supabase_session
restore_supabase_session()      # restore session jika token masih valid

# ── Page config (harus paling pertama) ───────────────────────────────────────
_is_logged_in = st.session_state.get("user_logged_in", False)
st.set_page_config(
    page_title="Ruang Statistika",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded" if _is_logged_in else "collapsed",
)

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:wght@300;400;500;600&display=swap');

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }

/* Sembunyikan tombol toggle sidebar saat belum login */
body:not(.rs-logged-in) [data-testid="collapsedControl"],
body:not(.rs-logged-in) [data-testid="stSidebarCollapsedControl"] {
    display: none !important;
}

[data-testid="stSidebar"] {
    background: #0c2340;
    border-right: 1px solid #1a3a5c;
}
[data-testid="stSidebar"] * { color: #b5d4f4 !important; }
[data-testid="stSidebar"] .stMarkdown h1,
[data-testid="stSidebar"] .stMarkdown h2,
[data-testid="stSidebar"] .stMarkdown h3 { color: #ffffff !important; }

/* ── Grouped Nav ── */
.nav-group-label {
    font-size: 0.63rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #4a7aaa !important;
    padding: 10px 4px 4px;
    margin-top: 4px;
    display: block;
}
.nav-btn {
    display: block;
    width: 100%;
    text-align: left;
    padding: 7px 10px 7px 12px;
    margin: 1px 0;
    border-radius: 8px;
    border: none;
    background: transparent;
    color: #b5d4f4 !important;
    font-size: 0.83rem;
    cursor: pointer;
    transition: background 0.15s, color 0.15s;
    line-height: 1.3;
}
.nav-btn:hover   { background: rgba(255,255,255,0.07); }
.nav-btn.active  {
    background: #185FA5 !important;
    color: #ffffff !important;
    font-weight: 600;
}
.nav-btn.pro-lock { color: #6a8fb5 !important; font-style: italic; }
.nav-btn.pro-lock.active { color: #fff !important; font-style: normal; }
.nav-divider {
    border: none;
    border-top: 1px solid #1a3a5c;
    margin: 6px 0;
}

/* ── Streamlit button override di sidebar ── */
[data-testid="stSidebar"] .stButton > button {
    background: transparent !important;
    border: none !important;
    color: #b5d4f4 !important;
    text-align: left !important;
    padding: 4px 10px !important;
    border-radius: 6px !important;
    font-size: 0.82rem !important;
    width: 100% !important;
    transition: background 0.15s !important;
    line-height: 1.3 !important;
    min-height: 0 !important;
    height: auto !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(255,255,255,0.07) !important;
    color: #fff !important;
}
/* Kurangi gap antar elemen di sidebar */
[data-testid="stSidebar"] .stButton {
    margin-bottom: 0 !important;
}
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlock"] {
    gap: 0 !important;
}
[data-testid="stSidebar"] .element-container {
    margin-bottom: 0 !important;
}

.rs-header {
    background: linear-gradient(135deg, #0c2340 0%, #185FA5 100%);
    padding: 2rem 2.5rem 1.5rem; border-radius: 14px;
    margin-bottom: 1.5rem; position: relative; overflow: hidden;
}
.rs-header::before {
    content: ''; position: absolute; right: -40px; top: -40px;
    width: 200px; height: 200px; border-radius: 50%;
    background: rgba(255,255,255,0.04);
}
.rs-header h1 {
    font-family: 'DM Serif Display', serif;
    font-size: 2rem; color: white; margin: 0 0 0.3rem;
}
.rs-header p { color: #85b7eb; font-size: 0.9rem; margin: 0; }
.rs-logo-link { text-decoration: none; color: #378add !important; font-size: 0.8rem; }

.rs-metric {
    background: #f0f6ff; border: 1px solid #d0e4f7;
    border-radius: 10px; padding: 1rem 1.2rem; text-align: center;
}
.rs-metric-label { font-size: 0.72rem; color: #5f8ab5; text-transform: uppercase;
                   letter-spacing: 0.06em; margin-bottom: 4px; }
.rs-metric-value { font-size: 1.8rem; font-weight: 600; color: #0c2340; }
.rs-metric-sub   { font-size: 0.72rem; color: #3b6d11; margin-top: 2px; }

.rs-narasi {
    background: #e6f1fb; border-left: 4px solid #185FA5;
    border-radius: 0 10px 10px 0; padding: 1rem 1.25rem;
    font-size: 0.9rem; color: #0c2340; line-height: 1.65; margin-top: 0.5rem;
}
.rs-ai-narasi {
    background: linear-gradient(135deg, #f0f4ff 0%, #e8f0fe 100%);
    border-left: 4px solid #6366f1; border-radius: 0 10px 10px 0;
    padding: 1rem 1.25rem; font-size: 0.9rem; color: #1e1b4b;
    line-height: 1.7; margin-top: 0.5rem;
}
.rs-ai-badge {
    display: inline-block;
    background: linear-gradient(90deg, #6366f1, #8b5cf6);
    color: white; font-size: 0.7rem; font-weight: 600;
    letter-spacing: 0.06em; padding: 2px 10px; border-radius: 20px;
    margin-bottom: 8px;
}
.badge-valid     { background:#eaf3de; color:#3b6d11; padding:2px 10px;
                   border-radius:20px; font-size:0.75rem; font-weight:500; }
.badge-invalid   { background:#fcebeb; color:#a32d2d; padding:2px 10px;
                   border-radius:20px; font-size:0.75rem; font-weight:500; }
.badge-reliable  { background:#eaf3de; color:#3b6d11; padding:3px 12px;
                   border-radius:20px; font-size:0.8rem; font-weight:600; }
.badge-unreliable{ background:#fcebeb; color:#a32d2d; padding:3px 12px;
                   border-radius:20px; font-size:0.8rem; font-weight:600; }

.rs-section-title { font-family:'DM Serif Display',serif; font-size:1.35rem;
                    color:#0c2340; margin-bottom:0.25rem; }
.rs-section-sub   { font-size:0.82rem; color:#5f8ab5; margin-bottom:1rem; }

.rs-step {
    background: #f7faff; border: 1px solid #d0e4f7;
    border-radius: 10px; padding: 14px 16px;
    display: flex; gap: 14px; align-items: flex-start; margin-bottom: 10px;
}
.rs-step-num {
    background: #e6f1fb; color: #185FA5;
    width: 30px; height: 30px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-weight: 600; font-size: 13px; flex-shrink: 0;
}
.rs-footer {
    margin-top: 3rem; padding-top: 1.5rem;
    border-top: 1px solid #e0eaf5; text-align: center;
    font-size: 0.8rem; color: #888;
}
.rs-footer a { color: #185FA5; text-decoration: none; }
.pro-badge {
    background: linear-gradient(90deg, #185FA5, #0c2340);
    color: white; padding: 3px 12px; border-radius: 20px;
    font-size: 0.75rem; font-weight: 600; letter-spacing: 0.04em;
}
.pro-lock-badge {
    background: linear-gradient(90deg, #6366f1, #8b5cf6);
    color: white; padding: 2px 8px; border-radius: 12px;
    font-size: 0.65rem; font-weight: 600; letter-spacing: 0.04em;
    margin-left: 4px; vertical-align: middle;
}
.chat-container {
    max-height: 420px; overflow-y: auto; padding: 0.5rem;
    background: #f7faff; border: 1px solid #d0e4f7;
    border-radius: 12px; margin-bottom: 1rem;
}
.chat-bubble-user {
    background: #185FA5; color: white; padding: 0.6rem 1rem;
    border-radius: 16px 16px 4px 16px;
    margin: 0.4rem 0 0.4rem 20%; font-size: 0.88rem; line-height: 1.5;
}
.chat-bubble-ai {
    background: white; border: 1px solid #d0e4f7; color: #0c2340;
    padding: 0.6rem 1rem; border-radius: 16px 16px 16px 4px;
    margin: 0.4rem 20% 0.4rem 0; font-size: 0.88rem; line-height: 1.6;
}
.chat-label { font-size: 0.7rem; color: #5f8ab5; margin-bottom: 2px; letter-spacing: 0.04em; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# DEFINISI GRUP MENU
# ══════════════════════════════════════════════════════════════════════════════

# Setiap item: (key_unik, label_tampil, is_pro_required)
# key_unik digunakan untuk routing — harus unik dan stabil

MENU_GROUPS = [
    {
        "label": None,   # tanpa header — beranda & data
        "items": [
            ("Beranda",           "🏠  Beranda",                False),
            ("Upload",            "📁  Upload & Cleaning",      False),
            ("Scraping",          "🕸️  Web Scraping",           True),
            ("EDA",               "🔍  Visualisasi EDA",        False),
            ("Compute",           "🧮  Compute Variabel",       False),
        ],
    },
    {
        "label": "── Eksplorasi Data",
        "items": [
            ("Deskriptif",        "📊  Statistik Deskriptif",   False),
            ("Validitas",         "✅  Validitas & Reliabilitas",False),
            ("Korelasi",          "🔗  Korelasi",               False),
            ("Kelompok",          "📂  Analisis Kelompok",      False),
            ("Klaster",           "🗂️  Analisis Klaster",       False),
            ("Outlier",           "🎯  Deteksi Outlier",        False),
        ],
    },
    {
        "label": "── Uji Statistik",
        "items": [
            ("Uji Asumsi",        "🔬  Uji Asumsi",             False),
            ("Uji Beda",          "🔢  Uji Beda (t / Mann-W)",  False),
            ("Uji Nonparametrik", "📐  Uji Non-Parametrik",     False),
            ("Power Analysis",    "🔋  Power Analysis",         False),
            # Gratis terbatas (one-way + η² saja; post-hoc & KW → Pro)
            ("ANOVA",             "📊  ANOVA & Post-hoc",       False),
        ],
    },
    {
        "label": "── Pemodelan",
        "items": [
            # Gratis terbatas (OLS dasar; VIF, prediksi, AI → Pro)
            ("Regresi",           "📈  Regresi & Prediksi",     False),
            # Gratis terbatas (OR + CM; ROC, CR, AI → Pro)
            ("Regresi Logistik",  "📉  Regresi Logistik",       False),
            # Full Pro
            ("OLS Plus",          "📐  Regresi OLS+",           True),
            ("OLS Robust",        "🛡️  Regresi Robust & WLS",   True),
            ("Mediasi",           "🔀  Mediasi",                True),
            ("Moderasi",          "🎛️  Moderasi",               True),
        ],
    },
    {
        "label": "── Faktor & SEM ★ Pro",
        "items": [
            ("EFA",               "🔬  EFA (Analisis Faktor)",  True),
            ("SEM",               "🧩  SEM & CFA",              True),
            ("CFA",               "🔬  CFA Standalone",         True),
        ],
    },
    {
        "label": "── AI & Laporan",
        "items": [
            ("Chat AI",           "🤖  Chat AI Analyst",        False),
            # Gratis terbatas (1x/hari, tanpa AI); Pro: tak terbatas + AI
            ("Laporan",           "📄  Generate Laporan",       False),
        ],
    },
]

# Flatten untuk lookup
def _iter_menu_items():
    """Iterate semua menu items, skip jika bukan tuple/list."""
    for group in MENU_GROUPS:
        for item in group["items"]:
            if isinstance(item, (tuple, list)) and len(item) == 3:
                yield item

_ALL_MENU_ITEMS = {
    key: (label, is_pro)
    for key, label, is_pro in _iter_menu_items()
}


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("""
    <div style='text-align:center;padding:1.5rem 0 0.5rem;'>
        <img src='https://i.imgur.com/tESt5qg.png' width='90'
             style='margin-bottom:15px; filter: drop-shadow(0px 4px 8px rgba(0,0,0,0.2));'>
        <div style='font-family:Georgia,serif;font-size:1.2rem;color:white;font-weight:600;'>
            Ruang Statistika
        </div>
        <div style='font-size:0.72rem;color:#5f8ab5;letter-spacing:0.08em;
                    text-transform:uppercase;margin-top:5px;'>
            v4.5 — AI-Powered Assistant
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Login state init ──────────────────────────────────────────────────────
    if "user_name" not in st.session_state:
        st.session_state.user_name = ""
    if "user_logged_in" not in st.session_state:
        st.session_state.user_logged_in = False

    # Inject body class untuk kontrol CSS sidebar toggle
    if st.session_state.user_logged_in:
        st.markdown(
            "<script>document.body.classList.add('rs-logged-in');</script>",
            unsafe_allow_html=True,
        )

    # Sidebar hanya tampilkan nama + tombol keluar (jika sudah login)
    if st.session_state.user_logged_in:
        _display_name = st.session_state.user_name or "Pengguna"
        _is_pro_user  = st.session_state.get("_user_data", {}).get("role") == "pro"
        _tier_badge   = (
            "<span style='background:linear-gradient(90deg,#185FA5,#0c2340);"
            "color:#fff;font-size:0.65rem;font-weight:600;letter-spacing:0.04em;"
            "padding:2px 8px;border-radius:10px;margin-left:6px;'>PRO</span>"
            if _is_pro_user else
            "<span style='background:rgba(255,255,255,0.12);color:#85b7eb;"
            "font-size:0.65rem;padding:2px 8px;border-radius:10px;margin-left:6px;'>"
            "GRATIS</span>"
        )
        st.markdown(
            f"<div style='padding:8px 10px;background:rgba(24,95,165,0.20);"
            f"border-radius:8px;margin-bottom:4px;display:flex;align-items:center;gap:8px;'>"
            f"<div style='width:30px;height:30px;border-radius:50%;background:#185FA5;"
            f"display:flex;align-items:center;justify-content:center;"
            f"font-size:0.72rem;color:#fff;font-weight:600;flex-shrink:0;'>"
            f"{(_display_name[:2].upper()) if _display_name else 'U'}</div>"
            f"<div style='min-width:0;'>"
            f"<div style='font-size:0.85rem;color:#ffffff;font-weight:600;"
            f"white-space:nowrap;overflow:hidden;text-overflow:ellipsis;'>"
            f"{_display_name}{_tier_badge}</div>"
            f"<div style='font-size:0.7rem;color:#4a7aaa;margin-top:1px;'>"
            f"{st.session_state.get('_user_data', {}).get('email', '') or 'Mode Gratis'}"
            f"</div></div></div>",
            unsafe_allow_html=True,
        )
        if st.button("⬡  Keluar", key="btn_logout", use_container_width=True):
            from utils.supabase_auth import supabase_sign_out
            supabase_sign_out()
            st.rerun()

    st.markdown("---")

    # ── License ──────────────────────────────────────────────────────────────
    # Jika key diinput via modal, pre-fill ke session state yang dibaca sidebar
    # Key harus cocok dengan key= di st.text_input di render_license_sidebar → "sidebar_license_key"
    if st.session_state.get("_modal_license_key"):
        st.session_state["sidebar_license_key"] = st.session_state["_modal_license_key"]
    from utils.auth import render_license_sidebar
    license_info = render_license_sidebar()
    is_pro = license_info["status"] == "pro"

    st.markdown("---")

    # ── AI Provider ──────────────────────────────────────────────────────────
    from utils.ai_helpers import ALL_PROVIDERS, PROVIDER_KEY_INFO

    st.markdown(
        "<p style='font-size:0.75rem;color:#5f8ab5;letter-spacing:0.06em;"
        "text-transform:uppercase;'>🤖 AI Interpreter</p>",
        unsafe_allow_html=True,
    )

    provider_display = []
    for p in ALL_PROVIDERS:
        if p == "Groq — Llama 3.3 70B":
            provider_display.append("── Gratis: Groq ──────────────")
        elif p == "HuggingFace — Mistral 7B":
            provider_display.append("── Gratis: HuggingFace ────────")
        provider_display.append(p)

    ai_provider_raw = st.selectbox(
        "Pilih Provider AI",
        provider_display,
        help="Groq & HuggingFace tersedia GRATIS",
    )
    ai_provider = (
        ai_provider_raw if not ai_provider_raw.startswith("──")
        else "Claude (Anthropic)"
    )

    key_label, key_url = PROVIDER_KEY_INFO.get(ai_provider, ("API Key", ""))

    is_free_provider = "Groq" in ai_provider or "HuggingFace" in ai_provider
    if is_free_provider:
        st.markdown(
            "<span style='background:#eaf3de;color:#3b6d11;padding:2px 8px;"
            "border-radius:10px;font-size:0.72rem;font-weight:600;'>✅ GRATIS</span>",
            unsafe_allow_html=True,
        )

    anthropic_api_key = st.text_input(
        key_label, type="password",
        help=f"Dapatkan API Key di: {key_url}",
    )
    ai_enabled = bool(anthropic_api_key)

    if ai_enabled:
        provider_short = (
            ai_provider.split("—")[0].strip() if "—" in ai_provider
            else ai_provider.split("(")[0].strip()
        )
        st.success(f"🤖 {provider_short} Aktif")
    else:
        if key_url:
            st.caption(f"Daftar/login di [{key_url}]({'https://' + key_url})")

    # ── Grouped Navigation ────────────────────────────────────────────────────
    st.markdown("---")

    # Inisialisasi menu aktif
    if "active_menu" not in st.session_state:
        st.session_state.active_menu = "Beranda"

    # ── BLOKIR navigasi jika belum melewati modal ─────────────────────────────
    _nav_locked = not st.session_state.get("user_logged_in", False)

    if _nav_locked:
        # Paksa tetap di Beranda
        st.session_state.active_menu = "Beranda"
        # CSS: redup semua tombol nav + non-interaktif
        st.markdown("""
        <style>
        [data-testid="stSidebar"] .stButton > button {
            opacity: 0.30 !important;
            pointer-events: none !important;
            cursor: not-allowed !important;
        }
        </style>
        <div style='text-align:center;margin-top:8px;padding:6px 12px;
                    background:rgba(12,35,64,0.6);border-radius:10px;
                    font-size:0.72rem;color:#5f8ab5;line-height:1.5;'>
            🔒 Selesaikan langkah awal<br>di halaman utama dulu
        </div>
        """, unsafe_allow_html=True)

    LOCK = " 🔒"

    for group in MENU_GROUPS:
        # Header grup
        if group["label"]:
            st.markdown(
                f"<span class='nav-group-label'>{group['label']}</span>",
                unsafe_allow_html=True,
            )

        for item in group["items"]:
            if not (isinstance(item, (tuple, list)) and len(item) == 3):
                continue
            key, label, needs_pro = item
            is_active   = st.session_state.active_menu == key
            is_locked   = needs_pro and not is_pro
            display_lbl = label + (LOCK if is_locked else "")

            # Render button dengan st.button; aktif diindikasikan via label styling
            st.markdown(
                f"""<style>
                div[data-testid="stButton"] > button[kind="secondary"]
                    {{ /* reset */ }}
                </style>""",
                unsafe_allow_html=True,
            )

            # Guard Python: klik diabaikan saat nav terkunci
            _clicked = st.button(
                display_lbl,
                key=f"nav_{key}",
                use_container_width=True,
            )
            if _clicked and not _nav_locked:
                st.session_state.active_menu = key

        # Tambah sedikit spasi antar grup
        st.markdown("<div style='margin-bottom:2px;'></div>", unsafe_allow_html=True)

    # Ambil nilai menu aktif saat ini
    menu = st.session_state.active_menu

    # ── Highlight tombol aktif via CSS dinamis ────────────────────────────────
    # Karena Streamlit button tidak support kelas aktif native, kita inject CSS
    # yang mentarget label teks tombol aktif
    active_label, _ = _ALL_MENU_ITEMS.get(menu, ("", False))
    # Hapus emoji + strip untuk selector yang aman
    _active_text_clean = active_label.strip()

    # Inject override CSS untuk semua nav button + highlight aktif
    nav_css_parts = []
    for group in MENU_GROUPS:
        for item in group["items"]:
            if not (isinstance(item, (tuple, list)) and len(item) == 3):
                continue
            key, label, needs_pro = item
            is_active = (key == menu)
            is_locked = needs_pro and not is_pro
            disp      = label + (LOCK if is_locked else "")
            if is_active:
                # Escaping minimal untuk CSS attribute selector
                safe = disp.replace('"', '\\"')
                nav_css_parts.append(
                    f"""[data-testid="stSidebar"] button[kind="secondary"]:has(p:-webkit-any(p)):not(:disabled)"""
                )

    # Inject via simpler approach: target berdasarkan urutan button di sidebar
    # Hitung posisi button dalam flat list
    flat_items = [
        (key, label + (LOCK if (needs_pro and not is_pro) else ""))
        for group in MENU_GROUPS
        for item in group["items"]
        if isinstance(item, (tuple, list)) and len(item) == 3
        for key, label, needs_pro in [item]
    ]
    active_idx = next(
        (i for i, (k, _) in enumerate(flat_items) if k == menu), 0
    )

    # CSS: button ke-N di sidebar (menggunakan nth-of-type pada container stButton)
    # Pendekatan: inject style tag yang menghighlight button aktif
    btn_highlight_css = f"""
    <style>
    /* Reset semua nav button */
    [data-testid="stSidebar"] .stButton > button {{
        background: transparent !important;
        border: none !important;
        color: #b5d4f4 !important;
        text-align: left !important;
        padding: 6px 10px !important;
        border-radius: 8px !important;
        font-size: 0.83rem !important;
        width: 100% !important;
        transition: background 0.15s !important;
        font-weight: 400 !important;
    }}
    [data-testid="stSidebar"] .stButton > button:hover {{
        background: rgba(255,255,255,0.08) !important;
        color: #fff !important;
    }}
    /* Highlight button aktif: nth-child di dalam wrapper div */
    [data-testid="stSidebar"] div[data-testid="stVerticalBlock"]
        > div:nth-child({active_idx + 1}) .stButton > button,
    [data-testid="stSidebar"] div[data-testid="stVerticalBlockBorderWrapper"]
        > div:nth-child({active_idx + 1}) .stButton > button {{
        background: #185FA5 !important;
        color: #ffffff !important;
        font-weight: 600 !important;
    }}
    </style>
    """
    # Gunakan pendekatan lebih andal: simpan key aktif dan inject per-button class
    # via label matching (lebih stabil cross-Streamlit-version)
    active_key_escaped = menu.replace("'", "\\'")
    final_nav_css = f"""
    <style>
    [data-testid="stSidebar"] .stButton > button {{
        background: transparent !important;
        border: none !important;
        color: #b5d4f4 !important;
        text-align: left !important;
        padding: 4px 10px !important;
        border-radius: 6px !important;
        font-size: 0.82rem !important;
        width: 100% !important;
        font-weight: 400 !important;
        margin: 0 !important;
        line-height: 1.35 !important;
        min-height: 0 !important;
        height: auto !important;
    }}
    [data-testid="stSidebar"] .stButton > button:hover {{
        background: rgba(255,255,255,0.09) !important;
        color: #ffffff !important;
    }}
    [data-testid="stSidebar"] .stButton > button:focus {{
        box-shadow: none !important;
        outline: none !important;
    }}
    [data-testid="stSidebar"] .stButton {{
        margin-bottom: 0 !important;
        margin-top: 0 !important;
    }}
    [data-testid="stSidebar"] .element-container {{
        margin-bottom: 0 !important;
        margin-top: 0 !important;
    }}
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {{
        gap: 0px !important;
    }}
    </style>
    """
    st.markdown(final_nav_css, unsafe_allow_html=True)

    # ── Parameter ─────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown(
        "<p style='font-size:0.7rem;letter-spacing:0.08em;text-transform:uppercase;"
        "color:#5f8ab5;'>Parameter</p>",
        unsafe_allow_html=True,
    )
    alpha_level = st.slider("Signifikansi (α)", 0.01, 0.10, 0.05, 0.01)
    r_tab       = st.number_input("r-tabel Validitas", 0.10, 0.50, 0.30, 0.01)

    st.markdown("---")
    st.markdown("""
    <div style='font-size:0.72rem; color:#3a6080; text-align:center; line-height:1.6;'>
        <a href='https://yogoaj.github.io' target='_blank' style='color:#378add;'>
            Ruang Statistika</a><br/>
        © 2026 Ruang Statistika v4.5
    </div>
    """, unsafe_allow_html=True)


# ── Context dict — diteruskan ke setiap modul ────────────────────────────────
ctx = {
    "license_info":      license_info,
    "is_pro":            is_pro,
    "alpha_level":       alpha_level,
    "r_tab":             r_tab,
    "ai_enabled":        ai_enabled,
    "anthropic_api_key": anthropic_api_key,
    "ai_provider":       ai_provider,
    "user_name":         st.session_state.get("user_name", ""),
}


# ══════════════════════════════════════════════════════════════════════════════
# RESET SCROLL — panggil SEBELUM render, hanya saat menu berubah
# ══════════════════════════════════════════════════════════════════════════════

def reset_scroll():
    components.html(
        """
        <script>
        (function() {
            window.scrollTo(0, 0);
            try {
                var p = window.parent;
                p.scrollTo(0, 0);
                var selectors = [
                    '.main', '.block-container',
                    '[data-testid="stAppViewContainer"]',
                    '[data-testid="block-container"]',
                    'section.main',
                ];
                selectors.forEach(function(sel) {
                    var el = p.document.querySelector(sel);
                    if (el) { el.scrollTop = 0; }
                });
                var all = p.document.querySelectorAll('*');
                for (var i = 0; i < all.length; i++) {
                    var style = p.getComputedStyle(all[i]);
                    var overflow = style.overflowY;
                    if ((overflow === 'auto' || overflow === 'scroll')
                            && all[i].scrollTop > 0) {
                        all[i].scrollTop = 0;
                    }
                }
            } catch(e) {}
        })();
        </script>
        """,
        height=0,
    )

if "previous_menu" not in st.session_state:
    st.session_state.previous_menu = menu

if menu != st.session_state.previous_menu:
    reset_scroll()
    st.session_state.previous_menu = menu


# ══════════════════════════════════════════════════════════════════════════════
# MENU ROUTING
# ══════════════════════════════════════════════════════════════════════════════

if menu == "Beranda":
    # ── Auth screen — muncul jika belum login ─────────────────────────────
    if not st.session_state.user_logged_in:

        # ── Tab state — murni session_state, tanpa query_params ────────────
        if "modal_tab" not in st.session_state:
            st.session_state.modal_tab = "masuk"
        tab = st.session_state.modal_tab

        # ── CSS: halaman login — bersih, sidebar tersembunyi ────────────────
        st.markdown("""
        <style>
        .rs-footer { display: none; }
        header[data-testid="stHeader"] { display: none; }

        /* Sembunyikan sidebar & tombol toggle-nya sepenuhnya */
        [data-testid="stSidebar"],
        [data-testid="collapsedControl"],
        [data-testid="stSidebarCollapsedControl"] {
            display: none !important;
        }

        /* Background terang — nada seperti email konfirmasi */
        [data-testid="stAppViewContainer"],
        [data-testid="stApp"] {
            background: #eef4fb !important;
        }

        /* Pusatkan kartu — pertahankan max-width sempit */
        section[data-testid="stMain"] .block-container {
            padding-top: 5vh !important;
            max-width: 440px !important;
            margin: 0 auto !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
            padding-bottom: 3rem !important;
        }

        /* ── Kartu utama — dengan header gradient di atas ── */
        .signin-card {
            background: #ffffff;
            border-radius: 18px;
            overflow: hidden;
            box-shadow: 0 8px 32px rgba(12,35,64,0.13), 0 2px 8px rgba(12,35,64,0.07);
            width: 100%;
            max-width: 420px;
            margin-bottom: 0;
        }

        /* ── Header kartu bergradient (seperti email konfirmasi) ── */
        .signin-card-header {
            background: linear-gradient(135deg, #0c2340 0%, #185FA5 65%, #1e73c8 100%);
            padding: 2rem 2rem 1.8rem;
            text-align: center;
            position: relative;
            overflow: hidden;
        }
        .signin-card-header::before {
            content: '';
            position: absolute;
            right: -50px; top: -50px;
            width: 180px; height: 180px;
            border-radius: 50%;
            background: rgba(255,255,255,0.06);
            pointer-events: none;
        }
        .signin-card-header::after {
            content: '';
            position: absolute;
            left: -30px; bottom: -50px;
            width: 140px; height: 140px;
            border-radius: 50%;
            background: rgba(255,255,255,0.04);
            pointer-events: none;
        }
        .signin-header-logo {
            position: relative; z-index: 1;
            margin-bottom: 12px;
        }
        .signin-header-logo img {
            width: 60px; height: 60px;
            object-fit: contain;
            filter: drop-shadow(0 3px 10px rgba(0,0,0,0.25));
        }
        .signin-header-title {
            font-family: 'DM Serif Display', serif;
            font-size: 1.55rem; font-weight: 400;
            color: #ffffff; letter-spacing: -0.2px;
            position: relative; z-index: 1;
            margin: 0 0 5px;
        }
        .signin-header-sub {
            font-size: 0.78rem; color: #85b7eb;
            position: relative; z-index: 1;
        }

        /* ── Body dalam kartu ── */
        .signin-body {
            padding: 1.6rem 2rem 1.4rem;
        }

        /* Tab strip — tombol Streamlit disamarkan jadi tab */
        .signin-tab-row {
            display: flex;
            border-bottom: 1px solid #e2ecf5;
            margin-bottom: 1.3rem;
            gap: 0;
        }
        .signin-tab-row .stButton { flex: 1; }
        .signin-tab-row .stButton > button {
            background: transparent !important;
            border: none !important;
            border-bottom: 2.5px solid transparent !important;
            border-radius: 0 !important;
            color: #8aabcc !important;
            font-size: 0.85rem !important;
            font-weight: 500 !important;
            padding: 8px 4px !important;
            width: 100% !important;
            margin-bottom: -1px !important;
            transition: color 0.15s, border-color 0.15s !important;
        }
        .signin-tab-row .stButton > button:hover {
            color: #0c2340 !important;
            background: transparent !important;
        }
        .signin-tab-active .stButton > button {
            color: #0c2340 !important;
            font-weight: 700 !important;
            border-bottom-color: #185FA5 !important;
        }

        /* Link-style buttons (footer & activate) */
        .signin-link-btn .stButton > button {
            background: transparent !important;
            border: none !important;
            color: #185FA5 !important;
            font-size: 0.74rem !important;
            font-weight: 600 !important;
            padding: 2px 6px !important;
            height: auto !important;
            min-height: 0 !important;
        }
        .signin-link-btn .stButton > button:hover {
            background: transparent !important;
            text-decoration: underline !important;
        }
        .signin-link-btn-muted .stButton > button {
            color: #7aa8cc !important;
            font-weight: 400 !important;
            font-size: 0.72rem !important;
        }

        /* Logo + judul (fallback lama, tidak dipakai lagi) */
        .signin-logo { text-align: center; margin-bottom: 1.6rem; }
        .signin-logo-icon {
            width: 48px; height: 48px; border-radius: 12px;
            background: #0c2340;
            display: inline-flex; align-items: center; justify-content: center;
            margin-bottom: 12px;
        }
        .signin-logo-icon img { width: 30px; filter: brightness(1.2); }
        .signin-logo h2 {
            font-family: 'DM Serif Display', serif;
            font-size: 1.45rem; color: #0c2340; margin: 0 0 5px;
        }
        .signin-logo p { font-size: 0.78rem; color: #8aabcc; margin: 0; }

        /* Tab strip — hanya Masuk & Daftar */
        .signin-tabs {
            display: flex;
            border-bottom: 1px solid #e8edf2;
            margin-bottom: 1.4rem;
        }
        .signin-tab {
            flex: 1; text-align: center; padding: 8px 4px;
            font-size: 0.85rem; font-weight: 500; color: #8aabcc;
            text-decoration: none;
            border-bottom: 2px solid transparent; margin-bottom: -1px;
            transition: color 0.15s, border-color 0.15s;
        }
        .signin-tab:hover { color: #0c2340; }
        .signin-tab.active {
            color: #0c2340; font-weight: 700;
            border-bottom-color: #185FA5;
        }

        /* Input fields */
        section[data-testid="stMain"] .stTextInput label {
            font-size: 0.78rem !important; font-weight: 600 !important;
            color: #3d5a73 !important; margin-bottom: 4px !important;
        }
        section[data-testid="stMain"] .stTextInput input {
            border: 1.5px solid #d0e4f2 !important;
            border-radius: 8px !important; padding: 10px 12px !important;
            font-size: 0.88rem !important; background: #f7faff !important;
            transition: border-color 0.15s, box-shadow 0.15s !important;
        }
        section[data-testid="stMain"] .stTextInput input:focus {
            border-color: #185FA5 !important;
            background: #ffffff !important;
            box-shadow: 0 0 0 3px rgba(24,95,165,0.10) !important;
        }

        /* Submit button (form) */
        section[data-testid="stMain"] .stForm [data-testid="stFormSubmitButton"] > button {
            background: linear-gradient(135deg, #0c2340 0%, #185FA5 100%) !important;
            color: #ffffff !important;
            border: none !important; border-radius: 9px !important;
            padding: 12px !important; font-size: 0.9rem !important;
            font-weight: 600 !important; width: 100% !important;
            transition: opacity 0.15s, box-shadow 0.15s !important;
            box-shadow: 0 4px 14px rgba(24,95,165,0.30) !important;
        }
        section[data-testid="stMain"] .stForm [data-testid="stFormSubmitButton"] > button:hover {
            opacity: 0.92 !important;
            box-shadow: 0 6px 18px rgba(24,95,165,0.38) !important;
        }

        /* CTA Coba Gratis — tombol Streamlit biasa di luar form */
        section[data-testid="stMain"] .stButton > button {
            background: #f0f6ff !important;
            border: 1.5px solid #c0d9f0 !important;
            border-radius: 9px !important; color: #185FA5 !important;
            font-size: 0.85rem !important; font-weight: 600 !important;
            padding: 9px !important; width: 100% !important;
            transition: background 0.15s, border-color 0.15s !important;
        }
        section[data-testid="stMain"] .stButton > button:hover {
            background: #deeef9 !important; border-color: #185FA5 !important;
        }

        /* Lupa password — link kecil */
        .forgot-link {
            text-align: right; margin: -6px 0 12px;
            font-size: 0.74rem;
        }
        .forgot-link a { color: #185FA5; text-decoration: none; }
        .forgot-link a:hover { text-decoration: underline; }

        /* Divider teks */
        .signin-divider {
            text-align: center; font-size: 0.74rem; color: #b5c8d8;
            margin: 10px 0 8px; position: relative;
        }
        .signin-divider::before, .signin-divider::after {
            content: ''; position: absolute; top: 50%;
            width: 40%; height: 1px; background: #e2ecf5;
        }
        .signin-divider::before { left: 0; }
        .signin-divider::after  { right: 0; }

        /* Footer links bawah kartu */
        .signin-footer {
            text-align: center; margin-top: 1rem;
            font-size: 0.74rem; color: #8aabcc;
        }
        .signin-footer a { color: #185FA5; font-weight: 600; text-decoration: none; }
        .signin-footer a:hover { text-decoration: underline; }

        /* Footer di bawah kartu */
        .signin-page-footer {
            text-align: center; margin-top: 1.4rem;
            font-size: 0.72rem; color: #9ab5cc; line-height: 1.7;
        }
        .signin-page-footer a { color: #185FA5; text-decoration: none; font-weight: 500; }

        /* Link aktivasi Pro */
        .activate-link {
            text-align: center; margin-top: 8px;
            font-size: 0.72rem; color: #a0bcd8;
        }
        .activate-link a { color: #7aa8cc; text-decoration: none; }
        .activate-link a:hover { text-decoration: underline; }
        </style>
        """, unsafe_allow_html=True)

        # ── Header kartu: gradient biru (nada email konfirmasi) ─────────────
        st.markdown("""
        <div class="signin-card">
          <div class="signin-card-header">
            <div class="signin-header-logo">
              <img src="https://i.imgur.com/tESt5qg.png" alt="logo Ruang Statistika">
            </div>
            <div class="signin-header-title">Ruang Statistika</div>
            <div class="signin-header-sub">AI-Powered Research &amp; Stats Reporting</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # ── Tab strip — st.button (tetap di halaman sama) ─────────────────
        st.markdown('<div class="signin-tab-row">', unsafe_allow_html=True)
        _tcols = st.columns(2)
        _tab_labels = {"masuk": "Masuk", "daftar": "Daftar"}
        for _i, (_tkey, _tlabel) in enumerate(_tab_labels.items()):
            _cls = "signin-tab-active" if tab == _tkey else ""
            with _tcols[_i]:
                st.markdown(f'<div class="{_cls}">', unsafe_allow_html=True)
                if st.button(_tlabel, key=f"tab_btn_{_tkey}", use_container_width=True):
                    st.session_state.modal_tab = _tkey
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # ── Pesan status ────────────────────────────────────────────────────
        if st.session_state.get("_auth_msg_error"):
            st.error(st.session_state.pop("_auth_msg_error"))
        if st.session_state.get("_auth_msg_success"):
            st.success(st.session_state.pop("_auth_msg_success"))

        # ── Form per tab ─────────────────────────────────────────────────────

        if tab == "masuk":
            with st.form("form_masuk", clear_on_submit=False):
                _email_inp = st.text_input("Email", placeholder="email@domain.com")
                _pw_inp    = st.text_input("Password", placeholder="Password kamu…",
                                           type="password")
                # Link lupa password — HTML saja (non-interaktif, trigger st.button di bawah)
                st.markdown(
                    '<div class="forgot-link" id="lupa-trigger">'
                    '<span style="color:#185FA5;cursor:pointer;" '
                    'onclick="window.parent.document.getElementById(\'btn_ke_lupa\').click()">'
                    'Lupa password?</span></div>',
                    unsafe_allow_html=True)
                if st.form_submit_button("Masuk →", use_container_width=True, type="primary"):
                    from utils.supabase_auth import supabase_sign_in
                    _ok, _msg = supabase_sign_in(_email_inp.strip(), _pw_inp)
                    if _ok:
                        st.query_params.clear()
                        st.rerun()
                    else:
                        st.session_state["_auth_msg_error"] = _msg
                        st.rerun()

            # Tombol tersembunyi untuk pindah ke tab lupa (dipanggil via JS di atas)
            st.markdown('<div style="display:none;" id="btn_ke_lupa_wrap">', unsafe_allow_html=True)
            if st.button("lupa password?", key="btn_ke_lupa"):
                st.session_state.modal_tab = "lupa password?"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

            # Divider + CTA Coba Gratis
            st.markdown('<div class="signin-divider">atau</div>', unsafe_allow_html=True)
            if st.button("✨  Coba Gratis — tanpa akun", key="btn_coba_gratis_masuk",
                         use_container_width=True):
                st.session_state.user_name      = ""
                st.session_state.user_logged_in = True
                st.query_params.clear()
                st.rerun()

            # Footer navigasi — st.button link-style
            st.markdown('<div class="signin-footer">Belum punya akun?</div>', unsafe_allow_html=True)
            _fc1, _fc2 = st.columns([1, 1])
            with _fc1:
                st.markdown('<div class="signin-link-btn">', unsafe_allow_html=True)
                if st.button("Daftar gratis", key="go_daftar_from_masuk", use_container_width=True):
                    st.session_state.modal_tab = "daftar"
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            with _fc2:
                st.markdown('<div class="signin-link-btn signin-link-btn-muted">', unsafe_allow_html=True)
                if st.button("Aktivasi Pro →", key="go_pro_from_masuk", use_container_width=True):
                    st.session_state.modal_tab = "pro"
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

        elif tab == "daftar":
            with st.form("form_daftar", clear_on_submit=False):
                _reg_name  = st.text_input("Nama Lengkap", placeholder="Nama kamu…")
                _reg_email = st.text_input("Email", placeholder="email@domain.com")
                _reg_pw    = st.text_input("Password", placeholder="Minimal 6 karakter…",
                                           type="password")
                _reg_pw2   = st.text_input("Konfirmasi Password",
                                           placeholder="Ulangi password…", type="password")
                if st.form_submit_button("Daftar Sekarang →", use_container_width=True,
                                         type="primary"):
                    if not _reg_name.strip():
                        st.error("Nama lengkap tidak boleh kosong.")
                    elif not _reg_email.strip():
                        st.error("Email tidak boleh kosong.")
                    elif _reg_pw != _reg_pw2:
                        st.error("❌ Password dan konfirmasi tidak cocok.")
                    elif len(_reg_pw) < 6:
                        st.error("❌ Password minimal 6 karakter.")
                    else:
                        from utils.supabase_auth import supabase_sign_up
                        _ok, _msg = supabase_sign_up(
                            _reg_email.strip(), _reg_pw, _reg_name.strip())
                        if _ok:
                            if st.session_state.get("user_logged_in"):
                                st.query_params.clear()
                                st.rerun()
                            else:
                                st.session_state["_auth_msg_success"] = (
                                    "✅ Cek inbox "
                                    f"**{_reg_email.strip()}** untuk konfirmasi, "
                                    "lalu kembali untuk **Masuk**."
                                )
                                st.session_state.modal_tab = "masuk"
                                st.rerun()
                        else:
                            st.session_state["_auth_msg_error"] = _msg
                            st.rerun()

            # Divider + CTA Coba Gratis
            st.markdown('<div class="signin-divider">atau</div>', unsafe_allow_html=True)
            if st.button("✨  Coba Gratis — tanpa akun", key="btn_coba_gratis_daftar",
                         use_container_width=True):
                st.session_state.user_name      = ""
                st.session_state.user_logged_in = True
                st.query_params.clear()
                st.rerun()

            st.markdown('<div class="signin-footer">Sudah punya akun?</div>', unsafe_allow_html=True)
            _dc1, _dc2 = st.columns([1, 1])
            with _dc1:
                st.markdown('<div class="signin-link-btn">', unsafe_allow_html=True)
                if st.button("Masuk", key="go_masuk_from_daftar", use_container_width=True):
                    st.session_state.modal_tab = "masuk"
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            with _dc2:
                st.markdown('<div class="signin-link-btn signin-link-btn-muted">', unsafe_allow_html=True)
                if st.button("Aktivasi Pro →", key="go_pro_from_daftar", use_container_width=True):
                    st.session_state.modal_tab = "pro"
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

        # ── Tab lupa, pro, gratis: navigasi via session_state ────────────────

        elif tab == "lupa":
            st.markdown(
                "<p style='font-size:0.82rem;color:#5f8ab5;margin:0 0 12px;'>"
                "Masukkan email saat daftar, kami kirimkan link reset.</p>",
                unsafe_allow_html=True)
            with st.form("form_lupa", clear_on_submit=True):
                _lupa_email = st.text_input("Email", placeholder="email@domain.com")
                if st.form_submit_button("Kirim Link Reset →", use_container_width=True,
                                         type="primary"):
                    if not _lupa_email.strip():
                        st.error("Masukkan email kamu.")
                    else:
                        from utils.supabase_auth import supabase_forgot_password
                        _app_url = st.secrets.get("app_url", "http://localhost:8501")
                        _ok, _msg = supabase_forgot_password(_lupa_email.strip(), _app_url)
                        st.session_state["_auth_msg_success" if _ok else "_auth_msg_error"] = _msg
                        st.rerun()
            st.markdown('<div class="signin-link-btn">', unsafe_allow_html=True)
            if st.button("← Kembali ke Masuk", key="go_masuk_from_lupa", use_container_width=True):
                st.session_state.modal_tab = "masuk"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        elif tab == "pro":
            with st.form("form_pro", clear_on_submit=False):
                _key_inp  = st.text_input("License Key", placeholder="PRO-STAT-XXXX",
                                          type="password")
                _pro_name = st.text_input("Nama Anda (untuk laporan)",
                                          placeholder="Nama peneliti…")
                if st.form_submit_button("Aktifkan Pro →", use_container_width=True,
                                         type="primary"):
                    from utils.auth import validate_license
                    _k = _key_inp.strip()
                    if not _k:
                        st.error("Masukkan license key terlebih dahulu.")
                    else:
                        _info = validate_license(_k)
                        if _info.get("status") == "pro":
                            st.session_state["_modal_license_key"]  = _k
                            st.session_state["sidebar_license_key"] = _k
                            _dname = _pro_name.strip() or "Pengguna Pro"
                            st.session_state["user_logged_in"] = True
                            st.session_state["user_name"]      = _dname
                            st.session_state["_user_data"] = {
                                "username": "pro_key_user", "name": _dname,
                                "email": "", "role": "pro",
                                "license_key": _k, "active": True,
                            }
                            st.query_params.clear()
                            st.rerun()
                        else:
                            st.error("❌ License key tidak valid atau sudah expired.")
            st.markdown(
                '<div class="signin-footer">Dapatkan key di '
                '<a href="https://yogoaj.github.io" target="_blank">yogoaj.github.io</a>'
                '</div>',
                unsafe_allow_html=True)
            st.markdown('<div class="signin-link-btn" style="margin-top:6px;">', unsafe_allow_html=True)
            if st.button("← Kembali ke Masuk", key="go_masuk_from_pro", use_container_width=True):
                st.session_state.modal_tab = "masuk"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        elif tab == "gratis":
            st.markdown("""
            <div style='background:#f0f7ff;border:1px solid #cce3f8;border-radius:10px;
                        padding:12px 14px;margin-bottom:14px;font-size:0.83rem;
                        color:#0c2340;line-height:1.75;'>
              ✅ Semua modul analisis dasar tersedia<br/>
              📄 Generate Laporan: <b>1×/hari</b><br/>
              🔒 Fitur Pro → butuh lisensi
            </div>
            """, unsafe_allow_html=True)
            with st.form("form_gratis", clear_on_submit=False):
                _free_name = st.text_input("Nama Anda (opsional)",
                                           placeholder="Untuk laporan — boleh kosong")
                if st.form_submit_button("Lanjutkan Gratis →", use_container_width=True,
                                         type="primary"):
                    st.session_state.user_name      = _free_name.strip()
                    st.session_state.user_logged_in = True
                    st.query_params.clear()
                    st.rerun()
            _gc1, _gc2 = st.columns([1, 1])
            with _gc1:
                st.markdown('<div class="signin-link-btn">', unsafe_allow_html=True)
                if st.button("Daftar gratis", key="go_daftar_from_gratis", use_container_width=True):
                    st.session_state.modal_tab = "daftar"
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            with _gc2:
                st.markdown('<div class="signin-link-btn signin-link-btn-muted">', unsafe_allow_html=True)
                if st.button("Aktivasi Pro", key="go_pro_from_gratis", use_container_width=True):
                    st.session_state.modal_tab = "pro"
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("""
        <div class="signin-page-footer">
            © 2026 Ruang Statistika v4.5 ·
            <a href="https://yogoaj.github.io" target="_blank">yogoaj.github.io</a>
        </div>
        """, unsafe_allow_html=True)

        st.stop()

    # ── Personalized greeting ──────────────────────────────────────────────
    _user = st.session_state.get("user_name", "")
    if _user:
        import datetime as _dt
        _hour = _dt.datetime.now().hour
        _salam = (
            "Selamat pagi" if _hour < 11 else
            "Selamat siang" if _hour < 15 else
            "Selamat sore" if _hour < 18 else
            "Selamat malam"
        )
        _tier = "✨ Pro" if is_pro else "🔓 Gratis"
        st.markdown(
            f"<div style='background:linear-gradient(135deg,#0c2340 0%,#185FA5 100%);"
            f"border-radius:12px;padding:14px 20px;margin-bottom:16px;"
            f"display:flex;align-items:center;justify-content:space-between;'>"
            f"<div>"
            f"<span style='font-size:1.05rem;color:#ffffff;font-weight:600;'>"
            f"{_salam}, {_user}! 👋</span><br/>"
            f"<span style='font-size:0.82rem;color:#85b7eb;'>"
            f"Siap membantu analisis statistik Anda hari ini.</span>"
            f"</div>"
            f"<div style='background:rgba(255,255,255,0.12);border-radius:8px;"
            f"padding:6px 14px;font-size:0.8rem;color:#d0e8ff;'>{_tier}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    st.markdown("""
    <div class="rs-header" style="display: flex; align-items: center; gap: 25px;">
        <img src="https://i.imgur.com/tESt5qg.png" width="80"
             style="background: rgba(255,255,255,0.1); padding: 8px; border-radius: 15px;">
        <div>
            <h1 style="margin: 0; font-size: 2.2rem;">Ruang Statistika</h1>
            <p style="margin: 0; opacity: 0.8;">
                AI-Powered Research & Stats Reporting — Data Anda Berbicara, AI Menjelaskan
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    metrics = [
        ("Modul Analisis", "30+", "Statistik lengkap"),
        ("AI Interpreter", "✨",  "Claude / GPT / Gemini"),
        ("Chat Analyst",   "💬",  "Tanya jawab data"),
        ("Export Laporan", "📄",  "Word / Markdown"),
    ]
    for col, (label, val, sub) in zip([c1, c2, c3, c4], metrics):
        with col:
            st.markdown(f"""<div class="rs-metric">
                <div class="rs-metric-label">{label}</div>
                <div class="rs-metric-value">{val}</div>
                <div class="rs-metric-sub">{sub}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<br/>", unsafe_allow_html=True)

    steps = [
        ("Upload & Cleaning",           "Unggah CSV/Excel/SPSS (.sav)/Stata (.dta)/TXT, sistem auto-bersihkan duplikat"),
        ("Compute Variabel (Opsional)", "Buat variabel baru: skor komposit, recode, transformasi"),
        ("Pilih Modul Analisis",        "Navigasi dari sidebar ke modul yang dibutuhkan"),
        ("Interpretasi AI (Opsional)",  "Masukkan API Key untuk narasi otomatis"),
        ("Generate Laporan",            "Export .docx atau .md dengan satu klik (Pro)"),
    ]
    for i, (title, desc) in enumerate(steps, 1):
        st.markdown(f"""
        <div class="rs-step">
            <div class="rs-step-num">{i}</div>
            <div>
                <div style='font-weight:500; color:#0c2340; font-size:0.95rem;'>{title}</div>
                <div style='font-size:0.85rem; color:#5f8ab5; margin-top:2px;'>{desc}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    from utils.effect_size import render_effect_size_summary_table
    with st.expander("📏 Panduan Effect Size (Cohen, 1988)"):
        render_effect_size_summary_table()

    st.info("💡 Mulai dari menu **📁 Upload & Cleaning** di sidebar kiri.")

    st.markdown("""
    <div class="rs-ai-narasi">
        <span class="rs-ai-badge">✨ v4.3 — Grouped Navigation</span><br/>
        <b>Baru di v4.3:</b> Login berbasis <b>nama pengguna & nama peneliti</b> di laporan kini tersedia<br/><br/>
        <b>Baru di v4.2:</b> <b>📈 Regresi, 📊 ANOVA, 📉 Regresi Logistik</b> kini tersedia
        <b>gratis terbatas</b> — analisis dasar (OLS, one-way ANOVA, odds ratio) dapat diakses
        tanpa License Key. Fitur lanjutan (VIF, post-hoc, ROC, AI) tetap eksklusif Pro.<br/><br/>
        <b>Baru di v4.2:</b> <b>📄 Generate Laporan</b> kini tersedia gratis <b>1 kali per hari</b>
        (tanpa narasi AI). Pro: laporan tak terbatas + narasi AI + grafik tertanam.<br/><br/>
        <b>Baru di v4.2:</b> Modul <b>🕸️ Web Scraping & Data Collector</b> — ambil data langsung dari website, tabel HTML, API REST/JSON, atau ekstrak teks via AI — langsung siap dianalisis.<br/><br/>
        <b>Baru di v4.2:</b> Modul <b>🔋 Power Analysis & Sample Size</b> — hitung ukuran sampel minimum dan kurva statistical power untuk t-test, ANOVA, regresi, proporsi, korelasi, dan chi-square.<br/><br/>
        <b>Baru di v4.2:</b> Navigasi sidebar kini dikelompokkan per kategori —
        Eksplorasi Data, Uji Statistik, Pemodelan, Faktor & SEM, AI & Laporan.<br/><br/>
        <b>Baru di v4.2:</b> Modul <b>🧮 Compute Variabel</b> — buat variabel baru via
        formula kustom, skor komposit, recode, standardisasi, transformasi log/power,
        dan lag/diff untuk data panel.<br/><br/>
        <b>Baru di v4.1 (Pro):</b> <b>Item-Total Statistics & Alpha jika Item Dihapus</b>
        — CITC, α-if-deleted, inter-item correlation matrix, flag item bermasalah,
        dan interpretasi AI item-level.
    </div>
    """, unsafe_allow_html=True)

elif menu == "Upload":
    from modules.upload import render
    render(ctx)

elif menu == "Scraping":
    if is_pro:
        from modules.scraping import render
        render(ctx)
    else:
        from utils.auth import require_pro
        require_pro(license_info, "Web Scraping & Data Collector")

elif menu == "EDA":
    from modules import eda
    eda.render(ctx)

elif menu == "Compute":
    from modules.compute import render
    render(ctx)

elif menu == "Deskriptif":
    from modules.deskriptif import render
    render(ctx)

elif menu == "Validitas":
    from modules.validitas import render
    render(ctx)

elif menu == "Korelasi":
    from modules.korelasi import render
    render(ctx)

elif menu == "Kelompok":
    from modules.kelompok import render
    render(ctx)

elif menu == "Klaster":
    from modules.klaster import render
    render(ctx)

elif menu == "Outlier":
    from modules.outlier import render
    render(ctx)

elif menu == "Uji Asumsi":
    from modules.uji_asumsi import render
    render(ctx)

elif menu == "Uji Beda":
    from modules.uji_beda import render
    render(ctx)
    
elif menu == "Uji Nonparametrik":
    from modules import uji_nonparametrik
    uji_nonparametrik.render(ctx)

elif menu == "Chat AI":
    from modules.chat_ai import render
    render(ctx)

elif menu == "Power Analysis":
    from modules.power_analysis import render
    render(ctx)

# ── Pro modules ───────────────────────────────────────────────────────────────

elif menu == "OLS Plus":
    if is_pro:
        from modules.ols_plus import render
        render(ctx)
    else:
        from utils.auth import require_pro
        require_pro(license_info, "Regresi OLS+")

elif menu == "OLS Robust":
    if is_pro:
        from modules.ols_robust import render
        render(ctx)
    else:
        from utils.auth import require_pro
        require_pro(license_info, "Regresi Robust & WLS")

elif menu == "Regresi":
    from modules.regresi import render
    render(ctx)

elif menu == "Mediasi":
    if is_pro:
        from modules.mediasi import render
        render(ctx)
    else:
        from utils.auth import require_pro
        require_pro(license_info, "Mediasi")

elif menu == "Moderasi":
    if is_pro:
        from modules.moderasi import render
        render(ctx)
    else:
        from utils.auth import require_pro
        require_pro(license_info, "Moderasi")

elif menu == "ANOVA":
    from modules.anova import render
    render(ctx)

elif menu == "Regresi Logistik":
    from modules.logistik import render
    render(ctx)

elif menu == "EFA":
    if is_pro:
        from modules.efa import render
        render(ctx)
    else:
        from utils.auth import require_pro
        require_pro(license_info, "EFA (Analisis Faktor)")

elif menu == "SEM":
    if is_pro:
        from modules.sem import render
        render(ctx)
    else:
        from utils.auth import require_pro
        require_pro(license_info, "SEM & CFA")
        
elif menu == "CFA":
    if is_pro:
        from modules.cfa import render
        render(ctx)
    else:
        from utils.auth import require_pro
        require_pro(license_info, "CFA Standalone")

elif menu == "Laporan":
    from modules.export import render
    render(ctx)


# ══════════════════════════════════════════════════════════════════════════════
# GLOBAL FOOTER
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<div class="rs-footer">
    📊 <b>Ruang Statistika</b> v4.5 — AI-Powered Assistant<br/>
    <a href='https://yogoaj.github.io' target='_blank'>Ruang Statistika</a> ·
    © 2026 Ruang Statistika · Powered by Python, Streamlit & Claude AI
</div>
""", unsafe_allow_html=True)
