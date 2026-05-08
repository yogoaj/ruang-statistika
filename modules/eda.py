"""
modules/eda.py — Visualisasi Eksplorasi Data / EDA (Free)
Ruang Statistika v4.2

Tab 1 — Ringkasan Data          : profil kolom, tipe data, distribusi cepat
Tab 2 — Distribusi & Violin     : histogram overlay, violin + strip plot per kolom
Tab 3 — Pair Plot               : scatter matrix otomatis (numerik × numerik)
Tab 4 — Kategorik & Mosaic      : bar chart, grouped bar, mosaic plot 2 var kategorik
Tab 5 — Korelasi & Paralel      : heatmap Pearson + parallel coordinates
Tab 6 — Missing Value           : heatmap missing, pola, bar missing per kolom

Semua chart: Plotly — zero dependency baru.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import plotly.figure_factory as ff
import streamlit as st
from scipy import stats as scipy_stats

from utils.stats_helpers import require_data, ss_get

# ── Palet ────────────────────────────────────────────────────────────────────
BLUE   = "#185FA5"
GREEN  = "#3B6D11"
RED    = "#A32D2D"
RED2   = "#E24B4A"
PURPLE = "#6B21A8"
PALETTE = px.colors.qualitative.Set2


# ═══════════════════════════════════════════════════════════════════════════════
# Shared helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _narasi(text: str, color: str = BLUE):
    st.markdown(
        f'<div class="rs-narasi" style="border-left-color:{color};">{text}</div>',
        unsafe_allow_html=True,
    )


def _col_select(label: str, options: list, key: str, default_idx: int = 0):
    return st.selectbox(label, options, index=min(default_idx, len(options) - 1), key=key)


def _skewness_label(sk: float) -> tuple[str, str]:
    """Return (label, color) untuk skewness."""
    if abs(sk) < 0.5:
        return "Simetris", GREEN
    elif abs(sk) < 1.0:
        return "Sedikit Miring", BLUE
    elif sk > 0:
        return "Miring Kanan (+)", RED2
    else:
        return "Miring Kiri (−)", PURPLE


# ═══════════════════════════════════════════════════════════════════════════════
# Tab 1 — Ringkasan Data (Data Profiler)
# ═══════════════════════════════════════════════════════════════════════════════

def _tab_ringkasan(df: pd.DataFrame):
    st.markdown("#### 🗂️ Profil Dataset")

    n_rows, n_cols = df.shape
    num_cols  = df.select_dtypes(include="number").columns.tolist()
    cat_cols  = df.select_dtypes(include=["object", "category"]).columns.tolist()
    bool_cols = df.select_dtypes(include="bool").columns.tolist()
    n_missing = int(df.isnull().sum().sum())
    pct_miss  = round(n_missing / (n_rows * n_cols) * 100, 2)
    n_dup     = int(df.duplicated().sum())

    # ── Metrik ringkas ────────────────────────────────────────────────────────
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    cards = [
        (m1, "Baris",      n_rows,           None),
        (m2, "Kolom",      n_cols,           None),
        (m3, "Numerik",    len(num_cols),    None),
        (m4, "Kategorik",  len(cat_cols),    None),
        (m5, "Missing",    n_missing,        RED if n_missing > 0 else GREEN),
        (m6, "Duplikat",   n_dup,            RED if n_dup > 0 else GREEN),
    ]
    for col_obj, lbl, val, color in cards:
        c_str = f'color:{color};' if color else ""
        col_obj.markdown(
            f'<div class="rs-metric">'
            f'<div class="rs-metric-label">{lbl}</div>'
            f'<div class="rs-metric-value" style="font-size:1.3rem;{c_str}">{val}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # ── Tabel profil per kolom ────────────────────────────────────────────────
    rows = []
    for col in df.columns:
        s = df[col]
        dtype  = str(s.dtype)
        n_miss = int(s.isnull().sum())
        pct_m  = round(n_miss / n_rows * 100, 1)
        n_uniq = int(s.nunique(dropna=True))

        if s.dtype.kind in "iufc":   # numerik
            vals = s.dropna()
            mean_v = round(float(vals.mean()), 3) if len(vals) else "–"
            std_v  = round(float(vals.std()),  3) if len(vals) else "–"
            min_v  = round(float(vals.min()),  3) if len(vals) else "–"
            max_v  = round(float(vals.max()),  3) if len(vals) else "–"
            sk     = round(float(scipy_stats.skew(vals)), 3) if len(vals) > 2 else "–"
            rows.append({
                "Kolom": col, "Tipe": dtype, "Missing": f"{n_miss} ({pct_m}%)",
                "Unik": n_uniq, "Mean": mean_v, "SD": std_v,
                "Min": min_v, "Max": max_v, "Skewness": sk,
                "Top Value": "–",
            })
        else:   # kategorik / teks
            top_val = s.value_counts().index[0] if n_uniq > 0 else "–"
            rows.append({
                "Kolom": col, "Tipe": dtype, "Missing": f"{n_miss} ({pct_m}%)",
                "Unik": n_uniq, "Mean": "–", "SD": "–",
                "Min": "–", "Max": "–", "Skewness": "–",
                "Top Value": str(top_val)[:30],
            })

    profile_df = pd.DataFrame(rows)

    def _highlight_missing(val):
        if isinstance(val, str) and "%" in val:
            try:
                pct = float(val.split("(")[1].replace("%)", ""))
                if pct > 20:
                    return "background-color:#fcebeb"
                elif pct > 5:
                    return "background-color:#faeeda"
            except Exception:
                pass
        return ""

    st.markdown("**📋 Profil Kolom:**")
    st.dataframe(
        profile_df.style.map(_highlight_missing, subset=["Missing"]),
        use_container_width=True, hide_index=True,
    )

    # ── Distribusi tipe data (donut) ──────────────────────────────────────────
    col_pie, col_miss_bar = st.columns(2)

    with col_pie:
        type_counts = {
            "Numerik": len(num_cols),
            "Kategorik": len(cat_cols),
            "Boolean": len(bool_cols),
            "Lainnya": n_cols - len(num_cols) - len(cat_cols) - len(bool_cols),
        }
        type_counts = {k: v for k, v in type_counts.items() if v > 0}
        fig_donut = go.Figure(go.Pie(
            labels=list(type_counts.keys()),
            values=list(type_counts.values()),
            hole=0.55,
            marker=dict(colors=[BLUE, GREEN, RED2, PURPLE]),
            textinfo="label+percent",
        ))
        fig_donut.update_layout(
            title="Komposisi Tipe Kolom",
            template="plotly_white", height=300,
            margin=dict(l=10, r=10, t=45, b=10),
            showlegend=False,
        )
        st.plotly_chart(fig_donut, use_container_width=True)

    with col_miss_bar:
        miss_series = df.isnull().sum()
        miss_series = miss_series[miss_series > 0].sort_values(ascending=False)
        if not miss_series.empty:
            colors = [RED if v / n_rows > 0.2 else RED2 if v / n_rows > 0.05 else BLUE
                      for v in miss_series.values]
            fig_miss = go.Figure(go.Bar(
                x=miss_series.index.tolist(),
                y=miss_series.values,
                marker_color=colors,
                text=[f"{v}" for v in miss_series.values],
                textposition="outside",
            ))
            fig_miss.update_layout(
                title="Missing Values per Kolom",
                yaxis_title="Jumlah Missing",
                template="plotly_white", height=300,
                margin=dict(l=10, r=10, t=45, b=10),
            )
            st.plotly_chart(fig_miss, use_container_width=True)
        else:
            st.success("🎉 Tidak ada missing values di dataset ini!")

    # ── Nilai unik per kolom kategorik ───────────────────────────────────────
    if cat_cols:
        with st.expander("📊 Frekuensi Nilai Kategorik"):
            cat_sel = st.selectbox("Pilih kolom kategorik:", cat_cols, key="eda_cat_freq")
            vc = df[cat_sel].value_counts().head(20)
            fig_vc = go.Figure(go.Bar(
                x=vc.index.astype(str).tolist(),
                y=vc.values,
                marker_color=BLUE,
                text=vc.values, textposition="outside",
            ))
            fig_vc.update_layout(
                title=f"Frekuensi: {cat_sel}",
                template="plotly_white", height=320,
                margin=dict(l=10, r=10, t=45, b=10),
            )
            st.plotly_chart(fig_vc, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# Tab 2 — Distribusi & Violin + Strip Plot
# ═══════════════════════════════════════════════════════════════════════════════

def _tab_distribusi(df: pd.DataFrame):
    st.markdown("#### 📈 Distribusi, Violin & Strip Plot")

    num_cols = df.select_dtypes(include="number").columns.tolist()
    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()

    if not num_cols:
        st.warning("⚠️ Tidak ada kolom numerik.")
        return

    # ── Mode: satu kolom vs semua ─────────────────────────────────────────────
    mode = st.radio(
        "Mode tampilan:",
        ["Satu variabel (detail)", "Semua variabel (overview)"],
        horizontal=True, key="eda_dist_mode",
    )

    if mode == "Satu variabel (detail)":
        sel_col = _col_select("Pilih variabel:", num_cols, "eda_dist_col")
        grp_col = st.selectbox(
            "Warnai berdasarkan (opsional):",
            ["– Tanpa kelompok –"] + cat_cols,
            key="eda_dist_grp",
        )
        grp = None if grp_col == "– Tanpa kelompok –" else grp_col

        s = df[sel_col].dropna()
        n = len(s)
        mean_v  = float(s.mean())
        med_v   = float(s.median())
        std_v   = float(s.std())
        sk_v    = float(scipy_stats.skew(s))
        kurt_v  = float(scipy_stats.kurtosis(s))
        sk_lbl, sk_col = _skewness_label(sk_v)

        # Stat ringkas
        m1, m2, m3, m4, m5 = st.columns(5)
        for col_o, lbl, val in zip(
            [m1, m2, m3, m4, m5],
            ["n", "Mean", "Median", "SD", "Skewness"],
            [n, round(mean_v,3), round(med_v,3), round(std_v,3), round(sk_v,3)],
        ):
            col_o.markdown(
                f'<div class="rs-metric">'
                f'<div class="rs-metric-label">{lbl}</div>'
                f'<div class="rs-metric-value" style="font-size:1.2rem">{val}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        _narasi(
            f"📐 Skewness = {sk_v:.3f} → <b>{sk_lbl}</b> | Kurtosis = {kurt_v:.3f}",
            sk_col,
        )

        col_v1, col_v2 = st.columns(2)

        # Histogram + KDE
        with col_v1:
            if grp:
                fig_h = px.histogram(
                    df.dropna(subset=[sel_col, grp]),
                    x=sel_col, color=grp, marginal="box",
                    opacity=0.7, barmode="overlay",
                    title=f"Histogram: {sel_col}",
                    template="plotly_white",
                    color_discrete_sequence=PALETTE,
                )
            else:
                fig_h = go.Figure()
                fig_h.add_trace(go.Histogram(
                    x=s, nbinsx=25, name="Frekuensi",
                    marker_color=BLUE, opacity=0.72,
                ))
                # KDE manual
                kde_x = np.linspace(s.min(), s.max(), 200)
                kde = scipy_stats.gaussian_kde(s)
                scale = len(s) * (s.max() - s.min()) / 25
                fig_h.add_trace(go.Scatter(
                    x=kde_x, y=kde(kde_x) * scale,
                    mode="lines", name="KDE",
                    line=dict(color=RED2, width=2.5),
                ))
                fig_h.add_vline(x=mean_v, line_dash="dash", line_color=GREEN,
                                annotation_text=f"Mean={mean_v:.2f}")
                fig_h.add_vline(x=med_v, line_dash="dot", line_color=PURPLE,
                                annotation_text=f"Median={med_v:.2f}")
                fig_h.update_layout(title=f"Histogram + KDE: {sel_col}",
                                    template="plotly_white", height=380,
                                    margin=dict(l=20, r=20, t=50, b=20))
            st.plotly_chart(fig_h, use_container_width=True)

        # Violin + Strip
        with col_v2:
            if grp:
                sub = df[[sel_col, grp]].dropna()
                groups = sub[grp].unique()
                fig_v = go.Figure()
                for i, g in enumerate(groups):
                    arr = sub[sub[grp] == g][sel_col].values
                    c = PALETTE[i % len(PALETTE)]
                    fig_v.add_trace(go.Violin(
                        y=arr, name=str(g), box_visible=True,
                        meanline_visible=True, fillcolor=c,
                        opacity=0.6, line_color=c, points="all",
                        jitter=0.3, pointpos=-1.8,
                    ))
            else:
                fig_v = go.Figure()
                fig_v.add_trace(go.Violin(
                    y=s, name=sel_col, box_visible=True,
                    meanline_visible=True, fillcolor=BLUE,
                    opacity=0.6, line_color=BLUE, points="all",
                    jitter=0.35, pointpos=-1.8,
                ))
            fig_v.update_layout(title=f"Violin + Strip: {sel_col}",
                                template="plotly_white", height=380,
                                margin=dict(l=20, r=20, t=50, b=20))
            st.plotly_chart(fig_v, use_container_width=True)

        # Q-Q Plot
        with st.expander("📐 Q-Q Plot Normalitas"):
            qq = scipy_stats.probplot(s, dist="norm")
            x_line = np.array([qq[0][0][0], qq[0][0][-1]])
            fig_qq = go.Figure()
            fig_qq.add_trace(go.Scatter(
                x=qq[0][0], y=qq[0][1], mode="markers", name="Data",
                marker=dict(color=BLUE, size=5),
            ))
            fig_qq.add_trace(go.Scatter(
                x=x_line, y=qq[1][0] * x_line + qq[1][1],
                mode="lines", name="Normal", line=dict(color=RED2, width=2),
            ))
            fig_qq.update_layout(
                title=f"Q-Q Plot: {sel_col}",
                xaxis_title="Theoretical Quantiles",
                yaxis_title="Sample Quantiles",
                template="plotly_white", height=340,
                margin=dict(l=20, r=20, t=50, b=20),
            )
            st.plotly_chart(fig_qq, use_container_width=True)
            # Shapiro
            if 3 <= n <= 5000:
                stat_sw, p_sw = scipy_stats.shapiro(s)
                sig_lbl = "❌ Tidak Normal (p < 0.05)" if p_sw < 0.05 else "✅ Normal (p ≥ 0.05)"
                _narasi(
                    f"Shapiro-Wilk: W = {stat_sw:.4f}, p = {p_sw:.4f} → {sig_lbl}",
                    RED if p_sw < 0.05 else GREEN,
                )

    else:   # Overview: semua variabel
        max_cols = st.slider("Maks kolom ditampilkan:", 2, min(12, len(num_cols)),
                              min(6, len(num_cols)), key="eda_dist_max")
        display_cols = num_cols[:max_cols]
        n_grid = len(display_cols)
        n_rows_g = (n_grid + 2) // 3

        st.markdown(f"**Distribusi {n_grid} variabel pertama:**")

        for row_i in range(n_rows_g):
            grid_cols = st.columns(3)
            for col_i in range(3):
                idx = row_i * 3 + col_i
                if idx >= n_grid:
                    break
                c = display_cols[idx]
                s = df[c].dropna()
                with grid_cols[col_i]:
                    fig_mini = go.Figure(go.Histogram(
                        x=s, nbinsx=20, marker_color=PALETTE[idx % len(PALETTE)],
                        opacity=0.8,
                    ))
                    sk = scipy_stats.skew(s) if len(s) > 2 else 0
                    fig_mini.update_layout(
                        title=f"{c} (sk={sk:.2f})",
                        template="plotly_white", height=200,
                        margin=dict(l=5, r=5, t=35, b=5),
                        showlegend=False,
                        xaxis=dict(showticklabels=False),
                    )
                    st.plotly_chart(fig_mini, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# Tab 3 — Pair Plot (Scatter Matrix)
# ═══════════════════════════════════════════════════════════════════════════════

def _tab_pairplot(df: pd.DataFrame):
    st.markdown("#### 🔵 Pair Plot (Scatter Matrix)")
    st.caption(
        "Visualisasi hubungan antar semua pasangan variabel numerik. "
        "Diagonal menampilkan distribusi masing-masing variabel."
    )

    num_cols = df.select_dtypes(include="number").columns.tolist()
    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()

    if len(num_cols) < 2:
        st.warning("⚠️ Diperlukan minimal 2 kolom numerik.")
        return

    # Pilih variabel
    max_vars = min(8, len(num_cols))
    selected = st.multiselect(
        f"Pilih variabel (maks {max_vars}):",
        num_cols,
        default=num_cols[:min(5, len(num_cols))],
        key="eda_pair_cols",
    )
    if len(selected) < 2:
        st.info("Pilih minimal 2 variabel.")
        return
    if len(selected) > max_vars:
        st.warning(f"⚠️ Maks {max_vars} variabel untuk performa. Menggunakan {max_vars} pertama.")
        selected = selected[:max_vars]

    color_col = st.selectbox(
        "Warnai berdasarkan (opsional):",
        ["– Tanpa kelompok –"] + cat_cols,
        key="eda_pair_color",
    )
    diag_type = st.radio("Diagonal:", ["histogram", "box", "violin"],
                          horizontal=True, key="eda_pair_diag")

    sub = df[selected + ([color_col] if color_col != "– Tanpa kelompok –" else [])].dropna()
    color = color_col if color_col != "– Tanpa kelompok –" else None

    with st.spinner("Membangun pair plot..."):
        fig = px.scatter_matrix(
            sub,
            dimensions=selected,
            color=color,
            color_discrete_sequence=PALETTE,
            opacity=0.55,
            title=f"Pair Plot — {len(selected)} Variabel",
            template="plotly_white",
        )
        # Sesuaikan diagonal
        fig.update_traces(
            diagonal_visible=True,
            showupperhalf=True,
        )
        # Ukuran dinamis
        size = max(500, 160 * len(selected))
        fig.update_layout(
            height=size,
            margin=dict(l=30, r=30, t=60, b=30),
        )

    st.plotly_chart(fig, use_container_width=True)

    # ── Tabel korelasi ringkas ───────────────────────────────────────────────
    with st.expander("📋 Tabel Korelasi Pearson"):
        corr = sub[selected].corr().round(3)

        def _color_corr(val):
            try:
                v = float(val)
                intensity = abs(v)
                if v > 0:
                    r, g, b = int(255 - intensity * 80), int(255 - intensity * 60), 255
                elif v < 0:
                    r, g, b = 255, int(255 - intensity * 60), int(255 - intensity * 80)
                else:
                    r, g, b = 255, 255, 255
                return f"background-color: rgb({r},{g},{b})"
            except Exception:
                return ""

        st.dataframe(corr.style.map(_color_corr),
                     use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# Tab 4 — Kategorik & Mosaic Plot
# ═══════════════════════════════════════════════════════════════════════════════

def _tab_kategorik(df: pd.DataFrame):
    st.markdown("#### 📊 Analisis Kategorik & Mosaic Plot")

    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
    # Kolom numerik biner juga bisa jadi kategorik
    num_cols = df.select_dtypes(include="number").columns.tolist()
    bin_cols = [c for c in num_cols if df[c].nunique() <= 10]
    all_cat  = cat_cols + bin_cols

    if not all_cat:
        st.warning("⚠️ Tidak ada kolom kategorik atau numerik dengan nilai unik ≤ 10.")
        return

    sub_tab = st.radio(
        "Jenis visualisasi:",
        ["Bar Chart Frekuensi", "Grouped / Stacked Bar", "Mosaic Plot 2 Variabel"],
        horizontal=True, key="eda_cat_subtab",
    )

    # ── Bar Chart Frekuensi ───────────────────────────────────────────────────
    if sub_tab == "Bar Chart Frekuensi":
        sel = _col_select("Pilih variabel kategorik:", all_cat, "eda_cat_freq2")
        orient = st.radio("Orientasi:", ["Vertikal", "Horizontal"],
                           horizontal=True, key="eda_cat_orient")
        top_n = st.slider("Tampilkan top N:", 5, 30, 15, key="eda_cat_topn")

        vc = df[sel].astype(str).value_counts().head(top_n)
        pct = (vc / vc.sum() * 100).round(1)

        if orient == "Vertikal":
            fig = go.Figure(go.Bar(
                x=vc.index.tolist(), y=vc.values,
                marker_color=BLUE,
                text=[f"{v} ({p}%)" for v, p in zip(vc.values, pct.values)],
                textposition="outside",
            ))
            fig.update_layout(xaxis_title=sel, yaxis_title="Frekuensi",
                               yaxis_range=[0, vc.max() * 1.2])
        else:
            fig = go.Figure(go.Bar(
                y=vc.index.tolist(), x=vc.values, orientation="h",
                marker_color=BLUE,
                text=[f"{v} ({p}%)" for v, p in zip(vc.values, pct.values)],
                textposition="outside",
            ))
            fig.update_layout(yaxis_title=sel, xaxis_title="Frekuensi",
                               xaxis_range=[0, vc.max() * 1.3])

        fig.update_layout(title=f"Frekuensi: {sel} (Top {top_n})",
                          template="plotly_white", height=380,
                          margin=dict(l=20, r=20, t=50, b=20))
        st.plotly_chart(fig, use_container_width=True)

    # ── Grouped / Stacked Bar ─────────────────────────────────────────────────
    elif sub_tab == "Grouped / Stacked Bar":
        if len(all_cat) < 2:
            st.warning("⚠️ Diperlukan minimal 2 variabel kategorik.")
            return
        c1, c2 = st.columns(2)
        with c1:
            var_x = _col_select("Variabel X (kategori):", all_cat, "eda_gb_x")
        with c2:
            var_grp = st.selectbox(
                "Variabel Kelompok (warna):",
                [c for c in all_cat if c != var_x],
                key="eda_gb_grp",
            )
        bar_mode = st.radio("Mode:", ["group", "stack", "relative"],
                             horizontal=True, key="eda_gb_mode")

        ct = pd.crosstab(df[var_x].astype(str), df[var_grp].astype(str))
        top_x = ct.sum(axis=1).nlargest(20).index
        ct = ct.loc[top_x]

        fig = go.Figure()
        for i, grp in enumerate(ct.columns):
            fig.add_trace(go.Bar(
                name=str(grp), x=ct.index.tolist(), y=ct[grp].values,
                marker_color=PALETTE[i % len(PALETTE)],
            ))
        fig.update_layout(
            barmode=bar_mode,
            title=f"{var_x} × {var_grp} ({bar_mode.title()})",
            xaxis_title=var_x, yaxis_title="Frekuensi",
            template="plotly_white", height=400,
            margin=dict(l=20, r=20, t=50, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)

        # Tabel crosstab
        with st.expander("📋 Tabel Kontingensi"):
            st.dataframe(ct, use_container_width=True)
            # Chi-square
            from scipy.stats import chi2_contingency
            chi2, p, dof, _ = chi2_contingency(ct.values)
            sig_lbl = "✅ Signifikan" if p < 0.05 else "❌ Tidak Signifikan"
            _narasi(
                f"🔬 Chi-Square Test: χ²({dof}) = {chi2:.3f}, p = {p:.4f} → {sig_lbl} pada α = 0.05",
                GREEN if p < 0.05 else RED,
            )

    # ── Mosaic Plot ───────────────────────────────────────────────────────────
    else:
        st.caption(
            "Mosaic plot menampilkan proporsi dua variabel kategorik secara bersamaan. "
            "Luas setiap kotak proporsional terhadap frekuensinya."
        )
        if len(all_cat) < 2:
            st.warning("⚠️ Diperlukan minimal 2 variabel kategorik.")
            return
        c1, c2 = st.columns(2)
        with c1:
            var_r = _col_select("Variabel Baris:", all_cat, "eda_mos_r")
        with c2:
            var_c = st.selectbox(
                "Variabel Kolom:",
                [c for c in all_cat if c != var_r],
                key="eda_mos_c",
            )

        sub = df[[var_r, var_c]].dropna().astype(str)
        ct  = pd.crosstab(sub[var_r], sub[var_c])
        cats_r = ct.index.tolist()
        cats_c = ct.columns.tolist()

        # Bangun mosaic dengan go.Figure rectangles
        fig = go.Figure()
        col_widths = ct.sum(axis=1) / ct.sum().sum()
        x_cursor   = 0.0

        for i, row_cat in enumerate(cats_r):
            col_total = ct.loc[row_cat].sum()
            w = float(col_widths[row_cat])
            y_cursor = 0.0
            for j, col_cat in enumerate(cats_c):
                count = ct.loc[row_cat, col_cat]
                h = count / col_total if col_total > 0 else 0
                color = PALETTE[j % len(PALETTE)]
                fig.add_shape(
                    type="rect",
                    x0=x_cursor + 0.005, x1=x_cursor + w - 0.005,
                    y0=y_cursor + 0.003, y1=y_cursor + h - 0.003,
                    fillcolor=color, opacity=0.8,
                    line=dict(color="white", width=2),
                )
                # Label tengah
                cx = x_cursor + w / 2
                cy = y_cursor + h / 2
                pct = round(count / ct.sum().sum() * 100, 1)
                if h > 0.06 and w > 0.06:
                    fig.add_annotation(
                        x=cx, y=cy,
                        text=f"<b>{col_cat}</b><br>{count} ({pct}%)",
                        showarrow=False, font=dict(size=10, color="white"),
                        align="center",
                    )
                y_cursor += h
            # Label baris
            fig.add_annotation(
                x=x_cursor + w / 2, y=-0.04,
                text=f"<b>{row_cat}</b><br>({ct.loc[row_cat].sum()})",
                showarrow=False, font=dict(size=10, color="#333"),
                align="center",
            )
            x_cursor += w

        fig.update_layout(
            title=f"Mosaic Plot: {var_r} × {var_c}",
            template="plotly_white", height=480,
            xaxis=dict(showticklabels=False, showgrid=False, range=[-0.02, 1.02]),
            yaxis=dict(showticklabels=False, showgrid=False, range=[-0.1, 1.05]),
            margin=dict(l=10, r=10, t=60, b=50),
        )

        # Legend manual
        for j, col_cat in enumerate(cats_c):
            fig.add_trace(go.Scatter(
                x=[None], y=[None], mode="markers",
                marker=dict(size=12, color=PALETTE[j % len(PALETTE)], symbol="square"),
                name=str(col_cat),
            ))

        st.plotly_chart(fig, use_container_width=True)

        with st.expander("📋 Tabel Proporsi"):
            prop_ct = ct.div(ct.sum().sum()).mul(100).round(2)

            def _color_prop(val):
                try:
                    v = float(val)
                    intensity = min(v / 100, 1.0)
                    b = int(255 - intensity * 120)
                    return f"background-color: rgb({b + 40},{b + 60},{255})"
                except Exception:
                    return ""

            st.dataframe(prop_ct.style.map(_color_prop),
                         use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# Tab 5 — Korelasi & Parallel Coordinates
# ═══════════════════════════════════════════════════════════════════════════════

def _tab_korelasi_paralel(df: pd.DataFrame):
    st.markdown("#### 🔗 Korelasi & Parallel Coordinates")

    num_cols = df.select_dtypes(include="number").columns.tolist()
    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()

    if len(num_cols) < 2:
        st.warning("⚠️ Diperlukan minimal 2 kolom numerik.")
        return

    sub_tab = st.radio(
        "Jenis visualisasi:",
        ["Heatmap Korelasi", "Parallel Coordinates"],
        horizontal=True, key="eda_cor_subtab",
    )

    # ── Heatmap ───────────────────────────────────────────────────────────────
    if sub_tab == "Heatmap Korelasi":
        method = st.radio("Metode:", ["pearson", "spearman", "kendall"],
                           horizontal=True, key="eda_cor_method")
        selected = st.multiselect(
            "Pilih variabel:", num_cols, default=num_cols[:min(10, len(num_cols))],
            key="eda_cor_vars",
        )
        if len(selected) < 2:
            st.info("Pilih minimal 2 variabel.")
            return

        sub = df[selected].dropna()
        corr = sub.corr(method=method).round(3)

        cscale = "RdBu"
        fig = go.Figure(go.Heatmap(
            z=corr.values, x=corr.columns.tolist(), y=corr.columns.tolist(),
            colorscale=cscale, zmin=-1, zmax=1,
            text=corr.values,
            texttemplate="%{text:.2f}", textfont={"size": 11},
            colorbar={"title": method.capitalize()},
        ))
        fig.update_layout(
            title=f"Heatmap Korelasi ({method.capitalize()})",
            template="plotly_white", height=max(400, 60 * len(selected)),
            margin=dict(l=10, r=10, t=55, b=10),
        )
        st.plotly_chart(fig, use_container_width=True)

        # Pasangan korelasi kuat
        thresh = st.slider("Threshold |r|:", 0.3, 0.9, 0.5, 0.05, key="eda_cor_thresh")
        pairs = []
        for i in range(len(corr.columns)):
            for j in range(i + 1, len(corr.columns)):
                r_val = corr.iloc[i, j]
                if abs(r_val) >= thresh:
                    pairs.append({
                        "Variabel A": corr.columns[i],
                        "Variabel B": corr.columns[j],
                        "r": round(r_val, 3),
                        "Kekuatan": "Kuat +" if r_val > 0 else "Kuat −",
                    })
        if pairs:
            st.markdown(f"**Pasangan dengan |r| ≥ {thresh}:**")
            st.dataframe(pd.DataFrame(pairs), use_container_width=True, hide_index=True)
        else:
            st.info(f"Tidak ada pasangan dengan |r| ≥ {thresh}.")

    # ── Parallel Coordinates ──────────────────────────────────────────────────
    else:
        st.caption(
            "Setiap garis mewakili satu observasi. "
            "Garis yang mengelompok menunjukkan pola korelasi antar variabel."
        )
        selected = st.multiselect(
            "Pilih variabel numerik (3–10 disarankan):",
            num_cols, default=num_cols[:min(6, len(num_cols))],
            key="eda_par_vars",
        )
        color_col = st.selectbox(
            "Warnai berdasarkan:",
            ["– Tanpa kelompok –"] + num_cols + cat_cols,
            key="eda_par_color",
        )

        if len(selected) < 2:
            st.info("Pilih minimal 2 variabel.")
            return

        all_needed = list(selected)
        if color_col not in ["– Tanpa kelompok –"] and color_col not in all_needed:
            all_needed.append(color_col)

        sub = df[all_needed].dropna()
        if len(sub) == 0:
            st.warning("⚠️ Tidak ada baris valid setelah dropna.")
            return

        # Jika color adalah kategorik, encode jadi int
        color_kwarg = {}
        if color_col != "– Tanpa kelompok –":
            if sub[color_col].dtype.kind not in "iufc":
                sub = sub.copy()
                sub["__color__"] = pd.factorize(sub[color_col])[0]
                color_kwarg = {"color": "__color__",
                               "color_continuous_scale": px.colors.sequential.Viridis}
            else:
                color_kwarg = {"color": color_col,
                               "color_continuous_scale": px.colors.sequential.Viridis}

        fig = px.parallel_coordinates(
            sub,
            dimensions=selected,
            title="Parallel Coordinates Plot",
            template="plotly_white",
            **color_kwarg,
        )
        fig.update_layout(
            height=480, margin=dict(l=60, r=60, t=70, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)

        _narasi(
            "💡 <b>Tips membaca Parallel Coordinates:</b> Seret sumbu untuk mengubah urutan. "
            "Klik dan seret pada sumbu untuk memfilter rentang nilai. "
            "Garis paralel menunjukkan korelasi positif; garis bersilang menunjukkan korelasi negatif.",
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Tab 6 — Missing Value Heatmap & Pola
# ═══════════════════════════════════════════════════════════════════════════════

def _tab_missing(df: pd.DataFrame):
    st.markdown("#### 🕳️ Analisis Missing Values")

    n_rows, n_cols_total = df.shape
    miss_total = df.isnull().sum().sum()

    if miss_total == 0:
        st.success("🎉 Dataset ini **tidak memiliki missing values**. Siap untuk analisis!")
        # Tetap tampilkan ringkasan
        st.metric("Total Observasi", n_rows)
        st.metric("Total Kolom", n_cols_total)
        return

    miss_per_col = df.isnull().sum()
    miss_per_col = miss_per_col[miss_per_col > 0].sort_values(ascending=False)
    miss_per_row = df.isnull().sum(axis=1)

    # ── Ringkasan ──────────────────────────────────────────────────────────────
    m1, m2, m3, m4 = st.columns(4)
    pct_miss = round(miss_total / (n_rows * n_cols_total) * 100, 2)
    n_rows_miss = int((miss_per_row > 0).sum())
    n_cols_miss = int(len(miss_per_col))

    for col_o, lbl, val, color in [
        (m1, "Total Missing", miss_total, RED),
        (m2, "% Missing", f"{pct_miss}%", RED if pct_miss > 10 else RED2),
        (m3, "Baris Terdampak", n_rows_miss, RED2),
        (m4, "Kolom Terdampak", n_cols_miss, RED2),
    ]:
        col_o.markdown(
            f'<div class="rs-metric">'
            f'<div class="rs-metric-label">{lbl}</div>'
            f'<div class="rs-metric-value" style="font-size:1.3rem;color:{color};">{val}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # ── Bar chart missing per kolom ───────────────────────────────────────────
    col_v1, col_v2 = st.columns(2)
    with col_v1:
        bar_colors = [RED if v / n_rows > 0.2 else RED2 if v / n_rows > 0.05 else BLUE
                      for v in miss_per_col.values]
        fig_bar = go.Figure(go.Bar(
            x=miss_per_col.index.tolist(),
            y=miss_per_col.values,
            marker_color=bar_colors,
            text=[f"{v} ({v/n_rows*100:.1f}%)" for v in miss_per_col.values],
            textposition="outside",
        ))
        fig_bar.add_hline(y=n_rows * 0.05, line_dash="dot", line_color=RED2,
                           annotation_text="5% threshold")
        fig_bar.add_hline(y=n_rows * 0.20, line_dash="dash", line_color=RED,
                           annotation_text="20% threshold")
        fig_bar.update_layout(
            title="Missing per Kolom",
            yaxis_title="Jumlah Missing", template="plotly_white",
            height=360, margin=dict(l=10, r=10, t=50, b=10),
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    with col_v2:
        # Distribusi missing per baris
        fig_row = go.Figure(go.Histogram(
            x=miss_per_row[miss_per_row > 0].values,
            nbinsx=20, marker_color=RED2, opacity=0.75,
        ))
        fig_row.update_layout(
            title="Distribusi Missing per Baris",
            xaxis_title="Jumlah Missing dalam Satu Baris",
            yaxis_title="Jumlah Baris",
            template="plotly_white", height=360,
            margin=dict(l=10, r=10, t=50, b=10),
        )
        st.plotly_chart(fig_row, use_container_width=True)

    # ── Heatmap pola missing ──────────────────────────────────────────────────
    st.markdown("##### 🗺️ Heatmap Pola Missing")
    st.caption(
        "Setiap baris = satu observasi, setiap kolom = satu variabel. "
        "Warna merah = nilai hilang. Pola vertikal mengindikasikan missing bersama (MCAR/MAR)."
    )

    # Batasi tampilan agar tidak terlalu besar
    max_rows_show = st.slider("Baris yang ditampilkan:", 50, min(500, n_rows), 200,
                               step=50, key="eda_miss_rows")
    miss_cols_only = miss_per_col.index.tolist()  # hanya kolom yang ada missing

    miss_matrix = df[miss_cols_only].head(max_rows_show).isnull().astype(int)

    fig_hm = go.Figure(go.Heatmap(
        z=miss_matrix.values,
        x=miss_matrix.columns.tolist(),
        y=[f"R{i+1}" for i in range(len(miss_matrix))],
        colorscale=[[0, "#eaf3de"], [1, "#A32D2D"]],
        showscale=False,
        zmin=0, zmax=1,
    ))
    fig_hm.update_layout(
        title=f"Pola Missing ({max_rows_show} baris pertama, {len(miss_cols_only)} kolom terdampak)",
        template="plotly_white",
        height=max(300, min(600, max_rows_show * 2)),
        margin=dict(l=50, r=10, t=60, b=10),
        yaxis=dict(showticklabels=max_rows_show <= 100),
    )
    st.plotly_chart(fig_hm, use_container_width=True)

    # ── Korelasi antar missing (co-occurrence) ────────────────────────────────
    if len(miss_cols_only) >= 2:
        with st.expander("🔗 Co-occurrence Missing (Kolom mana yang sering hilang bersamaan?)"):
            miss_bool = df[miss_cols_only].isnull()
            co_occur  = miss_bool.T.dot(miss_bool).astype(int)
            np.fill_diagonal(co_occur.values, 0)  # hapus diagonal (self)

            fig_co = go.Figure(go.Heatmap(
                z=co_occur.values,
                x=co_occur.columns.tolist(),
                y=co_occur.index.tolist(),
                colorscale="Reds",
                text=co_occur.values,
                texttemplate="%{text}",
                textfont={"size": 10},
                colorbar={"title": "Co-miss"},
            ))
            fig_co.update_layout(
                title="Co-occurrence: Jumlah Baris Missing Bersama",
                template="plotly_white", height=420,
                margin=dict(l=10, r=10, t=55, b=10),
            )
            st.plotly_chart(fig_co, use_container_width=True)

    # ── Rekomendasi penanganan ─────────────────────────────────────────────────
    st.markdown("##### 💡 Rekomendasi Penanganan Missing")
    recs = []
    for col, cnt in miss_per_col.items():
        pct = cnt / n_rows * 100
        if pct > 50:
            recs.append(f"🔴 **{col}** ({pct:.1f}%) — Pertimbangkan **hapus kolom** (>50% hilang).")
        elif pct > 20:
            recs.append(f"🟠 **{col}** ({pct:.1f}%) — Gunakan **multiple imputation** atau model-based imputation.")
        elif pct > 5:
            recs.append(f"🟡 **{col}** ({pct:.1f}%) — **Mean/median imputation** atau KNN imputation.")
        else:
            recs.append(f"🟢 **{col}** ({pct:.1f}%) — **Listwise deletion** atau mean imputation aman.")

    for r in recs:
        st.markdown(r)


# ═══════════════════════════════════════════════════════════════════════════════
# Entry point
# ═══════════════════════════════════════════════════════════════════════════════

def render(ctx: dict):
    st.markdown(
        '<p class="rs-section-title">🔍 Visualisasi Eksplorasi Data (EDA)</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="rs-section-sub">'
        'Profil data · Distribusi · Pair Plot · Kategorik & Mosaic · '
        'Korelasi & Parallel Coordinates · Missing Values'
        '</p>',
        unsafe_allow_html=True,
    )

    df = require_data()
    if df is None:
        st.stop()

    if len(df.columns) == 0:
        st.error("❌ Dataset kosong atau tidak memiliki kolom yang dapat dibaca.")
        st.stop()

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🗂️ Ringkasan",
        "📈 Distribusi & Violin",
        "🔵 Pair Plot",
        "📊 Kategorik & Mosaic",
        "🔗 Korelasi & Paralel",
        "🕳️ Missing Values",
    ])

    with tab1:
        _tab_ringkasan(df)

    with tab2:
        _tab_distribusi(df)

    with tab3:
        _tab_pairplot(df)

    with tab4:
        _tab_kategorik(df)

    with tab5:
        _tab_korelasi_paralel(df)

    with tab6:
        _tab_missing(df)

    # ── Simpan ringkasan ke session_state untuk export laporan ────────────────
    num_cols  = df.select_dtypes(include="number").columns.tolist()
    cat_cols  = df.select_dtypes(include=["object", "category"]).columns.tolist()
    n_missing = int(df.isnull().sum().sum())
    n_dup     = int(df.duplicated().sum())
    st.session_state["eda_result"] = {
        "n_rows":    len(df),
        "n_cols":    len(df.columns),
        "n_numeric": len(num_cols),
        "n_cat":     len(cat_cols),
        "n_missing": n_missing,
        "pct_missing": round(n_missing / max(len(df) * len(df.columns), 1) * 100, 2),
        "n_dup":     n_dup,
        "num_cols":  num_cols,
        "cat_cols":  cat_cols,
    }
