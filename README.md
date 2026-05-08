# Ruang Statistika v4.5 — Modular Architecture

> AI-Powered Research & Stats Reporting | [ruang-statistika.streamlit.app](https://ruang-statistika.streamlit.app/)

---

## 🗂️ Struktur Proyek

```
ruang_statistika/
│
├── app.py                          ← Entry point: routing menu, sidebar, login, CSS global
│
├── modules/
│   ├── __init__.py
│   │
│   ├── # ── FREE MODULES ──
│   ├── upload.py                   ← Upload & Cleaning (CSV / Excel / SPSS / Stata / TXT)
│   ├── compute.py                  ← Compute Variabel Baru (formula, recode, transform)
│   ├── eda.py                      ← Exploratory Data Analysis (distribusi, outlier, korelasi ringkas)
│   ├── deskriptif.py               ← Statistik Deskriptif + Normalitas
│   ├── validitas.py                ← Validitas & Reliabilitas (CITC, α-if-deleted)
│   ├── korelasi.py                 ← Korelasi Pearson + Scatter Plot
│   ├── kelompok.py                 ← Analisis Kelompok
│   ├── outlier.py                  ← Deteksi Outlier (IQR / Z-Score)
│   ├── uji_asumsi.py               ← Uji Asumsi Pra-Analisis
│   ├── uji_beda.py                 ← t-test / Mann-Whitney + tab Non-Parametrik Lengkap
│   ├── uji_nonparametrik.py        ← Wilcoxon, Friedman, McNemar, Cochran Q, Korelasi Ordinal
│   ├── chat_ai.py                  ← Chat AI Analyst
│   │
│   └── # ── PRO MODULES ──
│       ├── regresi.py              ← Regresi & Prediksi ★
│       ├── ols_plus.py             ← OLS+ Uji Asumsi Klasik ★
│       ├── ols_robust.py           ← Regresi Robust (RLM) & WLS ★
│       ├── efa.py                  ← Analisis Faktor Eksploratori (EFA) ★
│       ├── cfa.py                  ← Confirmatory Factor Analysis (CFA) ★
│       ├── mediasi.py              ← Mediasi + Bootstrap CI ★
│       ├── anova.py                ← ANOVA + Post-hoc ★
│       ├── moderasi.py             ← Moderasi/Interaksi + Johnson-Neyman ★
│       ├── logistik.py             ← Regresi Logistik + ROC ★
│       ├── sem.py                  ← SEM + CFA via semopy ★
│       ├── klaster.py              ← Analisis Klaster (K-Means + Hierarki) ★
│       ├── reliabilitas_icc.py     ← Reliabilitas ICC (Intraclass Correlation) ★
│       ├── power_analysis.py       ← Power Analysis & Sample Size ★
│       ├── scraping.py             ← Web Scraping Data ★
│       └── export.py               ← Generate Laporan Pro (.docx / .md) ★
│
├── utils/
│   ├── __init__.py
│   ├── auth.py                     ← License key validation, Pro guard, quota harian gratis
│   ├── supabase_auth.py            ← Autentikasi Supabase: Sign In/Up/Forgot Password
│   ├── ai_helpers.py               ← call_ai_api, interpretasi AI per modul (Claude/GPT/Gemini/Groq)
│   ├── stats_helpers.py            ← Fungsi statistik reusable + encode_categorical
│   ├── plot_helpers.py             ← Plotly chart factory (histogram, QQ, heatmap, mediasi SVG, dll.)
│   ├── docx_helpers.py             ← generate_pro_docx (+ user_name), generate_markdown_report
│   └── effect_size.py              ← Cohen d, eta², f², r, OR — konsisten di seluruh modul
│
├── .streamlit/
│   └── secrets.toml                ← Kredensial Supabase (JANGAN diupload ke GitHub!)
│
├── .gitignore
├── requirements.txt
└── README.md
```

---

## 🔐 Sistem Akses & Lisensi

### Alur Login (v4.5)

```
User buka app
      ↓
Modal login muncul (5 tab — layout 2 kolom)
      ↓
[Masuk]         → Email + Password via Supabase
[Daftar]        → Registrasi mandiri via Supabase
[Lupa Password] → Kirim link reset ke email via Supabase
[Kode Pro]      → Aktivasi Pro langsung dengan license key (tanpa akun Supabase)
[Lanjut Gratis] → Masuk tanpa akun
      ↓
Setelah login → cek License Key di sidebar
      ↓
Pro → akses semua fitur | Gratis → akses modul dasar + 1 laporan/hari
```

### Tabel Akses

| Kondisi | Tampilan Menu | Aksi Klik |
|---|---|---|
| Free | Semua menu tampil (ikon 🔒 pada Pro) | Modul Pro → prompt upgrade |
| Pro | Semua menu tampil (tanpa 🔒) | Langsung masuk modul |
| Pro expired | Semua menu tampil (ikon 🔒 pada Pro) | Notif expired + prompt renew |

### Kuota Laporan Gratis

Pengguna Free mendapat **1 laporan per hari**. Kuota dicatat di `.quota_cache.json`.
Pengguna Pro tidak terbatas.

### Menambah License Key Baru

Edit `utils/auth.py` → bagian `LICENSE_REGISTRY`:

```python
LICENSE_REGISTRY = {
    "PRO-STAT-2026":  {"expires": "2026-12-06", "label": "Akademisi Pro 2026"},
    "MY-NEW-KEY":     {"expires": "2027-03-31", "label": "Custom Key"},  # ← tambah di sini
}
```

### Kelola User (via Supabase Dashboard)

Buka [supabase.com](https://supabase.com) → project kamu → **Authentication → Users**

| Aksi | Cara |
|---|---|
| Lihat semua user | Authentication → Users |
| Hapus user | Klik nama user → Delete |
| Undang user baru | Klik "Invite user" → masukkan email |
| Reset password user | Klik nama user → Send password recovery |
| User daftar sendiri | Klik tab "Daftar" di modal login app |

---

## 👤 Personalisasi & Login

Sejak v4.5, login menggunakan **Supabase Authentication**:

- **Tab Masuk** — email + password
- **Tab Daftar** — registrasi mandiri (nama, email, password)
- **Tab Lupa Password** — kirim link reset ke email
- **Tab Kode Pro** — aktivasi Pro langsung dengan license key
- **Tab Lanjut Gratis** — masuk tanpa akun (nama opsional)
- **Sidebar** — tampilkan nama user + tombol Keluar
- **Laporan .docx & .md** — nama peneliti otomatis di cover page

Nama pengguna disimpan di `st.session_state` dan diteruskan via `ctx["user_name"]` ke semua modul.

---

## 🏗️ Struktur Standar Setiap Modul

```python
"""
modules/nama_modul.py — Deskripsi Singkat (Free/Pro)
Ruang Statistika v4.5
"""
import streamlit as st
from utils.auth import require_pro          # hanya untuk Pro modules
from utils.stats_helpers import require_data, require_cols

def render(ctx: dict):
    # ctx keys: license_info, is_pro, alpha_level, r_tab,
    #           ai_enabled, anthropic_api_key, ai_provider, user_name

    license_info = ctx["license_info"]
    user_name    = ctx.get("user_name", "")

    # (Pro modules only) — guard check, HARUS di baris paling awal
    if not require_pro(license_info, "Nama Modul"):
        st.stop()

    # ... logika modul ...
```

---

## 📦 Menambah Modul Baru

1. Buat file `modules/nama_modul.py` dengan fungsi `render(ctx: dict)`
2. Tambahkan entry di `app.py` → `MENU_GROUPS` — setiap item adalah tuple 3 elemen:

   ```python
   ("key_unik", "🔢  Label Tampil", is_pro_required)
   # is_pro_required: True = Pro, False = Free/terbatas
   ```

3. Tambahkan routing di `app.py` → blok `elif menu == "...":`

   ```python
   elif menu == "key_unik":
       if is_pro:
           from modules.nama_modul import render
           render(ctx)
       else:
           from utils.auth import require_pro
           require_pro(license_info, "Nama Modul")
   ```

4. Untuk modul Pro, panggil `require_pro(license_info, "Nama Modul")` di baris **pertama** `render()`
5. Simpan hasil analisis ke `st.session_state` dengan key yang terdaftar di `export.py` → `collect_session_results()`

---

## ✨ Changelog

### v4.5 (Terkini)
- **Auth Supabase:** Login, Registrasi mandiri, Lupa Password — semua via Supabase Auth
- **`utils/supabase_auth.py`:** `supabase_sign_in`, `supabase_sign_up`, `supabase_forgot_password`, `restore_supabase_session`
- **Modal login baru:** 5 tab (Masuk / Daftar / Lupa Password / Kode Pro / Lanjut Gratis) dalam layout 2 kolom
- **Google OAuth dihapus:** Tidak ada lagi ketergantungan pada Google Cloud Console — setup lebih sederhana
- **Session restore:** Token Supabase disimpan di `session_state`, di-restore otomatis saat refresh
- **Bug fix `auth.py`:** Tambah `check_daily_export_quota()`, `get_quota_remaining()`, dan `consume_export_quota()` tanpa argumen wajib — diperlukan oleh `export.py`

### v4.4
- **Auth berbasis akun:** Login username + password via `users.yaml` + bcrypt (digantikan v4.5 dengan Supabase)
- **`utils/auth.py`:** Tambah `verify_user_login()`, `save_user_to_session()`, `logout_user()`, `load_users_config()`

### v4.3
- **Personalisasi:** Login berbasis nama pengguna di sidebar — sapaan personal di Beranda, nama peneliti di cover laporan
- **Bugfix kritis `export.py`:** Berbagai perbaikan indentasi, duplikat key, dan quota handling

### v4.2
- **Modul baru:** `ols_robust.py`, `compute.py`
- **Navigasi:** Sidebar dikelompokkan per kategori
- **AI Provider:** Dukungan Groq dan HuggingFace gratis

### v4.1
- `validitas.py` ditingkatkan dengan Item-Total Statistics
- AI cache key konsisten di seluruh modul

### v4.0
- Arsitektur modular penuh
- EFA, OLS+, Mediasi, ANOVA, Moderasi, Logistik, SEM/CFA
- Export laporan multi-format

---

## 🗺️ Alur Data & Export Laporan

```
upload.py            → st.session_state["df_clean"]
modul analisis       → st.session_state["regresi_result"], ["anova_result"], dst.
export.py            → collect_session_results()
                     → generate_pro_docx(user_name=...) / generate_markdown_report(user_name=...)
                     → download .docx / .md
```

---

## 🚀 Menjalankan Aplikasi

```bash
cd ruang_statistika
pip install -r requirements.txt
streamlit run app.py
```

### Setup Supabase (wajib untuk fitur login)

1. Buat project di [supabase.com](https://supabase.com)
2. Ambil **URL** dan **anon key** dari Settings → API
3. Aktifkan Email provider di Authentication → Providers
4. Buat file `.streamlit/secrets.toml`:

```toml
[supabase]
url = "https://xxxxxx.supabase.co"
anon_key = "eyJhbGci..."

app_url = "http://localhost:8501"
```

### Prasyarat

| Komponen | Versi Minimum | Catatan |
|---|---|---|
| Python | >= 3.10 | Diperlukan untuk type hint modern |
| `supabase` | >= 2.0.0 | **WAJIB** untuk sistem auth |
| `kaleido` | >= 0.2.1 | **WAJIB** untuk embed grafik ke Word |
| `bcrypt` | >= 4.0.0 | Untuk fallback auth lokal (Kode Pro) |
| `pyyaml` | >= 6.0 | Untuk baca users.yaml jika fallback |
| `semopy` | >= 2.3.0 | Opsional — SEM & CFA |
| `pyreadstat` | >= 1.2.0 | Opsional — upload SPSS/Stata |
| `beautifulsoup4` | >= 4.12.0 | Opsional — Web Scraping |
| `lxml` | >= 5.1.0 | Opsional — parser HTML |

---

## 🤖 Konfigurasi AI Provider

| Provider | Gratis? | Cara Dapat Key |
|---|---|---|
| Claude (Anthropic) | Berbayar | [console.anthropic.com](https://console.anthropic.com) |
| GPT-4o (OpenAI) | Berbayar | [platform.openai.com](https://platform.openai.com) |
| Gemini (Google) | Terbatas gratis | [aistudio.google.com](https://aistudio.google.com) |
| Groq — Llama 3.3 70B | **Gratis** | [console.groq.com](https://console.groq.com) |
| HuggingFace — Mistral 7B | **Gratis** | [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) |

---

## 📐 Referensi Effect Size (Cohen, 1988)

| Effect Size | Konteks | Kecil | Sedang | Besar |
|---|---|---|---|---|
| Cohen's d | Uji Beda (t-test) | < 0.20 | 0.20–0.50 | ≥ 0.80 |
| Eta² (η²) | ANOVA | < 0.01 | 0.01–0.06 | ≥ 0.14 |
| Cohen's f² | Regresi Linier | < 0.02 | 0.02–0.15 | ≥ 0.35 |
| Pearson r | Korelasi | < 0.10 | 0.30–0.49 | ≥ 0.50 |
| Odds Ratio | Regresi Logistik | < 1.5 | 1.5–2.5 | ≥ 4.0 |
