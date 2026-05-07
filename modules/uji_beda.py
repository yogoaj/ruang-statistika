"""
modules/uji_beda.py — Uji Beda: Parametrik & Non-Parametrik (Free)
Ruang Statistika v4.2

Tab 1 — t-test / Mann-Whitney (independen) — kode asli v4.0
Tab 2 — Uji Non-Parametrik Lengkap (Wilcoxon, Friedman, McNemar, Cochran Q, Korelasi Ordinal)
         → delegasi ke modules/uji_nonparametrik.py
"""

import numpy as np
import streamlit as st
import plotly.graph_objects as go
from scipy import stats

from utils.stats_helpers import require_data, require_cols, ss_get
from utils.ai_helpers import call_ai_api

# Impor sub-modul non-parametrik
try:
    from modules import uji_nonparametrik as _nonpar
    _NONPAR_AVAILABLE = True
except ImportError:
    _NONPAR_AVAILABLE = False


def render(ctx: dict):
    alpha_level = ctx["alpha_level"]
    ai_enabled  = ctx["ai_enabled"]
    api_key     = ctx["anthropic_api_key"]
    ai_provider = ctx["ai_provider"]

    st.markdown('<p class="rs-section-title">🔢 Uji Beda & Non-Parametrik</p>',
                unsafe_allow_html=True)
    st.markdown(
        '<p class="rs-section-sub">'
        'Uji perbedaan kelompok independen (t-test / Mann-Whitney) dan uji non-parametrik lengkap.'
        '</p>',
        unsafe_allow_html=True,
    )

    df = require_data()
    if df is None:
        st.stop()
    cols = require_cols(df)
    if cols is None or len(cols) < 1:
        st.stop()

    # ── Dua Tab utama ─────────────────────────────────────────────────────────
    tab_par, tab_nonpar = st.tabs([
        "📊 t-test / Mann-Whitney (Independen)",
        "📐 Non-Parametrik Lengkap",
    ])

    # ═══════════════════════════════════════════════════════════════════════════
    # TAB 1 — Kode asli (t-test & Mann-Whitney independen)
    # ═══════════════════════════════════════════════════════════════════════════
    with tab_par:
        cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()

        input_mode = st.radio(
            "Mode Input Kelompok:",
            ["Kolom kategorik (2 kelompok)", "Dua kolom numerik terpisah"],
            horizontal=True,
            key="ub_input_mode",
        )

        num_col  = st.selectbox("Variabel Numerik (Y):", cols, key="ub_num_col")
        uji_type = st.selectbox(
            "Jenis Uji:",
            ["Independent t-test (parametrik)", "Mann-Whitney U (non-parametrik)"],
            key="ub_uji_type",
        )

        grp_data: dict = {}

        if input_mode == "Kolom kategorik (2 kelompok)":
            if not cat_cols:
                st.error("❌ Tidak ada kolom kategorik. Pilih mode dua kolom numerik.")
                st.stop()
            cat_col = st.selectbox("Kolom Kelompok:", cat_cols, key="ub_cat_col")
            unique_vals = df[cat_col].dropna().unique()
            if len(unique_vals) < 2:
                st.warning("⚠️ Kolom kelompok harus memiliki minimal 2 nilai unik.")
                st.stop()
            g1_val = st.selectbox("Kelompok 1:", unique_vals, index=0, key="ub_g1")
            g2_val = st.selectbox(
                "Kelompok 2:", [v for v in unique_vals if v != g1_val],
                index=0, key="ub_g2",
            )
            grp_data = {
                str(g1_val): df[df[cat_col] == g1_val][num_col].dropna().values,
                str(g2_val): df[df[cat_col] == g2_val][num_col].dropna().values,
            }
        else:
            if len(cols) < 2:
                st.warning("⚠️ Diperlukan minimal 2 kolom numerik.")
                st.stop()
            col1 = st.selectbox("Kolom Kelompok 1:", cols, index=0, key="uji_c1")
            col2 = st.selectbox(
                "Kolom Kelompok 2:", [c for c in cols if c != col1],
                index=0, key="uji_c2",
            )
            grp_data = {
                col1: df[col1].dropna().values,
                col2: df[col2].dropna().values,
            }

        g_names = list(grp_data.keys())
        g1_arr, g2_arr = grp_data[g_names[0]], grp_data[g_names[1]]

        if len(g1_arr) < 2 or len(g2_arr) < 2:
            st.warning("⚠️ Setiap kelompok harus memiliki minimal 2 data.")
            st.stop()

        # ── Hitung ──────────────────────────────────────────────────────────
        if "t-test" in uji_type:
            t_stat, p_val = stats.ttest_ind(g1_arr, g2_arr, equal_var=False)
        else:
            t_stat, p_val = stats.mannwhitneyu(g1_arr, g2_arr, alternative="two-sided")

        sig       = p_val < alpha_level
        pooled_std = np.sqrt((g1_arr.std() ** 2 + g2_arr.std() ** 2) / 2)
        cohen_d   = (g1_arr.mean() - g2_arr.mean()) / pooled_std if pooled_std > 0 else 0

        # ── Simpan ke session_state ──────────────────────────────────────────
        st.session_state["uji_beda_result"] = {
            "uji_type":    uji_type,
            "num_col":     num_col,
            "g1_name":     g_names[0],
            "g2_name":     g_names[1],
            "g1_mean":     round(float(g1_arr.mean()), 4),
            "g2_mean":     round(float(g2_arr.mean()), 4),
            "statistic":   round(float(t_stat), 4),
            "p_value":     round(float(p_val), 4),
            "effect_size": round(float(cohen_d), 4),
            "signifikan":  sig,
            "alpha":       alpha_level,
        }

        m1, m2, m3, m4 = st.columns(4)
        sig_label = "✅ Signifikan" if sig else "❌ Tidak Sig."
        col_sig   = "#3b6d11" if sig else "#a32d2d"
        for col, lbl, val in zip(
            [m1, m2, m3, m4],
            [f"Mean {g_names[0]}", f"Mean {g_names[1]}", "Statistik Uji", "Cohen's d"],
            [round(float(g1_arr.mean()), 4), round(float(g2_arr.mean()), 4),
             round(float(t_stat), 4), round(float(cohen_d), 4)],
        ):
            col.markdown(
                f'<div class="rs-metric"><div class="rs-metric-label">{lbl}</div>'
                f'<div class="rs-metric-value" style="font-size:1.4rem">{val}</div></div>',
                unsafe_allow_html=True,
            )

        st.markdown(
            f'<div class="rs-narasi">💬 Hasil <b>{uji_type}</b>: statistik = {t_stat:.4f}, '
            f"p = {p_val:.4f}. "
            f'<span style="color:{col_sig}; font-weight:600;">{sig_label}</span> pada α = {alpha_level}.<br/>'
            f"Effect size Cohen's d = {cohen_d:.4f} "
            f"({'kecil' if abs(cohen_d) < 0.5 else 'sedang' if abs(cohen_d) < 0.8 else 'besar'}).</div>",
            unsafe_allow_html=True,
        )

        # ── Visualisasi ──────────────────────────────────────────────────────
        col_v1, col_v2 = st.columns(2)
        with col_v1:
            fig_bx = go.Figure()
            for i, (gname, garr) in enumerate(grp_data.items()):
                color = "#185FA5" if i == 0 else "#E24B4A"
                fig_bx.add_trace(go.Box(
                    y=garr, name=str(gname),
                    marker=dict(color=color), boxpoints="outliers",
                ))
            fig_bx.update_layout(title=f"Boxplot: {num_col} per Kelompok",
                                   template="plotly_white", height=350,
                                   margin=dict(l=20, r=20, t=50, b=20))
            st.plotly_chart(fig_bx, use_container_width=True)
        with col_v2:
            fig_vio = go.Figure()
            for i, (gname, garr) in enumerate(grp_data.items()):
                color = "#185FA5" if i == 0 else "#E24B4A"
                fig_vio.add_trace(go.Violin(
                    y=garr, name=str(gname),
                    box_visible=True, meanline_visible=True,
                    fillcolor=color, opacity=0.6, line_color=color,
                ))
            fig_vio.update_layout(title=f"Violin Plot: {num_col}",
                                   template="plotly_white", height=350,
                                   margin=dict(l=20, r=20, t=50, b=20))
            st.plotly_chart(fig_vio, use_container_width=True)

        # ── AI ───────────────────────────────────────────────────────────────
        if ai_enabled:
            if st.button("🤖 Interpretasi Uji Beda dengan AI", key="ai_uji_btn"):
                prompt = f"""
Hasil {uji_type}:
- Statistik uji = {t_stat:.4f}, p-value = {p_val:.4f}
- Alpha = {alpha_level}
- Cohen's d = {cohen_d:.4f}
- Kesimpulan: {'Signifikan' if sig else 'Tidak Signifikan'}

Berikan interpretasi dalam Bahasa Indonesia mencakup:
1. Arti hasil uji beda dan kesimpulannya
2. Makna effect size (Cohen's d)
3. Implikasi praktis dari temuan ini
4. Rekomendasi analisis lanjutan
Format: 2-3 paragraf akademis.
"""
                with st.spinner("🤖 AI sedang menganalisis..."):
                    ai_uji = call_ai_api(prompt, api_key=api_key, provider=ai_provider)
                if "ai_cache" not in st.session_state:
                    st.session_state.ai_cache = {}
                st.session_state.ai_cache["uji_beda"] = ai_uji

            if ss_get("ai_cache", {}).get("uji_beda"):
                st.markdown(
                    f'<div class="rs-ai-narasi">'
                    f'<span class="rs-ai-badge">✨ AI — {ai_provider.split("(")[0].strip()}</span><br/>'
                    f'{ss_get("ai_cache", {})["uji_beda"].replace(chr(10), "<br/>")}'
                    f"</div>",
                    unsafe_allow_html=True,
                )
        else:
            st.caption("💡 Aktifkan API Key di sidebar untuk interpretasi AI.")

    # ═══════════════════════════════════════════════════════════════════════════
    # TAB 2 — Non-Parametrik Lengkap (delegasi ke uji_nonparametrik.py)
    # ═══════════════════════════════════════════════════════════════════════════
    with tab_nonpar:
        if _NONPAR_AVAILABLE:
            _nonpar.render(ctx)
        else:
            st.error(
                "❌ Modul `modules/uji_nonparametrik.py` tidak ditemukan. "
                "Pastikan file tersebut ada di direktori `modules/`."
            )
            st.code("# Salin file uji_nonparametrik.py ke folder modules/", language="bash")
