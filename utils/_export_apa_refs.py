"""
utils/_export_apa_refs.py — Ruang Statistika v4.8
Database referensi APA 7th Edition, mapping modul → referensi,
dan fungsi generate_apa_references() + render_apa_preview().

Menambah referensi baru:
  1. Tambahkan entri di APA_REFERENCES dict
  2. Tambahkan mapping di MODULE_APA_MAPPING

Diimport oleh: utils/export.py
"""

import streamlit as st

# ── Database referensi APA 7th ────────────────────────────────────────────────

APA_REFERENCES: dict[str, str] = {

    # ── Time Series ──────────────────────────────────────────────────────────
    "box_1976": (
        "Box, G. E. P., & Jenkins, G. M. (1976). *Time series analysis: "
        "Forecasting and control*. Holden-Day."
    ),
    "hyndman_2021": (
        "Hyndman, R. J., & Athanasopoulos, G. (2021). *Forecasting: Principles "
        "and practice* (3rd ed.). OTexts. https://otexts.com/fpp3"
    ),

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

    # Ambil teks referensi dan urutkan berdasarkan nama belakang penulis pertama (APA)
    import re as _re

    def _apa_sort_key(ref_text: str) -> str:
        clean = _re.sub(r"\*", "", ref_text).strip()
        first_token = _re.split(r"[,.]", clean)[0].strip().lower()
        return first_token

    ref_pairs = [APA_REFERENCES[k] for k in ref_keys if k in APA_REFERENCES]
    ref_texts = sorted(ref_pairs, key=_apa_sort_key)

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
            lines.append(f"{i}. {ref}\n")
        else:
            lines.append(f"{ref}\n")

    return "\n".join(lines)


def _strip_markdown_italics(text: str) -> str:
    """Hapus tanda asterisks Markdown: '*Psychometrika*' -> 'Psychometrika'."""
    import re
    return re.sub(r"\*([^*]+)\*", r"\1", text)


def render_apa_preview(apa_text: str):
    """Tampilkan preview referensi di Streamlit dengan hanging indent dan italics."""
    if not apa_text:
        return
    st.markdown("---")
    st.markdown("#### 📚 Preview Daftar Referensi (APA 7th)")
    with st.expander("Lihat daftar referensi yang akan disertakan dalam laporan"):
        lines = apa_text.split("\n")
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("## "):
                st.markdown(stripped)
            elif stripped[0].isdigit() and ". " in stripped[:4]:
                # Vancouver numbered
                st.markdown(stripped)
            else:
                # APA entry — hanging indent via HTML, asterisks render as italic
                st.markdown(
                    f'<p style="padding-left:2em; text-indent:-2em; '
                    f'margin-bottom:0.4em; font-size:0.93rem;">{stripped}</p>',
                    unsafe_allow_html=True,
                )


# ─────────────────────────────────────────────────────────────────────────────
# RENDER UTAMA
# ─────────────────────────────────────────────────────────────────────────────

