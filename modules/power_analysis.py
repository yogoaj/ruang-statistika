"""
modules/power_analysis.py — Power Analysis & Sample Size (Free)
Ruang Statistika v4.2

Menghitung ukuran sampel minimum dan kurva power untuk:
  • t-Test Satu Sampel
  • t-Test Dua Sampel Independen
  • t-Test Berpasangan (Paired)
  • ANOVA Satu Arah
  • Regresi Linier (Multiple)
  • Uji Proporsi (Satu & Dua Proporsi)
  • Korelasi Pearson
  • Chi-Square (Goodness-of-Fit & Independence)

Dependensi: scipy (sudah ada di requirements), numpy, pandas, plotly
"""

import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from scipy import stats
from math import ceil
from typing import Optional


# ─── Konstanta Effect Size Cohen ─────────────────────────────────────────────

EFFECT_SIZE_LABELS = {
    "Kecil":   "small",
    "Sedang":  "medium",
    "Besar":   "large",
}

COHEN_D = {"small": 0.2,  "medium": 0.5,  "large": 0.8}
COHEN_F = {"small": 0.1,  "medium": 0.25, "large": 0.4}
COHEN_F2= {"small": 0.02, "medium": 0.15, "large": 0.35}
COHEN_W = {"small": 0.1,  "medium": 0.3,  "large": 0.5}
COHEN_R = {"small": 0.1,  "medium": 0.3,  "large": 0.5}


# ─── Helper: Power Calculator per uji ────────────────────────────────────────

def power_ttest_one(n: int, d: float, alpha: float) -> float:
    """Power untuk t-test satu sampel."""
    nc = d * np.sqrt(n)
    df = n - 1
    t_crit = stats.t.ppf(1 - alpha / 2, df)
    power = 1 - stats.nct.cdf(t_crit, df, nc) + stats.nct.cdf(-t_crit, df, nc)
    return float(np.clip(power, 0, 1))


def power_ttest_two(n: int, d: float, alpha: float) -> float:
    """Power untuk t-test dua sampel independen (equal n)."""
    nc = d * np.sqrt(n / 2)
    df = 2 * n - 2
    t_crit = stats.t.ppf(1 - alpha / 2, df)
    power = 1 - stats.nct.cdf(t_crit, df, nc) + stats.nct.cdf(-t_crit, df, nc)
    return float(np.clip(power, 0, 1))


def power_ttest_paired(n: int, d: float, alpha: float) -> float:
    """Power untuk t-test berpasangan (identik dgn one-sample atas perbedaan)."""
    return power_ttest_one(n, d, alpha)


def power_anova(n_per_group: int, k: int, f: float, alpha: float) -> float:
    """Power untuk one-way ANOVA."""
    N = n_per_group * k
    df1 = k - 1
    df2 = N - k
    nc = f ** 2 * N          # noncentrality parameter λ
    f_crit = stats.f.ppf(1 - alpha, df1, df2)
    power = 1 - stats.ncf.cdf(f_crit, df1, df2, nc)
    return float(np.clip(power, 0, 1))


def power_regression(n: int, u: int, f2: float, alpha: float) -> float:
    """Power untuk regresi berganda. u = jumlah prediktor."""
    v = n - u - 1
    if v <= 0:
        return 0.0
    nc = f2 * n
    df1 = u
    f_crit = stats.f.ppf(1 - alpha, df1, v)
    power = 1 - stats.ncf.cdf(f_crit, df1, v, nc)
    return float(np.clip(power, 0, 1))


def power_proportion_one(n: int, p0: float, p1: float, alpha: float) -> float:
    """Power untuk uji proporsi satu sampel."""
    if p0 == p1:
        return alpha
    se0 = np.sqrt(p0 * (1 - p0) / n)
    se1 = np.sqrt(p1 * (1 - p1) / n)
    z_alpha = stats.norm.ppf(1 - alpha / 2)
    z_power = (abs(p1 - p0) - z_alpha * se0) / se1
    power = stats.norm.cdf(z_power) + stats.norm.cdf(-z_power - 2 * z_alpha * se0 / se1)
    return float(np.clip(power, 0, 1))


def power_proportion_two(n: int, p1: float, p2: float, alpha: float) -> float:
    """Power untuk uji proporsi dua sampel independen."""
    p_bar = (p1 + p2) / 2
    se0 = np.sqrt(2 * p_bar * (1 - p_bar) / n)
    se1 = np.sqrt(p1 * (1 - p1) / n + p2 * (1 - p2) / n)
    if se0 == 0 or se1 == 0:
        return alpha
    z_alpha = stats.norm.ppf(1 - alpha / 2)
    z_power = (abs(p1 - p2) - z_alpha * se0) / se1
    power = stats.norm.cdf(z_power)
    return float(np.clip(power, 0, 1))


def power_correlation(n: int, r: float, alpha: float) -> float:
    """Power untuk uji korelasi Pearson (Fisher z-transform)."""
    if abs(r) >= 1:
        return 1.0
    z_r = np.arctanh(r)
    se = 1 / np.sqrt(n - 3)
    z_alpha = stats.norm.ppf(1 - alpha / 2)
    power = stats.norm.cdf(abs(z_r) / se - z_alpha)
    return float(np.clip(power, 0, 1))


def power_chisquare(n: int, w: float, df: int, alpha: float) -> float:
    """Power untuk chi-square goodness-of-fit / independence."""
    nc = w ** 2 * n
    chi_crit = stats.chi2.ppf(1 - alpha, df)
    power = 1 - stats.ncx2.cdf(chi_crit, df, nc)
    return float(np.clip(power, 0, 1))


# ─── Helper: Cari n minimum ──────────────────────────────────────────────────

def find_n(power_fn, target_power: float, alpha: float, max_n: int = 5000, **kwargs) -> int:
    """Binary search untuk n minimum yang mencapai target power."""
    lo, hi = 2, max_n
    for _ in range(30):
        mid = (lo + hi) // 2
        p = power_fn(mid, alpha=alpha, **kwargs)
        if p >= target_power:
            hi = mid
        else:
            lo = mid
        if hi - lo <= 1:
            break
    # Verifikasi hi
    return hi if power_fn(hi, alpha=alpha, **kwargs) >= target_power else max_n


# ─── Helper: Buat kurva power ─────────────────────────────────────────────────

def make_power_curve(power_fn, n_range: np.ndarray, alpha: float, target_power: float,
                     n_min: int, label: str, **kwargs) -> go.Figure:
    """Buat plotly figure kurva power vs n."""
    powers = [power_fn(int(n), alpha=alpha, **kwargs) for n in n_range]

    fig = go.Figure()

    # Kurva utama
    fig.add_trace(go.Scatter(
        x=n_range, y=powers,
        mode="lines",
        line=dict(color="#185FA5", width=2.5),
        name="Power"
    ))

    # Garis target power
    fig.add_hline(
        y=target_power,
        line_dash="dash",
        line_color="#e05c2a",
        annotation_text=f"Target Power = {target_power:.0%}",
        annotation_position="top right",
        annotation_font_color="#e05c2a",
    )

    # Marker n minimum
    p_at_nmin = power_fn(n_min, alpha=alpha, **kwargs)
    fig.add_trace(go.Scatter(
        x=[n_min], y=[p_at_nmin],
        mode="markers+text",
        marker=dict(color="#e05c2a", size=10, symbol="circle"),
        text=[f" n = {n_min}"],
        textposition="top right",
        textfont=dict(color="#e05c2a", size=12),
        name=f"n minimum = {n_min}",
    ))

    # Shading area "cukup power"
    x_shaded = [n for n in n_range if n >= n_min]
    y_shaded = [power_fn(int(n), alpha=alpha, **kwargs) for n in x_shaded]
    if x_shaded:
        fig.add_trace(go.Scatter(
            x=list(x_shaded) + list(x_shaded[::-1]),
            y=y_shaded + [target_power] * len(x_shaded),
            fill="toself",
            fillcolor="rgba(24,95,165,0.08)",
            line=dict(color="rgba(0,0,0,0)"),
            showlegend=False,
            hoverinfo="skip",
        ))

    fig.update_layout(
        title=dict(text=f"<b>Kurva Power — {label}</b>", font=dict(size=14)),
        xaxis_title="Ukuran Sampel (n per kelompok)" if "per kelompok" in label.lower() else "Ukuran Sampel (n)",
        yaxis_title="Statistical Power (1 − β)",
        yaxis=dict(range=[0, 1.05], tickformat=".0%"),
        legend=dict(orientation="h", y=-0.15),
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=50, r=30, t=60, b=60),
        height=360,
    )
    fig.update_xaxes(showgrid=True, gridcolor="#f0f0f0")
    fig.update_yaxes(showgrid=True, gridcolor="#f0f0f0")

    return fig


# ─── Helper: Tabel ringkasan multi-scenario ──────────────────────────────────

def sensitivity_table(power_fn, alpha: float, target_power: float,
                       effect_sizes: dict, label_key: str = "d", **base_kwargs) -> pd.DataFrame:
    """Tabel n untuk kombinasi effect size × target power."""
    targets = [0.70, 0.80, 0.90, 0.95]
    rows = []
    for es_label, es_val in effect_sizes.items():
        row = {"Effect Size": f"{es_label} ({label_key}={es_val})"}
        kw = {**base_kwargs, label_key: es_val}
        for tp in targets:
            n = find_n(power_fn, tp, alpha, **kw)
            row[f"Power {tp:.0%}"] = n
        rows.append(row)
    return pd.DataFrame(rows)


# ─── Komponen UI per tab ──────────────────────────────────────────────────────

def _sidebar_params(prefix: str):
    """Widget alpha & target power (dibuat di sidebar setiap tab)."""
    alpha = st.selectbox(
        "Tingkat Signifikansi (α)",
        [0.01, 0.05, 0.10],
        index=1,
        key=f"{prefix}_alpha",
        format_func=lambda x: f"{x:.2f}",
    )
    target_power = st.slider(
        "Target Power (1 − β)",
        min_value=0.60,
        max_value=0.99,
        value=0.80,
        step=0.01,
        key=f"{prefix}_power",
        format="%.2f",
    )
    return alpha, target_power


def _effect_size_help():
    with st.expander("❓ Panduan Effect Size (Cohen, 1988)"):
        st.markdown("""
| Ukuran | d (t-test) | f (ANOVA) | f² (Regresi) | r (Korelasi) | w (Chi-sq) |
|--------|-----------|-----------|--------------|--------------|------------|
| Kecil  | 0.2       | 0.10      | 0.02         | 0.10         | 0.10       |
| Sedang | 0.5       | 0.25      | 0.15         | 0.30         | 0.30       |
| Besar  | 0.8       | 0.40      | 0.35         | 0.50         | 0.50       |

> **Power ≥ 0.80** adalah standar minimum yang direkomendasikan Cohen (1988) untuk penelitian ilmu sosial.
""")


def _result_card(n_min: int, power_achieved: float, alpha: float, target_power: float):
    """Card metrik utama hasil kalkulasi."""
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""<div class="rs-metric">
            <div class="rs-metric-label">Sampel Minimum</div>
            <div class="rs-metric-value" style="color:#185FA5">{n_min}</div>
            <div class="rs-metric-sub">responden / kelompok</div>
        </div>""", unsafe_allow_html=True)
    with col2:
        ok = power_achieved >= target_power
        col = "#3b6d11" if ok else "#a32d2d"
        st.markdown(f"""<div class="rs-metric">
            <div class="rs-metric-label">Power Tercapai</div>
            <div class="rs-metric-value" style="color:{col}">{power_achieved:.1%}</div>
            <div class="rs-metric-sub">target: {target_power:.0%}</div>
        </div>""", unsafe_allow_html=True)
    with col3:
        st.markdown(f"""<div class="rs-metric">
            <div class="rs-metric-label">Tingkat α</div>
            <div class="rs-metric-value">{alpha:.2f}</div>
            <div class="rs-metric-sub">error tipe I</div>
        </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — t-Test
# ══════════════════════════════════════════════════════════════════════════════

def tab_ttest():
    st.markdown("#### t-Test: Satu Sampel | Dua Sampel | Berpasangan")
    _effect_size_help()

    c1, c2 = st.columns([1, 2])
    with c1:
        jenis = st.radio(
            "Jenis t-Test",
            ["Satu Sampel", "Dua Sampel Independen", "Berpasangan (Paired)"],
            key="tt_jenis",
        )
        es_preset = st.selectbox("Effect Size (Cohen's d)", list(EFFECT_SIZE_LABELS.keys()), index=1, key="tt_es_sel")
        d = st.number_input("Nilai d (manual)", min_value=0.01, max_value=5.0,
                            value=COHEN_D[EFFECT_SIZE_LABELS[es_preset]], step=0.01, key="tt_d")
        alpha, target_power = _sidebar_params("tt")

        if jenis == "Satu Sampel":
            power_fn  = power_ttest_one
            label     = "t-Test Satu Sampel"
        elif jenis == "Dua Sampel Independen":
            power_fn  = power_ttest_two
            label     = "t-Test Dua Sampel (per kelompok)"
        else:
            power_fn  = power_ttest_paired
            label     = "t-Test Berpasangan"

        n_min = find_n(power_fn, target_power, alpha, d=d)
        p_ach = power_fn(n_min, d=d, alpha=alpha)

    with c2:
        _result_card(n_min, p_ach, alpha, target_power)
        n_range = np.arange(2, min(n_min * 3, 501))
        fig = make_power_curve(power_fn, n_range, alpha, target_power, n_min, label, d=d)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("##### 📋 Tabel Sensitivitas")
    tbl = sensitivity_table(power_fn, alpha, target_power,
                            {k: COHEN_D[v] for k, v in EFFECT_SIZE_LABELS.items()},
                            label_key="d")
    st.dataframe(tbl.set_index("Effect Size"), use_container_width=True)

    if jenis == "Dua Sampel Independen":
        st.info(f"💡 Total sampel yang dibutuhkan: **{n_min * 2} responden** ({n_min} per kelompok)")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — ANOVA
# ══════════════════════════════════════════════════════════════════════════════

def tab_anova():
    st.markdown("#### ANOVA Satu Arah")
    _effect_size_help()

    c1, c2 = st.columns([1, 2])
    with c1:
        k = st.number_input("Jumlah Kelompok (k)", min_value=2, max_value=20, value=3, key="an_k")
        es_preset = st.selectbox("Effect Size (Cohen's f)", list(EFFECT_SIZE_LABELS.keys()), index=1, key="an_es")
        f = st.number_input("Nilai f (manual)", min_value=0.01, max_value=5.0,
                            value=COHEN_F[EFFECT_SIZE_LABELS[es_preset]], step=0.01, key="an_f")
        alpha, target_power = _sidebar_params("an")

        fn = lambda n, alpha, f: power_anova(n, k, f, alpha)
        n_min = find_n(fn, target_power, alpha, f=f)
        p_ach = power_anova(n_min, k, f, alpha)
        n_total = n_min * k

    with c2:
        _result_card(n_min, p_ach, alpha, target_power)
        st.info(f"💡 Total sampel (semua kelompok): **{n_total} responden** ({n_min} × {k} kelompok)")
        n_range = np.arange(2, min(n_min * 3, 301))
        powers  = [power_anova(int(n), k, f, alpha) for n in n_range]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=n_range * k, y=powers, mode="lines",
                                 line=dict(color="#185FA5", width=2.5), name="Power"))
        fig.add_hline(y=target_power, line_dash="dash", line_color="#e05c2a",
                      annotation_text=f"Target = {target_power:.0%}")
        fig.add_trace(go.Scatter(x=[n_total], y=[p_ach], mode="markers+text",
                                 marker=dict(color="#e05c2a", size=10),
                                 text=[f" N = {n_total}"], textposition="top right",
                                 textfont=dict(color="#e05c2a"), name=f"N minimum = {n_total}"))
        fig.update_layout(
            title="<b>Kurva Power — ANOVA Satu Arah</b>",
            xaxis_title="Total Sampel (N)",
            yaxis_title="Statistical Power (1 − β)",
            yaxis=dict(range=[0, 1.05], tickformat=".0%"),
            plot_bgcolor="white", paper_bgcolor="white",
            margin=dict(l=50, r=30, t=60, b=60), height=360,
        )
        fig.update_xaxes(showgrid=True, gridcolor="#f0f0f0")
        fig.update_yaxes(showgrid=True, gridcolor="#f0f0f0")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("##### 📋 Tabel Sensitivitas")
    rows = []
    for es_label, es_key in EFFECT_SIZE_LABELS.items():
        fv = COHEN_F[es_key]
        fn2 = lambda n, alpha, f: power_anova(n, k, f, alpha)
        row = {f"f ({es_label})": fv}
        for tp in [0.70, 0.80, 0.90, 0.95]:
            n = find_n(fn2, tp, alpha, f=fv)
            row[f"Power {tp:.0%} (n/grp)"] = n
            row[f"Power {tp:.0%} (N total)"] = n * k
        rows.append(row)
    st.dataframe(pd.DataFrame(rows), use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Regresi
# ══════════════════════════════════════════════════════════════════════════════

def tab_regresi():
    st.markdown("#### Regresi Linier (Multiple)")
    _effect_size_help()

    c1, c2 = st.columns([1, 2])
    with c1:
        u = st.number_input("Jumlah Prediktor (u)", min_value=1, max_value=30, value=3, key="rg_u")
        es_preset = st.selectbox("Effect Size (Cohen's f²)", list(EFFECT_SIZE_LABELS.keys()), index=1, key="rg_es")
        f2 = st.number_input("Nilai f² (manual)", min_value=0.001, max_value=5.0,
                             value=COHEN_F2[EFFECT_SIZE_LABELS[es_preset]], step=0.01,
                             format="%.3f", key="rg_f2")
        alpha, target_power = _sidebar_params("rg")

        fn = lambda n, alpha, f2: power_regression(n, u, f2, alpha)
        n_min = find_n(fn, target_power, alpha, f2=f2)
        p_ach = power_regression(n_min, u, f2, alpha)

        # Rule of thumb Green (1991): N ≥ 50 + 8u
        rot = 50 + 8 * u

    with c2:
        _result_card(n_min, p_ach, alpha, target_power)
        if rot > n_min:
            st.warning(f"⚠️ Rule of thumb Green (1991): N ≥ **{rot}** untuk {u} prediktor. "
                       f"Pertimbangkan menggunakan N = {rot} untuk kestabilan estimasi.")
        else:
            st.success(f"✅ N minimum ({n_min}) melebihi rule of thumb Green (N ≥ {rot}).")

        n_range = np.arange(u + 5, min(n_min * 3, 501))
        fig = make_power_curve(fn, n_range, alpha, target_power, n_min,
                               f"Regresi Berganda (u={u} prediktor)", f2=f2)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("##### 📋 Tabel Sensitivitas")
    rows = []
    for es_label, es_key in EFFECT_SIZE_LABELS.items():
        f2v = COHEN_F2[es_key]
        fn2 = lambda n, alpha, f2: power_regression(n, u, f2, alpha)
        row = {f"f² ({es_label})": f2v}
        for tp in [0.70, 0.80, 0.90, 0.95]:
            row[f"Power {tp:.0%}"] = find_n(fn2, tp, alpha, f2=f2v)
        rows.append(row)
    st.dataframe(pd.DataFrame(rows), use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — Proporsi
# ══════════════════════════════════════════════════════════════════════════════

def tab_proporsi():
    st.markdown("#### Uji Proporsi")

    jenis = st.radio("Jenis Uji", ["Satu Proporsi", "Dua Proporsi Independen"], key="pr_jenis", horizontal=True)

    c1, c2 = st.columns([1, 2])
    with c1:
        if jenis == "Satu Proporsi":
            p0 = st.number_input("Proporsi Hipotesis Nol (p₀)", 0.01, 0.99, 0.50, 0.01, key="pr_p0")
            p1 = st.number_input("Proporsi Alternatif (p₁)", 0.01, 0.99, 0.65, 0.01, key="pr_p1")
            alpha, target_power = _sidebar_params("pr")

            fn = lambda n, alpha: power_proportion_one(n, p0, p1, alpha)
            n_min = find_n(fn, target_power, alpha)
            p_ach = power_proportion_one(n_min, p0, p1, alpha)
            label = "Uji Proporsi Satu Sampel"
        else:
            p1 = st.number_input("Proporsi Kelompok 1 (p₁)", 0.01, 0.99, 0.40, 0.01, key="pr_p1b")
            p2 = st.number_input("Proporsi Kelompok 2 (p₂)", 0.01, 0.99, 0.60, 0.01, key="pr_p2")
            alpha, target_power = _sidebar_params("pr")

            fn = lambda n, alpha: power_proportion_two(n, p1, p2, alpha)
            n_min = find_n(fn, target_power, alpha)
            p_ach = power_proportion_two(n_min, p1, p2, alpha)
            label = "Uji Proporsi Dua Sampel (per kelompok)"

    with c2:
        _result_card(n_min, p_ach, alpha, target_power)

        n_range = np.arange(5, min(n_min * 3, 801))
        fig = make_power_curve(fn, n_range, alpha, target_power, n_min, label)
        st.plotly_chart(fig, use_container_width=True)

    if jenis == "Dua Proporsi Independen":
        st.info(f"💡 Total sampel: **{n_min * 2} responden** ({n_min} per kelompok)")

    # Tabel variasi selisih proporsi
    st.markdown("##### 📋 Tabel Sensitivitas — Variasi Selisih Proporsi")
    if jenis == "Satu Proporsi":
        deltas = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30]
        rows = []
        for delta in deltas:
            p1_v = min(p0 + delta, 0.99)
            fn_v = lambda n, alpha, pv=p1_v: power_proportion_one(n, p0, pv, alpha)
            row = {"Δ (p₁ − p₀)": f"+{delta:.2f}", "p₁": f"{p1_v:.2f}"}
            for tp in [0.70, 0.80, 0.90]:
                row[f"Power {tp:.0%}"] = find_n(fn_v, tp, alpha)
            rows.append(row)
        st.dataframe(pd.DataFrame(rows), use_container_width=True)
    else:
        deltas = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30]
        rows = []
        for delta in deltas:
            p2_v = min(p1 + delta, 0.99)
            fn_v = lambda n, alpha, pv=p2_v: power_proportion_two(n, p1, pv, alpha)
            row = {"Δ (p₂ − p₁)": f"+{delta:.2f}", "p₂": f"{p2_v:.2f}"}
            for tp in [0.70, 0.80, 0.90]:
                row[f"Power {tp:.0%} (n/grp)"] = find_n(fn_v, tp, alpha)
            rows.append(row)
        st.dataframe(pd.DataFrame(rows), use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — Korelasi
# ══════════════════════════════════════════════════════════════════════════════

def tab_korelasi():
    st.markdown("#### Uji Korelasi Pearson")
    _effect_size_help()

    c1, c2 = st.columns([1, 2])
    with c1:
        es_preset = st.selectbox("Effect Size (Cohen's r)", list(EFFECT_SIZE_LABELS.keys()), index=1, key="kr_es")
        r = st.number_input("Nilai r (manual)", min_value=0.01, max_value=0.99,
                            value=COHEN_R[EFFECT_SIZE_LABELS[es_preset]], step=0.01, key="kr_r")
        alpha, target_power = _sidebar_params("kr")

        fn = lambda n, alpha: power_correlation(n, r, alpha)
        n_min = find_n(fn, target_power, alpha)
        p_ach = power_correlation(n_min, r, alpha)

    with c2:
        _result_card(n_min, p_ach, alpha, target_power)
        n_range = np.arange(5, min(n_min * 3, 601))
        fig = make_power_curve(fn, n_range, alpha, target_power, n_min,
                               f"Korelasi Pearson (r = {r:.2f})")
        st.plotly_chart(fig, use_container_width=True)

    # Heatmap power: r × n
    st.markdown("##### 🗺️ Heatmap Power (r × n)")
    r_vals = np.round(np.arange(0.10, 0.85, 0.05), 2)
    n_vals = np.arange(10, 301, 10)
    z = [[power_correlation(int(n), float(rv), alpha) for n in n_vals] for rv in r_vals]
    fig_hm = go.Figure(go.Heatmap(
        z=z, x=n_vals, y=[f"r={rv:.2f}" for rv in r_vals],
        colorscale="Blues", zmin=0, zmax=1,
        colorbar=dict(title="Power", tickformat=".0%"),
    ))
    fig_hm.update_layout(
        title=f"<b>Heatmap Power (α = {alpha:.2f})</b>",
        xaxis_title="Ukuran Sampel (n)",
        yaxis_title="Koefisien Korelasi (r)",
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=70, r=30, t=60, b=60), height=400,
    )
    st.plotly_chart(fig_hm, use_container_width=True)

    st.markdown("##### 📋 Tabel Sensitivitas")
    tbl = sensitivity_table(
        lambda n, alpha, r: power_correlation(n, r, alpha),
        alpha, target_power,
        {k: COHEN_R[v] for k, v in EFFECT_SIZE_LABELS.items()},
        label_key="r"
    )
    st.dataframe(tbl.set_index("Effect Size"), use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 6 — Chi-Square
# ══════════════════════════════════════════════════════════════════════════════

def tab_chisquare():
    st.markdown("#### Chi-Square (Goodness-of-Fit & Independence)")
    _effect_size_help()

    jenis = st.radio("Jenis Uji", ["Goodness-of-Fit", "Uji Independensi (Tabel Kontingensi)"],
                     key="cs_jenis", horizontal=True)

    c1, c2 = st.columns([1, 2])
    with c1:
        if jenis == "Goodness-of-Fit":
            k_cat = st.number_input("Jumlah Kategori", min_value=2, max_value=20, value=4, key="cs_k")
            df_chi = k_cat - 1
        else:
            r_cat = st.number_input("Jumlah Baris", min_value=2, max_value=10, value=2, key="cs_r")
            c_cat = st.number_input("Jumlah Kolom", min_value=2, max_value=10, value=3, key="cs_c")
            df_chi = (r_cat - 1) * (c_cat - 1)

        es_preset = st.selectbox("Effect Size (Cohen's w)", list(EFFECT_SIZE_LABELS.keys()), index=1, key="cs_es")
        w = st.number_input("Nilai w (manual)", min_value=0.01, max_value=5.0,
                            value=COHEN_W[EFFECT_SIZE_LABELS[es_preset]], step=0.01, key="cs_w")
        alpha, target_power = _sidebar_params("cs")

        fn = lambda n, alpha: power_chisquare(n, w, df_chi, alpha)
        n_min = find_n(fn, target_power, alpha)
        p_ach = power_chisquare(n_min, w, df_chi, alpha)
        st.caption(f"df = {df_chi}")

    with c2:
        _result_card(n_min, p_ach, alpha, target_power)
        n_range = np.arange(5, min(n_min * 3, 801))
        label_chi = "Chi-Square GoF" if jenis == "Goodness-of-Fit" else "Chi-Square Independensi"
        fig = make_power_curve(fn, n_range, alpha, target_power, n_min,
                               f"{label_chi} (df={df_chi}, w={w:.2f})")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("##### 📋 Tabel Sensitivitas")
    tbl = sensitivity_table(
        lambda n, alpha, w: power_chisquare(n, w, df_chi, alpha),
        alpha, target_power,
        {k: COHEN_W[v] for k, v in EFFECT_SIZE_LABELS.items()},
        label_key="w"
    )
    st.dataframe(tbl.set_index("Effect Size"), use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 7 — Kalkulator Balik (Achieved Power)
# ══════════════════════════════════════════════════════════════════════════════

def tab_achieved():
    st.markdown("#### Kalkulator Power Tercapai")
    st.markdown(
        "Sudah punya data? Masukkan n aktual dan parameter Anda untuk mengetahui "
        "berapa power yang dicapai oleh studi ini (*post-hoc power analysis*)."
    )
    st.warning("⚠️ Post-hoc power analysis sebaiknya digunakan untuk **perencanaan studi berikutnya**, "
               "bukan untuk menjelaskan hasil yang tidak signifikan dari studi saat ini.")

    uji = st.selectbox("Jenis Uji", [
        "t-Test Satu Sampel", "t-Test Dua Sampel Independen",
        "ANOVA Satu Arah", "Regresi Berganda",
        "Korelasi Pearson", "Chi-Square",
    ], key="ach_uji")

    c1, c2 = st.columns(2)
    with c1:
        n_actual = st.number_input("n Aktual (per kelompok / total)", min_value=3, max_value=10000,
                                   value=50, key="ach_n")
        alpha_ach = st.selectbox("Tingkat Signifikansi (α)", [0.01, 0.05, 0.10], index=1,
                                 key="ach_alpha", format_func=lambda x: f"{x:.2f}")

    with c2:
        if uji in ("t-Test Satu Sampel", "t-Test Dua Sampel Independen"):
            d_ach = st.number_input("Cohen's d", 0.01, 5.0, 0.5, 0.01, key="ach_d")
            if uji == "t-Test Satu Sampel":
                power_ach = power_ttest_one(n_actual, d_ach, alpha_ach)
            else:
                power_ach = power_ttest_two(n_actual, d_ach, alpha_ach)
        elif uji == "ANOVA Satu Arah":
            k_ach = st.number_input("Jumlah Kelompok", 2, 20, 3, key="ach_k")
            f_ach = st.number_input("Cohen's f", 0.01, 5.0, 0.25, 0.01, key="ach_f")
            power_ach = power_anova(n_actual, k_ach, f_ach, alpha_ach)
        elif uji == "Regresi Berganda":
            u_ach = st.number_input("Jumlah Prediktor", 1, 30, 3, key="ach_u")
            f2_ach = st.number_input("Cohen's f²", 0.001, 5.0, 0.15, 0.01, format="%.3f", key="ach_f2")
            power_ach = power_regression(n_actual, u_ach, f2_ach, alpha_ach)
        elif uji == "Korelasi Pearson":
            r_ach = st.number_input("Koefisien r", 0.01, 0.99, 0.30, 0.01, key="ach_r")
            power_ach = power_correlation(n_actual, r_ach, alpha_ach)
        else:  # Chi-Square
            w_ach = st.number_input("Cohen's w", 0.01, 5.0, 0.30, 0.01, key="ach_w")
            df_ach = st.number_input("Derajat Bebas (df)", 1, 50, 2, key="ach_df")
            power_ach = power_chisquare(n_actual, w_ach, int(df_ach), alpha_ach)

    # Tampilkan hasil
    status_col = "#3b6d11" if power_ach >= 0.80 else ("#e09a00" if power_ach >= 0.70 else "#a32d2d")
    status_txt = "Memadai ✓" if power_ach >= 0.80 else ("Marginal ⚠️" if power_ach >= 0.70 else "Rendah ✗")

    st.markdown(f"""
    <div class="rs-narasi" style="text-align:center; padding:1.5rem; margin-top:1rem;">
        <div style="font-size:0.9rem; color:#5f8ab5; margin-bottom:6px;">Power Studi Ini</div>
        <div style="font-size:3rem; font-weight:700; color:{status_col}; line-height:1.1">{power_ach:.1%}</div>
        <div style="font-size:1rem; color:{status_col}; margin-top:4px;">{status_txt}</div>
        <div style="font-size:0.82rem; color:#888; margin-top:8px;">
            Studi dengan n = {n_actual} dan α = {alpha_ach} pada uji ini memiliki 
            probabilitas {power_ach:.1%} untuk mendeteksi efek jika benar-benar ada.
        </div>
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# RENDER UTAMA
# ══════════════════════════════════════════════════════════════════════════════

def render(ctx: dict):
    st.markdown('<p class="rs-section-title">🔋 Power Analysis & Sample Size</p>',
                unsafe_allow_html=True)
    st.markdown(
        '<p class="rs-section-sub">'
        'Hitung ukuran sampel minimum dan kurva statistical power sebelum memulai penelitian. '
        'Mendukung t-test, ANOVA, regresi, proporsi, korelasi, dan chi-square.'
        '</p>',
        unsafe_allow_html=True,
    )

    tabs = st.tabs([
        "📊 t-Test",
        "📊 ANOVA",
        "📈 Regresi",
        "🔢 Proporsi",
        "🔗 Korelasi",
        "χ² Chi-Square",
        "🔍 Power Tercapai",
    ])

    with tabs[0]: tab_ttest()
    with tabs[1]: tab_anova()
    with tabs[2]: tab_regresi()
    with tabs[3]: tab_proporsi()
    with tabs[4]: tab_korelasi()
    with tabs[5]: tab_chisquare()
    with tabs[6]: tab_achieved()

    # ── Catatan metodologis ──────────────────────────────────────────────────
    st.markdown("---")
    with st.expander("📚 Referensi Metodologis"):
        st.markdown("""
**Perhitungan power** menggunakan distribusi non-sentral (non-central t, F, χ²) sesuai:

- **Cohen, J. (1988).** *Statistical Power Analysis for the Behavioral Sciences* (2nd ed.). Lawrence Erlbaum.
- **Green, S. B. (1991).** How many subjects does it take to do a regression analysis? *Multivariate Behavioral Research, 26*(3), 499–510.
- **Faul, F., et al. (2007).** G*Power 3: A flexible statistical power analysis program. *Behavior Research Methods, 39*(2), 175–191.

**Rekomendasi umum:**
- Power ≥ **0.80** → standar minimum ilmu sosial (Cohen, 1988)
- Power ≥ **0.90** → direkomendasikan untuk penelitian klinis & kebijakan
- Effect size **sedang** (d = 0.5, f = 0.25, r = 0.3) sebagai default konservatif jika belum ada studi sebelumnya
        """)
