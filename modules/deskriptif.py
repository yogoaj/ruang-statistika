"""
modules/deskriptif.py — Statistik Deskriptif (Free)
Ruang Statistika v4.0
"""

import streamlit as st

from utils.stats_helpers import (
    require_data, require_cols,
    descriptive_stats, normality_test,
    narrate_descriptive, ss_get,
)
from utils.plot_helpers import plotly_histogram, plotly_qq
from utils.ai_helpers import (
    ai_interpret_descriptive,
    ai_interpret_normality,
    ai_interpret_plots,
)


def render(ctx: dict):
    alpha_level       = ctx["alpha_level"]
    ai_enabled        = ctx["ai_enabled"]
    anthropic_api_key = ctx["anthropic_api_key"]
    ai_provider       = ctx["ai_provider"]

    st.markdown('<p class="rs-section-title">📊 Statistik Deskriptif</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="rs-section-sub">Ringkasan numerik, distribusi, dan uji normalitas setiap variabel.</p>',
        unsafe_allow_html=True,
    )

    df = require_data()
    if df is None:
        st.stop()
    cols = require_cols(df)
    if cols is None:
        st.stop()

    with st.spinner("Menghitung statistik..."):
        desc_df = descriptive_stats(df, cols)
        norm_df = normality_test(df, cols)

    # ── Pastikan ai_cache tersedia ────────────────────────────────────────────
    if "ai_cache" not in st.session_state:
        st.session_state.ai_cache = {}

    # =========================================================================
    # BAGIAN 1 — Statistik Deskriptif
    # =========================================================================
    st.dataframe(desc_df, use_container_width=True, hide_index=True)

    st.markdown(
        '<div class="rs-narasi">💬 <b>Interpretasi Otomatis</b><br/>' +
        narrate_descriptive(desc_df).replace("\n\n", "<br/><br/>") +
        "</div>",
        unsafe_allow_html=True,
    )

    if ai_enabled:
        if st.button("🤖 Interpretasi Deskriptif dengan AI", key="ai_desc_btn"):
            with st.spinner("🤖 AI sedang menganalisis data..."):
                ai_text = ai_interpret_descriptive(desc_df, norm_df, anthropic_api_key, ai_provider)
            st.session_state.ai_cache["descriptive"] = ai_text

        if ss_get("ai_cache", {}).get("descriptive"):
            st.markdown(
                f'<div class="rs-ai-narasi">'
                f'<span class="rs-ai-badge">✨ AI — {ai_provider.split("(")[0].strip()}</span><br/>'
                f'{ss_get("ai_cache", {})["descriptive"].replace(chr(10), "<br/>")}'
                f"</div>",
                unsafe_allow_html=True,
            )
    else:
        st.caption("💡 Aktifkan API Key di sidebar untuk interpretasi AI yang lebih mendalam.")

    # =========================================================================
    # BAGIAN 2 — Uji Normalitas Shapiro-Wilk
    # =========================================================================
    st.markdown("---")
    st.markdown("#### Uji Normalitas (Shapiro-Wilk)")
    st.dataframe(norm_df, use_container_width=True, hide_index=True)

    n_normal = (norm_df["Normal (α=0.05)"].str.contains("Ya")).sum()
    keterangan = (
        "Sebagian besar data berdistribusi normal."
        if n_normal >= len(norm_df) // 2
        else "Sebagian besar data TIDAK normal — pertimbangkan uji non-parametrik."
    )
    st.markdown(
        f'<div class="rs-narasi">💬 Dari {len(norm_df)} variabel, <b>{n_normal}</b> '
        f"berdistribusi normal (α = {alpha_level}). {keterangan}</div>",
        unsafe_allow_html=True,
    )

    if ai_enabled:
        if st.button("🤖 Interpretasi Normalitas dengan AI", key="ai_norm_btn"):
            with st.spinner("🤖 AI sedang menginterpretasi hasil normalitas..."):
                ai_norm_text = ai_interpret_normality(norm_df, alpha_level, anthropic_api_key, ai_provider)
            st.session_state.ai_cache["normality"] = ai_norm_text

        if ss_get("ai_cache", {}).get("normality"):
            st.markdown(
                f'<div class="rs-ai-narasi">'
                f'<span class="rs-ai-badge">✨ AI — {ai_provider.split("(")[0].strip()}</span><br/>'
                f'{ss_get("ai_cache", {})["normality"].replace(chr(10), "<br/>")}'
                f"</div>",
                unsafe_allow_html=True,
            )
    else:
        st.caption("💡 Aktifkan API Key di sidebar untuk interpretasi normalitas dengan AI.")

    # =========================================================================
    # BAGIAN 3 — Histogram & Q-Q Plot
    # =========================================================================
    st.markdown("---")
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("#### Histogram")
        col_h = st.selectbox("Pilih variabel:", cols, key="hist_sel")
        hist_fig = plotly_histogram(df[col_h].dropna(), col_h)
        st.plotly_chart(hist_fig, use_container_width=True)

    with col_b:
        st.markdown("#### Q-Q Plot")
        col_q = st.selectbox("Pilih variabel:", cols, key="qq_sel")
        qq_fig = plotly_qq(df[col_q], f"Q-Q Plot: {col_q}")
        st.plotly_chart(qq_fig, use_container_width=True)

    # ── Simpan figure ke session state untuk export ───────────────────────────
    st.session_state["deskriptif_figs"] = {
        "histogram": hist_fig,          # go.Figure — dipakai export.py → PNG
        "qq_plot":   qq_fig,
        "hist_var":  col_h,             # nama variabel untuk caption docx
        "qq_var":    col_q,
    }

    # Ambil statistik untuk variabel yang dipilih di histogram & QQ-plot
    def _get_var_stats(df, col_name, norm_df):
        """Ambil statistik ringkas satu variabel dari desc & norm df."""
        series = df[col_name].dropna()
        vstats = {
            "variabel": col_name,
            "n":        int(series.count()),
            "mean":     round(float(series.mean()), 4),
            "std":      round(float(series.std()), 4),
            "skewness": round(float(series.skew()), 4),
            "kurtosis": round(float(series.kurt()), 4),
            "min":      round(float(series.min()), 4),
            "max":      round(float(series.max()), 4),
        }
        if norm_df is not None and not norm_df.empty:
            norm_row = norm_df[norm_df.iloc[:, 0] == col_name]
            if not norm_row.empty:
                row = norm_row.iloc[0]
                vstats["shapiro_stat"]   = str(row.get("Statistik W", ""))
                vstats["shapiro_pvalue"] = str(row.get("p-value", ""))
                vstats["normal"]         = str(row.get("Normal (α=0.05)", ""))
        return vstats

    if ai_enabled:
        hist_stats = _get_var_stats(df, col_h, norm_df)
        qq_stats   = _get_var_stats(df, col_q, norm_df)
        plot_vars  = list({col_h, col_q})

        if st.button("🤖 Interpretasi Histogram & Q-Q Plot dengan AI", key="ai_plots_btn"):
            with st.spinner("🤖 AI sedang menginterpretasi grafik distribusi..."):
                ai_plots_text = ai_interpret_plots(
                    hist_stats if col_h == col_q else [hist_stats, qq_stats],
                    anthropic_api_key,
                    ai_provider,
                    same_var=(col_h == col_q),
                )
            st.session_state.ai_cache["plots"] = ai_plots_text
            st.session_state.ai_cache["plots_vars"] = plot_vars

        if ss_get("ai_cache", {}).get("plots"):
            vars_label = " & ".join(ss_get("ai_cache", {}).get("plots_vars", []))
            st.markdown(
                f'<div class="rs-ai-narasi">'
                f'<span class="rs-ai-badge">✨ AI — {ai_provider.split("(")[0].strip()} | {vars_label}</span><br/>'
                f'{ss_get("ai_cache", {})["plots"].replace(chr(10), "<br/>")}'
                f"</div>",
                unsafe_allow_html=True,
            )
    else:
        st.caption("💡 Aktifkan API Key di sidebar untuk interpretasi grafik distribusi dengan AI.")
