"""
utils/_docx_renderers.py — Ruang Statistika v4.8
Satu fungsi _render_XXX per modul analisis — mengisi bab hasil di laporan .docx.
Juga berisi _MODULE_RENDERERS (dict routing mod_key → fungsi renderer).

Menambah modul baru:
  1. Buat def _render_namamodul(doc, pr, data, figs_png, fig_no, bab, ai_texts)
  2. Daftarkan di _MODULE_RENDERERS di bawah

Diimport oleh: utils/docx_helpers.py
JANGAN diimport langsung dari modul lain — gunakan docx_helpers.py.
"""

from utils._docx_primitives import (
    StyleProfile, _add_para, _add_heading, _add_ai_narasi,
    _add_model_equation_box, _embed_image, _style_table,
    _tbl_caption, _fmt_val, _clean_ai_text,
)
from utils._docx_narasi import _fallback_narasi
from utils._export_normalize import _first_valid_df
import pandas as pd
import numpy as np

def _get_eq(analysis_type, data, ai_texts):
    return (ai_texts or {}).get(f"model_equation_{analysis_type}", "")


def _render_regresi(doc, pr, data, figs_png, fig_no, bab, ai_texts):
    _add_heading(doc, pr, f"{bab}. Analisis Regresi Linier", level=1)
    dep_var  = data.get("y","Y")
    ind_vars = data.get("x",[])
    _add_para(doc, pr,
        f"Analisis regresi linier dilakukan untuk menguji pengaruh "
        f"{', '.join(ind_vars)} terhadap {dep_var}.",
        first_indent=True, is_last_in_block=True)

    r2, adj_r2, f_pvalue, rmse = (data.get(k) for k in ("r2","adj_r2","f_pvalue","rmse"))
    if any(v is not None for v in [r2, adj_r2, f_pvalue]):
        fd = {}
        if r2       is not None: fd["R\u00b2"]          = round(r2, 4)
        if adj_r2   is not None: fd["R\u00b2 Adjusted"] = round(adj_r2, 4)
        if f_pvalue is not None: fd["F p-value"]        = round(f_pvalue, 4)
        if rmse     is not None: fd["RMSE"]              = round(rmse, 4)
        _style_table(doc, pd.DataFrame([fd]), pr, f"Tabel {bab}.1. Ringkasan Model Regresi")

    coef_df = data.get("coef_table")
    if coef_df is not None and not coef_df.empty:
        _style_table(doc, coef_df, pr, f"Tabel {bab}.2. Koefisien Regresi")

    for ks, ls in (("_scatter","Scatter Plot Aktual vs Prediksi"),
                   ("_residual","Plot Residual"),("_koefisien","Koefisien Regresi")):
        if figs_png.get(f"regresi{ks}"):
            _embed_image(doc, pr, figs_png[f"regresi{ks}"], f"Gambar {fig_no}. {ls}")
            fig_no += 1

    if _get_eq("regresi", data, ai_texts):
        _add_model_equation_box(doc, pr, _get_eq("regresi", data, ai_texts))

    _add_ai_narasi(doc, pr,
                   (ai_texts or {}).get("regresi") or (ai_texts or {}).get("ols_plus",""),
                   "Interpretasi Regresi Linier", mod_key="regresi", data=data)
    return fig_no


def _render_ols_plus(doc, pr, data, figs_png, fig_no, bab, ai_texts):
    _add_heading(doc, pr, f"{bab}. Regresi OLS (Diagnostik Lengkap)", level=1)
    _add_para(doc, pr,
        f"Regresi OLS dengan uji asumsi klasik untuk model "
        f"{data.get('y','Y')} ~ {', '.join(data.get('x',[]))}.",
        first_indent=True, is_last_in_block=True)

    coef_df = data.get("coef_table")
    if coef_df is not None and not coef_df.empty:
        _style_table(doc, coef_df, pr, f"Tabel {bab}.1. Koefisien Regresi OLS")

    diag = {k: round(v,4) for k,v in {
        "Durbin-Watson":  data.get("durbin_watson"),
        "VIF Maksimum":   data.get("vif_max"),
        "White Test p":   data.get("white_pvalue"),
        "Shapiro Res. p": data.get("shapiro_residual_p"),
    }.items() if v is not None}
    if diag:
        _style_table(doc, pd.DataFrame([diag]), pr, f"Tabel {bab}.2. Statistik Uji Asumsi Klasik")

    for ks, ls in (("_scatter","Scatter Aktual vs Prediksi"),
                   ("_residual","Plot Residual OLS"),("_koefisien","Koefisien OLS")):
        if figs_png.get(f"ols_plus{ks}"):
            _embed_image(doc, pr, figs_png[f"ols_plus{ks}"], f"Gambar {fig_no}. {ls}")
            fig_no += 1

    if _get_eq("ols_plus", data, ai_texts):
        _add_model_equation_box(doc, pr, _get_eq("ols_plus", data, ai_texts))

    _add_ai_narasi(doc, pr, (ai_texts or {}).get("ols_plus",""),
                   "Interpretasi OLS", mod_key="ols_plus", data=data)
    return fig_no


def _render_logistik(doc, pr, data, figs_png, fig_no, bab, ai_texts):
    _add_heading(doc, pr, f"{bab}. Regresi Logistik", level=1)
    _add_para(doc, pr,
        f"Regresi logistik biner untuk memprediksi {data.get('y','Y')} "
        f"berdasarkan {', '.join(data.get('x',[]))}.",
        first_indent=True, is_last_in_block=True)

    fit = {k: round(v,4) for k,v in {
        "AUC": data.get("auc"), "Pseudo R\u00b2": data.get("pseudo_r2"),
        "AIC": data.get("aic"), "BIC": data.get("bic"),
    }.items() if v is not None}
    if fit:
        _style_table(doc, pd.DataFrame([fit]), pr, f"Tabel {bab}.1. Kebaikan Model")

    coef_df = _first_valid_df(data.get("coef_table"), data.get("odds_df"))
    if coef_df is not None and not coef_df.empty:
        _style_table(doc, coef_df, pr, f"Tabel {bab}.2. Koefisien dan Odds Ratio")

    cr = data.get("cr", {})
    if cr:
        try:
            cr_df = pd.DataFrame({
                "Kelas":     ["0","1","Macro avg","Weighted avg"],
                "Precision": [round(cr[k]["precision"],4) for k in ("0","1","macro avg","weighted avg")],
                "Recall":    [round(cr[k]["recall"],4)    for k in ("0","1","macro avg","weighted avg")],
                "F1":        [round(cr[k]["f1-score"],4)  for k in ("0","1","macro avg","weighted avg")],
            })
            _style_table(doc, cr_df, pr, f"Tabel {bab}.3. Laporan Klasifikasi")
        except Exception:
            pass

    for fk, ls in (("logistik_odds_ratio","Odds Ratio"),("logistik_roc","Kurva ROC")):
        if figs_png.get(fk):
            _embed_image(doc, pr, figs_png[fk], f"Gambar {fig_no}. {ls}"); fig_no += 1

    if _get_eq("logistik", data, ai_texts):
        _add_model_equation_box(doc, pr, _get_eq("logistik", data, ai_texts))

    _add_ai_narasi(doc, pr, (ai_texts or {}).get("logistik",""),
                   "Interpretasi Regresi Logistik", mod_key="logistik", data=data)
    return fig_no


def _render_mediasi(doc, pr, data, figs_png, fig_no, bab, ai_texts):
    _add_heading(doc, pr, f"{bab}. Analisis Mediasi", level=1)
    x, m, y = data.get("x","X"), data.get("m","M"), data.get("y","Y")
    _add_para(doc, pr,
        f"Analisis mediasi menguji peran {m} sebagai mediator hubungan {x} \u2192 {y} "
        f"menggunakan prosedur Bootstrap (Preacher & Hayes, 2008).",
        first_indent=True, is_last_in_block=True)

    path_df = data.get("path_table")
    if path_df is not None and not path_df.empty:
        _style_table(doc, path_df, pr, f"Tabel {bab}.1. Koefisien Jalur Mediasi")

    boot_ci = data.get("bootstrap_ci")
    if boot_ci:
        ci_d = {"CI Bawah (95%)": round(boot_ci[0],4), "CI Atas (95%)": round(boot_ci[1],4)}
        if data.get("indirect_effect") is not None:
            ci_d["Efek Tidak Langsung"] = round(data["indirect_effect"],4)
        _style_table(doc, pd.DataFrame([ci_d]), pr, f"Tabel {bab}.2. Bootstrap CI")

    # Fix 4: mediasi_diagram bisa berupa bar chart efek (SVG path diagram tidak bisa jadi PNG)
    if figs_png.get("mediasi_diagram"):
        _embed_image(doc, pr, figs_png["mediasi_diagram"],
                     f"Gambar {fig_no}. Diagram Jalur Mediasi"); fig_no += 1
    elif figs_png.get("mediasi_efek"):
        _embed_image(doc, pr, figs_png["mediasi_efek"],
                     f"Gambar {fig_no}. Ringkasan Efek Mediasi (Indirect, Direct, Total)"); fig_no += 1

    if _get_eq("mediasi", data, ai_texts):
        _add_model_equation_box(doc, pr, _get_eq("mediasi", data, ai_texts))

    _add_ai_narasi(doc, pr, (ai_texts or {}).get("mediasi",""),
                   "Interpretasi Mediasi", mod_key="mediasi", data=data)
    return fig_no


def _render_moderasi(doc, pr, data, figs_png, fig_no, bab, ai_texts):
    _add_heading(doc, pr, f"{bab}. Analisis Moderasi", level=1)
    x, z, y = data.get("x","X"), data.get("z","Z"), data.get("y","Y")
    _add_para(doc, pr,
        f"Analisis moderasi menguji apakah {z} memoderasi hubungan {x} \u2192 {y}.",
        first_indent=True, is_last_in_block=True)

    coef_df = data.get("coef_table")
    if coef_df is not None and not coef_df.empty:
        _style_table(doc, coef_df, pr, f"Tabel {bab}.1. Koefisien Moderasi")

    r2, adj_r2 = data.get("r2"), data.get("adj_r2")
    if r2 is not None or adj_r2 is not None:
        fd = {}
        if r2:     fd["R\u00b2"]          = round(r2, 4)
        if adj_r2: fd["R\u00b2 Adjusted"] = round(adj_r2, 4)
        _style_table(doc, pd.DataFrame([fd]), pr, f"Tabel {bab}.2. Kebaikan Model Moderasi")

    if figs_png.get("moderasi_interaction"):
        _embed_image(doc, pr, figs_png["moderasi_interaction"],
                     f"Gambar {fig_no}. Plot Interaksi Moderasi"); fig_no += 1

    if _get_eq("moderasi", data, ai_texts):
        _add_model_equation_box(doc, pr, _get_eq("moderasi", data, ai_texts))

    _add_ai_narasi(doc, pr, (ai_texts or {}).get("moderasi",""),
                   "Interpretasi Moderasi", mod_key="moderasi", data=data)
    return fig_no


def _render_anova(doc, pr, data, figs_png, fig_no, bab, ai_texts):
    _add_heading(doc, pr, f"{bab}. Analisis Varians (ANOVA)", level=1)
    _add_para(doc, pr,
        "Uji ANOVA satu arah dilakukan untuk membandingkan rata-rata antar kelompok.",
        first_indent=True, is_last_in_block=True)

    if (df_ := data.get("anova_table")) is not None and not df_.empty:
        _style_table(doc, df_, pr, f"Tabel {bab}.1. Tabel ANOVA")
    if (df_ := data.get("posthoc_table")) is not None and not df_.empty:
        _style_table(doc, df_, pr, f"Tabel {bab}.2. Uji Post-Hoc")
    if data.get("eta_squared") is not None:
        _style_table(doc,
            pd.DataFrame([{"Eta Squared (\u03b7\u00b2)": round(data["eta_squared"],4)}]),
            pr, f"Tabel {bab}.3. Ukuran Efek")

    for fk, ls in (("anova_boxplot","Boxplot ANOVA per Kelompok"),
                   ("anova_bar","Bar Chart Rata-rata per Kelompok")):
        if figs_png.get(fk):
            _embed_image(doc, pr, figs_png[fk], f"Gambar {fig_no}. {ls}"); fig_no += 1

    if _get_eq("anova", data, ai_texts):
        _add_model_equation_box(doc, pr, _get_eq("anova", data, ai_texts))

    _add_ai_narasi(doc, pr, (ai_texts or {}).get("anova",""),
                   "Interpretasi ANOVA", mod_key="anova", data=data)
    return fig_no


def _render_uji_beda(doc, pr, data, figs_png, fig_no, bab, ai_texts):
    _add_heading(doc, pr, f"{bab}. Uji Beda", level=1)
    g1, g2 = data.get("g1_name","Kelompok 1"), data.get("g2_name","Kelompok 2")
    _add_para(doc, pr,
        f"Uji beda ({data.get('uji_type','t-test')}) dilakukan untuk membandingkan {g1} dan {g2}.",
        first_indent=True, is_last_in_block=True)

    res = {label: round(float(data[k]),4) for k,label in [
        ("statistic","Statistik Uji"),("p_value","p-value"),
        ("effect_size","Effect Size"),("g1_mean",f"Rata-rata {g1}"),
        ("g2_mean",f"Rata-rata {g2}"),
    ] if data.get(k) is not None}
    if res:
        _style_table(doc, pd.DataFrame([res]), pr, f"Tabel {bab}.1. Hasil Uji Beda")

    # Fix 5: embed boxplot jika tersedia
    for fk, ls in (("uji_beda_boxplot", "Boxplot Distribusi Per Kelompok"),
                   ("uji_beda_violin",  "Violin Plot Distribusi Per Kelompok")):
        if figs_png.get(fk):
            _embed_image(doc, pr, figs_png[fk], f"Gambar {fig_no}. {ls}")
            fig_no += 1

    _add_ai_narasi(doc, pr, (ai_texts or {}).get("uji_beda",""),
                   "Interpretasi Uji Beda", mod_key="uji_beda", data=data)
    return fig_no


def _render_outlier(doc, pr, data, figs_png, fig_no, bab, ai_texts):
    _add_heading(doc, pr, f"{bab}. Deteksi Outlier", level=1)
    if (df_ := data.get("outlier_table")) is not None and not df_.empty:
        _style_table(doc, df_, pr, f"Tabel {bab}.1. Data Outlier Terdeteksi")
    if figs_png.get("outlier_plot"):
        _embed_image(doc, pr, figs_png["outlier_plot"],
                     f"Gambar {fig_no}. Visualisasi Outlier"); fig_no += 1
    _add_ai_narasi(doc, pr, (ai_texts or {}).get("outlier",""),
                   "Interpretasi Outlier", mod_key="outlier", data=data)
    return fig_no


def _render_sem(doc, pr, data, figs_png, fig_no, bab, ai_texts):
    _add_heading(doc, pr, f"{bab}. Structural Equation Modeling (SEM) & CFA", level=1)
    _add_para(doc, pr,
        "Analisis SEM dan CFA dilakukan untuk menguji model pengukuran dan struktural "
        "(Hair et al., 2010).",
        first_indent=True, is_last_in_block=True)

    if (df_ := data.get("fit_indices")) is not None and not df_.empty:
        _style_table(doc, df_, pr, f"Tabel {bab}.1. Indeks Kecocokan Model")
        acuan = pd.DataFrame({
            "Indeks":    ["CFI","TLI","RMSEA","SRMR","\u03c7\u00b2/df"],
            "Kriteria":  ["\u2265 .90","\u2265 .90","\u2264 .08","\u2264 .08","\u2264 2.00"],
            "Referensi": ["Hair et al. (2010)"]*5,
        })
        _style_table(doc, acuan, pr, f"Tabel {bab}.1a. Kriteria Kecocokan Model")

    if (df_ := data.get("loadings")) is not None and not df_.empty:
        _style_table(doc, df_, pr, f"Tabel {bab}.2. Factor Loadings (CFA)")
    if (df_ := data.get("path_estimates")) is not None and not df_.empty:
        _style_table(doc, df_, pr, f"Tabel {bab}.3. Estimasi Jalur Struktural")

    if figs_png.get("sem_diagram"):
        _embed_image(doc, pr, figs_png["sem_diagram"],
                     f"Gambar {fig_no}. Diagram Jalur SEM"); fig_no += 1

    if _get_eq("sem", data, ai_texts):
        _add_model_equation_box(doc, pr, _get_eq("sem", data, ai_texts))

    _add_ai_narasi(doc, pr, (ai_texts or {}).get("sem",""),
                   "Interpretasi SEM & CFA", mod_key="sem", data=data)
    return fig_no


def _render_kelompok(doc, pr, data, figs_png, fig_no, bab, ai_texts):
    _add_heading(doc, pr, f"{bab}. Analisis Kelompok", level=1)
    cat, num = data.get("cat","Kelompok"), data.get("num","Variabel Numerik")
    _add_para(doc, pr,
        f"Analisis perbandingan variabel '{num}' berdasarkan kelompok '{cat}'.",
        first_indent=True, is_last_in_block=True)

    if (df_ := data.get("group_stats")) is not None and not df_.empty:
        _style_table(doc, df_, pr, f"Tabel {bab}.1. Statistik per Kelompok")

    res = {label: round(float(data[k]),4) for k,label in [
        ("f_stat","F-statistik"),("p_value","p-value"),
    ] if data.get(k) is not None}
    if res:
        _style_table(doc, pd.DataFrame([res]), pr, f"Tabel {bab}.2. Hasil ANOVA Kelompok")

    if figs_png.get("kelompok_plot"):
        _embed_image(doc, pr, figs_png["kelompok_plot"],
                     f"Gambar {fig_no}. Visualisasi Kelompok"); fig_no += 1

    _add_ai_narasi(doc, pr, (ai_texts or {}).get("kelompok",""),
                   "Interpretasi Kelompok", mod_key="kelompok", data=data)
    return fig_no



def _render_efa(doc, pr, data, figs_png, fig_no, bab, ai_texts):
    """Fix 9: EFA renderer — sebelumnya tidak ada di _MODULE_RENDERERS."""
    _add_heading(doc, pr, f"{bab}. Analisis Faktor Eksploratori (EFA)", level=1)
    _add_para(doc, pr,
        "Analisis Faktor Eksploratori (EFA) dilakukan untuk mengidentifikasi struktur "
        "laten yang mendasari item-item pengukuran (Hair et al., 2010).",
        first_indent=True, is_last_in_block=True)

    # KMO & Bartlett
    kmo    = data.get("kmo")
    kmo_lbl= data.get("kmo_label", "")
    bart_p = data.get("bartlett_p")
    if kmo is not None or bart_p is not None:
        fit_d = {}
        if kmo     is not None: fit_d["KMO"]                       = round(float(kmo), 4)
        if kmo_lbl:             fit_d["Kategori KMO"]              = kmo_lbl
        if bart_p  is not None: fit_d["Bartlett p-value"]          = round(float(bart_p), 4)
        n_fac = data.get("n_factors")
        rot   = data.get("rotation", "")
        tot_v = data.get("total_var")
        if n_fac  is not None: fit_d["Jumlah Faktor"]              = int(n_fac)
        if rot:                fit_d["Rotasi"]                      = rot
        if tot_v  is not None: fit_d["Total Variance Explained (%)"] = round(float(tot_v), 2)
        _style_table(doc, pd.DataFrame([fit_d]), pr,
                     f"Tabel {bab}.1. Hasil Uji Kelayakan Data EFA")

    # Variance explained per factor
    var_df = data.get("variance_df")
    if var_df is not None and not var_df.empty:
        _style_table(doc, var_df, pr, f"Tabel {bab}.2. Variansi yang Dijelaskan per Faktor")

    # Factor loadings
    load_df = data.get("loading_df")
    if load_df is not None and not load_df.empty:
        _style_table(doc, load_df, pr, f"Tabel {bab}.3. Factor Loadings")

    # Scree plot / diagram
    for fk, ls in (("efa_scree",   "Scree Plot"),
                   ("efa_loading", "Heatmap Factor Loadings")):
        if figs_png.get(fk):
            _embed_image(doc, pr, figs_png[fk], f"Gambar {fig_no}. {ls}")
            fig_no += 1

    # AI narasi — ambil dari ai_text field dalam data jika ada
    narasi = (ai_texts or {}).get("efa", "") or data.get("ai_text", "")
    _add_ai_narasi(doc, pr, narasi, "Interpretasi EFA", mod_key="efa", data=data)
    return fig_no

# =============================================================================
# RENDERER BARU — Poin 3: ols_robust, ols_wls, ols_robust_comparison,
#                          compute, reliabilitas_icc, uji_asumsi
# =============================================================================

def _render_ols_robust(doc, pr, data, figs_png, fig_no, bab, ai_texts):
    """Renderer untuk Regresi Robust (RLM Huber-M / Bisquare)."""
    _add_heading(doc, pr, f"{bab}. Regresi Robust (RLM)", level=1)
    dep_var   = data.get("dep_var", "Y")
    ind_vars  = data.get("ind_vars", [])
    estimator = data.get("estimator", "Huber-M")
    n_obs     = data.get("n_obs", "?")
    n_low     = data.get("n_low_weight", 0)
    n_changed = data.get("n_changed", 0)

    _add_para(doc, pr,
        f"Regresi Robust ({estimator}) dilakukan untuk memodelkan {dep_var} "
        f"berdasarkan {', '.join(ind_vars) if ind_vars else 'variabel prediktor'} "
        f"(N = {n_obs}). Estimator robust mereduksi pengaruh outlier dan leverage "
        f"points dengan memberi bobot rendah pada observasi bermasalah "
        f"(Huber, 1973; Greene, 2012).",
        first_indent=True, is_last_in_block=True)

    # Ringkasan metrik
    summary = {}
    if n_obs:          summary["N Observasi"]           = n_obs
    if estimator:      summary["Estimator"]              = estimator
    if n_low is not None: summary["Obs. Downweighted (<0.5)"] = n_low
    if n_changed is not None: summary["Koef. Berubah >10%"]   = n_changed
    ols_rmse = data.get("ols_rmse")
    rlm_rmse = data.get("rlm_rmse")
    if ols_rmse is not None: summary["RMSE OLS"]  = round(float(ols_rmse), 4)
    if rlm_rmse is not None: summary["RMSE RLM"]  = round(float(rlm_rmse), 4)
    if summary:
        _style_table(doc, pd.DataFrame([summary]), pr,
                     f"Tabel {bab}.1. Ringkasan Model Regresi Robust")

    # Tabel perbandingan koefisien OLS vs RLM
    coef_df = data.get("coef_df")
    if coef_df is not None and not coef_df.empty:
        _style_table(doc, coef_df, pr,
                     f"Tabel {bab}.2. Perbandingan Koefisien OLS vs {estimator}")

    # Figures
    for fk, ls in (("robust_weights",   "Robust Weights vs Residual"),
                   ("robust_coef_comp", "Perbandingan Koefisien OLS vs RLM")):
        if figs_png.get(fk):
            _embed_image(doc, pr, figs_png[fk], f"Gambar {fig_no}. {ls}")
            fig_no += 1

    _add_ai_narasi(doc, pr, (ai_texts or {}).get("ols_robust", ""),
                   "Interpretasi Regresi Robust", mod_key="ols_robust", data=data)
    return fig_no


def _render_ols_wls(doc, pr, data, figs_png, fig_no, bab, ai_texts):
    """Renderer untuk Weighted Least Squares (WLS)."""
    _add_heading(doc, pr, f"{bab}. Weighted Least Squares (WLS)", level=1)
    dep_var       = data.get("dep_var", "Y")
    ind_vars      = data.get("ind_vars", [])
    weight_method = data.get("weight_method", "1/|ε|")
    n_obs         = data.get("n_obs", "?")

    _add_para(doc, pr,
        f"WLS dilakukan untuk mengatasi heteroskedastisitas pada model "
        f"{dep_var} ~ {', '.join(ind_vars) if ind_vars else 'prediktor'} "
        f"menggunakan pembobotan {weight_method} (Greene, 2012).",
        first_indent=True, is_last_in_block=True)

    # Perbandingan metrik
    summary = {}
    r2      = data.get("r2")
    adj_r2  = data.get("adj_r2")
    ols_g   = data.get("ols_glejser_p")
    wls_g   = data.get("wls_glejser_p")
    ols_r   = data.get("ols_rmse")
    wls_r   = data.get("wls_rmse")
    n_ch    = data.get("n_changed")
    if r2      is not None: summary["R² WLS"]             = round(float(r2),    4)
    if adj_r2  is not None: summary["R² Adj WLS"]         = round(float(adj_r2), 4)
    if ols_g   is not None: summary["Glejser p (OLS)"]    = round(float(ols_g),  4)
    if wls_g   is not None: summary["Glejser p (WLS)"]    = round(float(wls_g),  4)
    if ols_r   is not None: summary["RMSE OLS"]           = round(float(ols_r),  4)
    if wls_r   is not None: summary["RMSE WLS"]           = round(float(wls_r),  4)
    if n_ch    is not None: summary["Koef. Berubah >10%"] = n_ch
    if summary:
        _style_table(doc, pd.DataFrame([summary]), pr,
                     f"Tabel {bab}.1. Perbandingan OLS vs WLS")

    # Tabel koefisien
    coef_df = data.get("coef_df")
    if coef_df is not None and not coef_df.empty:
        _style_table(doc, coef_df, pr,
                     f"Tabel {bab}.2. Koefisien OLS vs WLS")

    # Figures
    for fk, ls in (("wls_fit_plot",   "Plot Aktual vs Prediksi: OLS vs WLS"),
                   ("wls_coef_comp",  "Perbandingan Koefisien OLS vs WLS")):
        if figs_png.get(fk):
            _embed_image(doc, pr, figs_png[fk], f"Gambar {fig_no}. {ls}")
            fig_no += 1

    _add_ai_narasi(doc, pr, (ai_texts or {}).get("ols_wls", ""),
                   "Interpretasi WLS", mod_key="ols_wls", data=data)
    return fig_no


def _render_ols_robust_comparison(doc, pr, data, figs_png, fig_no, bab, ai_texts):
    """Renderer untuk Perbandingan Model: OLS / RLM-Huber / RLM-Bisquare / WLS."""
    _add_heading(doc, pr, f"{bab}. Perbandingan Model Regresi", level=1)
    dep_var    = data.get("dep_var", "Y")
    ind_vars   = data.get("ind_vars", [])
    best_model = data.get("best_model", "OLS (Baseline)")
    n_obs      = data.get("n_obs", "?")

    _add_para(doc, pr,
        f"Perbandingan empat model regresi (OLS, RLM Huber-M, RLM Bisquare, WLS) "
        f"dilakukan untuk memilih pendekatan estimasi terbaik bagi model "
        f"{dep_var} ~ {', '.join(ind_vars) if ind_vars else 'prediktor'} "
        f"(N = {n_obs}). Model terbaik dipilih berdasarkan RMSE terendah.",
        first_indent=True, is_last_in_block=True)

    comp_df = data.get("comparison_df")
    if comp_df is not None and not comp_df.empty:
        _style_table(doc, comp_df, pr,
                     f"Tabel {bab}.1. Perbandingan Metrik Semua Model")

    _add_para(doc, pr,
        f"Berdasarkan evaluasi RMSE, model terbaik adalah: {best_model}.",
        first_indent=True, is_last_in_block=True)

    if figs_png.get("robust_comparison_bar"):
        _embed_image(doc, pr, figs_png["robust_comparison_bar"],
                     f"Gambar {fig_no}. RMSE per Model")
        fig_no += 1

    _add_ai_narasi(doc, pr, (ai_texts or {}).get("ols_robust_comparison", ""),
                   "Rekomendasi Pemilihan Model",
                   mod_key="ols_robust_comparison", data=data)
    return fig_no


def _render_compute(doc, pr, data, figs_png, fig_no, bab, ai_texts):
    """Renderer untuk Compute Variabel Baru."""
    _add_heading(doc, pr, f"{bab}. Transformasi & Komputasi Variabel", level=1)

    compute_log = data.get("compute_log", [])
    n_ops = len(compute_log)

    _add_para(doc, pr,
        f"Sejumlah {n_ops} variabel baru dibuat melalui operasi komputasi "
        f"(formula kustom, skor komposit, recode, standardisasi, atau transformasi) "
        f"sebelum analisis utama dilakukan.",
        first_indent=True, is_last_in_block=True)

    if compute_log:
        log_rows = []
        for entry in compute_log:
            log_rows.append({
                "Variabel Baru": entry.get("new_col", ""),
                "Metode":        entry.get("method", ""),
                "Sumber/Formula": str(entry.get("source", ""))[:80],
            })
        if log_rows:
            _style_table(doc, pd.DataFrame(log_rows), pr,
                         f"Tabel {bab}.1. Log Operasi Compute Variabel")

    _add_ai_narasi(doc, pr, (ai_texts or {}).get("compute", ""),
                   "Rasionalisasi Komputasi Variabel",
                   mod_key="compute", data=data)
    return fig_no


def _render_reliabilitas_icc(doc, pr, data, figs_png, fig_no, bab, ai_texts):
    """Renderer untuk Uji Reliabilitas ICC."""
    _add_heading(doc, pr, f"{bab}. Uji Reliabilitas ICC (Intraclass Correlation)", level=1)

    n_subj      = data.get("n_subj", "?")
    n_rater     = data.get("n_rater", "?")
    use_type    = data.get("use_type", "")
    rec_model   = data.get("rec_model", "ICC(2,1)")
    rater_names = data.get("rater_names", [])

    _add_para(doc, pr,
        f"Uji reliabilitas menggunakan Intraclass Correlation Coefficient (ICC) "
        f"dilakukan untuk mengevaluasi konsistensi pengukuran "
        f"({use_type if use_type else 'rater agreement'}) "
        f"dengan {n_subj} subjek dan {n_rater} rater/sesi pengukuran "
        f"(Koo & Mae, 2016; Shrout & Fleiss, 1979).",
        first_indent=True, is_last_in_block=True)

    # Tabel hasil ICC semua model
    icc_records = data.get("icc_df", [])
    if icc_records:
        try:
            icc_df = pd.DataFrame(icc_records)
            # Pilih kolom utama saja agar tabel tidak terlalu lebar
            cols_show = [c for c in ("Model", "Tipe", "ICC", "CI_Lower",
                                     "CI_Upper", "F", "p_value")
                         if c in icc_df.columns]
            if cols_show:
                icc_show = icc_df[cols_show].copy()
                icc_show.columns = [c.replace("_", " ") for c in cols_show]
                _style_table(doc, icc_show, pr,
                             f"Tabel {bab}.1. Hasil Uji Reliabilitas ICC — Semua Model")
        except Exception:
            pass

    # Panduan interpretasi threshold
    threshold_df = pd.DataFrame({
        "Rentang ICC":        ["ICC < 0.50", "0.50 ≤ ICC < 0.75",
                               "0.75 ≤ ICC < 0.90", "ICC ≥ 0.90"],
        "Kualitas":           ["Buruk", "Sedang", "Baik", "Sangat Baik (Excellent)"],
        "Sumber":             ["Koo & Mae (2016)"] * 4,
    })
    _style_table(doc, threshold_df, pr,
                 f"Tabel {bab}.2. Panduan Interpretasi ICC (Koo & Mae, 2016)")

    # Tabel ANOVA dasar perhitungan
    anova_records = data.get("anova_tbl", [])
    if anova_records:
        try:
            anova_df = pd.DataFrame(anova_records)
            if not anova_df.empty:
                _style_table(doc, anova_df, pr,
                             f"Tabel {bab}.3. Tabel ANOVA Dasar Perhitungan ICC")
        except Exception:
            pass

    # AI narasi
    ai_text = (ai_texts or {}).get("reliabilitas_icc", "") or data.get("ai_text", "")
    _add_ai_narasi(doc, pr, ai_text,
                   "Interpretasi Reliabilitas ICC",
                   mod_key="reliabilitas_icc", data=data)
    return fig_no


def _render_uji_asumsi(doc, pr, data, figs_png, fig_no, bab, ai_texts):
    """Renderer untuk Uji Asumsi Pra-Analisis."""
    _add_heading(doc, pr, f"{bab}. Uji Asumsi Pra-Analisis", level=1)
    _add_para(doc, pr,
        "Uji asumsi dilakukan sebelum pemilihan metode analisis utama, mencakup "
        "normalitas multivariat (Mardia's test), homogenitas varians (Levene & Bartlett), "
        "dan linieritas (Ramsey RESET test).",
        first_indent=True, is_last_in_block=True)

    # Rekomendasi
    rec = data.get("rekomendasi", {})
    if isinstance(rec, dict):
        level      = rec.get("level", "").upper()
        skor       = rec.get("skor_lulus", "?")
        total      = rec.get("total_uji", "?")
        pct        = rec.get("pct_lulus", "?")
        rec_list   = rec.get("rekomendasi", [])
        peringatan = rec.get("peringatan", [])

        _style_table(doc, pd.DataFrame([{
            "Level Analisis": level,
            "Uji Lulus":      f"{skor}/{total}",
            "% Lulus":        f"{pct}%",
        }]), pr, f"Tabel {bab}.1. Ringkasan Hasil Uji Asumsi")

        if rec_list:
            _add_heading(doc, pr, "Rekomendasi Metode Analisis", level=3)
            clean_recs = [r.lstrip("✅🟡🔴 ").replace("**", "") for r in rec_list]
            for r in clean_recs:
                _add_para(doc, pr, f"• {r}", first_indent=False)

        if peringatan:
            _add_heading(doc, pr, "Peringatan", level=3)
            clean_warns = [w.lstrip("⚠️🚨ℹ️ ").replace("**", "") for w in peringatan]
            for w in clean_warns:
                _add_para(doc, pr, f"• {w}", first_indent=False)

    # Tabel detail
    detail = rec.get("detail", {}) if isinstance(rec, dict) else {}
    if detail:
        detail_rows = []
        labels_map = {
            "normalitas_univariat":   "Normalitas Univariat (Shapiro-Wilk)",
            "normalitas_multivariat": "Normalitas Multivariat (Mardia)",
            "homogenitas":            "Homogenitas Varians (Levene)",
            "linieritas":             "Linieritas (Ramsey RESET)",
        }
        for key, info in detail.items():
            if not isinstance(info, dict):
                continue
            lulus = info.get("lulus", False)
            label = labels_map.get(key, key)
            # Buat keterangan ringkas
            if key == "normalitas_univariat":
                ket = f"{info.get('n_normal','?')}/{info.get('n_variabel','?')} variabel normal ({info.get('pct_normal','?')}%)"
            elif key == "normalitas_multivariat":
                ket = f"Skewness p={info.get('p_skew','?')}, Kurtosis p={info.get('p_kurt','?')}"
            elif key == "homogenitas":
                ket = f"{info.get('n_lulus','?')}/{info.get('n_uji','?')} kelompok homogen"
            elif key == "linieritas":
                ket = f"{info.get('n_lulus','?')}/{info.get('n_uji','?')} pasangan linier"
            else:
                ket = ""
            detail_rows.append({
                "Uji Asumsi": label,
                "Status":     "Terpenuhi ✓" if lulus else "Tidak Terpenuhi ✗",
                "Keterangan": ket,
            })
        if detail_rows:
            _style_table(doc, pd.DataFrame(detail_rows), pr,
                         f"Tabel {bab}.2. Detail Hasil Per Uji Asumsi")

    ai_text = (ai_texts or {}).get("uji_asumsi", "")
    _add_ai_narasi(doc, pr, ai_text,
                   "Interpretasi Uji Asumsi",
                   mod_key="uji_asumsi", data=data)
    return fig_no



def _render_klaster(doc, pr, data, figs_png, fig_no, bab, ai_texts):
    """Renderer untuk Analisis Klaster (K-Means / Hierarchical)."""
    _add_heading(doc, pr, f"{bab}. Analisis Klaster", level=1)
    method    = data.get("method", "K-Means")
    k         = data.get("k", "?")
    cols      = data.get("cols", [])
    silhouette= data.get("silhouette")
    linkage   = data.get("linkage", "ward")
    n_var     = len(cols)

    sil_kat = ""
    if silhouette is not None:
        sv = float(silhouette)
        sil_kat = ("sangat baik" if sv >= 0.70 else
                   "baik" if sv >= 0.50 else
                   "cukup" if sv >= 0.30 else "rendah")

    _add_para(doc, pr,
        f"Analisis klaster dilakukan menggunakan metode {method} "
        f"dengan {k} klaster pada {n_var} variabel: "
        f"{', '.join(cols) if cols else 'lihat konfigurasi'}. "
        f"Data distandarisasi (Z-score) sebelum clustering untuk menghilangkan "
        f"efek skala (MacQueen, 1967; Ward, 1963).",
        first_indent=True, is_last_in_block=True)

    # Ringkasan metrik
    summary = {"Metode": method, "k Klaster": k, "N Variabel": n_var}
    if silhouette is not None:
        summary["Silhouette Score"] = round(float(silhouette), 4)
        summary["Kualitas"]         = sil_kat
    if method == "Hierarchical":
        summary["Linkage"] = linkage
    _style_table(doc, pd.DataFrame([summary]), pr,
                 f"Tabel {bab}.1. Ringkasan Hasil Analisis Klaster")

    # Tabel profil klaster
    profile_records = data.get("profile_df_records")
    if profile_records:
        try:
            profile_df = pd.DataFrame(profile_records)
            # Pilih kolom yang tidak terlalu lebar (max 8)
            show_cols = profile_df.columns.tolist()
            if len(show_cols) > 9:
                mean_cols = [c for c in show_cols if "(mean)" in c][:6]
                show_cols = ["Klaster", "N"] + mean_cols
                show_cols = [c for c in show_cols if c in profile_df.columns]
            _style_table(doc, profile_df[show_cols], pr,
                         f"Tabel {bab}.2. Profil Rata-rata per Klaster")
        except Exception:
            pass

    # Interpretasi silhouette standar
    if silhouette is not None:
        _add_para(doc, pr,
            f"Silhouette score = {float(silhouette):.4f} mengindikasikan kualitas "
            f"pengelompokan yang {sil_kat} (Rousseeuw, 1987). "
            f"Nilai ini menunjukkan bahwa klaster yang terbentuk memiliki "
            f"kohesi internal yang {'memadai' if float(silhouette) >= 0.30 else 'perlu diperbaiki'}.",
            first_indent=True, is_last_in_block=True)

    # Figures
    for fk, ls in (("klaster_scatter",  "Scatter Klaster via PCA"),
                   ("klaster_radar",    "Radar Chart Profil Klaster"),
                   ("klaster_elbow",    "Elbow Method & Silhouette Score"),
                   ("klaster_dendro",   "Dendrogram Hierarkikal")):
        if figs_png.get(fk):
            _embed_image(doc, pr, figs_png[fk], f"Gambar {fig_no}. {ls}")
            fig_no += 1

    _add_ai_narasi(doc, pr, (ai_texts or {}).get("klaster", ""),
                   "Interpretasi Analisis Klaster",
                   mod_key="klaster", data=data)
    return fig_no


def _render_eda(doc, pr, data, figs_png, fig_no, bab, ai_texts):
    """Renderer untuk EDA — ringkasan profil dataset."""
    _add_heading(doc, pr, f"{bab}. Eksplorasi Data (EDA)", level=1)
    n_rows    = data.get("n_rows", "?")
    n_cols    = data.get("n_cols", "?")
    n_num     = data.get("n_numeric", "?")
    n_cat     = data.get("n_cat", "?")
    n_miss    = data.get("n_missing", 0)
    pct_miss  = data.get("pct_missing", 0)
    n_dup     = data.get("n_dup", 0)

    _add_para(doc, pr,
        f"Eksplorasi data awal (EDA) dilakukan terhadap dataset yang terdiri dari "
        f"{n_rows} observasi dan {n_cols} variabel ({n_num} numerik, {n_cat} kategorik). "
        f"Terdapat {n_miss} missing values ({pct_miss}% dari total sel) "
        f"dan {n_dup} baris duplikat.",
        first_indent=True, is_last_in_block=True)

    # Tabel ringkasan profil
    summary = {
        "Jumlah Observasi": n_rows,
        "Jumlah Variabel":  n_cols,
        "Variabel Numerik": n_num,
        "Variabel Kategorik": n_cat,
        "Total Missing":    n_miss,
        "% Missing":        f"{pct_miss}%",
        "Baris Duplikat":   n_dup,
    }
    _style_table(doc, pd.DataFrame([summary]), pr,
                 f"Tabel {bab}.1. Ringkasan Profil Dataset")

    # Interpretasi kondisi data
    kondisi = []
    if float(pct_miss) > 20:
        kondisi.append(f"missing values tinggi ({pct_miss}%) — perlu imputasi atau eliminasi kolom")
    elif float(pct_miss) > 5:
        kondisi.append(f"missing values moderat ({pct_miss}%) — pertimbangkan imputasi")
    if n_dup > 0:
        kondisi.append(f"terdapat {n_dup} baris duplikat yang perlu diperiksa")

    if kondisi:
        _add_para(doc, pr,
            "Perhatian pada kualitas data: " + "; ".join(kondisi) + ".",
            first_indent=True, is_last_in_block=True)
    else:
        _add_para(doc, pr,
            "Dataset dalam kondisi baik untuk dilanjutkan ke tahap analisis statistik.",
            first_indent=True, is_last_in_block=True)

    # Figures EDA jika ada
    for fk, ls in (("eda_profil",    "Komposisi Tipe Kolom"),
                   ("eda_missing",   "Missing Values per Kolom"),
                   ("eda_histogram", "Distribusi Variabel Numerik")):
        if figs_png.get(fk):
            _embed_image(doc, pr, figs_png[fk], f"Gambar {fig_no}. {ls}")
            fig_no += 1

    return fig_no


def _render_cfa(doc, pr, data, figs_png, fig_no, bab, ai_texts):
    """Renderer untuk CFA Standalone — Confirmatory Factor Analysis."""
    _add_heading(doc, pr, f"{bab}. Confirmatory Factor Analysis (CFA)", level=1)

    factor_map  = data.get("factor_map", {})
    model_syntax= data.get("model_syntax", "")
    n_obs       = data.get("n_obs", "?")
    n_konstruk  = len(factor_map)

    _add_para(doc, pr,
        f"Confirmatory Factor Analysis (CFA) dilakukan untuk menguji validitas "
        f"konstruk model pengukuran dengan {n_konstruk} konstruk laten "
        f"dan {n_obs} observasi. "
        f"Estimasi menggunakan metode Maximum Likelihood via semopy "
        f"(Hair et al., 2010; Hu & Bentler, 1999).",
        first_indent=True, is_last_in_block=True)

    if model_syntax:
        _add_heading(doc, pr, "Sintaks Model", level=3)
        _add_para(doc, pr, model_syntax, first_indent=False, is_last_in_block=True)

    # Tabel fit indices
    fit_records = data.get("fit_df_records")
    if fit_records:
        try:
            _style_table(doc, pd.DataFrame(fit_records), pr,
                         f"Tabel {bab}.1. Indeks Kecocokan Model (Goodness of Fit)")
        except Exception:
            pass

    # Tabel factor loadings
    loading_records = data.get("loadings_df_records")
    if loading_records:
        try:
            ldf = pd.DataFrame(loading_records)
            show_cols = [c for c in ("Konstruk Laten", "Indikator", "Loading (λ)",
                                     "SE", "z / t", "p-value", "Kecukupan")
                         if c in ldf.columns]
            _style_table(doc, ldf[show_cols] if show_cols else ldf, pr,
                         f"Tabel {bab}.2. Factor Loadings (λ)")
        except Exception:
            pass

    # Tabel AVE & CR
    ave_records = data.get("ave_cr_df_records")
    if ave_records:
        try:
            _style_table(doc, pd.DataFrame(ave_records), pr,
                         f"Tabel {bab}.3. AVE dan Composite Reliability (CR)")
        except Exception:
            pass

    # Tabel HTMT
    htmt_records = data.get("htmt_df_records")
    if htmt_records:
        try:
            htmt_df = pd.DataFrame(htmt_records)
            _style_table(doc, htmt_df, pr,
                         f"Tabel {bab}.4. HTMT Matrix (Discriminant Validity)")
        except Exception:
            pass

    # Figure loadings
    if figs_png.get("cfa_loadings"):
        _embed_image(doc, pr, figs_png["cfa_loadings"],
                     f"Gambar {fig_no}. Factor Loadings per Konstruk")
        fig_no += 1

    ai_text = (ai_texts or {}).get("cfa", "")
    _add_ai_narasi(doc, pr, ai_text,
                   "Interpretasi CFA", mod_key="cfa", data=data)
    return fig_no




def _render_power_analysis(doc, pr, data, figs_png, fig_no, bab, ai_texts):
    """Render hasil Power Analysis ke dalam dokumen Word."""
    _add_heading(doc, pr, "Power Analysis", level=2)

    # Ringkasan parameter
    params = {
        k: v for k, v in {
            "Jenis Uji":       data.get("test_type"),
            "Effect Size":     data.get("effect_size"),
            "Alpha (α)": data.get("alpha"),
            "Power (1−β)": data.get("power"),
            "N Total":         data.get("n_total"),
            "N per Kelompok":  data.get("n_per_group"),
        }.items() if v is not None
    }
    if params:
        _style_table(
            doc, pd.DataFrame([params]), pr,
            f"Tabel {bab}.1. Parameter Power Analysis",
        )

    # Narasi
    _add_ai_narasi(
        doc, pr,
        ai_texts.get("power_analysis") or _fallback_narasi("power_analysis", data),
        f"Tabel {bab}.1",
    )



def _render_scraping(doc, pr, data, figs_png, fig_no, bab, ai_texts):
    """Renderer untuk Web Scraping & Data Collector."""
    _add_heading(doc, pr, f"{bab}. Pengumpulan Data via Web Scraping", level=1)

    source   = data.get("source", "tidak diketahui")
    n_rows   = data.get("n_rows", "?")
    n_cols   = data.get("n_cols", "?")
    n_num    = data.get("n_numeric", "?")
    n_miss   = data.get("n_missing", 0)
    n_dup    = data.get("n_dup", 0)
    cols     = data.get("col_names", [])

    _add_para(doc, pr,
        f"Data penelitian dikumpulkan secara otomatis melalui teknik web scraping "
        f"dari sumber: {source}. "
        f"Dataset yang diperoleh terdiri dari {n_rows} observasi dan {n_cols} variabel "
        f"({n_num} numerik). "
        f"Proses pengambilan data menggunakan pustaka requests dan BeautifulSoup "
        f"dengan rate-limiting untuk mematuhi etika pengambilan data publik.",
        first_indent=True, is_last_in_block=True)

    # Tabel ringkasan
    summary = {
        "Sumber Data":      source[:80],
        "Jumlah Observasi": n_rows,
        "Jumlah Variabel":  n_cols,
        "Variabel Numerik": n_num,
        "Missing Values":   n_miss,
        "Baris Duplikat":   n_dup,
    }
    _style_table(doc, pd.DataFrame([summary]), pr,
                 f"Tabel {bab}.1. Ringkasan Dataset Hasil Scraping")

    if cols:
        cols_df = pd.DataFrame({"No": range(1, len(cols)+1), "Nama Variabel": cols})
        _style_table(doc, cols_df, pr,
                     f"Tabel {bab}.2. Daftar Variabel")

    _add_para(doc, pr,
        f"Setelah pengambilan data, dilakukan proses cleaning meliputi: "
        f"penghapusan kolom dengan missing values tinggi, standardisasi format angka, "
        f"penghapusan duplikat, dan konversi tipe data. "
        + (f"Terdapat {n_miss} missing values yang ditangani sebelum analisis. "
           if int(n_miss) > 0 else "Dataset hasil scraping tidak memiliki missing values. "),
        first_indent=True, is_last_in_block=True)

    ai_text = (ai_texts or {}).get("scraping", "")
    _add_ai_narasi(doc, pr, ai_text,
                   "Evaluasi Kualitas Data Scraping",
                   mod_key="scraping", data=data)
    return fig_no


_MODULE_RENDERERS = {
    "regresi": _render_regresi,
    "ols_plus":              _render_ols_plus,
    "logistik": _render_logistik,
    "mediasi":               _render_mediasi,
    "moderasi":              _render_moderasi,
    "anova":                 _render_anova,
    "uji_beda":              _render_uji_beda,
    "outlier":               _render_outlier,
    "sem":                   _render_sem,
    "kelompok":              _render_kelompok,
    "efa":                   _render_efa,
    # Poin 3: renderer baru
    "ols_robust":            _render_ols_robust,
    "ols_wls":               _render_ols_wls,
    "ols_robust_comparison": _render_ols_robust_comparison,
    "compute":               _render_compute,
    "reliabilitas_icc":      _render_reliabilitas_icc,
    "uji_asumsi":            _render_uji_asumsi,
    # Modul baru v4.2
    "klaster":               _render_klaster,
    "eda":                   _render_eda,
    "cfa":                   _render_cfa,
    "scraping":              _render_scraping,
    "power_analysis":       _render_power_analysis,
}


# =============================================================================
# TITLE PAGE — satu-satunya tempat blank paragraf yang memang by design

