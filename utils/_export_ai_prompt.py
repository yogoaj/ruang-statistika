"""
utils/_export_ai_prompt.py — Ruang Statistika v4.8
Membangun prompt AI per modul untuk interpretasi laporan otomatis.
Setiap blok if-elif menghasilkan prompt spesifik berdasarkan hasil analisis.

Menambah modul baru:
  Tambahkan blok elif di _build_module_ai_prompt() dengan prompt
  yang memanfaatkan key dari _normalize_mod_data().

Diimport oleh: utils/export.py
"""

import json

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

    # Definisikan system_prompt default (digunakan untuk semua modul, termasuk CFA)
    # PERBAIKAN: dipindah ke atas agar tersedia untuk blok time_series dan CFA
    system_prompt = MODULE_SYSTEM_PROMPTS.get(
        mod_key,
        f"Buat interpretasi {mod_label} dalam Bahasa Indonesia. Format akademis 3 paragraf."
    )

    # ── Time Series Analysis ─────────────────────────────────────────────────
    if mod_key == "time_series":
        col_name    = mod_data.get("col_name", "deret waktu")
        model_label = mod_data.get("model_label", mod_data.get("order", "ARIMA"))
        metrics     = mod_data.get("metrics", {})
        rmse  = mod_data.get("rmse", metrics.get("RMSE", "—"))
        mae   = mod_data.get("mae",  metrics.get("MAE",  "—"))
        mape  = mod_data.get("mape", metrics.get("MAPE", "—"))
        aic   = mod_data.get("aic", "—")
        bic   = mod_data.get("bic", "—")
        adf_p = mod_data.get("stasioner", {}).get("adf_p", "—")
        kpss_p= mod_data.get("stasioner", {}).get("kpss_p", "—")
        conclusion = mod_data.get("stasioner", {}).get("conclusion", "—")
        n_forecast = mod_data.get("n_forecast", 0)
        fc_preview = mod_data.get("forecast_preview", [])
        decompose_t= mod_data.get("decompose_type", "—")

        return (
            system_prompt
            + f"""\n\nHasil Time Series Analysis — {col_name}:\n\n"""
            + f"""UJI STASIONERITAS:\n"""
            + f"""- ADF p-value  = {adf_p} | KPSS p-value = {kpss_p}\n"""
            + f"""- Kesimpulan   = {conclusion}\n\n"""
            + f"""DEKOMPOSISI: Model {decompose_t}\n\n"""
            + f"""MODEL: {model_label}\n"""
            + f"""- AIC = {aic}, BIC = {bic}\n"""
            + f"""- RMSE = {rmse}, MAE = {mae}, MAPE = {mape}%\n\n"""
            + f"""FORECAST {n_forecast} PERIODE:\n"""
            + f"""{fc_preview}\n\n"""
            + """Interpretasi Bahasa Indonesia (4 paragraf akademis):\n"""
            + """1. Evaluasi stasioneritas — apakah data perlu differencing?\n"""
            + """2. Kualitas model — interpretasi AIC/BIC dan MAPE\n"""
            + """3. Pola forecast — tren naik/turun/stabil? Ada seasonal?\n"""
            + """4. Rekomendasi penggunaan hasil untuk pengambilan keputusan\n"""
            + """Referensi: Box & Jenkins (1976), Hyndman & Athanasopoulos (2021)."""
        )

    # ── CFA (Confirmatory Factor Analysis) ──────────────────────────────────
    # Blok ini DIPINDAHKAN ke sini (setelah system_prompt didefinisikan)
    if mod_key == "cfa":
        fit = mod_data.get("fit_indices", {})
        loadings = mod_data.get("loadings_df")
        load_str = loadings.to_string(index=False) if hasattr(loadings, "to_string") else str(loadings)[:500]
        ave  = mod_data.get("ave", "N/A")
        cr   = mod_data.get("cr", "N/A")
        htmt = mod_data.get("htmt", "N/A")
        return (
            system_prompt
            + f"""\n\nHasil Confirmatory Factor Analysis (CFA):\n\n"""
            + f"""FIT INDICES:\n"""
            + f"""- CFI  = {fit.get('CFI', 'N/A')} (≥ 0.95)\n"""
            + f"""- RMSEA= {fit.get('RMSEA', 'N/A')} (≤ 0.06)\n"""
            + f"""- SRMR = {fit.get('SRMR', 'N/A')} (≤ 0.08)\n"""
            + f"""- GFI  = {fit.get('GFI', 'N/A')} (≥ 0.90)\n"""
            + f"""- Chi-Square p = {fit.get('chi2_p', 'N/A')}\n\n"""
            + f"""FACTOR LOADINGS (standardized):\n{load_str}\n\n"""
            + f"""AVE={ave} (≥0.50), CR={cr} (≥0.70), HTMT={htmt} (<0.85)\n\n"""
            + """Interpretasi Bahasa Indonesia (4-5 paragraf akademis):\n"""
            + """1. Evaluasi fit model berdasarkan semua fit indices\n"""
            + """2. Kualitas factor loadings (valid jika ≥ 0.50)\n"""
            + """3. Convergent validity (AVE) dan composite reliability (CR)\n"""
            + """4. Discriminant validity (HTMT)\n"""
            + """5. Rekomendasi modifikasi model jika perlu\n"""
            + """Referensi: Hair et al. (2019), Fornell & Larcker (1981), Henseler et al. (2015)."""
        )

    # Default return untuk semua modul lainnya
    return (
        system_prompt
        + "\n\nData hasil analisis:\n"
        + json.dumps(summary, default=str, indent=2)
    )