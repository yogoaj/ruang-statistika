"""
modules/moderasi.py — Moderasi / Interaksi (Pro)
Ruang Statistika v4.0
"""

import io
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from utils.auth import require_pro
from utils.stats_helpers import require_data, require_cols, ss_get
from utils.ai_helpers import call_ai_api


def render(ctx: dict):
    license_info = ctx["license_info"]
    alpha_level  = ctx["alpha_level"]
    ai_enabled   = ctx["ai_enabled"]
    api_key      = ctx["anthropic_api_key"]
    ai_provider  = ctx["ai_provider"]

    st.markdown('<p class="rs-section-title">🔀 Analisis Moderasi (Interaksi)</p>',
                unsafe_allow_html=True)
    st.markdown(
        '<p class="rs-section-sub">Uji apakah pengaruh X → Y bergantung pada nilai Z (moderator). '
        'Termasuk plot interaksi dan Johnson-Neyman interval.</p>',
        unsafe_allow_html=True,
    )

    if not require_pro(license_info, "Moderasi"):
        st.stop()

    df = require_data()
    if df is None:
        st.stop()
    cols = require_cols(df)
    if cols is None or len(cols) < 3:
        st.warning("⚠️ Diperlukan minimal 3 kolom numerik: X, Z (moderator), Y.")
        st.stop()

    st.markdown("""
    <div class="rs-narasi">
        📖 <b>Model Moderasi:</b> Y = β₀ + β₁X + β₂Z + β₃(X×Z) + ε<br/>
        Jika β₃ (interaksi X×Z) signifikan → efek moderasi terbukti.
    </div>
    """, unsafe_allow_html=True)

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        x_var = st.selectbox("Variabel X (Prediktor):", cols, key="mod_x")
    with col_b:
        z_var = st.selectbox("Variabel Z (Moderator):",
                             [c for c in cols if c != x_var], key="mod_z")
    with col_c:
        y_var = st.selectbox("Variabel Y (Outcome):",
                             [c for c in cols if c not in [x_var, z_var]], key="mod_y")

    center = st.checkbox("Mean-center X dan Z (direkomendasikan)", value=True)

    if st.button("▶ Jalankan Analisis Moderasi", type="primary"):
        try:
            with st.spinner("Menghitung model interaksi..."):
                result = _run_moderation(df, x_var, z_var, y_var, alpha_level, center)
            st.session_state["mod_result"] = {
                **result, "x": x_var, "z": z_var, "y": y_var,
            }
        except Exception as e:
            st.error(f"❌ Gagal: {e}")

    res = ss_get("mod_result")
    if not (res and res.get("x") == x_var and res.get("z") == z_var and res.get("y") == y_var):
        return

    _display_results(res, x_var, z_var, y_var, alpha_level, ai_enabled, api_key, ai_provider)


def _run_moderation(df, x_var, z_var, y_var, alpha_level, center):
    import statsmodels.api as sm

    subset = df[[x_var, z_var, y_var]].dropna().copy()
    X_raw  = subset[x_var].values.astype(float)
    Z_raw  = subset[z_var].values.astype(float)
    Y      = subset[y_var].values.astype(float)

    if center:
        X = X_raw - X_raw.mean()
        Z = Z_raw - Z_raw.mean()
    else:
        X, Z = X_raw, Z_raw

    XZ     = X * Z
    X_mat  = sm.add_constant(np.column_stack([X, Z, XZ]))
    model  = sm.OLS(Y, X_mat).fit()

    # Simple slopes (Z = -1SD, Mean, +1SD)
    z_vals = {
        "-1 SD":  Z.mean() - Z.std(),
        "Mean":   Z.mean(),
        "+1 SD":  Z.mean() + Z.std(),
    }

    b0, b1, b2, b3 = model.params  # const, X, Z, X*Z
    simple_slopes = {}
    for label, zv in z_vals.items():
        slope = b1 + b3 * zv
        intercept = b0 + b2 * zv
        simple_slopes[label] = {"slope": round(slope, 4), "intercept": round(intercept, 4)}

    return {
        "model": model, "b0": b0, "b1": b1, "b2": b2, "b3": b3,
        "X": X, "Z": Z, "Y": Y, "XZ": XZ,
        "simple_slopes": simple_slopes,
        "z_vals": z_vals,
        "center": center,
    }


def _display_results(res, x_var, z_var, y_var, alpha_level, ai_enabled, api_key, ai_provider):
    model  = res["model"]
    b0, b1, b2, b3 = res["b0"], res["b1"], res["b2"], res["b3"]
    pvals  = model.pvalues

    # ── Koefisien ──
    st.markdown("#### Koefisien Model Interaksi")
    coeff_df = pd.DataFrame({
        "Parameter":    ["Konstanta", x_var, z_var, f"{x_var} × {z_var}"],
        "β":            [round(b0, 4), round(b1, 4), round(b2, 4), round(b3, 4)],
        "SE":           model.bse.round(4).values,
        "t":            model.tvalues.round(4).values,
        "p-value":      pvals.round(4).values,
        "Signifikan":   ["✓" if p < alpha_level else "✗" for p in pvals],
    })
    st.dataframe(coeff_df, use_container_width=True, hide_index=True)

    r2     = round(model.rsquared, 4)
    r2_adj = round(model.rsquared_adj, 4)

    # ── Interpretasi Interaksi ──
    int_sig   = pvals.iloc[3] < alpha_level
    int_color = "#3b6d11" if int_sig else "#a32d2d"
    int_label = "✅ SIGNIFIKAN — Moderasi Terbukti" if int_sig else "❌ Tidak Signifikan — Tidak Ada Moderasi"
    st.markdown(
        f'<div class="rs-narasi">🔀 <b>Interaksi {x_var} × {z_var}:</b> β₃ = {b3:.4f}, '
        f'p = {pvals.iloc[3]:.4f} — '
        f'<span style="color:{int_color}; font-weight:600">{int_label}</span><br/>'
        f"R² = {r2}, R² Adj = {r2_adj}</div>",
        unsafe_allow_html=True,
    )

    # ── Simple Slopes ──
    st.markdown("---")
    st.markdown("#### Simple Slopes Analysis")
    ss_df = pd.DataFrame([
        {"Level Z": lvl, "Slope (β X→Y)": v["slope"],
         "Intercept": v["intercept"]}
        for lvl, v in res["simple_slopes"].items()
    ])
    st.dataframe(ss_df, use_container_width=True, hide_index=True)

    # ── Plot Interaksi ──
    st.markdown("#### Plot Interaksi")
    X_plot = np.linspace(res["X"].min(), res["X"].max(), 100)
    fig = go.Figure()
    colors = ["#E24B4A", "#185FA5", "#3B6D11"]
    for (label, vals), color in zip(res["simple_slopes"].items(), colors):
        Y_line = vals["intercept"] + vals["slope"] * X_plot
        fig.add_trace(go.Scatter(
            x=X_plot, y=Y_line, mode="lines",
            name=f"Z = {label}", line=dict(color=color, width=2.5)
        ))
    fig.update_layout(
        title=f"Interaction Plot: {x_var} × {z_var} → {y_var}",
        xaxis_title=f"{x_var} {'(centered)' if res['center'] else ''}",
        yaxis_title=y_var,
        template="plotly_white", height=420,
        margin=dict(l=30, r=30, t=50, b=30),
        legend=dict(title=f"Level {z_var}")
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── Johnson-Neyman interval ──
    st.markdown("---")
    st.markdown("#### Johnson-Neyman Interval")
    st.info(
        "Johnson-Neyman interval menunjukkan rentang nilai Z di mana efek X → Y "
        "signifikan secara statistik."
    )
    try:
        # Hitung JN: b1 + b3*Z = 0 → Z = -b1/b3
        if abs(b3) > 1e-10:
            jn_point = -b1 / b3
            Z_range  = np.linspace(res["Z"].min(), res["Z"].max(), 500)
            slopes   = b1 + b3 * Z_range
            se_slopes = np.sqrt(
                model.bse.iloc[1] ** 2 +
                2 * jn_point * model.cov_params().iloc[1, 3] +
                jn_point ** 2 * model.bse.iloc[3] ** 2
            )
            t_crit = 1.96  # approximation

            fig_jn = go.Figure()
            fig_jn.add_trace(go.Scatter(
                x=Z_range, y=slopes, mode="lines",
                line=dict(color="#185FA5", width=2), name="Simple slope"
            ))
            fig_jn.add_hline(y=0, line_dash="dash", line_color="#E24B4A")
            if res["Z"].min() <= jn_point <= res["Z"].max():
                fig_jn.add_vline(x=jn_point, line_dash="dot", line_color="#3B6D11",
                                  annotation_text=f"JN = {jn_point:.3f}")
            fig_jn.update_layout(
                title="Johnson-Neyman: Simple Slope of X sebagai fungsi Z",
                xaxis_title=z_var, yaxis_title=f"Simple Slope ({x_var} → {y_var})",
                template="plotly_white", height=380,
                margin=dict(l=30, r=30, t=50, b=30)
            )
            st.plotly_chart(fig_jn, use_container_width=True)
            st.markdown(
                f'<div class="rs-narasi">📐 <b>Johnson-Neyman point:</b> Z = {jn_point:.4f}. '
                f"Efek X → Y signifikan ketika Z berada di "
                f"{'bawah' if b3 < 0 else 'atas'} nilai ini.</div>",
                unsafe_allow_html=True,
            )
        else:
            st.info("Koefisien interaksi terlalu kecil untuk menghitung JN interval.")
    except Exception as e:
        st.caption(f"JN interval tidak dapat dihitung: {e}")

    # ── Export Excel ──
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        coeff_df.to_excel(writer, sheet_name="Koefisien_Moderasi", index=False)
        ss_df.to_excel(writer, sheet_name="Simple_Slopes", index=False)
    buf.seek(0)
    st.download_button("⬇️ Export ke Excel (.xlsx)", data=buf,
                       file_name=f"Moderasi_{x_var}x{z_var}.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # ── AI ──
    if ai_enabled:
        if st.button("🤖 Interpretasi Moderasi dengan AI", key="ai_mod_btn"):
            prompt = f"""
Hasil analisis moderasi (interaksi) dengan variabel:
- X (Prediktor): {x_var}, Z (Moderator): {z_var}, Y (Outcome): {y_var}

KOEFISIEN MODEL: {coeff_df.to_string(index=False)}
R² = {r2}, R² Adj = {r2_adj}

SIMPLE SLOPES: {ss_df.to_string(index=False)}

INTERAKSI: β₃ = {b3:.4f}, p = {pvals.iloc[3]:.4f}
Kesimpulan: {'Moderasi TERBUKTI' if pvals.iloc[3] < alpha_level else 'Moderasi TIDAK terbukti'}

Berikan interpretasi dalam Bahasa Indonesia:
1. Apakah efek moderasi terbukti? Apa artinya?
2. Interpretasi simple slopes — bagaimana efek X berbeda di setiap level Z?
3. Implikasi teoritis dan praktis
4. Rekomendasi analisis lanjutan
Format: 3-4 paragraf akademis.
"""
            with st.spinner("🤖 AI menganalisis moderasi..."):
                ai_mod = call_ai_api(prompt, api_key=api_key, provider=ai_provider)
            if "ai_cache" not in st.session_state:
                st.session_state.ai_cache = {}
            st.session_state.ai_cache["moderasi"] = ai_mod

        if ss_get("ai_cache", {}).get("moderasi"):
            st.markdown(
                f'<div class="rs-ai-narasi">'
                f'<span class="rs-ai-badge">✨ AI — {ai_provider.split("(")[0].strip()}</span><br/>'
                f'{ss_get("ai_cache", {})["moderasi"].replace(chr(10), "<br/>")}'
                f"</div>",
                unsafe_allow_html=True,
            )
