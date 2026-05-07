"""
modules/validitas.py — Validitas & Reliabilitas (Free) + Alpha-if-Deleted (Pro)
Ruang Statistika v4.1

Perubahan v4.1:
- Tambah Tab 3: "Alpha jika Item Dihapus" (Pro)
  • Item-total correlation (corrected & uncorrected)
  • Alpha jika item dihapus (α-if-deleted)
  • Inter-item correlation matrix
  • Mean inter-item correlation
  • Tabel flag otomatis: item yang menarik alpha ke bawah
  • AI interpretasi item-level
"""

import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from utils.stats_helpers import (
    require_data, require_cols,
    pearson_validity, calc_cronbach,
    narrate_validity, narrate_alpha, ss_get,
)
from utils.plot_helpers import plotly_validity_bar, plotly_cronbach_gauge
from utils.ai_helpers import (
    ai_interpret_validity_reliability,
    ai_interpret_validity_bar,
    ai_interpret_cronbach_gauge,
    ai_interpret_alpha_if_deleted,      # ← BARU (ditambahkan di ai_helpers.py)
)
from utils.auth import require_pro


# ─────────────────────────────────────────────────────────────────────────────
# Helper: hitung item-total statistics & alpha-if-deleted
# ─────────────────────────────────────────────────────────────────────────────

def _item_total_statistics(df: pd.DataFrame, cols: list) -> pd.DataFrame:
    """
    Hitung statistik per item (baris = item/butir):
    - Scale Mean if Item Deleted
    - Scale Variance if Item Deleted
    - Corrected Item-Total Correlation (CITC)
    - Squared Multiple Correlation (SMC / R²)
    - Alpha if Item Deleted

    Mengikuti konvensi SPSS Reliability Analysis — Item Statistics.
    Referensi: Nunnally (1978), Field (2018 — Discovering Statistics).
    """
    subset = df[cols].apply(pd.to_numeric, errors="coerce").dropna()
    k = subset.shape[1]
    rows = []

    for c in cols:
        rest_cols = [x for x in cols if x != c]
        rest      = subset[rest_cols]
        rest_sum  = rest.sum(axis=1)          # skala tanpa item c
        total_sum = subset.sum(axis=1)        # skala penuh

        # Scale Mean / Variance if deleted (skala = jumlah skor semua item lain)
        scale_mean_del = float(rest_sum.mean())
        scale_var_del  = float(rest_sum.var(ddof=1))

        # Corrected Item-Total Correlation (item vs rest)
        if rest_sum.std() == 0 or subset[c].std() == 0:
            citc = 0.0
        else:
            citc = float(np.corrcoef(subset[c], rest_sum)[0, 1])

        # Squared Multiple Correlation (R² item ~ semua item lain)
        try:
            from sklearn.linear_model import LinearRegression
            lr = LinearRegression()
            lr.fit(rest.values, subset[c].values)
            y_pred = lr.predict(rest.values)
            ss_res = np.sum((subset[c].values - y_pred) ** 2)
            ss_tot = np.sum((subset[c].values - subset[c].mean()) ** 2)
            smc = float(1 - ss_res / ss_tot) if ss_tot > 0 else 0.0
        except Exception:
            smc = float(np.corrcoef(subset[c], rest_sum)[0, 1] ** 2)

        # Alpha if item deleted — Cronbach's formula pada k-1 item
        if k >= 3:
            item_vars = rest.var(axis=0, ddof=1).sum()
            total_var = rest.sum(axis=1).var(ddof=1)
            if total_var > 0:
                k2 = k - 1
                alpha_del = float((k2 / (k2 - 1)) * (1 - item_vars / total_var))
            else:
                alpha_del = 0.0
        else:
            alpha_del = float("nan")

        rows.append({
            "Butir":                          c,
            "Mean Skala jika Dihapus":        round(scale_mean_del, 4),
            "Varians Skala jika Dihapus":     round(scale_var_del, 4),
            "Corrected Item-Total (CITC)":    round(citc, 4),
            "R² (Squared Multiple Corr.)":    round(smc, 4),
            "Alpha jika Item Dihapus (α-del)": round(alpha_del, 4),
        })

    return pd.DataFrame(rows)


def _inter_item_corr_matrix(df: pd.DataFrame, cols: list) -> pd.DataFrame:
    """Matriks korelasi antar item (inter-item correlation)."""
    subset = df[cols].apply(pd.to_numeric, errors="coerce").dropna()
    return subset.corr(method="pearson").round(4)


def _mean_inter_item_corr(iic: pd.DataFrame) -> float:
    """Rata-rata korelasi antar item (off-diagonal)."""
    n = len(iic)
    if n < 2:
        return float("nan")
    off_diag = iic.values[np.triu_indices(n, k=1)]
    return float(np.mean(off_diag))


def _flag_problematic_items(item_stats: pd.DataFrame, alpha_overall: float) -> pd.DataFrame:
    """
    Tandai item yang bermasalah:
    - CITC < 0.30 → item lemah (Nunnally, 1978)
    - α-del > α overall → item ini menarik alpha ke bawah (perlu revisi/hapus)
    """
    df = item_stats.copy()
    flags = []
    for _, row in df.iterrows():
        citc      = row["Corrected Item-Total (CITC)"]
        alpha_del = row["Alpha jika Item Dihapus (α-del)"]
        f = []
        if citc < 0.30:
            f.append("⚠️ CITC rendah (<0.30)")
        if not np.isnan(alpha_del) and alpha_del > alpha_overall + 0.005:
            f.append("🔺 Hapus meningkatkan α")
        flags.append("; ".join(f) if f else "✓ Baik")
    df["Status Item"] = flags
    return df


# ─────────────────────────────────────────────────────────────────────────────
# Plot helper: alpha-if-deleted bar chart
# ─────────────────────────────────────────────────────────────────────────────

def _plot_alpha_if_deleted(item_stats: pd.DataFrame, alpha_overall: float) -> go.Figure:
    BLUE = "#185FA5"
    RED  = "#A32D2D"
    GREEN = "#3B6D11"

    colors = []
    for _, row in item_stats.iterrows():
        a_del = row["Alpha jika Item Dihapus (α-del)"]
        if np.isnan(a_del):
            colors.append(BLUE)
        elif a_del > alpha_overall + 0.005:
            colors.append(RED)      # merah → menghapus item ini NAIKKAN alpha
        elif a_del < alpha_overall - 0.02:
            colors.append(GREEN)    # hijau → item sangat berkontribusi
        else:
            colors.append(BLUE)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=item_stats["Butir"],
        y=item_stats["Alpha jika Item Dihapus (α-del)"],
        marker_color=colors,
        text=item_stats["Alpha jika Item Dihapus (α-del)"].round(3),
        textposition="outside",
        name="α jika dihapus",
    ))
    fig.add_hline(
        y=alpha_overall, line_dash="dash", line_color="#E24B4A", line_width=2,
        annotation_text=f"α keseluruhan = {alpha_overall:.4f}",
        annotation_position="top left",
    )
    fig.update_layout(
        title="Alpha Cronbach jika Item Dihapus",
        xaxis_title="Butir / Item",
        yaxis_title="α jika Item Dihapus",
        yaxis=dict(range=[max(0, alpha_overall - 0.25), min(1.05, alpha_overall + 0.25)]),
        template="plotly_white",
        height=400,
        margin=dict(l=30, r=30, t=55, b=30),
        legend=dict(orientation="h", y=-0.15),
    )
    return fig


def _plot_citc_bar(item_stats: pd.DataFrame) -> go.Figure:
    BLUE = "#185FA5"
    RED  = "#A32D2D"
    threshold = 0.30

    colors = [RED if v < threshold else BLUE
              for v in item_stats["Corrected Item-Total (CITC)"]]

    fig = go.Figure(go.Bar(
        x=item_stats["Butir"],
        y=item_stats["Corrected Item-Total (CITC)"],
        marker_color=colors,
        text=item_stats["Corrected Item-Total (CITC)"].round(3),
        textposition="outside",
    ))
    fig.add_hline(
        y=threshold, line_dash="dash", line_color="#E24B4A",
        annotation_text="Threshold CITC = 0.30",
    )
    fig.update_layout(
        title="Corrected Item-Total Correlation (CITC) per Butir",
        xaxis_title="Butir", yaxis_title="CITC",
        template="plotly_white", height=380,
        margin=dict(l=30, r=30, t=55, b=30),
    )
    return fig


def _plot_iic_heatmap(iic: pd.DataFrame) -> go.Figure:
    fig = go.Figure(go.Heatmap(
        z=iic.values, x=iic.columns, y=iic.columns,
        colorscale="Blues",
        text=np.round(iic.values, 3),
        texttemplate="%{text}", textfont={"size": 9},
        zmin=-1, zmax=1,
        colorbar={"title": "r"},
    ))
    fig.update_layout(
        title="Inter-Item Correlation Matrix",
        template="plotly_white", height=max(350, len(iic) * 40 + 80),
        margin=dict(l=10, r=10, t=55, b=10),
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# render() — entry point dipanggil dari app.py
# ─────────────────────────────────────────────────────────────────────────────

def render(ctx: dict):
    r_tab       = ctx.get("r_tab") or ctx.get("r_tabel") or 0.30
    ai_enabled  = ctx["ai_enabled"]
    api_key     = ctx["anthropic_api_key"]
    ai_provider = ctx["ai_provider"]
    license_info = ctx["license_info"]
    is_pro      = ctx.get("is_pro", False)

    st.markdown('<p class="rs-section-title">✅ Validitas & Reliabilitas</p>',
                unsafe_allow_html=True)
    st.markdown(
        "<p class='rs-section-sub'>Uji Pearson Validity, Cronbach's Alpha, "
        "dan Item-Total Statistics (Alpha jika Item Dihapus).</p>",
        unsafe_allow_html=True,
    )

    df = require_data()
    if df is None:
        st.stop()
    cols = require_cols(df)
    if cols is None or len(cols) < 2:
        st.warning("⚠️ Pilih minimal 2 kolom numerik untuk uji ini.")
        st.stop()

    if "ai_cache" not in st.session_state:
        st.session_state.ai_cache = {}

    with st.spinner("Menghitung validitas dan reliabilitas..."):
        val_df       = pearson_validity(df, cols, r_tab)
        alpha_result = calc_cronbach(df, cols)

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab1, tab2, tab3 = st.tabs([
        "📊 Uji Validitas",
        "🔵 Cronbach's Alpha",
        f"🔬 Alpha jika Item Dihapus {'✨ Pro' if not is_pro else ''}",
    ])

    # =========================================================================
    # TAB 1 — Uji Validitas (Pearson)
    # =========================================================================
    with tab1:
        st.markdown("#### Uji Validitas (Pearson Correlation)")
        st.markdown(f"r-tabel yang digunakan: **{r_tab}** (dapat diubah di sidebar)")

        validity_bar_fig = plotly_validity_bar(val_df, r_tab)
        st.plotly_chart(validity_bar_fig, use_container_width=True)
        st.dataframe(val_df, use_container_width=True, hide_index=True)

        st.markdown(
            f'<div class="rs-narasi">💬 {narrate_validity(val_df, r_tab)}</div>',
            unsafe_allow_html=True,
        )

        if ai_enabled:
            if st.button("🤖 Interpretasi Grafik Validitas dengan AI", key="ai_val_bar_btn"):
                val_stats = {
                    "r_tabel":  r_tab,
                    "n_butir":  len(val_df),
                    "n_valid":  int(val_df["Status"].str.contains("Valid ✓").sum())
                                if "Status" in val_df.columns else None,
                    "butir":    val_df.to_dict(orient="records"),
                }
                with st.spinner("🤖 AI sedang membaca grafik validitas..."):
                    ai_vbar = ai_interpret_validity_bar(val_stats, api_key, ai_provider)
                st.session_state.ai_cache["validity_bar"] = ai_vbar

            if ss_get("ai_cache", {}).get("validity_bar"):
                st.markdown(
                    f'<div class="rs-ai-narasi">'
                    f'<span class="rs-ai-badge">✨ AI — {ai_provider.split("(")[0].strip()}</span><br/>'
                    f'{ss_get("ai_cache", {})["validity_bar"].replace(chr(10), "<br/>")}'
                    f"</div>",
                    unsafe_allow_html=True,
                )

            if val_df is not None and not val_df.empty and alpha_result is not None:
                if st.button("🤖 Interpretasi Validitas & Reliabilitas (Lengkap) dengan AI",
                             key="ai_val_btn"):
                    with st.spinner("🤖 AI sedang menganalisis instrumen penelitian..."):
                        ai_text = ai_interpret_validity_reliability(
                            val_df, alpha_result, r_tab, api_key, ai_provider
                        )
                    st.session_state.ai_cache["validity"] = ai_text

                if ss_get("ai_cache", {}).get("validity"):
                    st.markdown(
                        f'<div class="rs-ai-narasi">'
                        f'<span class="rs-ai-badge">✨ AI — {ai_provider.split("(")[0].strip()}</span><br/>'
                        f'{ss_get("ai_cache", {})["validity"].replace(chr(10), "<br/>")}'
                        f"</div>",
                        unsafe_allow_html=True,
                    )
        else:
            st.caption("💡 Aktifkan API Key di sidebar untuk interpretasi AI.")

    # =========================================================================
    # TAB 2 — Uji Reliabilitas (Cronbach's Alpha)
    # =========================================================================
    with tab2:
        st.markdown("#### Uji Reliabilitas (Cronbach's Alpha)")
        cronbach_gauge_fig = None

        if alpha_result is not None:
            col1, col2 = st.columns([1, 3])
            with col1:
                color      = "#3B6D11" if alpha_result >= 0.7 else "#A32D2D"
                badge_cls  = "badge-reliable" if alpha_result >= 0.7 else "badge-unreliable"
                status_lbl = "RELIABEL ✓" if alpha_result >= 0.7 else "TIDAK RELIABEL ✗"
                st.markdown(f"""
                <div style='text-align:center; background:#f0f6ff; border:1px solid #d0e4f7;
                            border-radius:12px; padding:1.5rem;'>
                    <div style='font-size:0.75rem; color:#5f8ab5; text-transform:uppercase;
                                letter-spacing:0.06em;'>Cronbach's Alpha</div>
                    <div style='font-size:2.5rem; font-weight:700; color:{color}; margin:8px 0;'>
                        {alpha_result}</div>
                    <span class='{badge_cls}'>{status_lbl}</span>
                </div>""", unsafe_allow_html=True)
            with col2:
                cronbach_gauge_fig = plotly_cronbach_gauge(alpha_result)
                st.plotly_chart(cronbach_gauge_fig, use_container_width=True)

            st.markdown(
                f'<div class="rs-narasi">💬 {narrate_alpha(alpha_result)}</div>',
                unsafe_allow_html=True,
            )

            if ai_enabled:
                if st.button("🤖 Interpretasi Cronbach's Alpha dengan AI", key="ai_cronbach_btn"):
                    if alpha_result >= 0.9:   level = "Sangat Tinggi"
                    elif alpha_result >= 0.8: level = "Tinggi"
                    elif alpha_result >= 0.7: level = "Cukup / Dapat Diterima"
                    elif alpha_result >= 0.6: level = "Diragukan"
                    else:                      level = "Tidak Dapat Diterima"

                    cronbach_stats = {
                        "alpha":    round(float(alpha_result), 4),
                        "n_butir":  len(cols),
                        "n_sampel": len(df),
                        "reliabel": alpha_result >= 0.7,
                        "level":    level,
                        "acuan":    "Ghozali (2018): α ≥ 0.70 = reliabel",
                    }
                    with st.spinner("🤖 AI sedang menginterpretasi reliabilitas instrumen..."):
                        ai_cron = ai_interpret_cronbach_gauge(cronbach_stats, api_key, ai_provider)
                    st.session_state.ai_cache["cronbach"] = ai_cron

                if ss_get("ai_cache", {}).get("cronbach"):
                    st.markdown(
                        f'<div class="rs-ai-narasi">'
                        f'<span class="rs-ai-badge">✨ AI — {ai_provider.split("(")[0].strip()}</span><br/>'
                        f'{ss_get("ai_cache", {})["cronbach"].replace(chr(10), "<br/>")}'
                        f"</div>",
                        unsafe_allow_html=True,
                    )
            else:
                st.caption("💡 Aktifkan API Key di sidebar untuk interpretasi AI.")

    # =========================================================================
    # TAB 3 — Alpha jika Item Dihapus (Pro)
    # =========================================================================
    with tab3:
        # ── Guard Pro ────────────────────────────────────────────────────────
        if not require_pro(license_info, "Alpha jika Item Dihapus"):
            st.stop()

        st.markdown("#### 🔬 Item-Total Statistics & Alpha jika Item Dihapus")
        st.markdown(
            "<p class='rs-section-sub'>"
            "Standar wajib analisis kuesioner — identifikasi item yang menarik alpha ke bawah "
            "(Nunnally, 1978; Field, 2018).</p>",
            unsafe_allow_html=True,
        )

        if alpha_result is None:
            st.error("❌ Tidak dapat menghitung alpha — periksa data Anda.")
            st.stop()

        with st.spinner("Menghitung item-total statistics..."):
            item_stats_raw = _item_total_statistics(df, cols)
            item_stats     = _flag_problematic_items(item_stats_raw, alpha_result)
            iic            = _inter_item_corr_matrix(df, cols)
            mean_iic       = _mean_inter_item_corr(iic)

        # ── Ringkasan metrik ───────────────────────────────────────────────
        n_bad_citc  = (item_stats["Corrected Item-Total (CITC)"] < 0.30).sum()
        n_raise_alpha = (
            item_stats["Alpha jika Item Dihapus (α-del)"] > alpha_result + 0.005
        ).sum()
        n_total = len(cols)

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.markdown(f"""<div class="rs-metric">
                <div class="rs-metric-label">α Keseluruhan</div>
                <div class="rs-metric-value">{alpha_result}</div>
                <div class="rs-metric-sub">Cronbach's Alpha</div></div>""",
                unsafe_allow_html=True)
        with m2:
            st.markdown(f"""<div class="rs-metric">
                <div class="rs-metric-label">Total Item</div>
                <div class="rs-metric-value">{n_total}</div>
                <div class="rs-metric-sub">Butir dianalisis</div></div>""",
                unsafe_allow_html=True)
        with m3:
            color3 = "#A32D2D" if n_bad_citc > 0 else "#3B6D11"
            st.markdown(f"""<div class="rs-metric">
                <div class="rs-metric-label">CITC &lt; 0.30</div>
                <div class="rs-metric-value" style="color:{color3};">{n_bad_citc}</div>
                <div class="rs-metric-sub">Item CITC rendah</div></div>""",
                unsafe_allow_html=True)
        with m4:
            color4 = "#A32D2D" if n_raise_alpha > 0 else "#3B6D11"
            st.markdown(f"""<div class="rs-metric">
                <div class="rs-metric-label">Naikan α jika Hapus</div>
                <div class="rs-metric-value" style="color:{color4};">{n_raise_alpha}</div>
                <div class="rs-metric-sub">Item kandidat hapus</div></div>""",
                unsafe_allow_html=True)

        st.markdown("<br/>", unsafe_allow_html=True)

        # ── Plot 1: Alpha-if-deleted bar ───────────────────────────────────
        st.markdown("##### 📊 Visualisasi Alpha jika Item Dihapus")
        st.plotly_chart(
            _plot_alpha_if_deleted(item_stats, alpha_result),
            use_container_width=True,
        )
        st.caption(
            "🔴 Merah = menghapus item ini akan **meningkatkan** α (kandidat hapus) · "
            "🟢 Hijau = item sangat berkontribusi pada reliabilitas · "
            "🔵 Biru = item normal"
        )

        # ── Plot 2: CITC bar ───────────────────────────────────────────────
        st.markdown("##### 📊 Corrected Item-Total Correlation (CITC)")
        st.plotly_chart(_plot_citc_bar(item_stats), use_container_width=True)

        # ── Tabel item-total statistics ────────────────────────────────────
        st.markdown("##### 📋 Tabel Item-Total Statistics")

        # Styling: tandai baris bermasalah dengan warna
        def _style_row(row):
            styles = [""] * len(row)
            idx_citc = list(row.index).index("Corrected Item-Total (CITC)")
            idx_adel = list(row.index).index("Alpha jika Item Dihapus (α-del)")
            idx_flag = list(row.index).index("Status Item")
            if row["Corrected Item-Total (CITC)"] < 0.30:
                styles[idx_citc] = "background-color:#fcebeb; color:#a32d2d; font-weight:600"
            if (not np.isnan(row["Alpha jika Item Dihapus (α-del)"])
                    and row["Alpha jika Item Dihapus (α-del)"] > alpha_result + 0.005):
                styles[idx_adel] = "background-color:#fcebeb; color:#a32d2d; font-weight:600"
            if "⚠️" in str(row["Status Item"]) or "🔺" in str(row["Status Item"]):
                styles[idx_flag] = "background-color:#fff8e1; color:#7a5c00;"
            return styles

        styled = item_stats.style.apply(_style_row, axis=1)
        st.dataframe(styled, use_container_width=True, hide_index=True)

        # ── Narasi otomatis ────────────────────────────────────────────────
        problem_items = item_stats[
            item_stats["Status Item"].str.contains("⚠️|🔺", regex=True)
        ]["Butir"].tolist()

        if n_raise_alpha == 0 and n_bad_citc == 0:
            narasi = (
                f"✅ Semua {n_total} item menunjukkan kualitas psikometrik yang baik. "
                f"Tidak ada item dengan CITC < 0.30 dan tidak ada item yang jika dihapus "
                f"akan meningkatkan Cronbach's Alpha (α = {alpha_result}). "
                f"Instrumen dinyatakan stabil."
            )
        else:
            parts = []
            if n_raise_alpha > 0:
                cands = item_stats[
                    item_stats["Alpha jika Item Dihapus (α-del)"] > alpha_result + 0.005
                ]["Butir"].tolist()
                max_gain = item_stats[
                    item_stats["Alpha jika Item Dihapus (α-del)"] > alpha_result + 0.005
                ]["Alpha jika Item Dihapus (α-del)"].max()
                parts.append(
                    f"**{n_raise_alpha}** item jika dihapus akan **meningkatkan** α "
                    f"(tertinggi hingga {max_gain:.4f}): {', '.join(cands)}."
                )
            if n_bad_citc > 0:
                low_citc = item_stats[
                    item_stats["Corrected Item-Total (CITC)"] < 0.30
                ]["Butir"].tolist()
                parts.append(
                    f"**{n_bad_citc}** item memiliki CITC < 0.30 (item lemah): "
                    f"{', '.join(low_citc)}."
                )
            narasi = " ".join(parts) + (
                " Pertimbangkan revisi atau penghapusan item-item tersebut "
                "untuk meningkatkan konsistensi internal instrumen."
            )

        st.markdown(
            f'<div class="rs-narasi">📊 {narasi}</div>',
            unsafe_allow_html=True,
        )

        # ── Inter-item correlation matrix ──────────────────────────────────
        st.markdown("---")
        st.markdown("##### 🔗 Inter-Item Correlation Matrix")
        st.caption(
            f"Rata-rata korelasi antar item (mean inter-item r) = **{mean_iic:.4f}**. "
            "Rentang ideal: 0.15 – 0.50 (Clark & Watson, 1995)."
        )
        if len(cols) <= 20:
            st.plotly_chart(_plot_iic_heatmap(iic), use_container_width=True)
        else:
            st.info(
                f"ℹ️ Terlalu banyak item ({len(cols)}) untuk heatmap. "
                "Menampilkan tabel saja."
            )
        with st.expander("📋 Tampilkan Tabel Inter-Item Correlation"):
            st.dataframe(iic.style.format("{:.4f}"), use_container_width=True)

        # ── Rekomendasi revisi ─────────────────────────────────────────────
        if problem_items:
            st.markdown("---")
            st.markdown("##### 🛠️ Rekomendasi Revisi Item")
            rec_rows = []
            for _, row in item_stats.iterrows():
                if row["Butir"] in problem_items:
                    recs = []
                    citc_v = row["Corrected Item-Total (CITC)"]
                    adel_v = row["Alpha jika Item Dihapus (α-del)"]
                    if citc_v < 0.30:
                        recs.append(f"CITC = {citc_v:.4f} → tinjau redaksi item")
                    if not np.isnan(adel_v) and adel_v > alpha_result + 0.005:
                        gain = adel_v - alpha_result
                        recs.append(
                            f"α naik {gain:+.4f} → pertimbangkan penghapusan"
                        )
                    rec_rows.append({
                        "Butir":     row["Butir"],
                        "CITC":      citc_v,
                        "α-del":     adel_v,
                        "Masalah":   row["Status Item"],
                        "Saran":     " | ".join(recs),
                    })
            st.dataframe(pd.DataFrame(rec_rows), use_container_width=True, hide_index=True)

        # ── AI Interpretasi ────────────────────────────────────────────────
        if ai_enabled:
            st.markdown("---")
            if st.button(
                "🤖 Interpretasi Item-Total Statistics dengan AI",
                key="ai_alpha_del_btn",
            ):
                payload = {
                    "alpha_overall":    round(float(alpha_result), 4),
                    "n_items":          n_total,
                    "n_sampel":         len(df),
                    "n_bad_citc":       int(n_bad_citc),
                    "n_raise_alpha":    int(n_raise_alpha),
                    "mean_iic":         round(float(mean_iic), 4),
                    "item_stats":       item_stats.to_dict(orient="records"),
                    "problem_items":    problem_items,
                }
                with st.spinner("🤖 AI sedang menganalisis item-level reliability..."):
                    ai_aidel = ai_interpret_alpha_if_deleted(payload, api_key, ai_provider)
                st.session_state.ai_cache["alpha_if_deleted"] = ai_aidel

            if ss_get("ai_cache", {}).get("alpha_if_deleted"):
                st.markdown(
                    f'<div class="rs-ai-narasi">'
                    f'<span class="rs-ai-badge">✨ AI — {ai_provider.split("(")[0].strip()}</span><br/>'
                    f'{ss_get("ai_cache", {})["alpha_if_deleted"].replace(chr(10), "<br/>")}'
                    f"</div>",
                    unsafe_allow_html=True,
                )
        else:
            st.caption("💡 Aktifkan API Key di sidebar untuk interpretasi AI item-level.")

        # ── Simpan ke session state untuk export ───────────────────────────
        st.session_state["item_total_stats"] = item_stats
        st.session_state["inter_item_corr"]  = iic
        st.session_state["mean_iic"]         = mean_iic

    # ── Simpan figure ke session state untuk export ───────────────────────────
    validity_bar_fig = plotly_validity_bar(val_df, r_tab)
    sess_figs = {"validity_bar": validity_bar_fig}
    if alpha_result is not None:
        sess_figs["cronbach_gauge"] = plotly_cronbach_gauge(alpha_result)
    st.session_state["validitas_figs"]  = sess_figs
    st.session_state["validitas_alpha"] = alpha_result
