"""
FITUR 4: Interpretasi Effect Size Standar
Lokasi  : utils/effect_size.py  (file baru — import dari semua modul Pro)
Dampak  : Cohen (1988), eta², d, f², r, Odds Ratio — dalam satu tempat,
          konsisten di seluruh modul.

Cara integrasi per modul:
  from utils.effect_size import interpret_effect_size, render_effect_size_card

  # Di modul regresi/ols_plus:
  render_effect_size_card("f2", f2_value, context="regresi")

  # Di modul ANOVA:
  render_effect_size_card("eta2", eta_sq, context="anova")

  # Di modul Uji Beda:
  render_effect_size_card("d", cohens_d, context="uji_beda")

  # Di modul Korelasi:
  render_effect_size_card("r", r_value, context="korelasi")

  # Di modul Logistik:
  render_effect_size_card("or", odds_ratio, context="logistik")
"""

import streamlit as st


# ── Tabel standar Cohen (1988) dan sumber lain ───────────────────────────────

EFFECT_SIZE_TABLES = {

    # Cohen's d — perbedaan rata-rata (Uji Beda, t-test)
    "d": {
        "nama":    "Cohen's d",
        "rumus":   "d = (M₁ − M₂) / SD_pooled",
        "sumber":  "Cohen (1988)",
        "konteks": "Uji Beda (t-test / Mann-Whitney)",
        "thresholds": [
            (0.20, "Kecil",  "#3B6D11",  "Efek kecil — perbedaan ada tapi kecil secara praktis."),
            (0.50, "Sedang", "#185FA5",  "Efek sedang — perbedaan bermakna secara praktis."),
            (0.80, "Besar",  "#A32D2D",  "Efek besar — perbedaan sangat bermakna secara praktis."),
        ],
        "acuan": "Kecil: d < 0.20 | Sedang: 0.20 ≤ d < 0.50 | Besar: d ≥ 0.80",
    },

    # eta squared — ANOVA
    "eta2": {
        "nama":    "Eta Squared (η²)",
        "rumus":   "η² = SS_between / SS_total",
        "sumber":  "Cohen (1988); Richardson (2011)",
        "konteks": "ANOVA (One-Way / Kruskal-Wallis)",
        "thresholds": [
            (0.01, "Kecil",  "#3B6D11", "Efek kecil — variabilitas antar kelompok rendah."),
            (0.06, "Sedang", "#185FA5", "Efek sedang — perbedaan kelompok cukup bermakna."),
            (0.14, "Besar",  "#A32D2D", "Efek besar — kelompok sangat berbeda secara substansial."),
        ],
        "acuan": "Kecil: η² < 0.01 | Sedang: 0.01 ≤ η² < 0.06 | Besar: η² ≥ 0.14",
    },

    # Cohen's f² — Regresi linier berganda
    "f2": {
        "nama":    "Cohen's f²",
        "rumus":   "f² = R² / (1 − R²)",
        "sumber":  "Cohen (1988)",
        "konteks": "Regresi Linier / OLS+",
        "thresholds": [
            (0.02, "Kecil",  "#3B6D11", "Efek kecil — model menjelaskan sedikit variansi."),
            (0.15, "Sedang", "#185FA5", "Efek sedang — model cukup menjelaskan variansi Y."),
            (0.35, "Besar",  "#A32D2D", "Efek besar — model sangat baik menjelaskan Y."),
        ],
        "acuan": "Kecil: f² < 0.02 | Sedang: 0.02 ≤ f² < 0.15 | Besar: f² ≥ 0.35",
    },

    # Pearson r — Korelasi
    "r": {
        "nama":    "Pearson r (Korelasi)",
        "rumus":   "r = Σ[(X−X̄)(Y−Ȳ)] / √[Σ(X−X̄)² · Σ(Y−Ȳ)²]",
        "sumber":  "Cohen (1988); Evans (1996)",
        "konteks": "Analisis Korelasi / Scatter Plot",
        "thresholds": [
            (0.10, "Lemah",        "#888888", "Hubungan sangat lemah — hampir tidak ada korelasi."),
            (0.30, "Kecil",        "#3B6D11", "Hubungan lemah — ada korelasi tapi kecil."),
            (0.50, "Sedang",       "#185FA5", "Hubungan sedang — cukup bermakna."),
            (1.01, "Kuat / Besar", "#A32D2D", "Hubungan kuat — korelasi bermakna secara praktis."),
        ],
        "acuan": "Lemah: |r| < 0.10 | Kecil: 0.10–0.29 | Sedang: 0.30–0.49 | Kuat: |r| ≥ 0.50",
    },

    # Odds Ratio — Regresi Logistik
    "or": {
        "nama":    "Odds Ratio (OR)",
        "rumus":   "OR = exp(β)",
        "sumber":  "Hosmer & Lemeshow (2013)",
        "konteks": "Regresi Logistik",
        "thresholds": [
            (1.50, "Lemah",        "#888888", "Perubahan peluang sangat kecil (OR ≈ 1 = tidak ada efek)."),
            (2.50, "Sedang",       "#185FA5", "Perubahan peluang cukup bermakna."),
            (4.00, "Kuat",         "#A32D2D", "Perubahan peluang besar — prediktor sangat berpengaruh."),
            (9999, "Sangat Kuat",  "#6B21A8", "OR > 4 = efek sangat kuat secara praktis."),
        ],
        "acuan": "Kecil: OR < 1.5 | Sedang: 1.5–2.5 | Kuat: 2.5–4.0 | Sangat Kuat: OR > 4.0",
    },

    # Partial eta² — ANOVA multivariat / regresi
    "partial_eta2": {
        "nama":    "Partial Eta Squared (η²p)",
        "rumus":   "η²p = SS_effect / (SS_effect + SS_error)",
        "sumber":  "Cohen (1988); Richardson (2011)",
        "konteks": "ANOVA / Regresi",
        "thresholds": [
            (0.01, "Kecil",  "#3B6D11", "Efek kecil."),
            (0.06, "Sedang", "#185FA5", "Efek sedang."),
            (0.14, "Besar",  "#A32D2D", "Efek besar."),
        ],
        "acuan": "Kecil: η²p < 0.01 | Sedang: 0.01–0.06 | Besar: η²p ≥ 0.14",
    },
}


def interpret_effect_size(
    es_type: str,
    value: float,
) -> dict:
    """
    Interpretasikan nilai effect size berdasarkan standar Cohen (1988).

    Args:
        es_type : 'd' | 'eta2' | 'f2' | 'r' | 'or' | 'partial_eta2'
        value   : nilai effect size (positif)

    Returns dict:
        label    : 'Kecil' / 'Sedang' / 'Besar'
        color    : hex color
        keterangan: deskripsi
        nama     : nama lengkap effect size
        acuan    : string acuan threshold
        sumber   : referensi APA
        f2       : nilai f² jika es_type='r2' (bonus)
    """
    table = EFFECT_SIZE_TABLES.get(es_type)
    if table is None:
        return {
            "label": "Tidak dikenali",
            "color": "#888",
            "keterangan": "Tipe effect size tidak dikenali.",
            "nama": es_type,
            "acuan": "",
            "sumber": "",
        }

    abs_val = abs(float(value))

    label      = "–"
    color      = "#888"
    keterangan = ""

    for threshold, lbl, col, ket in table["thresholds"]:
        if abs_val < threshold:
            label      = lbl
            color      = col
            keterangan = ket
            break
    else:
        # Nilai melebihi semua threshold → ambil yang terakhir
        _, label, color, keterangan = table["thresholds"][-1]

    result = {
        "label":      label,
        "color":      color,
        "keterangan": keterangan,
        "nama":       table["nama"],
        "rumus":      table["rumus"],
        "acuan":      table["acuan"],
        "sumber":     table["sumber"],
        "konteks":    table["konteks"],
        "value":      round(abs_val, 4),
    }

    # Bonus: hitung f² jika diberi R²
    if es_type in ("f2",):
        result["r2_equivalent"] = round(abs_val / (1 + abs_val), 4)

    return result


def compute_cohens_f2(r2: float) -> float:
    """Hitung Cohen's f² dari R²."""
    if r2 >= 1.0:
        return float("inf")
    return round(r2 / (1 - r2), 4)


def compute_cohens_d(mean1: float, mean2: float, std1: float, std2: float,
                     n1: int, n2: int) -> float:
    """Hitung Cohen's d dari dua kelompok."""
    pooled_sd = ((( n1 - 1) * std1 ** 2 + (n2 - 1) * std2 ** 2) / (n1 + n2 - 2)) ** 0.5
    if pooled_sd == 0:
        return 0.0
    return round(abs(mean1 - mean2) / pooled_sd, 4)


def render_effect_size_card(
    es_type: str,
    value: float,
    context: str = "",
    show_table: bool = True,
):
    """
    Render kartu interpretasi effect size di Streamlit.

    Args:
        es_type    : tipe effect size ('d', 'eta2', 'f2', 'r', 'or')
        value      : nilai effect size
        context    : string konteks tambahan untuk narasi
        show_table : tampilkan tabel threshold referensi lengkap
    """
    interp = interpret_effect_size(es_type, value)

    st.markdown(
        f'<div class="rs-narasi" style="border-left-color:{interp["color"]};">'
        f'📏 <b>{interp["nama"]}</b> = {interp["value"]} &nbsp;→&nbsp; '
        f'<span style="color:{interp["color"]}; font-weight:700;">'
        f'{interp["label"]}</span><br/>'
        f'<span style="font-size:0.85rem;">{interp["keterangan"]}</span><br/>'
        f'<span style="font-size:0.78rem; color:#5f8ab5;">'
        f'📖 Acuan: {interp["acuan"]} | Sumber: {interp["sumber"]}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    if show_table:
        table = EFFECT_SIZE_TABLES.get(es_type)
        if table:
            with st.expander(f"📚 Tabel Referensi: {table['nama']} (Cohen, 1988)"):
                st.markdown(f"**Rumus:** `{table['rumus']}`")
                st.markdown(f"**Konteks:** {table['konteks']}")
                st.markdown(f"**Sumber:** {table['sumber']}")
                st.markdown("---")
                for threshold, lbl, col, ket in table["thresholds"]:
                    st.markdown(
                        f'<span style="color:{col}; font-weight:600;">■ {lbl}</span> '
                        f'— {ket}',
                        unsafe_allow_html=True,
                    )


def render_effect_size_summary_table():
    """
    Render tabel ringkasan semua effect size — tampilkan di Help / Sidebar.
    Berguna sebagai referensi cepat di seluruh modul.
    """
    import pandas as pd

    rows = []
    for es_type, table in EFFECT_SIZE_TABLES.items():
        thresholds = table["thresholds"]
        kecil  = thresholds[0][0] if len(thresholds) > 0 else "–"
        sedang = thresholds[1][0] if len(thresholds) > 1 else "–"
        besar  = thresholds[2][0] if len(thresholds) > 2 else "–"
        rows.append({
            "Effect Size":  table["nama"],
            "Konteks":      table["konteks"],
            "Kecil":        f"< {kecil}",
            "Sedang":       f"{kecil} – {sedang}",
            "Besar":        f"≥ {besar}",
            "Sumber":       table["sumber"],
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)


# ── Contoh penggunaan per modul ───────────────────────────────────────────────

"""
# ── Di modules/regresi.py ─────────────────────────────────────────────────────
from utils.effect_size import compute_cohens_f2, render_effect_size_card

f2 = compute_cohens_f2(r2)
render_effect_size_card("f2", f2, context=f"Regresi {dep_var}")


# ── Di modules/anova.py ───────────────────────────────────────────────────────
from utils.effect_size import render_effect_size_card

render_effect_size_card("eta2", eta_sq, context=f"ANOVA {num_col}")


# ── Di modules/korelasi.py ────────────────────────────────────────────────────
from utils.effect_size import render_effect_size_card

render_effect_size_card("r", abs(r_val), context=f"{var_x} × {var_y}")


# ── Di modules/logistik.py ────────────────────────────────────────────────────
from utils.effect_size import render_effect_size_card

for _, row in sig_rows.iterrows():
    or_val = row["OR (exp β)"]
    render_effect_size_card("or", or_val, context=row["Parameter"])


# ── Di modules/kelompok.py / uji_beda.py ────────────────────────────────────
from utils.effect_size import compute_cohens_d, render_effect_size_card

d = compute_cohens_d(g1_mean, g2_mean, g1_std, g2_std, n1, n2)
render_effect_size_card("d", d, context=f"{g1_name} vs {g2_name}")


# ── Tabel ringkasan di Beranda atau Help ─────────────────────────────────────
from utils.effect_size import render_effect_size_summary_table

with st.expander("📏 Panduan Effect Size (Cohen, 1988)"):
    render_effect_size_summary_table()
"""
