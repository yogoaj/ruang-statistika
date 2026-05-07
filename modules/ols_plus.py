"""
modules/ols_plus.py — OLS+ (VIF, Glejser, Autokorelasi, Normalitas Residual) (Pro)
Ruang Statistika v4.0
"""

import io
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from scipy import stats

from utils.auth import require_pro
from utils.stats_helpers import require_data, require_cols, ols_advanced, ss_get
from utils.plot_helpers import plotly_vif_bar, plotly_qq
from utils.ai_helpers import call_ai_api
from utils.effect_size import interpret_effect_size, render_effect_size_card


def render(ctx: dict):
    license_info = ctx["license_info"]
    alpha_level  = ctx["alpha_level"]
    ai_enabled   = ctx["ai_enabled"]
    api_key      = ctx["anthropic_api_key"]
    ai_provider  = ctx["ai_provider"]

    st.markdown('<p class="rs-section-title">📐 Regresi OLS+ (Uji Asumsi Klasik)</p>',
                unsafe_allow_html=True)
    st.markdown(
        '<p class="rs-section-sub">Statsmodels OLS lengkap: VIF, Glejser, White test, '
        'Durbin-Watson, Breusch-Godfrey, normalitas residual, plot diagnostik.</p>',
        unsafe_allow_html=True,
    )

    if not require_pro(license_info, "Regresi OLS+"):
        st.stop()

    df = require_data()
    if df is None:
        st.stop()
    cols = require_cols(df)
    if cols is None or len(cols) < 2:
        st.warning("⚠️ Pilih minimal 2 kolom numerik.")
        st.stop()

    col_a, col_b = st.columns(2)
    with col_a:
        dep_var = st.selectbox("Variabel Dependen (Y):", cols, key="ols_y")
    with col_b:
        remaining    = [c for c in cols if c != dep_var]
        indep_vars   = st.multiselect("Variabel Independen (X):", remaining,
                                      default=remaining[:min(3, len(remaining))],
                                      key="ols_x")

    if not indep_vars:
        st.info("Pilih setidaknya satu variabel independen.")
        st.stop()

    if st.button("▶ Jalankan OLS+ Analysis", type="primary"):
        try:
            with st.spinner("⏳ Menghitung OLS dan uji asumsi..."):
                ols_model, vif_df, glejser_model = ols_advanced(df, dep_var, indep_vars)
            st.session_state["ols_result"] = {
                "model": ols_model, "vif": vif_df, "glejser": glejser_model,
                "y": dep_var, "x": indep_vars,
                # Data tambahan untuk export laporan
                "coef_table": pd.DataFrame({
                    "Parameter":    ols_model.params.index.tolist(),
                    "β (Koefisien)": ols_model.params.values.round(4).tolist(),
                    "Std. Error":   ols_model.bse.values.round(4).tolist(),
                    "t-hitung":     ols_model.tvalues.values.round(4).tolist(),
                    "p-value":      ols_model.pvalues.values.round(4).tolist(),
                    "Signifikan":   ["✓" if p < 0.05 else "✗" for p in ols_model.pvalues],
                }),
                "r2":        float(ols_model.rsquared),
                "adj_r2":    float(ols_model.rsquared_adj),
                "f_pvalue":  float(ols_model.f_pvalue),
                "y_actual":  ols_model.model.endog.tolist(),
                "y_pred":    ols_model.fittedvalues.tolist(),
                "residuals": ols_model.resid.tolist(),
                "durbin_watson": None,  # diisi setelah kalkulasi di tab autokorelasi
                "vif_max":   float(vif_df["VIF"].max()) if not vif_df.empty else None,
            }
        except Exception as e:
            st.error(f"❌ Gagal: {e}")
            st.stop()

    res = ss_get("ols_result")
    if res is None or res.get("y") != dep_var or res.get("x") != indep_vars:
        st.info("Klik **▶ Jalankan OLS+ Analysis** untuk memulai.")
        st.stop()

    ols_model     = res["model"]
    vif_df        = res["vif"]
    glejser_model = res["glejser"]

    tabs = st.tabs([
        "📊 Ringkasan OLS",
        "🔍 VIF (Multikolinearitas)",
        "📐 Glejser (Heterosk.)",
        "🔄 Autokorelasi",
        "📈 Normalitas Residual",
        "🗺️ Plot Diagnostik",
    ])

    # ── Tab 1: Ringkasan ──
    with tabs[0]:
        st.markdown("#### Ringkasan Model OLS (statsmodels)")
        r2_ols    = round(ols_model.rsquared, 4)
        r2adj_ols = round(ols_model.rsquared_adj, 4)
        fstat_ols = round(ols_model.fvalue, 4)
        fpval_ols = round(ols_model.f_pvalue, 4)
        n_obs     = int(ols_model.nobs)

        m1, m2, m3, m4 = st.columns(4)
        col_f = "#3b6d11" if fpval_ols < alpha_level else "#a32d2d"
        sig_f = "✅ Sig." if fpval_ols < alpha_level else "❌ Tidak Sig."
        for col, lbl, val, sub in zip(
            [m1, m2, m3, m4],
            ["R²", "R² Adjusted", "F-Statistik", "Observasi (N)"],
            [r2_ols, r2adj_ols, fstat_ols, n_obs],
            [f"{r2_ols*100:.1f}% varians", "", f"{sig_f} (p={fpval_ols})", ""],
        ):
            col.markdown(
                f'<div class="rs-metric"><div class="rs-metric-label">{lbl}</div>'
                f'<div class="rs-metric-value">{val}</div>'
                f'<div class="rs-metric-sub" style="color:{col_f}">{sub}</div></div>',
                unsafe_allow_html=True,
            )

        params, bse, tvalues, pvalues = (
            ols_model.params, ols_model.bse, ols_model.tvalues, ols_model.pvalues
        )
        conf = ols_model.conf_int()
        coeff_ols_df = pd.DataFrame({
            "Parameter":    params.index,
            "β (Koefisien)": params.values.round(4),
            "Std. Error":   bse.values.round(4),
            "t-hitung":     tvalues.values.round(4),
            "p-value":      pvalues.values.round(4),
            "CI Lower":     conf.iloc[:, 0].round(4),
            "CI Upper":     conf.iloc[:, 1].round(4),
            "Signifikan":   ["✓" if p < alpha_level else "✗" for p in pvalues],
        })
        st.dataframe(coeff_ols_df, use_container_width=True, hide_index=True)
        with st.expander("📄 Output Lengkap statsmodels"):
            st.text(ols_model.summary().as_text())

        from utils.effect_size import compute_cohens_f2, render_effect_size_card

        f2 = compute_cohens_f2(r2_ols)
        render_effect_size_card("f2", f2)

        # Export Excel
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            coeff_ols_df.to_excel(writer, sheet_name="Koefisien_OLS", index=False)
            vif_df.to_excel(writer, sheet_name="VIF", index=False)
        buf.seek(0)
        st.download_button("⬇️ Export Hasil ke Excel", data=buf,
                           file_name=f"OLS_{dep_var}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        if ai_enabled:
            if st.button("🤖 Interpretasi OLS+ dengan AI", key="ai_ols_btn"):
                prompt = f"""
Hasil regresi OLS (statsmodels) untuk variabel dependen: {dep_var}
Variabel independen: {', '.join(indep_vars)}

RINGKASAN: R² = {r2_ols}, R² Adj = {r2adj_ols}, F = {fstat_ols}, p = {fpval_ols}, N = {n_obs}

KOEFISIEN:
{coeff_ols_df.to_string(index=False)}

Berikan interpretasi komprehensif dalam Bahasa Indonesia:
1. Kualitas dan signifikansi model (R², F-test)
2. Interpretasi koefisien yang signifikan
3. Persamaan regresi dan maknanya
4. Rekomendasi analisis lanjutan
Format: 3-4 paragraf akademis.
"""
                with st.spinner("🤖 AI menganalisis..."):
                    ai_ols = call_ai_api(prompt, api_key=api_key, provider=ai_provider)
                if "ai_cache" not in st.session_state:
                    st.session_state.ai_cache = {}
                st.session_state.ai_cache["ols"] = ai_ols

            if ss_get("ai_cache", {}).get("ols"):
                st.markdown(
                    f'<div class="rs-ai-narasi">'
                    f'<span class="rs-ai-badge">✨ AI — {ai_provider.split("(")[0].strip()}</span><br/>'
                    f'{ss_get("ai_cache", {})["ols"].replace(chr(10), "<br/>")}'
                    f"</div>",
                    unsafe_allow_html=True,
                )

    # ── Tab 2: VIF ──
    with tabs[1]:
        st.markdown("#### Uji Multikolinearitas — Variance Inflation Factor (VIF)")
        st.info("VIF > 10 mengindikasikan masalah multikolinearitas yang serius.")
        st.dataframe(vif_df, use_container_width=True, hide_index=True)
        st.plotly_chart(plotly_vif_bar(vif_df), use_container_width=True)
        n_mk = (vif_df["VIF"] > 10).sum()
        if n_mk == 0:
            st.markdown('<div class="rs-narasi">✅ Tidak ditemukan masalah multikolinearitas. Semua VIF ≤ 10.</div>',
                        unsafe_allow_html=True)
        else:
            bad = vif_df[vif_df["VIF"] > 10]["Variabel"].tolist()
            st.markdown(f'<div class="rs-narasi">⚠️ <b>{n_mk}</b> variabel memiliki VIF > 10: <b>{", ".join(bad)}</b>. '
                        f'Pertimbangkan menghapus salah satu atau gunakan ridge regression.</div>',
                        unsafe_allow_html=True)

    # ── Tab 3: Glejser ──
    with tabs[2]:
        st.markdown("#### Uji Heteroskedastisitas — Glejser Test")
        st.info("H₀: tidak ada heteroskedastisitas. Variabel signifikan (p < α) → indikasi heterosk.")
        gp = glejser_model.params
        gpv = glejser_model.pvalues
        glejser_df = pd.DataFrame({
            "Parameter":       gp.index,
            "Koefisien":       gp.values.round(4),
            "p-value":         gpv.values.round(4),
            "Indikasi Heterosk.": ["⚠️ Ya" if (p < alpha_level and idx != "const") else "✓ Tidak"
                                   for idx, p in zip(gp.index, gpv)],
        })
        st.dataframe(glejser_df, use_container_width=True, hide_index=True)
        n_h = sum(1 for idx, p in zip(gp.index, gpv) if idx != "const" and p < alpha_level)
        if n_h == 0:
            st.markdown('<div class="rs-narasi">✅ Tidak ditemukan indikasi heteroskedastisitas (Glejser).</div>',
                        unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="rs-narasi">⚠️ Ditemukan indikasi heteroskedastisitas pada <b>{n_h}</b> variabel. '
                        f'Pertimbangkan transformasi log/sqrt, WLS, atau robust SE (HC).</div>',
                        unsafe_allow_html=True)
        with st.expander("📄 Output Lengkap Glejser"):
            st.text(glejser_model.summary().as_text())

        # White test (tambahan)
        st.markdown("---")
        st.markdown("#### White Test (Alternatif Glejser)")
        try:
            from statsmodels.stats.diagnostic import het_white
            import statsmodels.api as sm
            subset = df[[dep_var] + indep_vars].dropna()
            X_c    = sm.add_constant(subset[indep_vars])
            resid  = ols_model.resid
            wstat, wpval, wf, wfpval = het_white(resid, X_c)
            st.markdown(
                f'<div class="rs-narasi">🔬 <b>White Test:</b> LM Statistic = {wstat:.4f}, '
                f"p-value = {wpval:.4f}. "
                f'{"⚠️ Terindikasi heteroskedastisitas (p < α)." if wpval < alpha_level else "✅ Tidak ada indikasi heteroskedastisitas."}'
                f"</div>",
                unsafe_allow_html=True,
            )
        except Exception as e:
            st.caption(f"White test tidak tersedia: {e}")

    # ── Tab 4: Autokorelasi ──
    with tabs[3]:
        st.markdown("#### Uji Autokorelasi")
        try:
            from statsmodels.stats.stattools import durbin_watson
            from statsmodels.stats.diagnostic import acorr_breusch_godfrey

            dw_stat = durbin_watson(ols_model.resid)
            if "ols_result" in st.session_state:
                st.session_state["ols_result"]["durbin_watson"] = float(dw_stat)
            st.markdown(
                f'<div class="rs-narasi">🔄 <b>Durbin-Watson:</b> {dw_stat:.4f}<br/>'
                f"Nilai DW mendekati 2 = tidak ada autokorelasi. "
                f"DW < 1.5 → autokorelasi positif. DW > 2.5 → autokorelasi negatif.</div>",
                unsafe_allow_html=True,
            )

            bg_stat, bg_pval, _, _ = acorr_breusch_godfrey(ols_model, nlags=2)
            st.markdown(
                f'<div class="rs-narasi">📊 <b>Breusch-Godfrey (lag=2):</b> '
                f"χ² = {bg_stat:.4f}, p = {bg_pval:.4f}. "
                f'{"⚠️ Ada autokorelasi (p < α)." if bg_pval < alpha_level else "✅ Tidak ada autokorelasi."}'
                f"</div>",
                unsafe_allow_html=True,
            )

            # Residual time-series plot
            fig_rts = go.Figure()
            fig_rts.add_trace(go.Scatter(
                x=list(range(len(ols_model.resid))), y=ols_model.resid.values,
                mode="lines+markers", marker=dict(size=4), line=dict(color="#185FA5"),
                name="Residual"
            ))
            fig_rts.add_hline(y=0, line_dash="dash", line_color="#E24B4A")
            fig_rts.update_layout(title="Residual Time-Series Plot",
                                   xaxis_title="Observasi", yaxis_title="Residual",
                                   template="plotly_white", height=350,
                                   margin=dict(l=30, r=30, t=50, b=30))
            st.plotly_chart(fig_rts, use_container_width=True)

        except Exception as e:
            st.warning(f"Uji autokorelasi tidak tersedia: {e}")

    # ── Tab 5: Normalitas Residual ──
    with tabs[4]:
        st.markdown("#### Normalitas Residual")
        resid_series = ols_model.resid
        sw_stat, sw_p = stats.shapiro(resid_series)
        st.markdown(
            f'<div class="rs-narasi">🔔 <b>Shapiro-Wilk pada Residual:</b> '
            f"W = {sw_stat:.4f}, p = {sw_p:.4f}. "
            f'{"✅ Residual berdistribusi normal (p > 0.05)." if sw_p > 0.05 else "⚠️ Residual TIDAK berdistribusi normal (p ≤ 0.05). Pertimbangkan transformasi data."}'
            f"</div>",
            unsafe_allow_html=True,
        )
        col1, col2 = st.columns(2)
        with col1:
            fig_rh = go.Figure(go.Histogram(x=resid_series, nbinsx=20,
                                             marker_color="#185FA5", opacity=0.75))
            fig_rh.update_layout(title="Histogram Residual", template="plotly_white",
                                  height=320, margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig_rh, use_container_width=True)
        with col2:
            st.plotly_chart(
                plotly_qq(pd.Series(resid_series), "Q-Q Plot Residual"),
                use_container_width=True,
            )

    # ── Tab 6: Plot Diagnostik ──
    with tabs[5]:
        st.markdown("#### Plot Diagnostik Lengkap")
        fitted    = ols_model.fittedvalues
        resid_raw = ols_model.resid

        col1, col2 = st.columns(2)
        with col1:
            # Residuals vs Fitted
            fig1 = go.Figure()
            fig1.add_trace(go.Scatter(x=fitted, y=resid_raw, mode="markers",
                                       marker=dict(color="#185FA5", size=5, opacity=0.7)))
            fig1.add_hline(y=0, line_dash="dash", line_color="#E24B4A")
            fig1.update_layout(title="Residuals vs Fitted",
                                xaxis_title="Fitted", yaxis_title="Residual",
                                template="plotly_white", height=320,
                                margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig1, use_container_width=True)
        with col2:
            # Scale-Location
            sqrt_abs_resid = np.sqrt(np.abs(resid_raw))
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(x=fitted, y=sqrt_abs_resid, mode="markers",
                                       marker=dict(color="#3B6D11", size=5, opacity=0.7)))
            fig2.update_layout(title="Scale-Location Plot",
                                xaxis_title="Fitted", yaxis_title="√|Residual|",
                                template="plotly_white", height=320,
                                margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig2, use_container_width=True)

        col3, col4 = st.columns(2)
        with col3:
            st.plotly_chart(plotly_qq(pd.Series(resid_raw), "Normal Q-Q Residual"),
                            use_container_width=True)
        with col4:
            # Cook's Distance
            try:
                influence  = ols_model.get_influence()
                cooks_d, _ = influence.cooks_distance
                fig4 = go.Figure()
                fig4.add_trace(go.Bar(x=list(range(len(cooks_d))), y=cooks_d,
                                       marker_color="#185FA5", name="Cook's D"))
                thresh = 4 / len(cooks_d)
                fig4.add_hline(y=thresh, line_dash="dash", line_color="#E24B4A",
                                annotation_text=f"Threshold {thresh:.3f}")
                fig4.update_layout(title="Cook's Distance",
                                    xaxis_title="Observasi", yaxis_title="Cook's D",
                                    template="plotly_white", height=320,
                                    margin=dict(l=20, r=20, t=40, b=20))
                st.plotly_chart(fig4, use_container_width=True)
            except Exception:
                st.caption("Cook's Distance tidak tersedia.")
