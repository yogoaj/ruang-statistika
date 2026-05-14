"""
modules/anova.py — ANOVA + Post-hoc + Kruskal-Wallis
Ruang Statistika v4.2

Tier akses:
- FREE : One-way ANOVA, statistik deskriptif per kelompok, visualisasi boxplot &
         bar chart, effect size η², export Excel.
- PRO  : Semua fitur gratis + post-hoc Tukey HSD / Bonferroni, Kruskal-Wallis,
         interpretasi AI, dan hasil tersimpan ke session_state untuk laporan.

Perbaikan v4.2:
- Pisah fitur Free / Pro tanpa hard-stop di awal modul
"""

import io
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from scipy import stats
from itertools import combinations

from utils.stats_helpers import require_data, require_cols, ss_get
from utils.ai_helpers import call_ai_api
from utils.effect_size import render_effect_size_card


def _tukey_hsd(groups: dict, alpha: float = 0.05) -> pd.DataFrame:
    """Tukey HSD via statsmodels, fallback ke Bonferroni pairwise t-test."""
    try:
        from statsmodels.stats.multicomp import pairwise_tukeyhsd
        all_data   = np.concatenate(list(groups.values()))
        all_labels = np.concatenate([[k] * len(v) for k, v in groups.items()])
        result     = pairwise_tukeyhsd(all_data, all_labels, alpha=alpha)
        return pd.DataFrame(
            result.summary().data[1:],
            columns=result.summary().data[0]
        )
    except Exception:
        rows = []
        keys = list(groups.keys())
        n_pairs = len(list(combinations(keys, 2)))
        for g1, g2 in combinations(keys, 2):
            t, p = stats.ttest_ind(groups[g1], groups[g2])
            p_bonf = min(p * n_pairs, 1.0)
            rows.append({
                "Kelompok 1": g1, "Kelompok 2": g2,
                "t-stat": round(t, 4), "p-adj (Bonferroni)": round(p_bonf, 4),
                "Signifikan": "✓" if p_bonf < alpha else "✗",
            })
        return pd.DataFrame(rows)


def render(ctx: dict):
    license_info = ctx["license_info"]
    is_pro       = ctx["is_pro"]
    alpha_level  = ctx["alpha_level"]
    ai_enabled   = ctx["ai_enabled"]
    api_key      = ctx["anthropic_api_key"]
    ai_provider  = ctx["ai_provider"]

    st.markdown('<p class="rs-section-title">📊 ANOVA & Post-hoc Tests</p>',
                unsafe_allow_html=True)
    st.markdown(
        '<p class="rs-section-sub">One-way ANOVA, effect size η². '
        'Post-hoc Tukey/Bonferroni, Kruskal-Wallis, dan AI tersedia di Pro.</p>',
        unsafe_allow_html=True,
    )

    # Tidak ada hard-stop — modul berjalan untuk semua user

    df = require_data()
    if df is None:
        st.stop()
    cols = require_cols(df)
    if cols is None:
        st.stop()

    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
    if not cat_cols:
        st.error("❌ Tidak ditemukan kolom kategorik. Pastikan ada variabel kelompok.")
        st.stop()

    col_a, col_b = st.columns(2)
    with col_a:
        cat_col = st.selectbox("Variabel Kelompok:", cat_cols)
    with col_b:
        num_col = st.selectbox("Variabel Numerik (Y):", cols)

    unique_groups = df[cat_col].dropna().unique()
    if len(unique_groups) < 2:
        st.warning("⚠️ Diperlukan minimal 2 kelompok.")
        st.stop()

    groups = {
        str(g): df[df[cat_col] == g][num_col].dropna().values
        for g in unique_groups
    }
    groups = {k: v for k, v in groups.items() if len(v) >= 2}

    if len(groups) < 2:
        st.warning("⚠️ Setiap kelompok harus memiliki minimal 2 observasi.")
        st.stop()

    # ── Tabel Deskriptif per Kelompok ──────────────────────────────────────
    st.markdown("#### Statistik Deskriptif per Kelompok")
    desc_rows = []
    for gname, garr in groups.items():
        desc_rows.append({
            "Kelompok": gname, "N": len(garr),
            "Mean": round(float(garr.mean()), 4),
            "SD":   round(float(garr.std()), 4),
            "Min":  round(float(garr.min()), 4),
            "Max":  round(float(garr.max()), 4),
        })
    desc_df = pd.DataFrame(desc_rows)
    st.dataframe(desc_df, use_container_width=True, hide_index=True)

    # ── Visualisasi ─────────────────────────────────────────────────────────
    col_v1, col_v2 = st.columns(2)
    with col_v1:
        fig_box = px.box(
            df, x=cat_col, y=num_col, color=cat_col,
            title=f"Boxplot: {num_col} per {cat_col}",
            template="plotly_white"
        )
        fig_box.update_layout(height=380, showlegend=False,
                               margin=dict(l=20, r=20, t=50, b=30))
        st.plotly_chart(fig_box, use_container_width=True)
    with col_v2:
        fig_bar = px.bar(
            desc_df, x="Kelompok", y="Mean", error_y="SD",
            color="Kelompok",
            title=f"Mean ± SD: {num_col}",
            template="plotly_white"
        )
        fig_bar.update_layout(height=380, showlegend=False,
                               margin=dict(l=20, r=20, t=50, b=30))
        st.plotly_chart(fig_bar, use_container_width=True)

    # ── One-Way ANOVA ────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### One-Way ANOVA")
    f_stat, p_anova = stats.f_oneway(*groups.values())

    all_data   = np.concatenate(list(groups.values()))
    grand_mean = all_data.mean()
    ss_between = sum(len(g) * (g.mean() - grand_mean) ** 2 for g in groups.values())
    ss_total   = sum((x - grand_mean) ** 2 for g in groups.values() for x in g)
    eta_sq     = ss_between / ss_total if ss_total > 0 else 0

    render_effect_size_card("eta2", eta_sq)

    m1, m2, m3 = st.columns(3)
    sig_label = "✅ Signifikan" if p_anova < alpha_level else "❌ Tidak Signifikan"
    col_sig   = "#3b6d11" if p_anova < alpha_level else "#a32d2d"
    for col_, lbl, val, sub in zip(
        [m1, m2, m3],
        ["F-Statistik", "p-value", "η² (Effect Size)"],
        [round(f_stat, 4), round(p_anova, 4), round(eta_sq, 4)],
        [sig_label, "", "kecil<0.06 | sedang<0.14 | besar≥0.14"],
    ):
        col_.markdown(
            f'<div class="rs-metric"><div class="rs-metric-label">{lbl}</div>'
            f'<div class="rs-metric-value">{val}</div>'
            f'<div class="rs-metric-sub" style="color:{col_sig}">{sub}</div></div>',
            unsafe_allow_html=True,
        )

    eta_interp = (
        "besar (η² ≥ 0.14)" if eta_sq >= 0.14 else
        "sedang (η² ≥ 0.06)" if eta_sq >= 0.06 else
        "kecil (η² < 0.06)"
    )
    st.markdown(
        f'<div class="rs-narasi">💬 F({len(groups)-1}, {len(all_data)-len(groups)}) = {f_stat:.4f}, '
        f'p = {p_anova:.4f} — <span style="color:{col_sig}; font-weight:600">{sig_label}</span> '
        f'pada α = {alpha_level}. Effect size η² = {eta_sq:.4f} ({eta_interp}).</div>',
        unsafe_allow_html=True,
    )

    # Simpan hasil ke session_state (semua tier, karena ekspor ditangani export.py)
    anova_result_base = {
        "group_stats": desc_df,
        "anova_table": pd.DataFrame([{
            "F-statistik": round(f_stat, 4),
            "p-value":     round(p_anova, 4),
            "η² (Eta²)":   round(eta_sq, 4),
            "Signifikan":  "Ya ✓" if p_anova < alpha_level else "Tidak ✗",
        }]),
        "eta_squared": float(eta_sq),
        "f_stat":      float(f_stat),
        "p_value":     float(p_anova),
        "cat_col":     cat_col,
        "num_col":     num_col,
        "groups":      {k: v.tolist() for k, v in groups.items()},
    }

    # ── Export Excel (tersedia untuk semua tier) ──────────────────────────────
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        desc_df.to_excel(writer, sheet_name="Deskriptif_Kelompok", index=False)
        pd.DataFrame([{
            "F-stat": round(f_stat, 4), "p-ANOVA": round(p_anova, 4),
            "eta_sq": round(eta_sq, 4),
        }]).to_excel(writer, sheet_name="ANOVA_Summary", index=False)
    buf.seek(0)
    st.download_button(
        "⬇️ Export ke Excel (.xlsx)", data=buf,
        file_name=f"ANOVA_{num_col}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # ── Fitur Pro ─────────────────────────────────────────────────────────────
    st.markdown("---")
    if not is_pro:
        st.info(
            "🔒 **Fitur Pro:** Post-hoc Tukey HSD / Bonferroni, Kruskal-Wallis "
            "(uji non-parametrik), dan interpretasi AI — tersedia di **Paket Akademisi Pro**.\n\n"
            "👉 [Dapatkan akses Pro](https://lynk.id/ruangstatistika)"
        )
        st.session_state["anova_result"] = anova_result_base
        return

    # ── PRO ONLY: Post-hoc ────────────────────────────────────────────────────
    posthoc_df = None
    if p_anova < alpha_level:
        st.markdown("#### Post-hoc Test")
        st.radio("Metode Post-hoc:", ["Tukey HSD", "Bonferroni"], horizontal=True,
                 key="posthoc_method")
        posthoc_df = _tukey_hsd(groups, alpha=alpha_level)
        st.dataframe(posthoc_df, use_container_width=True, hide_index=True)
        anova_result_base["posthoc_table"] = posthoc_df
    else:
        st.info("ℹ️ ANOVA tidak signifikan — post-hoc test tidak diperlukan.")

    # ── PRO ONLY: Kruskal-Wallis ──────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### Kruskal-Wallis (Non-parametrik Alternatif)")
    kw_stat, kw_p = stats.kruskal(*groups.values())

    anova_result_base["kw_stat"] = round(float(kw_stat), 4)
    anova_result_base["kw_p"]    = round(float(kw_p), 4)
    kw_row = pd.DataFrame([{
        "H-statistik":  round(float(kw_stat), 4),
        "p-value (KW)": round(float(kw_p), 4),
        "Signifikan":   "Ya ✓" if kw_p < alpha_level else "Tidak ✗",
    }])
    anova_result_base["anova_table"] = pd.concat(
        [anova_result_base["anova_table"], kw_row], ignore_index=True
    )

    kw_sig = kw_p < alpha_level
    kw_col = "#3b6d11" if kw_sig else "#a32d2d"
    kw_lbl = "✅ Signifikan" if kw_sig else "❌ Tidak Signifikan"
    st.markdown(
        f'<div class="rs-narasi">📊 <b>Kruskal-Wallis H:</b> H = {kw_stat:.4f}, '
        f'p = {kw_p:.4f} — <span style="color:{kw_col}; font-weight:600">{kw_lbl}</span>.</div>',
        unsafe_allow_html=True,
    )

    # Simpan session_state lengkap (Pro)
    st.session_state["anova_result"] = anova_result_base

    # Export Excel Pro (dengan KW & post-hoc)
    buf2 = io.BytesIO()
    with pd.ExcelWriter(buf2, engine="openpyxl") as writer:
        desc_df.to_excel(writer, sheet_name="Deskriptif_Kelompok", index=False)
        anova_result_base["anova_table"].to_excel(writer, sheet_name="ANOVA_KW_Summary", index=False)
        if posthoc_df is not None:
            posthoc_df.to_excel(writer, sheet_name="Post_Hoc", index=False)
    buf2.seek(0)
    st.download_button(
        "⬇️ Export Lengkap ke Excel (.xlsx) — Pro", data=buf2,
        file_name=f"ANOVA_Pro_{num_col}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="anova_pro_export",
    )

    # ── PRO ONLY: AI ──────────────────────────────────────────────────────────
    if ai_enabled:
        if st.button("🤖 Interpretasi ANOVA dengan AI", key="ai_anova_btn"):
            ph_str = posthoc_df.to_string(index=False) if posthoc_df is not None else "N/A"
            prompt = f"""
Hasil One-Way ANOVA untuk variabel {num_col} berdasarkan kelompok {cat_col}:

DESKRIPTIF: {desc_df.to_string(index=False)}

ANOVA: F = {f_stat:.4f}, p = {p_anova:.4f}, η² = {eta_sq:.4f}
Kruskal-Wallis: H = {kw_stat:.4f}, p = {kw_p:.4f}
Post-hoc: {ph_str}

Berikan interpretasi dalam Bahasa Indonesia mencakup:
1. Apakah ada perbedaan signifikan antar kelompok?
2. Kelompok mana yang berbeda secara signifikan (jika post-hoc tersedia)?
3. Besaran dan makna effect size η²
4. Perbandingan ANOVA vs Kruskal-Wallis — interpretasi mana yang lebih tepat?
Format: 3 paragraf akademis.
"""
            with st.spinner("🤖 AI menganalisis..."):
                ai_anova = call_ai_api(prompt, api_key=api_key, provider=ai_provider)
            if "ai_cache" not in st.session_state:
                st.session_state.ai_cache = {}
            st.session_state.ai_cache["anova"] = ai_anova

        if ss_get("ai_cache", {}).get("anova"):
            st.markdown(
                f'<div class="rs-ai-narasi">'
                f'<span class="rs-ai-badge">✨ AI — {ai_provider.split("(")[0].strip()}</span><br/>'
                f'{ss_get("ai_cache", {})["anova"].replace(chr(10), "<br/>")}'
                f"</div>",
                unsafe_allow_html=True,
            )
