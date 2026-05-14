"""
modules/logistik.py — Regresi Logistik
Ruang Statistika v4.2

Tier akses:
- FREE : Koefisien & Odds Ratio, metrik model (AUC, Pseudo R², AIC, BIC),
         Confusion Matrix, export Excel.
- PRO  : Semua fitur gratis + ROC Curve, Classification Report lengkap,
         interpretasi AI, dan hasil tersimpan ke session_state untuk laporan.

Perbaikan v4.1:
- AI cache key konsisten: "logistik"
- Simpan log_result lengkap (odds_df, cr, roc fpr/tpr, auc)
"""

import io
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from utils.stats_helpers import require_data, require_cols, ss_get
from utils.ai_helpers import call_ai_api, ai_interpret_logistik
from utils.effect_size import render_effect_size_card


def render(ctx: dict):
    license_info = ctx["license_info"]
    is_pro       = ctx["is_pro"]
    alpha_level  = ctx["alpha_level"]
    ai_enabled   = ctx["ai_enabled"]
    api_key      = ctx["anthropic_api_key"]
    ai_provider  = ctx["ai_provider"]

    st.markdown('<p class="rs-section-title">📊 Regresi Logistik</p>',
                unsafe_allow_html=True)
    st.markdown(
        '<p class="rs-section-sub">Untuk variabel dependen biner (0/1). '
        'ROC curve, classification report, dan AI tersedia di Pro.</p>',
        unsafe_allow_html=True,
    )

    # Tidak ada hard-stop — modul berjalan untuk semua user

    df = require_data()
    if df is None:
        st.stop()
    cols = require_cols(df)
    if cols is None or len(cols) < 2:
        st.warning("⚠️ Pilih minimal 2 kolom numerik.")
        st.stop()

    st.markdown("""
    <div class="rs-narasi">
        📖 <b>Regresi Logistik:</b> Memodelkan probabilitas outcome biner (0/1).<br/>
        <b>Odds Ratio</b> = exp(β) — mengindikasikan seberapa besar perubahan peluang per unit X.<br/>
        <b>AUC ≥ 0.70</b> menunjukkan model dengan diskriminasi yang cukup.
    </div>
    """, unsafe_allow_html=True)

    col_a, col_b = st.columns(2)
    with col_a:
        dep_var = st.selectbox("Variabel Dependen Y (harus biner 0/1):", cols, key="log_y")
    with col_b:
        remaining  = [c for c in cols if c != dep_var]
        indep_vars = st.multiselect(
            "Variabel Independen (X):", remaining,
            default=remaining[:min(3, len(remaining))],
            key="log_x"
        )

    if not indep_vars:
        st.info("Pilih setidaknya satu variabel independen.")
        st.stop()

    # Validasi biner
    y_vals = df[dep_var].dropna().unique()
    if not set(y_vals).issubset({0, 1, 0.0, 1.0}):
        st.error(
            f"❌ Variabel **{dep_var}** bukan biner. "
            f"Nilai unik: {sorted(y_vals)}. Pastikan hanya bernilai 0 dan 1."
        )
        st.stop()

    if st.button("▶ Jalankan Regresi Logistik", type="primary"):
        try:
            with st.spinner("⏳ Fitting logistic regression..."):
                result = _run_logistic(df, dep_var, indep_vars)
            st.session_state["log_result"] = {
                **result,
                "y":          dep_var,
                "x":          indep_vars,
                "coef_table": result["odds_ratio_df"],
                "odds_df":    result["odds_ratio_df"],
            }
        except Exception as e:
            st.error(f"❌ Gagal: {e}")

    res = ss_get("log_result")
    if not (res and res.get("y") == dep_var and res.get("x") == indep_vars):
        return

    _display_results(res, dep_var, indep_vars, alpha_level,
                     is_pro, ai_enabled, api_key, ai_provider)


def _run_logistic(df, dep_var, indep_vars):
    import statsmodels.api as sm
    from sklearn.metrics import (roc_auc_score, roc_curve,
                                  classification_report, confusion_matrix)

    subset = df[[dep_var] + indep_vars].dropna()
    Y      = subset[dep_var].astype(int).values
    X_c    = sm.add_constant(subset[indep_vars].astype(float))

    model  = sm.Logit(Y, X_c).fit(disp=0)

    params = model.params
    bse    = model.bse
    pvals  = model.pvalues
    conf   = model.conf_int()

    odds_ratio_df = pd.DataFrame({
        "Parameter":    params.index,
        "β":            params.values.round(4),
        "SE":           bse.values.round(4),
        "z":            model.tvalues.round(4),
        "p-value":      pvals.values.round(4),
        "OR (exp β)":   np.exp(params.values).round(4),
        "OR CI Lower":  np.exp(conf.iloc[:, 0].values).round(4),
        "OR CI Upper":  np.exp(conf.iloc[:, 1].values).round(4),
    })

    y_prob = model.predict(X_c)
    y_pred = (y_prob >= 0.5).astype(int)

    auc    = roc_auc_score(Y, y_prob)
    fpr, tpr, _ = roc_curve(Y, y_prob)
    cm     = confusion_matrix(Y, y_pred)
    cr     = classification_report(Y, y_pred, output_dict=True)

    return {
        "model":         model,
        "odds_ratio_df": odds_ratio_df,
        "y_prob":        y_prob,
        "y_pred":        y_pred,
        "Y":             Y,
        "auc":           auc,
        "fpr":           fpr,
        "tpr":           tpr,
        "cm":            cm,
        "cr":            cr,
        "log_likelihood": model.llf,
        "aic":           model.aic,
        "bic":           model.bic,
        "pseudo_r2":     model.prsquared,
        "roc": {"fpr": list(fpr), "tpr": list(tpr), "auc": auc},
    }


def _display_results(res, dep_var, indep_vars, alpha_level,
                     is_pro, ai_enabled, api_key, ai_provider):

    # ── Metrik Model ──────────────────────────────────────────────────────
    st.markdown("#### Ringkasan Model")
    m1, m2, m3, m4 = st.columns(4)
    auc_interp = (
        "Sangat baik" if res["auc"] >= 0.90 else
        "Baik"        if res["auc"] >= 0.80 else
        "Cukup"       if res["auc"] >= 0.70 else "Lemah"
    )
    for col, lbl, val in zip(
        [m1, m2, m3, m4],
        ["AUC", "Pseudo R² (McFadden)", "AIC", "BIC"],
        [f"{res['auc']:.4f}", f"{res['pseudo_r2']:.4f}",
         f"{res['aic']:.2f}", f"{res['bic']:.2f}"],
    ):
        col.markdown(
            f'<div class="rs-metric"><div class="rs-metric-label">{lbl}</div>'
            f'<div class="rs-metric-value">{val}</div></div>',
            unsafe_allow_html=True,
        )
    st.markdown(
        f'<div class="rs-narasi">🎯 AUC = {res["auc"]:.4f} → '
        f'Kualitas model: <b>{auc_interp}</b></div>',
        unsafe_allow_html=True,
    )

    # ── Odds Ratio ────────────────────────────────────────────────────────
    st.markdown("#### Koefisien & Odds Ratio")
    odds_df = res["odds_ratio_df"]
    odds_df_display = odds_df.copy()
    odds_df_display["Signifikan"] = [
        "✓" if p < alpha_level else "✗" for p in odds_df["p-value"]
    ]
    st.dataframe(odds_df_display, use_container_width=True, hide_index=True)

    sig_rows = odds_df_display[odds_df_display["Signifikan"] == "✓"]
    sig_rows = sig_rows[sig_rows["Parameter"] != "const"]
    if not sig_rows.empty:
        narasi_parts = []
        for _, row in sig_rows.iterrows():
            OR   = row["OR (exp β)"]
            arah = "meningkatkan" if OR > 1 else "menurunkan"
            narasi_parts.append(
                f"<b>{row['Parameter']}</b> (OR={OR:.3f}): setiap kenaikan 1 unit "
                f"{arah} peluang {dep_var}=1 sebesar {abs(OR-1)*100:.1f}%"
            )
        st.markdown(
            '<div class="rs-narasi">📊 <b>Interpretasi OR Signifikan:</b><br/>'
            + "<br/>".join(narasi_parts) + "</div>",
            unsafe_allow_html=True,
        )
    for _, row in sig_rows.iterrows():
        render_effect_size_card("or", row["OR (exp β)"], show_table=False)

    # ── Confusion Matrix (tersedia semua tier) ────────────────────────────
    st.markdown("---")
    st.markdown("#### Confusion Matrix")
    cm = res["cm"]
    fig_cm = go.Figure(go.Heatmap(
        z=cm, x=["Pred: 0", "Pred: 1"], y=["True: 0", "True: 1"],
        colorscale="Blues", text=cm, texttemplate="%{text}",
        showscale=False,
    ))
    fig_cm.update_layout(
        template="plotly_white", height=360,
        margin=dict(l=30, r=30, t=30, b=30)
    )
    st.plotly_chart(fig_cm, use_container_width=True)

    # ── Export Excel (semua tier) ─────────────────────────────────────────
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        odds_df_display.to_excel(writer, sheet_name="Odds_Ratio", index=False)
        pd.DataFrame({
            "Metrik": ["AUC", "Pseudo R²", "AIC", "BIC"],
            "Nilai":  [res["auc"], res["pseudo_r2"], res["aic"], res["bic"]]
        }).to_excel(writer, sheet_name="Model_Summary", index=False)
    buf.seek(0)
    st.download_button(
        "⬇️ Export ke Excel (.xlsx)", data=buf,
        file_name=f"Logistik_{dep_var}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # ── Fitur Pro ─────────────────────────────────────────────────────────
    st.markdown("---")
    if not is_pro:
        st.info(
            "🔒 **Fitur Pro:** ROC Curve interaktif, Classification Report lengkap "
            "(precision, recall, F1), dan interpretasi AI — tersedia di "
            "**Paket Akademisi Pro**.\n\n"
            "👉 [Dapatkan akses Pro](https://lynk.id/ruangstatistika)"
        )
        return

    # ── PRO ONLY: ROC Curve ───────────────────────────────────────────────
    st.markdown("#### ROC Curve (Pro)")
    fig_roc = go.Figure()
    fig_roc.add_trace(go.Scatter(
        x=res["fpr"], y=res["tpr"], mode="lines",
        line=dict(color="#185FA5", width=2.5),
        name=f"ROC (AUC = {res['auc']:.4f})"
    ))
    fig_roc.add_trace(go.Scatter(
        x=[0, 1], y=[0, 1], mode="lines",
        line=dict(color="#E24B4A", dash="dash"), name="Chance"
    ))
    fig_roc.update_layout(
        xaxis_title="False Positive Rate",
        yaxis_title="True Positive Rate (Recall)",
        template="plotly_white", height=380,
        margin=dict(l=30, r=30, t=30, b=30)
    )
    st.plotly_chart(fig_roc, use_container_width=True)

    # ── PRO ONLY: Classification Report ──────────────────────────────────
    st.markdown("#### Classification Report (Pro)")
    cr = res["cr"]
    cr_df = pd.DataFrame({
        "Class":     ["0", "1", "Macro avg", "Weighted avg"],
        "Precision": [round(cr["0"]["precision"], 4), round(cr["1"]["precision"], 4),
                      round(cr["macro avg"]["precision"], 4),
                      round(cr["weighted avg"]["precision"], 4)],
        "Recall":    [round(cr["0"]["recall"], 4), round(cr["1"]["recall"], 4),
                      round(cr["macro avg"]["recall"], 4),
                      round(cr["weighted avg"]["recall"], 4)],
        "F1-Score":  [round(cr["0"]["f1-score"], 4), round(cr["1"]["f1-score"], 4),
                      round(cr["macro avg"]["f1-score"], 4),
                      round(cr["weighted avg"]["f1-score"], 4)],
    })
    st.dataframe(cr_df, use_container_width=True, hide_index=True)

    # Export Excel Pro (dengan CR)
    buf2 = io.BytesIO()
    with pd.ExcelWriter(buf2, engine="openpyxl") as writer:
        odds_df_display.to_excel(writer, sheet_name="Odds_Ratio", index=False)
        cr_df.to_excel(writer, sheet_name="Classification_Report", index=False)
        pd.DataFrame({
            "Metrik": ["AUC", "Pseudo R²", "AIC", "BIC"],
            "Nilai":  [res["auc"], res["pseudo_r2"], res["aic"], res["bic"]]
        }).to_excel(writer, sheet_name="Model_Summary", index=False)
    buf2.seek(0)
    st.download_button(
        "⬇️ Export Lengkap ke Excel (.xlsx) — Pro", data=buf2,
        file_name=f"Logistik_Pro_{dep_var}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="log_pro_export",
    )

    # ── PRO ONLY: AI Interpretasi ─────────────────────────────────────────
    if ai_enabled:
        if st.button("🤖 Interpretasi Logistik dengan AI", key="ai_log_btn"):
            result_data = {
                "y":          dep_var,
                "x":          indep_vars,
                "auc":        res["auc"],
                "pseudo_r2":  res["pseudo_r2"],
                "aic":        res["aic"],
                "bic":        res["bic"],
                "odds_df":    odds_df_display,
                "cr":         cr,
            }
            with st.spinner("🤖 AI menganalisis regresi logistik…"):
                ai_log = ai_interpret_logistik(result_data, api_key, ai_provider)
            if "ai_cache" not in st.session_state:
                st.session_state.ai_cache = {}
            st.session_state.ai_cache["logistik"] = ai_log

        cached = ss_get("ai_cache", {}).get("logistik")
        if cached:
            st.markdown(
                f'<div class="rs-ai-narasi">'
                f'<span class="rs-ai-badge">✨ AI — {ai_provider.split("(")[0].strip()}</span><br/>'
                f'{cached.replace(chr(10), "<br/>")}'
                f"</div>",
                unsafe_allow_html=True,
            )
