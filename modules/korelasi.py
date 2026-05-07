"""
modules/korelasi.py — Analisis Korelasi (Free)
Ruang Statistika v4.0
"""

import streamlit as st
from scipy import stats

from utils.stats_helpers import require_data, require_cols, narrate_correlation, ss_get
from utils.plot_helpers import plotly_heatmap, plotly_scatter
from utils.effect_size import interpret_effect_size, render_effect_size_card
from utils.ai_helpers import (
    ai_interpret_correlation,
    ai_interpret_heatmap,
    ai_interpret_scatter,
)


def render(ctx: dict):
    ai_enabled  = ctx["ai_enabled"]
    api_key     = ctx["anthropic_api_key"]
    ai_provider = ctx["ai_provider"]

    st.markdown('<p class="rs-section-title">🔗 Analisis Korelasi</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="rs-section-sub">Heatmap korelasi Pearson interaktif antar variabel.</p>',
        unsafe_allow_html=True,
    )

    df = require_data()
    if df is None:
        st.stop()
    cols = require_cols(df)
    if cols is None or len(cols) < 2:
        st.warning("⚠️ Pilih minimal 2 kolom numerik.")
        st.stop()

    # Pastikan ai_cache tersedia
    if "ai_cache" not in st.session_state:
        st.session_state.ai_cache = {}

    corr = df[cols].corr()

    # =========================================================================
    # BAGIAN 1 — Heatmap Korelasi
    # =========================================================================
    st.markdown("#### Heatmap Korelasi Pearson")
    st.plotly_chart(plotly_heatmap(corr), use_container_width=True)

    st.markdown(
        f'<div class="rs-narasi">💬 {narrate_correlation(corr)}</div>',
        unsafe_allow_html=True,
    )

    if ai_enabled:
        if st.button("🤖 Interpretasi Heatmap dengan AI", key="ai_heatmap_btn"):
            with st.spinner("🤖 AI sedang membaca pola heatmap..."):
                ai_hm = ai_interpret_heatmap(corr, api_key, ai_provider)
            st.session_state.ai_cache["heatmap"] = ai_hm

        if ss_get("ai_cache", {}).get("heatmap"):
            st.markdown(
                f'<div class="rs-ai-narasi">'
                f'<span class="rs-ai-badge">✨ AI — {ai_provider.split("(")[0].strip()}</span><br/>'
                f'{ss_get("ai_cache", {})["heatmap"].replace(chr(10), "<br/>")}'
                f"</div>",
                unsafe_allow_html=True,
            )
    else:
        st.caption("💡 Aktifkan API Key di sidebar untuk interpretasi heatmap dengan AI.")

    # =========================================================================
    # BAGIAN 2 — Matriks Korelasi (Tabel)
    # =========================================================================
    st.markdown("---")
    st.markdown("#### Matriks Korelasi (Tabel)")
    st.dataframe(corr.round(3), use_container_width=True)

    if ai_enabled:
        if st.button("🤖 Interpretasi Matriks Korelasi dengan AI", key="ai_corr_btn"):
            with st.spinner("🤖 AI sedang menganalisis pola korelasi..."):
                ai_corr = ai_interpret_correlation(corr, api_key, ai_provider)
            st.session_state.ai_cache["correlation"] = ai_corr

        if ss_get("ai_cache", {}).get("correlation"):
            st.markdown(
                f'<div class="rs-ai-narasi">'
                f'<span class="rs-ai-badge">✨ AI — {ai_provider.split("(")[0].strip()}</span><br/>'
                f'{ss_get("ai_cache", {})["correlation"].replace(chr(10), "<br/>")}'
                f"</div>",
                unsafe_allow_html=True,
            )
    else:
        st.caption("💡 Aktifkan API Key di sidebar untuk interpretasi matriks dengan AI.")

    # =========================================================================
    # BAGIAN 3 — Scatter Plot Dua Variabel
    # =========================================================================
    st.markdown("---")
    st.markdown("#### Scatter Plot Dua Variabel")
    ca, cb = st.columns(2)
    with ca:
        var_x = st.selectbox("Variabel X:", cols, index=0, key="scatter_x")
    with cb:
        var_y = st.selectbox("Variabel Y:", cols, index=min(1, len(cols) - 1), key="scatter_y")

    if var_x != var_y:
        paired = df[[var_x, var_y]].dropna()
        r_val, p_val = stats.pearsonr(paired[var_x], paired[var_y])
        scatter_fig = plotly_scatter(paired, var_x, var_y, r_val, p_val)
        st.plotly_chart(scatter_fig, use_container_width=True)

        sig_txt = "signifikan" if p_val < 0.05 else "tidak signifikan"
        st.markdown(
            f'<div class="rs-narasi">💬 Korelasi antara <b>{var_x}</b> dan <b>{var_y}</b>: '
            f'r = {r_val:.4f}, p = {p_val:.4f} ({sig_txt} pada α = 0.05).</div>',
            unsafe_allow_html=True,
        )

        # ── Simpan scatter ke session state untuk export ──────────────────
        st.session_state["korelasi_scatter"] = {
            "fig":   scatter_fig,       # go.Figure — untuk export PNG
            "var_x": var_x,
            "var_y": var_y,
            "r_val": r_val,
            "p_val": p_val,
            "n":     len(paired),
        }
        from utils.effect_size import render_effect_size_card

        render_effect_size_card("r", abs(r_val))
        # ── AI: Scatter Plot ──────────────────────────────────────────────
        if ai_enabled:
            if st.button("🤖 Interpretasi Scatter Plot dengan AI", key="ai_scatter_btn"):
                scatter_stats = {
                    "var_x": var_x,
                    "var_y": var_y,
                    "n":     len(paired),
                    "r":     round(r_val, 4),
                    "p":     round(p_val, 4),
                    "r2":    round(r_val ** 2, 4),
                    "signifikan": p_val < 0.05,
                    "corr_matriks_konteks": corr.round(3).to_dict(),
                }
                with st.spinner("🤖 AI sedang menginterpretasi scatter plot..."):
                    ai_sc = ai_interpret_scatter(scatter_stats, api_key, ai_provider)
                st.session_state.ai_cache["scatter"] = ai_sc
                st.session_state.ai_cache["scatter_vars"] = f"{var_x} × {var_y}"

            if ss_get("ai_cache", {}).get("scatter"):
                vars_label = ss_get("ai_cache", {}).get("scatter_vars", "")
                st.markdown(
                    f'<div class="rs-ai-narasi">'
                    f'<span class="rs-ai-badge">✨ AI — {ai_provider.split("(")[0].strip()}'
                    f'{" | " + vars_label if vars_label else ""}</span><br/>'
                    f'{ss_get("ai_cache", {})["scatter"].replace(chr(10), "<br/>")}'
                    f"</div>",
                    unsafe_allow_html=True,
                )
        else:
            st.caption("💡 Aktifkan API Key di sidebar untuk interpretasi scatter plot dengan AI.")

    else:
        st.info("Pilih dua variabel yang berbeda.")
        # Bersihkan scatter session jika variabel sama
        st.session_state.pop("korelasi_scatter", None)
