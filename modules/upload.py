"""
modules/upload.py — Upload & Auto Cleaning (Free)
Ruang Statistika v4.0

Struktur standar modul:
    render(ctx: dict) → None
    ctx keys: alpha_level, r_tab, license_info, ai_enabled, anthropic_api_key, ai_provider
"""

import streamlit as st
import pandas as pd
import numpy as np

from utils.stats_helpers import load_data, auto_clean, encode_categorical, ss_get

# ── Opsi tipe variabel ────────────────────────────────────────────────────────
TYPE_OPTIONS = [
    "Numerik Kontinu",
    "Numerik Diskrit",
    "Ordinal / Likert",
    "Kategorik Nominal",
    "Biner (0/1)",
    "ID / Diabaikan",
]

# Tipe yang dianggap analitik (dimasukkan ke selected_cols)
_NUMERIC_TYPES = {"Numerik Kontinu", "Numerik Diskrit", "Ordinal / Likert", "Biner (0/1)"}


def _auto_detect_var_types(df: pd.DataFrame, report: dict) -> dict:
    """
    Auto-detect tipe variabel berdasarkan profil data.
    Dipakai sebagai default awal — user bisa override via UI.
    Tidak mengubah df atau report.
    """
    numeric_cols     = set(report.get("numeric_cols", []))
    non_numeric_cols = set(report.get("non_numeric_cols", []))
    var_types = {}

    for col in df.columns:
        if col in non_numeric_cols:
            var_types[col] = "Kategorik Nominal"
        elif col in numeric_cols:
            s = pd.to_numeric(df[col], errors="coerce").dropna()
            if s.empty:
                var_types[col] = "Numerik Kontinu"
            elif set(s.unique()).issubset({0, 1, 0.0, 1.0}):
                var_types[col] = "Biner (0/1)"
            elif s.nunique() <= 10 and (s % 1 == 0).all():
                var_types[col] = "Ordinal / Likert"
            else:
                var_types[col] = "Numerik Kontinu"
        else:
            var_types[col] = "Numerik Kontinu"

    return var_types


def recommend_analysis(df: pd.DataFrame, report: dict) -> dict:
    """
    Analisis karakteristik data dan buat rekomendasi uji statistik.

    Returns dict berisi:
        primary    : list rekomendasi utama (nama uji + alasan)
        secondary  : list rekomendasi tambahan
        warnings   : list peringatan (distribusi tidak normal, dll)
        data_profile: ringkasan profil data
    """
    numeric_cols    = report.get("numeric_cols", [])
    non_numeric     = report.get("non_numeric_cols", [])
    total_missing   = report.get("total_missing", 0)
    n_rows          = len(df)
    n_numeric       = len(numeric_cols)
    n_categorical   = len(non_numeric)

    primary   = []
    secondary = []
    warnings  = []

    # ── Periksa normalitas cepat (Shapiro untuk N ≤ 5000) ────────────────
    from scipy import stats as scipy_stats
    normal_cols     = []
    non_normal_cols = []

    for col in numeric_cols[:10]:  # batasi 10 kolom untuk kecepatan
        s = pd.to_numeric(df[col], errors="coerce").dropna()
        if len(s) >= 3:
            try:
                samp = s if len(s) <= 5000 else s.sample(5000, random_state=42)
                _, p = scipy_stats.shapiro(samp)
                if p > 0.05:
                    normal_cols.append(col)
                else:
                    non_normal_cols.append(col)
            except Exception:
                pass

    pct_normal = len(normal_cols) / len(numeric_cols) * 100 if numeric_cols else 0

    # ── Profil data ───────────────────────────────────────────────────────
    data_profile = {
        "n_baris":       n_rows,
        "n_numerik":     n_numeric,
        "n_kategorik":   n_categorical,
        "n_missing":     total_missing,
        "pct_normal":    round(pct_normal, 1),
        "normal_cols":   normal_cols,
        "non_normal":    non_normal_cols,
    }

    # ── RULE ENGINE ───────────────────────────────────────────────────────

    # Hitung kolom biner
    binary_cols = []
    for col in numeric_cols:
        s = pd.to_numeric(df[col], errors="coerce").dropna()
        if set(s.unique()).issubset({0, 1, 0.0, 1.0}) and len(s) > 10:
            binary_cols.append(col)
    n_binary = len(binary_cols)

    # Estimasi apakah data time series (ada kolom tanggal / nama kolom mengandung "tahun","bulan","date","year","time","periode")
    _ts_keywords = {"tahun", "bulan", "date", "year", "time", "periode", "tanggal", "month", "quarter"}
    has_time_col  = any(any(kw in c.lower() for kw in _ts_keywords) for c in df.columns)

    # ── PRIMARY — selalu atau hampir selalu relevan ────────────────────────

    # 1. Deskriptif — selalu
    primary.append({
        "uji":    "📊 Statistik Deskriptif",
        "alasan": f"Dataset memiliki {n_numeric} variabel numerik — selalu mulai dari ringkasan deskriptif.",
        "modul":  "Deskriptif",
        "icon":   "✅",
    })

    # 2. Visualisasi EDA — selalu, deteksi pola & distribusi visual
    primary.append({
        "uji":    "🔍 Visualisasi EDA",
        "alasan": "Eksplorasi distribusi, histogram, dan pola data secara visual sebelum analisis inferensial.",
        "modul":  "EDA",
        "icon":   "✅",
    })

    # 3. Uji Asumsi — selalu (prasyarat uji parametrik)
    primary.append({
        "uji":    "🔬 Uji Asumsi",
        "alasan": "Periksa normalitas, homogenitas varians, dan linearitas sebelum analisis parametrik.",
        "modul":  "Uji Asumsi",
        "icon":   "✅",
    })

    # 4. Deteksi Outlier — selalu
    primary.append({
        "uji":    "🎯 Deteksi Outlier (IQR / Z-Score / Mahalanobis)",
        "alasan": "Nilai ekstrem dapat mendistorsi hasil uji parametrik — periksa sebelum analisis lanjutan.",
        "modul":  "Outlier",
        "icon":   "✅",
    })

    # 5. Validitas & Reliabilitas — jika banyak numerik (indikasi kuesioner Likert)
    if n_numeric >= 5:
        primary.append({
            "uji":    "✅ Validitas & Reliabilitas (Cronbach's Alpha)",
            "alasan": f"{n_numeric} variabel numerik terdeteksi — kemungkinan data kuesioner/skala Likert.",
            "modul":  "Validitas",
            "icon":   "✅",
        })

    # 6. Korelasi — jika ≥ 2 numerik
    if n_numeric >= 2:
        primary.append({
            "uji":    "🔗 Analisis Korelasi Pearson / Spearman",
            "alasan": "Periksa arah dan kekuatan hubungan linear antar variabel sebelum regresi.",
            "modul":  "Korelasi",
            "icon":   "✅",
        })

    # 7. Analisis Kelompok — jika ada kategorik
    if n_categorical > 0:
        cat_preview = ", ".join(non_numeric[:3])
        primary.append({
            "uji":    "📂 Analisis Kelompok",
            "alasan": f"Ditemukan {n_categorical} variabel kategorik ({cat_preview}) — bandingkan statistik antar kelompok.",
            "modul":  "Kelompok",
            "icon":   "✅",
        })

    # ── SECONDARY — berdasarkan kondisi data ──────────────────────────────

    # 8. Uji Beda — jika ada kategorik (biner → t-test / 2 grup)
    if n_categorical > 0 and n_numeric >= 1:
        if n_binary > 0:
            secondary.append({
                "uji":    "🔢 Uji Beda (Independent t-test / Mann-Whitney)",
                "alasan": f"Variabel biner ({binary_cols[0]}) cocok sebagai variabel pengelompok untuk uji beda dua kelompok.",
                "modul":  "Uji Beda",
                "icon":   "🟢",
            })
        else:
            secondary.append({
                "uji":    "🔢 Uji Beda (Independent t-test / Mann-Whitney)",
                "alasan": f"Variabel kategorik ({non_numeric[0]}) dapat digunakan untuk membandingkan dua kelompok independen.",
                "modul":  "Uji Beda",
                "icon":   "🟢",
            })

    # 9. ANOVA — jika ada kategorik + data cukup normal
    if n_categorical > 0 and n_numeric >= 1:
        if pct_normal >= 50:
            secondary.append({
                "uji":    "📊 ANOVA & Post-hoc (One-Way / Two-Way)",
                "alasan": f"Data cukup normal ({pct_normal}%) + variabel kategorik → ANOVA lebih tepat dari Kruskal-Wallis.",
                "modul":  "ANOVA",
                "icon":   "🟢",
            })
        else:
            secondary.append({
                "uji":    "📐 Uji Non-Parametrik (Kruskal-Wallis / Friedman)",
                "alasan": f"{len(non_normal_cols)} variabel tidak normal — alternatif ANOVA tanpa asumsi distribusi.",
                "modul":  "Uji Nonparametrik",
                "icon":   "🟡",
            })

    # 10. Power Analysis — berguna untuk validasi ukuran sampel
    secondary.append({
        "uji":    "🔋 Power Analysis (Ukuran Sampel Minimum)",
        "alasan": f"N = {n_rows}. Pastikan ukuran sampel cukup untuk mendeteksi efek yang diharapkan (Cohen, 1988).",
        "modul":  "Power Analysis",
        "icon":   "🟢" if n_rows >= 30 else "🟡",
    })

    # 11. Regresi Linier / OLS+ — jika ≥ 2 numerik
    if n_numeric >= 2:
        if pct_normal >= 70:
            secondary.append({
                "uji":    "📈 Regresi Linier Berganda (OLS)",
                "alasan": f"{len(normal_cols)} variabel normal — uji parametrik OLS direkomendasikan untuk prediksi Y.",
                "modul":  "Regresi",
                "icon":   "🟢",
            })
            secondary.append({
                "uji":    "📈 OLS+ (dengan Uji Asumsi Klasik Lengkap)",
                "alasan": "Versi OLS dengan pemeriksaan multikolinearitas (VIF), heteroskedastisitas (White), dan autokorelasi (DW).",
                "modul":  "OLS Plus",
                "icon":   "🟢",
            })
        else:
            secondary.append({
                "uji":    "📈 OLS Robust (Huber / MM-Estimator)",
                "alasan": f"Data tidak sepenuhnya normal ({pct_normal}%) — OLS Robust lebih tahan terhadap outlier dan heteroskedastisitas.",
                "modul":  "OLS Robust",
                "icon":   "🟡",
            })

    # 12. Regresi Logistik — jika ada variabel biner
    if n_binary > 0:
        secondary.append({
            "uji":    f"📉 Regresi Logistik (variabel outcome: {binary_cols[0]})",
            "alasan": f"Kolom '{binary_cols[0]}' terdeteksi sebagai variabel biner (0/1) — cocok sebagai variabel dependen logistik.",
            "modul":  "Regresi Logistik",
            "icon":   "🔵",
        })

    # 13. Mediasi — jika ≥ 3 numerik
    if n_numeric >= 3:
        secondary.append({
            "uji":    "🔀 Analisis Mediasi (Bootstrap / Baron-Kenny)",
            "alasan": f"Dengan {n_numeric} variabel numerik, uji jalur X → M → Y untuk mengidentifikasi mekanisme pengaruh.",
            "modul":  "Mediasi",
            "icon":   "🔵",
        })

    # 14. Moderasi — jika ≥ 3 numerik
    if n_numeric >= 3:
        secondary.append({
            "uji":    "🎛️ Analisis Moderasi (Interaksi / Johnson-Neyman)",
            "alasan": "Uji apakah variabel Z memoderasi kekuatan hubungan X → Y (efek interaksi).",
            "modul":  "Moderasi",
            "icon":   "🔵",
        })

    # 15. EFA — jika ≥ 5 numerik (indikasi konstruk laten)
    if n_numeric >= 5:
        secondary.append({
            "uji":    "🔬 Analisis Faktor Eksploratori (EFA)",
            "alasan": f"{n_numeric} variabel numerik — EFA cocok untuk mengidentifikasi faktor/konstruk laten yang mendasari data.",
            "modul":  "EFA",
            "icon":   "🔵",
        })

    # 16. CFA — jika ≥ 6 numerik (EFA dulu, lalu konfirmasi dengan CFA)
    if n_numeric >= 6:
        secondary.append({
            "uji":    "🔬 CFA Standalone (Confirmatory Factor Analysis)",
            "alasan": "Jika struktur faktor sudah dihipotesiskan, CFA menguji fit model pengukuran secara konfirmatori.",
            "modul":  "CFA",
            "icon":   "🔵",
        })

    # 17. SEM — jika ≥ 6 numerik (gabungan model pengukuran + struktural)
    if n_numeric >= 6:
        secondary.append({
            "uji":    "🧩 SEM & CFA (Structural Equation Modeling)",
            "alasan": f"{n_numeric} variabel — SEM menggabungkan CFA (model pengukuran) dan regresi jalur struktural sekaligus.",
            "modul":  "SEM",
            "icon":   "🔵",
        })

    # 18. Time Series — jika terdeteksi kolom waktu atau data cukup banyak baris
    if has_time_col or n_rows >= 24:
        secondary.append({
            "uji":    "⏱️ Time Series Analysis (ARIMA / Auto-ARIMA)",
            "alasan": (
                "Kolom bertanda waktu terdeteksi — analisis tren, musiman, dan peramalan deret waktu."
                if has_time_col
                else f"N = {n_rows} baris — data longitudinal berpotensi untuk analisis time series dan forecasting."
            ),
            "modul":  "Time Series",
            "icon":   "🔵",
        })

    # 19. Compute Variabel — jika ada banyak variabel numerik (potensi pembentukan indeks)
    if n_numeric >= 4:
        secondary.append({
            "uji":    "🧮 Compute Variabel (Indeks / Transformasi)",
            "alasan": f"{n_numeric} variabel numerik — bentuk variabel baru (mean score, z-score, interaksi, log) untuk analisis lanjutan.",
            "modul":  "Compute",
            "icon":   "🟡",
        })

    # 20. Reliabilitas ICC — jika ada variabel penilaian berulang / multi-rater
    if n_numeric >= 3:
        secondary.append({
            "uji":    "📏 Reliabilitas ICC (Intraclass Correlation Coefficient)",
            "alasan": "Jika data berasal dari penilaian berulang atau multi-rater, ICC mengukur konsistensi antar pengukur.",
            "modul":  "Reliabilitas ICC",
            "icon":   "🟡",
        })

    # ── Peringatan ────────────────────────────────────────────────────────
    if total_missing > 0:
        pct_miss = round(total_missing / (n_rows * max(n_numeric, 1)) * 100, 1)
        warnings.append(f"⚠️ Ada {total_missing} missing values ({pct_miss}%). Pertimbangkan imputasi sebelum regresi.")

    if n_rows < 30:
        warnings.append(f"⚠️ Ukuran sampel kecil (N = {n_rows}). Hasil uji statistik mungkin tidak stabil.")

    if non_normal_cols:
        warnings.append(f"⚠️ Variabel tidak normal: {', '.join(non_normal_cols[:5])}. Pertimbangkan uji non-parametrik atau transformasi data.")

    if n_binary > 0 and pct_normal < 50:
        warnings.append(f"⚠️ Variabel biner ({binary_cols[0]}) terdeteksi — untuk outcome biner, gunakan Regresi Logistik, bukan OLS.")

    return {
        "primary":      primary,
        "secondary":    secondary,
        "warnings":     warnings,
        "data_profile": data_profile,
    }


# Modul yang memerlukan lisensi Pro
_PRO_MODULES = {
    "Mediasi", "Moderasi", "Time Series", "EFA", "SEM", "CFA",
    "Scraping", "OLS Plus", "OLS Robust",
}


def render_recommendation_card(rec: dict):
    """Render kartu rekomendasi analisis di UI Streamlit."""
    if not rec:
        return

    profile = rec["data_profile"]

    st.markdown("---")
    st.markdown(
        '<p class="rs-section-title">💡 Rekomendasi Analisis</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<p class="rs-section-sub">Berdasarkan profil data Anda: '
        f'{profile["n_baris"]} baris, {profile["n_numerik"]} variabel numerik, '
        f'{profile["n_kategorik"]} kategorik, '
        f'{profile["pct_normal"]}% variabel normal.</p>',
        unsafe_allow_html=True,
    )

    # ── Peringatan ────────────────────────────────────────────────────────────
    if rec["warnings"]:
        for w in rec["warnings"]:
            st.warning(w)

    # ── Rekomendasi Utama ─────────────────────────────────────────────────────
    if rec["primary"]:
        st.markdown("**✅ Analisis yang Disarankan (Mulai dari Sini):**")
        cols_per_row = 2
        items = rec["primary"]
        for i in range(0, len(items), cols_per_row):
            row_items = items[i : i + cols_per_row]
            cols = st.columns(len(row_items))
            for col, item in zip(cols, row_items):
                is_pro = item["modul"] in _PRO_MODULES
                badge = (
                    ' <span style="font-size:0.68rem;background:#e8d5a3;'
                    'color:#7a5c00;padding:1px 6px;border-radius:4px;'
                    'vertical-align:middle;">★ Pro</span>'
                    if is_pro else ""
                )
                with col:
                    st.markdown(
                        f'<div class="rs-narasi" style="margin-bottom:6px;min-height:80px;">'
                        f'{item["icon"]} <b>{item["uji"]}</b>{badge}<br/>'
                        f'<span style="font-size:0.82rem;color:#5f8ab5;">'
                        f'{item["alasan"]}</span>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                    if st.button(
                        f"Buka → {item['modul']}",
                        key=f"rec_primary_{item['modul']}_{i}",
                        use_container_width=True,
                    ):
                        st.session_state.active_menu = item["modul"]
                        st.rerun()

    # ── Analisis Lanjutan ─────────────────────────────────────────────────────
    if rec["secondary"]:
        st.markdown("<br/>", unsafe_allow_html=True)
        with st.expander("🔍 Analisis Lanjutan yang Relevan", expanded=False):
            st.caption(
                "Modul berikut relevan berdasarkan profil data Anda. "
                "Klik tombol untuk langsung membuka modul. "
                "Modul bertanda ★ Pro memerlukan lisensi Pro."
            )

            _GROUP_ORDER = [
                ("🟢", "Direkomendasikan Kuat"),
                ("🔵", "Analisis Lanjutan"),
                ("🟡", "Opsional / Kondisional"),
            ]

            for icon_key, group_label in _GROUP_ORDER:
                group_items = [
                    it for it in rec["secondary"] if it.get("icon") == icon_key
                ]
                if not group_items:
                    continue

                st.markdown(
                    f'<div style="font-size:0.8rem;font-weight:700;color:#185fa5;'
                    f'letter-spacing:0.03em;margin:14px 0 6px 0;">'
                    f'{icon_key} {group_label}</div>',
                    unsafe_allow_html=True,
                )

                cols_per_row = 2
                for i in range(0, len(group_items), cols_per_row):
                    row_items = group_items[i : i + cols_per_row]
                    cols = st.columns(len(row_items))
                    for col, item in zip(cols, row_items):
                        is_pro = item["modul"] in _PRO_MODULES
                        badge = (
                            ' <span style="font-size:0.68rem;background:#e8d5a3;'
                            'color:#7a5c00;padding:1px 6px;border-radius:4px;">'
                            '★ Pro</span>'
                            if is_pro else ""
                        )
                        with col:
                            st.markdown(
                                f'<div class="rs-narasi" style="margin-bottom:6px;'
                                f'min-height:80px;">'
                                f'<b>{item["uji"]}</b>{badge}<br/>'
                                f'<span style="font-size:0.8rem;color:#5f8ab5;">'
                                f'{item["alasan"]}</span>'
                                f'</div>',
                                unsafe_allow_html=True,
                            )
                            if st.button(
                                f"→ {item['modul']}",
                                key=f"rec_sec_{item['modul']}_{i}",
                                use_container_width=True,
                            ):
                                st.session_state.active_menu = item["modul"]
                                st.rerun()


def render(ctx: dict):
    st.markdown('<p class="rs-section-title">📁 Upload & Auto Cleaning</p>',
                unsafe_allow_html=True)
    st.markdown(
        '<p class="rs-section-sub">Unggah file data Anda. Sistem otomatis memeriksa kualitas data. '
        'Format didukung: CSV, Excel, SPSS (.sav), Stata (.dta), TXT.</p>',
        unsafe_allow_html=True,
    )

    uploaded = st.file_uploader(
        "Pilih file data Anda",
        type=["csv", "xlsx", "xls", "sav", "dta", "txt"],
        help="Format yang didukung: CSV, Excel (.xlsx/.xls), SPSS (.sav), Stata (.dta), Teks (.txt)",
    )

    if uploaded:
        if st.session_state.get("last_uploaded_filename") != uploaded.name:
            st.session_state.df_clean = None
            st.session_state.report = None
            st.session_state.last_uploaded_filename = uploaded.name
            st.session_state.pop("var_types", None)   # reset tipe saat file baru
            
        with st.spinner("🔄 Memuat dan memeriksa data..."):
            raw_df = load_data(uploaded)
        if raw_df is None:
            st.error("❌ Gagal membaca file. Pastikan format CSV, Excel, SPSS (.sav), Stata (.dta), atau TXT.")
            st.stop()

        # Pembersihan otomatis awal
        df_clean, report = auto_clean(raw_df)

        # ✅ Hanya pakai session_state jika file SAMA (sudah ada encoding sebelumnya)
        # Cukup load session state untuk display, bukan untuk overwrite df_clean aktif
        display_df = ss_get("df_clean") if ss_get("df_clean") is not None else df_clean
        display_report = ss_get("report") if ss_get("report") is not None else report

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(f"""<div class="rs-metric">
                <div class="rs-metric-label">Baris Awal</div>
                <div class="rs-metric-value">{report['original_rows']}</div></div>""",
                unsafe_allow_html=True)
        with c2:
            st.markdown(f"""<div class="rs-metric">
                <div class="rs-metric-label">Baris Valid</div>
                <div class="rs-metric-value">{report['rows_after_clean']}</div>
                <div class="rs-metric-sub">setelah cleaning</div></div>""",
                unsafe_allow_html=True)
        with c3:
            col_miss = "#a32d2d" if report["total_missing"] > 0 else "#3b6d11"
            st.markdown(f"""<div class="rs-metric">
                <div class="rs-metric-label">Missing Values</div>
                <div class="rs-metric-value" style="color:{col_miss}">{report['total_missing']}</div>
                </div>""", unsafe_allow_html=True)
        with c4:
            col_dup = "#a32d2d" if report["duplicates"] > 0 else "#3b6d11"
            st.markdown(f"""<div class="rs-metric">
                <div class="rs-metric-label">Duplikat Dihapus</div>
                <div class="rs-metric-value" style="color:{col_dup}">{report['duplicates']}</div>
                </div>""", unsafe_allow_html=True)

        # ─── FITUR BARU: AUTO-ENCODE KATEGORIK ───
        if report.get("encodable_cols"):
            st.markdown("<br/>", unsafe_allow_html=True)
            with st.expander("🛠️ Transformasi Variabel Kategorik (Gender, Pendidikan, dll)", expanded=True):
                st.info(f"Ditemukan kolom teks yang bisa diubah ke angka: **{', '.join(report['encodable_cols'])}**")
                
                to_encode = st.multiselect(
                    "Pilih kolom untuk dijadikan numerik (Label Encoding):",
                    options=report["encodable_cols"],
                    default=report["encodable_cols"]
                )
                
                if st.button("🚀 Jalankan Encoding", type="secondary"):
                    # 1. Jalankan proses encoding
                    encoded_df, mapping = encode_categorical(df_clean, to_encode)
                    
                    # 2. Update report secara lokal agar pilihan numerik bertambah
                    for col in to_encode:
                        if col in report["non_numeric_cols"]:
                            report["non_numeric_cols"].remove(col)
                        if col not in report["numeric_cols"]:
                            report["numeric_cols"].append(col)
                    
                    # 3. Simpan ke session state agar permanen
                    st.session_state.df_clean = encoded_df
                    st.session_state.report = report
                    st.session_state.mapping_info = mapping
                    
                    # 4. Tambahkan ke selected_cols secara otomatis
                    current_selected = st.session_state.get("selected_cols", [])
                    for col in to_encode:
                        if col not in current_selected:
                            current_selected.append(col)
                    st.session_state.selected_cols = current_selected

                    st.success(f"✅ Berhasil mengonversi: {', '.join(to_encode)}")
                    st.rerun()

        st.markdown("<br/>", unsafe_allow_html=True)

        # ─── TIPE VARIABEL ────────────────────────────────────────────────────
        with st.expander(
            "🏷️ Tipe Variabel (Opsional — untuk rekomendasi lebih akurat)",
            expanded=False,
        ):
            st.caption(
                "Sistem mendeteksi tipe variabel secara otomatis. "
                "Ubah jika ada yang tidak sesuai — hasilnya dipakai untuk rekomendasi analisis "
                "dan pemilihan kolom analitik."
            )

            # Gabungkan: var_types tersimpan (prioritas) + auto-detect (fallback)
            _saved_types   = st.session_state.get("var_types", {})
            _auto_types    = _auto_detect_var_types(display_df, display_report)
            _current_types = {
                col: _saved_types.get(col, _auto_types.get(col, "Numerik Kontinu"))
                for col in display_df.columns
            }

            _type_df = pd.DataFrame({
                "Kolom":         list(display_df.columns),
                "Tipe Variabel": [_current_types[c] for c in display_df.columns],
            })

            _edited = st.data_editor(
                _type_df,
                column_config={
                    "Kolom": st.column_config.TextColumn(
                        "Kolom", disabled=True, width="medium"
                    ),
                    "Tipe Variabel": st.column_config.SelectboxColumn(
                        "Tipe Variabel",
                        options=TYPE_OPTIONS,
                        required=True,
                        width="medium",
                    ),
                },
                hide_index=True,
                use_container_width=True,
                key="var_type_editor",
            )

            if st.button(
                "💾 Terapkan Tipe Variabel",
                key="btn_apply_var_types",
                type="secondary",
            ):
                _new_var_types = dict(zip(_edited["Kolom"], _edited["Tipe Variabel"]))
                st.session_state["var_types"] = _new_var_types

                # Update report hanya jika data sudah di-save (hindari konflik)
                if st.session_state.get("report") is not None:
                    _rep = st.session_state["report"].copy()
                    _rep["numeric_cols"] = [
                        c for c in display_df.columns
                        if _new_var_types.get(c) in _NUMERIC_TYPES
                    ]
                    _rep["non_numeric_cols"] = [
                        c for c in display_df.columns
                        if _new_var_types.get(c) not in _NUMERIC_TYPES
                    ]
                    st.session_state["report"] = _rep

                    # Sesuaikan selected_cols — hapus kolom non-analitik
                    _sel = [
                        c for c in st.session_state.get("selected_cols", [])
                        if _new_var_types.get(c) in _NUMERIC_TYPES
                    ]
                    st.session_state["selected_cols"] = _sel

                st.success(
                    f"✅ Tipe variabel diterapkan untuk {len(_new_var_types)} kolom."
                )
                st.rerun()

        st.markdown("<br/>", unsafe_allow_html=True)

        tab1, tab2 = st.tabs(["📋 Preview Data", "🔧 Detail Cleaning"])
        with tab1:
            st.markdown(f"**{len(df_clean)} baris × {len(df_clean.columns)} kolom**")
            st.dataframe(display_df.head(30), use_container_width=True, height=300)
        with tab2:
            if report["missing_per_col"]:
                st.warning("**Missing values per kolom:**")
                st.dataframe(
                    pd.DataFrame.from_dict(
                        report["missing_per_col"], orient="index", columns=["Jumlah Missing"]
                    ),
                    use_container_width=True,
                )
            else:
                st.success("Tidak ada missing values.")
            st.markdown(
                f"**Kolom numerik ({len(report['numeric_cols'])}):** "
                f"{', '.join(report['numeric_cols']) or '–'}"
            )
            st.markdown(
                f"**Kolom non-numerik ({len(report['non_numeric_cols'])}):** "
                f"{', '.join(report['non_numeric_cols']) or '–'}"
            )

        if st.button("✅ Simpan & Gunakan Data Ini", type="primary"):
            # Pakai display_df & display_report agar hasil encoding ikut tersimpan
            st.session_state.df_clean  = display_df
            st.session_state.report    = display_report
            st.session_state.ai_cache  = {}

            # Tentukan selected_cols: hormati var_types jika sudah diset,
            # fallback ke perilaku lama (numeric_cols[:10]) agar backward compat
            _vt = st.session_state.get("var_types", {})
            if _vt:
                _analytic = [
                    c for c in display_report["numeric_cols"]
                    if _vt.get(c, "Numerik Kontinu") in _NUMERIC_TYPES
                ]
                st.session_state.selected_cols = _analytic[:10]
            else:
                st.session_state.selected_cols = display_report["numeric_cols"][:10]

            st.success("✅ Data siap dianalisis! Lanjutkan ke modul berikutnya.")

        # Menampilkan pilihan kolom jika data sudah tersimpan
        if ss_get("df_clean") is not None:
            st.markdown("---")
            st.markdown("**🎯 Pilih Kolom untuk Analisis:**")
            selected = st.multiselect(
                "Kolom numerik yang akan dianalisis",
                options=display_report["numeric_cols"],
                default=[c for c in ss_get("selected_cols", []) if c in display_report["numeric_cols"]],
            )
            st.session_state.selected_cols = selected

        # ── Auto-Rekomendasi Uji ──────────────────────────────────────────────────────
    if ss_get("df_clean") is not None and ss_get("report") is not None:
        rec = recommend_analysis(ss_get("df_clean"), ss_get("report"))
        render_recommendation_card(rec)

    elif ss_get("df_clean") is not None:
        st.info("✅ Data sudah tersimpan. Lanjutkan ke modul analisis.")
        st.dataframe(ss_get("df_clean").head(10), use_container_width=True)
    else:
        st.markdown("""
        <div style='text-align:center; padding:3rem; color:#5f8ab5;'>
            <div style='font-size:3rem;'>📂</div>
            <p>Belum ada data. Unggah file <b>CSV, Excel, SPSS (.sav), Stata (.dta),</b> atau <b>TXT</b> untuk memulai.</p>
        </div>""", unsafe_allow_html=True)
