"""
modules/regresi.py — Regresi & Prediksi
Ruang Statistika v4.2

Tier akses:
- FREE : OLS sederhana & berganda — koefisien, R², F-test, scatter/residual plot,
         export Excel.  Tanpa diagnostik lanjutan, tanpa prediksi manual, tanpa AI.
- PRO  : Semua fitur gratis + VIF, Cook's Distance, prediksi nilai baru,
         interpretasi AI, dan hasil tersimpan ke session_state untuk laporan.

Perbaikan v4.1:
- AI cache key konsisten: "regresi"
- Simpan regresi_result lengkap termasuk rmse, y_actual, y_pred, residuals
"""

import io
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from scipy import stats

from utils.stats_helpers import require_data, require_cols, ss_get
from utils.plot_helpers import plotly_residual_scatter
from utils.ai_helpers import call_ai_api, ai_interpret_regresi
from utils.effect_size import compute_cohens_f2, render_effect_size_card


def render(ctx: dict):
    license_info = ctx["license_info"]
    is_pro       = ctx["is_pro"]
    alpha_level  = ctx["alpha_level"]
    ai_enabled   = ctx["ai_enabled"]
    api_key      = ctx["anthropic_api_key"]
    ai_provider  = ctx["ai_provider"]

    st.markdown('<p class="rs-section-title">📈 Regresi & Prediksi</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="rs-section-sub">Analisis regresi linier sederhana & berganda. '
        'Fitur diagnostik lanjutan, prediksi, dan AI tersedia di Pro.</p>',
        unsafe_allow_html=True,
    )

    # Tidak ada hard-stop untuk user free — modul tetap berjalan dengan fitur terbatas

    df = require_data()
    if df is None:
        st.stop()
    cols = require_cols(df)
    if cols is None or len(cols) < 2:
        st.warning("⚠️ Pilih minimal 2 kolom numerik untuk analisis regresi.")
        st.stop()

    reg_mode = st.radio(
        "Mode Regresi:", ["Sederhana (1 prediktor)", "Berganda (≥2 prediktor)"],
        horizontal=True,
    )

    col_a, col_b = st.columns(2)
    with col_a:
        dep_var = st.selectbox("Variabel Dependen (Y):", cols)
    with col_b:
        remaining = [c for c in cols if c != dep_var]
        if reg_mode.startswith("Sederhana"):
            indep_vars = [st.selectbox("Variabel Independen (X):", remaining)]
        else:
            indep_vars = st.multiselect(
                "Variabel Independen (X):", remaining,
                default=remaining[:min(3, len(remaining))]
            )

    if not indep_vars:
        st.info("Pilih setidaknya satu variabel independen.")
        st.stop()

    data_reg = df[[dep_var] + indep_vars].dropna()
    if len(data_reg) < 5:
        st.error("❌ Data terlalu sedikit untuk regresi (minimal 5 baris valid).")
        st.stop()

    Y     = data_reg[dep_var].values
    X_raw = data_reg[indep_vars].values
    X_c   = np.column_stack([np.ones(len(X_raw)), X_raw])

    try:
        coeffs, _, _, _ = np.linalg.lstsq(X_c, Y, rcond=None)
        Y_pred = X_c @ coeffs
        resid  = Y - Y_pred
        n, k   = len(Y), len(indep_vars)
        ss_tot = np.sum((Y - Y.mean()) ** 2)
        ss_res = np.sum(resid ** 2)
        ss_reg = ss_tot - ss_res
        r2     = 1 - ss_res / ss_tot if ss_tot > 0 else 0
        r2_adj = 1 - (1 - r2) * (n - 1) / (n - k - 1) if n > k + 1 else 0
        mse    = ss_res / (n - k - 1) if n > k + 1 else 0
        rmse   = np.sqrt(mse)

        if k > 0 and ss_res > 0 and n > k + 1:
            f_stat = (ss_reg / k) / (ss_res / (n - k - 1))
            p_f    = 1 - stats.f.cdf(f_stat, k, n - k - 1)
        else:
            f_stat, p_f = 0.0, 1.0

        try:
            cov_matrix = mse * np.linalg.inv(X_c.T @ X_c)
            se_coeffs  = np.sqrt(np.diag(cov_matrix))
        except np.linalg.LinAlgError:
            se_coeffs = np.full(len(coeffs), np.nan)

        t_stats = coeffs / se_coeffs
        p_vals  = [2 * (1 - stats.t.cdf(abs(t), df=n - k - 1)) for t in t_stats]

    except Exception as e:
        st.error(f"❌ Gagal menghitung regresi: {e}")
        st.stop()

    # ── Koefisien ──────────────────────────────────────────────────────────
    coeff_labels = ["Konstanta (β₀)"] + [f"β_{v}" for v in indep_vars]
    coeff_df = pd.DataFrame({
        "Parameter":     coeff_labels,
        "Koefisien (β)": [round(float(c), 4) for c in coeffs],
        "Std. Error":    [round(float(s), 4) if not np.isnan(s) else "–" for s in se_coeffs],
        "t-hitung":      [round(float(t), 4) if not np.isnan(t) else "–" for t in t_stats],
        "p-value":       [round(float(p), 4) for p in p_vals],
        "Signifikan":    ["✓" if float(p) < alpha_level else "✗" for p in p_vals],
    })

    # ── Simpan ke session_state (Pro: lengkap; Free: ringkasan saja) ───────
    if is_pro:
        st.session_state["regresi_result"] = {
            "coef_table": coeff_df,
            "r2":         float(r2),
            "adj_r2":     float(r2_adj),
            "f_stat":     float(f_stat),
            "f_pvalue":   float(p_f),
            "rmse":       float(rmse),
            "y":          dep_var,
            "x":          indep_vars,
            "y_actual":   Y.tolist(),
            "y_pred":     Y_pred.tolist(),
            "residuals":  resid.tolist(),
        }

    # ── Metrik ─────────────────────────────────────────────────────────────
    st.markdown("#### Ringkasan Model Regresi")
    m1, m2, m3, m4 = st.columns(4)
    sig_f = "✅ Signifikan" if p_f < alpha_level else "❌ Tidak Signifikan"
    col_f = "#3b6d11" if p_f < alpha_level else "#a32d2d"
    for col, lbl, val, sub in zip(
        [m1, m2, m3, m4],
        ["R² (Koef. Determinasi)", "R² Adjusted", "F-Statistik", "RMSE"],
        [f"{r2:.4f}", f"{r2_adj:.4f}", f"{f_stat:.4f}", f"{rmse:.4f}"],
        [f"{r2*100:.1f}% varians dijelaskan", "",
         f"{sig_f} (p={p_f:.4f})", ""],
    ):
        extra = f'<div class="rs-metric-sub" style="color:{col_f}">{sub}</div>' if sub else ""
        col.markdown(
            f'<div class="rs-metric"><div class="rs-metric-label">{lbl}</div>'
            f'<div class="rs-metric-value">{val}</div>{extra}</div>',
            unsafe_allow_html=True,
        )

    st.markdown("#### Koefisien Regresi")
    st.dataframe(coeff_df, use_container_width=True, hide_index=True)

    f2 = compute_cohens_f2(r2)
    render_effect_size_card("f2", f2)

    # Persamaan regresi
    eq_parts = [f"{coeffs[0]:.4f}"]
    for i, v in enumerate(indep_vars):
        sign = "+" if coeffs[i + 1] >= 0 else "-"
        eq_parts.append(f"{sign} {abs(coeffs[i+1]):.4f}×{v}")
    eq_str = f"**{dep_var}** = " + " ".join(eq_parts)

    sig_model = "signifikan secara statistik (F-test)." if p_f < alpha_level else \
                "tidak signifikan secara keseluruhan."
    st.markdown(
        f'<div class="rs-narasi">📐 <b>Persamaan Regresi:</b><br/>{eq_str}<br/><br/>'
        f"Model menjelaskan <b>{r2*100:.1f}%</b> variasi pada <b>{dep_var}</b>. "
        f"Model {sig_model}</div>",
        unsafe_allow_html=True,
    )

    # ── Visualisasi ─────────────────────────────────────────────────────────
    st.markdown("---")
    tab_r1, tab_r2 = st.tabs(["📊 Aktual vs Prediksi", "📉 Plot Residual"])
    with tab_r1:
        if reg_mode.startswith("Sederhana"):
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=data_reg[indep_vars[0]], y=Y,
                mode="markers", name="Data Aktual",
                marker=dict(color="#185FA5", size=6, opacity=0.7)
            ))
            fig.add_trace(go.Scatter(
                x=data_reg[indep_vars[0]], y=Y_pred,
                mode="lines", name="Garis Regresi",
                line=dict(color="#E24B4A", width=2)
            ))
            fig.update_layout(
                title=f"Regresi: {dep_var} ~ {indep_vars[0]}",
                xaxis_title=indep_vars[0], yaxis_title=dep_var,
                template="plotly_white", height=380,
                margin=dict(l=30, r=30, t=50, b=30)
            )
        else:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=Y_pred, y=Y, mode="markers",
                marker=dict(color="#185FA5", size=6, opacity=0.7), name="Aktual"
            ))
            max_val = max(Y.max(), Y_pred.max())
            min_val = min(Y.min(), Y_pred.min())
            fig.add_trace(go.Scatter(
                x=[min_val, max_val], y=[min_val, max_val],
                mode="lines", name="Perfect Fit",
                line=dict(color="#E24B4A", dash="dash")
            ))
            fig.update_layout(
                title="Aktual vs Prediksi",
                xaxis_title="Prediksi", yaxis_title="Aktual",
                template="plotly_white", height=380,
                margin=dict(l=30, r=30, t=50, b=30)
            )
        st.plotly_chart(fig, use_container_width=True)

    with tab_r2:
        st.plotly_chart(
            plotly_residual_scatter(Y_pred, resid, dep_var),
            use_container_width=True,
        )

    # ── Export Excel ─────────────────────────────────────────────────────────
    st.markdown("---")
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        coeff_df.to_excel(writer, sheet_name="Koefisien", index=False)
        pd.DataFrame({
            "Metrik": ["R²", "R² Adj", "F-stat", "p-F", "RMSE"],
            "Nilai":  [r2, r2_adj, f_stat, p_f, rmse]
        }).to_excel(writer, sheet_name="Ringkasan", index=False)
        pd.DataFrame({
            "Y_Aktual":   Y.tolist(),
            "Y_Prediksi": Y_pred.tolist(),
            "Residual":   resid.tolist(),
        }).to_excel(writer, sheet_name="Aktual_Prediksi", index=False)
    buf.seek(0)
    st.download_button(
        "⬇️ Export ke Excel (.xlsx)", data=buf,
        file_name=f"Regresi_{dep_var}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    # ── Fitur Pro — diagnostik lanjutan & AI ─────────────────────────────────
    st.markdown("---")
    if not is_pro:
        st.info(
            "🔒 **Fitur Pro:** Uji VIF (multikolinearitas), Cook's Distance, "
            "prediksi nilai baru, dan interpretasi AI — tersedia di **Paket Akademisi Pro**.\n\n"
            "👉 [Dapatkan akses Pro](https://lynk.id/ruangstatistika)"
        )
        return

    # ── PRO ONLY: Diagnostik lanjutan ────────────────────────────────────────
    st.markdown("#### 🔍 Diagnostik Lanjutan (Pro)")

    with st.expander("Uji VIF (Multikolinearitas)", expanded=False):
        if len(indep_vars) >= 2:
            try:
                from statsmodels.stats.outliers_influence import variance_inflation_factor
                vif_data = pd.DataFrame({
                    "Variabel": indep_vars,
                    "VIF": [
                        round(variance_inflation_factor(X_raw, i), 4)
                        for i in range(X_raw.shape[1])
                    ],
                })
                vif_data["Interpretasi"] = vif_data["VIF"].apply(
                    lambda v: "✅ OK" if v < 5 else ("⚠️ Sedang" if v < 10 else "❌ Tinggi")
                )
                st.dataframe(vif_data, use_container_width=True, hide_index=True)
                vif_max = vif_data["VIF"].max()
                if vif_max < 5:
                    st.success(f"✅ VIF max = {vif_max:.2f} — tidak ada multikolinearitas.")
                elif vif_max < 10:
                    st.warning(f"⚠️ VIF max = {vif_max:.2f} — multikolinearitas sedang.")
                else:
                    st.error(f"❌ VIF max = {vif_max:.2f} — multikolinearitas tinggi.")
                st.session_state["regresi_result"]["vif"] = vif_data
            except ImportError:
                st.warning("Statsmodels tidak tersedia untuk VIF.")
        else:
            st.info("VIF hanya relevan untuk regresi berganda (≥ 2 prediktor).")

    with st.expander("Cook's Distance (Influential Points)", expanded=False):
        try:
            from statsmodels.stats.outliers_influence import OLSInfluence
            import statsmodels.api as sm
            model_sm = sm.OLS(Y, X_c).fit()
            influence = OLSInfluence(model_sm)
            cooks_d   = influence.cooks_distance[0]
            threshold = 4 / n
            n_influential = int((cooks_d > threshold).sum())
            fig_cook = go.Figure()
            fig_cook.add_trace(go.Bar(
                x=list(range(n)), y=cooks_d,
                marker_color=["#E24B4A" if d > threshold else "#185FA5" for d in cooks_d],
                name="Cook's D",
            ))
            fig_cook.add_hline(y=threshold, line_dash="dash", line_color="orange",
                               annotation_text=f"Threshold = {threshold:.4f}")
            fig_cook.update_layout(
                title="Cook's Distance", xaxis_title="Observasi",
                yaxis_title="Cook's D", template="plotly_white",
                height=350, margin=dict(l=30, r=30, t=50, b=30)
            )
            st.plotly_chart(fig_cook, use_container_width=True)
            if n_influential:
                st.warning(f"⚠️ {n_influential} observasi berpengaruh besar (Cook's D > {threshold:.4f}).")
            else:
                st.success("✅ Tidak ada observasi dengan pengaruh ekstrem.")
        except Exception as e:
            st.warning(f"Cook's Distance tidak dapat dihitung: {e}")

    # ── PRO ONLY: Prediksi nilai baru ─────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 🔮 Prediksi Nilai Baru (Pro)")
    with st.form("pred_form"):
        pred_inputs = {}
        pred_cols = st.columns(min(len(indep_vars), 3))
        for i, var in enumerate(indep_vars):
            with pred_cols[i % len(pred_cols)]:
                mean_val = float(data_reg[var].mean())
                pred_inputs[var] = st.number_input(
                    f"{var}", value=mean_val, format="%.4f", key=f"pred_{var}"
                )
        submitted = st.form_submit_button("▶ Prediksi")
    if submitted:
        x_new = np.array([1.0] + [pred_inputs[v] for v in indep_vars])
        y_new = float(x_new @ coeffs)
        try:
            se_pred = float(np.sqrt(mse * (1 + x_new @ np.linalg.inv(X_c.T @ X_c) @ x_new)))
            t_crit  = stats.t.ppf(1 - alpha_level / 2, df=n - k - 1)
            ci_lo   = y_new - t_crit * se_pred
            ci_hi   = y_new + t_crit * se_pred
            ci_str  = f"[{ci_lo:.4f}, {ci_hi:.4f}]"
        except Exception:
            ci_str = "N/A"
        st.markdown(
            f'<div class="rs-narasi">🔮 <b>Prediksi {dep_var}</b> = '
            f'<span style="font-size:1.3em; font-weight:700">{y_new:.4f}</span><br/>'
            f'CI {int((1-alpha_level)*100)}%: {ci_str}</div>',
            unsafe_allow_html=True,
        )

    # ── PRO ONLY: AI Interpretasi ─────────────────────────────────────────────
    if ai_enabled:
        st.markdown("---")
        if st.button("🤖 Interpretasi Regresi dengan AI", key="ai_reg_btn"):
            result_data = {
                "y":         dep_var,
                "x":         indep_vars,
                "r2":        r2,
                "adj_r2":    r2_adj,
                "f_pvalue":  p_f,
                "rmse":      rmse,
                "coef_table": coeff_df,
            }
            with st.spinner("🤖 AI menganalisis regresi…"):
                ai_reg = ai_interpret_regresi(result_data, api_key, ai_provider)
            if "ai_cache" not in st.session_state:
                st.session_state.ai_cache = {}
            st.session_state.ai_cache["regresi"] = ai_reg

        cached = ss_get("ai_cache", {}).get("regresi")
        if cached:
            st.markdown(
                f'<div class="rs-ai-narasi">'
                f'<span class="rs-ai-badge">✨ AI — {ai_provider.split("(")[0].strip()}</span><br/>'
                f'{cached.replace(chr(10), "<br/>")}'
                f"</div>",
                unsafe_allow_html=True,
            )
