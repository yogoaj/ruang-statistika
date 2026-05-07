"""
modules/kelompok.py — Analisis Kelompok (Free)
Ruang Statistika v4.0
"""

import streamlit as st
import plotly.express as px
from scipy import stats

from utils.stats_helpers import require_data, require_cols, ss_get
from utils.ai_helpers import call_ai_api


def render(ctx: dict):
    alpha_level = ctx["alpha_level"]
    ai_enabled  = ctx["ai_enabled"]
    api_key     = ctx["anthropic_api_key"]
    ai_provider = ctx["ai_provider"]

    st.markdown('<p class="rs-section-title">📂 Analisis Kelompok</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="rs-section-sub">Bandingkan nilai antar kelompok menggunakan variabel kategorik.</p>',
        unsafe_allow_html=True,
    )

    df = require_data()
    if df is None:
        st.stop()
    cols = require_cols(df)
    if cols is None:
        st.stop()

    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
    if not cat_cols:
        st.error(
            "❌ Tidak ditemukan kolom kategorik (teks) pada dataset. "
            "Pastikan ada kolom seperti 'Jenis Kelamin', 'Jurusan', dll."
        )
        st.stop()

    ca, cb = st.columns(2)
    with ca:
        cat = st.selectbox("Variabel Kelompok (Kategorik):", cat_cols)
    with cb:
        num = st.selectbox("Variabel Numerik:", cols)

    res_group = (
        df.groupby(cat)[num]
        .agg(N="count", Mean="mean", Std="std", Min="min", Max="max")
        .round(3)
        .reset_index()
    )
    res_group.columns = [cat, "N", "Mean", "Std Dev", "Min", "Max"]

    st.markdown(f"#### Ringkasan **{num}** berdasarkan **{cat}**")
    st.dataframe(res_group, use_container_width=True, hide_index=True)

    best_group  = res_group.loc[res_group["Mean"].idxmax(), cat]
    worst_group = res_group.loc[res_group["Mean"].idxmin(), cat]
    st.markdown(
        f'<div class="rs-narasi">💬 Kelompok <b>{best_group}</b> memiliki rata-rata '
        f"<b>{num}</b> tertinggi, sedangkan <b>{worst_group}</b> memiliki rata-rata terendah. "
        f"Perbedaan antar kelompok dapat ditelusuri lebih lanjut menggunakan uji ANOVA atau Kruskal-Wallis.</div>",
        unsafe_allow_html=True,
    )

    st.markdown("---")
    col_a, col_b = st.columns(2)
    with col_a:
        fig_box = px.box(
            df, x=cat, y=num, color=cat,
            title=f"Boxplot: {num} per {cat}", template="plotly_white"
        )
        fig_box.update_layout(height=380, margin=dict(l=20, r=20, t=50, b=30),
                               showlegend=False)
        st.plotly_chart(fig_box, use_container_width=True)
    with col_b:
        fig_bar = px.bar(
            res_group, x=cat, y="Mean", error_y="Std Dev", color=cat,
            title=f"Bar Chart Mean ± SD: {num}", template="plotly_white"
        )
        fig_bar.update_layout(height=380, margin=dict(l=20, r=20, t=50, b=30),
                               showlegend=False)
        st.plotly_chart(fig_bar, use_container_width=True)

    # Kumpulkan group_data untuk export (dibuat di sini, disimpan bersama dict di bawah)
    group_data_export = {
        str(g): df[df[cat] == g][num].dropna().tolist()
        for g in df[cat].dropna().unique()
    }

    groups = [grp[num].dropna().values for _, grp in df.groupby(cat)]
    f_stat, p_anova, sig = None, None, False
    if len(groups) >= 2 and all(len(g) >= 2 for g in groups):
        st.markdown("---")
        st.markdown("#### Uji One-Way ANOVA")
        f_stat, p_anova = stats.f_oneway(*groups)
        sig = p_anova < alpha_level
        st.markdown(
            f'<div class="rs-narasi">💬 Hasil uji One-Way ANOVA: F = {f_stat:.4f}, '
            f"p = {p_anova:.4f}. "
            f'{"Terdapat perbedaan yang <b>signifikan</b>" if sig else "Tidak terdapat perbedaan yang signifikan"} '
            f"rata-rata <b>{num}</b> antar kelompok <b>{cat}</b> (α = {alpha_level}).</div>",
            unsafe_allow_html=True,
        )

    # ── Simpan hasil ke session_state untuk export ──────────────────────────
    if "ai_cache" not in st.session_state:
        st.session_state.ai_cache = {}

    kelompok_data = {
        "cat":         cat,
        "num":         num,
        "group_stats": res_group,
        "best_group":  best_group,
        "worst_group": worst_group,
        "f_stat":      float(f_stat) if f_stat is not None else None,
        "p_value":     float(p_anova) if p_anova is not None else None,
        "signifikan":  sig,
        "alpha":       alpha_level,
        "group_data":  group_data_export,
    }
    st.session_state["kelompok_result"] = kelompok_data

    # ── AI Interpretasi ──────────────────────────────────────────────────────
    if ai_enabled:
        if st.button("🤖 Interpretasi Analisis Kelompok dengan AI", key="ai_kelompok_btn"):
            prompt = f"""
Berikut hasil analisis kelompok variabel penelitian:

VARIABEL KELOMPOK : {cat}
VARIABEL NUMERIK  : {num}
ALPHA             : {alpha_level}

STATISTIK PER KELOMPOK:
{res_group.to_string(index=False)}

UJI ONE-WAY ANOVA:
F-statistik = {f"{f_stat:.4f}" if f_stat is not None else 'N/A'}
p-value     = {f"{p_anova:.4f}" if p_anova is not None else 'N/A'}
Kesimpulan  = {"Signifikan — ada perbedaan nyata antar kelompok" if sig else "Tidak signifikan — tidak ada perbedaan nyata antar kelompok"}

Kelompok tertinggi: {best_group}
Kelompok terendah: {worst_group}

Berikan interpretasi mendalam dalam Bahasa Indonesia mencakup:
1. Perbandingan antar kelompok — siapa yang unggul dan seberapa jauh perbedaannya?
2. Makna hasil ANOVA — apakah perbedaan ini signifikan secara statistik dan praktis?
3. Implikasi penelitian — apa arti temuan ini bagi subjek/populasi yang diteliti?
4. Rekomendasi lanjutan — apakah perlu uji post-hoc (Tukey/Bonferroni) untuk mengidentifikasi
   pasangan kelompok yang berbeda secara signifikan?
Tulis dalam 3 paragraf, gaya laporan akademis yang lugas.
"""
            with st.spinner("🤖 AI sedang menganalisis perbedaan kelompok..."):
                ai_kelompok = call_ai_api(prompt, api_key=api_key, provider=ai_provider)
            st.session_state.ai_cache["kelompok"] = ai_kelompok

        if ss_get("ai_cache", {}).get("kelompok"):
            st.markdown(
                f'<div class="rs-ai-narasi">'
                f'<span class="rs-ai-badge">✨ AI — {ai_provider.split("(")[0].strip()}</span><br/>'
                f'{ss_get("ai_cache", {})["kelompok"].replace(chr(10), "<br/>")}'
                f"</div>",
                unsafe_allow_html=True,
            )
    else:
        st.caption("💡 Aktifkan API Key di sidebar untuk interpretasi AI.")
