"""
modules/cfa.py — CFA Standalone (Confirmatory Factor Analysis) — Pro ★
Ruang Statistika v4.2

Fitur utama:
- Model 1-faktor & multi-faktor via semopy
- Factor Loadings lengkap dengan status kecukupan
- AVE (Average Variance Extracted) — validitas konvergen
- Composite Reliability (CR) — reliabilitas komposit
- Discriminant Validity: HTMT (Henseler et al., 2015) & Fornell-Larcker Criterion
- Fit Indices detail: CFI, TLI, RMSEA, SRMR, χ²/df, GFI, NFI, AIC, BIC
- Modification Indices — saran perbaikan model
- Diagram loading visual (bar chart per konstruk)
- AI interpretasi lengkap (Bahasa Indonesia akademis)
- Export Excel multi-sheet & teks laporan siap tempel

Referensi:
- Hair et al. (2010): loading ≥ 0.50, AVE ≥ 0.50, CR ≥ 0.70
- Fornell & Larcker (1981): AVE > korelasi²
- Henseler et al. (2015): HTMT < 0.90 (konservatif < 0.85)
- Hu & Bentler (1999): CFI ≥ 0.95, RMSEA ≤ 0.06
"""

import io
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

from utils.auth import require_pro
from utils.stats_helpers import require_data, require_cols, ss_get
from utils.ai_helpers import call_ai_api

try:
    from semopy import Model as SemModel
    SEMOPY_AVAILABLE = True
except ImportError:
    SEMOPY_AVAILABLE = False


# ── Konstanta warna ──────────────────────────────────────────────────────────
BLUE  = "#185FA5"
NAVY  = "#0c2340"
GREEN = "#3B6D11"
RED   = "#A32D2D"
RED2  = "#E24B4A"


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def render(ctx: dict):
    license_info = ctx["license_info"]
    ai_enabled   = ctx["ai_enabled"]
    api_key      = ctx["anthropic_api_key"]
    ai_provider  = ctx["ai_provider"]

    st.markdown(
        '<p class="rs-section-title">🔬 CFA Standalone — Confirmatory Factor Analysis</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="rs-section-sub">'
        'Validasi konstruk laten: factor loadings, AVE, Composite Reliability, '
        'discriminant validity (HTMT & Fornell-Larcker), dan fit indices lengkap.'
        '</p>',
        unsafe_allow_html=True,
    )

    if not require_pro(license_info, "CFA Standalone"):
        st.stop()

    if not SEMOPY_AVAILABLE:
        st.error("❌ Library **semopy** tidak terinstal.")
        st.code("pip install semopy", language="bash")
        st.stop()

    df = require_data()
    if df is None:
        st.stop()
    cols = require_cols(df)
    if cols is None or len(cols) < 2:
        st.warning("⚠️ Diperlukan minimal 2 kolom numerik untuk CFA.")
        st.stop()

    _render_cfa_ui(df, cols, ai_enabled, api_key, ai_provider)


# ─────────────────────────────────────────────────────────────────────────────
# UI utama: spesifikasi model
# ─────────────────────────────────────────────────────────────────────────────

def _render_cfa_ui(df, cols, ai_enabled, api_key, ai_provider):

    # ── Narasi panduan ───────────────────────────────────────────────────
    with st.expander("📖 Panduan CFA & Kriteria Evaluasi", expanded=False):
        st.markdown("""
**Alur CFA:**
1. Tentukan jumlah konstruk laten dan beri nama
2. Pilih indikator (≥ 2 per konstruk, idealnya ≥ 3)
3. Jalankan model → evaluasi loadings, fit indices, AVE/CR, HTMT
4. Modifikasi model jika diperlukan (lihat Modification Indices)

| Kriteria | Nilai Ideal | Sumber |
|---|---|---|
| Factor Loading (λ) | ≥ 0.50 (min), ≥ 0.70 (ideal) | Hair et al. (2010) |
| AVE | ≥ 0.50 | Fornell & Larcker (1981) |
| CR (Composite Reliability) | ≥ 0.70 | Hair et al. (2010) |
| HTMT | < 0.90 (konservatif: < 0.85) | Henseler et al. (2015) |
| CFI / TLI | ≥ 0.90 (good: ≥ 0.95) | Hu & Bentler (1999) |
| RMSEA | ≤ 0.08 (good: ≤ 0.05) | Browne & Cudeck (1993) |
| SRMR | ≤ 0.08 | Hu & Bentler (1999) |
| χ²/df | ≤ 3.0 (good: ≤ 2.0) | Carmines & McIver (1981) |
        """)

    st.markdown("---")
    st.markdown("### ⚙️ Spesifikasi Model CFA")

    n_factors = st.number_input(
        "Jumlah Konstruk Laten:",
        min_value=1, max_value=15, value=2, step=1,
        help="Satu konstruk = CFA 1-faktor. Dua+ = multi-faktor.",
    )

    factor_map: dict[str, list[str]] = {}   # {nama: [indikator]}
    all_indicators_used = []

    for i in range(int(n_factors)):
        with st.container():
            st.markdown(
                f'<div style="background:#f7faff;border:1px solid #d0e4f7;border-radius:10px;'
                f'padding:0.85rem 1rem 0.6rem;margin-bottom:0.6rem;">'
                f'<b style="color:{NAVY};">Konstruk {i + 1}</b></div>',
                unsafe_allow_html=True,
            )
            c1, c2 = st.columns([1, 3])
            with c1:
                fname = st.text_input(
                    "Nama Konstruk:", value=f"F{i + 1}",
                    key=f"cfa_fn_{i}",
                    label_visibility="collapsed",
                    placeholder=f"Nama Konstruk {i + 1}",
                )
            with c2:
                # Exclude indikator yang sudah dipakai di konstruk lain
                available = [c for c in cols if c not in all_indicators_used]
                indicators = st.multiselect(
                    "Pilih Indikator:",
                    options=cols,          # tampilkan semua tapi beri warning jika duplikat
                    key=f"cfa_fi_{i}",
                    placeholder="Pilih ≥ 2 indikator…",
                    label_visibility="collapsed",
                )

            if fname and len(indicators) >= 2:
                factor_map[fname] = indicators
                all_indicators_used.extend(indicators)
            elif fname and len(indicators) == 1:
                st.caption(f"⚠️ **{fname}** butuh ≥ 2 indikator.")

    # ── Cek duplikat lintas konstruk ─────────────────────────────────────
    flat = [ind for inds in factor_map.values() for ind in inds]
    duplikat = [ind for ind in flat if flat.count(ind) > 1]
    if duplikat:
        st.warning(
            f"⚠️ Indikator berikut muncul di lebih dari satu konstruk: "
            f"**{', '.join(set(duplikat))}**. "
            f"Setiap indikator sebaiknya hanya mengukur satu konstruk."
        )

    if not factor_map:
        st.info("Tentukan minimal 1 konstruk dengan ≥ 2 indikator untuk menjalankan CFA.")
        return

    # ── Tampilkan sintaks model ───────────────────────────────────────────
    model_lines = [f"{fname} =~ {' + '.join(inds)}" for fname, inds in factor_map.items()]
    model_syntax = "\n".join(model_lines)

    st.markdown("**Model Syntax (semopy):**")
    st.code(model_syntax, language="text")

    # ── Opsi tambahan ──────────────────────────────────────────────────
    with st.expander("⚙️ Opsi Lanjutan", expanded=False):
        alpha_level = st.select_slider(
            "Tingkat Signifikansi (α):", options=[0.01, 0.05, 0.10], value=0.05
        )
        show_mi     = st.checkbox("Tampilkan Modification Indices", value=True)
        show_std    = st.checkbox("Tampilkan Standardized Loading (jika tersedia)", value=True)

    st.markdown("---")

    # ── Tombol jalankan ───────────────────────────────────────────────────
    col_run, col_reset = st.columns([3, 1])
    with col_run:
        run_btn = st.button("▶ Jalankan CFA", type="primary", use_container_width=True)
    with col_reset:
        if st.button("🔄 Reset", use_container_width=True):
            for key in ["cfa_result"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

    if run_btn:
        result = _run_cfa(df, cols, model_syntax, factor_map, alpha_level)
        if result:
            st.session_state["cfa_result"] = result
            st.rerun()

    # ── Tampilkan hasil jika tersedia ─────────────────────────────────────
    cfa_result = ss_get("cfa_result")
    if cfa_result:
        _render_cfa_results(
            cfa_result, factor_map, show_mi, show_std,
            ai_enabled, api_key, ai_provider,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Engine: fitting model
# ─────────────────────────────────────────────────────────────────────────────

def _run_cfa(df, cols, model_syntax, factor_map, alpha_level) -> dict | None:
    """Fit CFA model, hitung semua metrik, kembalikan dict hasil."""
    try:
        with st.spinner("⏳ Fitting CFA model…"):
            data_cfa  = df[cols].dropna()
            sem_model = SemModel(model_syntax)
            sem_model.fit(data_cfa)
    except Exception as e:
        st.error(f"❌ Gagal fitting model: {e}")
        st.info(
            "Pastikan semua variabel tersedia di dataset, "
            "tidak ada kolom dengan nilai konstan, "
            "dan sintaks model sesuai format semopy."
        )
        return None

    st.success("✅ Model CFA berhasil di-fit!")

    inspect_df   = sem_model.inspect()
    fit_df       = _calc_fit_indices(sem_model)
    loadings_df  = _extract_loadings(inspect_df, alpha_level)
    ave_cr_df    = _calc_ave_cr(loadings_df, factor_map)
    htmt_df      = _calc_htmt(data_cfa, factor_map, loadings_df)
    fl_df        = _calc_fornell_larcker(ave_cr_df, data_cfa, factor_map, loadings_df)
    mi_df        = _calc_modification_indices(sem_model)
    corr_df      = data_cfa.corr()

    return {
        "inspect_df":   inspect_df,
        "fit_df":       fit_df,
        "loadings_df":  loadings_df,
        "ave_cr_df":    ave_cr_df,
        "htmt_df":      htmt_df,
        "fl_df":        fl_df,
        "mi_df":        mi_df,
        "corr_df":      corr_df,
        "model_syntax": model_syntax,
        "factor_map":   factor_map,
        "alpha_level":  alpha_level,
        "n_obs":        len(data_cfa),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Render hasil lengkap
# ─────────────────────────────────────────────────────────────────────────────

def _render_cfa_results(result, factor_map, show_mi, show_std,
                         ai_enabled, api_key, ai_provider):

    st.markdown("---")
    st.markdown("## 📊 Hasil CFA")
    st.caption(f"N observasi: **{result['n_obs']}** | Konstruk: **{len(factor_map)}**")

    # ── Tab layout ────────────────────────────────────────────────────────
    tab_labels = [
        "📐 Fit Indices",
        "🔗 Factor Loadings",
        "✅ AVE & CR",
        "🔀 Discriminant Validity",
        "📊 Diagram Loading",
        "📋 Parameter Estimates",
    ]
    if show_mi and result["mi_df"] is not None and not result["mi_df"].empty:
        tab_labels.append("🔧 Modification Indices")

    tabs = st.tabs(tab_labels)
    tidx = 0

    # ── TAB 1: Fit Indices ────────────────────────────────────────────────
    with tabs[tidx]:
        _tab_fit_indices(result["fit_df"])
    tidx += 1

    # ── TAB 2: Factor Loadings ────────────────────────────────────────────
    with tabs[tidx]:
        _tab_factor_loadings(result["loadings_df"], result["alpha_level"])
    tidx += 1

    # ── TAB 3: AVE & CR ───────────────────────────────────────────────────
    with tabs[tidx]:
        _tab_ave_cr(result["ave_cr_df"])
    tidx += 1

    # ── TAB 4: Discriminant Validity ──────────────────────────────────────
    with tabs[tidx]:
        _tab_discriminant(result["htmt_df"], result["fl_df"])
    tidx += 1

    # ── TAB 5: Diagram Loading ────────────────────────────────────────────
    with tabs[tidx]:
        _tab_loading_diagram(result["loadings_df"], factor_map)
    tidx += 1

    # ── TAB 6: Parameter Estimates ────────────────────────────────────────
    with tabs[tidx]:
        _tab_param_estimates(result["inspect_df"])
    tidx += 1

    # ── TAB 7 (opsional): Modification Indices ────────────────────────────
    if show_mi and result["mi_df"] is not None and not result["mi_df"].empty:
        with tabs[tidx]:
            _tab_modification_indices(result["mi_df"])
        tidx += 1

    st.markdown("---")

    # ── Export Excel ──────────────────────────────────────────────────────
    _render_export(result)

    # ── AI Interpretasi ───────────────────────────────────────────────────
    if ai_enabled:
        _render_ai_section(result, api_key, ai_provider)


# ─────────────────────────────────────────────────────────────────────────────
# TAB renderers
# ─────────────────────────────────────────────────────────────────────────────

def _tab_fit_indices(fit_df):
    st.markdown("#### Indeks Kecocokan Model (Goodness of Fit)")
    st.markdown("""
    <div class="rs-narasi">
    📖 <b>Interpretasi:</b> Model diterima jika mayoritas indeks memenuhi threshold.
    Prioritaskan CFI ≥ 0.90 dan RMSEA ≤ 0.08 sebagai indeks utama (Hu & Bentler, 1999).
    </div>
    """, unsafe_allow_html=True)

    if fit_df is not None and not fit_df.empty:
        # Styling: warna baris berdasarkan status
        def highlight_status(row):
            color = ""
            s = str(row.get("Status", ""))
            if "✅" in s:
                color = "background-color:#f0f8e8"
            elif "🟡" in s:
                color = "background-color:#fffde7"
            elif "❌" in s:
                color = "background-color:#fdecea"
            return [color] * len(row)

        st.dataframe(
            fit_df.style.apply(highlight_status, axis=1),
            use_container_width=True, hide_index=True,
        )

        n_good  = fit_df["Status"].str.contains("✅").sum() if "Status" in fit_df.columns else 0
        n_total = len(fit_df)
        ratio   = n_good / n_total if n_total > 0 else 0

        if ratio >= 0.75:
            verdict = "✅ Model <b>diterima</b> — mayoritas fit indices terpenuhi."
            color   = GREEN
        elif ratio >= 0.50:
            verdict = "🟡 Model <b>acceptable</b> — sebagian fit indices perlu perbaikan."
            color   = "#a07010"
        else:
            verdict = "❌ Model <b>ditolak</b> — fit tidak memadai. Pertimbangkan respecifikasi."
            color   = RED

        st.markdown(
            f'<div class="rs-narasi" style="border-left-color:{color};">'
            f'📊 <b>Ringkasan Fit:</b> {n_good}/{n_total} indeks memenuhi kriteria.<br/>'
            f'<span style="color:{color};">{verdict}</span><br/>'
            f'<span style="font-size:0.82rem;color:#5f8ab5;">'
            f'Acuan: Hair et al. (2010); Hu & Bentler (1999)</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        st.info("Fit indices tidak dapat dihitung — semopy mungkin tidak mengembalikan stats.")


def _tab_factor_loadings(loadings_df, alpha_level):
    st.markdown("#### Factor Loadings (λ) — Measurement Model")
    st.info(
        f"Acuan: λ ≥ 0.50 = memadai, λ ≥ 0.70 = ideal (Hair et al., 2010). "
        f"Signifikansi pada α = {alpha_level}."
    )

    if loadings_df is not None and not loadings_df.empty:
        def style_loading(val):
            try:
                v = float(val)
                if abs(v) >= 0.70: return "color:#3B6D11; font-weight:700"
                if abs(v) >= 0.50: return "color:#185FA5; font-weight:600"
                return "color:#A32D2D; font-weight:600"
            except Exception:
                return ""

        styled = loadings_df.copy()
        if "Loading (λ)" in styled.columns:
            st.dataframe(
                styled.style.applymap(style_loading, subset=["Loading (λ)"]),
                use_container_width=True, hide_index=True,
            )
        else:
            st.dataframe(loadings_df, use_container_width=True, hide_index=True)

        # Ringkasan per konstruk
        if "Konstruk Laten" in loadings_df.columns and "Loading (λ)" in loadings_df.columns:
            st.markdown("**Ringkasan per Konstruk:**")
            summary_rows = []
            for konstruk, grp in loadings_df.groupby("Konstruk Laten"):
                lvals = pd.to_numeric(grp["Loading (λ)"], errors="coerce").dropna()
                n_ok  = (lvals.abs() >= 0.50).sum()
                summary_rows.append({
                    "Konstruk": konstruk,
                    "N Indikator": len(lvals),
                    "λ Min": round(lvals.min(), 3) if len(lvals) else "–",
                    "λ Max": round(lvals.max(), 3) if len(lvals) else "–",
                    "λ Rata-rata": round(lvals.mean(), 3) if len(lvals) else "–",
                    "Memadai (≥0.50)": f"{n_ok}/{len(lvals)}",
                })
            st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)

        # Warning item lemah
        if "Loading (λ)" in loadings_df.columns:
            weak = loadings_df[
                pd.to_numeric(loadings_df["Loading (λ)"], errors="coerce").abs() < 0.50
            ]
            if not weak.empty:
                items = weak["Indikator"].tolist() if "Indikator" in weak.columns else []
                st.warning(
                    f"⚠️ {len(weak)} indikator memiliki loading < 0.50: "
                    f"**{', '.join(items)}**. "
                    f"Pertimbangkan eliminasi atau respecifikasi."
                )
    else:
        st.info("Factor loadings tidak tersedia dari output semopy.")


def _tab_ave_cr(ave_cr_df):
    st.markdown("#### AVE (Average Variance Extracted) & Composite Reliability (CR)")
    st.markdown("""
    <div class="rs-narasi">
    📖 <b>AVE ≥ 0.50</b> — lebih dari separuh variansi indikator dijelaskan oleh konstruk (Fornell & Larcker, 1981).<br/>
    📖 <b>CR ≥ 0.70</b> — reliabilitas komposit terpenuhi; lebih robust dari Cronbach α karena tidak
    mengasumsikan equal loading (Hair et al., 2010).<br/>
    📖 Jika AVE < 0.50 tapi CR ≥ 0.70, reliabilitas masih dapat diterima secara kondisional.
    </div>
    """, unsafe_allow_html=True)

    if ave_cr_df is not None and not ave_cr_df.empty:
        def style_ave_cr(row):
            styles = [""] * len(row)
            for i, col in enumerate(row.index):
                if col == "AVE":
                    try:
                        styles[i] = (
                            "color:#3B6D11;font-weight:700" if float(row[col]) >= 0.50
                            else "color:#A32D2D;font-weight:700"
                        )
                    except Exception:
                        pass
                elif col == "CR (Composite Rel.)":
                    try:
                        styles[i] = (
                            "color:#3B6D11;font-weight:700" if float(row[col]) >= 0.70
                            else "color:#A32D2D;font-weight:700"
                        )
                    except Exception:
                        pass
            return styles

        st.dataframe(
            ave_cr_df.style.apply(style_ave_cr, axis=1),
            use_container_width=True, hide_index=True,
        )

        n_pass_ave = (pd.to_numeric(ave_cr_df["AVE"], errors="coerce") >= 0.50).sum()
        n_pass_cr  = (pd.to_numeric(ave_cr_df["CR (Composite Rel.)"], errors="coerce") >= 0.70).sum()
        n_total    = len(ave_cr_df)

        st.markdown(
            f'<div class="rs-narasi">'
            f'✅ AVE ≥ 0.50: <b>{n_pass_ave}/{n_total}</b> konstruk &nbsp;|&nbsp; '
            f'✅ CR ≥ 0.70: <b>{n_pass_cr}/{n_total}</b> konstruk'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        st.info("AVE & CR tidak dapat dihitung — periksa apakah loadings tersedia.")


def _tab_discriminant(htmt_df, fl_df):
    st.markdown("#### Discriminant Validity")
    st.markdown("""
    <div class="rs-narasi">
    📖 Discriminant validity mengonfirmasi bahwa setiap konstruk laten berbeda secara statistik
    dari konstruk lainnya — kunci validitas eksternal dalam CFA multi-faktor.<br/><br/>
    <b>Metode 1 — HTMT</b> (Henseler et al., 2015):
    Rata-rata korelasi indikator lintas-konstruk dibagi rata-rata korelasi dalam-konstruk.
    Threshold: HTMT &lt; 0.90 (konservatif: &lt; 0.85).<br/>
    <b>Metode 2 — Fornell-Larcker Criterion</b>: AVE setiap konstruk harus melebihi
    kuadrat korelasi antar-konstruk.
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**HTMT Matrix**")
        if htmt_df is not None and not htmt_df.empty:
            def style_htmt(val):
                try:
                    v = float(val)
                    if v == 1.0 or np.isnan(v):
                        return "color:#888"
                    if v < 0.85: return "color:#3B6D11;font-weight:700"
                    if v < 0.90: return "color:#a07010;font-weight:600"
                    return "color:#A32D2D;font-weight:700"
                except Exception:
                    return ""

            st.dataframe(
                htmt_df.style.applymap(style_htmt),
                use_container_width=True,
            )

            # Cek pelanggaran
            violations = []
            for col in htmt_df.columns:
                for idx in htmt_df.index:
                    if col != idx:
                        try:
                            v = float(htmt_df.loc[idx, col])
                            if v >= 0.90:
                                violations.append(f"{idx}–{col} (HTMT = {v:.3f})")
                        except Exception:
                            pass

            if violations:
                st.error(f"❌ Discriminant validity **tidak terpenuhi** pada: {', '.join(violations)}")
            else:
                st.success("✅ Semua pasangan konstruk memenuhi HTMT < 0.90")
        else:
            st.info(
                "HTMT memerlukan ≥ 2 konstruk. "
                "Untuk model 1-faktor, discriminant validity tidak berlaku."
            )

    with col2:
        st.markdown("**Fornell-Larcker Criterion**")
        if fl_df is not None and not fl_df.empty:
            def style_fl(val):
                try:
                    v = float(val)
                    if isinstance(val, str) and "√" in str(val): return ""
                    return "color:#3B6D11;font-weight:600" if v < 1.0 else ""
                except Exception:
                    return ""

            st.dataframe(fl_df, use_container_width=True)
            st.caption(
                "Diagonal = √AVE. Off-diagonal = korelasi antar-konstruk. "
                "√AVE harus > semua korelasi di baris/kolomnya."
            )
        else:
            st.info("Fornell-Larcker memerlukan ≥ 2 konstruk dengan AVE tersedia.")


def _tab_loading_diagram(loadings_df, factor_map):
    st.markdown("#### Diagram Factor Loadings")

    if loadings_df is None or loadings_df.empty:
        st.info("Data loadings tidak tersedia untuk diagram.")
        return

    if "Konstruk Laten" not in loadings_df.columns or "Loading (λ)" not in loadings_df.columns:
        st.info("Kolom 'Konstruk Laten' atau 'Loading (λ)' tidak ditemukan.")
        return

    konstruk_list = list(factor_map.keys())
    colors_palette = [
        BLUE, GREEN, "#8B2FC9", "#D4621B", "#0e7490",
        "#7c3aed", "#b45309", "#0f766e", "#b91c1c", "#1d4ed8",
    ]

    # Bar chart loading per konstruk (subplots)
    n_cols = min(2, len(konstruk_list))
    n_rows = (len(konstruk_list) + n_cols - 1) // n_cols

    from plotly.subplots import make_subplots
    fig = make_subplots(
        rows=n_rows, cols=n_cols,
        subplot_titles=konstruk_list,
        vertical_spacing=0.15,
    )

    for ki, konstruk in enumerate(konstruk_list):
        row = ki // n_cols + 1
        col = ki % n_cols + 1
        color = colors_palette[ki % len(colors_palette)]

        sub = loadings_df[loadings_df["Konstruk Laten"].astype(str).str.strip() == konstruk]
        if sub.empty:
            continue

        lvals = pd.to_numeric(sub["Loading (λ)"], errors="coerce")
        indics = sub["Indikator"].tolist() if "Indikator" in sub.columns else [f"I{j}" for j in range(len(sub))]

        bar_colors = [
            GREEN if abs(v) >= 0.70 else BLUE if abs(v) >= 0.50 else RED2
            for v in lvals.fillna(0)
        ]

        fig.add_trace(
            go.Bar(
                x=indics, y=lvals.round(3).tolist(),
                marker_color=bar_colors,
                text=[f"{v:.3f}" for v in lvals.round(3).fillna(0)],
                textposition="outside",
                name=konstruk, showlegend=False,
            ),
            row=row, col=col,
        )
        fig.add_hline(y=0.50, line_dash="dash", line_color=NAVY, line_width=1,
                      annotation_text="0.50", row=row, col=col)
        fig.add_hline(y=0.70, line_dash="dot", line_color=GREEN, line_width=1,
                      annotation_text="0.70", row=row, col=col)

    fig.update_layout(
        title="Factor Loadings per Konstruk",
        template="plotly_white",
        height=320 * n_rows,
        margin=dict(l=30, r=30, t=60, b=30),
    )
    fig.update_yaxes(range=[0, 1.15])
    st.plotly_chart(fig, use_container_width=True)

    # Legend warna
    st.markdown(
        '<div style="font-size:0.82rem;color:#444;margin-top:0.3rem;">'
        f'<span style="color:{GREEN};font-weight:700;">■</span> λ ≥ 0.70 (Ideal) &nbsp;'
        f'<span style="color:{BLUE};font-weight:700;">■</span> 0.50 ≤ λ < 0.70 (Memadai) &nbsp;'
        f'<span style="color:{RED2};font-weight:700;">■</span> λ < 0.50 (Perlu Ditinjau)'
        '</div>',
        unsafe_allow_html=True,
    )


def _tab_param_estimates(inspect_df):
    st.markdown("#### Parameter Estimates Lengkap")
    st.caption("Seluruh parameter yang diestimasi semopy termasuk kovarians antar-konstruk dan varians residual.")

    if inspect_df is not None and not inspect_df.empty:
        styled = inspect_df.copy()
        # Tambah kolom signifikansi jika ada p-value
        for col in styled.columns:
            if col.lower() in ("p-value", "pvalue", "p_value"):
                styled["Sig."] = styled[col].apply(
                    lambda p: "***" if (isinstance(p, (int, float)) and not np.isnan(float(p)) and p < 0.001)
                    else "**" if (isinstance(p, (int, float)) and not np.isnan(float(p)) and p < 0.01)
                    else "*" if (isinstance(p, (int, float)) and not np.isnan(float(p)) and p < 0.05)
                    else "–"
                )
                break
        st.dataframe(styled, use_container_width=True, hide_index=True)
    else:
        st.info("Parameter estimates tidak tersedia.")


def _tab_modification_indices(mi_df):
    st.markdown("#### Modification Indices (MI)")
    st.markdown("""
    <div class="rs-narasi">
    📖 MI mengestimasi penurunan χ² jika parameter tambahan dibebaskan.
    MI > 10 umumnya layak dipertimbangkan, tetapi modifikasi harus didukung teori —
    jangan modifikasi hanya berdasarkan angka (MacCallum et al., 1992).
    </div>
    """, unsafe_allow_html=True)

    if mi_df is not None and not mi_df.empty:
        mi_sorted = mi_df.sort_values(
            mi_df.columns[-1], ascending=False
        ).head(20).reset_index(drop=True)
        st.dataframe(mi_sorted, use_container_width=True, hide_index=True)

        high_mi = mi_sorted[
            pd.to_numeric(mi_sorted.iloc[:, -1], errors="coerce") > 10
        ]
        if not high_mi.empty:
            st.warning(
                f"⚠️ {len(high_mi)} pasang parameter memiliki MI > 10. "
                f"Pertimbangkan kovarians residual atau relokasi indikator jika didukung teori."
            )
    else:
        st.info("Modification indices tidak tersedia dari output semopy.")


# ─────────────────────────────────────────────────────────────────────────────
# Export Excel
# ─────────────────────────────────────────────────────────────────────────────

def _render_export(result):
    st.markdown("### ⬇️ Export Hasil CFA")

    col_e1, col_e2 = st.columns(2)

    with col_e1:
        # Export Excel lengkap
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            if result["fit_df"] is not None and not result["fit_df"].empty:
                result["fit_df"].to_excel(writer, sheet_name="Fit_Indices", index=False)
            if result["loadings_df"] is not None and not result["loadings_df"].empty:
                result["loadings_df"].to_excel(writer, sheet_name="Factor_Loadings", index=False)
            if result["ave_cr_df"] is not None and not result["ave_cr_df"].empty:
                result["ave_cr_df"].to_excel(writer, sheet_name="AVE_CR", index=False)
            if result["htmt_df"] is not None and not result["htmt_df"].empty:
                result["htmt_df"].to_excel(writer, sheet_name="HTMT_Matrix")
            if result["fl_df"] is not None and not result["fl_df"].empty:
                result["fl_df"].to_excel(writer, sheet_name="Fornell_Larcker")
            if result["inspect_df"] is not None and not result["inspect_df"].empty:
                result["inspect_df"].to_excel(writer, sheet_name="Parameter_Estimates", index=False)
            if result["mi_df"] is not None and not result["mi_df"].empty:
                result["mi_df"].to_excel(writer, sheet_name="Modification_Indices", index=False)
            pd.DataFrame({"Model Syntax": result["model_syntax"].split("\n")}).to_excel(
                writer, sheet_name="Model_Syntax", index=False
            )
        buf.seek(0)
        st.download_button(
            "📥 Export Lengkap (.xlsx)",
            data=buf,
            file_name="cfa_results.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    with col_e2:
        # Export teks laporan ringkas
        report_text = _generate_text_report(result)
        st.download_button(
            "📄 Export Teks Laporan (.txt)",
            data=report_text,
            file_name="cfa_laporan.txt",
            mime="text/plain",
            use_container_width=True,
        )


def _generate_text_report(result) -> str:
    """Hasilkan teks laporan CFA siap tempel ke skripsi/jurnal."""
    lines = [
        "=" * 70,
        "LAPORAN CONFIRMATORY FACTOR ANALYSIS (CFA)",
        "Ruang Statistika v4.2",
        "=" * 70,
        "",
        f"Model Syntax:\n{result['model_syntax']}",
        f"\nN Observasi: {result['n_obs']}",
        "",
    ]

    # Fit Indices
    lines.append("── FIT INDICES ──")
    if result["fit_df"] is not None and not result["fit_df"].empty:
        lines.append(result["fit_df"].to_string(index=False))
    lines.append("")

    # Factor Loadings
    lines.append("── FACTOR LOADINGS ──")
    if result["loadings_df"] is not None and not result["loadings_df"].empty:
        lines.append(result["loadings_df"].to_string(index=False))
    lines.append("")

    # AVE & CR
    lines.append("── AVE & COMPOSITE RELIABILITY ──")
    if result["ave_cr_df"] is not None and not result["ave_cr_df"].empty:
        lines.append(result["ave_cr_df"].to_string(index=False))
    lines.append("")

    # HTMT
    lines.append("── HTMT MATRIX ──")
    if result["htmt_df"] is not None and not result["htmt_df"].empty:
        lines.append(result["htmt_df"].to_string())
    lines.append("")

    lines += [
        "── REFERENSI ──",
        "Hair, J. F., Black, W. C., Babin, B. J., & Anderson, R. E. (2010).",
        "  Multivariate Data Analysis (7th ed.). Pearson.",
        "Fornell, C., & Larcker, D. F. (1981). Evaluating structural equation models",
        "  with unobservable variables and measurement error. JMR, 18(1), 39–50.",
        "Henseler, J., Ringle, C. M., & Sarstedt, M. (2015). A new criterion for",
        "  assessing discriminant validity in variance-based SEM. JAMS, 43(1), 115–135.",
        "Hu, L., & Bentler, P. M. (1999). Cutoff criteria for fit indexes in covariance",
        "  structure analysis. SEM, 6(1), 1–55.",
    ]

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# AI Interpretasi
# ─────────────────────────────────────────────────────────────────────────────

def _render_ai_section(result, api_key, ai_provider):
    st.markdown("### 🤖 Interpretasi AI")

    if st.button("🤖 Generate Interpretasi CFA dengan AI", type="secondary"):
        prompt = _build_ai_prompt(result)
        with st.spinner("🤖 AI menyusun interpretasi akademis…"):
            ai_text = call_ai_api(prompt, api_key, ai_provider)

        if "ai_cache" not in st.session_state:
            st.session_state.ai_cache = {}
        st.session_state.ai_cache["cfa"] = ai_text
        st.rerun()

    cached = ss_get("ai_cache", {}).get("cfa")
    if cached:
        st.markdown(
            f'<div class="rs-ai-narasi">'
            f'<span class="rs-ai-badge">✨ AI — {ai_provider.split("(")[0].strip()}</span><br/>'
            f'{cached.replace(chr(10), "<br/>")}'
            f"</div>",
            unsafe_allow_html=True,
        )


def _build_ai_prompt(result) -> str:
    """Susun prompt AI dari seluruh hasil CFA."""
    sections = [
        "Anda adalah Peneliti Senior dan Statistikawan. Tulis interpretasi akademis "
        "Confirmatory Factor Analysis (CFA) berikut dalam Bahasa Indonesia yang formal, "
        "mengalir, dan siap digunakan dalam skripsi/jurnal. "
        "Sertakan evaluasi fit indices, validitas konvergen (AVE), reliabilitas komposit (CR), "
        "dan discriminant validity (HTMT). Berikan rekomendasi jika ada yang perlu diperbaiki. "
        "Format: paragraf mengalir (bukan bullet), 3-4 paragraf.\n\n",
        f"=== Model Syntax ===\n{result['model_syntax']}\nN = {result['n_obs']}\n",
    ]

    if result["fit_df"] is not None and not result["fit_df"].empty:
        sections.append(f"\n=== Fit Indices ===\n{result['fit_df'].to_string(index=False)}")

    if result["loadings_df"] is not None and not result["loadings_df"].empty:
        sections.append(f"\n=== Factor Loadings ===\n{result['loadings_df'].to_string(index=False)}")

    if result["ave_cr_df"] is not None and not result["ave_cr_df"].empty:
        sections.append(f"\n=== AVE & CR ===\n{result['ave_cr_df'].to_string(index=False)}")

    if result["htmt_df"] is not None and not result["htmt_df"].empty:
        sections.append(f"\n=== HTMT Matrix ===\n{result['htmt_df'].to_string()}")

    if result["fl_df"] is not None and not result["fl_df"].empty:
        sections.append(f"\n=== Fornell-Larcker ===\n{result['fl_df'].to_string()}")

    return "\n".join(sections)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers: kalkulasi metrik
# ─────────────────────────────────────────────────────────────────────────────

def _extract_loadings(inspect_df: pd.DataFrame, alpha_level: float) -> pd.DataFrame | None:
    """Ekstrak factor loadings (baris bertipe =~) dari inspect_df semopy."""
    if inspect_df is None or inspect_df.empty:
        return None

    op_col = next((c for c in inspect_df.columns if c.lower() in ("op", "operator", "rel", "relation")), None)

    if op_col:
        sub = inspect_df[inspect_df[op_col] == "=~"].copy()
    else:
        mask = inspect_df.astype(str).apply(lambda row: row.str.contains("=~").any(), axis=1)
        sub  = inspect_df[mask].copy()

    if sub.empty:
        return None

    # Rename kolom
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
            col_map[c] = "z / t"
        elif cl in ("p-value", "pvalue", "p_value", "pr(>|z|)"):
            col_map[c] = "p-value"

    sub = sub.rename(columns=col_map)

    if "p-value" in sub.columns:
        sub["Signifikan"] = sub["p-value"].apply(
            lambda p: "✓" if (isinstance(p, (int, float)) and not np.isnan(float(p)) and float(p) < alpha_level)
            else "–"
        )

    if "Loading (λ)" in sub.columns:
        sub["Kecukupan"] = sub["Loading (λ)"].apply(
            lambda l: (
                "✅ Ideal (≥0.70)" if (isinstance(l, (int, float)) and abs(float(l)) >= 0.70)
                else "🟡 Memadai (≥0.50)" if (isinstance(l, (int, float)) and abs(float(l)) >= 0.50)
                else "❌ Rendah (<0.50)"
            ) if isinstance(l, (int, float)) else "–"
        )

    return sub.reset_index(drop=True)


def _calc_ave_cr(loadings_df: pd.DataFrame | None, factor_map: dict) -> pd.DataFrame | None:
    """Hitung AVE dan Composite Reliability dari loadings."""
    if loadings_df is None or "Loading (λ)" not in loadings_df.columns:
        return None
    if "Konstruk Laten" not in loadings_df.columns:
        return None

    rows = []
    for construct, indicators in factor_map.items():
        mask    = loadings_df["Konstruk Laten"].astype(str).str.strip() == construct
        sub     = loadings_df[mask]
        lambdas = pd.to_numeric(sub["Loading (λ)"], errors="coerce").dropna().tolist()

        if len(lambdas) < 2:
            continue

        l_sq   = [l ** 2 for l in lambdas]
        err    = [1 - l2 for l2 in l_sq]
        sum_lsq = sum(l_sq)
        sum_err = sum(err)
        ave     = sum_lsq / (sum_lsq + sum_err) if (sum_lsq + sum_err) > 0 else None
        sum_l   = sum(lambdas)
        cr_val  = (sum_l ** 2) / (sum_l ** 2 + sum_err) if (sum_l ** 2 + sum_err) > 0 else None

        # MaxR(H) — reliability yang paling konservatif
        maxrh = sum_lsq / (sum_lsq + min(err)) if min(err, default=None) is not None else None

        rows.append({
            "Konstruk":            construct,
            "N Indikator":         len(lambdas),
            "AVE":                 round(ave, 4) if ave is not None else "N/A",
            "CR (Composite Rel.)": round(cr_val, 4) if cr_val is not None else "N/A",
            "AVE Status":          ("✅ ≥ 0.50" if ave and ave >= 0.50 else "❌ < 0.50")
                                   if ave is not None else "–",
            "CR Status":           ("✅ ≥ 0.70" if cr_val and cr_val >= 0.70 else "❌ < 0.70")
                                   if cr_val is not None else "–",
            "MaxR(H)":             round(maxrh, 4) if maxrh is not None else "N/A",
        })

    return pd.DataFrame(rows) if rows else None


def _calc_htmt(data: pd.DataFrame, factor_map: dict,
               loadings_df: pd.DataFrame | None) -> pd.DataFrame | None:
    """
    Hitung HTMT (Heterotrait-Monotrait Ratio of Correlations).
    HTMT_{jk} = mean_HT(j,k) / sqrt(mean_MT(j) * mean_MT(k))
    """
    constructs = list(factor_map.keys())
    if len(constructs) < 2:
        return None

    n = len(constructs)
    mat = np.ones((n, n))
    corr = data.corr()

    for i in range(n):
        for j in range(i + 1, n):
            inds_i = [ind for ind in factor_map[constructs[i]] if ind in corr.columns]
            inds_j = [ind for ind in factor_map[constructs[j]] if ind in corr.columns]

            if not inds_i or not inds_j:
                mat[i, j] = mat[j, i] = np.nan
                continue

            # Hetero-trait (cross-construct) correlations
            ht_vals = []
            for a in inds_i:
                for b in inds_j:
                    if a != b:
                        ht_vals.append(abs(corr.loc[a, b]))

            # Mono-trait (within-construct) correlations
            mt_i = [abs(corr.loc[a, b]) for k, a in enumerate(inds_i)
                    for b in inds_i[k + 1:] if a != b]
            mt_j = [abs(corr.loc[a, b]) for k, a in enumerate(inds_j)
                    for b in inds_j[k + 1:] if a != b]

            if not ht_vals:
                mat[i, j] = mat[j, i] = np.nan
                continue

            mean_ht = np.mean(ht_vals)
            mean_mt_i = np.mean(mt_i) if mt_i else 1.0
            mean_mt_j = np.mean(mt_j) if mt_j else 1.0

            denom = np.sqrt(mean_mt_i * mean_mt_j)
            htmt_val = mean_ht / denom if denom > 0 else np.nan
            mat[i, j] = mat[j, i] = round(htmt_val, 4)

    df_htmt = pd.DataFrame(mat, index=constructs, columns=constructs)
    # Format diagonal sebagai "-"
    for c in constructs:
        df_htmt.loc[c, c] = "–"

    return df_htmt


def _calc_fornell_larcker(ave_cr_df: pd.DataFrame | None,
                           data: pd.DataFrame,
                           factor_map: dict,
                           loadings_df: pd.DataFrame | None) -> pd.DataFrame | None:
    """
    Fornell-Larcker Criterion:
    Diagonal = √AVE. Off-diagonal = korelasi antar-konstruk (skor komposit).
    √AVE harus > semua korelasi di baris/kolomnya.
    """
    if ave_cr_df is None or ave_cr_df.empty:
        return None

    constructs = ave_cr_df["Konstruk"].tolist()
    if len(constructs) < 2:
        return None

    # Hitung skor komposit (rata-rata indikator per konstruk)
    composite_scores = {}
    for construct in constructs:
        inds = [ind for ind in factor_map.get(construct, []) if ind in data.columns]
        if inds:
            composite_scores[construct] = data[inds].mean(axis=1)

    if len(composite_scores) < 2:
        return None

    score_df = pd.DataFrame(composite_scores)
    corr_mat = score_df.corr()

    # Ambil √AVE per konstruk
    sqrt_ave = {}
    for _, row in ave_cr_df.iterrows():
        try:
            sqrt_ave[row["Konstruk"]] = round(float(row["AVE"]) ** 0.5, 4)
        except Exception:
            sqrt_ave[row["Konstruk"]] = np.nan

    # Bangun matrix Fornell-Larcker
    n = len(constructs)
    mat = pd.DataFrame(index=constructs, columns=constructs, dtype=object)
    for i, ci in enumerate(constructs):
        for j, cj in enumerate(constructs):
            if i == j:
                mat.loc[ci, cj] = f"√AVE = {sqrt_ave.get(ci, '–')}"
            else:
                try:
                    corr_val = round(float(corr_mat.loc[ci, cj]), 4)
                    status = "✅" if sqrt_ave.get(ci, 0) > abs(corr_val) else "❌"
                    mat.loc[ci, cj] = f"{corr_val} {status}"
                except Exception:
                    mat.loc[ci, cj] = "N/A"

    return mat


def _calc_modification_indices(sem_model) -> pd.DataFrame | None:
    """Coba ambil modification indices dari semopy."""
    try:
        from semopy.stats import calc_stats
        mi = sem_model.inspect(mode="mi")
        if mi is not None and not mi.empty:
            return mi.reset_index(drop=True)
    except Exception:
        pass
    try:
        mi = sem_model.inspect(what="mi")
        if mi is not None and not mi.empty:
            return mi.reset_index(drop=True)
    except Exception:
        pass
    return None


def _calc_fit_indices(sem_model) -> pd.DataFrame:
    """Hitung dan format fit indices dari semopy model — versi diperluas."""
    try:
        from semopy.stats import calc_stats
        fit_stats = calc_stats(sem_model)
    except Exception:
        try:
            fit_stats = sem_model.calc_stats() if hasattr(sem_model, "calc_stats") else {}
        except Exception:
            fit_stats = {}

    def _v(key_variants):
        for k in key_variants:
            v = fit_stats.get(k)
            if v is not None:
                try: return float(v)
                except Exception: pass
        return None

    def _fmt(v):
        return "N/A" if v is None else str(round(v, 4))

    def _status_ge(v, good, acc):
        if v is None: return "–"
        if v >= good: return "✅ Good"
        if v >= acc:  return "🟡 Acceptable"
        return "❌ Poor"

    def _status_le(v, good, acc):
        if v is None: return "–"
        if v <= good: return "✅ Good"
        if v <= acc:  return "🟡 Acceptable"
        return "❌ Poor"

    cfi   = _v(["CFI", "cfi"])
    tli   = _v(["TLI", "tli", "NNFI", "nnfi"])
    rmsea = _v(["RMSEA", "rmsea"])
    srmr  = _v(["SRMR", "srmr"])
    gfi   = _v(["GFI", "gfi"])
    nfi   = _v(["NFI", "nfi"])
    ifi   = _v(["IFI", "ifi"])
    chi2  = _v(["chi2", "Chi2", "chi_2", "chisq", "Chi"])
    dof   = _v(["dof", "df", "DOF"])
    aic   = _v(["AIC", "aic"])
    bic   = _v(["BIC", "bic"])

    chi2_df = (chi2 / dof) if (chi2 is not None and dof is not None and dof > 0) else None

    rows = [
        {"Indeks": "CFI (Comparative Fit Index)",   "Nilai": _fmt(cfi),      "Kriteria": "≥ 0.90 (good: ≥ 0.95)", "Status": _status_ge(cfi, 0.95, 0.90)},
        {"Indeks": "TLI / NNFI",                    "Nilai": _fmt(tli),      "Kriteria": "≥ 0.90 (good: ≥ 0.95)", "Status": _status_ge(tli, 0.95, 0.90)},
        {"Indeks": "RMSEA",                         "Nilai": _fmt(rmsea),    "Kriteria": "≤ 0.08 (good: ≤ 0.05)", "Status": _status_le(rmsea, 0.05, 0.08)},
        {"Indeks": "SRMR",                          "Nilai": _fmt(srmr),     "Kriteria": "≤ 0.08 (good: ≤ 0.05)", "Status": _status_le(srmr, 0.05, 0.08)},
        {"Indeks": "GFI (Goodness of Fit Index)",   "Nilai": _fmt(gfi),      "Kriteria": "≥ 0.90",                "Status": _status_ge(gfi, 0.95, 0.90)},
        {"Indeks": "NFI (Normed Fit Index)",        "Nilai": _fmt(nfi),      "Kriteria": "≥ 0.90",                "Status": _status_ge(nfi, 0.95, 0.90)},
        {"Indeks": "IFI (Incremental Fit Index)",   "Nilai": _fmt(ifi),      "Kriteria": "≥ 0.90",                "Status": _status_ge(ifi, 0.95, 0.90)},
        {"Indeks": "χ²/df (CMIN/DF)",              "Nilai": _fmt(chi2_df),  "Kriteria": "≤ 3.0 (good: ≤ 2.0)",  "Status": _status_le(chi2_df, 2.0, 3.0)},
        {"Indeks": "χ² (Chi-Square)",              "Nilai": _fmt(chi2),     "Kriteria": "p > 0.05 (sensitif N)", "Status": "–"},
        {"Indeks": "df (Degrees of Freedom)",       "Nilai": _fmt(dof),      "Kriteria": "–",                     "Status": "–"},
        {"Indeks": "AIC (Akaike Info Criterion)",   "Nilai": _fmt(aic),      "Kriteria": "Lebih kecil = lebih baik", "Status": "–"},
        {"Indeks": "BIC (Bayesian Info Criterion)", "Nilai": _fmt(bic),      "Kriteria": "Lebih kecil = lebih baik", "Status": "–"},
    ]

    # Hapus baris yang semuanya N/A dan tidak memberikan info
    rows = [r for r in rows if r["Nilai"] != "N/A" or r["Status"] != "–"]
    return pd.DataFrame(rows)
