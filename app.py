"""
Ruang Statistika — Automated Research & Stats Reporting
Oleh: Yogo Aryo Jatmiko | yogoaj.github.io
Versi: 4.8 Pro — Supabase Auth + Google OAuth

Entry point: routing menu, sidebar, shared CSS & state.
Setiap modul di modules/ bertanggung jawab atas halaman-nya sendiri.
"""

import warnings
import streamlit as st
import streamlit.components.v1 as components
from utils.styles import (
    inject_global_css, inject_login_css,
    inject_nav_highlight_css, inject_nav_locked_css,
    render_greeting, render_hero_header,
    render_metrics_row, render_steps_grid,
    render_cta_wizard, render_changelog,
)

warnings.filterwarnings("ignore")

# ── Supabase: tangkap Google callback + restore session ──────────────────────
# Urutan PENTING: handle_google_callback dulu, baru restore_supabase_session
# Keduanya harus dipanggil SEBELUM apapun di-render, termasuk sidebar
from utils.supabase_auth import handle_google_callback, restore_supabase_session, supabase_update_password

# ── Tangkap fragment URL (#access_token=...&type=recovery) dari Supabase ─────
# Supabase mengirim token reset password / OAuth lewat URL fragment (#),
# tapi st.query_params hanya bisa baca query string (?).
# Script ini membaca window.location.hash dan redirect ke URL yang sama
# dengan fragment diubah menjadi query string, sehingga handle_google_callback
# bisa membacanya via st.query_params.
if not st.query_params.get("access_token"):
    components.html("""
    <script>
    (function() {
        function convertFragment() {
            try {
                var hash = window.parent.location.hash;
                if (hash && hash.includes('access_token')) {
                    var params = hash.replace(/^#/, '');
                    var newUrl = window.parent.location.origin +
                                 window.parent.location.pathname + '?' + params;
                    window.parent.location.replace(newUrl);
                    return true;
                }
            } catch(e) {}
            return false;
        }
        // Jalankan langsung + retry bertingkat
        convertFragment();
        setTimeout(convertFragment, 100);
        setTimeout(convertFragment, 400);
        setTimeout(convertFragment, 900);
        setTimeout(convertFragment, 1800);
    })();
    </script>
    """, height=1)

handle_google_callback()        # tangkap token dari Google OAuth redirect
restore_supabase_session()      # restore session jika token masih valid

# ── Page config (harus paling pertama) ───────────────────────────────────────
_is_logged_in = st.session_state.get("user_logged_in", False)
st.set_page_config(
    page_title="Ruang Statistika",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded" if _is_logged_in else "collapsed",
)

# ── Global CSS (utils/styles.py) ────────────────────────────────────────────
inject_global_css()


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
            ("Wizard",            "🧭  Wizard Analisis",        False),
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
            ("Reliabilitas ICC",  "📏  Reliabilitas ICC",       True),
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
            ("Time Series",       "⏱️  Time Series Analysis",   True), 
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
    st.markdown(
        """<div style='text-align:center;padding:16px 0 10px;
                    border-bottom:1px solid rgba(255,255,255,.06);margin-bottom:4px;'>
        <div style='width:44px;height:44px;border-radius:10px;
                    background:rgba(255,255,255,.08);
                    display:flex;align-items:center;justify-content:center;
                    margin:0 auto 8px;padding:6px;'>
            <img src='https://i.imgur.com/RF4mzxf.png' width='32' height='32'
                 style='object-fit:contain;filter:drop-shadow(0 2px 6px rgba(0,0,0,.25));'
                 alt='logo'></div>
        <div style='font-size:.9rem;color:#ffffff;font-weight:600;letter-spacing:-.1px;'>
            Ruang Statistika</div>
        <div style='font-size:.6rem;color:#2d5a87;letter-spacing:.1em;
                    text-transform:uppercase;margin-top:3px;'>
            v4.8 &#183; AI-Powered</div>
        </div>""",
        unsafe_allow_html=True,
    )

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
        _user_data    = st.session_state.get("_user_data", {})
        _is_pro_user  = _user_data.get("role") == "pro"
        _user_tier    = _user_data.get("tier", "starter") if _is_pro_user else "free"
        _TIER_COLORS  = {
            "starter":      ("#185FA5", "#0c2340"),
            "premium":      ("#7c3aed", "#4c1d95"),
            "professional": ("#b45309", "#78350f"),
        }
        _tc = _TIER_COLORS.get(_user_tier, ("#185FA5", "#0c2340"))
        _tier_badge   = (
            f"<span style='background:linear-gradient(90deg,{_tc[0]},{_tc[1]});"
            "color:#fff;font-size:0.65rem;font-weight:600;letter-spacing:0.04em;"
            f"padding:2px 8px;border-radius:10px;margin-left:6px;'>"
            f"{_user_tier.upper()}</span>"
            if _is_pro_user else
            "<span style='background:linear-gradient(90deg,#F5B800,#d4980a);color:#000;font-weight:800;"
            "font-size:0.68rem;padding:2px 9px;border-radius:10px;margin-left:6px;letter-spacing:.3px;'>"
            "GRATIS</span>"
        )
        _sb_init  = "".join(w[0].upper() for w in _display_name.split()[:2]) if _display_name else "?"
        _sb_email = st.session_state.get("_user_data", {}).get("email", "") or "Mode Gratis"
        st.markdown(
            f"""<div style='margin:8px 12px 4px;background:rgba(24,95,165,.18);
                    border-radius:8px;padding:8px 10px;
                    display:flex;align-items:center;gap:8px;'>
                <div style='width:30px;height:30px;border-radius:50%;background:#185FA5;
                            display:flex;align-items:center;justify-content:center;
                            font-size:.65rem;color:#fff;font-weight:600;flex-shrink:0;'
                    >{_sb_init}</div>
                <div style='min-width:0;overflow:hidden;'>
                    <div style='font-size:.82rem;color:#fff;font-weight:600;
                                white-space:nowrap;overflow:hidden;text-overflow:ellipsis;'
                        >{_display_name}{_tier_badge}</div>
                    <div style='font-size:.62rem;color:#4a7aaa;margin-top:1px;
                                white-space:nowrap;overflow:hidden;text-overflow:ellipsis;'
                        >{_sb_email}</div>
                </div></div>""",
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
    _session_role = st.session_state.get("_user_data", {}).get("role", "free")
    is_pro = (license_info["status"] == "pro") or (_session_role == "pro")

    st.markdown("---")

    # ── AI Provider ──────────────────────────────────────────────────────────
    from utils.ai_helpers import (
        ALL_PROVIDERS, PROVIDER_KEY_INFO,
        FREE_PROVIDER_KEYS, TRIAL_PROVIDER_KEYS,
    )

    st.markdown(
        "<p class='nav-group-label'>🤖 AI Interpreter</p>",
        unsafe_allow_html=True,
    )

    # ── Bangun dropdown dengan separator ──────────────────────────────────────
    # Kelompok berdasarkan prefix provider
    _separator_before = {
        "🌊 Mistral AI — Nemo":   "── 🟡 Trial Gratis ────────────",
        "🤖 Claude — Sonnet 4":   "── 💳 Berbayar ─────────────────",
    }

    provider_display = []
    for p in ALL_PROVIDERS:
        if p in _separator_before:
            provider_display.append(_separator_before[p])
        provider_display.append(p)
    # Tambah separator di awal untuk grup Gratis
    provider_display.insert(0, "── ✅ Gratis ────────────────────")

    ai_provider_raw = st.selectbox(
        "Pilih Provider AI",
        provider_display,
        help="Groq, Gemini, OpenRouter & HuggingFace GRATIS · Mistral & Cohere Trial Gratis",
    )

    # Jika user pilih separator (baris pemisah), default ke provider pertama
    ai_provider = (
        ai_provider_raw if not ai_provider_raw.startswith("──")
        else ALL_PROVIDERS[0]
    )

    key_label, key_url = PROVIDER_KEY_INFO.get(ai_provider, ("API Key", ""))

    # ── Badge status provider ─────────────────────────────────────────────────
    _prov_keyword = next(
        (k for k in FREE_PROVIDER_KEYS if k in ai_provider), None
    )
    _trial_keyword = next(
        (k for k in TRIAL_PROVIDER_KEYS if k in ai_provider), None
    )

    if _prov_keyword:
        st.markdown(
            "<span style='background:#eaf3de;color:#3b6d11;padding:2px 10px;"
            "border-radius:10px;font-size:0.72rem;font-weight:600;'>✅ GRATIS</span>",
            unsafe_allow_html=True,
        )
    elif _trial_keyword:
        st.markdown(
            "<span style='background:#fff8e1;color:#b45309;padding:2px 10px;"
            "border-radius:10px;font-size:0.72rem;font-weight:600;'>🟡 TRIAL GRATIS</span>",
            unsafe_allow_html=True,
        )

    anthropic_api_key = st.text_input(
        key_label, type="password",
        help=f"Daftar/login di: https://{key_url}" if key_url else "",
    )
    ai_enabled = bool(anthropic_api_key)

    if ai_enabled:
        # Ambil nama singkat provider untuk pesan sukses
        provider_short = ai_provider.split("—")[1].strip() if "—" in ai_provider else ai_provider
        st.success(f"🤖 {provider_short} Aktif")
    else:
        if key_url:
            st.caption(f"Daftar di [{key_url}](https://{key_url})")

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
        inject_nav_locked_css()

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

    # Hitung indeks 0-based posisi menu aktif dalam flat list (untuk CSS nth-child)
    _flat_keys = [key for key, _label, _is_pro in _iter_menu_items()]
    active_idx = _flat_keys.index(menu) if menu in _flat_keys else 0

    inject_nav_highlight_css(active_idx)

    # ── Parameter ─────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown(
        "<p class='nav-group-label'>⚙️ Parameter</p>",
        unsafe_allow_html=True,
    )
    alpha_level = st.slider("Signifikansi (α)", 0.01, 0.10, 0.05, 0.01)
    r_tab       = st.number_input("r-tabel Validitas", 0.10, 0.50, 0.30, 0.01)

    st.markdown("---")
    st.markdown(
        "<div class='rs-footer' style='margin-top:1rem;padding-top:.75rem;font-size:.68rem;'>"
        "<a href='https://yogoaj.github.io/#aplikasi' target='_blank'>Ruang Statistika</a>"
        "<br/>© 2026 v4.8</div>",
        unsafe_allow_html=True,
    )


# ── Context dict — diteruskan ke setiap modul ────────────────────────────────
_ctx_user_data = st.session_state.get("_user_data", {})
ctx = {
    "license_info":      license_info,
    "is_pro":            is_pro,
    "user_tier":         _ctx_user_data.get("tier", "free") if is_pro else "free",
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

        # ── Intercept: jika ada access_token di query_params tapi belum diproses ──
        # Ini terjadi saat JS sudah berhasil konversi fragment → query params,
        # tapi handle_google_callback() di atas belum berjalan (rerun belum terjadi).
        # Paksa rerun supaya handle_google_callback() membaca token yang baru masuk.
        if st.query_params.get("access_token") and not st.session_state.get("_recovery_access_token") and not st.session_state.get("user_logged_in"):
            _token_type = st.query_params.get("type", "")
            if _token_type == "recovery":
                from utils.supabase_auth import handle_google_callback
                handle_google_callback()
                st.rerun()
            else:
                from utils.supabase_auth import handle_google_callback
                handle_google_callback()
                st.rerun()

        # ── CSS: halaman login (utils/styles.py) ────────────────────────────
        inject_login_css()

        # ── Header kartu: gradient biru (nada email konfirmasi) ─────────────
        st.markdown("""
        <div class="signin-card">
          <div class="signin-card-header">
            <div class="signin-header-logo">
              <img src="https://i.imgur.com/RF4mzxf.png" alt="logo Ruang Statistika">
            </div>
            <div class="signin-header-title">Ruang Statistika</div>
            <div class="signin-header-sub">AI-Powered Research &amp; Stats Reporting</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # ── JS: baca URL fragment dari Supabase callback ────────────────────
        # Diperlukan untuk: Google OAuth callback DAN link reset password.
        # Supabase mengirim token via URL fragment (#access_token=...&type=recovery)
        # yang tidak dikirim ke server — dibaca JS lalu dikonversi ke query_params.
        components.html("""
        <script>
        (function() {
            function convertFragment() {
                try {
                    var hash = window.parent.location.hash.substring(1);
                    if (!hash || hash.indexOf('access_token') === -1) return false;
                    var params = new URLSearchParams(hash);
                    var at = params.get('access_token');
                    var rt = params.get('refresh_token') || '';
                    var tp = params.get('type') || '';
                    if (!at) return false;
                    var url = new URL(window.parent.location.href);
                    url.hash = '';
                    url.searchParams.set('access_token', at);
                    if (rt) url.searchParams.set('refresh_token', rt);
                    if (tp) url.searchParams.set('type', tp);
                    window.parent.location.replace(url.toString());
                    return true;
                } catch(e) {}
                return false;
            }
            // Jalankan langsung + retry bertingkat — height=1 agar iframe tidak di-skip browser
            convertFragment();
            setTimeout(convertFragment, 100);
            setTimeout(convertFragment, 400);
            setTimeout(convertFragment, 900);
            setTimeout(convertFragment, 1800);
        })();
        </script>
        """, height=1)

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
                if st.form_submit_button("Masuk →", use_container_width=True, type="primary"):
                    from utils.supabase_auth import supabase_sign_in
                    _ok, _msg = supabase_sign_in(_email_inp.strip(), _pw_inp)
                    if _ok:
                        st.query_params.clear()
                        st.rerun()
                    else:
                        st.session_state["_auth_msg_error"] = _msg
                        st.rerun()

            # Link lupa password — di luar form, tampil sebagai link teks kecil rata kanan
            st.markdown('<div class="signin-link-btn-right">', unsafe_allow_html=True)
            if st.button("Lupa password?", key="btn_ke_lupa", use_container_width=False):
                st.session_state.modal_tab = "lupa"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

            # ── Info: sudah beli Pro, login langsung pakai email + password ──
            st.markdown("""
            <div style='background:linear-gradient(135deg,#f5f0ff,#ede9fe);
                        border:1px solid #c4b5fd; border-radius:10px;
                        padding:10px 14px; margin:14px 0 4px;
                        font-size:0.80rem; color:#4c1d95; line-height:1.7;'>
                <div style='font-weight:700; font-size:0.82rem; margin-bottom:4px;'>
                    🎫 Sudah membeli Pro?
                </div>
                Langsung masuk menggunakan <b>email</b> dan <b>password</b> yang
                dikirim ke email kamu setelah pembelian. Tidak perlu daftar ulang.
            </div>
            """, unsafe_allow_html=True)

            # ── Tombol Google OAuth — SEMENTARA DINONAKTIFKAN (error callback) ──
            # st.markdown('<div class="signin-divider">atau masuk dengan</div>', unsafe_allow_html=True)
            # if st.button("🔵  Lanjutkan dengan Google", key="btn_google_login",
            #              use_container_width=True):
            #     from utils.supabase_auth import supabase_sign_in_google
            #     _ok, _url_or_err = supabase_sign_in_google()
            #     if _ok:
            #         st.markdown(
            #             f'<meta http-equiv="refresh" content="0; url={_url_or_err}">',
            #             unsafe_allow_html=True,
            #         )
            #         st.stop()
            #     else:
            #         st.session_state["_auth_msg_error"] = _url_or_err
            #         st.rerun()

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

            # ── Info: sudah beli Pro, tidak perlu daftar ────────────────────
            st.markdown("""
            <div style='background:linear-gradient(135deg,#f5f0ff,#ede9fe);
                        border:1px solid #c4b5fd; border-radius:10px;
                        padding:10px 14px; margin:12px 0 4px;
                        font-size:0.80rem; color:#4c1d95; line-height:1.7;'>
                <div style='font-weight:700; font-size:0.82rem; margin-bottom:4px;'>
                    🎫 Sudah membeli Pro?
                </div>
                Coba gunakan tab <b>Masuk</b> terlebih dahulu dengan <b>email</b>
                dan <b>password</b> yang dikirim ke emailmu setelah pembelian.<br/>
                Jika belum berhasil, daftar di sini menggunakan <b>email yang sama</b>
                untuk membuat akun baru.
            </div>
            """, unsafe_allow_html=True)

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
            if st.session_state.get("_lupa_email_sent"):
                # ── State: email reset sudah terkirim ────────────────────────
                _sent_to = st.session_state.get("_lupa_email_sent", "")
                st.success(
                    f"📧 Link reset password telah dikirim ke **{_sent_to}**.\n\n"
                    "Cek inbox kamu (dan folder **Spam** jika tidak ada). "
                    "Klik link di email, lalu kamu akan diarahkan ke halaman "
                    "untuk membuat password baru."
                )
                st.info(
                    "⏱ Link berlaku selama **1 jam**. "
                    "Jika sudah expired, kamu bisa minta link baru di bawah."
                )
                st.markdown('<div class="signin-link-btn">', unsafe_allow_html=True)
                if st.button("Kirim Ulang Link Reset", key="btn_resend_reset",
                             use_container_width=True):
                    st.session_state.pop("_lupa_email_sent", None)
                    st.rerun()
                if st.button("← Kembali ke Masuk", key="go_masuk_from_lupa_sent",
                             use_container_width=True):
                    st.session_state.pop("_lupa_email_sent", None)
                    st.session_state.modal_tab = "masuk"
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                # ── State: form input email ───────────────────────────────────
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
                            try:
                                _app_url = st.secrets["app_url"]
                            except Exception:
                                _app_url = "https://ruang-statistika.streamlit.app"
                            _ok, _msg = supabase_forgot_password(_lupa_email.strip(), _app_url)
                            if _ok:
                                st.session_state["_lupa_email_sent"] = _lupa_email.strip().lower()
                            else:
                                st.session_state["_auth_msg_error"] = _msg
                            st.rerun()
                st.markdown('<div class="signin-link-btn">', unsafe_allow_html=True)
                if st.button("← Kembali ke Masuk", key="go_masuk_from_lupa",
                             use_container_width=True):
                    st.session_state.modal_tab = "masuk"
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

        elif tab == "reset_password":
            # Tab ini hanya muncul setelah user klik link reset dari email Supabase.
            # handle_google_callback() mendeteksi type=recovery lalu set modal_tab = 'reset_password'.
            st.markdown(
                "<p style='font-size:0.82rem;color:#5f8ab5;margin:0 0 12px;'>"
                "Masukkan password baru kamu di bawah ini.</p>",
                unsafe_allow_html=True)
            if not st.session_state.get("_recovery_access_token"):
                st.warning("⚠️ Sesi reset sudah tidak berlaku. Minta link reset baru.")
                st.markdown('<div class="signin-link-btn">', unsafe_allow_html=True)
                if st.button("← Minta Link Reset Baru", key="go_lupa_from_reset",
                             use_container_width=True):
                    st.session_state.modal_tab = "lupa"
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                with st.form("form_reset_password", clear_on_submit=True):
                    _new_pw  = st.text_input("Password Baru", placeholder="Minimal 6 karakter…",
                                             type="password")
                    _new_pw2 = st.text_input("Konfirmasi Password Baru",
                                             placeholder="Ulangi password baru…",
                                             type="password")
                    if st.form_submit_button("Simpan Password Baru →",
                                             use_container_width=True, type="primary"):
                        if not _new_pw:
                            st.error("Password tidak boleh kosong.")
                        elif _new_pw != _new_pw2:
                            st.error("❌ Password dan konfirmasi tidak cocok.")
                        elif len(_new_pw) < 6:
                            st.error("❌ Password minimal 6 karakter.")
                        else:
                            _ok, _msg = supabase_update_password(_new_pw)
                            if _ok:
                                st.session_state["_auth_msg_success"] = _msg
                                st.session_state.modal_tab = "masuk"
                                st.rerun()
                            else:
                                st.error(_msg)

        elif tab == "pro":
            with st.form("form_pro", clear_on_submit=False):
                _key_inp  = st.text_input("License Key", placeholder="XXXX-XXXX-XXXX",
                                          type="password")
                _pro_name = st.text_input("Nama Anda (untuk laporan)",
                                          placeholder="Nama peneliti…")
                if st.form_submit_button("Aktifkan Pro →", use_container_width=True,
                                         type="primary"):
                    from utils.supabase_auth import validate_license_supabase
                    from utils.auth import validate_license as _validate_registry
                    _k = _key_inp.strip().upper()
                    if not _k:
                        st.error("Masukkan license key terlebih dahulu.")
                    else:
                        # Cek Supabase dulu (key dinamis dari Lynk.id)
                        _info = validate_license_supabase(_k)
                        # Fallback ke LICENSE_REGISTRY (key hardcoded lama)
                        if _info.get("status") != "pro":
                            _info_reg = _validate_registry(_k)
                            if _info_reg.get("status") == "pro":
                                _info = {
                                    "status": "pro",
                                    "label":  _info_reg.get("label", "Pro"),
                                    "expires": str(_info_reg["expires"]) if _info_reg.get("expires") else None,
                                    "name":   "",
                                    "email":  "",
                                    "tier":   "starter",
                                }

                        if _info.get("status") == "pro":
                            # Nama: dari input → dari pro_licenses → default
                            _dname = _pro_name.strip() or _info.get("name", "") or "Pengguna Pro"
                            st.session_state["_modal_license_key"] = _k
                            # sidebar_license_key adalah key widget st.text_input
                            # tidak bisa di-set manual — render_license_sidebar()
                            # otomatis baca dari _modal_license_key
                            st.session_state["user_logged_in"] = True
                            st.session_state["user_name"]      = _dname
                            st.session_state["_user_data"] = {
                                "username":    _info.get("email", "pro_key_user"),
                                "name":        _dname,
                                "email":       _info.get("email", ""),
                                "role":        "pro",
                                "tier":        _info.get("tier", "starter"),
                                "license_key": _k,
                                "expires_at":  _info.get("expires"),
                                "active":      True,
                            }
                            st.query_params.clear()
                            st.rerun()
                        elif _info.get("status") == "expired":
                            st.error("⏰ License key sudah expired. Perpanjang di lynk.id/ruangstatistika")
                        else:
                            st.error("❌ License key tidak valid. Pastikan key diketik dengan benar.")
            st.markdown(
                '<div class="signin-footer">Dapatkan key di '
                '<a href="https://lynk.id/ruangstatistika" target="_blank">lynk.id/ruangstatistika</a>'
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
                    _dname = _free_name.strip() or "Pengguna"
                    st.session_state["user_name"]      = _dname
                    st.session_state["user_logged_in"] = True
                    st.session_state["_user_data"] = {
                        "username":    "guest",
                        "name":        _dname,
                        "email":       "",
                        "role":        "free",
                        "tier":        "free",
                        "license_key": "",
                        "active":      True,
                    }
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
            © 2026 Ruang Statistika v4.8 ·
            <a href="https://lynk.id/ruangstatistika" target="_blank">lynk.id/ruangstatistika</a>
        </div>
        """, unsafe_allow_html=True)

        st.stop()

    # ── Beranda ────────────────────────────────────────────────────────────────
    _user = st.session_state.get("user_name", "")
    render_greeting(_user, is_pro)

    render_hero_header()
    render_metrics_row()

    st.markdown("<br/>", unsafe_allow_html=True)
    render_steps_grid()
    st.markdown("<br/>", unsafe_allow_html=True)

    from utils.effect_size import render_effect_size_summary_table
    with st.expander("📏 Panduan Effect Size (Cohen, 1988)"):
        render_effect_size_summary_table()

    st.markdown("<br/>", unsafe_allow_html=True)
    if render_cta_wizard():
        st.session_state.active_menu = "Wizard"
        st.rerun()

    st.info("💡 Baru di v4.8: Mulai dari **🧭 Wizard Analisis** untuk dipandu memilih uji.")
    render_changelog()

elif menu == "Wizard":
    from modules.wizard import render
    render(ctx)

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

elif menu == "Reliabilitas ICC":
    if is_pro:
        from modules.reliabilitas_icc import render
        render(ctx)
    else:
        from utils.auth import require_pro
        require_pro(license_info, "Reliabilitas ICC")

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

elif menu == "Time Series":
    if is_pro:
        from modules.time_series import render
        render(ctx)
    else:
        from utils.auth import require_pro
        require_pro(license_info, "Time Series Analysis")

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

st.markdown(
    '''<div class="rs-footer">
    📊 <b>Ruang Statistika</b> v4.8 &middot; AI-Powered Research &amp; Stats Reporting<br/>
    <a href="https://yogoaj.github.io/#aplikasi" target="_blank">ruangstatistika.app</a>
    &nbsp;&middot;&nbsp; &copy; 2026 Ruang Statistika
    &nbsp;&middot;&nbsp; Python &middot; Streamlit &middot; Claude AI
    </div>''',
    unsafe_allow_html=True,
)
