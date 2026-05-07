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

    # 1. Deskriptif — selalu
    primary.append({
        "uji":    "📊 Statistik Deskriptif",
        "alasan": f"Dataset memiliki {n_numeric} variabel numerik — selalu mulai dari ringkasan deskriptif.",
        "modul":  "Statistik Deskriptif",
        "icon":   "✅",
    })

    # 2. Validitas & Reliabilitas — jika banyak numerik (kuesioner)
    if n_numeric >= 5:
        primary.append({
            "uji":    "✅ Validitas & Reliabilitas (Cronbach's Alpha)",
            "alasan": f"{n_numeric} variabel numerik terdeteksi — kemungkinan data kuesioner skala Likert.",
            "modul":  "Validitas & Reliabilitas",
            "icon":   "✅",
        })

    # 3. Korelasi — jika ≥ 2 numerik
    if n_numeric >= 2:
        primary.append({
            "uji":    "🔗 Analisis Korelasi Pearson",
            "alasan": "Periksa hubungan linear antar variabel sebelum regresi.",
            "modul":  "Korelasi",
            "icon":   "✅",
        })

    # 4. Berdasarkan distribusi normal vs tidak
    if pct_normal >= 70:
        secondary.append({
            "uji":    "📈 Regresi Linier / OLS+",
            "alasan": f"{len(normal_cols)} variabel berdistribusi normal — uji parametrik direkomendasikan.",
            "modul":  "Regresi & Prediksi",
            "icon":   "🟢",
        })
        secondary.append({
            "uji":    "📊 ANOVA + Post-hoc",
            "alasan": "Data normal + ada variabel kategorik → ANOVA lebih tepat dari Kruskal-Wallis.",
            "modul":  "ANOVA & Post-hoc",
            "icon":   "🟢",
        })
    else:
        secondary.append({
            "uji":    "📉 Uji Non-Parametrik (Kruskal-Wallis / Mann-Whitney)",
            "alasan": f"{len(non_normal_cols)} variabel tidak normal → pertimbangkan uji non-parametrik.",
            "modul":  "Analisis Kelompok / Uji Beda",
            "icon":   "🟡",
        })

    # 5. Mediasi — jika ≥ 3 numerik
    if n_numeric >= 3:
        secondary.append({
            "uji":    "🔀 Analisis Mediasi (Baron & Kenny)",
            "alasan": f"Dengan {n_numeric} variabel, Anda dapat menguji hubungan mediasi X → M → Y.",
            "modul":  "Mediasi",
            "icon":   "🔵",
        })

    # 6. Moderasi — jika ≥ 3 numerik
    if n_numeric >= 3:
        secondary.append({
            "uji":    "🎛️ Analisis Moderasi (Interaksi)",
            "alasan": "Uji apakah variabel ketiga memoderasi hubungan X → Y.",
            "modul":  "Moderasi",
            "icon":   "🔵",
        })

    # 7. Logistik — jika ada variabel biner
    for col in numeric_cols:
        s = pd.to_numeric(df[col], errors="coerce").dropna()
        if set(s.unique()).issubset({0, 1, 0.0, 1.0}) and len(s) > 10:
            secondary.append({
                "uji":    f"📉 Regresi Logistik (variabel biner: {col})",
                "alasan": f"Kolom '{col}' terdeteksi sebagai variabel biner (0/1).",
                "modul":  "Regresi Logistik",
                "icon":   "🔵",
            })
            break

    # 8. Kelompok — jika ada kategorik
    if n_categorical > 0:
        primary.append({
            "uji":    "📂 Analisis Kelompok",
            "alasan": f"Ditemukan {n_categorical} variabel kategorik ({', '.join(non_numeric[:3])}) — bandingkan rata-rata antar kelompok.",
            "modul":  "Analisis Kelompok",
            "icon":   "✅",
        })

    # 9. Outlier — selalu
    secondary.append({
        "uji":    "🎯 Deteksi Outlier (IQR / Z-Score)",
        "alasan": "Periksa nilai ekstrem sebelum menjalankan analisis lanjutan.",
        "modul":  "Deteksi Outlier",
        "icon":   "⚠️",
    })

    # ── Peringatan ────────────────────────────────────────────────────────
    if total_missing > 0:
        pct_miss = round(total_missing / (n_rows * max(n_numeric, 1)) * 100, 1)
        warnings.append(f"⚠️ Ada {total_missing} missing values ({pct_miss}%). Pertimbangkan imputasi sebelum regresi.")

    if n_rows < 30:
        warnings.append(f"⚠️ Ukuran sampel kecil (N = {n_rows}). Hasil uji statistik mungkin tidak stabil.")

    if non_normal_cols:
        warnings.append(f"⚠️ Variabel tidak normal: {', '.join(non_normal_cols[:5])}. Pertimbangkan uji non-parametrik.")

    return {
        "primary":      primary,
        "secondary":    secondary,
        "warnings":     warnings,
        "data_profile": data_profile,
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

    # Peringatan
    if rec["warnings"]:
        for w in rec["warnings"]:
            st.warning(w)

    # Rekomendasi utama
    if rec["primary"]:
        st.markdown("**✅ Analisis yang Disarankan (Mulai dari Sini):**")
        for item in rec["primary"]:
            st.markdown(
                f'<div class="rs-narasi" style="margin-bottom:8px;">'
                f'{item["icon"]} <b>{item["uji"]}</b><br/>'
                f'<span style="font-size:0.85rem;color:#5f8ab5;">{item["alasan"]}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # Rekomendasi tambahan
    if rec["secondary"]:
        with st.expander("🔍 Analisis Lanjutan yang Relevan"):
            for item in rec["secondary"]:
                st.markdown(
                    f'{item["icon"]} **{item["uji"]}** — {item["alasan"]}'
                )


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
            st.session_state.df_clean = df_clean
            st.session_state.report = report
            st.session_state.selected_cols = report["numeric_cols"][:10]
            st.session_state.ai_cache = {}
            st.success("✅ Data siap dianalisis! Lanjutkan ke modul berikutnya.")

        # Menampilkan pilihan kolom jika data sudah tersimpan
        if ss_get("df_clean") is not None:
            st.markdown("---")
            st.markdown("**🎯 Pilih Kolom untuk Analisis:**")
            selected = st.multiselect(
                "Kolom numerik yang akan dianalisis",
                options=report["numeric_cols"],
                default=[c for c in ss_get("selected_cols", []) if c in report["numeric_cols"]],
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