"""
modules/time_series.py — Analisis Deret Waktu / Time Series (Pro)
Ruang Statistika v4.9

Tab 1 — Uji Stasioneritas  : ADF + KPSS
Tab 2 — Dekomposisi         : Additive / Multiplicative seasonal decomposition
Tab 3 — ACF / PACF Plot     : Korelogram untuk identifikasi order
Tab 4 — Model ARIMA/SARIMA  : Auto-ARIMA + manual order + forecast
Tab 5 — Evaluasi & Forecast : RMSE, MAE, MAPE, plot forecast + CI

Tier: Pro
Session key: st.session_state["time_series_result"]
"""

import io
import warnings
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from utils.auth import require_pro
from utils.stats_helpers import require_data, require_cols, ss_get
from utils.ai_helpers import call_ai_api

warnings.filterwarnings("ignore")

# ── Konstanta warna ───────────────────────────────────────────────────────────
BLUE   = "#185FA5"
GREEN  = "#3B6D11"
RED    = "#A32D2D"
RED2   = "#E24B4A"
PURPLE = "#6B21A8"
ORANGE = "#E05C2A"


# ═══════════════════════════════════════════════════════════════════════════════
# Helper: metrik evaluasi
# ═══════════════════════════════════════════════════════════════════════════════

def _metrics(actual: np.ndarray, predicted: np.ndarray) -> dict:
    actual    = np.array(actual, dtype=float)
    predicted = np.array(predicted, dtype=float)
    mask = ~np.isnan(actual) & ~np.isnan(predicted)
    actual, predicted = actual[mask], predicted[mask]
    if len(actual) == 0:
        return {"RMSE": np.nan, "MAE": np.nan, "MAPE": np.nan}
    rmse = float(np.sqrt(np.mean((actual - predicted) ** 2)))
    mae  = float(np.mean(np.abs(actual - predicted)))
    with np.errstate(divide="ignore", invalid="ignore"):
        mape_arr = np.abs((actual - predicted) / actual)
        mape = float(np.nanmean(mape_arr[np.isfinite(mape_arr)])) * 100
    return {"RMSE": round(rmse, 4), "MAE": round(mae, 4), "MAPE": round(mape, 2)}


def _metric_card(col, label: str, value, sub: str = "", color: str = BLUE):
    col.markdown(
        f'<div class="rs-metric">'
        f'<div class="rs-metric-label">{label}</div>'
        f'<div class="rs-metric-value" style="color:{color}">{value}</div>'
        f'<div class="rs-metric-sub">{sub}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _narasi(text: str, color: str = BLUE):
    st.markdown(
        f'<div class="rs-narasi" style="border-left-color:{color};">{text}</div>',
        unsafe_allow_html=True,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Tab 1 — Uji Stasioneritas
# ═══════════════════════════════════════════════════════════════════════════════

def _tab_stasioner(series: pd.Series, col_name: str, alpha: float):
    from statsmodels.tsa.stattools import adfuller, kpss

    st.markdown("#### 🔍 Uji Stasioneritas")
    st.markdown("""
    <div class="rs-narasi">
    📖 <b>Stasioneritas</b> = mean, varians, dan autokovariansi data tidak berubah seiring waktu.
    ARIMA mensyaratkan data stasioner. <br/>
    <b>ADF</b>: H₀ = ada unit root (tidak stasioner) → p kecil = stasioner.<br/>
    <b>KPSS</b>: H₀ = stasioner → p kecil = <i>tidak</i> stasioner.
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    # ADF Test
    try:
        adf_stat, adf_p, adf_lags, adf_nobs, adf_crit, _ = adfuller(series.dropna(), autolag="AIC")
        adf_stationary = adf_p < alpha
        with col1:
            st.markdown("##### Augmented Dickey-Fuller (ADF)")
            adf_df = pd.DataFrame([{
                "Statistik ADF": round(adf_stat, 4),
                "p-value":       round(adf_p, 4),
                "Lag digunakan": adf_lags,
                "N observasi":   adf_nobs,
            }])
            st.dataframe(adf_df, use_container_width=True, hide_index=True)
            crit_df = pd.DataFrame([
                {"Level": k, "Nilai Kritis": round(v, 4)}
                for k, v in adf_crit.items()
            ])
            st.dataframe(crit_df, use_container_width=True, hide_index=True)
            col_adf = GREEN if adf_stationary else RED
            _narasi(
                f"ADF: t = {adf_stat:.4f}, p = {adf_p:.4f} → "
                f"<b style='color:{col_adf}'>{'✅ Stasioner' if adf_stationary else '❌ Tidak Stasioner'}</b> (α={alpha})",
                color=col_adf,
            )
    except Exception as e:
        adf_stat = adf_p = np.nan
        adf_stationary = False
        with col1:
            st.error(f"ADF gagal: {e}")

    # KPSS Test
    try:
        kpss_stat, kpss_p, kpss_lags, kpss_crit = kpss(series.dropna(), regression="c", nlags="auto")
        kpss_stationary = kpss_p >= alpha  # H0: stasioner, tolak jika p < alpha
        with col2:
            st.markdown("##### KPSS Test")
            kpss_df = pd.DataFrame([{
                "Statistik KPSS": round(kpss_stat, 4),
                "p-value":        round(kpss_p, 4),
                "Lag digunakan":  kpss_lags,
            }])
            st.dataframe(kpss_df, use_container_width=True, hide_index=True)
            crit_df2 = pd.DataFrame([
                {"Level": k, "Nilai Kritis": round(v, 4)}
                for k, v in kpss_crit.items()
            ])
            st.dataframe(crit_df2, use_container_width=True, hide_index=True)
            col_kpss = GREEN if kpss_stationary else RED
            _narasi(
                f"KPSS: stat = {kpss_stat:.4f}, p = {kpss_p:.4f} → "
                f"<b style='color:{col_kpss}'>{'✅ Stasioner' if kpss_stationary else '❌ Tidak Stasioner'}</b> (α={alpha})",
                color=col_kpss,
            )
    except Exception as e:
        kpss_stat = kpss_p = np.nan
        kpss_stationary = True
        with col2:
            st.error(f"KPSS gagal: {e}")

    # Kesimpulan gabungan
    if adf_stationary and kpss_stationary:
        conclusion = "✅ <b>Stasioner</b> — kedua uji sepakat. Data siap untuk ARIMA tanpa differencing."
        col_conc = GREEN
        d_suggest = 0
    elif not adf_stationary and not kpss_stationary:
        conclusion = "❌ <b>Tidak Stasioner</b> — kedua uji sepakat. Gunakan differencing (d≥1) sebelum ARIMA."
        col_conc = RED
        d_suggest = 1
    elif adf_stationary and not kpss_stationary:
        conclusion = "⚠️ <b>Hasil Bertentangan</b> — ADF: stasioner, KPSS: tidak stasioner. Cek tren/musiman."
        col_conc = ORANGE
        d_suggest = 1
    else:
        conclusion = "⚠️ <b>Hasil Bertentangan</b> — ADF: tidak stasioner, KPSS: stasioner. Kemungkinan stasioner lemah."
        col_conc = ORANGE
        d_suggest = 0

    _narasi(f"📋 <b>Kesimpulan:</b> {conclusion}", color=col_conc)

    # Plot time series
    st.markdown("##### Plot Deret Waktu")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=list(range(len(series))), y=series.values,
        mode="lines", line=dict(color=BLUE, width=1.5), name=col_name,
    ))
    fig.add_trace(go.Scatter(
        x=list(range(len(series))),
        y=pd.Series(series.values).rolling(min(12, max(3, len(series)//10))).mean().values,
        mode="lines", line=dict(color=RED2, width=2, dash="dash"), name="Moving Average",
    ))
    fig.update_layout(
        title=f"Deret Waktu: {col_name}",
        xaxis_title="Indeks Waktu", yaxis_title=col_name,
        template="plotly_white", height=380,
        margin=dict(l=30, r=30, t=50, b=30),
        legend=dict(orientation="h", y=-0.2),
    )
    st.plotly_chart(fig, use_container_width=True)

    return {
        "adf_stat": round(float(adf_stat), 4) if not np.isnan(adf_stat) else None,
        "adf_p":    round(float(adf_p), 4) if not np.isnan(adf_p) else None,
        "adf_stationary": bool(adf_stationary),
        "kpss_stat": round(float(kpss_stat), 4) if not np.isnan(kpss_stat) else None,
        "kpss_p":   round(float(kpss_p), 4) if not np.isnan(kpss_p) else None,
        "kpss_stationary": bool(kpss_stationary),
        "d_suggest": d_suggest,
        "conclusion": conclusion.replace("<b>", "").replace("</b>", ""),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Tab 2 — Dekomposisi Musiman
# ═══════════════════════════════════════════════════════════════════════════════

def _tab_decompose(series: pd.Series, col_name: str):
    from statsmodels.tsa.seasonal import seasonal_decompose

    st.markdown("#### 📊 Dekomposisi Musiman")

    col_a, col_b = st.columns(2)
    with col_a:
        model_type = st.selectbox(
            "Model Dekomposisi:",
            ["additive", "multiplicative"],
            help="Additive: tren + musiman + residu. Multiplicative: tren × musiman × residu. "
                 "Pilih multiplicative jika amplitudo musiman meningkat seiring tren.",
        )
    with col_b:
        period = st.number_input(
            "Periode musiman:",
            min_value=2, max_value=min(365, len(series) // 2),
            value=min(12, len(series) // 4),
            help="12 untuk data bulanan, 4 untuk kuartalan, 7 untuk harian.",
        )

    if len(series.dropna()) < period * 2:
        st.warning(f"⚠️ Data minimal {period * 2} observasi untuk dekomposisi dengan periode {period}.")
        return None

    try:
        result = seasonal_decompose(series.dropna(), model=model_type, period=int(period))
    except Exception as e:
        st.error(f"❌ Dekomposisi gagal: {e}")
        return None

    # Plot 4 panel
    fig = make_subplots(
        rows=4, cols=1,
        subplot_titles=["Data Asli", "Tren", "Musiman (Seasonal)", "Residu"],
        shared_xaxes=True, vertical_spacing=0.06,
    )
    x_idx = list(range(len(series.dropna())))
    panels = [
        (series.dropna().values, BLUE),
        (result.trend,           ORANGE),
        (result.seasonal,        GREEN),
        (result.resid,           RED),
    ]
    for row, (y_data, color) in enumerate(panels, 1):
        fig.add_trace(go.Scatter(
            x=x_idx, y=y_data, mode="lines",
            line=dict(color=color, width=1.5), showlegend=False,
        ), row=row, col=1)

    fig.update_layout(
        title=f"Dekomposisi {model_type.title()}: {col_name}",
        template="plotly_white", height=700,
        margin=dict(l=30, r=30, t=60, b=30),
    )
    st.plotly_chart(fig, use_container_width=True)

    trend_vals = result.trend.dropna()
    trend_dir  = "naik" if trend_vals.iloc[-1] > trend_vals.iloc[0] else "turun"
    _narasi(
        f"📈 Model <b>{model_type}</b>, periode = <b>{period}</b>. "
        f"Tren secara keseluruhan <b>{trend_dir}</b>. "
        f"Komponen musiman: min = {result.seasonal.min():.3f}, "
        f"max = {result.seasonal.max():.3f}."
    )

    return {"model_type": model_type, "period": int(period)}


# ═══════════════════════════════════════════════════════════════════════════════
# Tab 3 — ACF / PACF
# ═══════════════════════════════════════════════════════════════════════════════

def _tab_acf_pacf(series: pd.Series, col_name: str):
    from statsmodels.tsa.stattools import acf, pacf

    st.markdown("#### 📉 ACF & PACF Plot")
    st.markdown("""
    <div class="rs-narasi">
    📖 <b>ACF</b> (Autocorrelation Function): identifikasi order <b>MA (q)</b> — lag signifikan terakhir di ACF.<br/>
    <b>PACF</b> (Partial ACF): identifikasi order <b>AR (p)</b> — lag signifikan terakhir di PACF.<br/>
    Bar yang melewati batas biru (confidence interval) = signifikan secara statistik.
    </div>
    """, unsafe_allow_html=True)

    nlags = st.slider(
        "Jumlah lag:", min_value=5,
        max_value=min(60, len(series) // 2 - 1),
        value=min(24, len(series) // 4),
        help="Umumnya 24 lag untuk data bulanan, 8 untuk kuartalan.",
    )

    s = series.dropna().values
    try:
        acf_vals,  acf_ci  = acf(s,  nlags=nlags, alpha=0.05, fft=True)
        pacf_vals, pacf_ci = pacf(s, nlags=nlags, alpha=0.05)
    except Exception as e:
        st.error(f"❌ ACF/PACF gagal: {e}")
        return

    x = list(range(len(acf_vals)))
    conf_bound = 1.96 / np.sqrt(len(s))

    fig = make_subplots(rows=1, cols=2, subplot_titles=["ACF", "PACF"])

    for col_idx, (vals, label) in enumerate([(acf_vals, "ACF"), (pacf_vals, "PACF")], 1):
        # Confidence interval bands
        fig.add_trace(go.Scatter(
            x=x, y=[conf_bound] * len(x), mode="lines",
            line=dict(color="rgba(24,95,165,0.3)", dash="dash", width=1),
            showlegend=False, name="CI Upper",
        ), row=1, col=col_idx)
        fig.add_trace(go.Scatter(
            x=x, y=[-conf_bound] * len(x), mode="lines",
            line=dict(color="rgba(24,95,165,0.3)", dash="dash", width=1),
            fill="tonexty", fillcolor="rgba(24,95,165,0.05)",
            showlegend=False, name="CI Lower",
        ), row=1, col=col_idx)
        # Bar chart
        colors = [RED if abs(v) > conf_bound else BLUE for v in vals]
        fig.add_trace(go.Bar(
            x=x, y=vals, marker_color=colors,
            showlegend=False, name=label,
        ), row=1, col=col_idx)

    fig.update_layout(
        title=f"ACF & PACF: {col_name}",
        template="plotly_white", height=400,
        margin=dict(l=30, r=30, t=60, b=30),
        bargap=0.1,
    )
    st.plotly_chart(fig, use_container_width=True)

    # Saran order
    sig_acf  = [i for i, v in enumerate(acf_vals[1:], 1)  if abs(v) > conf_bound]
    sig_pacf = [i for i, v in enumerate(pacf_vals[1:], 1) if abs(v) > conf_bound]
    q_suggest = max(sig_acf)  if sig_acf  else 0
    p_suggest = max(sig_pacf) if sig_pacf else 0

    _narasi(
        f"💡 <b>Saran order dari plot:</b> "
        f"AR(p) ≈ <b>{p_suggest}</b> (dari PACF), "
        f"MA(q) ≈ <b>{q_suggest}</b> (dari ACF). "
        f"Gunakan sebagai acuan awal di tab Model ARIMA.",
        color=PURPLE,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Tab 4 — Model ARIMA / SARIMA
# ═══════════════════════════════════════════════════════════════════════════════

def _tab_arima(series: pd.Series, col_name: str, alpha: float):
    st.markdown("#### 🤖 Model ARIMA / SARIMA")

    mode = st.radio(
        "Mode pemilihan order:",
        ["Auto-ARIMA (rekomendasi)", "Manual (ARIMA)", "Manual (SARIMA)"],
        horizontal=True,
        help="Auto-ARIMA mencari order terbaik berdasarkan AIC/BIC secara otomatis.",
    )

    col_a, col_b = st.columns(2)
    with col_a:
        n_forecast = st.number_input(
            "Langkah forecast (periode ke depan):",
            min_value=1, max_value=60, value=12,
            help="Jumlah periode yang akan di-forecast setelah data terakhir.",
        )
    with col_b:
        test_size = st.slider(
            "Ukuran test set (%):", 10, 40, 20,
            help="Persentase data yang digunakan untuk evaluasi out-of-sample.",
        )

    # Parameter manual
    p, d, q = 1, 1, 1
    P, D, Q, S = 0, 0, 0, 12

    if "Manual" in mode:
        st.markdown("##### Order ARIMA(p, d, q)")
        mc1, mc2, mc3 = st.columns(3)
        p = mc1.number_input("p (AR):", 0, 10, 1, key="arima_p",
                              help="Order autoregressive.")
        d = mc2.number_input("d (I):", 0, 3, 1, key="arima_d",
                              help="Order differencing.")
        q = mc3.number_input("q (MA):", 0, 10, 1, key="arima_q",
                              help="Order moving average.")

        if "SARIMA" in mode:
            st.markdown("##### Komponen Musiman SARIMA(P,D,Q,S)")
            ms1, ms2, ms3, ms4 = st.columns(4)
            P = ms1.number_input("P:", 0, 5, 0, key="sarima_P")
            D = ms2.number_input("D:", 0, 2, 0, key="sarima_D")
            Q = ms3.number_input("Q:", 0, 5, 0, key="sarima_Q")
            S = ms4.number_input("S (periode):", 2, 365, 12, key="sarima_S",
                                  help="12=bulanan, 4=kuartalan, 7=harian mingguan.")

    if st.button("▶ Fit Model & Forecast", type="primary", key="arima_fit_btn"):
        s = series.dropna().values
        n_test = max(1, int(len(s) * test_size / 100))
        train, test = s[:-n_test], s[-n_test:]

        try:
            with st.spinner("⏳ Fitting model... (Auto-ARIMA bisa 10-30 detik)"):
                if "Auto" in mode:
                    from pmdarima import auto_arima
                    auto_model = auto_arima(
                        train, seasonal=True, m=12,
                        information_criterion="aic",
                        stepwise=True, suppress_warnings=True,
                        error_action="ignore", max_p=5, max_q=5,
                    )
                    order         = auto_model.order
                    seasonal_order = auto_model.seasonal_order
                    p, d, q = order
                    P, D, Q, S = seasonal_order
                    _narasi(
                        f"✅ Auto-ARIMA memilih: <b>ARIMA({p},{d},{q})</b>"
                        + (f"×({P},{D},{Q})[{S}]" if any([P,D,Q]) else "")
                        + f"  |  AIC = {auto_model.aic():.2f}",
                        color=GREEN,
                    )
                    use_seasonal = any([P, D, Q])
                else:
                    use_seasonal = "SARIMA" in mode and any([P, D, Q])

                # Fit final model via statsmodels untuk summary lengkap
                from statsmodels.tsa.statespace.sarimax import SARIMAX
                seasonal_order_fit = (P, D, Q, S) if use_seasonal else (0, 0, 0, 0)
                model_fit = SARIMAX(
                    train,
                    order=(p, d, q),
                    seasonal_order=seasonal_order_fit,
                    enforce_stationarity=False,
                    enforce_invertibility=False,
                ).fit(disp=False, maxiter=200)

            # Prediksi pada test set
            pred_test = model_fit.forecast(steps=n_test)
            metrics   = _metrics(test, pred_test)

            # Forecast ke depan
            forecast_res = model_fit.get_forecast(steps=int(n_forecast))
            forecast_mean = forecast_res.predicted_mean
            conf_int      = forecast_res.conf_int(alpha=alpha)

            # Simpan ke session_state
            st.session_state["_ts_model_result"] = {
                "order":           (int(p), int(d), int(q)),
                "seasonal_order":  (int(P), int(D), int(Q), int(S)),
                "use_seasonal":    use_seasonal,
                "mode":            mode,
                "metrics":         metrics,
                "train":           train.tolist(),
                "test":            test.tolist(),
                "pred_test":       pred_test.tolist(),
                "forecast_mean":   forecast_mean.tolist(),
                "conf_int_lower":  conf_int.iloc[:, 0].tolist(),
                "conf_int_upper":  conf_int.iloc[:, 1].tolist(),
                "n_forecast":      int(n_forecast),
                "n_train":         int(len(train)),
                "n_test":          int(n_test),
                "aic":             round(float(model_fit.aic), 2),
                "bic":             round(float(model_fit.bic), 2),
                "model_summary":   model_fit.summary().as_text(),
                "col_name":        col_name,
            }
            st.success("✅ Model berhasil di-fit!")

        except Exception as e:
            st.error(f"❌ Gagal fitting model: {e}")
            st.info("Coba kurangi order p/q/P/Q atau gunakan Auto-ARIMA.")

    # Tampilkan hasil jika ada
    res = ss_get("_ts_model_result")
    if res and res.get("col_name") == col_name:
        _display_arima_results(res, alpha)

    return ss_get("_ts_model_result")


def _display_arima_results(res: dict, alpha: float):
    p, d, q  = res["order"]
    P, D, Q, S = res["seasonal_order"]
    metrics  = res["metrics"]
    use_seasonal = res["use_seasonal"]

    model_label = f"ARIMA({p},{d},{q})"
    if use_seasonal and any([P,D,Q]):
        model_label += f"×({P},{D},{Q})[{S}]"

    st.markdown(f"##### Hasil Model: {model_label}")

    # Metrik ringkasan
    m1, m2, m3, m4, m5 = st.columns(5)
    _metric_card(m1, "AIC",  res["aic"],  "lebih kecil = lebih baik")
    _metric_card(m2, "BIC",  res["bic"],  "lebih kecil = lebih baik")
    _metric_card(m3, "RMSE", metrics["RMSE"], "error rata-rata (unit asli)")
    _metric_card(m4, "MAE",  metrics["MAE"],  "error absolut rata-rata")
    mape_color = GREEN if metrics["MAPE"] < 10 else (ORANGE if metrics["MAPE"] < 20 else RED)
    _metric_card(m5, "MAPE", f"{metrics['MAPE']:.2f}%",
                 "< 10% sangat baik | < 20% baik | ≥ 20% lemah",
                 color=mape_color)

    mape_interp = (
        "sangat baik (< 10%)" if metrics["MAPE"] < 10 else
        "baik (< 20%)"        if metrics["MAPE"] < 20 else
        "lemah (≥ 20%) — pertimbangkan differencing atau order berbeda"
    )
    _narasi(
        f"📊 Model <b>{model_label}</b> — MAPE = <b>{metrics['MAPE']:.2f}%</b> "
        f"→ akurasi forecast <b>{mape_interp}</b>.",
        color=mape_color,
    )

    # Model summary (collapsible)
    with st.expander("📋 Ringkasan Model Lengkap (statsmodels)"):
        st.text(res["model_summary"])


# ═══════════════════════════════════════════════════════════════════════════════
# Tab 5 — Evaluasi & Forecast Plot
# ═══════════════════════════════════════════════════════════════════════════════

def _tab_forecast(series: pd.Series, col_name: str, ai_enabled: bool,
                  api_key: str, ai_provider: str):
    st.markdown("#### 📈 Evaluasi & Plot Forecast")

    res = ss_get("_ts_model_result")
    if not res or res.get("col_name") != col_name:
        st.info("⚠️ Jalankan model di tab **Model ARIMA** terlebih dahulu.")
        return

    p, d, q  = res["order"]
    P, D, Q, S = res["seasonal_order"]
    metrics  = res["metrics"]
    n_train  = res["n_train"]
    n_test   = res["n_test"]

    # ── Plot: Actual vs Fitted (Test Set) ────────────────────────────────────
    st.markdown("##### Actual vs Predicted (Test Set)")
    x_test = list(range(n_train, n_train + n_test))
    fig_eval = go.Figure()
    fig_eval.add_trace(go.Scatter(
        x=list(range(len(series.dropna()))),
        y=series.dropna().values,
        mode="lines", line=dict(color=BLUE, width=1.5), name="Data Aktual",
    ))
    fig_eval.add_trace(go.Scatter(
        x=x_test, y=res["pred_test"],
        mode="lines+markers",
        line=dict(color=RED, width=2, dash="dash"),
        marker=dict(size=5), name="Prediksi (Test)",
    ))
    fig_eval.add_vline(x=n_train - 0.5, line_dash="dot", line_color=ORANGE,
                       annotation_text="Train | Test")
    fig_eval.update_layout(
        title=f"Aktual vs Prediksi: {col_name}",
        xaxis_title="Indeks Waktu", yaxis_title=col_name,
        template="plotly_white", height=400,
        margin=dict(l=30, r=30, t=50, b=30),
        legend=dict(orientation="h", y=-0.2),
    )
    st.plotly_chart(fig_eval, use_container_width=True)

    # ── Plot: Forecast ke Depan ──────────────────────────────────────────────
    st.markdown("##### Forecast ke Depan")
    n_total   = len(series.dropna())
    x_fc      = list(range(n_total, n_total + res["n_forecast"]))

    fig_fc = go.Figure()
    fig_fc.add_trace(go.Scatter(
        x=list(range(n_total)),
        y=series.dropna().values,
        mode="lines", line=dict(color=BLUE, width=1.5), name="Data Historis",
    ))
    fig_fc.add_trace(go.Scatter(
        x=x_fc, y=res["forecast_mean"],
        mode="lines+markers",
        line=dict(color=ORANGE, width=2.5),
        marker=dict(size=6), name="Forecast",
    ))
    # Confidence interval
    fig_fc.add_trace(go.Scatter(
        x=x_fc + x_fc[::-1],
        y=res["conf_int_upper"] + res["conf_int_lower"][::-1],
        fill="toself",
        fillcolor="rgba(224,92,42,0.15)",
        line=dict(color="rgba(255,255,255,0)"),
        name="95% CI",
    ))
    fig_fc.add_vline(x=n_total - 0.5, line_dash="dot", line_color=GREEN,
                     annotation_text="Historis | Forecast")
    fig_fc.update_layout(
        title=f"Forecast {res['n_forecast']} Periode ke Depan: {col_name}",
        xaxis_title="Indeks Waktu", yaxis_title=col_name,
        template="plotly_white", height=420,
        margin=dict(l=30, r=30, t=50, b=30),
        legend=dict(orientation="h", y=-0.2),
    )
    st.plotly_chart(fig_fc, use_container_width=True)

    # Tabel forecast
    fc_df = pd.DataFrame({
        "Periode ke-":      list(range(1, res["n_forecast"] + 1)),
        "Forecast":         [round(v, 4) for v in res["forecast_mean"]],
        "CI Lower (95%)":   [round(v, 4) for v in res["conf_int_lower"]],
        "CI Upper (95%)":   [round(v, 4) for v in res["conf_int_upper"]],
    })
    st.dataframe(fc_df, use_container_width=True, hide_index=True)

    # Export Excel
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        fc_df.to_excel(writer, sheet_name="Forecast", index=False)
        pd.DataFrame([metrics]).to_excel(writer, sheet_name="Metrik_Evaluasi", index=False)
    buf.seek(0)
    st.download_button(
        "⬇️ Export Forecast ke Excel (.xlsx)", data=buf,
        file_name=f"forecast_{col_name}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="ts_export_btn",
    )

    # AI Interpretasi
    if ai_enabled:
        if st.button("🤖 Interpretasi Time Series dengan AI", key="ai_ts_btn"):
            p2, d2, q2  = res["order"]
            P2, D2, Q2, S2 = res["seasonal_order"]
            model_label = f"ARIMA({p2},{d2},{q2})"
            if any([P2,D2,Q2]):
                model_label += f"×({P2},{D2},{Q2})[{S2}]"
            prompt = f"""
Hasil analisis Time Series untuk variabel {col_name}:

MODEL: {model_label}
AIC = {res['aic']}, BIC = {res['bic']}

METRIK EVALUASI (Test Set):
RMSE = {metrics['RMSE']}, MAE = {metrics['MAE']}, MAPE = {metrics['MAPE']:.2f}%

FORECAST {res['n_forecast']} PERIODE KE DEPAN:
{fc_df.head(6).to_string(index=False)}

Berikan interpretasi dalam Bahasa Indonesia:
1. Evaluasi kualitas model — apakah MAPE menunjukkan akurasi yang baik?
2. Interpretasi order ARIMA — apa artinya p={p2}, d={d2}, q={q2}?
3. Pola forecast — apakah tren naik/turun/stasioner? Ada pola musiman?
4. Rekomendasi penggunaan hasil forecast untuk pengambilan keputusan
5. Saran perbaikan model jika akurasi kurang memuaskan
Format: 4 paragraf akademis, Bahasa Indonesia baku.
Referensi: Box & Jenkins (1976), Hyndman & Athanasopoulos (2021).
"""
            with st.spinner("🤖 AI menganalisis time series..."):
                ai_ts = call_ai_api(prompt, api_key=api_key, provider=ai_provider)
            if "ai_cache" not in st.session_state:
                st.session_state.ai_cache = {}
            st.session_state.ai_cache["time_series"] = ai_ts

        if ss_get("ai_cache", {}).get("time_series"):
            st.markdown(
                f'<div class="rs-ai-narasi">'
                f'<span class="rs-ai-badge">✨ AI — {ai_provider.split("(")[0].strip()}</span><br/>'
                f'{ss_get("ai_cache", {})["time_series"].replace(chr(10), "<br/>")}'
                f"</div>",
                unsafe_allow_html=True,
            )
    else:
        st.caption("💡 Aktifkan API Key di sidebar untuk interpretasi AI time series.")


# ═══════════════════════════════════════════════════════════════════════════════
# RENDER UTAMA
# ═══════════════════════════════════════════════════════════════════════════════

def render(ctx: dict):
    license_info = ctx["license_info"]
    alpha_level  = ctx["alpha_level"]
    ai_enabled   = ctx["ai_enabled"]
    api_key      = ctx["anthropic_api_key"]
    ai_provider  = ctx["ai_provider"]

    st.markdown('<p class="rs-section-title">📈 Time Series Analysis</p>',
                unsafe_allow_html=True)
    st.markdown(
        '<p class="rs-section-sub">Analisis deret waktu: stasioneritas, dekomposisi, '
        'ACF/PACF, ARIMA/SARIMA, dan forecast dengan confidence interval.</p>',
        unsafe_allow_html=True,
    )

    if not require_pro(license_info, "Time Series Analysis"):
        st.stop()

    df = require_data()
    if df is None:
        st.stop()

    # Pilih kolom numerik & kolom waktu (opsional)
    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if not num_cols:
        st.error("❌ Tidak ada kolom numerik di dataset.")
        st.stop()

    col_a, col_b = st.columns(2)
    with col_a:
        ts_col = st.selectbox(
            "Variabel deret waktu (Y):", num_cols,
            help="Pilih variabel yang akan dianalisis sebagai deret waktu.",
        )
    with col_b:
        date_cols = ["— (gunakan urutan baris)"] + \
                    df.select_dtypes(include=["object", "datetime"]).columns.tolist()
        date_col = st.selectbox(
            "Kolom tanggal/waktu (opsional):",
            date_cols,
            help="Jika ada kolom tanggal, pilih untuk x-axis yang bermakna.",
        )

    series = df[ts_col].dropna().reset_index(drop=True)
    if len(series) < 10:
        st.warning("⚠️ Data minimal 10 observasi untuk analisis time series.")
        st.stop()

    st.info(f"📊 Menganalisis **{ts_col}** | N = {len(series)} observasi")

    # ── 5 Tab ────────────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🔍 Stasioneritas",
        "📊 Dekomposisi",
        "📉 ACF/PACF",
        "🤖 Model ARIMA",
        "📈 Forecast",
    ])

    stationer_result  = None
    decompose_result  = None

    with tab1:
        stationer_result = _tab_stasioner(series, ts_col, alpha_level)

    with tab2:
        decompose_result = _tab_decompose(series, ts_col)

    with tab3:
        _tab_acf_pacf(series, ts_col)

    with tab4:
        _tab_arima(series, ts_col, alpha_level)

    with tab5:
        _tab_forecast(series, ts_col, ai_enabled, api_key, ai_provider)

    # ── Simpan hasil ke session_state untuk export laporan ────────────────────
    model_res = ss_get("_ts_model_result")
    if model_res and model_res.get("col_name") == ts_col:
        st.session_state["time_series_result"] = {
            "col_name":        ts_col,
            "n_obs":           int(len(series)),
            "stasioner":       stationer_result or {},
            "decompose":       decompose_result or {},
            "order":           model_res.get("order"),
            "seasonal_order":  model_res.get("seasonal_order"),
            "use_seasonal":    model_res.get("use_seasonal", False),
            "mode":            model_res.get("mode", ""),
            "metrics":         model_res.get("metrics", {}),
            "aic":             model_res.get("aic"),
            "bic":             model_res.get("bic"),
            "forecast_mean":   model_res.get("forecast_mean", []),
            "conf_int_lower":  model_res.get("conf_int_lower", []),
            "conf_int_upper":  model_res.get("conf_int_upper", []),
            "n_forecast":      model_res.get("n_forecast", 0),
            "ai_text":         ss_get("ai_cache", {}).get("time_series", ""),
        }
