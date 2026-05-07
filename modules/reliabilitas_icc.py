"""
modules/reliabilitas_icc.py — Uji Reliabilitas ICC (Pro)
Ruang Statistika v4.3

Intraclass Correlation Coefficient untuk:
  - Rater agreement (inter-rater reliability)
  - Test-retest reliability
  - Parallel-form reliability

Model ICC yang didukung:
  - ICC(1,1)  → One-way random, single rater
  - ICC(2,1)  → Two-way random, single rater   [Konsistency & Absolute Agreement]
  - ICC(3,1)  → Two-way mixed, single rater    [Konsistency & Absolute Agreement]
  - ICC(1,k)  → One-way random, mean of k raters
  - ICC(2,k)  → Two-way random, mean of k raters
  - ICC(3,k)  → Two-way mixed, mean of k raters

Referensi:
  Koo & Mae (2016). A Guideline of Selecting and Reporting Intraclass
  Correlation Coefficients for Reliability Research. JCCA.
  Shrout & Fleiss (1979). Intraclass Correlations.
  McGraw & Wong (1996). Forming Inferences About Some Intraclass Correlations.
"""

import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from scipy import stats

from utils.auth import require_pro
from utils.stats_helpers import require_data


# ─────────────────────────────────────────────────────────────────────────────
# ICC Computation (pure scipy/numpy, tanpa pingouin)
# ─────────────────────────────────────────────────────────────────────────────

def compute_icc(df_wide: pd.DataFrame) -> pd.DataFrame:
    """
    Hitung semua model ICC (1,1), (2,1), (3,1), (1,k), (2,k), (3,k)
    beserta confidence interval 95% dan p-value.

    Args:
        df_wide : DataFrame dengan baris = subjek, kolom = rater/waktu pengukuran
                  Hanya kolom numerik yang digunakan.

    Returns:
        pd.DataFrame dengan kolom:
            Model, Tipe, Deskripsi, ICC, CI_Lower, CI_Upper, F, df1, df2, p_value
    """
    X = df_wide.to_numpy(dtype=float)
    n, k = X.shape  # n = subjek, k = rater

    # ── Grand mean & sum of squares ──────────────────────────────────────────
    grand_mean   = X.mean()
    row_means    = X.mean(axis=1)
    col_means    = X.mean(axis=0)

    # SS between subjects (rows)
    ss_r = k * np.sum((row_means - grand_mean) ** 2)
    # SS between columns / raters
    ss_c = n * np.sum((col_means  - grand_mean) ** 2)
    # SS total
    ss_t = np.sum((X - grand_mean) ** 2)
    # SS error (residual)
    ss_e = ss_t - ss_r - ss_c
    # SS within (for one-way random)
    ss_w = ss_t - ss_r

    # ── Mean squares ─────────────────────────────────────────────────────────
    ms_r = ss_r / (n - 1)
    ms_c = ss_c / (k - 1)
    ms_e = ss_e / ((n - 1) * (k - 1))
    ms_w = ss_w / (n * (k - 1))

    def _ci_icc(icc_val, F_val, df1, df2, alpha=0.05):
        """Confidence interval menggunakan distribusi F (McGraw & Wong 1996)."""
        if np.isnan(F_val) or F_val <= 0 or np.isnan(icc_val):
            return np.nan, np.nan
        q = stats.f.ppf([alpha / 2, 1 - alpha / 2], df1, df2)
        FL = F_val / q[1]
        FU = F_val / q[0]
        ci_l = (FL - 1) / (FL + (k - 1))
        ci_u = (FU - 1) / (FU + (k - 1))
        return float(np.clip(ci_l, 0, 1)), float(np.clip(ci_u, 0, 1))

    rows = []

    # ── ICC(1,1) — One-way Random, single measure ─────────────────────────────
    icc11  = (ms_r - ms_w) / (ms_r + (k - 1) * ms_w)
    F11    = ms_r / ms_w if ms_w > 0 else np.nan
    p11    = 1 - stats.f.cdf(F11, n - 1, n * (k - 1)) if not np.isnan(F11) else np.nan
    ci_l11, ci_u11 = _ci_icc(icc11, F11, n - 1, n * (k - 1))
    rows.append({
        "Model": "ICC(1,1)", "Tipe": "One-Way Random",
        "Deskripsi": "1 rater acak, 1 pengukuran per subjek",
        "ICC": float(np.clip(icc11, 0, 1)), "CI_Lower": ci_l11, "CI_Upper": ci_u11,
        "F": F11, "df1": n - 1, "df2": n * (k - 1), "p_value": p11,
    })

    # ── ICC(2,1) — Two-way Random, single measure, Absolute Agreement ─────────
    icc21_aa = (ms_r - ms_e) / (ms_r + (k - 1) * ms_e + k * (ms_c - ms_e) / n)
    F21_aa   = ms_r / ms_e if ms_e > 0 else np.nan
    p21_aa   = 1 - stats.f.cdf(F21_aa, n - 1, (n - 1) * (k - 1)) if not np.isnan(F21_aa) else np.nan
    ci_l21aa, ci_u21aa = _ci_icc(icc21_aa, F21_aa, n - 1, (n - 1) * (k - 1))
    rows.append({
        "Model": "ICC(2,1)", "Tipe": "Two-Way Random / Absolute Agreement",
        "Deskripsi": "Rater dipilih acak, kesepakatan absolut antar rater",
        "ICC": float(np.clip(icc21_aa, 0, 1)), "CI_Lower": ci_l21aa, "CI_Upper": ci_u21aa,
        "F": F21_aa, "df1": n - 1, "df2": (n - 1) * (k - 1), "p_value": p21_aa,
    })

    # ── ICC(2,1) — Two-way Random, single measure, Consistency ───────────────
    icc21_c  = (ms_r - ms_e) / (ms_r + (k - 1) * ms_e)
    F21_c    = ms_r / ms_e if ms_e > 0 else np.nan
    p21_c    = 1 - stats.f.cdf(F21_c, n - 1, (n - 1) * (k - 1)) if not np.isnan(F21_c) else np.nan
    ci_l21c, ci_u21c = _ci_icc(icc21_c, F21_c, n - 1, (n - 1) * (k - 1))
    rows.append({
        "Model": "ICC(2,1)", "Tipe": "Two-Way Random / Consistency",
        "Deskripsi": "Rater dipilih acak, konsistensi relatif (bias rater diabaikan)",
        "ICC": float(np.clip(icc21_c, 0, 1)), "CI_Lower": ci_l21c, "CI_Upper": ci_u21c,
        "F": F21_c, "df1": n - 1, "df2": (n - 1) * (k - 1), "p_value": p21_c,
    })

    # ── ICC(3,1) — Two-way Mixed, single measure, Absolute Agreement ─────────
    icc31_aa = (ms_r - ms_e) / (ms_r + (k - 1) * ms_e + k * (ms_c - ms_e) / n)
    F31_aa   = ms_r / ms_e if ms_e > 0 else np.nan
    p31_aa   = 1 - stats.f.cdf(F31_aa, n - 1, (n - 1) * (k - 1)) if not np.isnan(F31_aa) else np.nan
    ci_l31aa, ci_u31aa = _ci_icc(icc31_aa, F31_aa, n - 1, (n - 1) * (k - 1))
    rows.append({
        "Model": "ICC(3,1)", "Tipe": "Two-Way Mixed / Absolute Agreement",
        "Deskripsi": "Rater tetap (fixed), kesepakatan absolut",
        "ICC": float(np.clip(icc31_aa, 0, 1)), "CI_Lower": ci_l31aa, "CI_Upper": ci_u31aa,
        "F": F31_aa, "df1": n - 1, "df2": (n - 1) * (k - 1), "p_value": p31_aa,
    })

    # ── ICC(3,1) — Two-way Mixed, single measure, Consistency ────────────────
    icc31_c  = (ms_r - ms_e) / (ms_r + (k - 1) * ms_e)
    F31_c    = ms_r / ms_e if ms_e > 0 else np.nan
    p31_c    = 1 - stats.f.cdf(F31_c, n - 1, (n - 1) * (k - 1)) if not np.isnan(F31_c) else np.nan
    ci_l31c, ci_u31c = _ci_icc(icc31_c, F31_c, n - 1, (n - 1) * (k - 1))
    rows.append({
        "Model": "ICC(3,1)", "Tipe": "Two-Way Mixed / Consistency",
        "Deskripsi": "Rater tetap (fixed), konsistensi relatif",
        "ICC": float(np.clip(icc31_c, 0, 1)), "CI_Lower": ci_l31c, "CI_Upper": ci_u31c,
        "F": F31_c, "df1": n - 1, "df2": (n - 1) * (k - 1), "p_value": p31_c,
    })

    # ── ICC(1,k), ICC(2,k), ICC(3,k) — Average of k raters ───────────────────
    icc1k  = (ms_r - ms_w) / ms_r
    icc2k_aa = (ms_r - ms_e) / (ms_r + (ms_c - ms_e) / n)
    icc2k_c  = (ms_r - ms_e) / ms_r
    icc3k_aa = icc2k_aa
    icc3k_c  = icc2k_c

    F1k = ms_r / ms_w if ms_w > 0 else np.nan
    p1k = 1 - stats.f.cdf(F1k, n - 1, n * (k - 1)) if not np.isnan(F1k) else np.nan
    F2k = ms_r / ms_e if ms_e > 0 else np.nan
    p2k = 1 - stats.f.cdf(F2k, n - 1, (n - 1) * (k - 1)) if not np.isnan(F2k) else np.nan

    def _ci_icc_k(icc_val, F_val, df1, df2, alpha=0.05):
        if np.isnan(F_val) or F_val <= 0:
            return np.nan, np.nan
        q = stats.f.ppf([alpha / 2, 1 - alpha / 2], df1, df2)
        FL = F_val / q[1]
        FU = F_val / q[0]
        ci_l = (FL - 1) / FL
        ci_u = (FU - 1) / FU
        return float(np.clip(ci_l, 0, 1)), float(np.clip(ci_u, 0, 1))

    ci_l1k, ci_u1k   = _ci_icc_k(icc1k, F1k, n - 1, n * (k - 1))
    ci_l2kaa, ci_u2kaa = _ci_icc_k(icc2k_aa, F2k, n - 1, (n - 1) * (k - 1))
    ci_l2kc, ci_u2kc  = _ci_icc_k(icc2k_c,  F2k, n - 1, (n - 1) * (k - 1))

    rows += [
        {
            "Model": "ICC(1,k)", "Tipe": "One-Way Random / k Raters",
            "Deskripsi": f"Rata-rata {k} rater acak",
            "ICC": float(np.clip(icc1k, 0, 1)),
            "CI_Lower": ci_l1k, "CI_Upper": ci_u1k,
            "F": F1k, "df1": n - 1, "df2": n * (k - 1), "p_value": p1k,
        },
        {
            "Model": "ICC(2,k)", "Tipe": "Two-Way Random / k Raters, Absolute",
            "Deskripsi": f"Rata-rata {k} rater acak, kesepakatan absolut",
            "ICC": float(np.clip(icc2k_aa, 0, 1)),
            "CI_Lower": ci_l2kaa, "CI_Upper": ci_u2kaa,
            "F": F2k, "df1": n - 1, "df2": (n - 1) * (k - 1), "p_value": p2k,
        },
        {
            "Model": "ICC(2,k)", "Tipe": "Two-Way Random / k Raters, Consistency",
            "Deskripsi": f"Rata-rata {k} rater acak, konsistensi",
            "ICC": float(np.clip(icc2k_c, 0, 1)),
            "CI_Lower": ci_l2kc, "CI_Upper": ci_u2kc,
            "F": F2k, "df1": n - 1, "df2": (n - 1) * (k - 1), "p_value": p2k,
        },
        {
            "Model": "ICC(3,k)", "Tipe": "Two-Way Mixed / k Raters, Absolute",
            "Deskripsi": f"Rata-rata {k} rater tetap, kesepakatan absolut",
            "ICC": float(np.clip(icc31_aa / (icc31_aa + (1 - icc31_aa) / k), 0, 1))
                   if not np.isnan(icc31_aa) else np.nan,
            "CI_Lower": ci_l2kaa, "CI_Upper": ci_u2kaa,
            "F": F2k, "df1": n - 1, "df2": (n - 1) * (k - 1), "p_value": p2k,
        },
        {
            "Model": "ICC(3,k)", "Tipe": "Two-Way Mixed / k Raters, Consistency",
            "Deskripsi": f"Rata-rata {k} rater tetap, konsistensi",
            "ICC": float(np.clip(icc3k_c, 0, 1)),
            "CI_Lower": ci_l2kc, "CI_Upper": ci_u2kc,
            "F": F2k, "df1": n - 1, "df2": (n - 1) * (k - 1), "p_value": p2k,
        },
    ]

    result_df = pd.DataFrame(rows)

    # Round numerik
    for col in ("ICC", "CI_Lower", "CI_Upper", "F", "p_value"):
        result_df[col] = pd.to_numeric(result_df[col], errors="coerce").round(4)

    return result_df


def interpret_icc(icc_val: float) -> tuple[str, str, str]:
    """
    Interpretasi kualitas reliabilitas berdasarkan ICC.
    Acuan: Koo & Mae (2016) — JCCA.
    Returns: (label, warna_hex, deskripsi)
    """
    if np.isnan(icc_val) or icc_val < 0:
        return "Tidak dapat dihitung", "#888888", "Nilai ICC tidak valid."
    elif icc_val < 0.50:
        return "Buruk", "#A32D2D", (
            "Reliabilitas buruk — kesepakatan antar rater/waktu sangat rendah. "
            "Instrumen perlu direvisi substantif sebelum digunakan dalam penelitian."
        )
    elif icc_val < 0.75:
        return "Sedang", "#C77A00", (
            "Reliabilitas sedang — kesepakatan cukup tetapi belum memadai untuk "
            "penggunaan klinis atau penelitian bersyarat tinggi."
        )
    elif icc_val < 0.90:
        return "Baik", "#3B6D11", (
            "Reliabilitas baik — instrumen dapat digunakan untuk tujuan penelitian. "
            "Standar ini umumnya cukup untuk publikasi ilmiah."
        )
    else:
        return "Sangat Baik", "#185FA5", (
            "Reliabilitas sangat baik / excellent — instrumen sangat andal dan "
            "memenuhi syarat untuk penggunaan klinis maupun penelitian tingkat tinggi."
        )


def _anova_table(df_wide: pd.DataFrame) -> pd.DataFrame:
    """Hitung tabel ANOVA dua arah untuk ICC (Two-Way)."""
    X = df_wide.to_numpy(dtype=float)
    n, k = X.shape
    grand_mean = X.mean()
    row_means  = X.mean(axis=1)
    col_means  = X.mean(axis=0)

    ss_r = k * np.sum((row_means - grand_mean) ** 2)
    ss_c = n * np.sum((col_means  - grand_mean) ** 2)
    ss_t = np.sum((X - grand_mean) ** 2)
    ss_e = ss_t - ss_r - ss_c

    df_r = n - 1
    df_c = k - 1
    df_e = (n - 1) * (k - 1)

    ms_r = ss_r / df_r
    ms_c = ss_c / df_c
    ms_e = ss_e / df_e

    F_r = ms_r / ms_e if ms_e > 0 else np.nan
    F_c = ms_c / ms_e if ms_e > 0 else np.nan
    p_r = 1 - stats.f.cdf(F_r, df_r, df_e) if not np.isnan(F_r) else np.nan
    p_c = 1 - stats.f.cdf(F_c, df_c, df_e) if not np.isnan(F_c) else np.nan

    return pd.DataFrame([
        {"Sumber Variasi": "Antar Subjek (Between Rows)", "SS": round(ss_r, 4),
         "df": df_r, "MS": round(ms_r, 4), "F": round(F_r, 4), "p-value": round(p_r, 4)},
        {"Sumber Variasi": "Antar Rater (Between Cols)",  "SS": round(ss_c, 4),
         "df": df_c, "MS": round(ms_c, 4), "F": round(F_c, 4), "p-value": round(p_c, 4)},
        {"Sumber Variasi": "Error (Residual)",             "SS": round(ss_e, 4),
         "df": df_e, "MS": round(ms_e, 4), "F": None,         "p-value": None},
        {"Sumber Variasi": "Total",                        "SS": round(ss_t, 4),
         "df": n * k - 1, "MS": None, "F": None, "p-value": None},
    ])


# ─────────────────────────────────────────────────────────────────────────────
# Plotly Visualisasi
# ─────────────────────────────────────────────────────────────────────────────

BLUE  = "#185FA5"
GREEN = "#3B6D11"
RED   = "#A32D2D"
NAVY  = "#0c2340"


def plot_icc_forest(icc_df: pd.DataFrame) -> go.Figure:
    """Forest plot semua model ICC dengan confidence interval."""
    df = icc_df.dropna(subset=["ICC", "CI_Lower", "CI_Upper"]).copy()
    labels = df["Model"] + " — " + df["Tipe"].str[:30]

    fig = go.Figure()

    # Threshold bands (Koo & Mae 2016)
    thresholds = [(0, 0.50, "#fcebeb", "Buruk (<0.50)"),
                  (0.50, 0.75, "#faeeda", "Sedang (0.50–0.75)"),
                  (0.75, 0.90, "#eaf3de", "Baik (0.75–0.90)"),
                  (0.90, 1.00, "#d0e4f7", "Sangat Baik (≥0.90)")]
    for lo, hi, color, _ in thresholds:
        fig.add_shape(type="rect", x0=lo, x1=hi, y0=-0.5, y1=len(df) - 0.5,
                      fillcolor=color, opacity=0.35, line_width=0, layer="below")

    # CI errorbar
    for i, row in df.iterrows():
        idx = list(df.index).index(i)
        color = interpret_icc(row["ICC"])[1]
        fig.add_trace(go.Scatter(
            x=[row["CI_Lower"], row["ICC"], row["CI_Upper"]],
            y=[labels.iloc[idx]] * 3,
            mode="lines+markers",
            marker=dict(size=[6, 12, 6], color=[color, color, color],
                        symbol=["line-ns", "diamond", "line-ns"]),
            line=dict(color=color, width=2),
            showlegend=False,
            hovertemplate=(
                f"<b>{row['Model']}</b><br>"
                f"ICC = {row['ICC']:.4f}<br>"
                f"95% CI: [{row['CI_Lower']:.4f}, {row['CI_Upper']:.4f}]<br>"
                f"p = {row['p_value']:.4f}<extra></extra>"
            ),
        ))

    # Garis referensi
    for thresh, label_text in [(0.50, ""), (0.75, ""), (0.90, "")]:
        fig.add_vline(x=thresh, line_dash="dot", line_color="#aaa", line_width=1)

    fig.update_layout(
        title="Forest Plot ICC — Semua Model (95% CI)",
        xaxis=dict(title="ICC Value", range=[0, 1], tickformat=".2f"),
        yaxis=dict(title=""),
        template="plotly_white",
        height=max(350, len(df) * 45 + 80),
        margin=dict(l=20, r=30, t=50, b=40),
    )
    return fig


def plot_icc_heatmap(df_wide: pd.DataFrame) -> go.Figure:
    """Heatmap nilai pengukuran subjek × rater."""
    fig = go.Figure(go.Heatmap(
        z=df_wide.values,
        x=df_wide.columns.tolist(),
        y=[f"S{i+1}" for i in range(len(df_wide))],
        colorscale="Blues",
        colorbar=dict(title="Nilai"),
        hovertemplate="Subjek: %{y}<br>Rater: %{x}<br>Nilai: %{z}<extra></extra>",
    ))
    fig.update_layout(
        title="Heatmap Nilai Pengukuran (Subjek × Rater)",
        xaxis_title="Rater / Waktu",
        yaxis_title="Subjek",
        template="plotly_white",
        height=max(350, len(df_wide) * 20 + 100),
        margin=dict(l=30, r=20, t=50, b=30),
    )
    return fig


def plot_rater_agreement(df_wide: pd.DataFrame) -> go.Figure:
    """Scatter matrix antar rater untuk visualisasi agreement."""
    cols = df_wide.columns.tolist()
    if len(cols) < 2:
        return None
    if len(cols) > 4:
        cols = cols[:4]  # batasi 4 rater agar tidak terlalu padat
    df_plot = df_wide[cols].copy()
    fig = px.scatter_matrix(
        df_plot,
        dimensions=cols,
        title="Scatter Matrix Antar Rater (Agreement Visualization)",
        template="plotly_white",
        color_discrete_sequence=[BLUE],
        opacity=0.6,
    )
    fig.update_traces(marker=dict(size=5))
    fig.update_layout(height=500, margin=dict(l=20, r=20, t=50, b=20))
    return fig


def plot_bland_altman(df_wide: pd.DataFrame, r1_idx: int = 0, r2_idx: int = 1) -> go.Figure:
    """
    Bland-Altman plot untuk sepasang rater.
    Mendeteksi sistematik bias antar dua pengukuran.
    """
    cols = df_wide.columns.tolist()
    r1_name = cols[r1_idx]
    r2_name = cols[r2_idx]
    v1 = df_wide.iloc[:, r1_idx].to_numpy(dtype=float)
    v2 = df_wide.iloc[:, r2_idx].to_numpy(dtype=float)

    mean_vals = (v1 + v2) / 2
    diff_vals = v1 - v2

    mean_diff = np.mean(diff_vals)
    std_diff  = np.std(diff_vals, ddof=1)
    loa_upper = mean_diff + 1.96 * std_diff
    loa_lower = mean_diff - 1.96 * std_diff

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=mean_vals, y=diff_vals,
        mode="markers",
        marker=dict(color=BLUE, size=7, opacity=0.7),
        name="Perbedaan",
        hovertemplate="Rata-rata: %{x:.3f}<br>Selisih: %{y:.3f}<extra></extra>",
    ))
    fig.add_hline(y=mean_diff, line_color=GREEN, line_width=2,
                  annotation_text=f"Mean diff = {mean_diff:.3f}", annotation_position="right")
    fig.add_hline(y=loa_upper, line_dash="dash", line_color=RED,
                  annotation_text=f"+1.96 SD = {loa_upper:.3f}", annotation_position="right")
    fig.add_hline(y=loa_lower, line_dash="dash", line_color=RED,
                  annotation_text=f"-1.96 SD = {loa_lower:.3f}", annotation_position="right")
    fig.add_hline(y=0, line_dash="dot", line_color="#ccc", line_width=1)

    fig.update_layout(
        title=f"Bland-Altman Plot: {r1_name} vs {r2_name}",
        xaxis_title="Rata-rata dua pengukuran",
        yaxis_title="Selisih (Rater 1 − Rater 2)",
        template="plotly_white",
        height=380,
        margin=dict(l=30, r=120, t=50, b=30),
    )
    return fig, mean_diff, std_diff, loa_lower, loa_upper


# ─────────────────────────────────────────────────────────────────────────────
# Main render
# ─────────────────────────────────────────────────────────────────────────────

def render(ctx: dict):
    license_info = ctx["license_info"]
    ai_enabled   = ctx["ai_enabled"]
    api_key      = ctx["anthropic_api_key"]
    ai_provider  = ctx["ai_provider"]

    # ── Pro guard ─────────────────────────────────────────────────────────────
    if not require_pro(license_info, "Reliabilitas ICC"):
        st.stop()

    st.markdown(
        '<p class="rs-section-title">📏 Uji Reliabilitas ICC</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="rs-section-sub">'
        'Intraclass Correlation Coefficient — rater agreement, test-retest, '
        'dan reliabilitas paralel. Acuan: Koo & Mae (2016), Shrout & Fleiss (1979).'
        '</p>',
        unsafe_allow_html=True,
    )

    # ── 1. Muat data ──────────────────────────────────────────────────────────
    df = require_data()
    if df is None:
        st.stop()

    num_cols = df.select_dtypes(include="number").columns.tolist()
    if len(num_cols) < 2:
        st.error("⚠️ Diperlukan minimal **2 kolom numerik** (rater/pengukuran) dalam dataset.")
        st.stop()

    # ── 2. Konfigurasi ────────────────────────────────────────────────────────
    with st.expander("⚙️ Konfigurasi Analisis ICC", expanded=True):
        col_a, col_b = st.columns([2, 1])

        with col_a:
            selected_cols = st.multiselect(
                "Pilih kolom rater / waktu pengukuran (min. 2)",
                num_cols,
                default=num_cols[:min(4, len(num_cols))],
                help="Setiap kolom = satu rater atau satu sesi pengukuran. "
                     "Setiap baris = satu subjek/responden.",
            )

        with col_b:
            use_type = st.radio(
                "Konteks penggunaan",
                ["Rater Agreement", "Test-Retest", "Parallel Forms"],
                help="Pemilihan konteks membantu rekomendasi model ICC yang paling tepat.",
            )
            alpha_ci = st.slider(
                "Level kepercayaan CI", 0.80, 0.99, 0.95, 0.01,
                format="%.2f",
                help="Confidence interval untuk ICC (default 95%).",
            )

        # Panduan model yang direkomendasikan
        context_guidance = {
            "Rater Agreement": (
                "**Rekomendasi model:** ICC(2,1) Absolute Agreement untuk 1 rater, "
                "ICC(2,k) jika rata-rata beberapa rater digunakan dalam praktik. "
                "Gunakan apabila rater dipilih secara acak dari populasi rater yang lebih besar."
            ),
            "Test-Retest": (
                "**Rekomendasi model:** ICC(3,1) Consistency atau ICC(3,k) untuk "
                "pengukuran berulang pada responden yang sama. "
                "Gunakan Two-Way Mixed karena waktu pengukuran bersifat tetap (fixed)."
            ),
            "Parallel Forms": (
                "**Rekomendasi model:** ICC(2,1) Absolute Agreement — kedua formulir "
                "dianggap sebagai rater acak dari domain item yang sama."
            ),
        }
        st.info(context_guidance[use_type])

    if len(selected_cols) < 2:
        st.warning("Pilih minimal 2 kolom untuk melanjutkan analisis.")
        st.stop()

    df_icc = df[selected_cols].dropna()
    n_subj, n_rater = df_icc.shape

    if n_subj < 10:
        st.warning(
            f"⚠️ Hanya tersedia {n_subj} subjek lengkap setelah menghapus baris kosong. "
            "Disarankan minimal 30 subjek untuk estimasi ICC yang stabil."
        )
    if n_subj < 2:
        st.error("Data tidak mencukupi setelah pembersihan nilai kosong (dibutuhkan min. 2 subjek).")
        st.stop()

    # ── 3. Ringkasan data ─────────────────────────────────────────────────────
    m1, m2, m3, m4 = st.columns(4)
    for col, label, val in [
        (m1, "Subjek (N)", n_subj),
        (m2, "Rater / Sesi (k)", n_rater),
        (m3, "Total Observasi", n_subj * n_rater),
        (m4, "Baris Dihapus (NA)", len(df) - n_subj),
    ]:
        with col:
            st.markdown(
                f'<div class="rs-metric">'
                f'<div class="rs-metric-label">{label}</div>'
                f'<div class="rs-metric-value">{val}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.markdown("<br/>", unsafe_allow_html=True)

    # ── 4. Hitung ICC ─────────────────────────────────────────────────────────
    with st.spinner("⏳ Menghitung ICC…"):
        icc_df = compute_icc(df_icc)
        anova_tbl = _anova_table(df_icc)

    # ── 5. Tab hasil ──────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Tabel ICC",
        "📈 Visualisasi",
        "🔬 ANOVA Tabel",
        "🤖 Interpretasi AI",
    ])

    # ── Tab 1: Tabel ICC ──────────────────────────────────────────────────────
    with tab1:
        st.markdown("#### Hasil Uji Reliabilitas ICC — Semua Model")

        # Highlight ICC berdasarkan kualitas
        def _style_icc(val):
            try:
                v = float(val)
            except (TypeError, ValueError):
                return ""
            if v >= 0.90:
                return "background-color:#d0e4f7; color:#0c2340; font-weight:600"
            elif v >= 0.75:
                return "background-color:#eaf3de; color:#3B6D11; font-weight:600"
            elif v >= 0.50:
                return "background-color:#faeeda; color:#7a4800"
            else:
                return "background-color:#fcebeb; color:#a32d2d"

        def _style_p(val):
            try:
                v = float(val)
            except (TypeError, ValueError):
                return ""
            return "color:#3B6D11; font-weight:600" if v < 0.05 else "color:#a32d2d"

        display_df = icc_df[["Model", "Tipe", "Deskripsi", "ICC",
                              "CI_Lower", "CI_Upper", "F", "df1", "df2", "p_value"]].copy()
        display_df.columns = ["Model", "Tipe", "Deskripsi", "ICC",
                               "CI Lower (95%)", "CI Upper (95%)", "F", "df1", "df2", "p-value"]

        styled = (
            display_df.style
            .map(_style_icc, subset=["ICC"])
            .map(_style_p,   subset=["p-value"])
            .format({
                "ICC": "{:.4f}", "CI Lower (95%)": "{:.4f}",
                "CI Upper (95%)": "{:.4f}", "F": "{:.3f}",
                "p-value": lambda v: f"{v:.4f}" if pd.notna(v) else "–",
            }, na_rep="–")
        )
        st.dataframe(styled, use_container_width=True, hide_index=True)

        # ── Tabel interpretasi threshold ──────────────────────────────────────
        st.markdown("<br/>", unsafe_allow_html=True)
        st.markdown("##### 📚 Panduan Interpretasi ICC (Koo & Mae, 2016)")
        st.markdown("""
| Rentang ICC | Kualitas Reliabilitas |
|---|---|
| ICC < 0.50 | **Buruk** |
| 0.50 ≤ ICC < 0.75 | **Sedang** |
| 0.75 ≤ ICC < 0.90 | **Baik** |
| ICC ≥ 0.90 | **Sangat Baik (Excellent)** |

*Sumber: Koo, T.K. & Mae, M.Y. (2016). A guideline of selecting and reporting intraclass
correlation coefficients for reliability research. Journal of Chiropractic Medicine, 15(2), 155–163.*
        """)

        # ── Kartu model yang direkomendasikan ─────────────────────────────────
        rec_model_map = {
            "Rater Agreement": ("ICC(2,1)", "Two-Way Random / Absolute Agreement"),
            "Test-Retest":     ("ICC(3,1)", "Two-Way Mixed / Consistency"),
            "Parallel Forms":  ("ICC(2,1)", "Two-Way Random / Absolute Agreement"),
        }
        rec_model, rec_tipe = rec_model_map[use_type]
        rec_row = icc_df[
            (icc_df["Model"] == rec_model) & (icc_df["Tipe"].str.contains(rec_tipe.split("/")[1].strip()))
        ]
        if not rec_row.empty:
            rv         = rec_row.iloc[0]
            icc_val    = rv["ICC"]
            label_k, color_k, desc_k = interpret_icc(icc_val)
            st.markdown("<br/>", unsafe_allow_html=True)
            st.markdown(f"##### ✅ Model yang Direkomendasikan untuk *{use_type}*")
            st.markdown(
                f'<div class="rs-narasi" style="border-left-color:{color_k};">'
                f'<b>{rec_model} — {rec_tipe}</b><br/>'
                f'ICC = <b>{icc_val:.4f}</b> &nbsp;|&nbsp; '
                f'95% CI [{rv["CI_Lower"]:.4f}, {rv["CI_Upper"]:.4f}] &nbsp;|&nbsp; '
                f'p = {rv["p_value"]:.4f}<br/>'
                f'<span style="color:{color_k}; font-weight:700;">Kualitas: {label_k}</span><br/>'
                f'<span style="font-size:0.85rem;">{desc_k}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

        # ── Ringkasan Bland-Altman (jika 2 kolom) ────────────────────────────
        if n_rater == 2:
            ba_result = plot_bland_altman(df_icc, 0, 1)
            if ba_result:
                _, mean_diff, std_diff, loa_lower, loa_upper = ba_result
                st.markdown("<br/>", unsafe_allow_html=True)
                st.markdown(f"##### 📐 Ringkasan Bland-Altman ({selected_cols[0]} vs {selected_cols[1]})")
                b1, b2, b3 = st.columns(3)
                with b1:
                    st.markdown(
                        f'<div class="rs-metric"><div class="rs-metric-label">Mean Difference</div>'
                        f'<div class="rs-metric-value">{mean_diff:.4f}</div></div>',
                        unsafe_allow_html=True)
                with b2:
                    st.markdown(
                        f'<div class="rs-metric"><div class="rs-metric-label">LoA Lower</div>'
                        f'<div class="rs-metric-value">{loa_lower:.4f}</div></div>',
                        unsafe_allow_html=True)
                with b3:
                    st.markdown(
                        f'<div class="rs-metric"><div class="rs-metric-label">LoA Upper</div>'
                        f'<div class="rs-metric-value">{loa_upper:.4f}</div></div>',
                        unsafe_allow_html=True)

    # ── Tab 2: Visualisasi ────────────────────────────────────────────────────
    with tab2:
        st.markdown("#### Visualisasi Reliabilitas ICC")

        # Forest plot
        st.plotly_chart(plot_icc_forest(icc_df), use_container_width=True)

        vis_col1, vis_col2 = st.columns(2)

        with vis_col1:
            # Heatmap data
            st.plotly_chart(plot_icc_heatmap(df_icc), use_container_width=True)

        with vis_col2:
            # Bland-Altman (pasangan pertama)
            if n_rater >= 2:
                ba_result = plot_bland_altman(df_icc, 0, 1)
                if ba_result:
                    fig_ba, *_ = ba_result
                    st.plotly_chart(fig_ba, use_container_width=True)

                    # Jika lebih dari 2 rater, tampilkan pilihan pasangan
                    if n_rater > 2:
                        st.markdown("**Plot pasangan lain:**")
                        pairs = [
                            (i, j)
                            for i in range(n_rater)
                            for j in range(i + 1, n_rater)
                        ]
                        pair_labels = [f"{selected_cols[i]} vs {selected_cols[j]}" for i, j in pairs]
                        chosen_pair = st.selectbox("Pasangan rater:", pair_labels, key="ba_pair")
                        ci_idx = pair_labels.index(chosen_pair)
                        ci_i, ci_j = pairs[ci_idx]
                        ba2 = plot_bland_altman(df_icc, ci_i, ci_j)
                        if ba2:
                            st.plotly_chart(ba2[0], use_container_width=True)

        # Scatter matrix
        if n_rater >= 2:
            fig_scatter = plot_rater_agreement(df_icc)
            if fig_scatter:
                st.plotly_chart(fig_scatter, use_container_width=True)

    # ── Tab 3: ANOVA Tabel ────────────────────────────────────────────────────
    with tab3:
        st.markdown("#### Tabel ANOVA Dua Arah (Dasar Perhitungan ICC)")
        st.markdown(
            "Tabel ANOVA ini menunjukkan dekomposisi varians yang menjadi dasar "
            "perhitungan semua model ICC dua arah (Two-Way Random & Mixed)."
        )

        def _style_anova_p(val):
            try:
                v = float(val)
                return "color:#3B6D11; font-weight:600" if v < 0.05 else ""
            except (TypeError, ValueError):
                return ""

        st.dataframe(
            anova_tbl.style
            .map(_style_anova_p, subset=["p-value"])
            .format({
                "SS": "{:.4f}", "MS": lambda v: f"{v:.4f}" if pd.notna(v) else "–",
                "F":  lambda v: f"{v:.4f}" if pd.notna(v) else "–",
                "p-value": lambda v: f"{v:.4f}" if pd.notna(v) else "–",
            }, na_rep="–"),
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("""
**Keterangan:**
- **SS** = Sum of Squares (jumlah kuadrat)
- **MS** = Mean Square (MS = SS / df)
- **F** = F-ratio (MS antar / MS error)
- Sumber: Shrout & Fleiss (1979), McGraw & Wong (1996)
        """)

        # Statistik deskriptif per rater
        st.markdown("#### Statistik Deskriptif per Rater / Sesi")
        desc_rater = df_icc.describe().T.reset_index().rename(columns={"index": "Rater/Sesi"})
        st.dataframe(desc_rater.round(4), use_container_width=True, hide_index=True)

    # ── Tab 4: Interpretasi AI ────────────────────────────────────────────────
    with tab4:
        st.markdown("#### 🤖 Interpretasi AI — Hasil Reliabilitas ICC")

        if not ai_enabled:
            st.info("💡 Masukkan API Key di sidebar untuk mengaktifkan interpretasi AI.")
        else:
            cache_key = f"icc_ai_{','.join(selected_cols)}_{n_subj}"
            if cache_key not in st.session_state:
                st.session_state[cache_key] = None

            if st.button("🤖 Generate Interpretasi AI", key="btn_icc_ai"):
                with st.spinner("🤖 AI sedang menganalisis hasil ICC…"):
                    from utils.ai_helpers import ai_interpret_icc
                    icc_summary = icc_df[["Model", "Tipe", "ICC", "CI_Lower",
                                          "CI_Upper", "p_value"]].to_dict(orient="records")
                    anova_summary = anova_tbl.to_dict(orient="records")
                    ai_text = ai_interpret_icc(
                        icc_summary=icc_summary,
                        anova_summary=anova_summary,
                        n_subj=n_subj,
                        n_rater=n_rater,
                        rater_names=selected_cols,
                        use_type=use_type,
                        api_key=api_key,
                        provider=ai_provider,
                    )
                    st.session_state[cache_key] = ai_text

            if st.session_state[cache_key]:
                st.markdown(
                    '<span class="rs-ai-badge">✨ AI Interpretasi</span>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f'<div class="rs-ai-narasi">{st.session_state[cache_key]}</div>',
                    unsafe_allow_html=True,
                )

    # ── 6. Simpan ke session_state untuk export ───────────────────────────────
    st.session_state["icc_result"] = {
        "icc_df":       icc_df.to_dict(orient="records"),
        "anova_tbl":    anova_tbl.to_dict(orient="records"),
        "n_subj":       n_subj,
        "n_rater":      n_rater,
        "rater_names":  selected_cols,
        "use_type":     use_type,
        "rec_model":    rec_model,
        "rec_tipe":     rec_tipe,
    }

    # Simpan juga AI text terbaru ke session_state untuk laporan
    ai_cached = st.session_state.get(
        f"icc_ai_{','.join(selected_cols)}_{n_subj}"
    )
    if ai_cached:
        st.session_state["icc_result"]["ai_text"] = ai_cached

    st.markdown("""
    <div class="rs-footer" style="margin-top:1.5rem;">
        📚 <b>Referensi:</b> Koo, T.K. & Mae, M.Y. (2016). <i>J Chiropr Med</i>, 15(2), 155–163. ·
        Shrout, P.E. & Fleiss, J.L. (1979). <i>Psychol Bull</i>, 86(2), 420–428. ·
        McGraw, K.O. & Wong, S.P. (1996). <i>Psychol Methods</i>, 1(1), 30–46.
    </div>
    """, unsafe_allow_html=True)
