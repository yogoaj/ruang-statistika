"""
modules/wizard.py — Wizard Pemilihan Metode Analisis (Free)
Ruang Statistika v4.9 - Wizard v2.4.2

Panduan interaktif 4 langkah untuk membantu pengguna memilih
uji statistik yang tepat berdasarkan tujuan, data, dan jumlah variabel.
Tidak memerlukan AI, tidak menyentuh database.

Changelog v2.4.2:
- [Fix] Tombol 'Ubah jawaban terakhir' sekarang berfungsi (tambah _pause_auto)
- [Fix] Cegah auto-advance loop saat kembali dari hasil

Changelog v2.4.1:
- [UI] Tooltip hover jadi kuning + border amber agar terlihat
- [UI] Help text diubah jadi info-box biru permanen dengan ikon 💡

Changelog v2.4:
- [New] Auto-advance di Langkah 4 — hemat 1 klik, hasil muncul otomatis
- [New] Tombol '↶ Ubah jawaban terakhir' di hasil untuk koreksi cepat
- [Improve] Layout tombol hasil jadi 2 baris agar tidak padat

Changelog v2.3:
- [Fix #9] Render hanya 1 langkah aktif (step == X) — hilangkan scroll akumulatif
- [Fix #10] Tambah caption konteks di tiap step untuk orientasi

Changelog v2.2:
- [Fix #1] Reset wizard_normal & wizard_sample saat tujuan/skala/konteks berubah
- [Fix #2] Swap normalitas hanya untuk uji yang normal_sensitive=True
- [Fix #3] "Belum cek" tampilkan saran cek normalitas tanpa blokir alur
- [Fix #4] Tambah spacer + border sebelum tombol "Lihat Rekomendasi"
- [Fix #5] Tambah tombol "← Kembali" per langkah tanpa reset penuh
- [Fix #6] Hapus tujuan duplikat "Menguji perbedaan dengan nilai acuan",
           gabung ke "Membandingkan kelompok → 1 kelompok vs nilai acuan"
- [Fix #7] Tambah entry yang hilang: McNemar, Chi-Square 3+ nominal,
           Binomial/GoF, Wilcoxon one-sample ordinal
- [Fix #8] Tambah entry Ordinal 1 prediktor & 2+ prediktor untuk prediksi
"""

import streamlit as st


# ══════════════════════════════════════════════════════════════════════════════
# DECISION TREE
# Struktur: {(tujuan, skala, konteks): rekomendasi}
# normal_sensitive=True  → rekomendasi di-swap ke alternatif jika tidak normal
# normal_sensitive=False → normalitas tidak mempengaruhi rekomendasi
# ══════════════════════════════════════════════════════════════════════════════

DECISION_TREE = {

    # ── HUBUNGAN / KORELASI ────────────────────────────────────────────────────

    ("Melihat hubungan antar variabel", "Interval / Rasio", "2 variabel"):
    {
        "uji":              "Korelasi Pearson",
        "menu_key":         "Korelasi",
        "deskripsi":        "Mengukur kekuatan dan arah hubungan linier antara dua variabel numerik.",
        "syarat":           "Kedua variabel berdistribusi normal, hubungan bersifat linier.",
        "alternatif":       "Korelasi Spearman (jika data tidak normal)",
        "alt_key":          "Uji Nonparametrik",
        "tips":             "Cek normalitas dulu di modul Statistik Deskriptif sebelum memilih Pearson atau Spearman.",
        "normal_sensitive": True,
    },
    ("Melihat hubungan antar variabel", "Ordinal", "2 variabel"):
    {
        "uji":              "Korelasi Spearman / Kendall Tau",
        "menu_key":         "Uji Nonparametrik",
        "deskripsi":        "Mengukur korelasi berbasis peringkat — cocok untuk data ordinal atau yang tidak normal.",
        "syarat":           "Tidak ada asumsi distribusi khusus.",
        "alternatif":       "Korelasi Pearson (jika data sebenarnya interval/rasio dan normal)",
        "alt_key":          "Korelasi",
        "tips":             "Skala Likert (1–5) umumnya diperlakukan sebagai ordinal, gunakan Spearman.",
        "normal_sensitive": False,
    },
    ("Melihat hubungan antar variabel", "Nominal / Kategorikal", "2 variabel"):
    {
        "uji":              "Chi-Square / Uji Asosiasi",
        "menu_key":         "Uji Nonparametrik",
        "deskripsi":        "Menguji apakah ada hubungan (asosiasi) antara dua variabel kategorikal.",
        "syarat":           "Frekuensi harapan setiap sel ≥ 5.",
        "alternatif":       "Fisher Exact Test (jika frekuensi harapan < 5)",
        "alt_key":          "Uji Nonparametrik",
        "tips":             "Untuk tabel 2×2, gunakan koreksi Yates. Untuk tabel lebih besar, gunakan Cramér's V untuk effect size.",
        "normal_sensitive": False,
    },
    ("Melihat hubungan antar variabel", "Interval / Rasio", "3+ variabel sekaligus"):
    {
        "uji":              "Matriks Korelasi Pearson / Parsial",
        "menu_key":         "Korelasi",
        "deskripsi":        "Melihat hubungan antar banyak variabel numerik sekaligus, bisa kontrol variabel lain dengan korelasi parsial.",
        "syarat":           "Data berdistribusi normal multivariat, hubungan linier.",
        "alternatif":       "Matriks Korelasi Spearman",
        "alt_key":          "Uji Nonparametrik",
        "tips":             "Gunakan heatmap korelasi di modul EDA untuk visualisasi cepat.",
        "normal_sensitive": True,
    },
    ("Melihat hubungan antar variabel", "Ordinal", "3+ variabel sekaligus"):
    {
        "uji":              "Matriks Korelasi Spearman / Kendall",
        "menu_key":         "Uji Nonparametrik",
        "deskripsi":        "Korelasi berbasis peringkat untuk banyak variabel ordinal.",
        "syarat":           "Tidak perlu asumsi normal.",
        "alternatif":       "Korelasi Pearson (jika data sebenarnya interval)",
        "alt_key":          "Korelasi",
        "tips":             "Cocok untuk data Likert dengan banyak item.",
        "normal_sensitive": False,
    },

    # ── PREDIKSI / REGRESI ─────────────────────────────────────────────────────

    ("Memprediksi nilai variabel", "Interval / Rasio", "1 prediktor"):
    {
        "uji":              "Regresi Linier Sederhana",
        "menu_key":         "Regresi",
        "deskripsi":        "Memprediksi variabel dependen numerik dari satu prediktor numerik.",
        "syarat":           "Residual normal, homoskedastis, tidak ada autokorelasi, hubungan linier.",
        "alternatif":       "Regresi Robust / RLM (jika ada outlier berpengaruh)",
        "alt_key":          "OLS Robust",
        "tips":             "Selalu cek uji asumsi klasik (VIF, Glejser, Durbin-Watson) setelah regresi — gunakan modul OLS+ untuk pemeriksaan lengkap.",
        "normal_sensitive": True,
    },
    ("Memprediksi nilai variabel", "Interval / Rasio", "2+ prediktor"):
    {
        "uji":              "Regresi Linier Berganda (OLS)",
        "menu_key":         "Regresi",
        "deskripsi":        "Memprediksi variabel dependen dari beberapa prediktor sekaligus.",
        "syarat":           "Tidak ada multikolinearitas (VIF < 10), residual normal dan homoskedastis.",
        "alternatif":       "Regresi Robust / WLS (jika heteroskedastisitas tidak bisa diatasi)",
        "alt_key":          "OLS Robust",
        "tips":             "Gunakan modul OLS+ untuk pemeriksaan asumsi klasik lengkap. Jika VIF > 10, pertimbangkan menghapus atau menggabungkan prediktor yang berkorelasi tinggi.",
        "normal_sensitive": True,
    },
    ("Memprediksi nilai variabel", "Nominal / Kategorikal", "1 prediktor"):
    {
        "uji":              "Regresi Logistik Biner",
        "menu_key":         "Regresi Logistik",
        "deskripsi":        "Memprediksi probabilitas kejadian kategori (ya/tidak) dari satu atau lebih prediktor.",
        "syarat":           "Variabel dependen biner (0/1), tidak ada multikolinearitas antar prediktor.",
        "alternatif":       "Regresi Logistik Multinomial (jika kategori > 2)",
        "alt_key":          "Regresi Logistik",
        "tips":             "Perhatikan odds ratio (OR) — OR > 1 berarti prediktor meningkatkan peluang kejadian. Gunakan ROC-AUC untuk evaluasi model (fitur Pro).",
        "normal_sensitive": False,
    },
    ("Memprediksi nilai variabel", "Nominal / Kategorikal", "2+ prediktor"):
    {
        "uji":              "Regresi Logistik Berganda",
        "menu_key":         "Regresi Logistik",
        "deskripsi":        "Memprediksi kategori (misal: lulus/tidak, ya/tidak) dari beberapa prediktor.",
        "syarat":           "Variabel dependen biner, sampel cukup (minimal 10 kejadian per prediktor).",
        "alternatif":       "Random Forest / Decision Tree (untuk prediksi non-linier, tidak tersedia di modul ini)",
        "alt_key":          "Regresi Logistik",
        "tips":             "Cek Nagelkerke R² untuk menilai seberapa baik model menjelaskan variasi data.",
        "normal_sensitive": False,
    },
    ("Memprediksi nilai variabel", "Nominal / Kategorikal", "Dependen ordinal (bertingkat)"):
    {
        "uji":              "Regresi Logistik Ordinal",
        "menu_key":         "Regresi Logistik",
        "deskripsi":        "Memprediksi variabel dependen bertingkat (misal: rendah/sedang/tinggi).",
        "syarat":           "Asumsi proportional odds terpenuhi.",
        "alternatif":       "Regresi Multinomial (jika tingkatan tidak berurutan)",
        "alt_key":          "Regresi Logistik",
        "tips":             "Pastikan urutan kategori sudah benar sebelum analisis.",
        "normal_sensitive": False,
    },
    # [Fix #8] Entry baru: Ordinal sebagai skala prediktor
    ("Memprediksi nilai variabel", "Ordinal", "1 prediktor"):
    {
        "uji":              "Regresi Linier / Spearman (tergantung distribusi)",
        "menu_key":         "Regresi",
        "deskripsi":        "Jika dependen numerik dan prediktor ordinal, OLS masih bisa digunakan dengan kehati-hatian. Alternatifnya gunakan korelasi Spearman.",
        "syarat":           "Pastikan skala ordinal memiliki interval yang cukup merata (≥5 kategori).",
        "alternatif":       "Korelasi Spearman (lebih aman untuk prediktor ordinal)",
        "alt_key":          "Uji Nonparametrik",
        "tips":             "Banyak penelitian skripsi menggunakan OLS dengan prediktor Likert — sah secara praktis, tapi Spearman lebih tepat secara statistik.",
        "normal_sensitive": True,
    },
    ("Memprediksi nilai variabel", "Ordinal", "2+ prediktor"):
    {
        "uji":              "Regresi Linier Berganda (dengan catatan)",
        "menu_key":         "Regresi",
        "deskripsi":        "OLS dengan prediktor ordinal (Likert) umum digunakan dalam penelitian sosial, namun perlu kehati-hatian dalam interpretasi.",
        "syarat":           "Residual normal, tidak ada multikolinearitas. Skala ordinal diperlakukan sebagai kontinu.",
        "alternatif":       "Regresi Ordinal atau pendekatan nonparametrik",
        "alt_key":          "Regresi Logistik",
        "tips":             "Jika semua prediktor adalah skala Likert 1–5, pastikan jumlah item cukup dan distribusi tidak terlalu skewed.",
        "normal_sensitive": True,
    },
    ("Memprediksi nilai variabel", "Ordinal", "Dependen ordinal (bertingkat)"):
    {
        "uji":              "Regresi Logistik Ordinal",
        "menu_key":         "Regresi Logistik",
        "deskripsi":        "Memprediksi variabel dependen bertingkat (misal: rendah/sedang/tinggi) dari prediktor ordinal.",
        "syarat":           "Asumsi proportional odds terpenuhi.",
        "alternatif":       "Regresi Multinomial (jika tingkatan tidak berurutan)",
        "alt_key":          "Regresi Logistik",
        "tips":             "Pastikan urutan kategori sudah benar sebelum analisis.",
        "normal_sensitive": False,
    },

    # ── PERBANDINGAN KELOMPOK ──────────────────────────────────────────────────

    ("Membandingkan kelompok", "Interval / Rasio", "2 kelompok independen"):
    {
        "uji":              "Independent Samples t-test",
        "menu_key":         "Uji Beda",
        "deskripsi":        "Membandingkan rata-rata dua kelompok yang berbeda (tidak berpasangan).",
        "syarat":           "Data berdistribusi normal di setiap kelompok, varians homogen (uji Levene).",
        "alternatif":       "Mann-Whitney U (jika tidak normal atau ordinal)",
        "alt_key":          "Uji Beda",
        "tips":             "Jika varians tidak homogen, gunakan Welch t-test (tersedia otomatis di modul Uji Beda).",
        "normal_sensitive": True,
    },
    ("Membandingkan kelompok", "Interval / Rasio", "2 kelompok berpasangan"):
    {
        "uji":              "Paired Samples t-test",
        "menu_key":         "Uji Beda",
        "deskripsi":        "Membandingkan rata-rata dua pengukuran pada subjek yang sama (pre-post, sebelum-sesudah).",
        "syarat":           "Selisih skor berdistribusi normal.",
        "alternatif":       "Wilcoxon Signed-Rank (jika tidak normal)",
        "alt_key":          "Uji Nonparametrik",
        "tips":             "Cocok untuk desain pre-test post-test atau studi crossover.",
        "normal_sensitive": True,
    },
    ("Membandingkan kelompok", "Interval / Rasio", "3+ kelompok independen"):
    {
        "uji":              "One-Way ANOVA",
        "menu_key":         "ANOVA",
        "deskripsi":        "Membandingkan rata-rata tiga kelompok atau lebih sekaligus.",
        "syarat":           "Data normal di setiap kelompok, varians homogen (uji Levene).",
        "alternatif":       "Kruskal-Wallis (jika tidak normal atau ordinal)",
        "alt_key":          "ANOVA",
        "tips":             "Jika ANOVA signifikan, lakukan uji post-hoc (Tukey HSD) untuk mengetahui pasangan kelompok mana yang berbeda — tersedia di modul ANOVA Pro.",
        "normal_sensitive": True,
    },
    ("Membandingkan kelompok", "Interval / Rasio", "3+ kelompok berpasangan"):
    {
        "uji":              "Repeated Measures ANOVA",
        "menu_key":         "ANOVA",
        "deskripsi":        "Membandingkan rata-rata ≥3 pengukuran pada subjek yang sama.",
        "syarat":           "Normalitas selisih, sphericity (uji Mauchly).",
        "alternatif":       "Friedman Test (jika tidak normal)",
        "alt_key":          "ANOVA",
        "tips":             "Gunakan jika desain pre-post-followup.",
        "normal_sensitive": True,
    },
    ("Membandingkan kelompok", "Interval / Rasio", "1 kelompok vs nilai acuan"):
    {
        "uji":              "One-Sample t-test",
        "menu_key":         "Uji Beda",
        "deskripsi":        "Menguji apakah rata-rata sampel berbeda dari nilai hipotesis tertentu.",
        "syarat":           "Data berdistribusi normal.",
        "alternatif":       "Wilcoxon Signed-Rank one-sample (jika tidak normal)",
        "alt_key":          "Uji Nonparametrik",
        "tips":             "Contoh: apakah rata-rata IPK mahasiswa = 3.0?",
        "normal_sensitive": True,
    },
    ("Membandingkan kelompok", "Ordinal", "2 kelompok independen"):
    {
        "uji":              "Mann-Whitney U",
        "menu_key":         "Uji Beda",
        "deskripsi":        "Alternatif nonparametrik untuk membandingkan dua kelompok independen berbasis peringkat.",
        "syarat":           "Tidak ada asumsi distribusi. Cocok untuk skala ordinal atau data tidak normal.",
        "alternatif":       "Independent t-test (jika data sebenarnya interval dan normal)",
        "alt_key":          "Uji Beda",
        "tips":             "Sering digunakan untuk data Likert antar kelompok (misal: pria vs wanita).",
        "normal_sensitive": False,
    },
    ("Membandingkan kelompok", "Ordinal", "2 kelompok berpasangan"):
    {
        "uji":              "Wilcoxon Signed-Rank",
        "menu_key":         "Uji Nonparametrik",
        "deskripsi":        "Membandingkan dua pengukuran berpasangan tanpa asumsi normalitas.",
        "syarat":           "Data berpasangan (subjek yang sama diukur dua kali).",
        "alternatif":       "Paired t-test (jika selisih berdistribusi normal)",
        "alt_key":          "Uji Beda",
        "tips":             "Pilihan utama untuk pre-post dengan skala ordinal atau sampel kecil.",
        "normal_sensitive": False,
    },
    ("Membandingkan kelompok", "Ordinal", "3+ kelompok independen"):
    {
        "uji":              "Kruskal-Wallis",
        "menu_key":         "ANOVA",
        "deskripsi":        "Alternatif nonparametrik untuk ANOVA — membandingkan tiga kelompok atau lebih berbasis peringkat.",
        "syarat":           "Tidak ada asumsi distribusi, skala minimal ordinal.",
        "alternatif":       "One-Way ANOVA (jika data normal dan varians homogen)",
        "alt_key":          "ANOVA",
        "tips":             "Tersedia di modul ANOVA — aktifkan opsi Kruskal-Wallis. Untuk post-hoc, gunakan Dunn test.",
        "normal_sensitive": False,
    },
    ("Membandingkan kelompok", "Ordinal", "3+ kelompok berpasangan"):
    {
        "uji":              "Friedman Test",
        "menu_key":         "ANOVA",
        "deskripsi":        "Alternatif nonparametrik untuk repeated measures dengan data ordinal.",
        "syarat":           "Data berpasangan, skala minimal ordinal.",
        "alternatif":       "Repeated Measures ANOVA (jika normal)",
        "alt_key":          "ANOVA",
        "tips":             "Lanjutkan dengan uji post-hoc Wilcoxon dengan koreksi Bonferroni.",
        "normal_sensitive": False,
    },
    # [Fix #7] Entry baru: Ordinal 1 kelompok vs nilai acuan
    ("Membandingkan kelompok", "Ordinal", "1 kelompok vs nilai acuan"):
    {
        "uji":              "Wilcoxon Signed-Rank (one-sample)",
        "menu_key":         "Uji Nonparametrik",
        "deskripsi":        "Menguji apakah median sampel berbeda dari nilai acuan tanpa asumsi normalitas.",
        "syarat":           "Data minimal ordinal, tidak perlu asumsi distribusi.",
        "alternatif":       "One-Sample t-test (jika data normal)",
        "alt_key":          "Uji Beda",
        "tips":             "Cocok untuk data Likert yang dibandingkan dengan nilai tengah skala.",
        "normal_sensitive": False,
    },
    ("Membandingkan kelompok", "Nominal / Kategorikal", "2 kelompok independen"):
    {
        "uji":              "Chi-Square / Fisher Exact",
        "menu_key":         "Uji Nonparametrik",
        "deskripsi":        "Menguji apakah proporsi kategori berbeda antar kelompok.",
        "syarat":           "Frekuensi harapan ≥ 5 (Chi-Square) atau < 5 (Fisher Exact).",
        "alternatif":       "McNemar Test (jika data berpasangan/matched)",
        "alt_key":          "Uji Nonparametrik",
        "tips":             "Contoh: apakah proporsi lulus berbeda antara kelas A dan kelas B?",
        "normal_sensitive": False,
    },
    # [Fix #7] Entry yang hilang: Nominal berpasangan → McNemar
    ("Membandingkan kelompok", "Nominal / Kategorikal", "2 kelompok berpasangan"):
    {
        "uji":              "McNemar Test",
        "menu_key":         "Uji Nonparametrik",
        "deskripsi":        "Menguji perubahan proporsi pada subjek yang sama sebelum dan sesudah intervensi.",
        "syarat":           "Data berpasangan, variabel biner (ya/tidak, lulus/tidak).",
        "alternatif":       "Chi-Square (jika kelompok independen)",
        "alt_key":          "Uji Nonparametrik",
        "tips":             "Contoh: apakah proporsi yang 'setuju' berubah sebelum dan sesudah pelatihan?",
        "normal_sensitive": False,
    },
    # [Fix #7] Entry yang hilang: Nominal 3+ kelompok independen
    ("Membandingkan kelompok", "Nominal / Kategorikal", "3+ kelompok independen"):
    {
        "uji":              "Chi-Square (tabel RxC)",
        "menu_key":         "Uji Nonparametrik",
        "deskripsi":        "Menguji asosiasi antara variabel kategorikal dengan 3+ kategori.",
        "syarat":           "Frekuensi harapan setiap sel ≥ 5.",
        "alternatif":       "Fisher Exact (jika frekuensi kecil)",
        "alt_key":          "Uji Nonparametrik",
        "tips":             "Gunakan Cramér's V untuk mengukur kekuatan asosiasi.",
        "normal_sensitive": False,
    },
    # [Fix #7] Entry yang hilang: Nominal 1 kelompok vs nilai acuan → Binomial/GoF
    ("Membandingkan kelompok", "Nominal / Kategorikal", "1 kelompok vs nilai acuan"):
    {
        "uji":              "Binomial Test / Chi-Square Goodness of Fit",
        "menu_key":         "Uji Nonparametrik",
        "deskripsi":        "Menguji apakah proporsi kategori sesuai dengan proporsi harapan.",
        "syarat":           "Sampel independen.",
        "alternatif":       "Exact Binomial (untuk sampel kecil)",
        "alt_key":          "Uji Nonparametrik",
        "tips":             "Contoh: apakah proporsi pria/wanita = 50:50?",
        "normal_sensitive": False,
    },

    # ── MELIHAT STRUKTUR DATA ──────────────────────────────────────────────────

    ("Melihat struktur / pola data", "Interval / Rasio", "Eksplorasi awal"):
    {
        "uji":              "Exploratory Data Analysis (EDA)",
        "menu_key":         "EDA",
        "deskripsi":        "Visualisasi distribusi, outlier, dan korelasi awal sebelum analisis lebih lanjut.",
        "syarat":           "Tidak ada asumsi khusus — cocok sebagai langkah pertama.",
        "alternatif":       "Statistik Deskriptif (untuk ringkasan numerik)",
        "alt_key":          "Deskriptif",
        "tips":             "Selalu mulai dari sini sebelum memilih uji inferensial. EDA membantu deteksi outlier dan distribusi data.",
        "normal_sensitive": False,
    },
    ("Melihat struktur / pola data", "Interval / Rasio", "Reduksi dimensi / faktor"):
    {
        "uji":              "Exploratory Factor Analysis (EFA)",
        "menu_key":         "EFA",
        "deskripsi":        "Mengidentifikasi faktor-faktor laten yang menjelaskan pola korelasi antar item/variabel.",
        "syarat":           "KMO > 0.5, uji Bartlett signifikan, sampel minimal 100 atau 5× jumlah item.",
        "alternatif":       "PCA — Principal Component Analysis (untuk reduksi dimensi, bukan pengukuran laten)",
        "alt_key":          "EFA",
        "tips":             "EFA digunakan untuk eksplorasi (belum tahu struktur faktor). Jika sudah tahu teorinya, gunakan CFA.",
        "normal_sensitive": False,
    },
    ("Melihat struktur / pola data", "Interval / Rasio", "Validasi instrumen / kuesioner"):
    {
        "uji":              "Confirmatory Factor Analysis (CFA)",
        "menu_key":         "CFA",
        "deskripsi":        "Menguji apakah model pengukuran yang sudah dihipotesiskan sesuai dengan data.",
        "syarat":           "Model sudah ditentukan sebelumnya, sampel minimal 200 disarankan.",
        "alternatif":       "EFA (jika belum punya hipotesis struktur faktor)",
        "alt_key":          "EFA",
        "tips":             "Cek fit indices: CFI ≥ 0.95, RMSEA ≤ 0.05, SRMR ≤ 0.08.",
        "normal_sensitive": False,
    },
    ("Melihat struktur / pola data", "Interval / Rasio", "Pengelompokan objek / segmentasi"):
    {
        "uji":              "Analisis Klaster (K-Means / Hierarki)",
        "menu_key":         "Klaster",
        "deskripsi":        "Mengelompokkan observasi ke dalam klaster berdasarkan kemiripan karakteristik.",
        "syarat":           "Variabel perlu distandardisasi. Tentukan jumlah klaster dengan Elbow Method.",
        "alternatif":       "Analisis Kelompok (jika pengelompokan sudah diketahui sebelumnya)",
        "alt_key":          "Kelompok",
        "tips":             "K-Means cocok untuk data besar. Hierarki (dendrogram) cocok untuk eksplorasi jumlah klaster optimal.",
        "normal_sensitive": False,
    },

    # ── MEDIASI / MODERASI ─────────────────────────────────────────────────────

    ("Menguji peran variabel ketiga", "Interval / Rasio", "Variabel mediator"):
    {
        "uji":              "Analisis Mediasi (Bootstrap CI)",
        "menu_key":         "Mediasi",
        "deskripsi":        "Menguji apakah pengaruh X terhadap Y dimediasi (diperantarai) oleh variabel M.",
        "syarat":           "Sampel minimal 200 untuk bootstrap stabil. Semua variabel numerik.",
        "alternatif":       "SEM (jika ada konstruk laten atau jalur yang lebih kompleks)",
        "alt_key":          "SEM",
        "tips":             "Gunakan 5000 bootstrap iterations untuk CI yang stabil. Mediasi parsial jika direct effect masih signifikan, penuh jika tidak.",
        "normal_sensitive": False,
    },
    ("Menguji peran variabel ketiga", "Interval / Rasio", "Variabel moderator"):
    {
        "uji":              "Analisis Moderasi (Interaction Effect)",
        "menu_key":         "Moderasi",
        "deskripsi":        "Menguji apakah kekuatan pengaruh X terhadap Y berubah tergantung nilai variabel moderator W.",
        "syarat":           "Semua variabel numerik, variabel perlu di-mean-center sebelum interaksi.",
        "alternatif":       "Mediasi Moderasi / Moderated Mediation (SEM)",
        "alt_key":          "SEM",
        "tips":             "Johnson-Neyman interval menunjukkan rentang nilai moderator di mana efek X signifikan — sangat berguna untuk interpretasi.",
        "normal_sensitive": False,
    },
    ("Menguji peran variabel ketiga", "Interval / Rasio", "Mediator + Moderator"):
    {
        "uji":              "Moderated Mediation (SEM)",
        "menu_key":         "SEM",
        "deskripsi":        "Model kombinasi di mana mediasi dipengaruhi oleh moderator.",
        "syarat":           "Sampel besar (≥200), teori kuat.",
        "alternatif":       "Analisis terpisah Mediasi + Moderasi",
        "alt_key":          "Mediasi",
        "tips":             "Gunakan modul SEM untuk model kompleks ini.",
        "normal_sensitive": False,
    },

    # ── VALIDITAS & RELIABILITAS ───────────────────────────────────────────────

    ("Menguji kualitas instrumen", "Ordinal", "Validitas & reliabilitas"):
    {
        "uji":              "Validitas (CITC) & Reliabilitas (Cronbach Alpha)",
        "menu_key":         "Validitas",
        "deskripsi":        "Menguji apakah item kuesioner valid (CITC ≥ r-tabel) dan reliabel (α ≥ 0.70).",
        "syarat":           "Minimal 10 responden untuk uji coba. Skala Likert atau sejenisnya.",
        "alternatif":       "ICC — Intraclass Correlation (untuk reliabilitas antar rater)",
        "alt_key":          "Validitas",
        "tips":             "Item dengan CITC < r-tabel perlu direvisi atau dihapus. Alpha if deleted menunjukkan dampak penghapusan setiap item.",
        "normal_sensitive": False,
    },
}


# ══════════════════════════════════════════════════════════════════════════════
# OPSI PERTANYAAN
# [Fix #6] Tujuan "Menguji perbedaan dengan nilai acuan" dihapus —
#          sudah tercakup di "Membandingkan kelompok → 1 kelompok vs nilai acuan"
# ══════════════════════════════════════════════════════════════════════════════

TUJUAN_OPTIONS = [
    "Melihat hubungan antar variabel",
    "Memprediksi nilai variabel",
    "Membandingkan kelompok",
    "Melihat struktur / pola data",
    "Menguji peran variabel ketiga",
    "Menguji kualitas instrumen",
]

KONTEKS_OPTIONS = {
    "Melihat hubungan antar variabel": [
        "2 variabel",
        "3+ variabel sekaligus",
    ],
    "Memprediksi nilai variabel": [
        "1 prediktor",
        "2+ prediktor",
        "Dependen ordinal (bertingkat)",
    ],
    "Membandingkan kelompok": [
        "2 kelompok independen",
        "2 kelompok berpasangan",
        "3+ kelompok independen",
        "3+ kelompok berpasangan",
        "1 kelompok vs nilai acuan",
    ],
    "Melihat struktur / pola data": [
        "Eksplorasi awal",
        "Reduksi dimensi / faktor",
        "Validasi instrumen / kuesioner",
        "Pengelompokan objek / segmentasi",
    ],
    "Menguji peran variabel ketiga": [
        "Variabel mediator",
        "Variabel moderator",
        "Mediator + Moderator",
    ],
    "Menguji kualitas instrumen": [
        "Validitas & reliabilitas",
    ],
}

SKALA_OPTIONS = [
    "Interval / Rasio",
    "Ordinal",
    "Nominal / Kategorikal",
]

SKALA_PER_TUJUAN = {
    "Melihat hubungan antar variabel":  ["Interval / Rasio", "Ordinal", "Nominal / Kategorikal"],
    "Memprediksi nilai variabel":       ["Interval / Rasio", "Ordinal", "Nominal / Kategorikal"],
    "Membandingkan kelompok":           ["Interval / Rasio", "Ordinal", "Nominal / Kategorikal"],
    "Melihat struktur / pola data":     ["Interval / Rasio"],
    "Menguji peran variabel ketiga":    ["Interval / Rasio"],
    "Menguji kualitas instrumen":       ["Ordinal"],
}

SKALA_HELP = {
    "Interval / Rasio":       "Angka murni — skor ujian, berat badan, pendapatan, usia",
    "Ordinal":                "Peringkat / skala bertingkat — Likert 1–5, tingkat kepuasan",
    "Nominal / Kategorikal":  "Kategori tanpa urutan — jenis kelamin, jurusan, kota",
}

KONTEKS_HELP = {
    "2 variabel":                       "Hanya ada X dan Y",
    "3+ variabel sekaligus":            "Matriks korelasi atau korelasi parsial antar banyak variabel",
    "1 prediktor":                      "Satu variabel bebas (X) → satu variabel terikat (Y)",
    "2+ prediktor":                     "Dua atau lebih variabel bebas → satu variabel terikat",
    "Dependen ordinal (bertingkat)":    "Y berupa tingkatan (misal: rendah/sedang/tinggi)",
    "2 kelompok independen":            "Kelompok berbeda, misal: pria vs wanita, kelas A vs B",
    "2 kelompok berpasangan":           "Subjek yang sama diukur dua kali, misal: sebelum vs sesudah",
    "3+ kelompok independen":           "Tiga kelompok atau lebih, misal: rendah/sedang/tinggi",
    "3+ kelompok berpasangan":          "Pengukuran berulang ≥3 kali pada subjek sama",
    "1 kelompok vs nilai acuan":        "Bandingkan rata-rata/proporsi sampel dengan nilai tertentu — misal: IPK = 3.0, proporsi = 50%",
    "Eksplorasi awal":                  "Belum tahu mau analisis apa — mulai dari visualisasi",
    "Reduksi dimensi / faktor":         "Ingin menemukan faktor-faktor di balik banyak variabel",
    "Validasi instrumen / kuesioner":   "Ingin konfirmasi struktur kuesioner yang sudah ada",
    "Pengelompokan objek / segmentasi": "Ingin mengelompokkan responden/objek berdasarkan kemiripan",
    "Variabel mediator":                "M menjelaskan mengapa X mempengaruhi Y",
    "Variabel moderator":               "W mengubah seberapa kuat pengaruh X terhadap Y",
    "Mediator + Moderator":             "Model kombinasi (moderated mediation)",
    "Validitas & reliabilitas":         "Uji apakah item kuesioner valid dan konsisten",
}


# ══════════════════════════════════════════════════════════════════════════════
# RENDER UTAMA
# ══════════════════════════════════════════════════════════════════════════════

def render(ctx: dict):
    st.markdown("""
    <div class="rs-header">
        <h1>🧭 Wizard Pemilihan Analisis</h1>
        <p>Jawab 4 pertanyaan singkat — sistem akan merekomendasikan uji statistik yang tepat untuk data Anda.</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Tooltip berwarna + info box ──────────────────────────────────────────
    st.markdown("""
    <style>
    /* Tooltip hover jadi kuning */
    div[data-baseweb="tooltip"] {
        background-color: #fef9c3 !important;
        color: #854d0e !important;
        border: 1px solid #facc15 !important;
        border-radius: 8px !important;
        padding: 8px 12px !important;
        font-size: 0.85rem !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.12) !important;
        max-width: 280px !important;
    }
    /* Info box biru untuk help text */
    .rs-info-box {
        background: #eff6ff;
        border-left: 3px solid #3b82f6;
        padding: 6px 10px;
        margin-top: 4px;
        border-radius: 4px;
        font-size: 0.78rem;
        color: #1e40af;
        line-height: 1.4;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── Inisialisasi state ─────────────────────────────────────────────────────
    for key, default in [
        ("wizard_step",    1),
        ("wizard_tujuan",  None),
        ("wizard_skala",   None),
        ("wizard_konteks", None),
        ("wizard_normal",  None),
        ("wizard_sample",  None),
        ("wizard_done",    False),
    ]:
        if key not in st.session_state:
            st.session_state[key] = default

    step    = st.session_state.wizard_step
    is_done = st.session_state.wizard_done

    # ── Progress bar ───────────────────────────────────────────────────────────
    progress_pct = 100 if is_done else int((step - 1) / 4 * 100)
    st.markdown(f"""
    <div style='margin-bottom: 1.5rem;'>
        <div style='display:flex; justify-content:space-between; font-size:0.78rem;
                    color:#5f8ab5; margin-bottom:6px;'>
            <span>{'✅ Selesai' if is_done else f'Langkah {step} dari 4'}</span>
            <span>{progress_pct}%</span>
        </div>
        <div style='background:#e0eaf5; border-radius:99px; height:6px;'>
            <div style='background:{"#22c55e" if is_done else "#185FA5"}; width:{progress_pct}%;
                        height:6px; border-radius:99px; transition:width 0.4s;'></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════
    # STEP 1 — TUJUAN
    # ══════════════════════════════════════════════════════════════════════════
    if not is_done:
        # ── Render hanya langkah aktif — mencegah halaman memanjang ─────────────
        if step == 1:
            with st.container():
                st.markdown("#### Langkah 1 — Apa tujuan analisis Anda?")
                st.caption("Pilih satu yang paling mendekati")

                tujuan_cols = st.columns(2)
                for i, tujuan in enumerate(TUJUAN_OPTIONS):
                    with tujuan_cols[i % 2]:
                        is_selected = st.session_state.wizard_tujuan == tujuan
                        if st.button(
                            ("✅ " if is_selected else "") + tujuan,
                            key=f"wiz_tujuan_{i}",
                            use_container_width=True,
                        ):
                            st.session_state.wizard_tujuan  = tujuan
                            st.session_state.wizard_skala   = None
                            st.session_state.wizard_konteks = None
                            st.session_state.wizard_normal  = None
                            st.session_state.wizard_sample  = None
                            st.session_state.wizard_step    = 2
                            st.session_state.wizard_done    = False
                            st.rerun()

        elif step == 2 and st.session_state.wizard_tujuan:
            tujuan      = st.session_state.wizard_tujuan
            skala_valid = SKALA_PER_TUJUAN.get(tujuan, SKALA_OPTIONS)

            if st.button("← Ubah tujuan", key="back_to_1", type="secondary"):
                st.session_state.wizard_step = 1
                st.rerun()

            st.markdown("#### Langkah 2 — Apa skala data variabel utama Anda?")
            st.caption(f"Tujuan: **{tujuan}**")

            skala_cols = st.columns(len(skala_valid))
            for i, skala in enumerate(skala_valid):
                with skala_cols[i]:
                    is_selected = st.session_state.wizard_skala == skala
                    help_text   = SKALA_HELP.get(skala, "")
                    if st.button(
                        ("✅ " if is_selected else "") + skala,
                        key=f"wiz_skala_{i}",
                        use_container_width=True,
                        help=help_text,
                    ):
                        st.session_state.wizard_skala   = skala
                        st.session_state.wizard_konteks = None
                        st.session_state.wizard_normal  = None
                        st.session_state.wizard_sample  = None
                        st.session_state.wizard_step    = 3
                        st.session_state.wizard_done    = False
                        st.rerun()
                    if help_text:
                        st.markdown(f"<div class='rs-info-box'>💡 {help_text}</div>", unsafe_allow_html=True)

        elif step == 3 and st.session_state.wizard_tujuan and st.session_state.wizard_skala:
            tujuan          = st.session_state.wizard_tujuan
            konteks_options = KONTEKS_OPTIONS.get(tujuan, [])

            # Auto-skip jika hanya satu opsi
            if len(konteks_options) == 1 and not st.session_state.wizard_konteks:
                st.session_state.wizard_konteks = konteks_options[0]
                st.session_state.wizard_step    = 4
                st.rerun()

            if st.button("← Ubah skala data", key="back_to_2", type="secondary"):
                st.session_state.wizard_step    = 2
                st.session_state.wizard_konteks = None
                st.session_state.wizard_normal  = None
                st.session_state.wizard_sample  = None
                st.rerun()

            st.markdown("#### Langkah 3 — Sedikit info tambahan:")
            st.caption(f"{tujuan} → {st.session_state.wizard_skala}")

            for i, konteks in enumerate(konteks_options):
                is_selected = st.session_state.wizard_konteks == konteks
                help_text   = KONTEKS_HELP.get(konteks, "")
                if st.button(
                    ("✅ " if is_selected else "") + konteks,
                    key=f"wiz_konteks_{i}",
                    use_container_width=True,
                    help=help_text,
                ):
                    st.session_state.wizard_konteks = konteks
                    st.session_state.wizard_normal  = None
                    st.session_state.wizard_sample  = None
                    st.session_state.wizard_step    = 4
                    st.session_state.wizard_done    = False
                    st.rerun()
                if help_text:
                    st.markdown(f"<div class='rs-info-box'>💡 {help_text}</div>", unsafe_allow_html=True)

        elif step == 4 and st.session_state.wizard_konteks:
            if st.button("← Ubah konteks", key="back_to_3", type="secondary"):
                st.session_state.wizard_step   = 3
                st.session_state.wizard_normal = None
                st.session_state.wizard_sample = None
                st.rerun()

            st.markdown("#### Langkah 4 — Cek cepat asumsi Anda")
            st.caption("Ini membantu wizard memilih uji yang tepat")

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Apakah data berdistribusi normal?**")
                norm_opts = ["Ya", "Tidak", "Belum cek"]
                for i, opt in enumerate(norm_opts):
                    if st.button(
                        ("✅ " if st.session_state.wizard_normal == opt else "") + opt,
                        key=f"wiz_norm_{i}",
                        use_container_width=True,
                    ):
                        st.session_state.wizard_normal = opt
                        st.rerun()
            with col2:
                st.markdown("**Berapa ukuran sampel?**")
                samp_opts = ["< 30", "30-100", "> 100"]
                for i, opt in enumerate(samp_opts):
                    if st.button(
                        ("✅ " if st.session_state.wizard_sample == opt else "") + opt,
                        key=f"wiz_samp_{i}",
                        use_container_width=True,
                    ):
                        st.session_state.wizard_sample = opt
                        st.rerun()

            if st.session_state.wizard_normal and st.session_state.wizard_sample:
                if st.session_state.get('_pause_auto'):
                    st.session_state._pause_auto = False
                    st.markdown(
                        "<div style='border-top:1px solid #d0e4f7; margin:1.2rem 0 0.8rem;'></div>",
                        unsafe_allow_html=True,
                    )
                    st.warning("Silakan periksa kembali pilihan normalitas & sampel, lalu pilih ulang untuk konfirmasi.", icon="🔄")
                else:
                    # Auto-advance hemat klik — langsung tampilkan hasil
                    st.markdown(
                        "<div style='border-top:1px solid #d0e4f7; margin:1.2rem 0 0.8rem;'></div>",
                        unsafe_allow_html=True,
                    )
                    st.info("✅ Jawaban lengkap — menampilkan rekomendasi...", icon="🧭")
                    st.session_state.wizard_done = True
                    st.rerun()

        # ══════════════════════════════════════════════════════════════════════════
    # HASIL REKOMENDASI
    # ══════════════════════════════════════════════════════════════════════════
    if is_done:
        tujuan  = st.session_state.wizard_tujuan
        skala   = st.session_state.wizard_skala
        konteks = st.session_state.wizard_konteks
        normal  = st.session_state.get("wizard_normal", "-")
        sample  = st.session_state.get("wizard_sample", "-")

        lookup_key = (tujuan, skala, konteks)
        hasil      = DECISION_TREE.get(lookup_key)

        # [Fix #2] Swap ke alternatif HANYA jika uji normal_sensitive=True
        if hasil and normal == "Tidak" and hasil.get("normal_sensitive") and hasil.get("alternatif"):
            hasil = {
                **hasil,
                "uji":       hasil["alternatif"].split("(")[0].strip(),
                "deskripsi": f"Versi nonparametrik karena data tidak normal. {hasil['deskripsi']}",
                "menu_key":  hasil.get("alt_key", hasil["menu_key"]),
            }

        st.divider()

        if hasil:
            # ── Kartu rekomendasi utama ────────────────────────────────────────
            st.markdown(f"""
            <div style='background:linear-gradient(135deg,#0c2340,#185FA5);
                        border-radius:14px; padding:1.5rem 1.8rem; margin-bottom:1rem;'>
                <div style='font-size:0.72rem; font-weight:700; color:#F5C518;
                            text-transform:uppercase; letter-spacing:0.1em; margin-bottom:8px;'>
                    ✅ Rekomendasi Uji Statistik
                </div>
                <div style='font-family:"DM Serif Display",serif; font-size:1.6rem;
                            color:#ffffff; margin-bottom:8px;'>
                    {hasil["uji"]}
                </div>
                <div style='font-size:0.88rem; color:rgba(255,255,255,0.8); line-height:1.65;'>
                    {hasil["deskripsi"]}
                </div>
            </div>
            """, unsafe_allow_html=True)

            # ── Detail dalam kolom ─────────────────────────────────────────────
            col_a, col_b = st.columns(2)

            with col_a:
                st.markdown(f"""
                <div style='background:#f0f6ff; border:1px solid #d0e4f7;
                            border-radius:10px; padding:1rem 1.2rem; height:100%;'>
                    <div style='font-size:0.72rem; font-weight:700; color:#185FA5;
                                text-transform:uppercase; letter-spacing:0.08em; margin-bottom:6px;'>
                        📋 Syarat & Asumsi
                    </div>
                    <div style='font-size:0.86rem; color:#0c2340; line-height:1.6;'>
                        {hasil["syarat"]}
                    </div>
                </div>
                """, unsafe_allow_html=True)

            with col_b:
                st.markdown(f"""
                <div style='background:#faf8ff; border:1px solid #d4c5fb;
                            border-radius:10px; padding:1rem 1.2rem; height:100%;'>
                    <div style='font-size:0.72rem; font-weight:700; color:#6366f1;
                                text-transform:uppercase; letter-spacing:0.08em; margin-bottom:6px;'>
                        🔄 Alternatif (jika asumsi tidak terpenuhi)
                    </div>
                    <div style='font-size:0.86rem; color:#3730a3; line-height:1.6;'>
                        {hasil["alternatif"]}
                    </div>
                </div>
                """, unsafe_allow_html=True)

            # ── Tips + warning sampel kecil ────────────────────────────────────
            sample_warning = ""
            if sample == "< 30" and any(
                x in hasil["uji"].lower()
                for x in ["sem", "cfa", "mediasi", "moderasi", "efa"]
            ):
                sample_warning = """
                <div style='background:#fef3c7; border:1px solid #f59e0b; border-radius:8px;
                            padding:0.6rem 1rem; margin-top:0.8rem; font-size:0.82rem; color:#92400e;'>
                    <strong>⚠️ Sampel kecil:</strong> Uji ini idealnya butuh n &gt; 100.
                    Hasil bisa tidak stabil dengan n &lt; 30.
                </div>"""

            st.markdown(f"""
            <div class="rs-narasi" style='margin-top:1rem;'>
                <strong>💡 Tips:</strong> {hasil["tips"]}
            </div>
            {sample_warning}
            """, unsafe_allow_html=True)

            # ── Ringkasan pilihan user ─────────────────────────────────────────
            st.markdown(f"""
            <div style='background:#f7faff; border:1px solid #d0e4f7; border-radius:10px;
                        padding:0.8rem 1.2rem; margin-top:1rem; font-size:0.82rem; color:#5f8ab5;'>
                <strong style='color:#0c2340;'>Pilihan Anda:</strong>
                &nbsp;{tujuan} &nbsp;→&nbsp; {skala} &nbsp;→&nbsp; {konteks}
                &nbsp;|&nbsp; Normal: {normal} &nbsp;|&nbsp; n: {sample}
            </div>
            """, unsafe_allow_html=True)

            # ── Tombol navigasi ────────────────────────────────────────────────
            st.markdown("<div style='margin-top:1.5rem;'>", unsafe_allow_html=True)
            btn_col1, btn_col2 = st.columns([3, 2])

            with btn_col1:
                if st.button(
                    f"🚀  Buka Modul {hasil['uji'].split('(')[0].strip()}",
                    key="wiz_goto_main",
                    use_container_width=True,
                    type="primary",
                ):
                    st.session_state.active_menu = hasil["menu_key"]
                    _reset_wizard()
                    st.rerun()

            with btn_col2:
                if hasil.get("alt_key") and hasil["alt_key"] != hasil["menu_key"]:
                    if st.button(
                        "↗  Buka Alternatif",
                        key="wiz_goto_alt",
                        use_container_width=True,
                    ):
                        st.session_state.active_menu = hasil["alt_key"]
                        _reset_wizard()
                        st.rerun()

            # Baris kedua untuk koreksi
            btn_col3, btn_col4 = st.columns(2)
            with btn_col3:
                if st.button("↶  Ubah jawaban terakhir", key="wiz_undo", use_container_width=True, help="Kembali ke Langkah 4 untuk memperbaiki normalitas/sampel"):
                    st.session_state.wizard_done = False
                    st.session_state.wizard_step = 4
                    st.session_state._pause_auto = True
                    st.rerun()
            with btn_col4:
                if st.button("🔄  Ulangi dari awal", key="wiz_reset", use_container_width=True):
                    _reset_wizard()
                    st.rerun()

            st.markdown("</div>", unsafe_allow_html=True)

        else:
            # ── Tidak ada hasil di decision tree ──────────────────────────────
            st.warning(
                "Kombinasi pilihan ini belum ada di database wizard. "
                "Coba konsultasikan ke **🤖 Chat AI Analyst** untuk saran yang lebih spesifik.",
                icon="⚠️",
            )
            col1, col2 = st.columns(2)
            with col1:
                if st.button(
                    "💬  Tanya Chat AI",
                    key="wiz_to_chat",
                    use_container_width=True,
                    type="primary",
                ):
                    st.session_state.active_menu = "Chat AI"
                    _reset_wizard()
                    st.rerun()
            with col2:
                if st.button("🔄  Coba Lagi", key="wiz_retry", use_container_width=True):
                    _reset_wizard()
                    st.rerun()

        # ── Tabel referensi cepat ──────────────────────────────────────────────
        with st.expander("📖 Tabel Panduan Cepat Semua Uji", expanded=False):
            _render_quick_reference()


# ══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def _reset_wizard():
    """Reset semua state wizard ke kondisi awal."""
    for key in [
        "wizard_step", "wizard_tujuan", "wizard_skala",
        "wizard_konteks", "wizard_normal", "wizard_sample", "wizard_done",
    ]:
        st.session_state.pop(key, None)


def _render_quick_reference():
    """Tabel referensi singkat semua uji yang tersedia."""
    import pandas as pd

    data = [
        ("Korelasi Pearson",                "Interval/Rasio",    "Hubungan",          "Normal, linier",            "Korelasi"),
        ("Korelasi Spearman/Kendall",       "Ordinal",            "Hubungan",          "Bebas distribusi",          "Uji Nonparametrik"),
        ("Chi-Square / Uji Asosiasi",       "Nominal",            "Hubungan",          "Frekuensi harapan ≥ 5",     "Uji Nonparametrik"),
        ("Regresi Linier (OLS)",            "Interval/Rasio",    "Prediksi",          "Normal, homoskedastis",     "Regresi"),
        ("Regresi Logistik Biner",          "Nominal",            "Prediksi",          "Dependen biner",            "Regresi Logistik"),
        ("Regresi Logistik Ordinal",        "Ordinal/Nominal",    "Prediksi",          "Proportional odds",         "Regresi Logistik"),
        ("Independent t-test",              "Interval/Rasio",    "Beda 2 kelompok",   "Normal, varians homogen",   "Uji Beda"),
        ("Paired t-test",                   "Interval/Rasio",    "Beda berpasangan",  "Selisih normal",            "Uji Beda"),
        ("One-Sample t-test",               "Interval/Rasio",    "Vs nilai acuan",    "Normal",                    "Uji Beda"),
        ("Mann-Whitney U",                  "Ordinal",            "Beda 2 kelompok",   "Bebas distribusi",          "Uji Beda"),
        ("Wilcoxon Signed-Rank",            "Ordinal",            "Beda berpasangan",  "Bebas distribusi",          "Uji Nonparametrik"),
        ("McNemar Test",                    "Nominal",            "Beda berpasangan",  "Data berpasangan biner",    "Uji Nonparametrik"),
        ("Binomial / GoF Chi-Square",       "Nominal",            "Vs nilai acuan",    "Sampel independen",         "Uji Nonparametrik"),
        ("One-Way ANOVA",                   "Interval/Rasio",    "Beda 3+ kelompok",  "Normal, homogen",           "ANOVA"),
        ("Repeated Measures ANOVA",         "Interval/Rasio",    "Beda berpasangan",  "Normal, sphericity",        "ANOVA"),
        ("Kruskal-Wallis",                  "Ordinal",            "Beda 3+ kelompok",  "Bebas distribusi",          "ANOVA"),
        ("Friedman Test",                   "Ordinal",            "Beda berpasangan",  "Bebas distribusi",          "ANOVA"),
        ("EFA",                             "Interval/Rasio",    "Struktur faktor",   "KMO > 0.5",                 "EFA"),
        ("CFA",                             "Interval/Rasio",    "Validasi model",    "Hipotesis sudah ada",       "CFA"),
        ("Mediasi Bootstrap",               "Interval/Rasio",    "Peran mediator",    "Sampel ≥ 200",              "Mediasi"),
        ("Moderasi / Interaksi",            "Interval/Rasio",    "Peran moderator",   "Mean-centered",             "Moderasi"),
        ("Moderated Mediation (SEM)",       "Interval/Rasio",    "Mediator+Moderator","Sampel besar, teori kuat",  "SEM"),
        ("Analisis Klaster",                "Interval/Rasio",    "Segmentasi",        "Standardisasi diperlukan",  "Klaster"),
        ("Validitas CITC + Cronbach Alpha", "Ordinal",            "Kualitas instrumen","Min 10 responden",          "Validitas"),
    ]

    df = pd.DataFrame(data, columns=["Uji Statistik", "Skala Data", "Tujuan", "Syarat Utama", "Modul"])
    st.dataframe(df, use_container_width=True, hide_index=True)
