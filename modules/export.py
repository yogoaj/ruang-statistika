"""
modules/export.py — Generate Laporan Pro
Ruang Statistika v4.0

Perbaikan v4.1:
- Setiap modul analisis kini menghasilkan AI interpretasi lengkap
  (tabel + grafik + persamaan model + narasi akademis)
- Tambah generate model equation per modul via ai_generate_model_equation()
- Konsistensi ai_texts keys dengan docx_helpers.py
- Perbaikan progress bar dan status message
- Auto-generate AI interpretasi bahkan dari cache sesi sebelumnya

# ═══════════════════════════════════════════════════════════════════════════════
# RINGKASAN PERUBAHAN v4.2
# ═══════════════════════════════════════════════════════════════════════════════
#
# File yang diubah          Baris yang berubah    Keterangan
# ──────────────────────── ──────────────────── ─────────────────────────────────
# utils/auth.py             Tambah ~60 baris     Fungsi quota (check/consume/get)
# modules/export.py         ~1109–1131            Guard diganti (quota + free mode)
#                           ~2118 & ~2141         Konsumsi quota setelah sukses
# modules/regresi.py        Seluruh file          Guard soft, Pro block di bawah
# modules/anova.py          Seluruh file          Guard soft, Pro block di bawah
# modules/logistik.py       Seluruh file          Guard soft, Pro block di bawah
#
# File yang TIDAK berubah
# ──────────────────────────────────────────────────────────────────────────────
# app.py, utils/ai_helpers.py, utils/docx_helpers.py, utils/stats_helpers.py,
# utils/plot_helpers.py, utils/effect_size.py, semua modul lain
# ═══════════════════════════════════════════════════════════════════════════════

"""
from __future__ import annotations

import io
import json
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from utils.auth import require_pro, check_daily_export_quota, consume_export_quota, get_quota_remaining
from utils.stats_helpers import (
    require_data, require_cols, ss_get,
    descriptive_stats, normality_test,
    pearson_validity, calc_cronbach,
)
from utils.ai_helpers import (
    ai_interpret_descriptive,
    ai_interpret_validity_reliability,
    ai_interpret_correlation,
    ai_generate_kesimpulan,
    ai_generate_model_equation,
    ai_raw_interpret,
    ai_interpret_heatmap,
    ai_interpret_scatter,
    ai_interpret_compute,
    # Patch v4.2 — Regresi Robust & WLS
    ai_interpret_robust,
    ai_interpret_wls_robust,
    ai_interpret_model_comparison,
)
from utils.docx_helpers import generate_pro_docx, generate_markdown_report


def _first_valid_df(*candidates):
    """Kembalikan DataFrame/nilai pertama yang tidak None dan tidak kosong.
    Aman digunakan sebagai pengganti `a or b` ketika salah satu bisa berupa DataFrame."""
    for c in candidates:
        if c is None:
            continue
        try:
            if not c.empty:
                return c
        except AttributeError:
            if c:
                return c
    return None



# ─────────────────────────────────────────────────────────────────────────────
# Helper: Plotly figure → PNG bytes
# ─────────────────────────────────────────────────────────────────────────────

def fig_to_png_bytes(fig: go.Figure, width: int = 800, height: int = 400) -> bytes | None:
    try:
        return fig.to_image(format="png", width=width, height=height, scale=2)
    except Exception:
        try:
            import plotly.io as pio
            return pio.to_image(fig, format="png", width=width, height=height)
        except Exception:
            return None


# ─────────────────────────────────────────────────────────────────────────────
# Helper: Normalisasi data modul dari session_state
# ─────────────────────────────────────────────────────────────────────────────

def _normalize_mod_data(mod_key: str, raw: dict) -> dict:
    if not isinstance(raw, dict):
        return {}

    out = dict(raw)

    if mod_key == "ols_plus":
        model = raw.get("model")
        if model is not None and raw.get("coef_table") is None:
            try:
                out["coef_table"] = pd.DataFrame({
                    "Parameter":     model.params.index.tolist(),
                    "β (Koefisien)": model.params.values.round(4).tolist(),
                    "Std. Error":    model.bse.values.round(4).tolist(),
                    "t-hitung":      model.tvalues.values.round(4).tolist(),
                    "p-value":       model.pvalues.values.round(4).tolist(),
                    "Signifikan":    ["✓" if p < 0.05 else "✗" for p in model.pvalues],
                })
                out["r2"]       = float(model.rsquared)
                out["adj_r2"]   = float(model.rsquared_adj)
                out["f_pvalue"] = float(model.f_pvalue)
                out["y_actual"] = model.model.endog.tolist()
                out["y_pred"]   = model.fittedvalues.tolist()
                out["residuals"]= model.resid.tolist()
            except Exception:
                pass
        vif_df = raw.get("vif")
        if vif_df is not None and not raw.get("vif_max"):
            try:
                out["vif_max"] = float(vif_df["VIF"].max())
            except Exception:
                pass
        try:
            from statsmodels.stats.stattools import durbin_watson
            model = raw.get("model")
            if model is not None and not raw.get("durbin_watson"):
                out["durbin_watson"] = float(durbin_watson(model.resid))
        except Exception:
            pass

    elif mod_key == "mediasi":
        med_info = raw.get("med_info", {})
        boot     = raw.get("boot", {})
        if med_info and not raw.get("path_table"):
            try:
                x = raw.get("x", "X")
                m = raw.get("m", "M")
                y = raw.get("y", "Y")
                out["path_table"] = pd.DataFrame([
                    {"Jalur": "a (X→M)",       "Koefisien": med_info.get("a (X→M)"),
                     "Keterangan": f"{x} → {m}"},
                    {"Jalur": "b (M→Y|X)",     "Koefisien": med_info.get("b (M→Y|X)"),
                     "Keterangan": f"{m} → {y}"},
                    {"Jalur": "c (Total)",      "Koefisien": med_info.get("c (total X→Y)"),
                     "Keterangan": f"{x} → {y} total"},
                    {"Jalur": "c' (Langsung)", "Koefisien": med_info.get("c' (direct X→Y)"),
                     "Keterangan": f"{x} → {y} langsung"},
                ])
                if med_info.get("Indirect (a×b)") is not None:
                    out["indirect_effect"] = float(med_info["Indirect (a×b)"])
                if med_info.get("c' (direct X→Y)") is not None:
                    out["direct_effect"] = float(med_info["c' (direct X→Y)"])
                if med_info.get("c (total X→Y)") is not None:
                    out["total_effect"] = float(med_info["c (total X→Y)"])
            except Exception:
                pass
        if boot and not raw.get("bootstrap_ci"):
            lo = boot.get("ci_lower")
            hi = boot.get("ci_upper")
            if lo is not None and hi is not None:
                out["bootstrap_ci"] = [float(lo), float(hi)]

    elif mod_key == "moderasi":
        model = raw.get("model")
        if model is not None and not raw.get("coef_table"):
            try:
                x = raw.get("x", "X")
                z = raw.get("z", "Z")
                b0 = raw.get("b0", 0)
                b1 = raw.get("b1", 0)
                b2 = raw.get("b2", 0)
                b3 = raw.get("b3", 0)
                pvals = model.pvalues
                out["coef_table"] = pd.DataFrame({
                    "Parameter":  ["Konstanta", x, z, f"{x} × {z}"],
                    "β":          [round(b0, 4), round(b1, 4), round(b2, 4), round(b3, 4)],
                    "SE":         model.bse.round(4).tolist(),
                    "t":          model.tvalues.round(4).tolist(),
                    "p-value":    pvals.round(4).tolist(),
                    "Signifikan": ["✓" if p < 0.05 else "✗" for p in pvals],
                })
                out["r2"]     = float(model.rsquared)
                out["adj_r2"] = float(model.rsquared_adj)
                if abs(b3) > 1e-10:
                    out["johnson_neyman"] = float(-b1 / b3)
            except Exception:
                pass

    elif mod_key == "logistik":
        odds_df = raw.get("odds_df")
        coef_table = raw.get("coef_table")
        coef_table_missing = coef_table is None or (hasattr(coef_table, "empty") and coef_table.empty)
        if odds_df is not None and coef_table_missing:
            out["coef_table"] = odds_df
        for alias in ("auc", "pseudo_r2", "aic", "bic"):
            if raw.get(alias) is not None:
                out[alias] = raw[alias]
        if raw.get("fpr") is not None and raw.get("tpr") is not None:
            out["roc"] = {
                "fpr": list(raw["fpr"]),
                "tpr": list(raw["tpr"]),
                "auc": raw.get("auc"),
            }
        # Sertakan classification report
        if raw.get("cr") is not None:
            out["cr"] = raw["cr"]

    elif mod_key == "uji_beda":
        for field in ("uji_type", "num_col", "g1_name", "g2_name",
                      "g1_mean", "g2_mean", "statistic", "p_value",
                      "effect_size", "signifikan", "alpha"):
            if raw.get(field) is not None and out.get(field) is None:
                out[field] = raw[field]

    elif mod_key == "outlier":
        for field in ("variabel", "method", "n_total", "total_outliers", "pct_outliers"):
            if raw.get(field) is not None and out.get(field) is None:
                out[field] = raw[field]

    elif mod_key == "kelompok":
        for field in ("cat", "num", "best_group", "worst_group",
                      "f_stat", "p_value", "signifikan", "alpha"):
            if raw.get(field) is not None and out.get(field) is None:
                out[field] = raw[field]

    elif mod_key == "anova":
        pass  # sudah lengkap dari anova.py patch

    elif mod_key == "efa":
        # efa_session sudah flat dict dari efa.py, normalisasi minimal
        # Bridging efa_ai_text -> ai_text agar renderer bisa pakai
        if not raw.get("ai_text"):
            ai_t = st.session_state.get("efa_ai_text", "")
            if ai_t:
                out["ai_text"] = ai_t
        for field in ("kmo", "kmo_label", "bartlett_p", "n_factors",
                      "rotation", "total_var", "loading_df", "variance_df", "ai_text"):
            if raw.get(field) is not None and out.get(field) is None:
                out[field] = raw[field]

    elif mod_key == "reliabilitas_icc":
        # Pastikan icc_df tersimpan sebagai list of dict (agar bisa di-DataFrame)
        icc_df = raw.get("icc_df")
        if icc_df is not None:
            try:
                if hasattr(icc_df, "to_dict"):
                    out["icc_df"] = icc_df.to_dict("records")
                elif isinstance(icc_df, list):
                    out["icc_df"] = icc_df
            except Exception:
                pass
        anova_tbl = raw.get("anova_tbl")
        if anova_tbl is not None:
            try:
                if hasattr(anova_tbl, "to_dict"):
                    out["anova_tbl"] = anova_tbl.to_dict("records")
                elif isinstance(anova_tbl, list):
                    out["anova_tbl"] = anova_tbl
            except Exception:
                pass
        for field in ("n_subj", "n_rater", "use_type", "rec_model",
                      "rater_names", "ai_text"):
            if raw.get(field) is not None and out.get(field) is None:
                out[field] = raw[field]

    elif mod_key == "uji_asumsi":
        # rekomendasi bisa berupa dict dari _build_rekomendasi_dict()
        rec = raw.get("rekomendasi")
        if rec is not None:
            out["rekomendasi"] = rec
        for field in ("n_var", "alpha", "ai_text"):
            if raw.get(field) is not None and out.get(field) is None:
                out[field] = raw[field]

    elif mod_key in ("ols_robust", "ols_wls", "ols_robust_comparison"):
        # Normalisasi coef_df dari statsmodels jika belum DataFrame biasa
        coef_df = raw.get("coef_df")
        if coef_df is not None and hasattr(coef_df, "to_dict"):
            try:
                out["coef_df"] = coef_df.reset_index(drop=True)
            except Exception:
                pass
        comp_df = raw.get("comparison_df")
        if comp_df is not None and hasattr(comp_df, "to_dict"):
            try:
                out["comparison_df"] = comp_df.reset_index(drop=True)
            except Exception:
                pass
        for field in ("dep_var", "ind_vars", "estimator", "n_obs",
                      "n_low_weight", "n_changed", "best_model",
                      "ols_rmse", "rlm_rmse", "wls_rmse",
                      "ols_glejser_p", "wls_glejser_p", "weight_method",
                      "r2", "adj_r2", "ai_text"):
            if raw.get(field) is not None and out.get(field) is None:
                out[field] = raw[field]

    elif mod_key == "compute":
        # compute_log bisa di root atau nested
        log = raw.get("compute_log") or raw.get("log", [])
        if log:
            out["compute_log"] = log if isinstance(log, list) else []

    elif mod_key == "klaster":
        # Normalisasi profile_df ke list of dict
        profile_df = raw.get("profile_df")
        if profile_df is not None and hasattr(profile_df, "to_dict"):
            try:
                out["profile_df_records"] = profile_df.to_dict("records")
                out["profile_cols"]       = profile_df.columns.tolist()
            except Exception:
                pass
        # labels numpy array -> list
        labels = raw.get("labels")
        if labels is not None and hasattr(labels, "tolist"):
            out["labels"] = labels.tolist()
        for field in ("method", "k", "cols", "silhouette", "linkage"):
            if raw.get(field) is not None and out.get(field) is None:
                out[field] = raw[field]

    elif mod_key == "eda":
        for field in ("n_rows", "n_cols", "n_numeric", "n_cat",
                      "n_missing", "pct_missing", "n_dup", "num_cols", "cat_cols"):
            if raw.get(field) is not None and out.get(field) is None:
                out[field] = raw[field]

    elif mod_key == "scraping":
        for field in ("n_rows", "n_cols", "source", "col_names",
                      "n_numeric", "n_missing", "n_dup"):
            if raw.get(field) is not None and out.get(field) is None:
                out[field] = raw[field]
        # Bridge dari scraping_result jika tersedia
        import streamlit as st
        scr = st.session_state.get("scraping_result", {})
        if scr and not out.get("source"):
            out["source"] = scr.get("source", "")
            out["n_rows"] = scr.get("n_rows", 0)
            out["n_cols"] = scr.get("n_cols", 0)

    elif mod_key == "cfa":
        # Serialize DataFrame ke records agar bisa masuk docx renderer
        for df_field in ("fit_df", "loadings_df", "ave_cr_df"):
            df_val = raw.get(df_field)
            if df_val is not None and hasattr(df_val, "to_dict"):
                try:
                    out[df_field + "_records"] = df_val.to_dict("records")
                    out[df_field + "_cols"]    = df_val.columns.tolist()
                except Exception:
                    pass
        # htmt_df dan fl_df adalah DataFrame dengan index = konstruk
        for df_field in ("htmt_df", "fl_df"):
            df_val = raw.get(df_field)
            if df_val is not None and hasattr(df_val, "to_dict"):
                try:
                    out[df_field + "_records"] = df_val.reset_index().to_dict("records")
                except Exception:
                    pass
        for field in ("model_syntax", "factor_map", "n_obs", "alpha_level"):
            if raw.get(field) is not None and out.get(field) is None:
                out[field] = raw[field]
        # Bridge ai_text dari ai_cache["cfa"]
        import streamlit as st
        if not raw.get("ai_text"):
            ai_t = st.session_state.get("ai_cache", {}).get("cfa", "")
            if ai_t:
                out["ai_text"] = ai_t

    return out


def collect_session_results() -> dict:
    CONFIRMED_KEYS = {
        "ols_result":             ("ols_plus",    "Regresi OLS+"),
        "log_result":             ("logistik",    "Regresi Logistik"),
        "med_result":             ("mediasi",     "Mediasi"),
        "mod_result":             ("moderasi",    "Moderasi / Interaksi"),
        "anova_result":           ("anova",       "ANOVA & Post-hoc"),
        "regresi_result":         ("regresi",     "Regresi Linier"),
        "compute_log":            ("compute",     "Compute Variabel"),
        # Patch v4.2 — Regresi Robust & WLS
        "robust_result":          ("ols_robust",  "Regresi Robust (RLM)"),
        "wls_result":             ("ols_wls",     "Weighted Least Squares (WLS)"),
        "robust_comparison_result": ("ols_robust_comparison", "Perbandingan Model Robust"),
        # Poin 4 — modul baru
        "icc_result":             ("reliabilitas_icc", "Reliabilitas ICC"),
        "asumsi_result":          ("uji_asumsi",       "Uji Asumsi Pra-Analisis"),
        # Modul baru v4.2
        "klaster_result":         ("klaster",          "Analisis Klaster"),
        "eda_result":             ("eda",              "Eksplorasi Data (EDA)"),
        "cfa_result":             ("cfa",              "CFA Standalone"),
        "scraping_session":       ("scraping",         "Web Scraping"),
    }

    FALLBACK_KEYS = {
        "regression_result":  ("regresi",  "Regresi Linier"),
        "regresi":            ("regresi",  "Regresi Linier"),
        "reg_result":         ("regresi",  "Regresi Linier"),
        "moderation_result":  ("moderasi", "Moderasi / Interaksi"),
        "moderasi_result":    ("moderasi", "Moderasi / Interaksi"),
        "oneway_result":      ("anova",    "ANOVA & Post-hoc"),
        "uji_beda_result":    ("uji_beda", "Uji Beda (t-test/Mann-Whitney)"),
        "uji_beda":           ("uji_beda", "Uji Beda (t-test/Mann-Whitney)"),
        "ttest_result":       ("uji_beda", "Uji Beda (t-test/Mann-Whitney)"),
        "outlier_result":     ("outlier",  "Deteksi Outlier"),
        "sem_result":         ("sem",      "SEM & CFA"),
        "efa_session":        ("efa",      "EFA (Analisis Faktor)"),
        "kelompok_result":    ("kelompok", "Analisis Kelompok"),
        "group_result":       ("kelompok", "Analisis Kelompok"),
        # Poin 4 — fallback keys modul baru
        "icc_result":         ("reliabilitas_icc", "Reliabilitas ICC"),
        "reliabilitas_result":("reliabilitas_icc", "Reliabilitas ICC"),
        "asumsi_result":      ("uji_asumsi",       "Uji Asumsi Pra-Analisis"),
        "assumption_result":  ("uji_asumsi",       "Uji Asumsi Pra-Analisis"),
        "power_result":       ("power_analysis",   "Power Analysis"),
        # Modul baru v4.2
        "cluster_result":     ("klaster",          "Analisis Klaster"),
        "clustering_result":  ("klaster",          "Analisis Klaster"),
        "eda_summary":        ("eda",              "Eksplorasi Data (EDA)"),
        "cfa_result":         ("cfa",              "CFA Standalone"),
        "scraping_result":    ("scraping",         "Web Scraping"),
    }

    MODULE_LABELS = {
        "regresi":               "Regresi Linier",
        "ols_plus":              "Regresi OLS+",
        "logistik":              "Regresi Logistik",
        "mediasi":               "Mediasi",
        "moderasi":              "Moderasi / Interaksi",
        "anova":                 "ANOVA & Post-hoc",
        "uji_beda":              "Uji Beda (t-test/Mann-Whitney)",
        "outlier":               "Deteksi Outlier",
        "sem":                   "SEM & CFA",
        "efa":                   "EFA (Analisis Faktor)",
        "kelompok":              "Analisis Kelompok",
        "compute":               "Compute Variabel",
        # Patch v4.2
        "ols_robust":            "Regresi Robust (RLM)",
        "ols_wls":               "Weighted Least Squares (WLS)",
        "ols_robust_comparison": "Perbandingan Model Robust",
        # Poin 4
        "reliabilitas_icc":      "Reliabilitas ICC",
        "uji_asumsi":            "Uji Asumsi Pra-Analisis",
        "power_analysis":        "Power Analysis",
        # Modul baru v4.2
        "klaster":               "Analisis Klaster",
        "eda":                   "Eksplorasi Data (EDA)",
        "cfa":                   "CFA Standalone",
        "scraping":              "Web Scraping & Data Collector",
    }

    collected = {}

    for ss_key, (module_id, label) in CONFIRMED_KEYS.items():
        val = st.session_state.get(ss_key)
        if val is not None:
            collected[module_id] = {
                "label": label,
                "data":  _normalize_mod_data(module_id, val),
            }

    for ss_key, (module_id, label) in FALLBACK_KEYS.items():
        if module_id in collected:
            continue
        val = st.session_state.get(ss_key)
        if val is not None:
            collected[module_id] = {
                "label": label,
                "data":  _normalize_mod_data(module_id, val),
            }

    # Scan substring
    module_keywords = {
        "regresi":               ["regres", "linear"],
        "ols_plus":              ["ols"],
        "logistik":              ["logis", "logit", "log_result"],
        "mediasi":               ["medias", "sobel", "med_result"],
        "moderasi":              ["moderas", "interact", "mod_result"],
        "anova":                 ["anova", "oneway", "posthoc"],
        "uji_beda":              ["uji_beda", "ttest", "t_test", "mann", "whitney"],
        "outlier":               ["outlier", "zscore", "z_score", "iqr"],
        "sem":                   ["_sem", "sem_", "_cfa", "cfa_"],
        "efa":                   ["efa_session", "efa_result", "_efa"],
        "kelompok":              ["kelompok", "group_", "cluster"],
        "compute":               ["compute_log", "compute_result", "_compute"],
        # Patch v4.2
        "ols_robust":            ["robust_result"],
        "ols_wls":               ["wls_result"],
        "ols_robust_comparison": ["robust_comparison"],
    }

    all_ss_keys = list(st.session_state.keys())
    for module_id, keywords in module_keywords.items():
        if module_id in collected:
            continue
        for ss_key in all_ss_keys:
            ss_key_lower = ss_key.lower()
            for kw in keywords:
                if kw in ss_key_lower:
                    val = st.session_state.get(ss_key)
                    if (val is not None and val != {} and val != []
                            and not isinstance(val, (bool, str, int, float))):
                        collected[module_id] = {
                            "label": MODULE_LABELS.get(module_id, module_id),
                            "data":  _normalize_mod_data(module_id, val),
                        }
                        break
            if module_id in collected:
                break

    return collected


# ─────────────────────────────────────────────────────────────────────────────
# Helper: build scatter figure dari regresi
# ─────────────────────────────────────────────────────────────────────────────

def build_regression_scatter(df: pd.DataFrame, reg_result: dict) -> go.Figure | None:
    try:
        y_pred   = reg_result.get("y_pred")
        y_actual = reg_result.get("y_actual")
        if y_pred is None or y_actual is None:
            return None
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=y_actual, y=y_pred, mode="markers",
            marker=dict(color="#185FA5", size=6, opacity=0.7),
            name="Aktual vs Prediksi"
        ))
        mn = min(min(y_actual), min(y_pred))
        mx = max(max(y_actual), max(y_pred))
        fig.add_trace(go.Scatter(
            x=[mn, mx], y=[mn, mx], mode="lines",
            line=dict(color="#E24B4A", dash="dash"), name="Garis Sempurna"
        ))
        fig.update_layout(
            title="Scatter Aktual vs Prediksi",
            xaxis_title="Nilai Aktual", yaxis_title="Nilai Prediksi",
            template="plotly_white"
        )
        return fig
    except Exception:
        return None

def build_model_comparison_table(session_results: dict) -> pd.DataFrame | None:
    """
    Bandingkan semua model regresi yang ada di sesi aktif.

    Mendukung modul: regresi, ols_plus, logistik, moderasi.

    Returns:
        pd.DataFrame dengan kolom: Modul, Variabel Y, Variabel X,
        R² / AUC, R² Adj, F p-value, RMSE / AIC, Kualitas Model
    atau None jika tidak ada model yang bisa dibandingkan.
    """
    REGRESSION_MODULES = ("regresi", "ols_plus", "moderasi")
    LOGISTIC_MODULES   = ("logistik",)

    rows = []

    for mod_key, info in session_results.items():
        data  = info.get("data", {})
        label = info.get("label", mod_key)

        if mod_key in REGRESSION_MODULES:
            r2      = data.get("r2")
            adj_r2  = data.get("adj_r2")
            f_pval  = data.get("f_pvalue")
            rmse    = data.get("rmse")
            y_var   = data.get("y", "–")
            x_vars  = data.get("x", [])

            if r2 is None:
                # Coba ambil dari model statsmodels langsung
                model = data.get("model")
                if model is not None:
                    try:
                        r2     = float(model.rsquared)
                        adj_r2 = float(model.rsquared_adj)
                        f_pval = float(model.f_pvalue)
                    except Exception:
                        pass

            if r2 is None:
                continue

            # Kategorikan kualitas R²
            if r2 >= 0.7:
                kualitas = "🟢 Kuat"
            elif r2 >= 0.5:
                kualitas = "🟡 Sedang"
            elif r2 >= 0.3:
                kualitas = "🟠 Lemah"
            else:
                kualitas = "🔴 Sangat Lemah"

            rows.append({
                "Modul":           label,
                "Variabel Y":      y_var,
                "Variabel X":      ", ".join(x_vars) if x_vars else "–",
                "R²":              round(float(r2), 4)     if r2     is not None else "–",
                "R² Adjusted":     round(float(adj_r2), 4) if adj_r2 is not None else "–",
                "F p-value":       round(float(f_pval), 4) if f_pval is not None else "–",
                "RMSE":            round(float(rmse), 4)   if rmse   is not None else "–",
                "AUC":             "–",
                "Kualitas Model":  kualitas,
            })

        elif mod_key in LOGISTIC_MODULES:
            auc        = data.get("auc")
            pseudo_r2  = data.get("pseudo_r2")
            aic        = data.get("aic")
            y_var      = data.get("y", "–")
            x_vars     = data.get("x", [])

            if auc is None:
                continue

            if auc >= 0.9:
                kualitas = "🟢 Sangat Baik"
            elif auc >= 0.8:
                kualitas = "🟢 Baik"
            elif auc >= 0.7:
                kualitas = "🟡 Cukup"
            else:
                kualitas = "🔴 Lemah"

            rows.append({
                "Modul":           label,
                "Variabel Y":      y_var,
                "Variabel X":      ", ".join(x_vars) if x_vars else "–",
                "R²":              round(float(pseudo_r2), 4) if pseudo_r2 is not None else "–",
                "R² Adjusted":     "–",
                "F p-value":       "–",
                "RMSE":            round(float(aic), 2)       if aic       is not None else "–",
                "AUC":             round(float(auc), 4)       if auc       is not None else "–",
                "Kualitas Model":  kualitas,
            })

    if not rows:
        return None

    df_comp = pd.DataFrame(rows)

    # Rename RMSE kolom jadi lebih deskriptif
    df_comp = df_comp.rename(columns={"RMSE": "RMSE / AIC"})

    return df_comp


# ─────────────────────────────────────────────────────────────────────────────
# Helper: prompt ringkasan per modul untuk AI
# ─────────────────────────────────────────────────────────────────────────────

def _build_module_ai_prompt(mod_key: str, mod_data: dict, mod_label: str) -> str:
    """Buat prompt AI yang kaya konteks untuk setiap modul."""

    # Kumpulkan ringkasan data
    summary = {}
    for k in ("coef_table", "r2", "adj_r2", "f_pvalue", "rmse",
              "accuracy", "auc", "pseudo_r2", "aic", "bic",
              "indirect_effect", "direct_effect", "total_effect",
              "bootstrap_ci", "eta_squared", "statistic", "p_value",
              "effect_size", "total_outliers", "method", "pct_outliers",
              "variabel", "num_col", "g1_name", "g2_name", "g1_mean", "g2_mean",
              "cat", "num", "best_group", "worst_group", "f_stat",
              "fit_indices", "durbin_watson", "vif_max",
              "n_total", "n_valid", "n_butir",
              "x", "y", "m", "z", "jenis_mediasi", "johnson_neyman",
              "posthoc_method", "test_name", "n_groups"):
        v = mod_data.get(k) if isinstance(mod_data, dict) else None
        if v is not None:
            if hasattr(v, "to_dict"):
                summary[k] = v.head(10).to_dict()
            elif isinstance(v, (int, float, str, list, dict, bool)):
                summary[k] = v

    # Prompt spesifik per modul
    MODULE_SYSTEM_PROMPTS = {
        "regresi": (
            "Buat interpretasi komprehensif hasil Regresi Linier dalam Bahasa Indonesia "
            "mencakup: (1) kualitas model (R², F-test), (2) interpretasi koefisien yang "
            "signifikan, (3) persamaan regresi dan maknanya, (4) rekomendasi. "
            "Format: 4 paragraf akademis tanpa bullet points."
        ),
        "ols_plus": (
            "Buat interpretasi komprehensif hasil Regresi OLS+ dalam Bahasa Indonesia "
            "mencakup: (1) kualitas model, (2) koefisien signifikan, "
            "(3) evaluasi uji asumsi klasik (Durbin-Watson, VIF, White test, normalitas), "
            "(4) rekomendasi jika ada asumsi yang dilanggar. "
            "Format: 4 paragraf akademis tanpa bullet points."
        ),
        "logistik": (
            "Buat interpretasi komprehensif hasil Regresi Logistik dalam Bahasa Indonesia "
            "mencakup: (1) kualitas model (AUC, Pseudo R²), (2) odds ratio yang signifikan, "
            "(3) performa klasifikasi, (4) limitasi model. "
            "Format: 4 paragraf akademis tanpa bullet points."
        ),
        "mediasi": (
            "Buat interpretasi komprehensif hasil Analisis Mediasi dalam Bahasa Indonesia "
            "mencakup: (1) jalur a, b, c, c', (2) efek tidak langsung & Bootstrap CI, "
            "(3) jenis mediasi (penuh/sebagian/tidak ada), (4) implikasi teoritis. "
            "Format: 4 paragraf akademis tanpa bullet points."
        ),
        "moderasi": (
            "Buat interpretasi komprehensif hasil Analisis Moderasi dalam Bahasa Indonesia "
            "mencakup: (1) signifikansi efek interaksi, (2) interpretasi substantif, "
            "(3) Johnson-Neyman jika ada, (4) implikasi penelitian. "
            "Format: 4 paragraf akademis tanpa bullet points."
        ),
        "anova": (
            "Buat interpretasi komprehensif hasil ANOVA dalam Bahasa Indonesia "
            "mencakup: (1) keputusan H₀ (F-test), (2) ukuran efek η², "
            "(3) perbedaan spesifik antar kelompok (post-hoc), (4) implikasi. "
            "Format: 4 paragraf akademis tanpa bullet points."
        ),
        "uji_beda": (
            "Buat interpretasi komprehensif hasil Uji Beda dalam Bahasa Indonesia "
            "mencakup: (1) statistik uji & p-value, (2) besar perbedaan (effect size), "
            "(3) kesimpulan praktis, (4) rekomendasi. "
            "Format: 3-4 paragraf akademis tanpa bullet points."
        ),
        "outlier": (
            "Buat interpretasi singkat hasil Deteksi Outlier dalam Bahasa Indonesia "
            "mencakup: (1) metode & jumlah outlier, (2) dampak pada analisis, "
            "(3) rekomendasi penanganan. "
            "Format: 2-3 paragraf akademis tanpa bullet points."
        ),
        "sem": (
            "Buat interpretasi komprehensif hasil SEM & CFA dalam Bahasa Indonesia "
            "mencakup: (1) evaluasi model fit, (2) factor loadings CFA, "
            "(3) jalur struktural, (4) kesimpulan. "
            "Format: 4 paragraf akademis tanpa bullet points."
        ),
        "efa": (
            "Buat interpretasi komprehensif hasil Analisis Faktor Eksploratori (EFA) "
            "dalam Bahasa Indonesia mencakup: (1) evaluasi kelayakan data (KMO & Bartlett), "
            "(2) jumlah faktor yang tepat dan dasar pengambilan keputusan (Kaiser criterion, "
            "cumulative variance), (3) struktur faktor dan interpretasi konseptual loading, "
            "(4) rekomendasi untuk penelitian selanjutnya (CFA, construct validity). "
            "Format: 4 paragraf akademis tanpa bullet points."
        ),
        "kelompok": (
            "Buat interpretasi komprehensif hasil Analisis Kelompok dalam Bahasa Indonesia "
            "mencakup: (1) perbedaan antar kelompok, (2) kelompok terbaik/terburuk, "
            "(3) signifikansi statistik, (4) implikasi. "
            "Format: 3 paragraf akademis tanpa bullet points."
        ),
    }

    # Handle compute modul separately — return early before generic prompt
    if mod_key == "compute":
        compute_log = mod_data.get("compute_log", [])
        n_ops       = len(compute_log)
        log_str     = json.dumps(compute_log[:10], ensure_ascii=False, indent=2)
        return (
            f"Ringkasan operasi Compute Variabel ({n_ops} operasi):\n{log_str}\n\n"
            "Berikan interpretasi akademis dalam Bahasa Indonesia:\n"
            "1. Rasionalisasi setiap variabel baru yang dibuat\n"
            "2. Metode komputasi yang digunakan dan implikasinya\n"
            "3. Rekomendasi penggunaan variabel baru dalam analisis\n"
            "Format: 3 paragraf akademis."
        )

    system_prompt = MODULE_SYSTEM_PROMPTS.get(
        mod_key,
        f"Buat interpretasi {mod_label} dalam Bahasa Indonesia. Format akademis 3 paragraf."
    )

    return (
        system_prompt
        + "\n\nData hasil analisis:\n"
        + json.dumps(summary, default=str, indent=2)
    )

# ── Database referensi APA 7th ────────────────────────────────────────────────

APA_REFERENCES: dict[str, str] = {

    # ── Statistik Umum ───────────────────────────────────────────────────────
    "field_2018": (
        "Field, A. (2018). *Discovering statistics using IBM SPSS statistics* "
        "(5th ed.). SAGE Publications."
    ),
    "hair_2010": (
        "Hair, J. F., Black, W. C., Babin, B. J., & Anderson, R. E. (2010). "
        "*Multivariate data analysis* (7th ed.). Pearson Prentice Hall."
    ),
    "ghozali_2018": (
        "Ghozali, I. (2018). *Aplikasi analisis multivariate dengan program IBM SPSS 25* "
        "(9th ed.). Badan Penerbit Universitas Diponegoro."
    ),
    "sugiyono_2019": (
        "Sugiyono. (2019). *Metode penelitian kuantitatif, kualitatif, dan R&D* "
        "(2nd ed.). Alfabeta."
    ),

    # ── Validitas & Reliabilitas ──────────────────────────────────────────────
    "cronbach_1951": (
        "Cronbach, L. J. (1951). Coefficient alpha and the internal structure of tests. "
        "*Psychometrika*, *16*(3), 297–334. https://doi.org/10.1007/BF02310555"
    ),
    "pearson_1895": (
        "Pearson, K. (1895). Notes on regression and inheritance in the case of two parents. "
        "*Proceedings of the Royal Society of London*, *58*, 240–242."
    ),
    "nunnally_1978": (
        "Nunnally, J. C. (1978). *Psychometric theory* (2nd ed.). McGraw-Hill."
    ),

    # ── Normalitas ────────────────────────────────────────────────────────────
    "shapiro_wilk_1965": (
        "Shapiro, S. S., & Wilk, M. B. (1965). An analysis of variance test for normality "
        "(complete samples). *Biometrika*, *52*(3–4), 591–611. "
        "https://doi.org/10.1093/biomet/52.3-4.591"
    ),

    # ── Regresi ───────────────────────────────────────────────────────────────
    "cohen_1988": (
        "Cohen, J. (1988). *Statistical power analysis for the behavioral sciences* "
        "(2nd ed.). Lawrence Erlbaum Associates."
    ),
    "durbin_watson_1950": (
        "Durbin, J., & Watson, G. S. (1950). Testing for serial correlation in least squares "
        "regression: I. *Biometrika*, *37*(3–4), 409–428. "
        "https://doi.org/10.1093/biomet/37.3-4.409"
    ),
    "white_1980": (
        "White, H. (1980). A heteroskedasticity-consistent covariance matrix estimator and a "
        "direct test for heteroskedasticity. *Econometrica*, *48*(4), 817–838. "
        "https://doi.org/10.2307/1912934"
    ),
    "breusch_godfrey_1978": (
        "Breusch, T. S. (1978). Testing for autocorrelation in dynamic linear models. "
        "*Australian Economic Papers*, *17*(31), 334–355."
    ),
    "vif_marquardt_1970": (
        "Marquardt, D. W. (1970). Generalized inverses, ridge regression, biased linear "
        "estimation, and nonlinear estimation. *Technometrics*, *12*(3), 591–612. "
        "https://doi.org/10.1080/00401706.1970.10488699"
    ),

    # ── Mediasi ───────────────────────────────────────────────────────────────
    "baron_kenny_1986": (
        "Baron, R. M., & Kenny, D. A. (1986). The moderator–mediator variable distinction in "
        "social psychological research: Conceptual, strategic, and statistical considerations. "
        "*Journal of Personality and Social Psychology*, *51*(6), 1173–1182. "
        "https://doi.org/10.1037/0022-3514.51.6.1173"
    ),
    "preacher_hayes_2008": (
        "Preacher, K. J., & Hayes, A. F. (2008). Asymptotic and resampling strategies for "
        "assessing and comparing indirect effects in multiple mediator models. "
        "*Behavior Research Methods*, *40*(3), 879–891. "
        "https://doi.org/10.3758/BRM.40.3.879"
    ),
    "hayes_2013": (
        "Hayes, A. F. (2013). *Introduction to mediation, moderation, and conditional process "
        "analysis: A regression-based approach*. Guilford Press."
    ),
    "sobel_1982": (
        "Sobel, M. E. (1982). Asymptotic confidence intervals for indirect effects in structural "
        "equation models. *Sociological Methodology*, *13*, 290–312. "
        "https://doi.org/10.2307/270723"
    ),

    # ── Moderasi ─────────────────────────────────────────────────────────────
    "johnson_neyman_1936": (
        "Johnson, P. O., & Neyman, J. (1936). Tests of certain linear hypotheses and their "
        "application to some educational problems. *Statistical Research Memoirs*, *1*, 57–93."
    ),
    "aiken_west_1991": (
        "Aiken, L. S., & West, S. G. (1991). *Multiple regression: Testing and interpreting "
        "interactions*. SAGE Publications."
    ),

    # ── ANOVA ─────────────────────────────────────────────────────────────────
    "tukey_1949": (
        "Tukey, J. W. (1949). Comparing individual means in the analysis of variance. "
        "*Biometrics*, *5*(2), 99–114. https://doi.org/10.2307/3001913"
    ),
    "kruskal_wallis_1952": (
        "Kruskal, W. H., & Wallis, W. A. (1952). Use of ranks in one-criterion variance analysis. "
        "*Journal of the American Statistical Association*, *47*(260), 583–621. "
        "https://doi.org/10.1080/01621459.1952.10483441"
    ),

    # ── Regresi Logistik ─────────────────────────────────────────────────────
    "hosmer_lemeshow_2013": (
        "Hosmer, D. W., Lemeshow, S., & Sturdivant, R. X. (2013). "
        "*Applied logistic regression* (3rd ed.). Wiley."
    ),
    "mcfadden_1974": (
        "McFadden, D. (1974). Conditional logit analysis of qualitative choice behavior. "
        "In P. Zarembka (Ed.), *Frontiers in econometrics* (pp. 105–142). Academic Press."
    ),

    # ── EFA ───────────────────────────────────────────────────────────────────
    "kaiser_1974": (
        "Kaiser, H. F. (1974). An index of factorial simplicity. "
        "*Psychometrika*, *39*(1), 31–36. https://doi.org/10.1007/BF02291575"
    ),
    "bartlett_1950": (
        "Bartlett, M. S. (1950). Tests of significance in factor analysis. "
        "*British Journal of Psychology*, *3*(2), 77–85. "
        "https://doi.org/10.1111/j.2044-8317.1950.tb00285.x"
    ),
    "jennrich_sampson_1966": (
        "Jennrich, R. I., & Sampson, P. F. (1966). Rotation for simple loadings. "
        "*Psychometrika*, *31*(3), 313–323. https://doi.org/10.1007/BF02289465"
    ),
    "cattell_1966": (
        "Cattell, R. B. (1966). The scree test for the number of factors. "
        "*Multivariate Behavioral Research*, *1*(2), 245–276. "
        "https://doi.org/10.1207/s15327906mbr0102_10"
    ),
    "fabrigar_1999": (
        "Fabrigar, L. R., Wegener, D. T., MacCallum, R. C., & Strahan, E. J. (1999). "
        "Evaluating the use of exploratory factor analysis in psychological research. "
        "*Psychological Methods*, *4*(3), 272–299. https://doi.org/10.1037/1082-989X.4.3.272"
    ),

    # ── SEM ───────────────────────────────────────────────────────────────────
    "fornell_larcker_1981": (
        "Fornell, C., & Larcker, D. F. (1981). Evaluating structural equation models with "
        "unobservable variables and measurement error. *Journal of Marketing Research*, "
        "*18*(1), 39–50. https://doi.org/10.1177/002224378101800104"
    ),
    "hu_bentler_1999": (
        "Hu, L., & Bentler, P. M. (1999). Cutoff criteria for fit indexes in covariance structure "
        "analysis: Conventional criteria versus new alternatives. *Structural Equation Modeling*, "
        "*6*(1), 1–55. https://doi.org/10.1080/10705519909540118"
    ),

    # ── Software ─────────────────────────────────────────────────────────────
    "python_statsmodels": (
        "Seabold, S., & Perktold, J. (2010). Statsmodels: Econometric and statistical modeling "
        "with Python. *Proceedings of the 9th Python in Science Conference*, 92–96. "
        "https://doi.org/10.25080/Majora-92bf1922-011"
    ),
    "scipy_2020": (
        "Virtanen, P., Gommers, R., Oliphant, T. E., Haberland, M., Reddy, T., "
        "Cournapeau, D., ... & van der Walt, S. J. (2020). SciPy 1.0: Fundamental algorithms "
        "for scientific computing in Python. *Nature Methods*, *17*(3), 261–272. "
        "https://doi.org/10.1038/s41592-019-0686-2"
    ),
}


# ── Mapping modul → referensi yang relevan ─────────────────────────────────

MODULE_REFERENCES: dict[str, list[str]] = {
    "deskriptif": [
        "field_2018", "ghozali_2018", "sugiyono_2019",
        "shapiro_wilk_1965", "scipy_2020",
    ],
    "validitas": [
        "cronbach_1951", "pearson_1895", "nunnally_1978",
        "ghozali_2018", "field_2018",
    ],
    "korelasi": [
        "pearson_1895", "field_2018", "cohen_1988", "scipy_2020",
    ],
    "regresi": [
        "field_2018", "hair_2010", "cohen_1988",
        "python_statsmodels", "scipy_2020",
    ],
    "ols_plus": [
        "field_2018", "hair_2010",
        "durbin_watson_1950", "white_1980", "breusch_godfrey_1978",
        "vif_marquardt_1970", "shapiro_wilk_1965",
        "python_statsmodels",
    ],
    "mediasi": [
        "baron_kenny_1986", "preacher_hayes_2008", "hayes_2013",
        "sobel_1982", "field_2018",
    ],
    "moderasi": [
        "aiken_west_1991", "hayes_2013",
        "johnson_neyman_1936", "cohen_1988", "field_2018",
    ],
    "anova": [
        "field_2018", "tukey_1949", "kruskal_wallis_1952",
        "cohen_1988", "scipy_2020",
    ],
    "logistik": [
        "hosmer_lemeshow_2013", "mcfadden_1974",
        "field_2018", "python_statsmodels",
    ],
    "sem": [
        "hair_2010", "fornell_larcker_1981", "hu_bentler_1999",
        "cohen_1988",
    ],
    "efa": [
        "kaiser_1974", "bartlett_1950", "jennrich_sampson_1966",
        "cattell_1966", "fabrigar_1999", "hair_2010", "field_2018",
    ],
    "uji_beda": [
        "field_2018", "cohen_1988", "kruskal_wallis_1952", "scipy_2020",
    ],
    "kelompok": [
        "field_2018", "ghozali_2018", "scipy_2020",
    ],
    "outlier": [
        "field_2018", "ghozali_2018",
    ],
}

# Referensi wajib yang selalu disertakan
ALWAYS_INCLUDE = [
    "field_2018",
    "ghozali_2018",
    "sugiyono_2019",
    "cohen_1988",
    "scipy_2020",
    "python_statsmodels",
]

   
    # ... kode Anda selanjutnya ...
def generate_apa_references(
    inc_desc: bool,
    inc_val: bool,
    inc_corr: bool,
    module_checkboxes: dict,       # {mod_key: bool}
    report_style: str = "APA 7th Edition",
) -> str:
    """
    Generate daftar referensi APA 7th berdasarkan modul yang digunakan.

    Returns:
        String teks referensi siap masuk ke dokumen laporan.
    """
    ref_keys: set[str] = set(ALWAYS_INCLUDE)

    if inc_desc:
        ref_keys.update(MODULE_REFERENCES.get("deskriptif", []))
    if inc_val:
        ref_keys.update(MODULE_REFERENCES.get("validitas", []))
    if inc_corr:
        ref_keys.update(MODULE_REFERENCES.get("korelasi", []))

    for mod_key, selected in module_checkboxes.items():
        if selected:
            ref_keys.update(MODULE_REFERENCES.get(mod_key, []))

    # Ambil teks referensi dan urutkan alfabetis
    ref_texts = []
    for key in sorted(ref_keys):
        text = APA_REFERENCES.get(key)
        if text:
            ref_texts.append(text)

    if not ref_texts:
        return ""

    # Header sesuai gaya laporan
    if "APA" in report_style:
        header = "References"
    elif "Vancouver" in report_style:
        header = "Daftar Pustaka (Vancouver)"
    else:
        header = "Daftar Pustaka"

    lines = [f"## {header}\n"]
    for i, ref in enumerate(ref_texts, 1):
        if "Vancouver" in report_style:
            # Vancouver: numbered
            lines.append(f"{i}. {ref}\n")
        else:
            # APA / Skripsi Indonesia: hanging indent simulation
            lines.append(f"{ref}\n")

    return "\n".join(lines)


def render_apa_preview(apa_text: str):
    """Tampilkan preview referensi di Streamlit."""
    if not apa_text:
        return
    st.markdown("---")
    st.markdown("#### 📚 Preview Daftar Referensi (APA 7th)")
    with st.expander("Lihat daftar referensi yang akan disertakan dalam laporan"):
        st.markdown(apa_text)


# ─────────────────────────────────────────────────────────────────────────────
# RENDER UTAMA
# ─────────────────────────────────────────────────────────────────────────────

def render(ctx: dict):
    license_info      = ctx["license_info"]
    r_tab             = ctx["r_tab"]
    ai_enabled        = ctx["ai_enabled"]
    anthropic_api_key = ctx["anthropic_api_key"]
    ai_provider       = ctx["ai_provider"]

    st.markdown('<p class="rs-section-title">📄 Generate Laporan Professional</p>',
                unsafe_allow_html=True)
    st.markdown(
        '<p class="rs-section-sub">Hasilkan laporan lengkap dengan narasi AI — '
        'tabel standar, grafik tertanam, persamaan model, dan interpretasi akademis.</p>',
        unsafe_allow_html=True,
    )

    df = require_data()
    if df is None:
        st.stop()
    cols = require_cols(df)
    if cols is None:
        st.stop()

    report = ss_get("report", {})

    is_pro = license_info.get("status") == "pro"

    if not is_pro:
        # ── Cek quota gratis ──────────────────────────────────────────────────
        can_export, used_today = check_daily_export_quota()

        if not can_export:
            # Quota habis — tampilkan info dan stop
            st.error(
                f"⏳ **Kuota laporan gratis hari ini sudah habis** ({used_today}/{1} digunakan).\n\n"
                "Laporan gratis tersedia **1 kali per hari**. Coba lagi besok, atau upgrade ke "
                "**Paket Pro** untuk laporan tak terbatas dengan narasi AI penuh."
            )
            st.info("👉 [Dapatkan akses Pro](https://yogoaj.github.io)")
            st.markdown("---")
            st.markdown("**Fitur eksklusif laporan Pro:**")
            for item in [
                "📐 Persamaan model AI-generated per modul",
                "🤖 Interpretasi AI per tabel & grafik",
                "📝 Kesimpulan & rekomendasi AI",
                "📊 Grafik Plotly tertanam di dokumen Word",
                "♾️ Tidak ada batasan jumlah laporan",
                "📋 Multi-format: APA 7th, Skripsi Indonesia, Vancouver, Jurnal, Bisnis",
            ]:
                st.markdown(f"- {item}")
            st.stop()

        # Quota masih ada — lanjut tapi matikan AI
        remaining = 1 - used_today
        st.info(
            f"📄 **Mode Gratis** — Sisa kuota laporan hari ini: **{remaining}/1**.\n\n"
            "Laporan akan dibuat **tanpa narasi AI**. "
            "Upgrade ke Pro untuk laporan lengkap dengan interpretasi AI."
        )
        # Override ai_enabled agar tidak ada call ke API AI
        ai_enabled = False

        # ── Konfigurasi (Free) ────────────────────────────────────────────────
        st.markdown("#### ⚙️ Konfigurasi Laporan")
        cfg1, cfg2 = st.columns(2)
        with cfg1:
            data_type = st.radio("📋 Tipe Data / Penelitian:", [
                "Data Primer (Kuesioner / Survei)",
                "Data Sekunder (Laporan / Statistik / Keuangan)",
                "Data Eksperimen (Pre-Post / Kelompok Kontrol)",
            ])
        with cfg2:
            report_style = st.selectbox("🎨 Gaya Format Laporan:", [
                "APA 7th Edition",
                "Skripsi / Tesis Indonesia (DIKTI)",
                "Vancouver (Medis / Kesehatan)",
                "Jurnal Ilmiah Umum",
                "Laporan Bisnis / Kantor",
            ])

        output_format = st.radio("📄 Format File Output:", ["Word (.docx)", "Markdown (.md)"],
                                  horizontal=True)

        # ── Deteksi modul sesi (Free) ─────────────────────────────────────────
        st.markdown("---")
        st.markdown("#### 📦 Pilih Konten Laporan")

    else:
        # Pro — akses penuh
        st.success("✨ Akses Pro dikonfirmasi. Laporan lengkap siap di-generate.")
        if ai_enabled:
            st.info(
                f"🤖 AI Interpreter aktif: **{ai_provider}** "
                "— interpretasi & persamaan model akan disertakan"
            )
        else:
            st.caption(
                "💡 Masukkan API Key di sidebar untuk laporan dengan narasi AI dan persamaan model."
            )

        # ── Konfigurasi (Pro) ─────────────────────────────────────────────────
        st.markdown("#### ⚙️ Konfigurasi Laporan")
        cfg1, cfg2 = st.columns(2)
        with cfg1:
            data_type = st.radio("📋 Tipe Data / Penelitian:", [
                "Data Primer (Kuesioner / Survei)",
                "Data Sekunder (Laporan / Statistik / Keuangan)",
                "Data Eksperimen (Pre-Post / Kelompok Kontrol)",
            ])
        with cfg2:
            report_style = st.selectbox("🎨 Gaya Format Laporan:", [
                "APA 7th Edition",
                "Skripsi / Tesis Indonesia (DIKTI)",
                "Vancouver (Medis / Kesehatan)",
                "Jurnal Ilmiah Umum",
                "Laporan Bisnis / Kantor",
            ])

        output_format = st.radio("📄 Format File Output:", ["Word (.docx)", "Markdown (.md)"],
                                  horizontal=True)

        # ── Deteksi modul sesi ────────────────────────────────────────────────
        st.markdown("---")
        st.markdown("#### 📦 Pilih Konten Laporan")

    session_results = collect_session_results()
    # ── Tabel Perbandingan Model ──────────────────────────────────────────────────
    comp_table = build_model_comparison_table(session_results)
    if comp_table is not None:
        st.markdown("---")
        st.markdown("#### 📊 Perbandingan Model Regresi")
        st.markdown(
            '<p class="rs-section-sub">Ringkasan R², AUC, dan kualitas semua model '
            'yang dijalankan dalam sesi ini.</p>',
            unsafe_allow_html=True,
        )
        st.dataframe(comp_table, use_container_width=True, hide_index=True)

        # Highlight model terbaik
        r2_vals = [r for r in comp_table["R²"] if isinstance(r, float)]
        if r2_vals:
            max_r2 = max(r2_vals)
            matched = comp_table[comp_table["R²"] == max_r2]
            if not matched.empty:
                best_row = matched.iloc[0]
                st.markdown(
                    f'<div class="rs-narasi">🏆 Model terbaik: <b>{best_row["Modul"]}</b> '
                    f'(R² = {best_row["R²"]}, kualitas: {best_row["Kualitas Model"]})</div>',
                    unsafe_allow_html=True,
                )

    inc_desc  = st.checkbox("📊 Statistik Deskriptif + Uji Normalitas", value=True)
    show_val = not data_type.startswith("Data Sekunder")
    inc_val   = st.checkbox(
        "✅ Validitas & Reliabilitas",
        value=show_val and len(cols) >= 2,
        disabled=not show_val,
        help="Hanya relevan untuk data primer/eksperimen",
    )
    if not show_val:
        st.caption("ℹ️ Uji validitas/reliabilitas dinonaktifkan untuk data sekunder.")

    inc_corr = st.checkbox("🔗 Analisis Korelasi + Heatmap", value=len(cols) >= 2)

    # ── Modul lanjutan ────────────────────────────────────────────────────
    st.markdown("**Modul analisis lanjutan (dari sesi aktif):**")

    with st.expander("🔍 Debug: Key session_state", expanded=False):
        all_keys = list(st.session_state.keys())
        if all_keys:
            st.code("\n".join(sorted(all_keys)), language="text")
        else:
            st.caption("session_state kosong.")

    module_checkboxes = {}
    MODULE_ICONS = {
        "regresi":   "📈", "ols_plus":  "📐", "logistik":  "📉",
        "mediasi":   "🔀", "moderasi":  "🎛️", "anova":     "📊",
        "uji_beda":  "🔢", "outlier":   "🎯", "sem":       "🧩",
        "efa":       "🔬", "kelompok":  "📂", "compute": "🧮",
    }
    if session_results:
        cols_cb = st.columns(2)
        for i, (mod_key, info) in enumerate(session_results.items()):
            icon = MODULE_ICONS.get(mod_key, "📌")
            with cols_cb[i % 2]:
                module_checkboxes[mod_key] = st.checkbox(
                    f"{icon} {info['label']}",
                    value=True,
                    help=f"Hasil dari modul {info['label']} di sesi ini"
                )
    else:
        st.caption(
            "ℹ️ Belum ada hasil analisis lanjutan. "
            "Jalankan modul (Regresi, ANOVA, dll.) terlebih dahulu."
        )

    st.markdown("---")

    # ── Opsi AI ──────────────────────────────────────────────────────────
    col_ai1, col_ai2 = st.columns(2)
    with col_ai1:
        inc_ai_kes = st.checkbox(
            "🤖 Kesimpulan & Rekomendasi AI",
            value=ai_enabled, disabled=not ai_enabled,
            help="Memerlukan API Key",
        )
    with col_ai2:
        inc_model_eq = st.checkbox(
            "📐 Persamaan Model (AI-generated)",
            value=ai_enabled, disabled=not ai_enabled,
            help="Hasilkan persamaan matematis model penelitian per modul",
        )

    # Fix 7: cek kaleido sebelum tawarkan embed
    _kaleido_ok = False
    try:
        import kaleido  # noqa: F401
        _kaleido_ok = True
    except ImportError:
        st.warning(
            "⚠️ Library **kaleido** tidak ditemukan. "
            "Grafik tidak akan bisa di-embed ke dokumen. "
            "Install dengan: `pip install kaleido`",
            icon="⚠️",
        )

    embed_images = st.checkbox(
        "🖼️ Embed grafik/chart ke dalam dokumen",
        value=_kaleido_ok,
        disabled=not _kaleido_ok,
        help="Memerlukan library kaleido (pip install kaleido).",
    )

    st.markdown("---")

    if st.button("🚀 Generate & Unduh Laporan", type="primary", use_container_width=True):
        with st.spinner("⏳ Menyusun laporan… Mohon tunggu."):
            prog   = st.progress(0)
            status = st.empty()

            # ── 1. Statistik dasar ────────────────────────────────────────
            status.caption("⏳ Menghitung statistik deskriptif…")
            desc_df = descriptive_stats(df, cols) if inc_desc else pd.DataFrame()
            prog.progress(8)
            norm_df = normality_test(df, cols)   if inc_desc else pd.DataFrame()
            prog.progress(12)

            # ── 2. Validitas & Reliabilitas ───────────────────────────────
            val_df = None
            alpha_result = None
            if inc_val and len(cols) >= 2:
                status.caption("⏳ Menghitung validitas & reliabilitas…")
                val_df       = pearson_validity(df, cols, r_tab)
                alpha_result = calc_cronbach(df, cols)
            prog.progress(18)

            # ── 3. Korelasi ───────────────────────────────────────────────
            corr_matrix = df[cols].corr() if inc_corr and len(cols) >= 2 else None
            prog.progress(22)

            # ── 4. Build figures ──────────────────────────────────────────
            status.caption("⏳ Membuat grafik…")
            figs_export = {}

            if inc_desc and cols:
                s_hist = df[cols[0]].dropna()
                figs_export["histogram"] = go.Figure(go.Histogram(
                    x=s_hist, nbinsx=20, marker_color="#185FA5",
                    marker_line=dict(color="white", width=0.5),
                ))
                figs_export["histogram"].update_layout(
                    title=f"Distribusi: {cols[0]}", template="plotly_white",
                    xaxis_title=cols[0], yaxis_title="Frekuensi",
                )

            if val_df is not None and not val_df.empty:
                v_colors = [
                    "#3B6D11" if "Valid ✓" in str(s) else "#A32D2D"
                    for s in val_df["Status"]
                ]
                figs_export["validitas"] = go.Figure(go.Bar(
                    x=val_df["Butir"], y=val_df["r-hitung"],
                    marker_color=v_colors,
                    text=val_df["r-hitung"].round(3),
                    textposition="outside",
                ))
                figs_export["validitas"].add_hline(
                    y=r_tab, line_dash="dash", line_color="#E24B4A",
                    annotation_text=f"r-tabel = {r_tab}",
                )
                figs_export["validitas"].update_layout(
                    title="Hasil Uji Validitas Per Butir",
                    yaxis_title="r-hitung", template="plotly_white",
                )

            if corr_matrix is not None:
                rounded = np.round(corr_matrix.values, 3)
                figs_export["heatmap"] = go.Figure(go.Heatmap(
                    z=rounded,
                    x=list(corr_matrix.columns),
                    y=list(corr_matrix.columns),
                    colorscale="Blues",
                    text=rounded,
                    texttemplate="%{text}",
                    zmin=-1, zmax=1,
                ))
                figs_export["heatmap"].update_layout(
                    title="Matriks Korelasi", template="plotly_white",
                )

            # Scatter dari sesi korelasi
            scatter_sess = ss_get("korelasi_scatter", None)
            if scatter_sess and isinstance(scatter_sess, dict):
                sc_fig = scatter_sess.get("fig")
                if sc_fig is not None:
                    # docx_helpers uses "scatter" key
                    figs_export["scatter"]          = sc_fig
                    figs_export["korelasi_scatter"] = sc_fig

            # Figures dari modul sesi
            for mod_key, include in module_checkboxes.items():
                if not include:
                    continue
                mod_data = session_results[mod_key]["data"]
                if not isinstance(mod_data, dict):
                    continue

                if mod_key in ("regresi", "ols_plus"):
                    fig_scatter = build_regression_scatter(df, mod_data)
                    if fig_scatter:
                        figs_export[f"{mod_key}_scatter"] = fig_scatter

                    residuals = mod_data.get("residuals")
                    if residuals is not None:
                        fig_res = go.Figure(go.Scatter(
                            x=list(range(len(residuals))), y=list(residuals),
                            mode="markers",
                            marker=dict(color="#185FA5", size=5, opacity=0.6),
                            name="Residual",
                        ))
                        fig_res.add_hline(y=0, line_dash="dash", line_color="#E24B4A")
                        fig_res.update_layout(
                            title="Plot Residual",
                            xaxis_title="Observasi", yaxis_title="Residual",
                            template="plotly_white",
                        )
                        figs_export[f"{mod_key}_residual"] = fig_res

                    coef_table = mod_data.get("coef_table")
                    if coef_table is not None and hasattr(coef_table, "iterrows"):
                        try:
                            var_col  = coef_table.columns[0]
                            coef_col = next(
                                (c for c in coef_table.columns
                                 if c.lower() in ("koefisien (β)", "β (koefisien)", "β",
                                                  "coef", "b", "coefficient")),
                                coef_table.columns[1] if len(coef_table.columns) > 1 else None
                            )
                            if coef_col:
                                vals = pd.to_numeric(coef_table[coef_col], errors="coerce")
                                colors = ["#3B6D11" if v >= 0 else "#A32D2D" for v in vals.fillna(0)]
                                fig_coef = go.Figure(go.Bar(
                                    x=coef_table[var_col].astype(str),
                                    y=vals,
                                    marker_color=colors,
                                    text=vals.round(4),
                                    textposition="outside",
                                ))
                                fig_coef.add_hline(y=0, line_dash="solid", line_color="#888", line_width=1)
                                fig_coef.update_layout(
                                    title="Koefisien Regresi",
                                    xaxis_title="Variabel", yaxis_title="Nilai Koefisien",
                                    template="plotly_white",
                                )
                                figs_export[f"{mod_key}_koefisien"] = fig_coef
                        except Exception:
                            pass

                elif mod_key == "logistik":
                    coef_table = mod_data.get("coef_table")
                    if coef_table is not None and hasattr(coef_table, "iterrows"):
                        try:
                            var_col = coef_table.columns[0]
                            or_col  = next(
                                (c for c in coef_table.columns
                                 if c.lower() in ("or (exp β)", "odds ratio", "exp(b)", "exp(coef)")),
                                None
                            )
                            if or_col:
                                or_vals = pd.to_numeric(coef_table[or_col], errors="coerce")
                                fig_or = go.Figure(go.Bar(
                                    x=coef_table[var_col].astype(str),
                                    y=or_vals,
                                    marker_color="#185FA5",
                                    text=or_vals.round(3),
                                    textposition="outside",
                                ))
                                fig_or.add_hline(y=1, line_dash="dash",
                                                 line_color="#E24B4A",
                                                 annotation_text="OR = 1 (referensi)")
                                fig_or.update_layout(
                                    title="Odds Ratio — Regresi Logistik",
                                    xaxis_title="Variabel", yaxis_title="Odds Ratio",
                                    template="plotly_white",
                                )
                                figs_export["logistik_odds_ratio"] = fig_or
                        except Exception:
                            pass

                    roc_data = mod_data.get("roc")
                    if roc_data and isinstance(roc_data, dict):
                        fpr = roc_data.get("fpr", [])
                        tpr = roc_data.get("tpr", [])
                        auc = roc_data.get("auc")
                        if len(fpr) and len(tpr):
                            fig_roc = go.Figure()
                            fig_roc.add_trace(go.Scatter(
                                x=list(fpr), y=list(tpr), mode="lines",
                                name=f"ROC (AUC={auc:.3f})" if auc else "ROC",
                                line=dict(color="#185FA5", width=2),
                            ))
                            fig_roc.add_trace(go.Scatter(
                                x=[0, 1], y=[0, 1], mode="lines",
                                line=dict(color="#888", dash="dash"), name="Random",
                            ))
                            fig_roc.update_layout(
                                title="ROC Curve — Regresi Logistik",
                                xaxis_title="False Positive Rate",
                                yaxis_title="True Positive Rate",
                                template="plotly_white",
                            )
                            figs_export["logistik_roc"] = fig_roc

                elif mod_key == "mediasi":
                    effects = {}
                    for ek, lbl in [("indirect_effect", "Efek Tidak Langsung (a×b)"),
                                    ("direct_effect", "Efek Langsung (c')"),
                                    ("total_effect", "Efek Total (c)")]:
                        v = mod_data.get(ek)
                        if v is not None:
                            effects[lbl] = float(v)
                    if effects:
                        colors = ["#185FA5" if v >= 0 else "#A32D2D" for v in effects.values()]
                        fig_med = go.Figure(go.Bar(
                            x=list(effects.keys()),
                            y=list(effects.values()),
                            marker_color=colors,
                            text=[f"{v:.4f}" for v in effects.values()],
                            textposition="outside",
                        ))
                        fig_med.add_hline(y=0, line_dash="solid", line_color="#888", line_width=1)
                        fig_med.update_layout(
                            title="Ringkasan Efek Mediasi",
                            xaxis_title="Jenis Efek", yaxis_title="Nilai Efek",
                            template="plotly_white",
                        )
                        # Export both diagram and bar chart — docx_helpers needs "mediasi_diagram"
                        figs_export["mediasi_diagram"]  = fig_med
                        figs_export["mediasi_efek"]     = fig_med

                elif mod_key == "moderasi":
                    coef_table = mod_data.get("coef_table")
                    if coef_table is not None and hasattr(coef_table, "iterrows"):
                        try:
                            var_col  = coef_table.columns[0]
                            coef_col = next(
                                (c for c in coef_table.columns
                                 if c.lower() in ("β", "b", "coef", "koefisien")),
                                coef_table.columns[1] if len(coef_table.columns) > 1 else None
                            )
                            if coef_col:
                                vals = pd.to_numeric(coef_table[coef_col], errors="coerce")
                                colors = ["#185FA5" if v >= 0 else "#A32D2D" for v in vals.fillna(0)]
                                fig_mod = go.Figure(go.Bar(
                                    x=coef_table[var_col].astype(str),
                                    y=vals,
                                    marker_color=colors,
                                    text=vals.round(4),
                                    textposition="outside",
                                ))
                                fig_mod.add_hline(y=0, line_dash="solid", line_color="#888", line_width=1)
                                fig_mod.update_layout(
                                    title="Koefisien Moderasi / Interaksi",
                                    xaxis_title="Variabel", yaxis_title="Nilai Koefisien",
                                    template="plotly_white",
                                )
                                # docx_helpers uses "moderasi_interaction"
                                figs_export["moderasi_interaction"] = fig_mod
                                figs_export["moderasi_koefisien"]   = fig_mod
                        except Exception:
                            pass

                elif mod_key == "anova":
                    group_stats = _first_valid_df(mod_data.get("group_stats"), mod_data.get("group_means"))
                    if group_stats is not None and hasattr(group_stats, "iterrows"):
                        try:
                            grp_col  = group_stats.columns[0]
                            mean_col = next(
                                (c for c in group_stats.columns
                                 if "mean" in c.lower() or "rata" in c.lower()),
                                group_stats.columns[1] if len(group_stats.columns) > 1 else None
                            )
                            if mean_col:
                                mean_vals = pd.to_numeric(group_stats[mean_col], errors="coerce")
                                fig_anova = go.Figure(go.Bar(
                                    x=group_stats[grp_col].astype(str),
                                    y=mean_vals,
                                    marker_color="#185FA5",
                                    text=mean_vals.round(3),
                                    textposition="outside",
                                ))
                                fig_anova.update_layout(
                                    title="Rata-rata Per Kelompok — ANOVA",
                                    xaxis_title="Kelompok", yaxis_title="Rata-rata",
                                    template="plotly_white",
                                )
                                # docx_helpers uses "anova_bar"
                                figs_export["anova_bar"]          = fig_anova
                                figs_export["anova_group_means"]  = fig_anova
                        except Exception:
                            pass

                    groups_raw = mod_data.get("groups")
                    num_col    = mod_data.get("num_col", "Nilai")
                    if groups_raw and isinstance(groups_raw, dict):
                        try:
                            fig_box = go.Figure()
                            for grp_name, grp_vals in groups_raw.items():
                                fig_box.add_trace(go.Box(
                                    y=list(grp_vals),
                                    name=str(grp_name),
                                    boxpoints="outliers",
                                ))
                            fig_box.update_layout(
                                title=f"Distribusi {num_col} Per Kelompok",
                                yaxis_title=num_col,
                                template="plotly_white",
                            )
                            figs_export["anova_boxplot"] = fig_box
                        except Exception:
                            pass

                elif mod_key == "uji_beda":
                    group_data = _first_valid_df(mod_data.get("group_data"), mod_data.get("groups"))
                    if group_data and isinstance(group_data, dict):
                        try:
                            fig_box = go.Figure()
                            for grp_name, grp_vals in group_data.items():
                                fig_box.add_trace(go.Box(
                                    y=list(grp_vals), name=str(grp_name),
                                    boxpoints="outliers",
                                    marker_color="#185FA5",
                                ))
                            fig_box.update_layout(
                                title="Distribusi Per Kelompok — Uji Beda",
                                yaxis_title="Nilai", template="plotly_white",
                            )
                            figs_export["uji_beda_boxplot"] = fig_box
                        except Exception:
                            pass

                elif mod_key == "outlier":
                    outlier_df_raw = _first_valid_df(mod_data.get("outlier_df"), mod_data.get("result_df"))
                    if outlier_df_raw is not None and hasattr(outlier_df_raw, "__len__"):
                        try:
                            score_col = next(
                                (c for c in outlier_df_raw.columns
                                 if "score" in c.lower() or "zscore" in c.lower()),
                                None
                            )
                            if score_col:
                                is_out_col = next(
                                    (c for c in outlier_df_raw.columns
                                     if "outlier" in c.lower() or "is_out" in c.lower()),
                                    None
                                )
                                colors = (
                                    ["#A32D2D" if v else "#185FA5"
                                     for v in outlier_df_raw[is_out_col]]
                                    if is_out_col else ["#185FA5"] * len(outlier_df_raw)
                                )
                                fig_out = go.Figure(go.Scatter(
                                    x=list(range(len(outlier_df_raw))),
                                    y=outlier_df_raw[score_col],
                                    mode="markers",
                                    marker=dict(color=colors, size=6, opacity=0.7),
                                    name="Z-Score",
                                ))
                                fig_out.add_hline(y=3,  line_dash="dash", line_color="#E24B4A",
                                                  annotation_text="+3σ")
                                fig_out.add_hline(y=-3, line_dash="dash", line_color="#E24B4A",
                                                  annotation_text="-3σ")
                                fig_out.update_layout(
                                    title="Deteksi Outlier — Z-Score",
                                    xaxis_title="Observasi", yaxis_title="Z-Score",
                                    template="plotly_white",
                                )
                                # docx_helpers uses "outlier_plot"
                                figs_export["outlier_plot"]   = fig_out
                                figs_export["outlier_zscore"] = fig_out
                        except Exception:
                            pass
                elif mod_key == "ols_robust":
                    # Bar chart: perbandingan koefisien OLS vs RLM
                    coef_df = mod_data.get("coef_df")
                    if coef_df is not None and hasattr(coef_df, "iterrows"):
                        try:
                            param_col = coef_df.columns[0]
                            ols_col   = next((c for c in coef_df.columns
                                              if "ols" in c.lower()), None)
                            rlm_col   = next((c for c in coef_df.columns
                                              if any(x in c.lower() for x in
                                                     ("rlm", "robust", "huber", "bisquare"))), None)
                            if ols_col and rlm_col:
                                ols_vals = pd.to_numeric(coef_df[ols_col], errors="coerce")
                                rlm_vals = pd.to_numeric(coef_df[rlm_col], errors="coerce")
                                params   = coef_df[param_col].astype(str)
                                fig_comp = go.Figure()
                                fig_comp.add_trace(go.Bar(
                                    name="OLS", x=params, y=ols_vals,
                                    marker_color="#185FA5", opacity=0.7,
                                ))
                                fig_comp.add_trace(go.Bar(
                                    name="RLM", x=params, y=rlm_vals,
                                    marker_color="#E24B4A", opacity=0.7,
                                ))
                                fig_comp.update_layout(
                                    barmode="group",
                                    title="Perbandingan Koefisien OLS vs RLM",
                                    xaxis_title="Parameter", yaxis_title="Nilai Koefisien",
                                    template="plotly_white",
                                )
                                figs_export["robust_coef_comp"] = fig_comp
                        except Exception:
                            pass

                elif mod_key == "ols_wls":
                    # Scatter aktual vs prediksi WLS
                    coef_df = mod_data.get("coef_df")
                    if coef_df is not None and hasattr(coef_df, "iterrows"):
                        try:
                            param_col = coef_df.columns[0]
                            ols_col   = next((c for c in coef_df.columns
                                              if "ols" in c.lower()), None)
                            wls_col   = next((c for c in coef_df.columns
                                              if "wls" in c.lower()), None)
                            if ols_col and wls_col:
                                ols_vals = pd.to_numeric(coef_df[ols_col], errors="coerce")
                                wls_vals = pd.to_numeric(coef_df[wls_col], errors="coerce")
                                params   = coef_df[param_col].astype(str)
                                fig_wls  = go.Figure()
                                fig_wls.add_trace(go.Bar(
                                    name="OLS", x=params, y=ols_vals,
                                    marker_color="#185FA5", opacity=0.7,
                                ))
                                fig_wls.add_trace(go.Bar(
                                    name="WLS", x=params, y=wls_vals,
                                    marker_color="#3B6D11", opacity=0.7,
                                ))
                                fig_wls.update_layout(
                                    barmode="group",
                                    title="Perbandingan Koefisien OLS vs WLS",
                                    xaxis_title="Parameter", yaxis_title="Nilai Koefisien",
                                    template="plotly_white",
                                )
                                figs_export["wls_coef_comp"] = fig_wls
                        except Exception:
                            pass

                elif mod_key == "ols_robust_comparison":
                    # Bar chart RMSE per model
                    comp_df = mod_data.get("comparison_df")
                    if comp_df is not None and hasattr(comp_df, "iterrows"):
                        try:
                            model_col = comp_df.columns[0]
                            rmse_col  = next((c for c in comp_df.columns
                                              if "rmse" in c.lower()), None)
                            if rmse_col:
                                rmse_vals  = pd.to_numeric(comp_df[rmse_col], errors="coerce")
                                best_model = mod_data.get("best_model", "")
                                colors_bar = [
                                    "#3B6D11" if str(m) == best_model else "#185FA5"
                                    for m in comp_df[model_col]
                                ]
                                fig_cmp = go.Figure(go.Bar(
                                    x=comp_df[model_col].astype(str),
                                    y=rmse_vals,
                                    marker_color=colors_bar,
                                    text=rmse_vals.round(4),
                                    textposition="outside",
                                ))
                                fig_cmp.add_annotation(
                                    text=f"★ Terbaik: {best_model}",
                                    xref="paper", yref="paper",
                                    x=0.01, y=0.97, showarrow=False,
                                    font=dict(color="#3B6D11", size=12),
                                )
                                fig_cmp.update_layout(
                                    title="RMSE per Model",
                                    xaxis_title="Model", yaxis_title="RMSE",
                                    template="plotly_white",
                                )
                                figs_export["robust_comparison_bar"] = fig_cmp
                        except Exception:
                            pass

                elif mod_key == "compute":
                    # compute module has no figure — skip silently
                    pass

                elif mod_key == "klaster":
                    # Scatter klaster dari profile data jika tersedia
                    profile_records = mod_data.get("profile_df_records")
                    cols_kl = mod_data.get("cols", [])
                    k_kl    = mod_data.get("k", 3)
                    if profile_records and cols_kl:
                        try:
                            profile_df_kl = pd.DataFrame(profile_records)
                            # Ambil baris per klaster (bukan keseluruhan)
                            kl_rows = profile_df_kl[
                                profile_df_kl.get("Klaster", profile_df_kl.iloc[:, 0]) != "Keseluruhan"
                            ] if "Klaster" in profile_df_kl.columns else profile_df_kl
                            mean_cols_kl = [c for c in profile_df_kl.columns if "(mean)" in c][:6]
                            if mean_cols_kl and "Klaster" in profile_df_kl.columns:
                                kl_plot = kl_rows[["Klaster"] + mean_cols_kl]
                                fig_kl = go.Figure()
                                colors_kl = ["#185FA5", "#3B6D11", "#A32D2D", "#8B5CF6",
                                             "#D97706", "#0891B2", "#DB2777", "#059669"]
                                for mc_i, mc in enumerate(mean_cols_kl):
                                    fig_kl.add_trace(go.Bar(
                                        name=mc.replace(" (mean)", ""),
                                        x=kl_plot["Klaster"],
                                        y=pd.to_numeric(kl_plot[mc], errors="coerce"),
                                        marker_color=colors_kl[mc_i % len(colors_kl)],
                                    ))
                                fig_kl.update_layout(
                                    barmode="group",
                                    title="Profil Rata-rata per Klaster",
                                    xaxis_title="Klaster",
                                    yaxis_title="Nilai Rata-rata",
                                    template="plotly_white",
                                )
                                figs_export["klaster_radar"] = fig_kl
                        except Exception:
                            pass

                elif mod_key == "cfa":
                    # Bar chart factor loadings per konstruk
                    cfa_raw = st.session_state.get("cfa_result", {})
                    loadings_df = cfa_raw.get("loadings_df") if cfa_raw else None
                    factor_map_cfa = cfa_raw.get("factor_map", {}) if cfa_raw else {}
                    if loadings_df is not None and not loadings_df.empty and factor_map_cfa:
                        try:
                            if "Konstruk Laten" in loadings_df.columns and "Loading (λ)" in loadings_df.columns:
                                konstruk_list = list(factor_map_cfa.keys())
                                colors_cfa = ["#185FA5", "#3B6D11", "#A32D2D", "#8B5CF6",
                                              "#D97706", "#0891B2"]
                                fig_cfa = go.Figure()
                                for ki, konstruk in enumerate(konstruk_list):
                                    sub = loadings_df[
                                        loadings_df["Konstruk Laten"].astype(str).str.strip() == konstruk
                                    ]
                                    if sub.empty:
                                        continue
                                    lvals = pd.to_numeric(sub["Loading (λ)"], errors="coerce")
                                    indics = sub["Indikator"].tolist() if "Indikator" in sub.columns else                                              [f"I{j}" for j in range(len(sub))]
                                    bar_colors = [
                                        "#3B6D11" if abs(v) >= 0.70 else
                                        "#185FA5" if abs(v) >= 0.50 else "#E24B4A"
                                        for v in lvals.fillna(0)
                                    ]
                                    fig_cfa.add_trace(go.Bar(
                                        name=konstruk,
                                        x=[f"{konstruk}:{ind}" for ind in indics],
                                        y=lvals.round(3).tolist(),
                                        marker_color=bar_colors,
                                        text=[f"{v:.3f}" for v in lvals.round(3).fillna(0)],
                                        textposition="outside",
                                    ))
                                fig_cfa.add_hline(y=0.50, line_dash="dash",
                                                  line_color="#0c2340", line_width=1)
                                fig_cfa.add_hline(y=0.70, line_dash="dot",
                                                  line_color="#3B6D11", line_width=1)
                                fig_cfa.update_layout(
                                    barmode="group",
                                    title="Factor Loadings (λ) per Konstruk",
                                    xaxis_title="Indikator", yaxis_title="Loading (λ)",
                                    yaxis_range=[0, 1.15],
                                    template="plotly_white",
                                )
                                figs_export["cfa_loadings"] = fig_cfa
                        except Exception:
                            pass

                elif mod_key == "eda":
                    # Bar chart missing values per kolom jika ada
                    try:
                        df_clean = st.session_state.get("df_clean")
                        if df_clean is not None:
                            miss_s = df_clean.isnull().sum()
                            miss_s = miss_s[miss_s > 0].sort_values(ascending=False)
                            if not miss_s.empty:
                                n_rows_eda = len(df_clean)
                                bar_colors_eda = [
                                    "#A32D2D" if v / n_rows_eda > 0.2 else
                                    "#E24B4A" if v / n_rows_eda > 0.05 else "#185FA5"
                                    for v in miss_s.values
                                ]
                                fig_eda = go.Figure(go.Bar(
                                    x=miss_s.index.tolist(),
                                    y=miss_s.values,
                                    marker_color=bar_colors_eda,
                                    text=[f"{v} ({v/n_rows_eda*100:.1f}%)"
                                          for v in miss_s.values],
                                    textposition="outside",
                                ))
                                fig_eda.update_layout(
                                    title="Missing Values per Kolom",
                                    yaxis_title="Jumlah Missing",
                                    template="plotly_white",
                                )
                                figs_export["eda_missing"] = fig_eda
                    except Exception:
                        pass
            prog.progress(38)

            # ── 5. Convert figures → PNG ──────────────────────────────────
            figs_png = {}
            if embed_images:
                status.caption("⏳ Mengonversi grafik ke gambar…")
                for fig_key, fig in figs_export.items():
                    png_bytes = fig_to_png_bytes(fig)
                    if png_bytes:
                        figs_png[fig_key] = png_bytes
                    else:
                        st.toast(f"⚠️ Grafik '{fig_key}' tidak bisa di-embed (install kaleido)", icon="⚠️")
            prog.progress(48)

            # ── 6. AI Narasi ──────────────────────────────────────────────
            ai_texts = {}

            # Ambil cache dari sesi modul sebelumnya
            session_ai_cache = ss_get("ai_cache", {})
            for cache_key, export_key in [
                ("descriptive",  "descriptive"),
                ("normality",    "normality"),
                ("validity",     "validity"),
                ("validity_bar", "validity_bar"),
                ("cronbach",     "cronbach"),
                ("correlation",  "correlation"),
                ("heatmap",      "heatmap"),
                ("scatter",      "scatter"),
                ("plots",        "plots"),
                ("uji_beda",     "uji_beda"),
                ("kelompok",     "kelompok"),
                ("outlier",      "outlier"),
                # modul cache langsung
                ("ols",                 "ols_plus"),
                ("regresi",             "regresi"),
                ("logistik",            "logistik"),
                ("mediasi",             "mediasi"),      # key baru (v4.2+)
                ("mediation",           "mediasi"),      # key lama (backward compat)
                ("moderasi",            "moderasi"),
                ("anova",               "anova"),
                # Patch v4.2 — Regresi Robust & WLS
                ("robust_rlm",          "ols_robust"),
                ("robust_wls",          "ols_wls"),
                ("robust_comparison",   "ols_robust_comparison"),
                # Poin 4 — modul baru
                ("reliabilitas_icc",    "reliabilitas_icc"),
                ("icc",                 "reliabilitas_icc"),
                ("uji_asumsi",          "uji_asumsi"),
                ("asumsi",              "uji_asumsi"),
                ("power_analysis",      "power_analysis"),
                ("power",               "power_analysis"),
                ("compute",             "compute"),
                # Modul baru v4.2
                ("klaster",             "klaster"),
                ("cluster",             "klaster"),
                ("efa",                 "efa"),
                ("cfa",                 "cfa"),
                ("scraping",            "scraping"),
                ("scraping_quality",    "scraping"),
            ]:
                if session_ai_cache.get(cache_key):
                    ai_texts[export_key] = session_ai_cache[cache_key]

            # Scatter metadata
            scatter_sess_init = ss_get("korelasi_scatter", None)
            if scatter_sess_init and isinstance(scatter_sess_init, dict):
                ai_texts.setdefault("_scatter_meta", {
                    "var_x": scatter_sess_init.get("var_x", ""),
                    "var_y": scatter_sess_init.get("var_y", ""),
                    "r_val": scatter_sess_init.get("r_val", ""),
                    "p_val": scatter_sess_init.get("p_val", ""),
                    "n":     scatter_sess_init.get("n", ""),
                })

            if ai_enabled:
                # Deskriptif
                if inc_desc and not desc_df.empty:
                    status.caption("🤖 AI: menganalisis statistik deskriptif…")
                    prog.progress(52)
                    ai_texts["descriptive"] = ai_interpret_descriptive(
                        desc_df, norm_df, anthropic_api_key, ai_provider
                    )

                # Validitas
                if inc_val and val_df is not None and not val_df.empty and alpha_result is not None:
                    status.caption("🤖 AI: menganalisis validitas & reliabilitas…")
                    prog.progress(56)
                    ai_texts["validity"] = ai_interpret_validity_reliability(
                        val_df, alpha_result, r_tab, anthropic_api_key, ai_provider
                    )

                # Korelasi
                if inc_corr and corr_matrix is not None:
                    status.caption("🤖 AI: menganalisis korelasi…")
                    prog.progress(60)
                    ai_texts["correlation"] = ai_interpret_correlation(
                        corr_matrix, anthropic_api_key, ai_provider
                    )
                    status.caption("🤖 AI: menginterpretasi heatmap…")
                    ai_texts["heatmap"] = ai_interpret_heatmap(
                        corr_matrix, anthropic_api_key, ai_provider
                    )
                    # Scatter AI
                    scatter_sess = ss_get("korelasi_scatter", None)
                    if scatter_sess and isinstance(scatter_sess, dict):
                        ai_texts["_scatter_meta"] = {
                            "var_x": scatter_sess.get("var_x", ""),
                            "var_y": scatter_sess.get("var_y", ""),
                            "r_val": scatter_sess.get("r_val", ""),
                            "p_val": scatter_sess.get("p_val", ""),
                            "n":     scatter_sess.get("n", ""),
                        }
                        cached_scatter = ss_get("ai_cache", {}).get("scatter")
                        if cached_scatter:
                            ai_texts["scatter"] = cached_scatter
                        else:
                            status.caption("🤖 AI: menginterpretasi scatter plot…")
                            scatter_stats = {
                                "var_x":      scatter_sess.get("var_x", ""),
                                "var_y":      scatter_sess.get("var_y", ""),
                                "n":          scatter_sess.get("n", 0),
                                "r":          scatter_sess.get("r_val", 0),
                                "p":          scatter_sess.get("p_val", 1),
                                "r2":         scatter_sess.get("r_val", 0) ** 2,
                                "signifikan": scatter_sess.get("p_val", 1) < 0.05,
                            }
                            ai_texts["scatter"] = ai_interpret_scatter(
                                scatter_stats, anthropic_api_key, ai_provider
                            )

                # ── AI per modul lanjutan ─────────────────────────────────
                n_active_mods = sum(1 for v in module_checkboxes.values() if v)
                prog_per_mod  = max(1, 20 // max(n_active_mods, 1))

                for mod_key, include in module_checkboxes.items():
                    if not include:
                        continue
                    mod_data  = session_results[mod_key]["data"]
                    mod_label = session_results[mod_key]["label"]

                    # Interpretasi naratif
                    if not ai_texts.get(mod_key):
                        status.caption(f"🤖 AI: interpretasi {mod_label}…")
                        try:
                            full_prompt = _build_module_ai_prompt(mod_key, mod_data, mod_label)
                            ai_texts[mod_key] = ai_raw_interpret(
                                full_prompt, anthropic_api_key, ai_provider
                            )
                        except Exception:
                            ai_texts[mod_key] = ""

                    # Persamaan model (opsional)
                    if inc_model_eq:
                        eq_key = f"model_equation_{mod_key}"
                        if mod_key in ("regresi", "ols_plus", "logistik",
                                       "mediasi", "moderasi", "anova", "sem"):
                            status.caption(f"📐 AI: generate persamaan model {mod_label}…")
                            try:
                                ai_texts[eq_key] = ai_generate_model_equation(
                                    mod_key, mod_data,
                                    anthropic_api_key, ai_provider
                                )
                            except Exception:
                                ai_texts[eq_key] = ""

                    prog.progress(min(80, 65 + prog_per_mod))

                # ── AI Regresi Robust & WLS (dedicated, pakai fungsi spesifik) ──
                for rob_ss_key, rob_mod_key, rob_ai_fn, rob_label in [
                    ("robust_result",           "ols_robust",
                     lambda d: ai_interpret_robust(
                         d.get("dep_var","Y"), d.get("ind_vars",[]),
                         d.get("coef_df", pd.DataFrame()),
                         d.get("n_changed", 0), d.get("n_low_weight", 0),
                         d.get("n_obs", 0), d.get("estimator","Huber-M"),
                         anthropic_api_key, ai_provider,
                     ), "Regresi Robust"),
                    ("wls_result",              "ols_wls",
                     lambda d: ai_interpret_wls_robust(
                         d.get("dep_var","Y"), d.get("ind_vars",[]),
                         d.get("coef_df", pd.DataFrame()),
                         d.get("ols_glejser_p", 1.0), d.get("wls_glejser_p", 1.0),
                         d.get("ols_rmse", 0.0), d.get("wls_rmse", 0.0),
                         d.get("weight_method","1/|ε|"),
                         d.get("n_obs", 0),
                         anthropic_api_key, ai_provider,
                     ), "WLS"),
                    ("robust_comparison_result","ols_robust_comparison",
                     lambda d: ai_interpret_model_comparison(
                         d.get("comparison_df", pd.DataFrame()),
                         d.get("best_model","OLS"),
                         d.get("dep_var","Y"),
                         anthropic_api_key, ai_provider,
                     ), "Perbandingan Model Robust"),
                ]:
                    rob_data = st.session_state.get(rob_ss_key)
                    if (rob_data and isinstance(rob_data, dict)
                            and not ai_texts.get(rob_mod_key)):
                        status.caption(f"🤖 AI: interpretasi {rob_label}…")
                        try:
                            ai_texts[rob_mod_key] = rob_ai_fn(rob_data)
                        except Exception:
                            ai_texts[rob_mod_key] = ""

                prog.progress(82)

                # Kesimpulan
                if inc_ai_kes:
                    status.caption("🤖 AI: menyusun kesimpulan & rekomendasi…")
                    active_modules = [
                        session_results[k]["label"]
                        for k, v in module_checkboxes.items() if v
                    ]
                    df_info = {
                        "rows":           report.get("rows_after_clean", len(df)),
                        "cols":           len(cols),
                        "active_modules": active_modules,
                        "report_style":   report_style,
                        "data_type":      data_type,
                    }
                    ai_texts["kesimpulan"] = ai_generate_kesimpulan(
                        df_info, desc_df, norm_df, val_df, alpha_result,
                        corr_matrix, anthropic_api_key, ai_provider,
                    )

            prog.progress(88)
            # ── Referensi APA ─────────────────────────────────────────────────────────────
            apa_refs = generate_apa_references(
                inc_desc, inc_val, inc_corr,
                module_checkboxes, report_style
            )
            if apa_refs:
                ai_texts["apa_references"] = apa_refs
                render_apa_preview(apa_refs)

            # ── 7. Kumpulkan modul yang dicentang ─────────────────────────
            selected_session = {
                k: session_results[k]
                for k, v in module_checkboxes.items() if v
            }

            # ── 8. Generate dokumen ───────────────────────────────────────
            status.caption("⏳ Menyusun dokumen final…")
            if output_format == "Word (.docx)":
                doc_buf = generate_pro_docx(
                    df, report, desc_df, norm_df, val_df, alpha_result,
                    corr_matrix, cols, r_tab,
                    figs=figs_export,
                    figs_png=figs_png,
                    ai_texts=ai_texts,
                    report_style=report_style,
                    data_type=data_type,
                    session_results=selected_session,
                    user_name=ctx.get("user_name", ""),
                )
                prog.progress(100)
                status.empty()
                st.success("✅ Laporan berhasil dibuat!")
                if not is_pro:
                    consume_export_quota()
                    st.caption("📄 Kuota laporan gratis hari ini telah digunakan.")

                fname = f"Laporan_RuangStatistika_{report_style.split()[0]}.docx"
                st.download_button(
                    label="⬇️ Download Laporan .docx",
                    data=doc_buf,
                    file_name=fname,
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                )

            else:  # Markdown
                md_content = generate_markdown_report(
                    df, report, desc_df, norm_df, val_df, alpha_result,
                    corr_matrix, cols, r_tab,
                    ai_texts=ai_texts,
                    report_style=report_style,
                    data_type=data_type,
                    session_results=selected_session,
                    user_name=ctx.get("user_name", ""),
                )
                prog.progress(100)
                status.empty()
                st.success("✅ Laporan Markdown berhasil dibuat!")
                if not is_pro:
                    consume_export_quota()
                    st.caption("📄 Kuota laporan gratis hari ini telah digunakan.")

                fname = f"Laporan_RuangStatistika_{report_style.split()[0]}.md"
                st.download_button(
                    label="⬇️ Download Laporan .md",
                    data=md_content.encode("utf-8"),
                    file_name=fname,
                    mime="text/markdown",
                    use_container_width=True,
                )
                with st.expander("👁️ Preview Markdown"):
                    st.markdown(md_content)

        # ── Ringkasan konten ──────────────────────────────────────────────
        active_mod_labels = [
            session_results[k]["label"]
            for k, v in module_checkboxes.items() if v
        ]
        active_str = "".join(
            f"• {lbl}<br/>" for lbl in active_mod_labels
        ) if active_mod_labels else "• (tidak ada modul lanjutan dipilih)<br/>"

        img_info = (
            f"• {len(figs_png)} grafik tertanam<br/>"
            if embed_images and figs_png else
            "• Grafik tidak disertakan (install kaleido)<br/>"
        )

        eq_info = ""
        eq_count = sum(1 for k in ai_texts if k.startswith("model_equation_"))
        if eq_count:
            eq_info = f"• 📐 {eq_count} persamaan model AI-generated<br/>"

        st.markdown(f"""
        <div class="rs-narasi">
            📋 <b>Laporan mencakup:</b><br/>
            • Gaya format: <b>{report_style}</b> | Tipe data: <b>{data_type.split('(')[0].strip()}</b><br/>
            • Ringkasan data ({report.get('rows_after_clean', len(df))} baris, {len(cols)} variabel)<br/>
            {'• Statistik deskriptif + normalitas<br/>' if inc_desc else ''}
            {'• Validitas Pearson + Cronbach Alpha<br/>' if inc_val else ''}
            {'• Matriks korelasi + heatmap<br/>' if inc_corr else ''}
            {active_str}
            {img_info}
            {eq_info}
            {'• 🤖 AI: ' + ai_provider.split("(")[0].strip() + '<br/>' if ai_enabled and ai_texts else ''}
            {'• 🤖 Kesimpulan & Rekomendasi AI<br/>' if ai_texts.get('kesimpulan') else ''}
            • Format output: {output_format}
        </div>
        """, unsafe_allow_html=True)
