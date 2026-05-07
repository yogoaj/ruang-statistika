"""
modules/ols_robust.py — Regresi Robust & WLS (Pro)
Ruang Statistika v4.2

Fitur:
  Tab 1 — Regresi Robust (RLM)
    • Huber-M estimator (bisquare opsional)
    • Tabel koefisien RLM vs OLS side-by-side
    • Robustness gain: identifikasi koefisien yang berubah signifikan
    • Residual weight plot (observasi berpengaruh/outlier diberi bobot rendah)
    • AI interpretasi

  Tab 2 — Weighted Least Squares (WLS)
    • Bobot 1/|residual OLS| (iterative reweighting proxy)
    • Bobot manual: kolom bobot dari data atau invers varians per grup
    • Tabel koefisien WLS vs OLS side-by-side
    • Heteroskedastisitas sebelum/sesudah (Glejser p-value)
    • AI interpretasi

  Tab 3 — Perbandingan Model
    • Tabel R², AIC, BIC, RMSE untuk OLS / RLM-Huber / RLM-Bisquare / WLS
    • Rekomendasi model terbaik berdasarkan konteks
    • Plot koefisien side-by-side (bar chart)

Referensi: Huber (1973), Hampel et al. (1986), Greene (2012).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

from utils.auth import require_pro
from utils.stats_helpers import require_data, require_cols, ss_get
from utils.ai_helpers import (
    ai_interpret_robust,
    ai_interpret_wls_robust,
    ai_interpret_model_comparison,
)

# ── Konstanta warna ───────────────────────────────────────────────────────────
BLUE   = "#185FA5"
RED    = "#A32D2D"
GREEN  = "#3B6D11"
ORANGE = "#C4590A"
PURPLE = "#6B21A8"
NAVY   = "#0c2340"


# ─────────────────────────────────────────────────────────────────────────────
# Helper statistik
# ─────────────────────────────────────────────────────────────────────────────

def _prep_data(df: pd.DataFrame, dep_var: str, ind_vars: list):
    """Siapkan X dan y dari DataFrame, pastikan numerik, hapus NaN."""
    import statsmodels.api as sm
    subset = df[[dep_var] + ind_vars].apply(pd.to_numeric, errors="coerce").dropna()
    X = sm.add_constant(subset[ind_vars])
    y = subset[dep_var]
    return X, y, subset


def _fit_ols(X, y):
    import statsmodels.api as sm
    return sm.OLS(y, X).fit()


def _fit_rlm_huber(X, y):
    import statsmodels.api as sm
    import statsmodels.robust.norms as norms
    return sm.RLM(y, X, M=norms.HuberT()).fit()


def _fit_rlm_bisquare(X, y):
    import statsmodels.api as sm
    import statsmodels.robust.norms as norms
    return sm.RLM(y, X, M=norms.TukeyBiweight()).fit()


def _fit_wls(X, y, weights: np.ndarray):
    import statsmodels.api as sm
    return sm.WLS(y, X, weights=weights).fit()


def _glejser_p(model_resid, X_no_const: pd.DataFrame) -> float:
    """Jalankan Glejser test — kembalikan p-value global F-test."""
    import statsmodels.api as sm
    try:
        abs_resid = np.abs(model_resid)
        X_g = sm.add_constant(X_no_const)
        g_model = sm.OLS(abs_resid, X_g).fit()
        return float(g_model.f_pvalue)
    except Exception:
        return float("nan")


def _compute_rmse(model) -> float:
    try:
        return float(np.sqrt(np.mean(model.resid ** 2)))
    except Exception:
        return float("nan")


def _model_summary_row(
    label: str,
    model,
    model_type: str = "ols",          # "ols" | "rlm" | "wls"
) -> dict:
    """Buat baris ringkasan model untuk tabel perbandingan."""
    row = {"Model": label}
    try:
        if model_type in ("ols", "wls"):
            row["R²"]       = round(float(model.rsquared), 4)
            row["R² Adj"]   = round(float(model.rsquared_adj), 4)
            row["AIC"]      = round(float(model.aic), 2)
            row["BIC"]      = round(float(model.bic), 2)
            row["F p-val"]  = round(float(model.f_pvalue), 4)
        else:
            # RLM — tidak ada R² native; hitung pseudo-R² vs null model
            row["R²"]       = "–"
            row["R² Adj"]   = "–"
            row["AIC"]      = "–"
            row["BIC"]      = "–"
            row["F p-val"]  = "–"
        row["RMSE"] = round(_compute_rmse(model), 4)
    except Exception:
        row.update({"R²": "–", "R² Adj": "–", "AIC": "–", "BIC": "–",
                    "F p-val": "–", "RMSE": "–"})
    return row


def _coef_comparison_df(
    ols_model,
    alt_model,
    alt_label: str,
    param_names: list,
) -> pd.DataFrame:
    """
    Buat tabel perbandingan koefisien OLS vs model alternatif.
    Tambahkan kolom 'Δ%' dan flag perubahan besar (>10%).
    """
    rows = []
    for p in param_names:
        ols_b  = ols_model.params.get(p, float("nan"))
        ols_se = ols_model.bse.get(p, float("nan"))
        ols_p  = ols_model.pvalues.get(p, float("nan"))

        try:
            alt_b  = alt_model.params[p]
            alt_se = alt_model.bse[p]
            alt_p  = alt_model.pvalues[p] if hasattr(alt_model, "pvalues") else float("nan")
        except Exception:
            alt_b = alt_se = alt_p = float("nan")

        # Δ%: perubahan koefisien relatif terhadap OLS
        if abs(ols_b) > 1e-10 and not np.isnan(alt_b):
            delta_pct = round((alt_b - ols_b) / abs(ols_b) * 100, 2)
        else:
            delta_pct = float("nan")

        changed = (
            not np.isnan(delta_pct) and abs(delta_pct) > 10
        )

        rows.append({
            "Parameter":          p,
            "β OLS":              round(float(ols_b), 4),
            "SE OLS":             round(float(ols_se), 4),
            "p OLS":              round(float(ols_p), 4),
            f"β {alt_label}":     round(float(alt_b), 4),
            f"SE {alt_label}":    round(float(alt_se), 4),
            f"p {alt_label}":     round(float(alt_p), 4),
            "Δ% Koef":            delta_pct if not np.isnan(delta_pct) else "–",
            "Berubah >10%":       "⚠️ Ya" if changed else "✓ Stabil",
        })
    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────────────
# Plot helpers
# ─────────────────────────────────────────────────────────────────────────────

def _plot_weights(weights: np.ndarray, resid: np.ndarray, n_show: int = 200) -> go.Figure:
    """Plot bobot robust vs residual — titik merah = observasi berpengaruh."""
    idx = np.arange(len(weights))
    if len(weights) > n_show:
        sample_idx = np.random.choice(len(weights), n_show, replace=False)
        idx = sample_idx
    colors = [RED if w < 0.5 else BLUE for w in weights[idx]]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=resid[idx], y=weights[idx],
        mode="markers",
        marker=dict(color=colors, size=7, opacity=0.75),
        hovertemplate="Residual: %{x:.3f}<br>Bobot: %{y:.4f}<extra></extra>",
    ))
    fig.add_hline(y=0.5, line_dash="dash", line_color=RED,
                  annotation_text="Bobot = 0.5 (ambang downweighting)")
    fig.update_layout(
        title="Robust Weights vs Residual",
        xaxis_title="Residual", yaxis_title="Bobot Robust (0–1)",
        template="plotly_white", height=380,
        margin=dict(l=30, r=30, t=55, b=30),
    )
    return fig


def _plot_coef_comparison(
    param_names: list,
    ols_coefs: list,
    alt_coefs: list,
    alt_label: str,
) -> go.Figure:
    """Bar chart perbandingan koefisien OLS vs model alternatif (tanpa konstanta)."""
    params = [p for p in param_names if p != "const"]
    ols_vals = [ols_coefs[param_names.index(p)] for p in params]
    alt_vals = [alt_coefs[param_names.index(p)] if p in param_names else 0 for p in params]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="OLS", x=params, y=ols_vals,
        marker_color=BLUE, opacity=0.8,
    ))
    fig.add_trace(go.Bar(
        name=alt_label, x=params, y=alt_vals,
        marker_color=ORANGE, opacity=0.8,
    ))
    fig.update_layout(
        barmode="group",
        title=f"Perbandingan Koefisien: OLS vs {alt_label}",
        xaxis_title="Variabel", yaxis_title="Koefisien (β)",
        template="plotly_white", height=400,
        margin=dict(l=30, r=30, t=55, b=30),
        legend=dict(orientation="h", y=-0.18),
    )
    return fig


def _plot_wls_fit(y_actual, y_pred_ols, y_pred_wls, dep_var: str) -> go.Figure:
    """Scatter aktual vs prediksi: OLS vs WLS."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=y_actual, y=y_pred_ols, mode="markers", name="OLS",
        marker=dict(color=BLUE, size=6, opacity=0.6),
    ))
    fig.add_trace(go.Scatter(
        x=y_actual, y=y_pred_wls, mode="markers", name="WLS",
        marker=dict(color=GREEN, size=6, opacity=0.6),
    ))
    mn = min(y_actual.min(), min(y_pred_ols), min(y_pred_wls))
    mx = max(y_actual.max(), max(y_pred_ols), max(y_pred_wls))
    fig.add_trace(go.Scatter(
        x=[mn, mx], y=[mn, mx], mode="lines",
        line=dict(color=RED, dash="dash"), name="Garis Sempurna",
    ))
    fig.update_layout(
        title=f"Aktual vs Prediksi: OLS & WLS ({dep_var})",
        xaxis_title="Nilai Aktual", yaxis_title="Nilai Prediksi",
        template="plotly_white", height=400,
        margin=dict(l=30, r=30, t=55, b=30),
        legend=dict(orientation="h", y=-0.18),
    )
    return fig


def _plot_model_comparison_bar(comparison_df: pd.DataFrame) -> go.Figure:
    """Bar chart RMSE per model untuk perbandingan cepat."""
    models = comparison_df["Model"].tolist()
    rmse   = comparison_df["RMSE"].tolist()
    colors = [BLUE, ORANGE, GREEN, PURPLE][:len(models)]
    fig = go.Figure(go.Bar(
        x=models, y=rmse,
        marker_color=colors,
        text=[f"{v:.4f}" for v in rmse],
        textposition="outside",
    ))
    fig.update_layout(
        title="RMSE per Model (lebih kecil = lebih baik)",
        xaxis_title="Model", yaxis_title="RMSE",
        template="plotly_white", height=360,
        margin=dict(l=30, r=30, t=55, b=30),
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# AI interpretasi — delegasi ke utils/ai_helpers.py (fungsi publik)
# ─────────────────────────────────────────────────────────────────────────────
# ai_interpret_robust, ai_interpret_wls_robust, ai_interpret_model_comparison
# sudah diimport dari utils.ai_helpers — tidak perlu definisi lokal.


# ─────────────────────────────────────────────────────────────────────────────
# render() — entry point
# ─────────────────────────────────────────────────────────────────────────────

def render(ctx: dict):
    license_info = ctx["license_info"]
    ai_enabled   = ctx["ai_enabled"]
    api_key      = ctx["anthropic_api_key"]
    ai_provider  = ctx["ai_provider"]
    alpha_level  = ctx.get("alpha_level", 0.05)

    st.markdown('<p class="rs-section-title">🛡️ Regresi Robust & WLS</p>',
                unsafe_allow_html=True)
    st.markdown(
        "<p class='rs-section-sub'>Alternatif OLS ketika outlier atau heteroskedastisitas "
        "tidak dapat diatasi — Huber-M, Bisquare, dan Weighted Least Squares "
        "(Huber, 1973; Greene, 2012).</p>",
        unsafe_allow_html=True,
    )

    # ── Guard Pro ─────────────────────────────────────────────────────────────
    if not require_pro(license_info, "Regresi Robust & WLS"):
        st.stop()

    df = require_data()
    if df is None:
        st.stop()

    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if len(num_cols) < 2:
        st.warning("⚠️ Minimal 2 kolom numerik diperlukan.")
        st.stop()

    if "ai_cache" not in st.session_state:
        st.session_state.ai_cache = {}

    # ── Pilih variabel ─────────────────────────────────────────────────────────
    st.markdown("#### ⚙️ Konfigurasi Model")
    col_y, col_x = st.columns([1, 2])
    with col_y:
        dep_var = st.selectbox("Variabel Dependen (Y)", num_cols, key="robust_dep")
    with col_x:
        ind_options = [c for c in num_cols if c != dep_var]
        ind_vars = st.multiselect(
            "Variabel Independen (X)",
            ind_options,
            default=ind_options[:min(3, len(ind_options))],
            key="robust_ind",
        )

    if not ind_vars:
        st.info("Pilih minimal 1 variabel independen.")
        st.stop()

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab1, tab2, tab3 = st.tabs([
        "🛡️ Regresi Robust (RLM)",
        "⚖️ Weighted Least Squares (WLS)",
        "📊 Perbandingan Model",
    ])

    # Fit OLS sekali — digunakan di semua tab
    with st.spinner("Memfitting model..."):
        try:
            X, y, subset = _prep_data(df, dep_var, ind_vars)
            ols_model = _fit_ols(X, y)
        except Exception as e:
            st.error(f"❌ Gagal fit OLS: {e}")
            st.stop()

    param_names   = list(ols_model.params.index)
    n_obs         = len(y)
    X_no_const    = subset[ind_vars]
    ols_glejser_p = _glejser_p(ols_model.resid, X_no_const)

    # =========================================================================
    # TAB 1 — Regresi Robust (RLM)
    # =========================================================================
    with tab1:
        st.markdown("#### 🛡️ Regresi Robust — RLM (Huber-M / Bisquare)")
        st.markdown(
            "<p class='rs-section-sub'>Robust Linear Model mereduksi pengaruh outlier dan "
            "observasi high-leverage dengan memberi bobot rendah pada observasi bermasalah.</p>",
            unsafe_allow_html=True,
        )

        estimator = st.radio(
            "Pilih Estimator Robust",
            ["Huber-M (default — lebih umum)", "Bisquare / Tukey (lebih agresif)"],
            horizontal=True,
            key="rlm_estimator",
        )
        use_bisquare = "Bisquare" in estimator
        est_label    = "Bisquare" if use_bisquare else "Huber-M"

        with st.spinner(f"Memfitting RLM {est_label}..."):
            try:
                rlm_model = _fit_rlm_bisquare(X, y) if use_bisquare else _fit_rlm_huber(X, y)
            except Exception as e:
                st.error(f"❌ Gagal fit RLM: {e}")
                st.stop()

        # Hitung bobot robust
        try:
            weights = rlm_model.weights
        except AttributeError:
            weights = np.ones(n_obs)
        n_low_weight = int((weights < 0.5).sum())

        # Tabel koefisien side-by-side
        coef_df = _coef_comparison_df(ols_model, rlm_model, est_label, param_names)
        n_changed = int((coef_df["Berubah >10%"] == "⚠️ Ya").sum())

        # ── Metrics ───────────────────────────────────────────────────────────
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.markdown(f"""<div class="rs-metric">
                <div class="rs-metric-label">Estimator</div>
                <div class="rs-metric-value" style="font-size:1.1rem;">{est_label}</div>
                <div class="rs-metric-sub">Robust M-estimator</div></div>""",
                unsafe_allow_html=True)
        with m2:
            st.markdown(f"""<div class="rs-metric">
                <div class="rs-metric-label">N Observasi</div>
                <div class="rs-metric-value">{n_obs}</div>
                <div class="rs-metric-sub">Total data</div></div>""",
                unsafe_allow_html=True)
        with m3:
            color3 = RED if n_low_weight > 0 else GREEN
            st.markdown(f"""<div class="rs-metric">
                <div class="rs-metric-label">Obs. Downweighted</div>
                <div class="rs-metric-value" style="color:{color3};">{n_low_weight}</div>
                <div class="rs-metric-sub">Bobot &lt; 0.5</div></div>""",
                unsafe_allow_html=True)
        with m4:
            color4 = RED if n_changed > 0 else GREEN
            st.markdown(f"""<div class="rs-metric">
                <div class="rs-metric-label">Koef. Berubah &gt;10%</div>
                <div class="rs-metric-value" style="color:{color4};">{n_changed}</div>
                <div class="rs-metric-sub">Tidak robust vs OLS</div></div>""",
                unsafe_allow_html=True)

        st.markdown("<br/>", unsafe_allow_html=True)

        # ── Plot weight ────────────────────────────────────────────────────────
        st.markdown("##### Robust Weights vs Residual")
        st.plotly_chart(
            _plot_weights(weights, rlm_model.resid.values),
            use_container_width=True,
        )
        st.caption(
            "🔴 Titik merah = observasi berpengaruh (weight < 0.5) yang diberi bobot rendah "
            "oleh estimator robust. Semakin banyak titik merah → OLS terpengaruh outlier."
        )

        # ── Tabel perbandingan koefisien ───────────────────────────────────────
        st.markdown(f"##### Tabel Koefisien: OLS vs {est_label}")

        def _style_coef(row):
            n_cols = len(row)
            styles = [""] * n_cols
            if "Berubah >10%" in row.index:
                idx = list(row.index).index("Berubah >10%")
                if row["Berubah >10%"] == "⚠️ Ya":
                    styles[idx] = "background-color:#fff8e1; color:#7a5c00; font-weight:600;"
            return styles

        st.dataframe(
            coef_df.style.apply(_style_coef, axis=1),
            use_container_width=True, hide_index=True,
        )

        # ── Plot koefisien ────────────────────────────────────────────────────
        try:
            ols_vals = [float(ols_model.params[p]) for p in param_names]
            rlm_vals = [float(rlm_model.params[p]) for p in param_names]
            st.plotly_chart(
                _plot_coef_comparison(param_names, ols_vals, rlm_vals, est_label),
                use_container_width=True,
            )
        except Exception:
            pass

        # ── Narasi otomatis ────────────────────────────────────────────────────
        if n_changed == 0 and n_low_weight < n_obs * 0.05:
            narasi = (
                f"✅ Model OLS tampak robust terhadap outlier pada dataset ini. "
                f"Hanya {n_low_weight} dari {n_obs} observasi yang menerima bobot rendah, "
                f"dan tidak ada koefisien yang berubah lebih dari 10%. "
                f"Penggunaan OLS biasa dapat dipertahankan."
            )
        else:
            pct_low = round(n_low_weight / n_obs * 100, 1)
            narasi = (
                f"⚠️ Ditemukan {n_low_weight} ({pct_low}%) observasi dengan bobot robust < 0.5, "
                f"dan {n_changed} koefisien berubah lebih dari 10% dibanding OLS. "
                f"Ini mengindikasikan adanya outlier atau leverage points yang mempengaruhi estimasi OLS. "
                f"Model {est_label} lebih sesuai untuk data ini."
            )
        st.markdown(
            f'<div class="rs-narasi">📊 {narasi}</div>',
            unsafe_allow_html=True,
        )

        # ── AI ─────────────────────────────────────────────────────────────────
        if ai_enabled:
            if st.button(f"🤖 Interpretasi Regresi {est_label} dengan AI", key="ai_rlm_btn"):
                with st.spinner("🤖 AI sedang menganalisis regresi robust..."):
                    ai_rlm = ai_interpret_robust(
                        dep_var, ind_vars, coef_df,
                        n_changed, n_low_weight, n_obs, est_label,
                        api_key, ai_provider,
                    )
                st.session_state.ai_cache["robust_rlm"] = ai_rlm
            if ss_get("ai_cache", {}).get("robust_rlm"):
                st.markdown(
                    f'<div class="rs-ai-narasi">'
                    f'<span class="rs-ai-badge">✨ AI — {ai_provider.split("(")[0].strip()}</span><br/>'
                    f'{ss_get("ai_cache", {})["robust_rlm"].replace(chr(10), "<br/>")}'
                    f"</div>",
                    unsafe_allow_html=True,
                )
        else:
            st.caption("💡 Aktifkan API Key untuk interpretasi AI.")

        # ── Simpan ke session state ────────────────────────────────────────────
        st.session_state["robust_result"] = {
            "dep_var":        dep_var,
            "ind_vars":       ind_vars,
            "estimator":      est_label,
            "n_obs":          n_obs,
            "n_low_weight":   n_low_weight,
            "n_changed":      n_changed,
            "ols_rmse":       _compute_rmse(ols_model),
            "rlm_rmse":       _compute_rmse(rlm_model),
            "coef_df":        coef_df,
        }

    # =========================================================================
    # TAB 2 — Weighted Least Squares (WLS)
    # =========================================================================
    with tab2:
        st.markdown("#### ⚖️ Weighted Least Squares (WLS)")
        st.markdown(
            "<p class='rs-section-sub'>WLS memperbaiki heteroskedastisitas dengan memberi bobot "
            "berbeda per observasi — observasi dengan varians tinggi mendapat bobot lebih kecil.</p>",
            unsafe_allow_html=True,
        )

        weight_method = st.radio(
            "Metode Pembobotan",
            [
                "1/|residual OLS| (otomatis — FGLS proxy)",
                "1/fitted² (varians proporsional nilai prediksi)",
                "Kolom bobot dari data (manual)",
            ],
            horizontal=False,
            key="wls_weight_method",
        )

        wls_weights = None
        wls_label   = ""

        if "1/|residual OLS|" in weight_method:
            abs_resid = np.abs(ols_model.resid)
            abs_resid = np.where(abs_resid < 1e-8, 1e-8, abs_resid)
            wls_weights = 1.0 / abs_resid
            wls_label   = "1/|ε_OLS|"
        elif "1/fitted²" in weight_method:
            fitted = ols_model.fittedvalues
            fitted = np.where(np.abs(fitted) < 1e-8, 1e-8, np.abs(fitted))
            wls_weights = 1.0 / (fitted ** 2)
            wls_label   = "1/Ŷ²"
        else:
            weight_cols = [c for c in num_cols if c not in [dep_var] + ind_vars]
            if not weight_cols:
                st.warning("Tidak ada kolom bobot tersedia. Pilih metode otomatis.")
                st.stop()
            w_col = st.selectbox("Pilih kolom bobot", weight_cols, key="wls_wcol")
            raw_w = pd.to_numeric(df[w_col], errors="coerce").values[:n_obs]
            raw_w = np.where(np.isnan(raw_w) | (raw_w <= 0), 1e-8, raw_w)
            wls_weights = raw_w
            wls_label   = f"kolom '{w_col}'"

        with st.spinner("Memfitting WLS..."):
            try:
                wls_model = _fit_wls(X, y, wls_weights)
            except Exception as e:
                st.error(f"❌ Gagal fit WLS: {e}")
                st.stop()

        wls_glejser_p = _glejser_p(wls_model.resid, X_no_const)
        ols_rmse = _compute_rmse(ols_model)
        wls_rmse = _compute_rmse(wls_model)

        # Tabel koefisien
        coef_df_wls = _coef_comparison_df(ols_model, wls_model, "WLS", param_names)
        n_changed_wls = int((coef_df_wls["Berubah >10%"] == "⚠️ Ya").sum())

        # ── Metrics ───────────────────────────────────────────────────────────
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.markdown(f"""<div class="rs-metric">
                <div class="rs-metric-label">R² WLS</div>
                <div class="rs-metric-value">{round(wls_model.rsquared, 4)}</div>
                <div class="rs-metric-sub">R² OLS: {round(ols_model.rsquared, 4)}</div></div>""",
                unsafe_allow_html=True)
        with m2:
            glejser_col = GREEN if ols_glejser_p < 0.05 and wls_glejser_p >= 0.05 else (
                RED if wls_glejser_p < 0.05 else GREEN
            )
            st.markdown(f"""<div class="rs-metric">
                <div class="rs-metric-label">Glejser p (WLS)</div>
                <div class="rs-metric-value" style="color:{glejser_col};">{round(wls_glejser_p, 4)}</div>
                <div class="rs-metric-sub">OLS: {round(ols_glejser_p, 4)}</div></div>""",
                unsafe_allow_html=True)
        with m3:
            rmse_color = GREEN if wls_rmse <= ols_rmse else RED
            st.markdown(f"""<div class="rs-metric">
                <div class="rs-metric-label">RMSE WLS</div>
                <div class="rs-metric-value" style="color:{rmse_color};">{round(wls_rmse, 4)}</div>
                <div class="rs-metric-sub">OLS: {round(ols_rmse, 4)}</div></div>""",
                unsafe_allow_html=True)
        with m4:
            color4 = RED if n_changed_wls > 0 else GREEN
            st.markdown(f"""<div class="rs-metric">
                <div class="rs-metric-label">Koef. Berubah &gt;10%</div>
                <div class="rs-metric-value" style="color:{color4};">{n_changed_wls}</div>
                <div class="rs-metric-sub">WLS vs OLS</div></div>""",
                unsafe_allow_html=True)

        st.markdown("<br/>", unsafe_allow_html=True)

        # ── Plot aktual vs prediksi ────────────────────────────────────────────
        st.markdown("##### Plot Aktual vs Prediksi: OLS vs WLS")
        y_pred_ols = ols_model.fittedvalues.values
        y_pred_wls = wls_model.fittedvalues.values
        st.plotly_chart(
            _plot_wls_fit(y.values, y_pred_ols, y_pred_wls, dep_var),
            use_container_width=True,
        )

        # ── Tabel koefisien ────────────────────────────────────────────────────
        st.markdown("##### Tabel Koefisien: OLS vs WLS")
        st.dataframe(coef_df_wls, use_container_width=True, hide_index=True)

        # ── Plot koefisien ─────────────────────────────────────────────────────
        try:
            ols_vals = [float(ols_model.params[p]) for p in param_names]
            wls_vals = [float(wls_model.params[p]) for p in param_names]
            st.plotly_chart(
                _plot_coef_comparison(param_names, ols_vals, wls_vals, "WLS"),
                use_container_width=True,
            )
        except Exception:
            pass

        # ── Heteroskedastisitas sebelum/sesudah ────────────────────────────────
        st.markdown("##### Evaluasi Heteroskedastisitas (Glejser Test)")
        col_a, col_b = st.columns(2)
        with col_a:
            color_a = RED if ols_glejser_p < alpha_level else GREEN
            label_a = "Heteroskedastisitas ✗" if ols_glejser_p < alpha_level else "Homoskedastisitas ✓"
            st.markdown(
                f'<div class="rs-narasi" style="border-left-color:{color_a};">'
                f'<b>Sebelum WLS (OLS)</b><br/>'
                f'Glejser p = {ols_glejser_p:.4f} → <b>{label_a}</b></div>',
                unsafe_allow_html=True,
            )
        with col_b:
            color_b = RED if wls_glejser_p < alpha_level else GREEN
            label_b = "Masih Heteroskedastis ⚠️" if wls_glejser_p < alpha_level else "Homoskedastisitas ✓"
            st.markdown(
                f'<div class="rs-narasi" style="border-left-color:{color_b};">'
                f'<b>Sesudah WLS</b><br/>'
                f'Glejser p = {wls_glejser_p:.4f} → <b>{label_b}</b></div>',
                unsafe_allow_html=True,
            )

        # ── Narasi otomatis ────────────────────────────────────────────────────
        if ols_glejser_p >= alpha_level:
            narasi_wls = (
                f"ℹ️ Tidak terdeteksi heteroskedastisitas pada OLS (Glejser p = {ols_glejser_p:.4f}). "
                f"WLS tetap dapat dijalankan sebagai robustness check, namun OLS sudah efisien. "
                f"Metode pembobotan: {wls_label}."
            )
        elif wls_glejser_p < alpha_level:
            narasi_wls = (
                f"⚠️ Heteroskedastisitas terdeteksi pada OLS (p = {ols_glejser_p:.4f}) dan "
                f"masih tersisa setelah WLS (p = {wls_glejser_p:.4f}). "
                f"Pertimbangkan HC robust standard errors atau transformasi variabel Y. "
                f"Bobot: {wls_label}."
            )
        else:
            narasi_wls = (
                f"✅ WLS berhasil mengatasi heteroskedastisitas. "
                f"Glejser p naik dari {ols_glejser_p:.4f} (OLS) menjadi {wls_glejser_p:.4f} (WLS) — "
                f"melewati ambang signifikansi α = {alpha_level}. "
                f"Estimasi WLS lebih efisien untuk data ini. Bobot: {wls_label}."
            )
        st.markdown(
            f'<div class="rs-narasi">📊 {narasi_wls}</div>',
            unsafe_allow_html=True,
        )

        # ── AI ─────────────────────────────────────────────────────────────────
        if ai_enabled:
            if st.button("🤖 Interpretasi WLS dengan AI", key="ai_wls_btn"):
                with st.spinner("🤖 AI sedang menganalisis WLS..."):
                    ai_wls = ai_interpret_wls_robust(
                        dep_var, ind_vars, coef_df_wls,
                        ols_glejser_p, wls_glejser_p,
                        ols_rmse, wls_rmse, wls_label, n_obs,
                        api_key, ai_provider,
                    )
                st.session_state.ai_cache["robust_wls"] = ai_wls
            if ss_get("ai_cache", {}).get("robust_wls"):
                st.markdown(
                    f'<div class="rs-ai-narasi">'
                    f'<span class="rs-ai-badge">✨ AI — {ai_provider.split("(")[0].strip()}</span><br/>'
                    f'{ss_get("ai_cache", {})["robust_wls"].replace(chr(10), "<br/>")}'
                    f"</div>",
                    unsafe_allow_html=True,
                )
        else:
            st.caption("💡 Aktifkan API Key untuk interpretasi AI.")

        # ── Simpan ke session state ────────────────────────────────────────────
        st.session_state["wls_result"] = {
            "dep_var":          dep_var,
            "ind_vars":         ind_vars,
            "weight_method":    wls_label,
            "r2":               float(wls_model.rsquared),
            "adj_r2":           float(wls_model.rsquared_adj),
            "ols_rmse":         ols_rmse,
            "wls_rmse":         wls_rmse,
            "ols_glejser_p":    ols_glejser_p,
            "wls_glejser_p":    wls_glejser_p,
            "n_changed":        n_changed_wls,
            "coef_df":          coef_df_wls,
        }

    # =========================================================================
    # TAB 3 — Perbandingan Model
    # =========================================================================
    with tab3:
        st.markdown("#### 📊 Perbandingan Model: OLS / RLM-Huber / RLM-Bisquare / WLS")
        st.markdown(
            "<p class='rs-section-sub'>Tabel ringkasan metrik semua model untuk memilih "
            "model terbaik sesuai kondisi data.</p>",
            unsafe_allow_html=True,
        )

        with st.spinner("Memfitting semua model untuk perbandingan..."):
            try:
                rlm_h  = _fit_rlm_huber(X, y)
                rlm_bs = _fit_rlm_bisquare(X, y)

                # WLS dengan bobot default 1/|residual|
                abs_resid = np.where(np.abs(ols_model.resid.values) < 1e-8,
                                     1e-8, np.abs(ols_model.resid.values))
                wls_auto = _fit_wls(X, y, 1.0 / abs_resid)

                comparison_rows = [
                    _model_summary_row("OLS (Baseline)",         ols_model,  "ols"),
                    _model_summary_row("RLM Huber-M",            rlm_h,      "rlm"),
                    _model_summary_row("RLM Bisquare",           rlm_bs,     "rlm"),
                    _model_summary_row("WLS (1/|ε|)",            wls_auto,   "wls"),
                ]
                comparison_df = pd.DataFrame(comparison_rows)

            except Exception as e:
                st.error(f"❌ Gagal membangun tabel perbandingan: {e}")
                st.stop()

        # ── Tentukan model terbaik (min RMSE, hanya model dengan RMSE numerik) ─
        numeric_rmse = comparison_df[comparison_df["RMSE"] != "–"]
        if not numeric_rmse.empty:
            best_idx   = numeric_rmse["RMSE"].astype(float).idxmin()
            best_model = comparison_df.loc[best_idx, "Model"]
        else:
            best_model = "OLS (Baseline)"

        # ── Tabel perbandingan ─────────────────────────────────────────────────
        st.markdown("##### Tabel Metrik Perbandingan")

        def _highlight_best(col):
            if col.name not in ("R²", "R² Adj", "RMSE"):
                return [""] * len(col)
            styles = []
            for v in col:
                try:
                    styles.append("")
                except Exception:
                    styles.append("")
            return styles

        st.dataframe(comparison_df, use_container_width=True, hide_index=True)

        st.info(
            f"✅ **Model terbaik berdasarkan RMSE: {best_model}** — "
            f"RMSE lebih rendah = prediksi lebih akurat."
        )

        # ── Plot RMSE ──────────────────────────────────────────────────────────
        try:
            rmse_vals = [float(r) for r in comparison_df["RMSE"] if r != "–"]
            rmse_models = comparison_df[comparison_df["RMSE"] != "–"]["Model"].tolist()
            if len(rmse_vals) >= 2:
                df_rmse = pd.DataFrame({"Model": rmse_models, "RMSE": rmse_vals})
                st.plotly_chart(_plot_model_comparison_bar(df_rmse), use_container_width=True)
        except Exception:
            pass

        # ── Panduan pemilihan model ────────────────────────────────────────────
        st.markdown("---")
        st.markdown("##### 📋 Panduan Pemilihan Model")
        st.markdown("""
        <div class="rs-narasi">
        <b>OLS (Ordinary Least Squares)</b> — Pilih jika: asumsi terpenuhi, tidak ada outlier ekstrem, 
        residual homoskedastis. Interpretasi paling mudah dan standar untuk publikasi.<br/><br/>
        <b>RLM Huber-M</b> — Pilih jika: terdapat outlier moderat (weight < 0.5 pada 5–15% data),
        distribusi residual sedikit heavy-tailed. Perubahan koefisien kecil → OLS masih OK.<br/><br/>
        <b>RLM Bisquare</b> — Pilih jika: outlier parah dan leverage points dominan.
        Lebih agresif dalam downweighting — cocok untuk data survei dengan respons ekstrem.<br/><br/>
        <b>WLS</b> — Pilih jika: heteroskedastisitas terdeteksi (Glejser/White p &lt; 0.05) dan
        pola varians dapat dimodelkan. WLS tidak menangani outlier sebaik RLM.
        </div>
        """, unsafe_allow_html=True)

        # ── AI interpretasi perbandingan ───────────────────────────────────────
        if ai_enabled:
            if st.button("🤖 Rekomendasi Model dengan AI", key="ai_comp_btn"):
                with st.spinner("🤖 AI sedang merekomendasikan model terbaik..."):
                    ai_comp = ai_interpret_model_comparison(
                        comparison_df, best_model, dep_var, api_key, ai_provider
                    )
                st.session_state.ai_cache["robust_comparison"] = ai_comp
            if ss_get("ai_cache", {}).get("robust_comparison"):
                st.markdown(
                    f'<div class="rs-ai-narasi">'
                    f'<span class="rs-ai-badge">✨ AI — {ai_provider.split("(")[0].strip()}</span><br/>'
                    f'{ss_get("ai_cache", {})["robust_comparison"].replace(chr(10), "<br/>")}'
                    f"</div>",
                    unsafe_allow_html=True,
                )
        else:
            st.caption("💡 Aktifkan API Key untuk rekomendasi AI.")

        # ── Simpan ke session state (untuk export) ────────────────────────────
        st.session_state["robust_comparison_result"] = {
            "dep_var":        dep_var,
            "ind_vars":       ind_vars,
            "comparison_df":  comparison_df,
            "best_model":     best_model,
            "n_obs":          n_obs,
        }
