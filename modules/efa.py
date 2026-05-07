"""
modules/efa.py — Analisis Faktor Eksploratori / EFA (Pro)
Ruang Statistika v4.0

Fitur:
  - KMO & Bartlett's Test of Sphericity
  - Scree Plot + Eigenvalue Table
  - Principal Component Analysis (PCA)
  - Exploratory Factor Analysis — rotasi Varimax & Oblimin
  - Factor Loading Matrix + Communalities
  - Interpretasi AI terintegrasi
  - Export Excel

Dependency: scikit-learn, scipy, numpy, pandas — semua sudah ada di requirements.txt
(factor-analyzer tidak diperlukan; KMO & Oblimin diimplementasi manual)
"""

import streamlit as st
import numpy as np
import pandas as pd
from scipy import linalg
from scipy.stats import chi2
from sklearn.decomposition import PCA, FactorAnalysis
from sklearn.preprocessing import StandardScaler
import plotly.graph_objects as go
import plotly.express as px
import io

from utils.auth import require_pro
from utils.stats_helpers import require_data, require_cols, ss_get
from utils.ai_helpers import call_ai_api


# ─────────────────────────────────────────────────────────────────────────────
# KONSTANTA
# ─────────────────────────────────────────────────────────────────────────────

BLUE  = "#185FA5"
GREEN = "#3B6D11"
RED   = "#A32D2D"
NAVY  = "#0c2340"

KMO_INTERP = [
    (0.90, "Marvellous (Luar Biasa)",   GREEN),
    (0.80, "Meritorious (Sangat Baik)", GREEN),
    (0.70, "Middling (Cukup Baik)",     "#B8860B"),
    (0.60, "Mediocre (Sedang)",         "#B8860B"),
    (0.50, "Miserable (Buruk)",         RED),
    (0.00, "Unacceptable (Tidak Layak)",RED),
]

LOADING_THRESH = 0.40   # minimum factor loading bermakna


# ─────────────────────────────────────────────────────────────────────────────
# KOMPUTASI STATISTIK
# ─────────────────────────────────────────────────────────────────────────────

def _compute_kmo_bartlett(X: np.ndarray, n_obs: int):
    """
    Hitung KMO Kaiser–Meyer–Olkin dan Bartlett's Test of Sphericity
    dari matriks korelasi.
    Referensi: Kaiser (1974), Bartlett (1950).
    """
    R = np.corrcoef(X, rowvar=False)
    p = R.shape[0]

    # ── KMO ──────────────────────────────────────────────────────────────────
    try:
        R_inv = linalg.inv(R)
    except linalg.LinAlgError:
        R_inv = linalg.pinv(R)

    # Matriks korelasi parsial (anti-image)
    diag_inv = np.diag(R_inv)
    P = -R_inv / np.sqrt(np.outer(diag_inv, diag_inv))
    np.fill_diagonal(P, 1.0)

    r2_sum  = np.sum(R ** 2)  - np.trace(R ** 2)   # sum r_ij²  (i≠j)
    p2_sum  = np.sum(P ** 2)  - np.trace(P ** 2)   # sum p_ij²  (i≠j)
    kmo_overall = r2_sum / (r2_sum + p2_sum) if (r2_sum + p2_sum) > 0 else 0.0

    # KMO per variabel
    kmo_per_var = []
    for i in range(p):
        r2_i = np.sum(R[i, :] ** 2) - R[i, i] ** 2
        p2_i = np.sum(P[i, :] ** 2) - P[i, i] ** 2
        kmo_i = r2_i / (r2_i + p2_i) if (r2_i + p2_i) > 0 else 0.0
        kmo_per_var.append(round(kmo_i, 4))

    # ── Bartlett's Test ───────────────────────────────────────────────────────
    det_R = linalg.det(R)
    det_R = max(det_R, 1e-300)   # hindari log(0)
    chi2_stat = -(n_obs - 1 - (2 * p + 5) / 6) * np.log(det_R)
    df_bart   = p * (p - 1) // 2
    p_bart    = float(1 - chi2.cdf(chi2_stat, df_bart))

    return {
        "kmo":           round(float(kmo_overall), 4),
        "kmo_per_var":   kmo_per_var,
        "chi2":          round(float(chi2_stat), 3),
        "df":            df_bart,
        "p_value":       round(p_bart, 4),
        "n_vars":        p,
        "corr_matrix":   R,
    }


def _interpret_kmo(kmo_val: float) -> tuple[str, str]:
    for threshold, label, color in KMO_INTERP:
        if kmo_val >= threshold:
            return label, color
    return "Tidak Layak", RED


def _run_pca(X_scaled: np.ndarray, n_vars: int):
    """Jalankan PCA — kembalikan eigenvalue, variansi, dan cumulative variance."""
    pca = PCA()
    pca.fit(X_scaled)
    eigenvalues   = pca.explained_variance_
    var_explained = pca.explained_variance_ratio_ * 100
    cum_var       = np.cumsum(var_explained)
    return eigenvalues, var_explained, cum_var, pca


def _suggest_n_factors(eigenvalues: np.ndarray, cum_var: np.ndarray,
                       cum_thresh: float = 60.0) -> int:
    """Saran jumlah faktor: Kaiser (eigenvalue > 1) dan cumulative variance."""
    n_kaiser = int(np.sum(eigenvalues > 1))
    n_kaiser = max(1, min(n_kaiser, len(eigenvalues) - 1))
    return n_kaiser


def _oblimin_rotation(A: np.ndarray, gamma: float = 0.0,
                      max_iter: int = 1000, tol: float = 1e-8) -> tuple:
    """
    Direct Oblimin rotation (gamma=0 → Quartimin, standard oblique).
    Referensi: Jennrich & Sampson (1966).
    """
    p, k = A.shape
    if k < 2:
        return A, np.eye(k)

    T = np.eye(k)
    for _ in range(max_iter):
        L  = A @ T
        L2 = L ** 2
        ones = np.ones((p, p)) / p
        if gamma == 0.0:
            G = L * L2
        else:
            G = L * (L2 - (np.eye(p) - ones * gamma) @ L2)
        G2 = np.linalg.solve(T.T, A.T @ G)
        U, s, Vt = np.linalg.svd(G2)
        T_new = U @ Vt
        diff  = np.max(np.abs(T - T_new))
        T     = T_new
        if diff < tol:
            break

    L = A @ T
    return L, T


def _run_efa(X_scaled: np.ndarray, n_factors: int, rotation: str) -> dict:
    """
    Jalankan Exploratory Factor Analysis.
    Rotation: 'varimax' atau 'oblimin'.
    """
    n_factors = min(n_factors, X_scaled.shape[1] - 1)
    n_factors = max(1, n_factors)

    # Gunakan sklearn FactorAnalysis (iterasi communalitas via EM)
    rotation_sklearn = "varimax" if rotation == "varimax" else None
    fa = FactorAnalysis(
        n_components=n_factors,
        rotation=rotation_sklearn,
        max_iter=1000,
        tol=1e-4,
        random_state=42,
    )
    fa.fit(X_scaled)

    # Loadings: shape (n_vars, n_factors)
    loadings = fa.components_.T

    # Jika oblimin, terapkan manual oblimin di atas loading varimax awal
    if rotation == "oblimin":
        fa_unrot = FactorAnalysis(n_components=n_factors, rotation=None,
                                  max_iter=1000, random_state=42)
        fa_unrot.fit(X_scaled)
        A = fa_unrot.components_.T   # unrotated loadings
        loadings, _ = _oblimin_rotation(A, gamma=0.0)

    # Communalities = sum of squared loadings per variable
    communalities = np.sum(loadings ** 2, axis=1)

    # Uniqueness
    uniqueness = 1 - communalities

    # Variance explained per factor
    ss_loadings    = np.sum(loadings ** 2, axis=0)
    n_obs, n_vars  = X_scaled.shape
    var_pct        = ss_loadings / n_vars * 100
    cum_var_pct    = np.cumsum(var_pct)

    return {
        "loadings":       loadings,
        "communalities":  communalities,
        "uniqueness":     uniqueness,
        "ss_loadings":    ss_loadings,
        "var_pct":        var_pct,
        "cum_var_pct":    cum_var_pct,
        "n_factors":      n_factors,
        "rotation":       rotation,
    }


# ─────────────────────────────────────────────────────────────────────────────
# DATAFRAME BUILDERS
# ─────────────────────────────────────────────────────────────────────────────

def _build_eigenvalue_df(eigenvalues, var_explained, cum_var, col_names) -> pd.DataFrame:
    rows = []
    for i, (ev, ve, cv) in enumerate(zip(eigenvalues, var_explained, cum_var)):
        rows.append({
            "Komponen": f"PC{i+1}",
            "Eigenvalue": round(float(ev), 4),
            "Var. Explained (%)": round(float(ve), 2),
            "Cumulative (%)": round(float(cv), 2),
            "Kaiser (>1)": "✓" if ev > 1 else "–",
        })
    return pd.DataFrame(rows)


def _build_loading_df(loadings: np.ndarray, var_names: list,
                      n_factors: int, threshold: float = LOADING_THRESH) -> pd.DataFrame:
    cols = {f"Faktor {i+1}": [] for i in range(n_factors)}
    cols["Communality"] = []

    for i, var in enumerate(var_names):
        row_loads = loadings[i]
        comm = float(np.sum(row_loads ** 2))
        for j in range(n_factors):
            val = round(float(row_loads[j]), 3)
            cols[f"Faktor {j+1}"].append(val)
        cols["Communality"].append(round(comm, 3))

    df = pd.DataFrame(cols, index=var_names)
    df.index.name = "Variabel"
    return df.reset_index()


def _build_variance_df(ss_loadings, var_pct, cum_var_pct) -> pd.DataFrame:
    rows = []
    for i, (ss, vp, cv) in enumerate(zip(ss_loadings, var_pct, cum_var_pct)):
        rows.append({
            "Faktor": f"Faktor {i+1}",
            "SS Loadings": round(float(ss), 4),
            "Variance (%)": round(float(vp), 2),
            "Cumulative (%)": round(float(cv), 2),
        })
    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────────────
# PLOTLY CHARTS
# ─────────────────────────────────────────────────────────────────────────────

def _plot_scree(eigenvalues, n_vars) -> go.Figure:
    x = list(range(1, n_vars + 1))
    ev = [float(e) for e in eigenvalues[:n_vars]]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x, y=ev, mode="lines+markers",
        name="Eigenvalue",
        line=dict(color=BLUE, width=2.5),
        marker=dict(size=8, color=BLUE),
    ))
    fig.add_hline(y=1, line_dash="dash", line_color=RED,
                  annotation_text="Kaiser criterion (λ = 1)",
                  annotation_position="right")
    # Highlight komponen dengan eigenvalue > 1
    sig = [(xi, yi) for xi, yi in zip(x, ev) if yi > 1]
    if sig:
        fig.add_trace(go.Scatter(
            x=[s[0] for s in sig], y=[s[1] for s in sig],
            mode="markers", name="Faktor Signifikan (λ > 1)",
            marker=dict(size=12, color=GREEN, symbol="circle"),
        ))
    fig.update_layout(
        title="Scree Plot — Eigenvalue per Komponen",
        xaxis_title="Nomor Komponen",
        yaxis_title="Eigenvalue (λ)",
        template="plotly_white", height=380,
        margin=dict(l=40, r=40, t=55, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def _plot_loading_heatmap(loading_df: pd.DataFrame, n_factors: int,
                          var_names: list) -> go.Figure:
    factor_cols = [f"Faktor {i+1}" for i in range(n_factors)]
    z_vals = loading_df.set_index("Variabel")[factor_cols].values

    # Warna: merah tinggi (+), putih 0, biru rendah (-)
    fig = go.Figure(go.Heatmap(
        z=z_vals,
        x=factor_cols,
        y=var_names,
        colorscale="RdBu_r",
        zmid=0, zmin=-1, zmax=1,
        text=np.round(z_vals, 2),
        texttemplate="%{text}",
        textfont={"size": 10},
        colorbar={"title": "Loading"},
    ))
    fig.update_layout(
        title="Factor Loading Heatmap",
        template="plotly_white",
        height=max(300, len(var_names) * 35 + 100),
        margin=dict(l=20, r=20, t=55, b=40),
        xaxis={"side": "top"},
    )
    return fig


def _plot_biplot(pca_obj, X_scaled: np.ndarray, var_names: list) -> go.Figure:
    """Biplot PC1 vs PC2."""
    scores  = pca_obj.transform(X_scaled)
    loadings = pca_obj.components_.T

    fig = go.Figure()
    # Observasi (titik)
    fig.add_trace(go.Scatter(
        x=scores[:, 0], y=scores[:, 1],
        mode="markers",
        marker=dict(color=BLUE, size=5, opacity=0.5),
        name="Observasi",
    ))
    # Vektor variabel
    scale = np.max(np.abs(scores)) * 0.8
    for i, vname in enumerate(var_names):
        lx = loadings[i, 0] * scale
        ly = loadings[i, 1] * scale
        fig.add_annotation(
            ax=0, ay=0, axref="x", ayref="y",
            x=lx, y=ly, xref="x", yref="y",
            showarrow=True, arrowhead=2,
            arrowcolor=RED, arrowwidth=1.5,
        )
        fig.add_annotation(
            x=lx * 1.1, y=ly * 1.1, text=vname,
            showarrow=False, font=dict(size=10, color=RED),
        )
    pct = pca_obj.explained_variance_ratio_
    fig.update_layout(
        title=f"PCA Biplot — PC1 ({pct[0]*100:.1f}%) vs PC2 ({pct[1]*100:.1f}%)",
        xaxis_title=f"PC1 ({pct[0]*100:.1f}% var)",
        yaxis_title=f"PC2 ({pct[1]*100:.1f}% var)",
        template="plotly_white", height=420,
        margin=dict(l=40, r=40, t=55, b=40),
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# AI INTERPRETATION
# ─────────────────────────────────────────────────────────────────────────────

def _ai_interpret_efa(kmo_res: dict, efa_res: dict, loading_df: pd.DataFrame,
                      var_names: list, api_key: str, provider: str) -> str:
    kmo_val   = kmo_res["kmo"]
    kmo_label, _ = _interpret_kmo(kmo_val)
    sig_bart  = "signifikan" if kmo_res["p_value"] < 0.05 else "tidak signifikan"
    n_factors = efa_res["n_factors"]
    rotation  = efa_res["rotation"].capitalize()

    # Ringkasan loading per faktor
    factor_cols = [f"Faktor {i+1}" for i in range(n_factors)]
    loading_summary = []
    for fc in factor_cols:
        top = loading_df.nlargest(3, fc)[["Variabel", fc]].values.tolist()
        loading_summary.append({
            "faktor": fc,
            "loading_tertinggi": [{"variabel": v, "loading": round(l, 3)} for v, l in top],
            "var_explained_pct": round(float(efa_res["var_pct"][int(fc[-1])-1]), 2),
        })

    prompt = f"""
Anda adalah statistikawan akademis. Berikut hasil Analisis Faktor Eksploratori (EFA):

── UJI KELAYAKAN ──────────────────────────────────────────
KMO = {kmo_val} → Kategori: {kmo_label}
Bartlett's Test: χ² = {kmo_res['chi2']}, df = {kmo_res['df']}, p = {kmo_res['p_value']} → {sig_bart}
Jumlah variabel: {kmo_res['n_vars']} | Rotasi: {rotation}

── STRUKTUR FAKTOR ────────────────────────────────────────
Jumlah faktor yang diekstrak: {n_factors}
Ringkasan loading per faktor:
{loading_summary}

── VARIABEL ───────────────────────────────────────────────
{', '.join(var_names)}

Buatlah interpretasi mendalam dalam Bahasa Indonesia (3–4 paragraf, gaya jurnal ilmiah):
1. Evaluasi kelayakan data (KMO & Bartlett) — apakah data layak untuk EFA?
2. Jumlah faktor yang tepat dan alasannya (Kaiser criterion, cumulative variance)
3. Interpretasi struktur faktor — variabel mana yang memuat faktor apa? Apakah ada makna konseptual?
4. Rekomendasi untuk penelitian selanjutnya (confirmatory factor analysis, construct validity)

Tulis dengan gaya akademis formal, Bahasa Indonesia baku. Hindari frasa klise AI.
"""
    return call_ai_api(prompt, system="", api_key=api_key, provider=provider)


# ─────────────────────────────────────────────────────────────────────────────
# EXCEL EXPORT
# ─────────────────────────────────────────────────────────────────────────────

def _export_excel(kmo_res: dict, eigenvalue_df: pd.DataFrame,
                  loading_df: pd.DataFrame, variance_df: pd.DataFrame,
                  var_names: list, ai_text: str) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        # Sheet 1: KMO & Bartlett
        kmo_label, _ = _interpret_kmo(kmo_res["kmo"])
        kmo_df = pd.DataFrame({
            "Uji": ["KMO (Overall)", "Bartlett χ²", "Bartlett df", "Bartlett p-value"],
            "Nilai": [kmo_res["kmo"], kmo_res["chi2"], kmo_res["df"], kmo_res["p_value"]],
            "Keterangan": [kmo_label,
                           "Signifikan" if kmo_res["p_value"] < 0.05 else "Tidak Signifikan",
                           "", ""],
        })
        kmo_df.to_excel(writer, sheet_name="KMO & Bartlett", index=False)

        # Sheet 2: KMO per variabel
        kmo_var_df = pd.DataFrame({
            "Variabel": var_names,
            "KMO": kmo_res["kmo_per_var"],
        })
        kmo_var_df.to_excel(writer, sheet_name="KMO per Variabel", index=False)

        # Sheet 3: Eigenvalue
        eigenvalue_df.to_excel(writer, sheet_name="Eigenvalue & Scree", index=False)

        # Sheet 4: Factor Loadings
        loading_df.to_excel(writer, sheet_name="Factor Loadings", index=False)

        # Sheet 5: Variance Explained
        variance_df.to_excel(writer, sheet_name="Variance Explained", index=False)

        # Sheet 6: Interpretasi AI
        if ai_text:
            ai_df = pd.DataFrame({"Interpretasi AI": [ai_text]})
            ai_df.to_excel(writer, sheet_name="Interpretasi AI", index=False)

    buf.seek(0)
    return buf.read()


# ─────────────────────────────────────────────────────────────────────────────
# RENDER UTAMA
# ─────────────────────────────────────────────────────────────────────────────

def render(ctx: dict):
    license_info = ctx["license_info"]
    ai_enabled   = ctx.get("ai_enabled", False)
    api_key      = ctx.get("anthropic_api_key", "")
    provider     = ctx.get("ai_provider", "Claude (Anthropic)")
    alpha        = ctx.get("alpha_level", 0.05)

    # ── Guard Pro ────────────────────────────────────────────────────────────
    if not require_pro(license_info, "Analisis Faktor Eksploratori (EFA)"):
        st.stop()

    st.markdown(
        '<p class="rs-section-title">🔬 Analisis Faktor Eksploratori (EFA)</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="rs-section-sub">'
        'Identifikasi struktur laten di balik variabel manifes — '
        'PCA, EFA Varimax / Oblimin, KMO & Bartlett, Scree Plot, Factor Loading Matrix.'
        '</p>',
        unsafe_allow_html=True,
    )

    # ── Data ─────────────────────────────────────────────────────────────────
    df = require_data()
    if df is None:
        st.stop()

    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if len(num_cols) < 3:
        st.error("❌ EFA memerlukan minimal **3 variabel numerik**. Periksa data Anda.")
        st.stop()

    # ── Sidebar / Konfigurasi ────────────────────────────────────────────────
    st.markdown("### ⚙️ Konfigurasi Analisis")
    col_cfg1, col_cfg2 = st.columns(2)
    with col_cfg1:
        selected_vars = st.multiselect(
            "Pilih variabel untuk EFA (min. 3):",
            options=num_cols,
            default=ss_get("selected_cols", num_cols[:min(10, len(num_cols))]),
            help="Pilih variabel yang merepresentasikan konstruk yang ingin diukur.",
        )
    with col_cfg2:
        rotation_method = st.selectbox(
            "Metode Rotasi:",
            options=["varimax", "oblimin"],
            index=0,
            help=(
                "**Varimax** (orthogonal) — faktor tidak berkorelasi, cocok untuk instrumen independen.\n\n"
                "**Oblimin** (oblique) — faktor boleh berkorelasi, lebih realistis untuk konstruk psikologis."
            ),
        )

    if len(selected_vars) < 3:
        st.warning("⚠️ Pilih minimal **3 variabel** untuk menjalankan EFA.")
        st.stop()

    col_cfg3, col_cfg4 = st.columns(2)
    with col_cfg3:
        auto_factors = st.checkbox(
            "Otomatis tentukan jumlah faktor (Kaiser criterion λ > 1)",
            value=True,
        )
    with col_cfg4:
        loading_threshold = st.slider(
            "Threshold loading bermakna:", 0.20, 0.70, LOADING_THRESH, 0.05,
            help="Loading di bawah threshold akan ditampilkan abu-abu di tabel.",
        )

    if not auto_factors:
        n_factors_manual = st.slider(
            "Jumlah faktor yang diekstrak:",
            min_value=1,
            max_value=min(len(selected_vars) - 1, 10),
            value=min(3, len(selected_vars) - 1),
        )

    run_btn = st.button("▶️ Jalankan EFA", type="primary", use_container_width=True)

    if not run_btn and "efa_results" not in st.session_state:
        st.info("Klik **▶️ Jalankan EFA** untuk memulai analisis.")
        return

    # ── Komputasi ─────────────────────────────────────────────────────────────
    if run_btn:
        with st.spinner("🔬 Menghitung KMO, Eigenvalue, dan Factor Loadings..."):
            try:
                subset = df[selected_vars].apply(pd.to_numeric, errors="coerce").dropna()
                n_obs, n_vars = subset.shape

                if n_obs < n_vars * 5:
                    st.warning(
                        f"⚠️ Rasio observasi:variabel = {n_obs}:{n_vars} "
                        f"({n_obs/n_vars:.1f}:1). Idealnya minimal 5:1 — "
                        "hasil EFA mungkin tidak stabil."
                    )

                X_scaled = StandardScaler().fit_transform(subset.values)

                # KMO & Bartlett
                kmo_res = _compute_kmo_bartlett(X_scaled, n_obs)

                # PCA
                eigenvalues, var_explained, cum_var, pca_obj = _run_pca(X_scaled, n_vars)

                # Tentukan jumlah faktor
                if auto_factors:
                    n_factors = _suggest_n_factors(eigenvalues, cum_var)
                else:
                    n_factors = n_factors_manual

                n_factors = max(1, min(n_factors, n_vars - 1))

                # EFA
                efa_res = _run_efa(X_scaled, n_factors, rotation_method)

                # DataFrames
                eigenvalue_df = _build_eigenvalue_df(
                    eigenvalues[:n_vars], var_explained[:n_vars], cum_var[:n_vars],
                    selected_vars
                )
                loading_df = _build_loading_df(
                    efa_res["loadings"], selected_vars, n_factors, loading_threshold
                )
                variance_df = _build_variance_df(
                    efa_res["ss_loadings"], efa_res["var_pct"], efa_res["cum_var_pct"]
                )

                st.session_state.efa_results = {
                    "kmo_res":       kmo_res,
                    "efa_res":       efa_res,
                    "pca_obj":       pca_obj,
                    "X_scaled":      X_scaled,
                    "eigenvalue_df": eigenvalue_df,
                    "loading_df":    loading_df,
                    "variance_df":   variance_df,
                    "selected_vars": selected_vars,
                    "n_factors":     n_factors,
                    "rotation":      rotation_method,
                    "n_obs":         n_obs,
                    "loading_threshold": loading_threshold,
                }
                st.session_state.efa_ai_text = ""

            except Exception as e:
                st.error(f"❌ Error komputasi EFA: {str(e)}")
                import traceback
                st.code(traceback.format_exc())
                return

    # ── Ambil dari session state ──────────────────────────────────────────────
    res           = st.session_state.efa_results
    kmo_res       = res["kmo_res"]
    efa_res       = res["efa_res"]
    pca_obj       = res["pca_obj"]
    X_scaled      = res["X_scaled"]
    eigenvalue_df = res["eigenvalue_df"]
    loading_df    = res["loading_df"]
    variance_df   = res["variance_df"]
    selected_vars = res["selected_vars"]
    n_factors     = res["n_factors"]
    rotation      = res["rotation"]
    n_obs         = res["n_obs"]
    load_thresh   = res["loading_threshold"]

    # ── HASIL ─────────────────────────────────────────────────────────────────
    st.markdown("---")

    # ── 1. KMO & BARTLETT ────────────────────────────────────────────────────
    st.markdown("### 1. Uji Kelayakan Data")
    kmo_label, kmo_color = _interpret_kmo(kmo_res["kmo"])
    bart_sig = kmo_res["p_value"] < alpha

    col_k1, col_k2, col_k3, col_k4 = st.columns(4)
    with col_k1:
        st.markdown(
            f'<div class="rs-metric">'
            f'<div class="rs-metric-label">KMO Overall</div>'
            f'<div class="rs-metric-value" style="color:{kmo_color}">{kmo_res["kmo"]}</div>'
            f'<div class="rs-metric-sub">{kmo_label}</div>'
            f'</div>', unsafe_allow_html=True,
        )
    with col_k2:
        bart_color = GREEN if bart_sig else RED
        bart_label = f"Signifikan (p < {alpha})" if bart_sig else f"Tidak Sig. (p ≥ {alpha})"
        st.markdown(
            f'<div class="rs-metric">'
            f'<div class="rs-metric-label">Bartlett χ²</div>'
            f'<div class="rs-metric-value" style="color:{bart_color}">{kmo_res["chi2"]}</div>'
            f'<div class="rs-metric-sub">{bart_label}</div>'
            f'</div>', unsafe_allow_html=True,
        )
    with col_k3:
        st.markdown(
            f'<div class="rs-metric">'
            f'<div class="rs-metric-label">p-value Bartlett</div>'
            f'<div class="rs-metric-value">{kmo_res["p_value"]}</div>'
            f'<div class="rs-metric-sub">df = {kmo_res["df"]}</div>'
            f'</div>', unsafe_allow_html=True,
        )
    with col_k4:
        st.markdown(
            f'<div class="rs-metric">'
            f'<div class="rs-metric-label">N Obs / N Vars</div>'
            f'<div class="rs-metric-value">{n_obs} / {kmo_res["n_vars"]}</div>'
            f'<div class="rs-metric-sub">Rasio {n_obs/kmo_res["n_vars"]:.1f}:1</div>'
            f'</div>', unsafe_allow_html=True,
        )

    # Interpretasi kelayakan
    layak = kmo_res["kmo"] >= 0.50 and bart_sig
    if layak:
        st.success(
            f"✅ Data **layak** untuk EFA — KMO = {kmo_res['kmo']} ({kmo_label}), "
            f"Bartlett signifikan (p = {kmo_res['p_value']})."
        )
    else:
        msgs = []
        if kmo_res["kmo"] < 0.50:
            msgs.append(f"KMO = {kmo_res['kmo']} < 0.50 (tidak layak)")
        if not bart_sig:
            msgs.append(f"Bartlett tidak signifikan (p = {kmo_res['p_value']})")
        st.error(f"❌ Data **kurang layak** untuk EFA: {'; '.join(msgs)}.")

    # KMO per variabel
    with st.expander("📋 KMO per Variabel (Anti-Image Correlation)"):
        kmo_var_df = pd.DataFrame({
            "Variabel": selected_vars,
            "KMO": kmo_res["kmo_per_var"],
            "Status": ["✓ Layak" if k >= 0.50 else "✗ Pertimbangkan dikeluarkan"
                       for k in kmo_res["kmo_per_var"]],
        })
        st.dataframe(kmo_var_df, use_container_width=True, hide_index=True)
        n_bad = sum(1 for k in kmo_res["kmo_per_var"] if k < 0.50)
        if n_bad > 0:
            st.warning(
                f"⚠️ {n_bad} variabel memiliki KMO < 0.50. "
                "Pertimbangkan untuk mengeluarkan variabel tersebut dan ulangi analisis."
            )

    # ── 2. SCREE PLOT & EIGENVALUE ────────────────────────────────────────────
    st.markdown("### 2. Scree Plot & Eigenvalue")
    st.markdown(
        f"Berdasarkan **Kaiser criterion (λ > 1)**, disarankan mengekstrak "
        f"**{n_factors} faktor** "
        f"(rotasi: **{rotation.capitalize()}**)."
    )

    col_sc1, col_sc2 = st.columns([3, 2])
    with col_sc1:
        st.plotly_chart(
            _plot_scree(pca_obj.explained_variance_, len(selected_vars)),
            use_container_width=True,
        )
    with col_sc2:
        st.markdown("**Tabel Eigenvalue**")
        st.dataframe(
            eigenvalue_df.style.map(
                lambda v: "color: #3B6D11; font-weight:bold" if v == "✓" else "",
                subset=["Kaiser (>1)"],
            ),
            use_container_width=True,
            hide_index=True,
            height=min(300, len(eigenvalue_df) * 38 + 40),
        )

    # ── 3. FACTOR LOADINGS ────────────────────────────────────────────────────
    st.markdown(f"### 3. Factor Loading Matrix (Rotasi: {rotation.capitalize()})")
    st.caption(
        f"Loading ≥ {load_thresh} dianggap bermakna (ditandai **tebal**). "
        "Communality = proporsi variansi variabel yang dijelaskan oleh semua faktor."
    )

    # Heatmap
    st.plotly_chart(
        _plot_loading_heatmap(loading_df, n_factors, selected_vars),
        use_container_width=True,
    )

    # Tabel loading dengan highlight
    factor_cols = [f"Faktor {i+1}" for i in range(n_factors)]

    def _style_loading(val):
        try:
            v = float(val)
            if abs(v) >= load_thresh:
                if v > 0:
                    intensity = min(255, int(abs(v) * 120))
                    return f"background-color: rgba(24,95,165,{abs(v)*0.6:.2f}); color:white; font-weight:bold"
                else:
                    return f"background-color: rgba(163,45,45,{abs(v)*0.6:.2f}); color:white; font-weight:bold"
            return "color: #aaa"
        except (TypeError, ValueError):
            return ""

    styled_df = loading_df.style.map(_style_loading, subset=factor_cols)
    st.dataframe(styled_df, use_container_width=True, hide_index=True)

    # Tabel variance explained
    st.markdown("**Variance Explained per Faktor**")
    st.dataframe(variance_df, use_container_width=True, hide_index=True)
    total_var = float(efa_res["cum_var_pct"][-1]) if len(efa_res["cum_var_pct"]) > 0 else 0
    st.info(
        f"📊 **{n_factors} faktor** menjelaskan total **{total_var:.1f}%** variansi. "
        f"{'✅ Memadai (≥ 60%)' if total_var >= 60 else '⚠️ Pertimbangkan menambah faktor (< 60%)'}"
    )

    # ── 4. PCA BIPLOT (jika ≥ 2 faktor) ──────────────────────────────────────
    if n_factors >= 2 and len(selected_vars) >= 2:
        st.markdown("### 4. PCA Biplot")
        st.caption("Biplot menampilkan posisi observasi (titik biru) dan arah vektor variabel (merah).")
        st.plotly_chart(_plot_biplot(pca_obj, X_scaled, selected_vars), use_container_width=True)

    # ── 5. INTERPRETASI AI ────────────────────────────────────────────────────
    st.markdown("### 5. Interpretasi AI")
    ai_text = st.session_state.get("efa_ai_text", "")

    if ai_enabled:
        if st.button("🤖 Generate Interpretasi AI", key="efa_ai_btn"):
            with st.spinner("🤖 AI sedang menganalisis struktur faktor..."):
                ai_text = _ai_interpret_efa(
                    kmo_res, efa_res, loading_df,
                    selected_vars, api_key, provider,
                )
                st.session_state.efa_ai_text = ai_text
                # Simpan ke ai_cache["efa"] agar export.py bisa membaca
                if "ai_cache" not in st.session_state:
                    st.session_state.ai_cache = {}
                st.session_state.ai_cache["efa"] = ai_text
    else:
        st.info("🔒 Aktifkan API Key di sidebar untuk interpretasi AI otomatis.")

    if ai_text:
        st.markdown(
            f'<div class="rs-narasi">{ai_text}</div>',
            unsafe_allow_html=True,
        )

    # ── 6. EXPORT EXCEL ───────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📥 Export Hasil")
    if st.button("📊 Download Excel", key="efa_export"):
        excel_bytes = _export_excel(
            kmo_res, eigenvalue_df, loading_df, variance_df,
            selected_vars, ai_text,
        )
        st.download_button(
            label="⬇️ Download Hasil EFA (.xlsx)",
            data=excel_bytes,
            file_name="efa_results.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    # ── Simpan ke session untuk Export Laporan ────────────────────────────────
    st.session_state["efa_session"] = {
        "kmo":         kmo_res["kmo"],
        "kmo_label":   _interpret_kmo(kmo_res["kmo"])[0],
        "bartlett_p":  kmo_res["p_value"],
        "n_factors":   n_factors,
        "rotation":    rotation,
        "total_var":   total_var,
        "loading_df":  loading_df,
        "variance_df": variance_df,
        "ai_text":     ai_text,
    }
