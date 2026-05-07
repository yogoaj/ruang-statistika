"""
modules/uji_asumsi.py — Uji Asumsi Pra-Analisis (Free)
Ruang Statistika v4.0

Memandu pengguna sebelum memilih metode analisis:
  - Uji normalitas multivariat (Mardia's test)
  - Uji homogenitas varians (Levene, Bartlett)
  - Uji linieritas (Ramsey RESET, scatter matrix)
  - Rekomendasi otomatis metode analisis yang tepat
"""

import numpy as np
import pandas as pd
import streamlit as st
from scipy import stats
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

from utils.stats_helpers import require_data, require_cols, ss_get
from utils.ai_helpers import call_ai_api

# ── Warna konsisten dengan codebase ──────────────────────────────────────────
BLUE  = "#185FA5"
NAVY  = "#0c2340"
GREEN = "#3B6D11"
RED   = "#A32D2D"
RED2  = "#E24B4A"
PURPLE = "#6B21A8"


# ═════════════════════════════════════════════════════════════════════════════
# KOMPUTASI — Mardia's Multivariate Normality Test
# ═════════════════════════════════════════════════════════════════════════════

def mardia_test(X: np.ndarray) -> dict:
    """
    Mardia's test untuk normalitas multivariat.
    Menghitung skewness dan kurtosis multivariat.

    Returns dict: skewness, kurtosis, p_skew, p_kurt, normal_skew, normal_kurt
    """
    n, p = X.shape
    if n < 20:
        return {"error": "Minimal 20 observasi diperlukan untuk Mardia's test."}

    # Center data
    X_c = X - X.mean(axis=0)

    # Covariance matrix (MLE)
    S = np.cov(X_c.T, ddof=0)

    try:
        S_inv = np.linalg.inv(S)
    except np.linalg.LinAlgError:
        return {"error": "Matriks kovarians singular — ada kolom yang berkorelasi sempurna."}

    # Mahalanobis distances squared
    D = X_c @ S_inv @ X_c.T  # n x n matrix

    # Mardia's multivariate skewness: b1,p
    skewness = float(np.sum(D ** 3) / (n ** 2))

    # Mardia's multivariate kurtosis: b2,p
    kurtosis = float(np.sum(np.diag(D) ** 2) / n)

    # Test statistics
    # Skewness: kappa = n * b1,p / 6 ~ chi-squared with p(p+1)(p+2)/6 df
    df_skew = int(p * (p + 1) * (p + 2) / 6)
    stat_skew = n * skewness / 6.0
    p_skew = float(1 - stats.chi2.cdf(stat_skew, df_skew))

    # Kurtosis: z ~ standard normal
    expected_kurt = p * (p + 2)
    var_kurt = 8 * p * (p + 2) / n
    z_kurt = (kurtosis - expected_kurt) / np.sqrt(var_kurt)
    p_kurt = float(2 * (1 - stats.norm.cdf(abs(z_kurt))))

    return {
        "n":             n,
        "p":             p,
        "skewness":      round(skewness, 4),
        "kurtosis":      round(kurtosis, 4),
        "stat_skew":     round(stat_skew, 4),
        "df_skew":       df_skew,
        "p_skew":        round(p_skew, 4),
        "z_kurt":        round(z_kurt, 4),
        "p_kurt":        round(p_kurt, 4),
        "expected_kurt": round(expected_kurt, 4),
        "normal_skew":   p_skew > 0.05,
        "normal_kurt":   p_kurt > 0.05,
        "normal_overall": p_skew > 0.05 and p_kurt > 0.05,
    }


# ═════════════════════════════════════════════════════════════════════════════
# KOMPUTASI — Uji Homogenitas Varians
# ═════════════════════════════════════════════════════════════════════════════

def homogeneity_tests(df: pd.DataFrame, num_col: str, cat_col: str) -> dict:
    """
    Levene & Bartlett test untuk homogenitas varians antar kelompok.
    """
    groups = []
    group_labels = []
    zero_var_groups = []
    for name, grp in df.groupby(cat_col):
        vals = pd.to_numeric(grp[num_col], errors="coerce").dropna().values
        if len(vals) >= 2:
            groups.append(vals)
            group_labels.append(str(name))
            if float(vals.std(ddof=1)) == 0:
                zero_var_groups.append(str(name))

    if len(groups) < 2:
        return {"error": "Minimal 2 kelompok dengan data cukup diperlukan."}

    # Levene's test (robust terhadap non-normalitas)
    lev_stat, lev_p = stats.levene(*groups, center="median")

    # Bartlett's test — requires non-zero variance in every group.
    # scipy >= 1.14 / Python 3.14 raises IndexError when any group has std=0.
    # Fall back gracefully instead of crashing.
    bart_stat, bart_p = None, None
    bart_error = None
    if zero_var_groups:
        bart_error = (
            f"Bartlett tidak dapat dijalankan: kelompok "
            f"{', '.join(zero_var_groups)} memiliki varians = 0 "
            f"(semua nilai identik). Gunakan hasil Levene sebagai acuan."
        )
    else:
        try:
            bart_stat, bart_p = stats.bartlett(*groups)
        except Exception as e:
            bart_error = f"Bartlett gagal: {e}. Gunakan hasil Levene sebagai acuan."

    # Deskriptif per kelompok
    group_stats = []
    for label, g in zip(group_labels, groups):
        group_stats.append({
            "Kelompok": label,
            "N":        len(g),
            "Mean":     round(float(g.mean()), 4),
            "Std Dev":  round(float(g.std(ddof=1)), 4),
            "Varians":  round(float(g.var(ddof=1)), 4),
        })

    return {
        "levene_stat":      round(float(lev_stat), 4),
        "levene_p":         round(float(lev_p), 4),
        "bartlett_stat":    round(float(bart_stat), 4) if bart_stat is not None else None,
        "bartlett_p":       round(float(bart_p), 4)    if bart_p   is not None else None,
        "homogen_levene":   lev_p > 0.05,
        "homogen_bartlett": (bart_p > 0.05) if bart_p is not None else None,
        "bart_error":       bart_error,
        "group_labels":     group_labels,
        "n_groups":         len(groups),
        "group_stats":      pd.DataFrame(group_stats),
    }


# ═════════════════════════════════════════════════════════════════════════════
# KOMPUTASI — Uji Linieritas (Ramsey RESET)
# ═════════════════════════════════════════════════════════════════════════════

def ramsey_reset_test(df: pd.DataFrame, y_col: str, x_col: str) -> dict:
    """
    Ramsey RESET test untuk uji linieritas hubungan Y ~ X.
    H0: hubungan linier (tidak ada misspecification).
    """
    import statsmodels.api as sm

    subset = df[[y_col, x_col]].apply(pd.to_numeric, errors="coerce").dropna()
    if len(subset) < 10:
        return {"error": "Minimal 10 observasi diperlukan untuk RESET test."}

    y = subset[y_col].values
    x = subset[x_col].values

    # Model linier dasar
    X_lin = sm.add_constant(x)
    model_lin = sm.OLS(y, X_lin).fit()
    y_hat = model_lin.fittedvalues

    # Model augmented dengan fitted values kuadrat & kubik (RESET)
    X_aug = sm.add_constant(
        np.column_stack([x, y_hat ** 2, y_hat ** 3])
    )
    model_aug = sm.OLS(y, X_aug).fit()

    # F-test: apakah koefisien y_hat^2 dan y_hat^3 secara bersama = 0
    n = len(y)
    k_lin = X_lin.shape[1]
    k_aug = X_aug.shape[1]

    rss_lin = model_lin.ssr
    rss_aug = model_aug.ssr

    if rss_aug == 0 or rss_lin == 0:
        return {"error": "RSS nol — data mungkin terlalu sempurna atau terlalu sedikit."}

    df1 = k_aug - k_lin
    df2 = n - k_aug
    if df2 <= 0:
        return {"error": "Degree of freedom tidak cukup."}

    F_stat = ((rss_lin - rss_aug) / df1) / (rss_aug / df2)
    p_value = float(1 - stats.f.cdf(F_stat, df1, df2))

    r2_lin = float(model_lin.rsquared)
    correlation = float(np.corrcoef(x, y)[0, 1])

    return {
        "y_col":      y_col,
        "x_col":      x_col,
        "n":          n,
        "r":          round(correlation, 4),
        "r2":         round(r2_lin, 4),
        "F_stat":     round(float(F_stat), 4),
        "df1":        df1,
        "df2":        df2,
        "p_value":    round(p_value, 4),
        "linier":     p_value > 0.05,
        "y_hat":      y_hat.tolist(),
        "x_vals":     x.tolist(),
        "y_vals":     y.tolist(),
        "resid":      model_lin.resid.tolist(),
    }


# ═════════════════════════════════════════════════════════════════════════════
# VISUALISASI
# ═════════════════════════════════════════════════════════════════════════════

def plot_mahalanobis_qq(X: np.ndarray, p: int) -> go.Figure:
    """Chi-squared Q-Q plot untuk Mahalanobis distances (normalitas multivariat)."""
    n = len(X)
    X_c = X - X.mean(axis=0)
    S = np.cov(X_c.T, ddof=0)
    try:
        S_inv = np.linalg.inv(S)
        maha_sq = np.array([X_c[i] @ S_inv @ X_c[i] for i in range(n)])
    except np.linalg.LinAlgError:
        return go.Figure()

    maha_sorted = np.sort(maha_sq)
    quantiles = np.array([
        stats.chi2.ppf((i - 0.5) / n, df=p)
        for i in range(1, n + 1)
    ])

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=quantiles, y=maha_sorted, mode="markers",
        marker=dict(color=BLUE, size=5, opacity=0.7),
        name="Mahalanobis D²"
    ))
    ref_max = max(quantiles.max(), maha_sorted.max())
    fig.add_trace(go.Scatter(
        x=[0, ref_max], y=[0, ref_max], mode="lines",
        line=dict(color=RED2, dash="dash", width=2), name="Garis Referensi"
    ))
    fig.update_layout(
        title=f"Chi-squared Q-Q Plot (Mahalanobis D², df={p})",
        xaxis_title=f"Kuantil Chi-squared (df={p})",
        yaxis_title="Mahalanobis D² (terurut)",
        template="plotly_white", height=380,
        margin=dict(l=30, r=30, t=50, b=30),
    )
    return fig


def plot_variance_bars(group_stats_df: pd.DataFrame) -> go.Figure:
    """Bar chart varians per kelompok."""
    colors = [BLUE] * len(group_stats_df)
    fig = go.Figure(go.Bar(
        x=group_stats_df["Kelompok"].astype(str),
        y=group_stats_df["Varians"],
        marker_color=colors,
        text=group_stats_df["Varians"].round(3),
        textposition="outside",
    ))
    fig.update_layout(
        title="Varians per Kelompok",
        xaxis_title="Kelompok", yaxis_title="Varians",
        template="plotly_white", height=340,
        margin=dict(l=30, r=30, t=50, b=30),
    )
    return fig


def plot_scatter_linearity(result: dict) -> go.Figure:
    """Scatter plot dengan garis regresi untuk uji linieritas."""
    x_vals = result["x_vals"]
    y_vals = result["y_vals"]
    y_hat  = result["y_hat"]

    # Sort by x for smooth line
    order = np.argsort(x_vals)
    x_s   = np.array(x_vals)[order]
    yh_s  = np.array(y_hat)[order]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x_vals, y=y_vals, mode="markers",
        marker=dict(color=BLUE, size=6, opacity=0.6),
        name="Data"
    ))
    fig.add_trace(go.Scatter(
        x=x_s.tolist(), y=yh_s.tolist(), mode="lines",
        line=dict(color=RED2, width=2), name="Garis Regresi"
    ))
    r = result.get("r", 0)
    p = result.get("p_value", 1)
    fig.update_layout(
        title=(
            f"{result['x_col']} vs {result['y_col']} | "
            f"r = {r:.3f}, RESET p = {p:.4f}"
        ),
        xaxis_title=result["x_col"],
        yaxis_title=result["y_col"],
        template="plotly_white", height=360,
        margin=dict(l=30, r=30, t=50, b=30),
    )
    return fig


def plot_residual_linearity(result: dict) -> go.Figure:
    """Plot residual vs fitted untuk deteksi non-linieritas."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=result["y_hat"], y=result["resid"],
        mode="markers",
        marker=dict(color=BLUE, size=5, opacity=0.65),
        name="Residual"
    ))
    fig.add_hline(y=0, line_dash="dash", line_color=RED2)
    fig.update_layout(
        title="Residual vs Fitted — Deteksi Non-Linieritas",
        xaxis_title="Fitted Values", yaxis_title="Residual",
        template="plotly_white", height=340,
        margin=dict(l=30, r=30, t=50, b=30),
    )
    return fig


def plot_scatter_matrix(df: pd.DataFrame, cols: list) -> go.Figure:
    """Scatter matrix untuk inspeksi linieritas antar variabel."""
    display_cols = cols[:6]  # batasi 6 kolom agar tidak terlalu padat
    fig = px.scatter_matrix(
        df[display_cols].apply(pd.to_numeric, errors="coerce").dropna(),
        dimensions=display_cols,
        title=f"Scatter Matrix — {len(display_cols)} Variabel",
        color_discrete_sequence=[BLUE],
        opacity=0.5,
    )
    fig.update_traces(marker=dict(size=3))
    fig.update_layout(
        template="plotly_white",
        height=520,
        margin=dict(l=10, r=10, t=50, b=10),
    )
    return fig


# ═════════════════════════════════════════════════════════════════════════════
# ENGINE REKOMENDASI
# ═════════════════════════════════════════════════════════════════════════════

from typing import Optional, List

def build_recommendation(
    mardia_result: Optional[dict],
    homo_results: List[dict],
    linearity_results: List[dict],
    norm_univariate: Optional[pd.DataFrame],
    n_rows: int,
    alpha: float = 0.05,
) -> dict:
    """
    Bangun rekomendasi analisis berdasarkan semua hasil uji asumsi.

    Returns dict:
        level      : 'parametrik' | 'non-parametrik' | 'campuran'
        rekomendasi: list string
        peringatan : list string
        skor_lulus : int (0-4, dari 4 uji)
        detail     : dict ringkasan per uji
    """
    rekomendasi = []
    peringatan  = []
    detail      = {}
    skor_lulus  = 0
    total_uji   = 0

    # ── 1. Normalitas univariat ───────────────────────────────────────────
    if norm_univariate is not None and not norm_univariate.empty:
        total_uji += 1
        n_normal   = norm_univariate["Normal (α=0.05)"].str.contains("Ya").sum()
        n_total    = len(norm_univariate)
        pct_normal = n_normal / n_total * 100 if n_total > 0 else 0

        detail["normalitas_univariat"] = {
            "n_variabel": n_total,
            "n_normal": int(n_normal),
            "pct_normal": round(pct_normal, 1),
            "lulus": pct_normal >= 70,
        }

        if pct_normal >= 70:
            skor_lulus += 1
        else:
            non_norm_cols = norm_univariate[
                norm_univariate["Normal (α=0.05)"].str.contains("Tidak")
            ]["Variabel"].tolist()
            peringatan.append(
                f"⚠️ {len(non_norm_cols)} variabel tidak berdistribusi normal: "
                f"{', '.join(non_norm_cols[:5])}."
            )

        # Ukuran sampel besar → CLT berlaku
        if n_rows >= 100:
            peringatan.append(
                f"ℹ️ N = {n_rows} ≥ 100: Central Limit Theorem berlaku — "
                "uji parametrik tetap valid meskipun data tidak normal sempurna."
            )

    # ── 2. Normalitas multivariat (Mardia) ────────────────────────────────
    if mardia_result and "error" not in mardia_result:
        total_uji += 1
        mv_ok = mardia_result.get("normal_overall", False)
        detail["normalitas_multivariat"] = {
            "skewness": mardia_result["skewness"],
            "kurtosis": mardia_result["kurtosis"],
            "p_skew":   mardia_result["p_skew"],
            "p_kurt":   mardia_result["p_kurt"],
            "lulus":    mv_ok,
        }
        if mv_ok:
            skor_lulus += 1
        else:
            if not mardia_result.get("normal_skew"):
                peringatan.append(
                    f"⚠️ Skewness multivariat signifikan (p = {mardia_result['p_skew']:.4f}) "
                    "— distribusi data tidak simetris secara multivariat."
                )
            if not mardia_result.get("normal_kurt"):
                peringatan.append(
                    f"⚠️ Kurtosis multivariat signifikan (p = {mardia_result['p_kurt']:.4f}) "
                    "— ekor distribusi data tidak sesuai normal."
                )

    # ── 3. Homogenitas varians ────────────────────────────────────────────
    n_homo_ok = 0
    n_homo_total = 0
    for h in homo_results:
        if "error" in h:
            continue
        n_homo_total += 1
        if h.get("homogen_levene"):
            n_homo_ok += 1
        else:
            peringatan.append(
                f"⚠️ Varians tidak homogen (Levene p = {h['levene_p']:.4f}) "
                f"— {h['n_groups']} kelompok."
            )

    if n_homo_total > 0:
        total_uji += 1
        homo_ok = (n_homo_ok == n_homo_total)
        detail["homogenitas"] = {
            "n_uji":  n_homo_total,
            "n_lulus": n_homo_ok,
            "lulus":  homo_ok,
        }
        if homo_ok:
            skor_lulus += 1

    # ── 4. Linieritas ─────────────────────────────────────────────────────
    n_lin_ok    = 0
    n_lin_total = 0
    for lin in linearity_results:
        if "error" in lin:
            continue
        n_lin_total += 1
        if lin.get("linier"):
            n_lin_ok += 1
        else:
            peringatan.append(
                f"⚠️ Hubungan {lin['x_col']} → {lin['y_col']} tidak linier "
                f"(RESET p = {lin['p_value']:.4f}) — pertimbangkan transformasi atau regresi non-linier."
            )

    if n_lin_total > 0:
        total_uji += 1
        lin_ok = (n_lin_ok == n_lin_total)
        detail["linieritas"] = {
            "n_uji":   n_lin_total,
            "n_lulus": n_lin_ok,
            "lulus":   lin_ok,
        }
        if lin_ok:
            skor_lulus += 1

    # ── Keputusan level analisis ──────────────────────────────────────────
    pct_lulus = skor_lulus / total_uji * 100 if total_uji > 0 else 0

    if pct_lulus >= 75:
        level = "parametrik"
        rekomendasi += [
            "✅ **Regresi Linier (OLS / OLS+)** — asumsi linieritas & normalitas terpenuhi.",
            "✅ **ANOVA** — varians homogen antar kelompok.",
            "✅ **Korelasi Pearson** — distribusi mendekati normal.",
            "✅ **Analisis Mediasi & Moderasi** — cocok untuk data parametrik.",
        ]
    elif pct_lulus >= 50:
        level = "campuran"
        rekomendasi += [
            "🟡 **Regresi OLS+** dengan pemeriksaan asumsi klasik (VIF, Durbin-Watson, White test).",
            "🟡 **Kruskal-Wallis** sebagai alternatif ANOVA jika ada kelompok dengan varians tidak homogen.",
            "🟡 **Korelasi Spearman** sebagai alternatif Pearson untuk variabel tidak normal.",
            "🟡 **Transformasi data** (log, sqrt, Box-Cox) sebelum analisis parametrik.",
        ]
        peringatan.insert(0,
            "⚠️ Sebagian asumsi tidak terpenuhi. Lanjutkan dengan hati-hati atau gunakan alternatif non-parametrik."
        )
    else:
        level = "non-parametrik"
        rekomendasi += [
            "🔴 **Kruskal-Wallis** — pengganti ANOVA untuk data tidak normal/tidak homogen.",
            "🔴 **Mann-Whitney U** — pengganti t-test independen.",
            "🔴 **Spearman / Kendall** — korelasi non-parametrik.",
            "🔴 **Regresi Robust** — jika regresi linier tetap digunakan dengan pelanggaran asumsi.",
            "🔴 **Bootstrap** — estimasi CI tanpa asumsi distribusi.",
        ]
        peringatan.insert(0,
            "🚨 **Data Anda sebaiknya menggunakan uji non-parametrik** — "
            "asumsi parametrik banyak yang tidak terpenuhi."
        )

    return {
        "level":       level,
        "rekomendasi": rekomendasi,
        "peringatan":  peringatan,
        "skor_lulus":  skor_lulus,
        "total_uji":   total_uji,
        "pct_lulus":   round(pct_lulus, 1),
        "detail":      detail,
    }


# ═════════════════════════════════════════════════════════════════════════════
# UI HELPERS
# ═════════════════════════════════════════════════════════════════════════════

def _render_badge(text: str, color: str, bg: str):
    st.markdown(
        f'<span style="background:{bg};color:{color};padding:3px 12px;'
        f'border-radius:20px;font-size:0.78rem;font-weight:600;">{text}</span>',
        unsafe_allow_html=True,
    )


def _render_result_box(label: str, value: str, is_ok: bool, extra: str = ""):
    color  = GREEN if is_ok else RED
    icon   = "✓" if is_ok else "✗"
    status = "Terpenuhi" if is_ok else "Tidak Terpenuhi"
    st.markdown(
        f'<div class="rs-narasi" style="border-left-color:{color};">'
        f'<b>{label}</b>: {value}<br/>'
        f'<span style="color:{color};font-weight:600;">{icon} {status}</span>'
        f'{"<br/><span style=\'font-size:0.82rem;color:#5f8ab5;\'>" + extra + "</span>" if extra else ""}'
        f'</div>',
        unsafe_allow_html=True,
    )


def _render_rekomendasi_card(rec: dict):
    """Render kartu rekomendasi besar di bagian bawah."""
    level   = rec["level"]
    skor    = rec["skor_lulus"]
    total   = rec["total_uji"]
    pct     = rec["pct_lulus"]

    level_config = {
        "parametrik":    ("#3B6D11", "#eaf3de", "✅ Parametrik", "Semua asumsi terpenuhi"),
        "campuran":      ("#185FA5", "#e6f1fb", "🟡 Campuran",   "Sebagian asumsi terpenuhi"),
        "non-parametrik": ("#A32D2D", "#fcebeb", "🚨 Non-Parametrik", "Asumsi banyak dilanggar"),
    }
    col_txt, col_bg, label_txt, sub_txt = level_config.get(
        level, (NAVY, "#f7faff", level, "")
    )

    st.markdown(
        f"""
        <div style="background:{col_bg};border:2px solid {col_txt};border-radius:14px;
                    padding:1.5rem 1.8rem;margin:1rem 0;">
          <div style="font-size:1.25rem;font-weight:700;color:{col_txt};">
            {label_txt} &nbsp;
            <span style="font-size:0.85rem;font-weight:400;color:#5f8ab5;">
              ({skor}/{total} uji lulus, {pct}%)
            </span>
          </div>
          <div style="font-size:0.88rem;color:{col_txt};margin-top:4px;">{sub_txt}</div>
          <hr style="border-color:{col_txt};opacity:0.2;margin:12px 0;">
          <div style="font-size:0.9rem;color:#0c2340;font-weight:600;">
            📌 Metode analisis yang direkomendasikan:
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    for item in rec["rekomendasi"]:
        st.markdown(item)

    if rec["peringatan"]:
        st.markdown("---")
        for w in rec["peringatan"]:
            if w.startswith("🚨"):
                st.error(w)
            elif w.startswith("⚠️"):
                st.warning(w)
            else:
                st.info(w)


# ═════════════════════════════════════════════════════════════════════════════
# RENDER UTAMA
# ═════════════════════════════════════════════════════════════════════════════

def render(ctx: dict):
    alpha_level   = ctx["alpha_level"]
    ai_enabled    = ctx["ai_enabled"]
    api_key       = ctx["anthropic_api_key"]
    ai_provider   = ctx["ai_provider"]

    st.markdown(
        '<p class="rs-section-title">🔬 Uji Asumsi Pra-Analisis</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="rs-section-sub">Periksa asumsi data sebelum memilih metode analisis — '
        'normalitas multivariat, homogenitas varians, dan linieritas.</p>',
        unsafe_allow_html=True,
    )

    df = require_data()
    if df is None:
        st.stop()

    cols = require_cols(df)
    if cols is None or len(cols) < 2:
        st.warning("⚠️ Pilih minimal 2 kolom numerik untuk uji asumsi.")
        st.stop()

    num_df = df[cols].apply(pd.to_numeric, errors="coerce")

    # ── Sidebar konfigurasi ───────────────────────────────────────────────
    st.markdown("#### ⚙️ Konfigurasi Pengujian")

    cfg1, cfg2 = st.columns(2)
    with cfg1:
        run_mardia    = st.checkbox("🔵 Uji Normalitas Multivariat (Mardia)", value=True)
        run_homogen   = st.checkbox("🟢 Uji Homogenitas Varians (Levene & Bartlett)", value=True)
    with cfg2:
        run_linearity = st.checkbox("🟡 Uji Linieritas (Ramsey RESET)", value=True)
        run_scatter   = st.checkbox("🔷 Scatter Matrix (Inspeksi Visual)", value=True)

    # Pilihan kolom untuk uji homogenitas (butuh variabel kategorik)
    cat_cols_all = df.select_dtypes(include=["object", "category"]).columns.tolist()
    cat_cols_numeric_binary = [
        c for c in df.columns
        if c not in cols and df[c].nunique() <= 10
    ]
    cat_candidates = cat_cols_all + [c for c in cat_cols_numeric_binary if c not in cat_cols_all]

    homo_cat_col = None
    homo_num_col = None
    if run_homogen:
        st.markdown("**Konfigurasi Homogenitas:**")
        hcol1, hcol2 = st.columns(2)
        with hcol1:
            if cat_candidates:
                homo_cat_col = st.selectbox(
                    "Variabel Kelompok (kategorik)",
                    cat_candidates,
                    help="Kolom yang membagi data ke dalam kelompok"
                )
            else:
                st.info("ℹ️ Tidak ada kolom kategorik terdeteksi. Homogenitas dilewati.")
        with hcol2:
            if cat_candidates:
                homo_num_col = st.selectbox(
                    "Variabel Numerik yang diuji",
                    cols,
                    help="Varians variabel ini yang akan dibandingkan antar kelompok"
                )

    # Pilihan pasangan variabel untuk linieritas
    lin_pairs = []
    if run_linearity and len(cols) >= 2:
        st.markdown("**Konfigurasi Linieritas:**")
        lin1, lin2 = st.columns(2)
        with lin1:
            y_lin = st.selectbox("Variabel Y (dependen)", cols, index=0, key="lin_y")
        with lin2:
            x_options = [c for c in cols if c != y_lin]
            if x_options:
                x_lin = st.multiselect(
                    "Variabel X (independen) — pilih 1-3",
                    x_options,
                    default=[x_options[0]],
                    key="lin_x",
                )
                lin_pairs = [(y_lin, x) for x in x_lin[:3]]

    st.markdown("---")

    if not st.button("🚀 Jalankan Uji Asumsi", type="primary", use_container_width=True):
        st.info("💡 Klik tombol di atas untuk memulai pengujian asumsi.")
        return

    # ═══════════════════════════════════════════════════════════════════════
    # EKSEKUSI PENGUJIAN
    # ═══════════════════════════════════════════════════════════════════════

    prog   = st.progress(0)
    status = st.empty()

    mardia_result     = None
    homo_results      = []
    linearity_results = []
    norm_df_uni       = None

    # ── Normalitas univariat (dari stats_helpers) ─────────────────────────
    status.caption("⏳ Menghitung normalitas univariat…")
    from utils.stats_helpers import normality_test
    norm_df_uni = normality_test(df, cols)
    prog.progress(15)

    # ══════════════════════════════════════════════════════════════════════
    # TAB LAYOUT
    # ══════════════════════════════════════════════════════════════════════
    tabs_labels = ["📊 Normalitas Multivariat", "📐 Homogenitas Varians",
                   "📈 Linieritas", "🎯 Rekomendasi"]
    tab_norm, tab_homo, tab_lin, tab_rek = st.tabs(tabs_labels)

    # ══════════════════════════════════════════════════════════════════════
    # TAB 1: NORMALITAS MULTIVARIAT
    # ══════════════════════════════════════════════════════════════════════
    with tab_norm:
        st.markdown("### 🔵 Normalitas Univariat — Shapiro-Wilk")
        st.caption(f"H₀: data berdistribusi normal | α = {alpha_level}")

        if norm_df_uni is not None and not norm_df_uni.empty:
            # Warnai baris tidak normal
            def _color_normal(val):
                if "Ya" in str(val):
                    return "color: #3B6D11; font-weight: 600"
                elif "Tidak" in str(val):
                    return "color: #A32D2D; font-weight: 600"
                return ""
            st.dataframe(
                norm_df_uni.style.applymap(_color_normal, subset=["Normal (α=0.05)"]),
                use_container_width=True, hide_index=True
            )
            n_normal   = norm_df_uni["Normal (α=0.05)"].str.contains("Ya").sum()
            n_total    = len(norm_df_uni)
            pct_normal = round(n_normal / n_total * 100, 1)

            col_s1, col_s2, col_s3 = st.columns(3)
            with col_s1:
                st.markdown(f'<div class="rs-metric"><div class="rs-metric-label">Total Variabel</div>'
                            f'<div class="rs-metric-value">{n_total}</div></div>',
                            unsafe_allow_html=True)
            with col_s2:
                st.markdown(f'<div class="rs-metric"><div class="rs-metric-label">Normal</div>'
                            f'<div class="rs-metric-value" style="color:{GREEN}">{n_normal}</div></div>',
                            unsafe_allow_html=True)
            with col_s3:
                col_pct = GREEN if pct_normal >= 70 else RED
                st.markdown(f'<div class="rs-metric"><div class="rs-metric-label">% Normal</div>'
                            f'<div class="rs-metric-value" style="color:{col_pct}">{pct_normal}%</div></div>',
                            unsafe_allow_html=True)

        st.markdown("---")

        if run_mardia:
            st.markdown("### 🔵 Normalitas Multivariat — Mardia's Test")
            st.caption(
                "Mardia's test menguji apakah distribusi **bersama** semua variabel "
                "mengikuti distribusi normal multivariat. "
                "H₀: skewness dan kurtosis multivariat sesuai normal."
            )

            status.caption("⏳ Menghitung Mardia's test…")
            clean_df = num_df.dropna()

            if len(clean_df) < 20:
                st.warning("⚠️ Sampel terlalu kecil untuk Mardia's test (minimal N = 20).")
            elif len(cols) < 2:
                st.warning("⚠️ Minimal 2 variabel diperlukan.")
            else:
                X = clean_df.values
                mardia_result = mardia_test(X)

                if "error" in mardia_result:
                    st.error(f"❌ {mardia_result['error']}")
                else:
                    # Tabel hasil
                    mardia_df = pd.DataFrame([{
                        "Statistik":           "Mardia's Skewness",
                        "Nilai":               mardia_result["skewness"],
                        "Statistik Uji":       mardia_result["stat_skew"],
                        "df":                  mardia_result["df_skew"],
                        "p-value":             mardia_result["p_skew"],
                        f"Normal (α={alpha_level})": "Ya ✓" if mardia_result["normal_skew"] else "Tidak ✗",
                    }, {
                        "Statistik":           "Mardia's Kurtosis",
                        "Nilai":               mardia_result["kurtosis"],
                        "Statistik Uji":       mardia_result["z_kurt"],
                        "df":                  "–",
                        "p-value":             mardia_result["p_kurt"],
                        f"Normal (α={alpha_level})": "Ya ✓" if mardia_result["normal_kurt"] else "Tidak ✗",
                    }])
                    st.dataframe(mardia_df, use_container_width=True, hide_index=True)

                    # Kesimpulan
                    overall_ok = mardia_result["normal_overall"]
                    _render_result_box(
                        "Normalitas Multivariat (Mardia)",
                        f"p_skew = {mardia_result['p_skew']:.4f}, "
                        f"p_kurt = {mardia_result['p_kurt']:.4f}",
                        overall_ok,
                        extra=f"N = {mardia_result['n']}, p variabel = {mardia_result['p']}"
                    )

                    st.markdown("<br/>", unsafe_allow_html=True)

                    # Chi-squared Q-Q plot
                    st.markdown("**Chi-squared Q-Q Plot (Mahalanobis D²)**")
                    st.caption(
                        "Titik yang mengikuti garis diagonal mengindikasikan "
                        "normalitas multivariat. Penyimpangan di ekor menunjukkan outlier atau distribusi ekor berat."
                    )
                    fig_qq = plot_mahalanobis_qq(X, mardia_result["p"])
                    st.plotly_chart(fig_qq, use_container_width=True)

        prog.progress(35)
        status.caption("")

    # ══════════════════════════════════════════════════════════════════════
    # TAB 2: HOMOGENITAS VARIANS
    # ══════════════════════════════════════════════════════════════════════
    with tab_homo:
        st.markdown("### 🟢 Uji Homogenitas Varians")
        st.markdown(
            '<p class="rs-section-sub">Levene & Bartlett test — menguji apakah varians '
            'sama di semua kelompok (homoskedastisitas antar grup).</p>',
            unsafe_allow_html=True,
        )

        if not run_homogen or homo_cat_col is None or homo_num_col is None:
            st.info("ℹ️ Pilih variabel kelompok dan numerik di konfigurasi, lalu jalankan ulang.")
        else:
            status.caption("⏳ Menghitung homogenitas varians…")
            h_result = homogeneity_tests(df, homo_num_col, homo_cat_col)

            if "error" in h_result:
                st.error(f"❌ {h_result['error']}")
            else:
                homo_results.append(h_result)

                # Tabel hasil uji
                bart_stat_disp  = h_result["bartlett_stat"]
                bart_p_disp     = h_result["bartlett_p"]
                bart_error_msg  = h_result.get("bart_error")
                bart_homogen    = h_result["homogen_bartlett"]

                homo_df = pd.DataFrame([{
                    "Uji":        "Levene (center=median)",
                    "Statistik":  h_result["levene_stat"],
                    "p-value":    h_result["levene_p"],
                    "Homogen?":   "Ya ✓" if h_result["homogen_levene"] else "Tidak ✗",
                    "Catatan":    "Robust terhadap non-normalitas",
                }, {
                    "Uji":        "Bartlett",
                    "Statistik":  bart_stat_disp if bart_stat_disp is not None else "N/A",
                    "p-value":    bart_p_disp    if bart_p_disp    is not None else "N/A",
                    "Homogen?":   ("Ya ✓" if bart_homogen else "Tidak ✗") if bart_homogen is not None else "N/A",
                    "Catatan":    bart_error_msg or "Sensitif terhadap non-normalitas",
                }])
                st.dataframe(homo_df, use_container_width=True, hide_index=True)

                if bart_error_msg:
                    st.warning(f"⚠️ {bart_error_msg}")

                # Kesimpulan utama dari Levene (lebih robust)
                bart_p_str = f"{bart_p_disp:.4f}" if bart_p_disp is not None else "N/A"
                _render_result_box(
                    f"Homogenitas Varians: {homo_num_col} per {homo_cat_col}",
                    f"Levene p = {h_result['levene_p']:.4f} | "
                    f"Bartlett p = {bart_p_str}",
                    h_result["homogen_levene"],
                    extra=f"{h_result['n_groups']} kelompok: {', '.join(h_result['group_labels'])}"
                )

                # Statistik per kelompok
                st.markdown("<br/>", unsafe_allow_html=True)
                st.markdown("**Statistik Deskriptif Per Kelompok:**")
                st.dataframe(h_result["group_stats"], use_container_width=True, hide_index=True)

                # Bar chart varians
                fig_var = plot_variance_bars(h_result["group_stats"])
                st.plotly_chart(fig_var, use_container_width=True)

                if not h_result["homogen_levene"]:
                    st.warning(
                        "💡 Varians tidak homogen → pertimbangkan **Welch's t-test** (2 kelompok) "
                        "atau **Kruskal-Wallis** (≥ 3 kelompok) sebagai alternatif ANOVA standar."
                    )
                else:
                    st.success("✅ Varians homogen — ANOVA standar dan t-test dapat digunakan.")

        prog.progress(55)

    # ══════════════════════════════════════════════════════════════════════
    # TAB 3: LINIERITAS
    # ══════════════════════════════════════════════════════════════════════
    with tab_lin:
        st.markdown("### 🟡 Uji Linieritas — Ramsey RESET Test")
        st.markdown(
            '<p class="rs-section-sub">H₀: hubungan antar variabel bersifat linier. '
            'p > 0.05 → asumsi linieritas terpenuhi.</p>',
            unsafe_allow_html=True,
        )

        if not run_linearity or not lin_pairs:
            st.info("ℹ️ Pilih pasangan variabel di konfigurasi, lalu jalankan ulang.")
        else:
            status.caption("⏳ Menjalankan Ramsey RESET test…")

            for y_col, x_col in lin_pairs:
                st.markdown(f"#### {x_col} → {y_col}")
                lin_result = ramsey_reset_test(df, y_col, x_col)

                if "error" in lin_result:
                    st.error(f"❌ {lin_result['error']}")
                    continue

                linearity_results.append(lin_result)

                # Tabel hasil
                lin_df = pd.DataFrame([{
                    "Pasangan":    f"{x_col} → {y_col}",
                    "r Pearson":   lin_result["r"],
                    "R²":          lin_result["r2"],
                    "F RESET":     lin_result["F_stat"],
                    "df1 / df2":   f"{lin_result['df1']} / {lin_result['df2']}",
                    "p RESET":     lin_result["p_value"],
                    "Linier?":     "Ya ✓" if lin_result["linier"] else "Tidak ✗",
                }])
                st.dataframe(lin_df, use_container_width=True, hide_index=True)

                _render_result_box(
                    f"Linieritas: {x_col} → {y_col}",
                    f"RESET F = {lin_result['F_stat']:.4f}, p = {lin_result['p_value']:.4f}",
                    lin_result["linier"],
                    extra=f"r = {lin_result['r']:.4f}, R² = {lin_result['r2']:.4f}, N = {lin_result['n']}"
                )

                # Plot scatter + garis regresi
                col_plot1, col_plot2 = st.columns(2)
                with col_plot1:
                    fig_sc = plot_scatter_linearity(lin_result)
                    st.plotly_chart(fig_sc, use_container_width=True)
                with col_plot2:
                    fig_res = plot_residual_linearity(lin_result)
                    st.plotly_chart(fig_res, use_container_width=True)

                if not lin_result["linier"]:
                    st.warning(
                        f"💡 Hubungan {x_col} → {y_col} tidak linier. "
                        "Coba: transformasi log/sqrt, regresi polinomial, atau GAM."
                    )
                st.markdown("---")

        # Scatter matrix
        if run_scatter:
            st.markdown("### 🔷 Scatter Matrix — Inspeksi Visual Linieritas")
            st.caption(
                "Inspeksi visual pola hubungan antar semua variabel. "
                "Pola melengkung atau berbentuk S mengindikasikan non-linieritas."
            )
            fig_sm = plot_scatter_matrix(num_df, cols)
            st.plotly_chart(fig_sm, use_container_width=True)

        prog.progress(80)

    # ══════════════════════════════════════════════════════════════════════
    # TAB 4: REKOMENDASI
    # ══════════════════════════════════════════════════════════════════════
    with tab_rek:
        st.markdown("### 🎯 Rekomendasi Metode Analisis")
        st.markdown(
            '<p class="rs-section-sub">Berdasarkan semua hasil uji asumsi di atas — '
            'sistem memberikan rekomendasi metode analisis yang tepat.</p>',
            unsafe_allow_html=True,
        )

        rec = build_recommendation(
            mardia_result=mardia_result,
            homo_results=homo_results,
            linearity_results=linearity_results,
            norm_univariate=norm_df_uni,
            n_rows=len(df),
            alpha=alpha_level,
        )

        # ── Skor dashboard ────────────────────────────────────────────────
        if rec["total_uji"] > 0:
            skor_cols = st.columns(4)
            metrics_data = [
                ("Uji Dijalankan",   str(rec["total_uji"]),  NAVY),
                ("Uji Lulus",        str(rec["skor_lulus"]), GREEN if rec["skor_lulus"] == rec["total_uji"] else RED),
                ("% Lulus",          f"{rec['pct_lulus']}%", GREEN if rec["pct_lulus"] >= 75 else RED),
                ("Level Analisis",   rec["level"].title(),   GREEN if rec["level"] == "parametrik" else (
                    "#185FA5" if rec["level"] == "campuran" else RED)),
            ]
            for col_m, (label, val, color) in zip(skor_cols, metrics_data):
                with col_m:
                    st.markdown(
                        f'<div class="rs-metric">'
                        f'<div class="rs-metric-label">{label}</div>'
                        f'<div class="rs-metric-value" style="color:{color};">{val}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

            st.markdown("<br/>", unsafe_allow_html=True)

        # ── Detail per uji ────────────────────────────────────────────────
        detail = rec["detail"]
        if detail:
            with st.expander("🔍 Detail Hasil Per Uji Asumsi", expanded=True):
                detail_rows = []
                labels_map = {
                    "normalitas_univariat":    "Normalitas Univariat (Shapiro-Wilk)",
                    "normalitas_multivariat":  "Normalitas Multivariat (Mardia)",
                    "homogenitas":             "Homogenitas Varians (Levene)",
                    "linieritas":              "Linieritas (Ramsey RESET)",
                }
                for key, info in detail.items():
                    lulus = info.get("lulus", False)
                    detail_rows.append({
                        "Uji Asumsi":   labels_map.get(key, key),
                        "Status":       "✓ Terpenuhi" if lulus else "✗ Tidak Terpenuhi",
                        "Keterangan":   _detail_summary(key, info),
                    })
                if detail_rows:
                    st.dataframe(
                        pd.DataFrame(detail_rows),
                        use_container_width=True,
                        hide_index=True,
                    )

        # ── Kartu rekomendasi utama ───────────────────────────────────────
        _render_rekomendasi_card(rec)

        # ── Panduan cepat ─────────────────────────────────────────────────
        st.markdown("---")
        with st.expander("📚 Panduan: Kapan Pakai Parametrik vs Non-Parametrik?"):
            guide_df = pd.DataFrame([
                {
                    "Kondisi":                 "Data normal, varians homogen",
                    "Uji Perbedaan":           "t-test / ANOVA",
                    "Uji Korelasi":            "Pearson",
                    "Regresi":                 "OLS / OLS+",
                },
                {
                    "Kondisi":                 "Data tidak normal, N kecil",
                    "Uji Perbedaan":           "Mann-Whitney / Kruskal-Wallis",
                    "Uji Korelasi":            "Spearman / Kendall",
                    "Regresi":                 "Robust Regression / Bootstrap",
                },
                {
                    "Kondisi":                 "Varians tidak homogen",
                    "Uji Perbedaan":           "Welch's t-test / Welch ANOVA",
                    "Uji Korelasi":            "Pearson (robust)",
                    "Regresi":                 "WLS (Weighted Least Squares)",
                },
                {
                    "Kondisi":                 "Hubungan tidak linier",
                    "Uji Perbedaan":           "–",
                    "Uji Korelasi":            "Spearman",
                    "Regresi":                 "Regresi Polinomial / GAM",
                },
                {
                    "Kondisi":                 "Data normal, N ≥ 100 (CLT berlaku)",
                    "Uji Perbedaan":           "t-test / ANOVA",
                    "Uji Korelasi":            "Pearson",
                    "Regresi":                 "OLS tetap valid",
                },
            ])
            st.dataframe(guide_df, use_container_width=True, hide_index=True)

        # ── AI Narasi ─────────────────────────────────────────────────────
        if ai_enabled:
            st.markdown("---")
            if st.button("🤖 Minta Interpretasi AI", use_container_width=True):
                with st.spinner("🤖 AI sedang menganalisis asumsi data Anda…"):
                    ai_text = _ai_interpret_assumptions(
                        rec, mardia_result, homo_results,
                        linearity_results, norm_df_uni,
                        api_key, ai_provider
                    )
                if ai_text and not ai_text.startswith(("❌", "⚠️")):
                    st.markdown(
                        f'<div class="rs-ai-narasi">'
                        f'<span class="rs-ai-badge">🤖 AI Interpretation</span><br/>'
                        f'{ai_text.replace(chr(10), "<br/>")}'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                    # Simpan ke cache
                    ai_cache = ss_get("ai_cache", {})
                    ai_cache["uji_asumsi"] = ai_text
                    st.session_state.ai_cache = ai_cache
                else:
                    st.error(ai_text or "Gagal mendapatkan interpretasi AI.")
        else:
            st.caption("💡 Masukkan API Key di sidebar untuk mendapatkan interpretasi AI.")

        # Simpan hasil ke session state
        st.session_state["asumsi_result"] = {
            "mardia":       mardia_result,
            "homo":         homo_results,
            "linearity":    linearity_results,
            "rekomendasi":  rec,
            "norm_univariate": norm_df_uni.to_dict() if norm_df_uni is not None else None,
        }

    prog.progress(100)
    status.empty()


# ═════════════════════════════════════════════════════════════════════════════
# HELPERS INTERNAL
# ═════════════════════════════════════════════════════════════════════════════

def _detail_summary(key: str, info: dict) -> str:
    """Buat string keterangan singkat untuk tabel detail."""
    if key == "normalitas_univariat":
        return (
            f"{info['n_normal']}/{info['n_variabel']} variabel normal "
            f"({info['pct_normal']}%)"
        )
    elif key == "normalitas_multivariat":
        return (
            f"Skewness p={info['p_skew']:.4f}, "
            f"Kurtosis p={info['p_kurt']:.4f}"
        )
    elif key == "homogenitas":
        return f"{info['n_lulus']}/{info['n_uji']} kelompok homogen"
    elif key == "linieritas":
        return f"{info['n_lulus']}/{info['n_uji']} pasangan linier"
    return ""


def _ai_interpret_assumptions(
    rec: dict,
    mardia_result: dict | None,
    homo_results: list[dict],
    linearity_results: list[dict],
    norm_df_uni: pd.DataFrame | None,
    api_key: str,
    provider: str,
) -> str:
    """Kirim ringkasan hasil uji asumsi ke AI untuk interpretasi naratif."""
    parts = []

    parts.append(
        f"Hasil uji asumsi pra-analisis:\n"
        f"Level analisis yang direkomendasikan: {rec['level'].upper()}\n"
        f"Skor: {rec['skor_lulus']}/{rec['total_uji']} uji lulus ({rec['pct_lulus']}%)\n"
    )

    if norm_df_uni is not None and not norm_df_uni.empty:
        n_normal = norm_df_uni["Normal (α=0.05)"].str.contains("Ya").sum()
        parts.append(
            f"Normalitas univariat (Shapiro-Wilk): "
            f"{n_normal}/{len(norm_df_uni)} variabel normal."
        )

    if mardia_result and "error" not in mardia_result:
        parts.append(
            f"Normalitas multivariat (Mardia): "
            f"skewness p={mardia_result['p_skew']:.4f}, "
            f"kurtosis p={mardia_result['p_kurt']:.4f}. "
            f"Overall: {'normal' if mardia_result['normal_overall'] else 'tidak normal'}."
        )

    for h in homo_results:
        if "error" not in h:
            parts.append(
                f"Homogenitas varians (Levene p={h['levene_p']:.4f}): "
                f"{'homogen' if h['homogen_levene'] else 'tidak homogen'}."
            )

    for lin in linearity_results:
        if "error" not in lin:
            parts.append(
                f"Linieritas {lin['x_col']}→{lin['y_col']} "
                f"(RESET p={lin['p_value']:.4f}): "
                f"{'linier' if lin['linier'] else 'tidak linier'}."
            )

    parts.append(f"\nRekomendasi sistem: {'; '.join(rec['rekomendasi'])}")
    if rec["peringatan"]:
        parts.append(f"Peringatan: {'; '.join(rec['peringatan'])}")

    prompt = (
        "\n".join(parts) +
        "\n\nBerikan interpretasi komprehensif dalam Bahasa Indonesia mencakup:\n"
        "1. Evaluasi kondisi normalitas data (univariat dan multivariat)\n"
        "2. Evaluasi homogenitas varians dan implikasinya\n"
        "3. Evaluasi linieritas dan konsekuensinya terhadap regresi\n"
        "4. Rekomendasi metode analisis yang tepat beserta alasan\n"
        "5. Langkah konkret yang sebaiknya dilakukan peneliti\n"
        "Format: 4-5 paragraf akademis. Jangan gunakan bullet points. "
        "Gaya penulisan skripsi/laporan penelitian."
    )

    system = (
        "Kamu adalah Statistikawan Ahli yang membantu peneliti memahami "
        "kondisi data mereka sebelum memilih metode analisis. "
        "Berikan penjelasan yang tepat, akurat, dan dapat dimengerti oleh mahasiswa S1/S2."
    )

    return call_ai_api(prompt, system=system, api_key=api_key, provider=provider)
