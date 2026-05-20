"""
utils/_export_normalize.py — Ruang Statistika v4.8
Normalisasi raw session_state result ke format standar untuk docx/markdown.
Satu blok if-elif per modul — pastikan key konsisten dengan yang ditulis modul.

Menambah modul baru:
  Tambahkan blok elif di _normalize_mod_data() dan pastikan
  key yang diakses sesuai dengan session_state yang ditulis modul tersebut.

Diimport oleh: utils/export.py
"""

import pandas as pd
import numpy as np
import streamlit as st  # diperlukan untuk bridge ai_cache & session_state tertentu


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
        if not raw.get("ai_text"):
            ai_t = st.session_state.get("ai_cache", {}).get("cfa", "")
            if ai_t:
                out["ai_text"] = ai_t


    elif mod_key == "regresi":
        # alias dari ols_plus — normalisasi minimal
        model = raw.get("model")
        if model is not None and raw.get("coef_table") is None:
            try:
                out["coef_table"] = pd.DataFrame({
                    "Parameter": model.params.index.tolist(),
                    "β (Koefisien)": model.params.values.round(4).tolist(),
                    "Std. Error": model.bse.values.round(4).tolist(),
                    "t-hitung": model.tvalues.values.round(4).tolist(),
                    "p-value": model.pvalues.values.round(4).tolist(),
                })
                out["r2"] = float(model.rsquared)
                out["adj_r2"] = float(model.rsquared_adj)
                out["f_pvalue"] = float(model.f_pvalue)
            except Exception:
                pass

    elif mod_key == "sem":
        # normalisasi fit indices dan path estimates
        for df_field in ("fit_indices", "path_estimates", "loadings"):
            df_val = raw.get(df_field)
            if df_val is not None and hasattr(df_val, "to_dict"):
                try:
                    out[df_field + "_records"] = df_val.to_dict("records")
                    out[df_field + "_cols"] = df_val.columns.tolist()
                except Exception:
                    pass
        for field in ("model_syntax", "n_obs", "estimator", "ai_text"):
            if raw.get(field) is not None and out.get(field) is None:
                out[field] = raw[field]

    elif mod_key == "power_analysis":
        for field in ("test_type", "effect_size", "alpha", "power", "n_total", "n_per_group", "ai_text"):
            if raw.get(field) is not None and out.get(field) is None:
                out[field] = raw[field]

    return out


