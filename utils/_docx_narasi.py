"""
utils/_docx_narasi.py — Ruang Statistika v4.8
Narasi fallback otomatis (tanpa AI) untuk setiap modul analisis.
Dipanggil oleh _add_ai_narasi() di _docx_primitives.py ketika AI tidak aktif.

Struktur:
  _fallback_narasi(mod_key, data) -> str
    └─ if mod_key == "regresi":   ...
    └─ if mod_key == "anova":     ...
    └─ ... (21 modul)

Diimport oleh: utils/docx_helpers.py
JANGAN diimport langsung dari modul lain — gunakan docx_helpers.py.
"""

import pandas as pd
from utils._docx_primitives import _first_valid_df


def _fallback_narasi(mod_key: str, data: dict) -> str:
    """
    Buat narasi interpretasi otomatis berstandar paper ilmiah dari data statistik,
    digunakan jika ai_texts[mod_key] kosong atau tidak tersedia.
    Seluruh narasi menggunakan diksi akademis formal sesuai konvensi jurnal ilmiah.
    """
    dep     = data.get("y", "variabel dependen")
    ind     = data.get("x", [])
    ind_str = ", ".join(ind) if ind else "variabel prediktor"

    # ── Interpretasi ukuran efek menggunakan standar Cohen (1988) ─────────────
    def _kat_d(v):
        v = abs(v)
        return "besar" if v >= 0.80 else ("sedang" if v >= 0.50 else "kecil")

    def _kat_eta2(v):
        return "besar" if v >= 0.14 else ("sedang" if v >= 0.06 else "kecil")

    def _kat_f2(v):
        return "besar" if v >= 0.35 else ("sedang" if v >= 0.15 else "kecil")

    def _kat_r(v):
        v = abs(v)
        return "kuat" if v >= 0.50 else ("sedang" if v >= 0.30 else
               "lemah" if v >= 0.10 else "sangat lemah")

    def _sig_str(pval, alpha=0.05):
        return "signifikan" if pval < alpha else "tidak signifikan"

    # ══════════════════════════════════════════════════════════════════════════
    # REGRESI LINIER & OLS+
    # ══════════════════════════════════════════════════════════════════════════
    if mod_key in ("regresi", "ols_plus"):
        r2      = data.get("r2")
        adj_r2  = data.get("adj_r2")
        pval    = data.get("f_pvalue")
        rmse    = data.get("rmse")
        dw      = data.get("durbin_watson")
        vif_max = data.get("vif_max")
        white_p = data.get("white_pvalue")
        shap_p  = data.get("shapiro_residual_p")

        r2_pct  = f"{r2 * 100:.1f}%" if r2 is not None else "—"
        adj_pct = f"{adj_r2 * 100:.1f}%" if adj_r2 is not None else "—"

        if r2 is not None:
            f2 = r2 / (1 - r2) if r2 < 1.0 else float("inf")
            kat_f2 = _kat_f2(f2)
        else:
            f2 = None
            kat_f2 = ""

        paragraf1 = (
            f"Analisis regresi linier berganda dilakukan untuk menguji pengaruh "
            f"{ind_str} terhadap {dep}. "
        )
        if pval is not None:
            sig_model = _sig_str(pval)
            paragraf1 += (
                f"Hasil uji F menunjukkan bahwa model secara simultan {sig_model} "
                f"(p = {pval:.3f}, \u03b1 = .05), "
            )
        if r2 is not None:
            paragraf1 += (
                f"dengan koefisien determinasi R\u00b2 = {r2:.3f} "
                f"(R\u00b2 Adjusted = {adj_pct}), "
                f"yang berarti model mampu menjelaskan {r2_pct} varians {dep}. "
            )
        if f2 is not None and not (f2 == float("inf")):
            paragraf1 += (
                f"Ukuran efek Cohen\u2019s f\u00b2 = {f2:.3f} termasuk kategori {kat_f2} "
                f"(Cohen, 1988), mengindikasikan relevansi praktis model yang "
                f"{'memadai' if f2 >= 0.15 else 'perlu ditingkatkan'}. "
            )

        # Paragraf koefisien
        lines_coef = []
        coef_df = data.get("coef_table")
        if coef_df is not None and not coef_df.empty:
            p_col   = next((c for c in coef_df.columns
                            if c.lower() in ("p", "p-value", "sig", "pval")), None)
            b_col   = next((c for c in coef_df.columns
                            if c.lower() in ("b", "coef", "koefisien", "\u03b2 (koefisien)",
                                             "\u03b2", "coefficient")), None)
            var_col = coef_df.columns[0]
            for _, row in coef_df.iterrows():
                var_name = str(row[var_col])
                if var_name.lower() in ("konstanta", "constant", "intercept"):
                    continue
                if p_col and b_col:
                    try:
                        pv = float(row[p_col])
                        bv = float(row[b_col])
                        ket_sig = (
                            "berpengaruh positif dan signifikan" if (bv > 0 and pv < 0.05) else
                            "berpengaruh negatif dan signifikan" if (bv < 0 and pv < 0.05) else
                            "tidak berpengaruh signifikan"
                        )
                        lines_coef.append(
                            f"Variabel {var_name} {ket_sig} terhadap {dep} "
                            f"(\u03b2 = {bv:.3f}, p = {pv:.3f})"
                        )
                    except Exception:
                        pass

        paragraf2 = ""
        if lines_coef:
            paragraf2 = (
                "Berdasarkan hasil pengujian koefisien regresi parsial, diperoleh temuan "
                "sebagai berikut: "
                + "; ".join(lines_coef) + ". "
                "Koefisien yang signifikan (p < .05) menunjukkan kontribusi unik variabel "
                "tersebut dalam memprediksi variabel dependen setelah mengontrol variabel "
                "lainnya (Field, 2018)."
            )

        # Paragraf asumsi klasik (khusus ols_plus)
        paragraf3 = ""
        if mod_key == "ols_plus":
            asumsi_lines = []
            if dw is not None:
                ket_dw = "terpenuhi" if 1.5 < float(dw) < 2.5 else "perlu diperiksa lebih lanjut"
                asumsi_lines.append(
                    f"autokorelasi diuji dengan Durbin-Watson = {float(dw):.3f} "
                    f"(asumsi {ket_dw})"
                )
            if vif_max is not None:
                ket_vif = ("tidak terdapat masalah multikolinearitas"
                           if float(vif_max) < 10
                           else "terdeteksi multikolinearitas (VIF > 10)")
                asumsi_lines.append(
                    f"VIF maksimum = {float(vif_max):.2f} ({ket_vif}, "
                    "acuan Marquardt, 1970)"
                )
            if white_p is not None:
                ket_het = ("homoskedastisitas terpenuhi"
                           if float(white_p) >= 0.05
                           else "terindikasi heteroskedastisitas")
                asumsi_lines.append(
                    f"uji White menunjukkan {ket_het} "
                    f"(p = {float(white_p):.3f}, White, 1980)"
                )
            if shap_p is not None:
                ket_norm = ("residual berdistribusi normal"
                            if float(shap_p) >= 0.05
                            else "residual tidak berdistribusi normal")
                asumsi_lines.append(
                    f"Shapiro-Wilk residual: {ket_norm} (p = {float(shap_p):.3f})"
                )
            if asumsi_lines:
                paragraf3 = (
                    "Evaluasi uji asumsi klasik menunjukkan: "
                    + "; ".join(asumsi_lines) + ". "
                    "Pemenuhan asumsi klasik merupakan prasyarat validitas inferensi "
                    "statistik dalam analisis regresi OLS (Hair et al., 2010)."
                )

        return "\n\n".join(p for p in [paragraf1, paragraf2, paragraf3] if p.strip())

    # ══════════════════════════════════════════════════════════════════════════
    # REGRESI LOGISTIK
    # ══════════════════════════════════════════════════════════════════════════
    elif mod_key == "logistik":
        auc     = data.get("auc")
        pseudo  = data.get("pseudo_r2")
        aic     = data.get("aic")
        bic     = data.get("bic")
        coef_df = _first_valid_df(data.get("coef_table"), data.get("odds_df"))

        paragraf1 = (
            f"Analisis regresi logistik biner dilakukan untuk memprediksi {dep} "
            f"berdasarkan {ind_str}. "
            "Model regresi logistik dipilih mengingat variabel dependen bersifat dikotomis, "
            "sehingga pendekatan ini lebih tepat dibandingkan regresi linier biasa "
            "(Hosmer & Lemeshow, 2013). "
        )
        if pseudo is not None:
            paragraf1 += (
                f"Pseudo R\u00b2 McFadden = {pseudo:.3f} mengindikasikan proporsi "
                "variansi yang dapat dijelaskan oleh model. "
            )
        if aic is not None and bic is not None:
            paragraf1 += f"Kriteria informasi model: AIC = {aic:.2f}, BIC = {bic:.2f}. "

        paragraf2 = ""
        if auc is not None:
            auc_f = float(auc)
            if auc_f >= 0.90:
                kat_auc, deskripsi = "sangat baik (excellent)", "sangat tinggi"
            elif auc_f >= 0.80:
                kat_auc, deskripsi = "baik (good)", "tinggi"
            elif auc_f >= 0.70:
                kat_auc, deskripsi = "cukup (fair)", "sedang"
            else:
                kat_auc, deskripsi = "rendah (poor)", "rendah"
            paragraf2 = (
                "Evaluasi performa diskriminatif model menggunakan area di bawah kurva ROC "
                f"(AUC) menghasilkan nilai {auc_f:.3f}, yang termasuk kategori {kat_auc}. "
                f"Nilai ini mengindikasikan kemampuan klasifikasi model yang {deskripsi} "
                f"dalam membedakan antara kedua kategori {dep} "
                "(Hosmer & Lemeshow, 2013). "
            )

        paragraf3 = ""
        or_lines = []
        if coef_df is not None and not coef_df.empty:
            p_col  = next((c for c in coef_df.columns
                           if c.lower() in ("p", "p-value", "sig")), None)
            or_col = next((c for c in coef_df.columns
                           if c.lower() in ("or (exp \u03b2)", "odds ratio",
                                            "exp(b)", "exp(coef)", "or")), None)
            var_col = coef_df.columns[0]
            if p_col and or_col:
                for _, row in coef_df.iterrows():
                    vn = str(row[var_col])
                    if vn.lower() in ("konstanta", "constant", "intercept"):
                        continue
                    try:
                        pv = float(row[p_col])
                        ov = float(row[or_col])
                        if pv < 0.05:
                            arah = "meningkatkan" if ov > 1 else "menurunkan"
                            or_lines.append(
                                f"{vn} secara signifikan {arah} kemungkinan {dep} "
                                f"sebesar {abs(ov - 1) * 100:.1f}% "
                                f"(OR = {ov:.3f}, p = {pv:.3f})"
                            )
                    except Exception:
                        pass
        if or_lines:
            paragraf3 = (
                "Berdasarkan nilai Odds Ratio (OR = exp[\u03b2]) variabel prediktor "
                "yang signifikan: "
                + "; ".join(or_lines) + ". "
                "OR > 1 menunjukkan peningkatan peluang kejadian, sedangkan OR < 1 "
                "menunjukkan penurunan peluang (Hosmer & Lemeshow, 2013)."
            )

        return "\n\n".join(p for p in [paragraf1, paragraf2, paragraf3] if p.strip())

    # ══════════════════════════════════════════════════════════════════════════
    # MEDIASI
    # ══════════════════════════════════════════════════════════════════════════
    elif mod_key == "mediasi":
        m        = data.get("m", "variabel mediator")
        x_var    = data.get("x", ind_str)
        boot_ci  = data.get("bootstrap_ci")
        indirect = data.get("indirect_effect")
        direct   = data.get("direct_effect")
        total    = data.get("total_effect")

        paragraf1 = (
            f"Analisis mediasi dilakukan untuk menguji peran {m} sebagai variabel "
            f"mediator dalam hubungan antara {x_var} dan {dep}, "
            "menggunakan prosedur bootstrapping sebagaimana direkomendasikan oleh "
            "Preacher dan Hayes (2008). "
        )

        paragraf2 = ""
        if boot_ci and indirect is not None:
            ci_lo, ci_hi = boot_ci
            tidak_nol = not (float(ci_lo) < 0 < float(ci_hi))
            sig_med = ("terdapat efek mediasi yang signifikan" if tidak_nol
                       else "tidak terdapat efek mediasi yang signifikan")
            paragraf2 = (
                f"Hasil bootstrapping (95% Bias-Corrected CI) menunjukkan {sig_med}, "
                f"dengan efek tidak langsung (indirect effect) = {float(indirect):.3f} "
                f"[{float(ci_lo):.3f}, {float(ci_hi):.3f}]. "
            )
            if tidak_nol and direct is not None and total is not None:
                d_f = float(direct)
                t_f = float(total)
                if abs(d_f) < 0.001:
                    jenis = "mediasi penuh (full mediation)"
                elif (d_f > 0) == (t_f > 0):
                    jenis = "mediasi sebagian (partial mediation)"
                else:
                    jenis = "mediasi suppressif"
                paragraf2 += (
                    f"Efek langsung (c\u2019) = {d_f:.3f}, efek total (c) = {t_f:.3f}, "
                    f"mengindikasikan {jenis} "
                    "(Baron & Kenny, 1986; Hayes, 2013). "
                )
            elif not tidak_nol:
                paragraf2 += (
                    "Interval kepercayaan yang mencakup nol mengindikasikan bahwa "
                    f"{m} tidak memediasi hubungan secara signifikan. "
                )

        paragraf3 = (
            f"Temuan ini memberikan pemahaman mekanistik mengenai bagaimana {x_var} "
            f"memengaruhi {dep} melalui {m} sebagai variabel perantara. "
            "Implikasi teoritis dari hasil mediasi ini perlu dikontekstualisasikan "
            "dalam kerangka teoretis penelitian yang lebih luas (Hayes, 2013)."
        )

        return "\n\n".join(p for p in [paragraf1, paragraf2, paragraf3] if p.strip())

    # ══════════════════════════════════════════════════════════════════════════
    # MODERASI
    # ══════════════════════════════════════════════════════════════════════════
    elif mod_key == "moderasi":
        z        = data.get("z", "variabel moderator")
        x_var    = data.get("x", ind_str)
        r2       = data.get("r2")
        adj_r2   = data.get("adj_r2")
        jn_point = data.get("johnson_neyman")

        paragraf1 = (
            f"Analisis moderasi dilakukan untuk menguji apakah {z} memoderasi "
            f"hubungan antara {x_var} dan {dep} "
            "(Aiken & West, 1991; Hayes, 2013). "
            "Pengujian dilakukan dengan memasukkan suku interaksi (X \u00d7 Z) ke dalam "
            "model regresi, di mana signifikansi suku interaksi menjadi indikator utama "
            "adanya efek moderasi. "
        )
        if r2 is not None:
            paragraf1 += (
                f"Model moderasi menjelaskan {r2 * 100:.1f}% variansi {dep} "
                f"(R\u00b2 = {r2:.3f}"
                + (f", R\u00b2 Adjusted = {adj_r2:.3f}" if adj_r2 is not None else "")
                + "). "
            )

        paragraf2 = ""
        coef_df = data.get("coef_table")
        interact_lines = []
        if coef_df is not None and not coef_df.empty:
            p_col   = next((c for c in coef_df.columns
                            if c.lower() in ("p", "p-value", "sig")), None)
            b_col   = next((c for c in coef_df.columns
                            if c.lower() in ("\u03b2", "b", "coef", "koefisien")), None)
            var_col = coef_df.columns[0]
            if p_col:
                for _, row in coef_df.iterrows():
                    vn = str(row[var_col])
                    if (":" in vn or "\u00d7" in vn or "*" in vn
                            or "interaction" in vn.lower()):
                        try:
                            pv = float(row[p_col])
                            bv = float(row[b_col]) if b_col else None
                            sig_int = _sig_str(pv)
                            ket = (
                                f"Suku interaksi {vn} {sig_int} (p = {pv:.3f}"
                                + (f", \u03b2 = {bv:.3f}" if bv is not None else "")
                                + "), "
                            )
                            if pv < 0.05:
                                ket += (
                                    f"menunjukkan bahwa {z} secara signifikan memoderasi "
                                    f"hubungan {x_var} \u2192 {dep}."
                                )
                            else:
                                ket += (
                                    f"menunjukkan bahwa {z} tidak terbukti memoderasi "
                                    f"hubungan {x_var} \u2192 {dep}."
                                )
                            interact_lines.append(ket)
                        except Exception:
                            pass
        if interact_lines:
            paragraf2 = " ".join(interact_lines)

        paragraf3 = ""
        if jn_point is not None:
            paragraf3 = (
                f"Analisis Johnson-Neyman mengidentifikasi titik transisi pada nilai "
                f"{z} = {float(jn_point):.3f}, di mana di bawah nilai tersebut hubungan "
                f"{x_var} \u2192 {dep} berubah signifikansinya (Johnson & Neyman, 1936). "
                "Temuan ini mengimplikasikan perlunya mempertimbangkan kondisi batas "
                "dalam perumusan rekomendasi praktis berbasis hasil penelitian ini."
            )

        return "\n\n".join(p for p in [paragraf1, paragraf2, paragraf3] if p.strip())

    # ══════════════════════════════════════════════════════════════════════════
    # ANOVA
    # ══════════════════════════════════════════════════════════════════════════
    elif mod_key == "anova":
        anova_df       = data.get("anova_table")
        eta2           = data.get("eta_squared")
        posthoc_df     = data.get("posthoc_table")
        posthoc_method = data.get("posthoc_method", "Tukey HSD")
        n_groups       = data.get("n_groups")
        num_col        = data.get("num_col", "variabel dependen")

        paragraf1 = (
            f"Uji analisis varians satu arah (One-Way ANOVA) dilakukan untuk menguji "
            f"perbedaan rata-rata {num_col} di antara kelompok yang dibandingkan. "
        )
        if n_groups:
            paragraf1 += f"Analisis melibatkan {n_groups} kelompok. "

        if anova_df is not None and not anova_df.empty:
            p_col = next((c for c in anova_df.columns
                          if c.lower() in ("p", "p-value", "pr(>f)", "p_value")), None)
            f_col = next((c for c in anova_df.columns
                          if c.lower() in ("f", "f-ratio", "f_stat")), None)
            if p_col:
                try:
                    pv = float(anova_df[p_col].iloc[0])
                    fv = float(anova_df[f_col].iloc[0]) if f_col else None
                    sig = _sig_str(pv)
                    paragraf1 += (
                        f"Hasil uji F"
                        + (f" = {fv:.3f} " if fv else " ")
                        + f"menunjukkan {sig} perbedaan rata-rata antar kelompok "
                        f"(p = {pv:.3f}). "
                    )
                    if pv < 0.05:
                        paragraf1 += (
                            "Dengan demikian, hipotesis nol yang menyatakan tidak terdapat "
                            "perbedaan rata-rata antar kelompok ditolak pada tingkat "
                            "signifikansi \u03b1 = .05. "
                        )
                    else:
                        paragraf1 += (
                            "Dengan demikian, tidak terdapat cukup bukti untuk menolak "
                            "hipotesis nol. "
                        )
                except Exception:
                    pass

        paragraf2 = ""
        if eta2 is not None:
            kat = _kat_eta2(float(eta2))
            paragraf2 = (
                f"Ukuran efek diukur menggunakan Eta Squared "
                f"(\u03b7\u00b2 = {float(eta2):.3f}), yang termasuk kategori {kat} "
                "berdasarkan konvensi Cohen (1988). "
                f"Nilai ini mengindikasikan bahwa {float(eta2) * 100:.1f}% variansi total "
                f"{num_col} dapat dijelaskan oleh perbedaan antar kelompok. "
                "Interpretasi ukuran efek penting untuk menilai signifikansi praktis "
                "di luar sekadar signifikansi statistik (Cohen, 1988; Field, 2018)."
            )

        paragraf3 = ""
        if posthoc_df is not None and not posthoc_df.empty:
            paragraf3 = (
                f"Untuk mengidentifikasi pasangan kelompok yang berbeda secara signifikan, "
                f"dilakukan uji post-hoc {posthoc_method}. "
                "Uji post-hoc berfungsi mengendalikan tingkat kesalahan tipe I pada "
                "perbandingan berganda (Tukey, 1949). "
                "Hasil selengkapnya dapat dilihat pada tabel post-hoc yang disajikan."
            )

        return "\n\n".join(p for p in [paragraf1, paragraf2, paragraf3] if p.strip())

    # ══════════════════════════════════════════════════════════════════════════
    # UJI BEDA
    # ══════════════════════════════════════════════════════════════════════════
    elif mod_key == "uji_beda":
        g1   = data.get("g1_name", "Kelompok 1")
        g2   = data.get("g2_name", "Kelompok 2")
        pval = data.get("p_value")
        stat = data.get("statistic")
        eff  = data.get("effect_size")
        uji  = data.get("uji_type", "t-test independen")
        m1   = data.get("g1_mean")
        m2   = data.get("g2_mean")

        paragraf1 = (
            f"Pengujian perbedaan dua kelompok dilakukan menggunakan {uji} "
            f"untuk membandingkan {g1} dan {g2}. "
        )
        if m1 is not None and m2 is not None:
            paragraf1 += (
                f"Rata-rata {g1} = {float(m1):.3f} "
                f"dan rata-rata {g2} = {float(m2):.3f}. "
            )

        paragraf2 = ""
        if pval is not None:
            sig = _sig_str(float(pval))
            ada = "terdapat" if float(pval) < 0.05 else "tidak terdapat"
            paragraf2 = (
                f"Hasil pengujian menunjukkan {ada} perbedaan yang {sig} secara statistik "
                f"antara {g1} dan {g2} "
                + (f"(statistik uji = {float(stat):.3f}, " if stat is not None else "(")
                + f"p = {float(pval):.3f}). "
                "Keputusan pengujian didasarkan pada tingkat signifikansi \u03b1 = .05 "
                "(Field, 2018; Cohen, 1988)."
            )

        paragraf3 = ""
        if eff is not None:
            kat = _kat_d(float(eff))
            paragraf3 = (
                f"Relevansi praktis perbedaan dinilai melalui ukuran efek "
                f"Cohen\u2019s d = {float(eff):.3f}, yang termasuk kategori {kat} "
                "menurut konvensi Cohen (1988). "
                "Ukuran efek yang signifikan secara statistik tidak selalu bermakna "
                "secara praktis, sehingga interpretasi Cohen\u2019s d menjadi penting "
                "untuk melengkapi keputusan inferensial."
            )

        return "\n\n".join(p for p in [paragraf1, paragraf2, paragraf3] if p.strip())

    # ══════════════════════════════════════════════════════════════════════════
    # SEM
    # ══════════════════════════════════════════════════════════════════════════
    elif mod_key == "sem":
        fit_df  = data.get("fit_indices")
        n_obs   = data.get("n_obs", "?")

        paragraf1 = (
            "Structural Equation Modeling (SEM) dilakukan secara terintegrasi dengan "
            "Confirmatory Factor Analysis (CFA) untuk menguji model pengukuran dan "
            "model struktural secara simultan. "
            f"Estimasi parameter dilakukan terhadap {n_obs} observasi. "
            "Pendekatan ini memungkinkan pengujian hubungan kausal antar variabel laten "
            "dengan mempertimbangkan kesalahan pengukuran "
            "(Hair et al., 2010; Hu & Bentler, 1999). "
        )

        paragraf2 = ""
        if fit_df is not None:
            try:
                is_df   = hasattr(fit_df, "empty")
                is_list = isinstance(fit_df, list)
                ok      = (is_df and not fit_df.empty) or (is_list and len(fit_df) > 0)
                if ok:
                    fit_data = fit_df if is_list else fit_df.to_dict("records")
                    idx_lines = []
                    thresholds = {
                        "cfi":   (0.90, "\u2265 .90", True),
                        "tli":   (0.90, "\u2265 .90", True),
                        "rmsea": (0.08, "\u2264 .08", False),
                        "srmr":  (0.08, "\u2264 .08", False),
                    }
                    for rec in fit_data:
                        if not isinstance(rec, dict):
                            continue
                        idx = str(rec.get("Indeks", rec.get("Index", ""))).lower()
                        val = rec.get("Nilai", rec.get("Value", rec.get("Hasil", "")))
                        for thr_key, (thr_val, thr_str, higher_better) in thresholds.items():
                            if thr_key in idx:
                                try:
                                    v  = float(str(val).replace("<", "").replace(">", ""))
                                    ok_fit = (v >= thr_val) if higher_better else (v <= thr_val)
                                    status = "memenuhi" if ok_fit else "tidak memenuhi"
                                    idx_lines.append(
                                        f"{thr_key.upper()} = {v:.3f} "
                                        f"({status} kriteria {thr_str})"
                                    )
                                except Exception:
                                    pass
                    if idx_lines:
                        paragraf2 = (
                            "Evaluasi kecocokan model (goodness-of-fit) menunjukkan: "
                            + "; ".join(idx_lines) + ". "
                            "Indeks kecocokan dievaluasi berdasarkan kriteria Hu dan Bentler "
                            "(1999): CFI dan TLI \u2265 .90, RMSEA \u2264 .08, SRMR \u2264 .08."
                        )
            except Exception:
                pass

        if not paragraf2:
            paragraf2 = (
                "Evaluasi kecocokan model dilakukan berdasarkan indeks CFI, TLI, RMSEA, "
                "dan SRMR (Hu & Bentler, 1999). "
                "Kriteria: CFI \u2265 .90, TLI \u2265 .90, RMSEA \u2264 .08, SRMR \u2264 .08. "
                "Interpretasi lengkap indeks kecocokan disajikan pada tabel di atas."
            )

        paragraf3 = (
            "Factor loadings pada model CFA mencerminkan validitas konvergen indikator "
            "terhadap konstruk laten. Loading \u2265 .50 dianggap cukup, sedangkan "
            "loading \u2265 .70 mengindikasikan validitas yang kuat (Hair et al., 2010). "
            "Estimasi jalur struktural dapat diinterpretasikan setelah memastikan "
            "kecocokan model yang memadai."
        )

        return "\n\n".join(p for p in [paragraf1, paragraf2, paragraf3] if p.strip())

    # ══════════════════════════════════════════════════════════════════════════
    # EFA — Analisis Faktor Eksploratori
    # ══════════════════════════════════════════════════════════════════════════
    elif mod_key == "efa":
        kmo      = data.get("kmo")
        kmo_lbl  = data.get("kmo_label", "")
        bart_p   = data.get("bartlett_p")
        n_fac    = data.get("n_factors")
        rotation = data.get("rotation", "Varimax")
        tot_v    = data.get("total_var")
        load_df  = data.get("loading_df")

        paragraf1 = (
            "Analisis Faktor Eksploratori (EFA) dilakukan untuk mengidentifikasi "
            "struktur laten yang mendasari seperangkat indikator pengukuran, "
            "dengan tujuan mereduksi dimensi data sekaligus mengungkap konstruk yang "
            "tidak dapat diobservasi secara langsung "
            "(Fabrigar et al., 1999; Hair et al., 2010). "
        )

        # Kelayakan data
        kel_lines = []
        if kmo is not None:
            kmo_f = float(kmo)
            kat_kmo = kmo_lbl if kmo_lbl else (
                "sangat memuaskan" if kmo_f >= 0.90 else
                "memuaskan"        if kmo_f >= 0.80 else
                "layak (middling)" if kmo_f >= 0.70 else
                "cukup (mediocre)" if kmo_f >= 0.60 else
                "tidak layak"
            )
            kel_lines.append(
                f"nilai Kaiser-Meyer-Olkin (KMO) = {kmo_f:.3f} ({kat_kmo}, Kaiser, 1974)"
            )
        if bart_p is not None:
            sig_bart = "signifikan" if float(bart_p) < 0.05 else "tidak signifikan"
            kel_lines.append(
                f"uji Bartlett of Sphericity {sig_bart} "
                f"(p = {float(bart_p):.4f}, Bartlett, 1950)"
            )

        paragraf2 = ""
        if kel_lines:
            layak = (
                (kmo is None or float(kmo) >= 0.60)
                and (bart_p is None or float(bart_p) < 0.05)
            )
            paragraf2 = (
                "Evaluasi kelayakan data untuk analisis faktor dilakukan melalui: "
                + " dan ".join(kel_lines) + ". "
                + (
                    "Data dinyatakan layak untuk dianalisis menggunakan EFA. "
                    if layak else
                    "Hasil uji mengindikasikan bahwa data perlu diperiksa kembali "
                    "sebelum dilanjutkan ke tahap analisis faktor. "
                )
            )

        paragraf3 = ""
        if n_fac is not None:
            paragraf3 = (
                f"Berdasarkan kriteria Kaiser (eigenvalue > 1) dan scree plot "
                f"(Cattell, 1966), diekstrak {n_fac} faktor menggunakan metode "
                f"rotasi {rotation}. "
            )
            if tot_v is not None:
                paragraf3 += (
                    f"Solusi faktor yang dihasilkan mampu menjelaskan "
                    f"{float(tot_v):.2f}% total variansi variabel-variabel yang dianalisis. "
                )

        # Loading summary
        paragraf4 = ""
        if load_df is not None and hasattr(load_df, "empty") and not load_df.empty:
            try:
                fac_cols = [
                    c for c in load_df.columns
                    if c.lower().startswith("factor")
                    or (c.lower().startswith("f") and c[1:].isdigit())
                ]
                if fac_cols:
                    n_high = 0
                    for col in fac_cols:
                        vals = pd.to_numeric(load_df[col], errors="coerce").abs()
                        n_high += int((vals >= 0.50).sum())
                    paragraf4 = (
                        f"Interpretasi faktor didasarkan pada nilai loading \u2265 .50 "
                        "sebagai kriteria item yang bermakna secara substantif "
                        "(Fabrigar et al., 1999). "
                        f"Sejumlah {n_high} item memiliki loading memadai pada faktor terkait. "
                        "Hasil EFA ini dapat menjadi dasar pengembangan instrumen lebih lanjut "
                        "melalui Confirmatory Factor Analysis (CFA) pada sampel independen "
                        "(Hair et al., 2010)."
                    )
            except Exception:
                pass

        if not paragraf4:
            paragraf4 = (
                "Interpretasi faktor dilakukan berdasarkan nilai factor loading setiap item, "
                "di mana loading \u2265 .50 dianggap bermakna secara substantif. "
                "Temuan EFA ini bersifat eksploratori dan perlu dikonfirmasi pada penelitian "
                "selanjutnya menggunakan CFA pada sampel yang berbeda "
                "(Fabrigar et al., 1999)."
            )

        return "\n\n".join(p for p in [paragraf1, paragraf2, paragraf3, paragraf4] if p.strip())

    # ══════════════════════════════════════════════════════════════════════════
    # CFA — Confirmatory Factor Analysis
    # ══════════════════════════════════════════════════════════════════════════
    elif mod_key == "cfa":
        factor_map  = data.get("factor_map", {})
        n_konstruk  = len(factor_map)
        n_obs       = data.get("n_obs", "?")
        fit_records = data.get("fit_df_records", [])
        ave_records = data.get("ave_cr_df_records", [])

        paragraf1 = (
            "Confirmatory Factor Analysis (CFA) dilakukan untuk menguji validitas "
            f"konstruk model pengukuran yang terdiri dari {n_konstruk} konstruk laten "
            f"dengan {n_obs} observasi. "
            "CFA merupakan pendekatan berbasis teori yang menguji sejauh mana model "
            "pengukuran yang ditetapkan sesuai dengan data empiris "
            "(Hair et al., 2010; Hu & Bentler, 1999). "
            "Estimasi parameter menggunakan metode Maximum Likelihood (ML)."
        )

        paragraf2 = ""
        if fit_records:
            try:
                fit_df2 = pd.DataFrame(fit_records)
                if "Status" in fit_df2.columns:
                    n_good  = int(fit_df2["Status"].str.contains("\u2705").sum())
                    n_total = len(fit_df2)
                    pct     = n_good / n_total * 100
                    if n_good / n_total >= 0.75:
                        kat = "diterima (good fit)"
                    elif n_good / n_total >= 0.50:
                        kat = "diterima secara marginal (acceptable fit)"
                    else:
                        kat = ("tidak dapat diterima (poor fit) \u2014 "
                               "pertimbangkan respecifikasi model")
                    paragraf2 = (
                        f"Evaluasi kecocokan model menunjukkan {n_good} dari {n_total} "
                        f"indeks fit ({pct:.0f}%) memenuhi threshold yang ditetapkan, "
                        f"sehingga model secara keseluruhan dinyatakan {kat} "
                        "(Hu & Bentler, 1999). "
                        "Kriteria evaluasi meliputi CFI \u2265 .90, TLI \u2265 .90, "
                        "RMSEA \u2264 .08, dan SRMR \u2264 .08."
                    )
            except Exception:
                pass

        if not paragraf2:
            paragraf2 = (
                "Evaluasi kecocokan model dilakukan berdasarkan indeks CFI, TLI, "
                "RMSEA, dan SRMR (Hu & Bentler, 1999): "
                "CFI \u2265 .90, TLI \u2265 .90, RMSEA \u2264 .08, SRMR \u2264 .08."
            )

        paragraf3 = ""
        if ave_records:
            try:
                ave_df2 = pd.DataFrame(ave_records)
                ave_col = next(
                    (c for c in ave_df2.columns if "ave" in c.lower()), None
                )
                cr_col = next(
                    (c for c in ave_df2.columns
                     if "cr" in c.lower() or "composite" in c.lower()), None
                )
                if ave_col and cr_col:
                    n_ave = int(
                        (pd.to_numeric(ave_df2[ave_col], errors="coerce") >= 0.50).sum()
                    )
                    n_cr = int(
                        (pd.to_numeric(ave_df2[cr_col], errors="coerce") >= 0.70).sum()
                    )
                    n_tot = len(ave_df2)
                    paragraf3 = (
                        "Validitas konvergen dievaluasi melalui Average Variance Extracted "
                        f"(AVE) dan Composite Reliability (CR). "
                        f"AVE \u2265 .50 terpenuhi pada {n_ave}/{n_tot} konstruk, "
                        f"CR \u2265 .70 terpenuhi pada {n_cr}/{n_tot} konstruk "
                        "(Fornell & Larcker, 1981; Hair et al., 2010). "
                    )
                    if n_ave == n_tot and n_cr == n_tot:
                        paragraf3 += (
                            "Seluruh konstruk memenuhi kriteria validitas konvergen, "
                            "mengindikasikan bahwa indikator-indikator secara konsisten "
                            "mengukur konstruk laten yang dimaksud."
                        )
                    else:
                        paragraf3 += (
                            "Konstruk yang tidak memenuhi kriteria perlu ditinjau ulang, "
                            "baik melalui modifikasi model maupun penghapusan indikator "
                            "yang bermasalah."
                        )
            except Exception:
                pass

        return "\n\n".join(p for p in [paragraf1, paragraf2, paragraf3] if p.strip())

    # ══════════════════════════════════════════════════════════════════════════
    # OUTLIER
    # ══════════════════════════════════════════════════════════════════════════
    elif mod_key == "outlier":
        n        = data.get("total_outliers", 0)
        n_total  = data.get("n_total", 0)
        pct      = data.get("pct_outliers", 0.0)
        variabel = data.get("variabel", "variabel yang dianalisis")
        method   = data.get("method", "IQR")

        if n > 0:
            return (
                f"Deteksi outlier pada variabel {variabel} menggunakan metode {method} "
                f"mengidentifikasi {n} observasi ({float(pct):.1f}% dari {n_total} total data) "
                "sebagai nilai pencilan (outlier). "
                "Keberadaan outlier berpotensi mendistorsi estimasi parameter regresi OLS "
                "maupun hasil uji statistik berbasis asumsi normalitas "
                "(Field, 2018; Ghozali, 2018). "
                "Penanganan outlier harus dilakukan berdasarkan pertimbangan substantif: "
                "jika outlier merupakan kesalahan pengukuran atau entri data, penghapusan "
                "dapat dibenarkan; namun jika mencerminkan variasi alami populasi, outlier "
                "sebaiknya dipertahankan menggunakan metode estimasi yang lebih robust. "
                "Analisis sensitivitas (dengan dan tanpa outlier) direkomendasikan untuk "
                "menilai pengaruhnya terhadap kesimpulan penelitian."
            )
        else:
            return (
                f"Hasil deteksi outlier pada variabel {variabel} menggunakan metode {method} "
                f"tidak menemukan nilai pencilan dari {n_total} observasi yang diperiksa. "
                "Seluruh data berada dalam rentang yang diharapkan berdasarkan distribusi "
                "empiris variabel, sehingga dinyatakan layak untuk dianalisis lebih lanjut "
                "tanpa perlakuan khusus."
            )

    # ══════════════════════════════════════════════════════════════════════════
    # ANALISIS KELOMPOK
    # ══════════════════════════════════════════════════════════════════════════
    elif mod_key == "kelompok":
        cat   = data.get("cat", "kelompok")
        num   = data.get("num", "variabel")
        pval  = data.get("p_value")
        fstat = data.get("f_stat")
        best  = data.get("best_group")
        worst = data.get("worst_group")

        paragraf1 = (
            f"Analisis perbandingan variabel \u2018{num}\u2019 berdasarkan kategori "
            f"\u2018{cat}\u2019 dilakukan untuk mengidentifikasi perbedaan karakteristik "
            "antar kelompok secara statistik (Field, 2018). "
        )

        paragraf2 = ""
        if pval is not None:
            ada = "terdapat" if float(pval) < 0.05 else "tidak terdapat"
            sig = _sig_str(float(pval))
            paragraf2 = (
                f"Hasil pengujian menunjukkan {ada} perbedaan yang {sig} "
                f"pada variabel {num} antar kelompok {cat} "
                + (f"(F = {float(fstat):.3f}, " if fstat else "(")
                + f"p = {float(pval):.3f}). "
            )
            if best and float(pval) < 0.05:
                paragraf2 += (
                    f"Kelompok {best} memiliki rata-rata tertinggi"
                    + (f", sedangkan kelompok {worst} memiliki rata-rata terendah. "
                       if worst else ". ")
                )

        paragraf3 = (
            "Temuan ini memberikan implikasi bagi pengambilan keputusan berbasis kelompok. "
            "Perbedaan yang signifikan mengindikasikan perlunya strategi atau intervensi "
            "yang disesuaikan dengan karakteristik masing-masing kelompok."
        )

        return "\n\n".join(p for p in [paragraf1, paragraf2, paragraf3] if p.strip())

    # ══════════════════════════════════════════════════════════════════════════
    # RELIABILITAS ICC
    # ══════════════════════════════════════════════════════════════════════════
    elif mod_key == "reliabilitas_icc":
        rec_model   = data.get("rec_model", "ICC(2,1)")
        n_subj      = data.get("n_subj", "?")
        n_rater     = data.get("n_rater", "?")
        use_type    = data.get("use_type", "rater agreement")
        icc_records = data.get("icc_df", [])

        paragraf1 = (
            "Uji reliabilitas menggunakan Intraclass Correlation Coefficient (ICC) "
            "dilakukan untuk mengevaluasi tingkat konsistensi dan keandalan pengukuran "
            f"dalam konteks {use_type}, "
            f"melibatkan {n_subj} subjek dan {n_rater} rater atau sesi pengukuran. "
            "ICC merupakan indeks yang digunakan secara luas untuk menilai reliabilitas "
            "antar-penilai maupun tes-retes pada data pengukuran berulang "
            "(Koo & Mae, 2016; Shrout & Fleiss, 1979). "
        )

        paragraf2 = ""
        if icc_records:
            try:
                for row in icc_records:
                    if isinstance(row, dict) and row.get("Model") == rec_model:
                        icc_val = row.get("ICC")
                        p_val   = row.get("p_value")
                        ci_lo   = row.get("CI_Lower")
                        ci_hi   = row.get("CI_Upper")
                        if icc_val is not None:
                            v = float(icc_val)
                            if v >= 0.90:
                                kat = "sangat baik (excellent)"
                                imp = ("pengukuran dapat diandalkan untuk pengambilan "
                                       "keputusan klinis maupun penelitian")
                            elif v >= 0.75:
                                kat = "baik (good)"
                                imp = ("pengukuran memiliki konsistensi yang cukup "
                                       "untuk keperluan penelitian")
                            elif v >= 0.50:
                                kat = "sedang (moderate)"
                                imp = ("pengukuran perlu ditingkatkan sebelum "
                                       "digunakan secara luas")
                            else:
                                kat = "buruk (poor)"
                                imp = "prosedur pengukuran perlu direvisi secara substansial"
                            paragraf2 = (
                                f"Model ICC yang direkomendasikan ({rec_model}) "
                                f"menghasilkan ICC = {v:.4f} ({kat})"
                                + (f", 95% CI [{float(ci_lo):.4f}, {float(ci_hi):.4f}]"
                                   if ci_lo is not None and ci_hi is not None else "")
                                + (f", p = {float(p_val):.4f}" if p_val is not None else "")
                                + f". Nilai ini mengindikasikan bahwa {imp} "
                                  "(Koo & Mae, 2016). "
                            )
                        break
            except Exception:
                pass

        if not paragraf2:
            paragraf2 = (
                "Interpretasi ICC mengikuti kriteria Koo dan Mae (2016): "
                "ICC < .50 = buruk, .50\u2013.75 = sedang, .75\u2013.90 = baik, "
                "\u2265 .90 = sangat baik. "
                "Nilai ICC yang tinggi mengindikasikan konsistensi pengukuran yang "
                "dapat diandalkan antar rater maupun antar waktu pengukuran."
            )

        paragraf3 = (
            "Pemilihan model ICC yang tepat bergantung pada desain studi: "
            "ICC(1) untuk rater acak tanpa efek campuran; "
            "ICC(2) untuk rater yang dipilih dan digeneralisasikan ke populasi; "
            "ICC(3) untuk rater yang dipilih tanpa generalisasi "
            "(Shrout & Fleiss, 1979). "
            "Perbedaan antara \u2018agreement\u2019 dan \u2018consistency\u2019 perlu "
            "diperhatikan: agreement memperhitungkan perbedaan sistematis antar rater, "
            "sedangkan consistency hanya menilai konsistensi relatif."
        )

        return "\n\n".join(p for p in [paragraf1, paragraf2, paragraf3] if p.strip())

    # ══════════════════════════════════════════════════════════════════════════
    # UJI ASUMSI PRA-ANALISIS
    # ══════════════════════════════════════════════════════════════════════════
    elif mod_key == "uji_asumsi":
        rec = data.get("rekomendasi", {})
        if not isinstance(rec, dict):
            return (
                "Uji asumsi pra-analisis telah dilakukan untuk menentukan pendekatan "
                "statistik yang paling sesuai dengan karakteristik data. "
                "Hasil uji asumsi menjadi dasar pemilihan metode analisis, apakah "
                "parametrik atau non-parametrik (Field, 2018)."
            )

        level  = rec.get("level", "")
        skor   = rec.get("skor_lulus", "?")
        total  = rec.get("total_uji", "?")
        pct    = rec.get("pct_lulus", "?")
        detail = rec.get("detail", {})

        paragraf1 = (
            "Serangkaian uji asumsi statistik dilakukan sebagai prosedur pra-analisis "
            "untuk menentukan kesesuaian data terhadap persyaratan metode statistik parametrik. "
            f"Hasil evaluasi menunjukkan {skor} dari {total} uji asumsi terpenuhi "
            f"({pct}%)"
            + (f", sehingga data direkomendasikan untuk analisis {level}. "
               if level else ". ")
        )

        paragraf2 = ""
        if isinstance(detail, dict) and detail:
            asumsi_lines = []
            labels = {
                "normalitas_univariat":   ("Normalitas univariat (Shapiro-Wilk)",
                                           "n_normal", "n_variabel"),
                "normalitas_multivariat": ("Normalitas multivariat (Mardia\u2019s test)",
                                           "p_skew", "p_kurt"),
                "homogenitas":            ("Homogenitas varians (Levene & Bartlett)",
                                           "n_lulus", "n_uji"),
                "linieritas":             ("Linieritas (Ramsey RESET test)",
                                           "n_lulus", "n_uji"),
            }
            for key, info in detail.items():
                if not isinstance(info, dict):
                    continue
                lbl_tuple = labels.get(key)
                lbl   = lbl_tuple[0] if lbl_tuple else key
                lulus = info.get("lulus", False)
                status = "terpenuhi" if lulus else "tidak terpenuhi"
                if key == "normalitas_univariat":
                    n_n = info.get("n_normal", "?")
                    n_v = info.get("n_variabel", "?")
                    ket = f"{n_n}/{n_v} variabel berdistribusi normal"
                elif key == "normalitas_multivariat":
                    ps = info.get("p_skew", "?")
                    pk = info.get("p_kurt", "?")
                    ket = f"skewness p = {ps}, kurtosis p = {pk}"
                elif key == "homogenitas":
                    nl = info.get("n_lulus", "?")
                    nu = info.get("n_uji", "?")
                    ket = f"{nl}/{nu} kelompok homogen"
                elif key == "linieritas":
                    nl = info.get("n_lulus", "?")
                    nu = info.get("n_uji", "?")
                    ket = f"{nl}/{nu} pasangan memenuhi asumsi linieritas"
                else:
                    ket = ""
                asumsi_lines.append(
                    f"{lbl}: {status} ({ket})" if ket else f"{lbl}: {status}"
                )
            if asumsi_lines:
                paragraf2 = (
                    "Rincian hasil uji asumsi per komponen: "
                    + "; ".join(asumsi_lines) + ". "
                )

        paragraf3 = (
            "Pemenuhan asumsi statistik merupakan prasyarat validitas inferensi pada "
            "metode parametrik. Apabila asumsi normalitas tidak terpenuhi, penggunaan "
            "uji non-parametrik (Mann-Whitney, Kruskal-Wallis) atau transformasi data "
            "direkomendasikan. Pelanggaran homogenitas varians dapat diatasi dengan "
            "uji Welch atau estimasi robust (Field, 2018)."
        )

        return "\n\n".join(p for p in [paragraf1, paragraf2, paragraf3] if p.strip())

    # ══════════════════════════════════════════════════════════════════════════
    # REGRESI ROBUST
    # ══════════════════════════════════════════════════════════════════════════
    elif mod_key == "ols_robust":
        dep_var   = data.get("dep_var", "variabel dependen")
        ind_vars  = data.get("ind_vars", [])
        ind_s     = ", ".join(ind_vars) if ind_vars else "variabel prediktor"
        estimator = data.get("estimator", "Huber-M")
        n_low     = data.get("n_low_weight", 0)
        n_obs     = data.get("n_obs", "?")
        n_changed = data.get("n_changed", 0)
        ols_rmse  = data.get("ols_rmse")
        rlm_rmse  = data.get("rlm_rmse")

        paragraf1 = (
            f"Regresi Robust menggunakan estimator M ({estimator}) dilakukan untuk "
            f"memodelkan {dep_var} berdasarkan {ind_s} (N = {n_obs}). "
            "Pendekatan ini dipilih karena estimator OLS sensitif terhadap outlier dan "
            "leverage points yang dapat mendistorsi estimasi koefisien secara substansial. "
            "Regresi Robust mereduksi pengaruh observasi bermasalah dengan memberikan "
            "bobot lebih rendah secara iteratif (Huber, 1973; Greene, 2012)."
        )

        p2_lines = []
        if n_low:
            p2_lines.append(
                f"sebanyak {n_low} observasi memperoleh bobot rendah (< 0.5), "
                "mengindikasikan keberadaan outlier atau leverage points"
            )
        if n_changed:
            p2_lines.append(
                f"{n_changed} koefisien mengalami perubahan > 10% dibandingkan OLS, "
                "menunjukkan sensitivitas OLS terhadap data bermasalah"
            )
        if ols_rmse is not None and rlm_rmse is not None:
            rlm_f = float(rlm_rmse)
            ols_f = float(ols_rmse)
            lebih = "lebih rendah" if rlm_f < ols_f else "sebanding"
            p2_lines.append(
                f"RMSE Robust ({rlm_f:.4f}) {lebih} dibandingkan OLS ({ols_f:.4f})"
            )

        paragraf2 = ""
        if p2_lines:
            paragraf2 = (
                "Hasil diagnostik regresi robust menunjukkan: "
                + "; ".join(p2_lines) + ". "
                "Perbandingan koefisien OLS dan Robust disarankan untuk menilai "
                "robustness temuan penelitian (Huber, 1973)."
            )

        return "\n\n".join(p for p in [paragraf1, paragraf2] if p.strip())

    # ══════════════════════════════════════════════════════════════════════════
    # WLS
    # ══════════════════════════════════════════════════════════════════════════
    elif mod_key == "ols_wls":
        dep_var       = data.get("dep_var", "variabel dependen")
        ind_vars      = data.get("ind_vars", [])
        ind_s         = ", ".join(ind_vars) if ind_vars else "variabel prediktor"
        weight_method = data.get("weight_method", "1/|\u03b5|")
        n_obs         = data.get("n_obs", "?")
        ols_g         = data.get("ols_glejser_p")
        wls_g         = data.get("wls_glejser_p")
        ols_r         = data.get("ols_rmse")
        wls_r         = data.get("wls_rmse")
        n_changed     = data.get("n_changed", 0)

        paragraf1 = (
            f"Weighted Least Squares (WLS) diterapkan untuk mengatasi masalah "
            f"heteroskedastisitas pada model {dep_var} ~ {ind_s} (N = {n_obs}), "
            f"menggunakan skema pembobotan {weight_method}. "
            "Heteroskedastisitas melanggar asumsi OLS dan menghasilkan estimasi yang "
            "tidak efisien, sehingga inferensi berbasis standard error OLS menjadi "
            "tidak valid (Greene, 2012; White, 1980). "
        )

        p2_lines = []
        if ols_g is not None and wls_g is not None:
            ols_gf = float(ols_g)
            wls_gf = float(wls_g)
            if ols_gf < 0.05 and wls_gf >= 0.05:
                status = "WLS berhasil mengatasi heteroskedastisitas"
            elif ols_gf < 0.05 and wls_gf < 0.05:
                status = ("heteroskedastisitas masih terdeteksi setelah WLS "
                          "\u2014 pertimbangkan transformasi tambahan")
            else:
                status = ("OLS tidak menunjukkan heteroskedastisitas signifikan, "
                          "WLS sebagai robustness check")
            p2_lines.append(
                f"uji Glejser: OLS p = {ols_gf:.4f} \u2192 WLS p = {wls_gf:.4f} "
                f"({status})"
            )
        if ols_r is not None and wls_r is not None:
            wls_rf = float(wls_r)
            ols_rf = float(ols_r)
            p2_lines.append(
                f"RMSE: OLS = {ols_rf:.4f}, WLS = {wls_rf:.4f} "
                f"({'WLS lebih efisien' if wls_rf < ols_rf else 'OLS sebanding'})"
            )
        if n_changed:
            p2_lines.append(f"{n_changed} koefisien berubah > 10% dari OLS ke WLS")

        paragraf2 = ""
        if p2_lines:
            paragraf2 = (
                "Perbandingan diagnostik OLS versus WLS: "
                + "; ".join(p2_lines) + ". "
                "Koefisien WLS yang berbeda signifikan dari OLS mengindikasikan bahwa "
                "heteroskedastisitas berpengaruh pada estimasi (Greene, 2012)."
            )

        return "\n\n".join(p for p in [paragraf1, paragraf2] if p.strip())

    # ══════════════════════════════════════════════════════════════════════════
    # PERBANDINGAN MODEL REGRESI
    # ══════════════════════════════════════════════════════════════════════════
    elif mod_key == "ols_robust_comparison":
        dep_var    = data.get("dep_var", "variabel dependen")
        ind_vars   = data.get("ind_vars", [])
        ind_s      = ", ".join(ind_vars) if ind_vars else "variabel prediktor"
        best_model = data.get("best_model", "OLS (Baseline)")
        n_obs      = data.get("n_obs", "?")

        paragraf1 = (
            "Perbandingan empat pendekatan regresi \u2014 OLS (baseline), RLM Huber-M, "
            f"RLM Bisquare, dan WLS \u2014 dilakukan untuk memilih estimator yang paling "
            f"tepat dalam memodelkan {dep_var} ~ {ind_s} (N = {n_obs}). "
            "Pendekatan komparatif ini memastikan bahwa kesimpulan penelitian bersifat "
            "robust terhadap berbagai kondisi data (Greene, 2012; Huber, 1973)."
        )

        paragraf2 = (
            f"Berdasarkan kriteria RMSE sebagai ukuran akurasi prediksi, model terbaik "
            f"adalah {best_model}. "
            "RMSE yang lebih rendah mengindikasikan deviasi prediksi yang lebih kecil, "
            "sehingga model tersebut direkomendasikan untuk analisis lanjutan. "
            "Perbandingan koefisien antar model disarankan untuk menilai stabilitas "
            "estimasi dan mengidentifikasi pengaruh observasi bermasalah."
        )

        return "\n\n".join(p for p in [paragraf1, paragraf2] if p.strip())

    # ══════════════════════════════════════════════════════════════════════════
    # COMPUTE VARIABEL
    # ══════════════════════════════════════════════════════════════════════════
    elif mod_key == "compute":
        compute_log = data.get("compute_log", [])
        n_ops       = len(compute_log)

        if n_ops == 0:
            return (
                "Tidak terdapat operasi komputasi variabel yang tercatat dalam sesi ini. "
                "Transformasi atau pembentukan variabel baru dapat dilakukan melalui modul "
                "Compute Variabel sebelum analisis statistik utama dijalankan."
            )

        methods  = list({e.get("method", "") for e in compute_log if e.get("method")})
        new_cols = [e.get("new_col", "") for e in compute_log[:8] if e.get("new_col")]

        paragraf1 = (
            f"Sebanyak {n_ops} variabel baru dibentuk melalui operasi komputasi "
            f"yang mencakup: {', '.join(methods) if methods else 'berbagai metode transformasi'}. "
            "Pembentukan variabel baru merupakan bagian dari tahap persiapan data yang "
            "bertujuan menghasilkan indikator pengukuran yang sesuai dengan kerangka "
            "konseptual penelitian (Field, 2018). "
        )

        paragraf2 = ""
        if new_cols:
            paragraf2 = (
                f"Variabel baru yang dibentuk antara lain: {', '.join(new_cols)}"
                + (" (dan lainnya)" if n_ops > 8 else "")
                + ". Setiap variabel komposit atau transformasi harus didokumentasikan "
                "secara eksplisit dalam laporan metodologi penelitian, termasuk dasar "
                "teoritis dan prosedur komputasi yang digunakan."
            )

        return "\n\n".join(p for p in [paragraf1, paragraf2] if p.strip())

    # ══════════════════════════════════════════════════════════════════════════
    # ANALISIS KLASTER
    # ══════════════════════════════════════════════════════════════════════════
    elif mod_key == "klaster":
        method     = data.get("method", "K-Means")
        k          = data.get("k", "?")
        cols_kl    = data.get("cols", [])
        silhouette = data.get("silhouette")
        linkage    = data.get("linkage", "ward")
        n_var      = len(cols_kl)

        paragraf1 = (
            f"Analisis klaster dilakukan menggunakan metode {method} untuk "
            f"mengelompokkan observasi ke dalam {k} klaster berdasarkan {n_var} variabel"
            + (f": {', '.join(cols_kl[:6])}"
               + (" (dan lainnya)" if n_var > 6 else "")
               if cols_kl else "")
            + ". Data distandarisasi menggunakan Z-score sebelum proses clustering "
            "untuk menghilangkan pengaruh perbedaan skala pengukuran "
            "(MacQueen, 1967; Ward, 1963). "
        )
        if method == "Hierarchical":
            paragraf1 += (
                f"Metode hierarchical clustering dengan linkage {linkage} digunakan, "
                "di mana jumlah klaster optimal ditentukan berdasarkan inspeksi "
                "dendrogram."
            )

        paragraf2 = ""
        if silhouette is not None:
            sv = float(silhouette)
            if sv >= 0.70:
                kat  = "sangat baik"
                interp = ("klaster-klaster terbentuk dengan kohesi internal yang tinggi "
                          "dan separasi yang jelas")
            elif sv >= 0.50:
                kat  = "baik"
                interp = "klaster terbentuk dengan kohesi internal yang memadai"
            elif sv >= 0.30:
                kat  = "cukup (acceptable)"
                interp = "klaster terbentuk namun dengan overlap yang perlu diperhatikan"
            else:
                kat  = "rendah"
                interp = ("kualitas klaster perlu ditingkatkan \u2014 pertimbangkan "
                          "jumlah klaster yang berbeda")
            paragraf2 = (
                f"Kualitas pengelompokan dievaluasi menggunakan Silhouette Score = {sv:.4f}, "
                f"yang termasuk kategori {kat} (Rousseeuw, 1987). "
                f"Nilai ini mengindikasikan bahwa {interp}. "
                "Interpretasi profil klaster dilakukan dengan membandingkan rata-rata "
                "masing-masing variabel antar klaster untuk merumuskan karakteristik "
                "dominan setiap segmen."
            )

        paragraf3 = (
            "Hasil analisis klaster bersifat deskriptif-eksploratif dan tidak menghasilkan "
            "inferensi statistik seperti pada uji hipotesis. Validitas temuan klaster dapat "
            "ditingkatkan melalui prosedur cross-validation atau replikasi pada sampel "
            "independen (Rousseeuw, 1987)."
        )

        return "\n\n".join(p for p in [paragraf1, paragraf2, paragraf3] if p.strip())

    # ══════════════════════════════════════════════════════════════════════════
    # EDA
    # ══════════════════════════════════════════════════════════════════════════
    elif mod_key == "eda":
        n_rows   = data.get("n_rows", "?")
        n_cols   = data.get("n_cols", "?")
        n_num    = data.get("n_numeric", "?")
        n_cat    = data.get("n_cat", "?")
        n_miss   = data.get("n_missing", 0)
        pct_miss = data.get("pct_missing", 0)
        n_dup    = data.get("n_dup", 0)

        paragraf1 = (
            "Eksplorasi Data Awal (Exploratory Data Analysis/EDA) dilakukan terhadap "
            f"dataset yang terdiri dari {n_rows} observasi dan {n_cols} variabel "
            f"({n_num} numerik, {n_cat} kategorik). "
            "EDA merupakan tahap fundamental yang bertujuan memahami karakteristik "
            "distribusi data, mengidentifikasi anomali, dan menentukan strategi analisis "
            "yang tepat sebelum pengujian hipotesis dilakukan (Tukey, 1977; Field, 2018)."
        )

        p2_lines = []
        try:
            pct_f = float(pct_miss)
            mi    = int(n_miss)
            di    = int(n_dup)
            if mi > 0:
                if pct_f > 20:
                    p2_lines.append(
                        f"missing values tinggi ({mi} sel, {pct_f:.1f}%) \u2014 "
                        "direkomendasikan multiple imputation atau penghapusan variabel "
                        "dengan > 30% missing"
                    )
                elif pct_f > 5:
                    p2_lines.append(
                        f"missing values moderat ({mi} sel, {pct_f:.1f}%) \u2014 "
                        "direkomendasikan imputasi (mean, median, atau MICE)"
                    )
                else:
                    p2_lines.append(
                        f"missing values minimal ({mi} sel, {pct_f:.1f}%) \u2014 "
                        "dapat ditangani dengan listwise deletion atau imputasi sederhana"
                    )
            if di > 0:
                p2_lines.append(
                    f"{di} baris duplikat terdeteksi \u2014 perlu dievaluasi apakah "
                    "merupakan entri ganda atau data sah"
                )
        except Exception:
            pass

        paragraf2 = ""
        if p2_lines:
            paragraf2 = (
                "Evaluasi kualitas data mengidentifikasi: "
                + "; ".join(p2_lines) + ". "
                "Penanganan yang tepat diperlukan sebelum analisis statistik inferensial "
                "dilanjutkan."
            )
        else:
            try:
                if int(n_miss) == 0 and int(n_dup) == 0:
                    paragraf2 = (
                        "Dataset berada dalam kondisi baik: tidak terdapat missing values "
                        "maupun baris duplikat. Data siap dianalisis lebih lanjut tanpa "
                        "memerlukan prosedur pembersihan tambahan."
                    )
            except Exception:
                pass

        return "\n\n".join(p for p in [paragraf1, paragraf2] if p.strip())

    # ══════════════════════════════════════════════════════════════════════════
    # SCRAPING
    # ══════════════════════════════════════════════════════════════════════════
    elif mod_key == "scraping":
        source = data.get("source", "sumber tidak diketahui")
        n_rows = data.get("n_rows", "?")
        n_cols = data.get("n_cols", "?")
        n_num  = data.get("n_numeric", "?")
        n_miss = data.get("n_missing", 0)
        n_dup  = data.get("n_dup", 0)

        paragraf1 = (
            "Data penelitian diperoleh secara otomatis melalui teknik web scraping dari "
            f"sumber: {source}. Dataset yang berhasil dikumpulkan terdiri dari {n_rows} "
            f"observasi dan {n_cols} variabel ({n_num} numerik). "
            "Pengambilan data dilakukan dengan memperhatikan kebijakan robots.txt dan "
            "rate-limiting untuk mematuhi etika pengambilan data publik digital."
        )

        kl = []
        try:
            if int(n_miss) > 0:
                kl.append(f"{n_miss} missing values yang ditangani melalui cleaning")
            if int(n_dup) > 0:
                kl.append(f"{n_dup} baris duplikat yang dieliminasi pada preprocessing")
        except Exception:
            pass

        paragraf2 = (
            "Proses data cleaning meliputi: " + "; ".join(kl) + ". "
            "Standardisasi format, konversi tipe variabel, dan validasi rentang nilai "
            "dilakukan sebelum analisis untuk memastikan integritas dataset."
            if kl else
            "Dataset hasil scraping tidak memiliki missing values maupun duplikat, "
            "sehingga siap dianalisis setelah validasi format dan tipe data."
        )

        paragraf3 = (
            "Validitas data sekunder yang dikumpulkan melalui scraping perlu dikritisi "
            "mengingat potensi perubahan struktur halaman web, bias seleksi sumber, dan "
            "keterbatasan aksesibilitas. Reproducibility penelitian dapat ditingkatkan "
            "dengan menyimpan log scraping yang mencatat waktu pengambilan, URL, dan "
            "versi dataset yang digunakan."
        )

        return "\n\n".join(p for p in [paragraf1, paragraf2, paragraf3] if p.strip())

    # ══════════════════════════════════════════════════════════════════════════
    # POWER ANALYSIS
    # ══════════════════════════════════════════════════════════════════════════
    elif mod_key == "power_analysis":
        test_type   = data.get("test_type", "uji statistik")
        effect_size = data.get("effect_size")
        alpha       = data.get("alpha", 0.05)
        power       = data.get("power", 0.80)
        n_total     = data.get("n_total")
        n_per_group = data.get("n_per_group")

        paragraf1 = (
            f"Analisis kekuatan statistik (power analysis) dilakukan untuk {test_type} "
            "guna menentukan ukuran sampel minimum yang diperlukan agar penelitian "
            "memiliki kekuatan statistik yang memadai. "
            f"Tingkat signifikansi yang ditetapkan adalah \u03b1 = {alpha}, "
            f"dengan target statistical power = {power} (Cohen, 1988). "
        )

        paragraf2 = ""
        if effect_size is not None:
            paragraf2 = (
                f"Berdasarkan ukuran efek yang diantisipasi (effect size = "
                f"{float(effect_size):.3f}) dan tingkat power {power}, "
            )
            if n_total is not None:
                paragraf2 += f"diperlukan total sampel minimum N = {n_total}"
                if n_per_group is not None:
                    paragraf2 += f" ({n_per_group} per kelompok)"
                paragraf2 += ". "
            paragraf2 += (
                "Ukuran sampel yang memadai memastikan bahwa penelitian memiliki "
                "kemampuan yang cukup untuk mendeteksi efek yang sesungguhnya ada di "
                "populasi (Cohen, 1988; Field, 2018)."
            )

        return "\n\n".join(p for p in [paragraf1, paragraf2] if p.strip())

    # ══════════════════════════════════════════════════════════════════════════
    # Fallback generik
    # ══════════════════════════════════════════════════════════════════════════
    return (
        "Analisis statistik telah dilakukan sesuai dengan prosedur yang ditetapkan. "
        "Interpretasi hasil disajikan pada tabel dan visualisasi yang menyertai bagian ini. "
        "Pembaca disarankan merujuk pada nilai statistik uji, tingkat signifikansi, "
        "dan ukuran efek yang dilaporkan untuk menarik kesimpulan yang tepat "
        "(Field, 2018; Cohen, 1988)."
    )

    if mod_key == "time_series":
        col_name    = data.get("col_name", "deret waktu")
        model_label = data.get("model_label", "ARIMA")
        mape        = data.get("mape", "—")
        adf_ok      = data.get("adf_stationary")
        kpss_ok     = data.get("kpss_stationary")
        n_forecast  = data.get("n_forecast", 0)
        decompose_t = data.get("decompose_type", "—")
        if adf_ok and kpss_ok:
            stat_ket = "berdistribusi stasioner berdasarkan kedua uji (ADF dan KPSS)"
        elif not adf_ok and not kpss_ok:
            stat_ket = "tidak stasioner, sehingga dilakukan differencing"
        else:
            stat_ket = "menunjukkan hasil berbeda antara uji ADF dan KPSS"
        mape_ket = ""
        if mape != "—":
            try:
                mf = float(mape)
                if mf < 10:   mape_ket = f"MAPE {mape}% menunjukkan akurasi sangat baik."
                elif mf < 20: mape_ket = f"MAPE {mape}% menunjukkan akurasi baik."
                else:         mape_ket = f"MAPE {mape}% menunjukkan akurasi lemah — pertimbangkan penyesuaian order."
            except Exception:
                mape_ket = f"MAPE = {mape}%."
        return (
            f"Analisis deret waktu pada variabel {col_name} menunjukkan bahwa data {stat_ket}. "
            f"Dekomposisi musiman model {decompose_t} digunakan untuk memisahkan komponen "
            f"tren, musiman, dan residu. Model {model_label} dipilih berdasarkan AIC/BIC terkecil. "
            f"{mape_ket} Forecast {n_forecast} periode ke depan disajikan beserta "
            f"confidence interval 95% sebagai dasar pengambilan keputusan "
            f"(Box & Jenkins, 1976; Hyndman & Athanasopoulos, 2021)."
        )

