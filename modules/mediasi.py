"""
modules/mediasi.py — Mediasi Baron & Kenny + Bootstrap CI (Pro)
Ruang Statistika v4.0
"""

import io
import numpy as np
import pandas as pd
import streamlit as st
from scipy import stats

from utils.auth import require_pro
from utils.stats_helpers import require_data, require_cols, run_mediation, ss_get
from utils.plot_helpers import mediasi_path_svg
from utils.ai_helpers import call_ai_api


def _bootstrap_indirect(df: pd.DataFrame, x_col: str, m_col: str, y_col: str,
                         n_boot: int = 5000, ci: float = 0.95) -> dict:
    """Bootstrap confidence interval untuk indirect effect (Preacher & Hayes)."""
    import statsmodels.api as sm

    subset   = df[[x_col, m_col, y_col]].dropna().reset_index(drop=True)
    n        = len(subset)
    indirect_boot = []

    rng = np.random.default_rng(42)
    for _ in range(n_boot):
        idx   = rng.integers(0, n, size=n)
        samp  = subset.iloc[idx]

        try:
            X1   = sm.add_constant(samp[[x_col]])
            a    = sm.OLS(samp[m_col], X1).fit().params[x_col]
            X2   = sm.add_constant(samp[[x_col, m_col]])
            b    = sm.OLS(samp[y_col], X2).fit().params[m_col]
            indirect_boot.append(a * b)
        except Exception:
            continue

    alpha_tail = (1 - ci) / 2
    lo = np.percentile(indirect_boot, alpha_tail * 100)
    hi = np.percentile(indirect_boot, (1 - alpha_tail) * 100)
    mean_ind = np.mean(indirect_boot)
    se_boot  = np.std(indirect_boot, ddof=1)

    return {
        "n_boot":      n_boot,
        "ci":          ci,
        "mean":        round(float(mean_ind), 4),
        "se":          round(float(se_boot), 4),
        "ci_lower":    round(float(lo), 4),
        "ci_upper":    round(float(hi), 4),
        "significant": not (lo <= 0 <= hi),   # CI tidak melewati 0 → signifikan
    }


def render(ctx: dict):
    license_info = ctx["license_info"]
    alpha_level  = ctx["alpha_level"]
    ai_enabled   = ctx["ai_enabled"]
    api_key      = ctx["anthropic_api_key"]
    ai_provider  = ctx["ai_provider"]

    st.markdown('<p class="rs-section-title">🔀 Analisis Mediasi (Baron & Kenny)</p>',
                unsafe_allow_html=True)
    st.markdown(
        '<p class="rs-section-sub">Path coefficients, Sobel test, dan Bootstrap CI '
        '(Preacher & Hayes — standar publikasi).</p>',
        unsafe_allow_html=True,
    )

    if not require_pro(license_info, "Mediasi"):
        st.stop()

    df = require_data()
    if df is None:
        st.stop()
    cols = require_cols(df)
    if cols is None or len(cols) < 3:
        st.warning("⚠️ Diperlukan minimal 3 kolom numerik: X, M, dan Y.")
        st.stop()

    st.markdown("""
    <div class="rs-narasi">
        📖 <b>Prosedur Baron & Kenny (1986):</b><br/>
        Path <b>a</b>: X → M &nbsp;|&nbsp;
        Path <b>b</b>: M → Y (dikontrol X) &nbsp;|&nbsp;
        Path <b>c</b>: X → Y (total) &nbsp;|&nbsp;
        Path <b>c'</b>: X → Y (langsung, dikontrol M)<br/>
        <b>Indirect effect</b> = a × b — diuji dengan Sobel test &amp; Bootstrap CI
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br/>", unsafe_allow_html=True)

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        x_med = st.selectbox("Variabel X (Independen):", cols, key="med_x")
    with col_b:
        m_med = st.selectbox("Variabel M (Mediator):",
                             [c for c in cols if c != x_med], key="med_m")
    with col_c:
        y_med = st.selectbox("Variabel Y (Dependen):",
                             [c for c in cols if c not in [x_med, m_med]], key="med_y")

    col_opt1, col_opt2 = st.columns(2)
    with col_opt1:
        n_boot = st.number_input("Jumlah Bootstrap samples:", 1000, 10000, 5000, 1000)
    with col_opt2:
        ci_level = st.selectbox("Tingkat Kepercayaan CI:", [0.95, 0.99, 0.90], index=0)

    if st.button("▶ Jalankan Analisis Mediasi", type="primary"):
        try:
            with st.spinner("Menghitung jalur mediasi..."):
                m_model, y_model, c_model, med_info = run_mediation(df, x_med, m_med, y_med)
            with st.spinner(f"🥾 Bootstrap {n_boot:,} samples... (Preacher & Hayes)"):
                boot_result = _bootstrap_indirect(df, x_med, m_med, y_med,
                                                  n_boot=n_boot, ci=ci_level)
            st.session_state["med_result"] = {
                "m_model": m_model, "y_model": y_model, "c_model": c_model,
                "med_info": med_info, "boot": boot_result,
                "x": x_med, "m": m_med, "y": y_med,
                # Data tambahan untuk export laporan (format yang dikenali export.py)
                "path_table": pd.DataFrame([
                    {"Jalur": "a (X→M)",     "Koefisien": med_info["a (X→M)"],          "Keterangan": f"{x_med} → {m_med}"},
                    {"Jalur": "b (M→Y|X)",   "Koefisien": med_info["b (M→Y|X)"],        "Keterangan": f"{m_med} → {y_med} (dikontrol X)"},
                    {"Jalur": "c (Total)",   "Koefisien": med_info["c (total X→Y)"],    "Keterangan": f"{x_med} → {y_med} (total)"},
                    {"Jalur": "c' (Langsung)","Koefisien": med_info["c' (direct X→Y)"], "Keterangan": f"{x_med} → {y_med} (langsung)"},
                ]),
                "indirect_effect": float(med_info["Indirect (a×b)"]),
                "direct_effect":   float(med_info["c' (direct X→Y)"]),
                "total_effect":    float(med_info["c (total X→Y)"]),
                "bootstrap_ci":    [float(boot_result["ci_lower"]), float(boot_result["ci_upper"])],
            }
        except Exception as e:
            st.error(f"❌ Gagal: {e}")

    med_res = ss_get("med_result")
    if not (med_res and med_res.get("x") == x_med
            and med_res.get("m") == m_med and med_res.get("y") == y_med):
        return

    info        = med_res["med_info"]
    boot        = med_res["boot"]

    # ── Path Coefficients ──
    st.markdown("---")
    st.markdown("#### Ringkasan Path Coefficients")
    cols4 = st.columns(4)
    for col_, (lbl, val) in zip(cols4, [
        ("Path a (X→M)",    info["a (X→M)"]),
        ("Path b (M→Y|X)",  info["b (M→Y|X)"]),
        ("Path c (Total)",  info["c (total X→Y)"]),
        ("Path c' (Direct)", info["c' (direct X→Y)"]),
    ]):
        col_.markdown(
            f'<div class="rs-metric"><div class="rs-metric-label">{lbl}</div>'
            f'<div class="rs-metric-value" style="font-size:1.5rem">{val}</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown("<br/>", unsafe_allow_html=True)

    # ── Sobel Test ──
    p_sob      = info["p Sobel"]
    sobel_sig  = p_sob < alpha_level
    col_sob    = "#3b6d11" if sobel_sig else "#a32d2d"
    sobel_lbl  = "✅ Signifikan" if sobel_sig else "❌ Tidak Signifikan"
    st.markdown(f"""
    <div class="rs-narasi">
        🧪 <b>Sobel Test — Indirect Effect (a × b)</b><br/>
        Indirect = <b>{info['Indirect (a×b)']}</b> &nbsp;|&nbsp;
        SE = {info['SE Indirect']} &nbsp;|&nbsp;
        z = {info['z Sobel']} &nbsp;|&nbsp;
        p = <span style="color:{col_sob}; font-weight:600">{p_sob} ({sobel_lbl})</span>
    </div>
    """, unsafe_allow_html=True)

    # ── Bootstrap CI (Preacher & Hayes) ──
    boot_sig   = boot["significant"]
    boot_color = "#3b6d11" if boot_sig else "#a32d2d"
    boot_lbl   = "✅ Signifikan (CI tidak melewati 0)" if boot_sig else "❌ Tidak Signifikan (CI melewati 0)"
    st.markdown(f"""
    <div class="rs-narasi" style="border-left-color:#6366f1;">
        🥾 <b>Bootstrap CI — Indirect Effect (Preacher &amp; Hayes, {int(boot['ci']*100)}%)</b><br/>
        N bootstrap = {boot['n_boot']:,} &nbsp;|&nbsp;
        Mean indirect = <b>{boot['mean']}</b> &nbsp;|&nbsp;
        SE = {boot['se']}<br/>
        <b>CI [{boot['ci_lower']}, {boot['ci_upper']}]</b> &nbsp;→&nbsp;
        <span style="color:{boot_color}; font-weight:600">{boot_lbl}</span><br/>
        <small>⭐ Bootstrap CI adalah standar modern untuk publikasi (Hayes, 2013).</small>
    </div>
    """, unsafe_allow_html=True)

    # ── Jenis Mediasi ──
    c_val  = info["c (total X→Y)"]
    cp_val = info["c' (direct X→Y)"]
    if boot_sig and abs(cp_val) < 0.01:
        jenis = "🔵 Mediasi Penuh (Full Mediation)"
    elif boot_sig and abs(cp_val) > 0.01:
        jenis = "🟡 Mediasi Sebagian (Partial Mediation)"
    else:
        jenis = "⚪ Tidak Ada Mediasi"
    st.info(f"**Kesimpulan Mediasi:** {jenis}")

    # ── Diagram Path ──
    st.markdown("---")
    st.markdown("#### Diagram Path")
    st.markdown(
        mediasi_path_svg(
            x_med, m_med, y_med,
            info["a (X→M)"], info["b (M→Y|X)"],
            info["c (total X→Y)"], info["c' (direct X→Y)"],
            info["Indirect (a×b)"],
        ),
        unsafe_allow_html=True,
    )

    # ── Detail Regresi ──
    st.markdown("---")
    tab_pa, tab_pb, tab_pc = st.tabs(
        ["Path a: M ~ X", "Path b+c': Y ~ X + M", "Path c: Y ~ X (Total)"]
    )
    with tab_pa:
        st.text(med_res["m_model"].summary().as_text())
    with tab_pb:
        st.text(med_res["y_model"].summary().as_text())
    with tab_pc:
        st.text(med_res["c_model"].summary().as_text())

    # ── Export Excel ──
    buf = io.BytesIO()
    summary_df = pd.DataFrame([
        {"Metrik": "Path a (X→M)",    "Nilai": info["a (X→M)"]},
        {"Metrik": "Path b (M→Y|X)",  "Nilai": info["b (M→Y|X)"]},
        {"Metrik": "Path c (Total)",   "Nilai": info["c (total X→Y)"]},
        {"Metrik": "Path c' (Direct)", "Nilai": info["c' (direct X→Y)"]},
        {"Metrik": "Indirect (a×b)",   "Nilai": info["Indirect (a×b)"]},
        {"Metrik": "z Sobel",          "Nilai": info["z Sobel"]},
        {"Metrik": "p Sobel",          "Nilai": info["p Sobel"]},
        {"Metrik": f"Bootstrap CI {int(ci_level*100)}% Lower", "Nilai": boot["ci_lower"]},
        {"Metrik": f"Bootstrap CI {int(ci_level*100)}% Upper", "Nilai": boot["ci_upper"]},
        {"Metrik": "Jenis Mediasi",    "Nilai": jenis},
    ])
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        summary_df.to_excel(writer, sheet_name="Mediasi_Summary", index=False)
    buf.seek(0)
    st.download_button("⬇️ Export ke Excel (.xlsx)", data=buf,
                       file_name=f"Mediasi_{x_med}_{m_med}_{y_med}.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # ── AI ──
    if ai_enabled:
        if st.button("🤖 Interpretasi Mediasi dengan AI", key="ai_med_btn"):
            prompt = f"""
Hasil analisis mediasi (Baron & Kenny + Bootstrap) dengan variabel:
- X (Independen): {x_med}, M (Mediator): {m_med}, Y (Dependen): {y_med}

PATH COEFFICIENTS:
a={info['a (X→M)']}, b={info['b (M→Y|X)']}, c={info['c (total X→Y)']}, c'={info["c' (direct X→Y)"]}
Indirect (a×b) = {info['Indirect (a×b)']}

SOBEL TEST: z={info['z Sobel']}, p={info['p Sobel']}

BOOTSTRAP CI ({int(ci_level*100)}%): [{boot['ci_lower']}, {boot['ci_upper']}]
Bootstrap signifikan: {boot['significant']}

KESIMPULAN MEDIASI: {jenis}

Berikan interpretasi komprehensif dalam Bahasa Indonesia:
1. Penjelasan setiap jalur (a, b, c, c') dan maknanya
2. Kesimpulan mediasi: penuh, sebagian, atau tidak ada?
3. Perbandingan Sobel test dan Bootstrap CI — mana yang lebih andal?
4. Implikasi praktis dan rekomendasi penelitian lanjutan
Format: 3-4 paragraf akademis, gaya skripsi/tesis.
"""
            with st.spinner("🤖 AI menganalisis mediasi..."):
                ai_med = call_ai_api(prompt, api_key=api_key, provider=ai_provider)
            if "ai_cache" not in st.session_state:
                st.session_state.ai_cache = {}
            # Key "mediasi" konsisten dengan export.py collect_session_results()
            st.session_state.ai_cache["mediasi"] = ai_med

        if ss_get("ai_cache", {}).get("mediasi"):
            st.markdown(
                f'<div class="rs-ai-narasi">'
                f'<span class="rs-ai-badge">✨ AI — {ai_provider.split("(")[0].strip()}</span><br/>'
                f'{ss_get("ai_cache", {})["mediasi"].replace(chr(10), "<br/>")}'
                f"</div>",
                unsafe_allow_html=True,
            )
    else:
        st.caption("💡 Aktifkan API Key di sidebar untuk interpretasi AI mediasi.")
