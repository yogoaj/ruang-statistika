"""
modules/sem.py — SEM + CFA via semopy (Pro)
Ruang Statistika v4.0

Perbaikan v4.1:
- AI cache key konsisten: "sem"
- Simpan sem_result lengkap (fit_indices, loadings, path_estimates) untuk export laporan
- AI interpretasi memanggil ai_interpret_sem_full()
- Persamaan/model SEM di-generate oleh AI (ai_generate_model_equation)
- Export Excel lengkap (Parameter Estimates + Fit Indices + Factor Loadings)
- Narasi interpretasi inline setiap tab
- Tambah validitas konvergen (AVE) dan reliabilitas komposit (CR) untuk CFA
"""

import io
import pandas as pd
import numpy as np
import streamlit as st

from utils.auth import require_pro
from utils.stats_helpers import require_data, require_cols, ss_get
from utils.ai_helpers import call_ai_api, ai_interpret_sem_full, ai_generate_model_equation

try:
    from semopy import Model as SemModel
    SEMOPY_AVAILABLE = True
except ImportError:
    SEMOPY_AVAILABLE = False


def render(ctx: dict):
    license_info = ctx["license_info"]
    ai_enabled   = ctx["ai_enabled"]
    api_key      = ctx["anthropic_api_key"]
    ai_provider  = ctx["ai_provider"]

    st.markdown('<p class="rs-section-title">🧩 SEM & CFA (Structural Equation Modeling)</p>',
                unsafe_allow_html=True)
    st.markdown(
        '<p class="rs-section-sub">Model persamaan struktural dan Confirmatory Factor Analysis '
        'via semopy. Fit indices: CFI, RMSEA, SRMR, χ²/df. Interpretasi AI & export laporan.</p>',
        unsafe_allow_html=True,
    )

    if not require_pro(license_info, "SEM"):
        st.stop()

    if not SEMOPY_AVAILABLE:
        st.error("❌ Library **semopy** tidak terinstal. Jalankan: `pip install semopy`")
        st.code("pip install semopy", language="bash")
        st.stop()

    df = require_data()
    if df is None:
        st.stop()
    cols = require_cols(df)
    if cols is None or len(cols) < 3:
        st.warning("⚠️ Diperlukan minimal 3 kolom numerik untuk SEM/CFA.")
        st.stop()

    # ── Mode: SEM atau CFA ────────────────────────────────────────────────
    mode = st.radio(
        "Mode Analisis:",
        ["SEM (Structural Equation Model)", "CFA (Confirmatory Factor Analysis)"],
        horizontal=True,
    )

    st.markdown("---")

    if "CFA" in mode:
        _render_cfa(df, cols, ai_enabled, api_key, ai_provider)
    else:
        _render_sem(df, cols, ai_enabled, api_key, ai_provider)


# ─────────────────────────────────────────────────────────────────────────────
# CFA
# ─────────────────────────────────────────────────────────────────────────────

def _render_cfa(df, cols, ai_enabled, api_key, ai_provider):
    st.markdown("#### CFA — Confirmatory Factor Analysis")
    st.markdown("""
    <div class="rs-narasi">
        📖 <b>CFA</b> menguji apakah indikator-indikator yang dipilih benar-benar
        mengukur konstruk laten yang dimaksud.<br/>
        <b>Acuan loading:</b> λ ≥ 0.50 (Hair et al., 2010) &nbsp;|&nbsp;
        <b>AVE ≥ 0.50</b> (validitas konvergen) &nbsp;|&nbsp;
        <b>CR ≥ 0.70</b> (reliabilitas komposit)
    </div>
    """, unsafe_allow_html=True)

    n_factors = st.number_input("Jumlah Konstruk Laten:", 1, 10, 2, 1)
    factor_specs = []
    factor_map   = {}   # {nama_konstruk: [indikator]}

    for i in range(int(n_factors)):
        st.markdown(f"**Konstruk {i+1}:**")
        c1, c2 = st.columns([1, 3])
        with c1:
            fname = st.text_input(f"Nama Konstruk {i+1}:", value=f"F{i+1}", key=f"fn_{i}")
        with c2:
            indicators = st.multiselect(f"Indikator:", cols, key=f"fi_{i}")
        if fname and len(indicators) >= 2:
            factor_specs.append(f"{fname} =~ {' + '.join(indicators)}")
            factor_map[fname] = indicators
        elif fname and len(indicators) == 1:
            st.warning(f"⚠️ Konstruk **{fname}** memerlukan minimal 2 indikator.")

    if not factor_specs:
        st.info("Tentukan minimal 1 konstruk dengan ≥ 2 indikator untuk menjalankan CFA.")
        return

    model_syntax = "\n".join(factor_specs)
    st.code(model_syntax, language="text")

    if st.button("▶ Jalankan CFA", type="primary"):
        _run_sem_model(
            df, cols, model_syntax, "CFA",
            ai_enabled, api_key, ai_provider,
            factor_map=factor_map,
        )


# ─────────────────────────────────────────────────────────────────────────────
# SEM
# ─────────────────────────────────────────────────────────────────────────────

def _render_sem(df, cols, ai_enabled, api_key, ai_provider):
    st.markdown("#### SEM — Structural Equation Model")
    st.markdown("""
    <div class="rs-narasi">
    📖 <b>Sintaks Model semopy:</b><br/>
    • <code>eta =~ y1 + y2 + y3</code> — Measurement model (bagian CFA)<br/>
    • <code>eta ~ xi1 + xi2</code> &nbsp;&nbsp;&nbsp; — Structural path (jalur struktural)<br/>
    • <code>y1 ~~ y2</code> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; — Kovarians residual (opsional)<br/><br/>
    <b>Acuan fit:</b> CFI ≥ 0.90 | RMSEA ≤ 0.08 | SRMR ≤ 0.08 | χ²/df ≤ 2.0
    </div>
    """, unsafe_allow_html=True)

    default_syntax = ""
    if len(cols) >= 4:
        default_syntax = (
            f"# Measurement Model\n"
            f"Eta =~ {cols[0]} + {cols[1]}\n"
            f"Xi  =~ {cols[2]} + {cols[3]}\n\n"
            f"# Structural Path\n"
            f"Eta ~ Xi"
        )

    model_syntax = st.text_area(
        "Model Syntax (semopy):",
        value=default_syntax,
        height=200,
        key="sem_syntax",
        help="Gunakan format semopy. Lihat contoh di narasi di atas.",
    )

    if st.button("▶ Jalankan SEM", type="primary"):
        if not model_syntax.strip():
            st.warning("⚠️ Masukkan sintaks model terlebih dahulu.")
            return
        _run_sem_model(
            df, cols, model_syntax, "SEM",
            ai_enabled, api_key, ai_provider,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Core runner
# ─────────────────────────────────────────────────────────────────────────────

def _run_sem_model(df, cols, model_syntax, mode_label, ai_enabled, api_key, ai_provider,
                   factor_map: dict | None = None):
    """
    Fit model SEM/CFA, tampilkan hasil, simpan ke session_state,
    dan optionally generate AI interpretasi + persamaan model.
    """
    try:
        with st.spinner(f"⏳ Fitting {mode_label} model…"):
            data_sem  = df[cols].dropna()
            sem_model = SemModel(model_syntax)
            sem_model.fit(data_sem)
    except Exception as e:
        st.error(f"❌ Gagal fitting model: {e}")
        st.info(
            "Pastikan sintaks model sesuai format semopy dan "
            "semua variabel tersedia di dataset yang dipilih."
        )
        return

    st.success(f"✅ Model {mode_label} berhasil di-fit!")

    # ── Kumpulkan semua hasil ────────────────────────────────────────────
    inspect_df = sem_model.inspect()
    fit_df     = _calc_fit_indices(sem_model)
    loadings_df = _extract_loadings(inspect_df, mode_label)
    path_df    = _extract_paths(inspect_df, mode_label)
    ave_cr_df  = _calc_ave_cr(inspect_df, factor_map) if factor_map else None

    # ── Simpan ke session_state — konsisten dengan collect_session_results ──
    st.session_state["sem_result"] = {
        "mode":           mode_label,
        "model_syntax":   model_syntax,
        "fit_indices":    fit_df,
        "loadings":       loadings_df,
        "path_estimates": path_df,
        "ave_cr":         ave_cr_df,
        "inspect_raw":    inspect_df,
    }

    # ── Tab hasil ────────────────────────────────────────────────────────
    tab_labels = ["📐 Fit Indices", "📊 Parameter Estimates"]
    if loadings_df is not None and not loadings_df.empty:
        tab_labels.append("🔗 Factor Loadings")
    if path_df is not None and not path_df.empty:
        tab_labels.append("🔀 Jalur Struktural")
    if ave_cr_df is not None and not ave_cr_df.empty:
        tab_labels.append("✅ AVE & CR")

    tabs = st.tabs(tab_labels)
    tab_idx = 0

    # ── Tab: Fit Indices ─────────────────────────────────────────────────
    with tabs[tab_idx]:
        tab_idx += 1
        st.markdown("#### Indeks Kecocokan Model (Goodness of Fit)")

        if fit_df is not None and not fit_df.empty:
            st.dataframe(fit_df, use_container_width=True, hide_index=True)

            n_good = fit_df["Status"].str.contains("✅").sum() if "Status" in fit_df.columns else 0
            n_total = len(fit_df)
            verdict = "✅ Model diterima — fit memadai." if n_good >= n_total * 0.75 else \
                      "⚠️ Model perlu modifikasi — beberapa indeks belum memenuhi kriteria."
            color   = "#3b6d11" if n_good >= n_total * 0.75 else "#a32d2d"

            st.markdown(
                f'<div class="rs-narasi">'
                f'📊 <b>Model Fit Summary:</b> {n_good}/{n_total} indeks memenuhi kriteria.<br/>'
                f'<span style="color:{color};font-weight:600;">{verdict}</span><br/><br/>'
                f'<b>Acuan (Hair et al., 2010):</b> CFI ≥ 0.90 | TLI ≥ 0.90 | '
                f'RMSEA ≤ 0.08 | SRMR ≤ 0.08 | χ²/df ≤ 2.0'
                f'</div>',
                unsafe_allow_html=True,
            )
        else:
            st.info("Fit indices tidak dapat dihitung.")

    # ── Tab: Parameter Estimates ─────────────────────────────────────────
    with tabs[tab_idx]:
        tab_idx += 1
        st.markdown("#### Parameter Estimates (Semua Jalur)")
        if inspect_df is not None and not inspect_df.empty:
            # Highlight kolom p-value
            styled_df = inspect_df.copy()
            if "p-value" in styled_df.columns:
                styled_df["Signifikan"] = styled_df["p-value"].apply(
                    lambda p: "✓" if (isinstance(p, (int, float)) and p < 0.05) else "–"
                )
            st.dataframe(styled_df, use_container_width=True, hide_index=True)
        else:
            st.info("Parameter estimates tidak tersedia.")

    # ── Tab: Factor Loadings ─────────────────────────────────────────────
    if loadings_df is not None and not loadings_df.empty and tab_idx < len(tabs):
        with tabs[tab_idx]:
            tab_idx += 1
            st.markdown("#### Factor Loadings (Measurement Model)")
            st.info("Acuan: loading ≥ 0.50 dianggap memadai (Hair et al., 2010).")
            st.dataframe(loadings_df, use_container_width=True, hide_index=True)

            # Highlight loading lemah
            if "Loading (λ)" in loadings_df.columns:
                weak = loadings_df[
                    pd.to_numeric(loadings_df["Loading (λ)"], errors="coerce") < 0.50
                ]
                if not weak.empty:
                    st.warning(
                        f"⚠️ {len(weak)} indikator memiliki loading < 0.50: "
                        f"{', '.join(weak['Indikator'].tolist() if 'Indikator' in weak.columns else [])}"
                    )

    # ── Tab: Jalur Struktural ─────────────────────────────────────────────
    if path_df is not None and not path_df.empty and tab_idx < len(tabs):
        with tabs[tab_idx]:
            tab_idx += 1
            st.markdown("#### Estimasi Jalur Struktural")
            st.dataframe(path_df, use_container_width=True, hide_index=True)

            # Narasi jalur signifikan
            sig_paths = path_df[path_df["Signifikan"] == "✓"] if "Signifikan" in path_df.columns else pd.DataFrame()
            if not sig_paths.empty:
                narasi = []
                for _, row in sig_paths.iterrows():
                    narasi.append(
                        f"<b>{row.get('Dari', '?')} → {row.get('Ke', '?')}</b>: "
                        f"β = {row.get('Estimate', '?')}, p = {row.get('p-value', '?')}"
                    )
                st.markdown(
                    '<div class="rs-narasi">📌 <b>Jalur Signifikan (p < 0.05):</b><br/>'
                    + "<br/>".join(narasi) + "</div>",
                    unsafe_allow_html=True,
                )

    # ── Tab: AVE & CR ────────────────────────────────────────────────────
    if ave_cr_df is not None and not ave_cr_df.empty and tab_idx < len(tabs):
        with tabs[tab_idx]:
            tab_idx += 1
            st.markdown("#### Validitas Konvergen (AVE) & Reliabilitas Komposit (CR)")
            st.info(
                "**AVE ≥ 0.50** = validitas konvergen terpenuhi (Fornell & Larcker, 1981) | "
                "**CR ≥ 0.70** = reliabilitas komposit terpenuhi (Hair et al., 2010)"
            )
            st.dataframe(ave_cr_df, use_container_width=True, hide_index=True)

    st.markdown("---")

    # ── Export Excel ──────────────────────────────────────────────────────
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        if inspect_df is not None and not inspect_df.empty:
            inspect_df.to_excel(writer, sheet_name="Parameter_Estimates", index=False)
        if fit_df is not None and not fit_df.empty:
            fit_df.to_excel(writer, sheet_name="Fit_Indices", index=False)
        if loadings_df is not None and not loadings_df.empty:
            loadings_df.to_excel(writer, sheet_name="Factor_Loadings", index=False)
        if path_df is not None and not path_df.empty:
            path_df.to_excel(writer, sheet_name="Structural_Paths", index=False)
        if ave_cr_df is not None and not ave_cr_df.empty:
            ave_cr_df.to_excel(writer, sheet_name="AVE_CR", index=False)
        # Model syntax sebagai sheet teks
        pd.DataFrame({"Model Syntax": model_syntax.split("\n")}).to_excel(
            writer, sheet_name="Model_Syntax", index=False
        )
    buf.seek(0)
    st.download_button(
        "⬇️ Export Lengkap ke Excel (.xlsx)",
        data=buf,
        file_name=f"{mode_label}_results.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    # ── AI Interpretasi ───────────────────────────────────────────────────
    if ai_enabled:
        col_ai1, col_ai2 = st.columns(2)

        with col_ai1:
            if st.button(f"🤖 Interpretasi {mode_label} dengan AI", key="ai_sem_btn"):
                result_data = {
                    "fit_indices":    fit_df,
                    "loadings":       loadings_df,
                    "path_estimates": path_df,
                }
                with st.spinner(f"🤖 AI menganalisis {mode_label}…"):
                    ai_sem = ai_interpret_sem_full(result_data, api_key, ai_provider)

                if "ai_cache" not in st.session_state:
                    st.session_state.ai_cache = {}
                st.session_state.ai_cache["sem"] = ai_sem
                st.rerun()

        with col_ai2:
            if st.button("📐 Generate Persamaan Model", key="ai_sem_eq_btn"):
                result_data = {
                    "fit_indices":    fit_df,
                    "loadings":       loadings_df,
                    "path_estimates": path_df,
                }
                with st.spinner("📐 AI menyusun persamaan model…"):
                    eq_text = ai_generate_model_equation(
                        "sem", result_data, api_key, ai_provider
                    )
                if "ai_cache" not in st.session_state:
                    st.session_state.ai_cache = {}
                st.session_state.ai_cache["sem_equation"] = eq_text
                st.rerun()

        # Tampilkan persamaan model jika ada
        cached_eq = ss_get("ai_cache", {}).get("sem_equation")
        if cached_eq and not str(cached_eq).startswith(("❌", "⚠️")):
            st.markdown(
                '<div style="background:#f0f6ff;border-left:4px solid #0c2340;'
                'border-radius:0 10px 10px 0;padding:1rem 1.25rem;margin-bottom:0.75rem;">'
                '<b style="color:#0c2340;">📐 Model Persamaan Penelitian:</b><br/><br/>'
                + cached_eq.replace("**", "").replace("\n", "<br/>")
                + "</div>",
                unsafe_allow_html=True,
            )

        # Tampilkan interpretasi AI
        cached_sem = ss_get("ai_cache", {}).get("sem")
        if cached_sem:
            st.markdown(
                f'<div class="rs-ai-narasi">'
                f'<span class="rs-ai-badge">✨ AI — {ai_provider.split("(")[0].strip()}</span><br/>'
                f'{cached_sem.replace(chr(10), "<br/>")}'
                f"</div>",
                unsafe_allow_html=True,
            )


# ─────────────────────────────────────────────────────────────────────────────
# Helper: Hitung Fit Indices
# ─────────────────────────────────────────────────────────────────────────────

def _calc_fit_indices(sem_model) -> pd.DataFrame:
    """Hitung dan format fit indices dari semopy model."""
    try:
        from semopy.stats import calc_stats
        fit_stats = calc_stats(sem_model)
    except Exception:
        try:
            fit_stats = sem_model.calc_stats() if hasattr(sem_model, "calc_stats") else {}
        except Exception:
            fit_stats = {}

    fit_rows = []

    # CFI
    cfi = fit_stats.get("CFI") or fit_stats.get("cfi")
    fit_rows.append({
        "Indeks":   "CFI (Comparative Fit Index)",
        "Nilai":    _fmt_val(cfi),
        "Kriteria": "≥ 0.90",
        "Status":   _status_cfi(cfi),
    })

    # TLI
    tli = fit_stats.get("TLI") or fit_stats.get("tli") or fit_stats.get("NNFI")
    fit_rows.append({
        "Indeks":   "TLI / NNFI",
        "Nilai":    _fmt_val(tli),
        "Kriteria": "≥ 0.90",
        "Status":   _status_cfi(tli),   # kriteria sama dengan CFI
    })

    # RMSEA
    rmsea = fit_stats.get("RMSEA") or fit_stats.get("rmsea")
    fit_rows.append({
        "Indeks":   "RMSEA",
        "Nilai":    _fmt_val(rmsea),
        "Kriteria": "≤ 0.08",
        "Status":   ("✅ Good" if rmsea and float(rmsea) <= 0.05 else
                     "🟡 Acceptable" if rmsea and float(rmsea) <= 0.08 else "❌ Poor")
        if rmsea is not None else "–",
    })

    # SRMR
    srmr = fit_stats.get("SRMR") or fit_stats.get("srmr")
    fit_rows.append({
        "Indeks":   "SRMR",
        "Nilai":    _fmt_val(srmr),
        "Kriteria": "≤ 0.08",
        "Status":   ("✅ Good" if srmr and float(srmr) <= 0.05 else
                     "🟡 Acceptable" if srmr and float(srmr) <= 0.08 else "❌ Poor")
        if srmr is not None else "–",
    })

    # Chi-square / df
    chi2 = fit_stats.get("chi2") or fit_stats.get("Chi2") or fit_stats.get("chi_2")
    dof  = fit_stats.get("dof")  or fit_stats.get("df")
    chi2_df_val = None
    if chi2 is not None and dof is not None and float(dof) > 0:
        chi2_df_val = float(chi2) / float(dof)
    fit_rows.append({
        "Indeks":   "χ²/df (CMIN/DF)",
        "Nilai":    _fmt_val(chi2_df_val),
        "Kriteria": "≤ 2.0",
        "Status":   ("✅ Good" if chi2_df_val and chi2_df_val <= 2.0 else
                     "🟡 Acceptable" if chi2_df_val and chi2_df_val <= 3.0 else "❌ Poor")
        if chi2_df_val is not None else "–",
    })

    # GFI (jika tersedia)
    gfi = fit_stats.get("GFI") or fit_stats.get("gfi")
    if gfi is not None:
        fit_rows.append({
            "Indeks":   "GFI (Goodness of Fit Index)",
            "Nilai":    _fmt_val(gfi),
            "Kriteria": "≥ 0.90",
            "Status":   _status_cfi(gfi),
        })

    return pd.DataFrame(fit_rows)


def _fmt_val(v) -> str:
    if v is None:
        return "N/A"
    try:
        return str(round(float(v), 4))
    except Exception:
        return str(v)


def _status_cfi(v) -> str:
    if v is None:
        return "–"
    try:
        fv = float(v)
        if fv >= 0.95: return "✅ Good"
        if fv >= 0.90: return "🟡 Acceptable"
        return "❌ Poor"
    except Exception:
        return "–"


# ─────────────────────────────────────────────────────────────────────────────
# Helper: Ekstrak Factor Loadings dari inspect_df
# ─────────────────────────────────────────────────────────────────────────────

def _extract_loadings(inspect_df: pd.DataFrame, mode_label: str) -> pd.DataFrame | None:
    """Pisahkan baris loading (=~) dari tabel parameter estimates."""
    if inspect_df is None or inspect_df.empty:
        return None

    # Semopy menggunakan kolom "op" untuk tipe relasi
    op_col = None
    for c in inspect_df.columns:
        if c.lower() in ("op", "operator", "rel", "relation"):
            op_col = c
            break

    if op_col is None:
        # Fallback: cari baris dengan "=~" di string representation
        mask = inspect_df.astype(str).apply(
            lambda row: row.str.contains("=~").any(), axis=1
        )
        sub = inspect_df[mask].copy()
    else:
        sub = inspect_df[inspect_df[op_col] == "=~"].copy()

    if sub.empty:
        return None

    # Rename kolom agar ramah ekspor
    col_map = {}
    for c in sub.columns:
        cl = c.lower()
        if cl in ("lval", "lhs", "from", "latent", "construct"):
            col_map[c] = "Konstruk Laten"
        elif cl in ("rval", "rhs", "to", "indicator", "observed"):
            col_map[c] = "Indikator"
        elif cl in ("estimate", "coef", "loading", "value", "est"):
            col_map[c] = "Loading (λ)"
        elif cl in ("se", "std.err", "std_err", "std. err."):
            col_map[c] = "SE"
        elif cl in ("z", "z-value", "z_value", "t", "t-value"):
            col_map[c] = "z"
        elif cl in ("p-value", "pvalue", "p_value", "pr(>|z|)"):
            col_map[c] = "p-value"

    sub = sub.rename(columns=col_map)

    # Tambah kolom Signifikan & Status Loading
    if "p-value" in sub.columns:
        sub["Signifikan"] = sub["p-value"].apply(
            lambda p: "✓" if (isinstance(p, (int, float)) and not np.isnan(float(p))
                              and float(p) < 0.05) else "–"
        )
    if "Loading (λ)" in sub.columns:
        sub["Kecukupan"] = sub["Loading (λ)"].apply(
            lambda l: "✅ Memadai" if (isinstance(l, (int, float))
                                        and abs(float(l)) >= 0.50) else "⚠️ Rendah"
            if isinstance(l, (int, float)) else "–"
        )

    return sub.reset_index(drop=True)


# ─────────────────────────────────────────────────────────────────────────────
# Helper: Ekstrak Jalur Struktural dari inspect_df
# ─────────────────────────────────────────────────────────────────────────────

def _extract_paths(inspect_df: pd.DataFrame, mode_label: str) -> pd.DataFrame | None:
    """Pisahkan baris jalur struktural (~) dari tabel parameter estimates."""
    if inspect_df is None or inspect_df.empty:
        return None
    if mode_label == "CFA":
        return None   # CFA tidak punya jalur struktural

    op_col = None
    for c in inspect_df.columns:
        if c.lower() in ("op", "operator", "rel", "relation"):
            op_col = c
            break

    if op_col is None:
        mask = inspect_df.astype(str).apply(
            lambda row: row.str.contains(r"(?<!=)~(?!=)").any(), axis=1
        )
        sub = inspect_df[mask].copy()
    else:
        sub = inspect_df[inspect_df[op_col] == "~"].copy()

    if sub.empty:
        return None

    col_map = {}
    for c in sub.columns:
        cl = c.lower()
        if cl in ("lval", "lhs", "from"):
            col_map[c] = "Ke (Endogen)"
        elif cl in ("rval", "rhs", "to"):
            col_map[c] = "Dari (Eksogen)"
        elif cl in ("estimate", "coef", "value", "est"):
            col_map[c] = "Estimate (β)"
        elif cl in ("se", "std.err", "std_err"):
            col_map[c] = "SE"
        elif cl in ("z", "z-value", "t", "t-value"):
            col_map[c] = "z"
        elif cl in ("p-value", "pvalue", "p_value"):
            col_map[c] = "p-value"

    sub = sub.rename(columns=col_map)

    if "p-value" in sub.columns:
        sub["Signifikan"] = sub["p-value"].apply(
            lambda p: "✓" if (isinstance(p, (int, float)) and not np.isnan(float(p))
                              and float(p) < 0.05) else "–"
        )
        sub["Keputusan"] = sub["p-value"].apply(
            lambda p: "Diterima ✓" if (isinstance(p, (int, float))
                                        and not np.isnan(float(p))
                                        and float(p) < 0.05) else "Ditolak ✗"
        )

    return sub.reset_index(drop=True)


# ─────────────────────────────────────────────────────────────────────────────
# Helper: Hitung AVE & CR untuk CFA
# ─────────────────────────────────────────────────────────────────────────────

def _calc_ave_cr(inspect_df: pd.DataFrame, factor_map: dict) -> pd.DataFrame | None:
    """
    Hitung Average Variance Extracted (AVE) dan Composite Reliability (CR)
    dari loading yang diestimasi.

    AVE = Σ(λ²) / [Σ(λ²) + Σ(1 - λ²)]
    CR  = [Σλ]² / ([Σλ]² + Σ(1 - λ²))
    """
    if inspect_df is None or inspect_df.empty or not factor_map:
        return None

    # Ambil tabel loading
    loadings_df = _extract_loadings(inspect_df, "CFA")
    if loadings_df is None or "Loading (λ)" not in loadings_df.columns:
        return None

    rows = []
    for construct, indicators in factor_map.items():
        # Filter loading untuk konstruk ini
        if "Konstruk Laten" in loadings_df.columns:
            mask = loadings_df["Konstruk Laten"].astype(str).str.strip() == construct
        else:
            mask = pd.Series([False] * len(loadings_df))

        sub = loadings_df[mask]
        if sub.empty:
            continue

        lambdas = pd.to_numeric(sub["Loading (λ)"], errors="coerce").dropna().tolist()
        if not lambdas:
            continue

        l_sq   = [l**2 for l in lambdas]
        err    = [1 - l2 for l2 in l_sq]
        ave    = sum(l_sq) / (sum(l_sq) + sum(err)) if (sum(l_sq) + sum(err)) > 0 else None
        sum_l  = sum(lambdas)
        cr_val = (sum_l ** 2) / (sum_l ** 2 + sum(err)) if (sum_l ** 2 + sum(err)) > 0 else None

        rows.append({
            "Konstruk":             construct,
            "N Indikator":          len(lambdas),
            "AVE":                  round(ave, 4) if ave is not None else "N/A",
            "CR (Composite Rel.)":  round(cr_val, 4) if cr_val is not None else "N/A",
            "AVE Status":           ("✅ ≥ 0.50" if ave and ave >= 0.50 else "❌ < 0.50")
                                    if ave is not None else "–",
            "CR Status":            ("✅ ≥ 0.70" if cr_val and cr_val >= 0.70 else "❌ < 0.70")
                                    if cr_val is not None else "–",
        })

    return pd.DataFrame(rows) if rows else None
