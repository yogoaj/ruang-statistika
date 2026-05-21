# Ruang Statistika v4.8 — AI-Powered Research & Stats Reporting

> Platform analisis statistik & pelaporan ilmiah berbasis AI | [ruang-statistika.streamlit.app](https://ruang-statistika.streamlit.app/)

---

## Daftar Isi

- [Struktur Proyek](#struktur-proyek)
- [Sistem Akses & Lisensi](#sistem-akses--lisensi)
- [Setup & Menjalankan Aplikasi](#setup--menjalankan-aplikasi)
- [Konfigurasi Supabase](#konfigurasi-supabase)
- [Konfigurasi AI Provider](#konfigurasi-ai-provider)
- [Arsitektur Modul](#arsitektur-modul)
- [Menambah Modul Baru](#menambah-modul-baru)
- [Alur Data & Export Laporan](#alur-data--export-laporan)
- [Referensi Effect Size](#referensi-effect-size)
- [Changelog](#changelog)
- [Bug yang Diperbaiki](#bug-yang-diperbaiki)

---

## Struktur Proyek

```
ruang_statistika/
│
├── app.py                            ← Entry point: routing menu, sidebar, login, CSS global
│
├── modules/
│   ├── __init__.py
│   │
│   ├── # ── FREE MODULES ─────────────────────────────────────────────────────
│   ├── upload.py                     ← Upload & Cleaning (CSV / Excel / SPSS / Stata / TXT)
│   ├── wizard.py                     ← Wizard Analisis — panduan 4 langkah pilih uji statistik
│   ├── compute.py                    ← Compute Variabel Baru (formula, recode, transform)
│   ├── eda.py                        ← Exploratory Data Analysis (distribusi, outlier, korelasi ringkas)
│   ├── deskriptif.py                 ← Statistik Deskriptif + Normalitas
│   ├── validitas.py                  ← Validitas & Reliabilitas (CITC, α-if-deleted)
│   ├── korelasi.py                   ← Korelasi Pearson + Scatter Plot
│   ├── kelompok.py                   ← Analisis Kelompok
│   ├── klaster.py                    ← Analisis Klaster (K-Means + Hierarki)
│   ├── outlier.py                    ← Deteksi Outlier (IQR / Z-Score)
│   ├── uji_asumsi.py                 ← Uji Asumsi Pra-Analisis
│   ├── uji_beda.py                   ← t-test / Mann-Whitney
│   ├── uji_nonparametrik.py          ← Wilcoxon, Friedman, McNemar, Cochran Q, Korelasi Ordinal
│   ├── power_analysis.py             ← Power Analysis & Sample Size
│   ├── chat_ai.py                    ← Chat AI Analyst
│   │
│   └── # ── FREE (terbatas) + PRO MODULES ────────────────────────────────────
│       ├── regresi.py                ← Regresi & Prediksi (OLS dasar gratis; VIF, prediksi, AI → Pro)
│       ├── anova.py                  ← ANOVA + Post-hoc (one-way + η² gratis; post-hoc, KW, AI → Pro)
│       ├── logistik.py               ← Regresi Logistik (OR + CM gratis; ROC, CR, AI → Pro)
│       │
│       ├── # ── FULL PRO ─────────────────────────────────────────────────────
│       ├── ols_plus.py               ← OLS+ Uji Asumsi Klasik ★ Pro
│       ├── ols_robust.py             ← Regresi Robust (RLM) & WLS ★ Pro
│       ├── time_series.py            ← Time Series Analysis (ARIMA/SARIMA/Auto) ★ Pro
│       ├── mediasi.py                ← Mediasi + Bootstrap CI ★ Pro
│       ├── moderasi.py               ← Moderasi/Interaksi + Johnson-Neyman ★ Pro
│       ├── efa.py                    ← Analisis Faktor Eksploratori (EFA) ★ Pro
│       ├── sem.py                    ← SEM + CFA via semopy ★ Pro
│       ├── cfa.py                    ← Confirmatory Factor Analysis Standalone ★ Pro
│       ├── reliabilitas_icc.py       ← Reliabilitas ICC (Intraclass Correlation) ★ Pro
│       ├── scraping.py               ← Web Scraping Data ★ Pro
│       └── export.py                 ← Generate Laporan (1×/sesi gratis; tak terbatas + AI → Pro)
│
├── utils/
│   ├── __init__.py
│   │
│   ├── # ── AUTH & AKSES ─────────────────────────────────────────────────────
│   ├── auth.py                       ← License key, Pro guard, tier system (starter/premium/professional), kuota
│   ├── supabase_auth.py              ← Autentikasi Supabase: Sign In/Up/Out, Forgot Password, Google OAuth
│   │
│   ├── # ── AI & STATISTIK ──────────────────────────────────────────────────
│   ├── ai_helpers.py                 ← call_ai_api, interpretasi AI per modul (Claude/GPT/Gemini/Groq/dll.)
│   ├── stats_helpers.py              ← Fungsi statistik reusable + encode_categorical
│   ├── effect_size.py                ← Cohen d, eta², f², r, OR — konsisten di seluruh modul
│   │
│   ├── # ── VISUALISASI & UI ─────────────────────────────────────────────────
│   ├── plot_helpers.py               ← Plotly chart factory (histogram, QQ, heatmap, mediasi SVG, dll.)
│   ├── styles.py                     ← CSS terpusat: inject_global_css, inject_login_css, render_hero_header, dll.
│   │
│   ├── # ── EXPORT LAPORAN ──────────────────────────────────────────────────
│   ├── docx_helpers.py               ← generate_pro_docx (router utama), generate_markdown_report
│   ├── _docx_primitives.py           ← Primitive Word: StyleProfile, _add_para, _add_heading, tabel, gambar
│   ├── _docx_narasi.py               ← Narasi fallback otomatis (tanpa AI) per modul analisis
│   ├── _docx_renderers.py            ← _render_XXX per modul → mengisi bab hasil di .docx
│   ├── _export_normalize.py          ← Normalisasi raw session_state ke format standar docx/markdown
│   ├── _export_ai_prompt.py          ← Prompt builder AI per modul untuk interpretasi laporan
│   └── _export_apa_refs.py           ← Database referensi APA 7th Edition per modul
│
├── .streamlit/
│   └── secrets.toml                  ← Kredensial Supabase & AI keys (JANGAN diupload ke GitHub!)
│
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Sistem Akses & Lisensi

### Alur Login

```
User buka app
      ↓
Halaman login (2 tab: Masuk / Daftar)
      ↓
[Masuk]           → Email + Password via Supabase Auth
                  → atau Google OAuth (Supabase provider)
[Daftar]          → Registrasi mandiri — nama, email, password
[Lupa Password?]  → Kirim link reset ke email via Supabase
[Aktivasi Pro]    → Input license key manual
[Coba Gratis]     → Masuk tanpa akun
      ↓
Login berhasil → cek tabel pro_licenses di Supabase → set role & tier
      ↓
Pro → akses semua fitur  |  Gratis → akses modul dasar + 1 laporan/sesi
```

### Tier Akses

| Tier | Keterangan |
|---|---|
| `free` | Modul dasar, 1 laporan per sesi, tanpa narasi AI |
| `starter` | Semua modul Pro, laporan tak terbatas + narasi AI |
| `premium` | Starter + fitur lanjutan (sesuai konfigurasi) |
| `professional` | Akses penuh semua fitur |

### Tampilan Menu per Status

| Kondisi | Menu | Aksi klik modul Pro |
|---|---|---|
| Free | Semua menu tampil (ikon 🔒 pada Pro) | Prompt upgrade |
| Pro (aktif) | Semua menu tampil tanpa 🔒 | Langsung masuk modul |
| Pro (expired) | Semua menu tampil (ikon 🔒 pada Pro) | Notif expired + prompt renew |

### Kuota Laporan Gratis

Pengguna Free mendapat **1 laporan per sesi** (disimpan di `st.session_state`, bukan file — aman untuk Streamlit Cloud). Pengguna Pro tidak terbatas.

### Kelola User via Supabase Dashboard

Buka [supabase.com](https://supabase.com) → project kamu → **Authentication → Users**

| Aksi | Cara |
|---|---|
| Lihat semua user | Authentication → Users |
| Hapus user | Klik nama user → Delete |
| Undang user baru | Klik "Invite user" → masukkan email |
| Reset password user | Klik nama user → Send password recovery |
| Set akses Pro | Tambahkan baris di tabel `pro_licenses` |

### Tabel `pro_licenses` di Supabase

Tambahkan user Pro dengan menyisipkan baris ke tabel `pro_licenses`:

| Kolom | Tipe | Keterangan |
|---|---|---|
| `email` | text | Email user (lowercase) |
| `name` | text | Nama tampil |
| `password` | text | Password plaintext (fallback login sebelum sign-up Supabase) |
| `license_key` | text | Kode lisensi, opsional |
| `tier` | text | `starter` / `premium` / `professional` |
| `expires_at` | timestamptz | Tanggal kedaluwarsa, `NULL` = permanen |
| `is_active` | boolean | `true` = aktif |

### Menambah License Key Manual

Edit `utils/auth.py` → bagian `LICENSE_REGISTRY`:

```python
LICENSE_REGISTRY = {
    "PRO-STAT-2026":  {"expires": "2026-12-06", "label": "Akademisi Pro 2026"},
    "MY-NEW-KEY":     {"expires": "2027-03-31", "label": "Custom Key"},  # ← tambah di sini
}
```

### Link Upgrade Paket

Semua tombol dan link "Upgrade" di dalam aplikasi mengarah ke: **[lynk.id/ruangstatistika](https://lynk.id/ruangstatistika)**

---

## Setup & Menjalankan Aplikasi

```bash
git clone <repo-url>
cd ruang_statistika
pip install -r requirements.txt
streamlit run app.py
```

### Instalasi Minimal (tanpa SEM & Scraping)

```bash
pip install streamlit supabase bcrypt pyyaml pandas numpy scipy \
            statsmodels scikit-learn plotly kaleido python-docx \
            openpyxl requests httpx tabulate pyreadstat pingouin pmdarima
```

### Prasyarat

| Komponen | Versi Minimum | Keterangan |
|---|---|---|
| Python | >= 3.10 | Diperlukan untuk type hint modern |
| `streamlit` | >= 1.35.0 | Framework UI |
| `supabase` | >= 2.0.0 | **Wajib** — sistem autentikasi |
| `kaleido` | == 0.2.1 | **Wajib** — konversi Plotly → PNG untuk embed di Word |
| `pandas` | >= 2.0.0 | Manipulasi data |
| `numpy` | >= 1.26.0 | Komputasi numerik |
| `scipy` | >= 1.11.0 | Statistik dasar |
| `statsmodels` | >= 0.14.0 | OLS, RLM, WLS, Logit, VIF, Durbin-Watson, dll. |
| `scikit-learn` | >= 1.4.0 | EFA, K-Means, Silhouette, StandardScaler |
| `pingouin` | >= 0.5.4 | ANOVA, ICC, effect size |
| `pmdarima` | >= 2.0.0 | Auto-ARIMA (Time Series) |
| `plotly` | == 5.19.0 | Visualisasi interaktif |
| `python-docx` | >= 1.1.0 | Generate laporan .docx |
| `openpyxl` | >= 3.1.0 | Export .xlsx & baca Excel |
| `bcrypt` | >= 4.0.0 | Fallback auth lokal |
| `pyyaml` | >= 6.0 | Baca users.yaml (fallback) |
| `requests` | >= 2.31.0 | HTTP ke AI provider |
| `httpx` | >= 0.27.0 | Async HTTP |
| `tabulate` | >= 0.9.0 | Markdown table rendering |
| `pyreadstat` | >= 1.2.0 | Upload SPSS (.sav) dan Stata (.dta) |
| `semopy` | >= 2.3.0 | **Opsional** — SEM & CFA |
| `beautifulsoup4` | >= 4.12.0 | **Opsional** — Web Scraping |
| `lxml` | >= 5.1.0 | **Opsional** — parser HTML/XML |

> **Catatan:** Jika `semopy` gagal install, modul SEM & CFA tidak akan berfungsi — modul lain tetap berjalan normal.
> Jika `kaleido` gagal di Linux/server, coba `pip install kaleido==0.2.1` atau `pip install kaleido --pre`.

---

## Konfigurasi Supabase

### 1. Buat Project Supabase

1. Daftar/masuk di [supabase.com](https://supabase.com)
2. Buat project baru
3. Ambil **URL** dan **anon key** dari Settings → API

### 2. Aktifkan Provider Auth

- **Email:** Authentication → Providers → Email → Enable
- **Google OAuth:** Authentication → Providers → Google → masukkan Client ID & Secret dari Google Cloud Console

### 3. Buat Tabel `pro_licenses`

Jalankan SQL berikut di Supabase SQL Editor:

```sql
create table pro_licenses (
  id          uuid default gen_random_uuid() primary key,
  email       text unique not null,
  name        text,
  password    text,
  license_key text,
  tier        text default 'starter',
  expires_at  timestamptz,
  is_active   boolean default true,
  created_at  timestamptz default now()
);
```

### 4. Buat File Secrets

Buat file `.streamlit/secrets.toml` (jangan diupload ke GitHub):

```toml
[supabase]
url      = "https://xxxxxx.supabase.co"
anon_key = "eyJhbGci..."

app_url = "https://ruang-statistika.streamlit.app"   # URL deploy kamu
```

Untuk deploy di Streamlit Community Cloud, isi secrets yang sama di **App Settings → Secrets**.

### 5. Google OAuth — Catatan Penting

Authorized Redirect URI yang harus didaftarkan di Google Cloud Console adalah URL **Supabase callback**, bukan URL aplikasi Streamlit:

```
https://xxxxxx.supabase.co/auth/v1/callback
```

Jangan isi `redirect_to` di kode — biarkan Supabase memakai callback URL default-nya. Lihat komentar di `supabase_auth.py` → `supabase_sign_in_google()` untuk penjelasan lengkap.

---

## Konfigurasi AI Provider

AI provider dikonfigurasi oleh masing-masing user dari sidebar aplikasi (input API key). Tidak ada AI key yang disimpan di server.

| Provider | Gratis? | Cara Dapat Key |
|---|---|---|
| Claude (Anthropic) | Berbayar | [console.anthropic.com](https://console.anthropic.com) |
| GPT-4o (OpenAI) | Berbayar | [platform.openai.com](https://platform.openai.com) |
| Gemini (Google) | Terbatas gratis | [aistudio.google.com](https://aistudio.google.com) |
| Groq — Llama 3.3 70B | **Gratis** | [console.groq.com](https://console.groq.com) |
| OpenRouter | **Gratis** (model tertentu) | [openrouter.ai](https://openrouter.ai) |
| HuggingFace — Mistral 7B | **Gratis** | [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) |
| Mistral AI | Trial gratis | [console.mistral.ai](https://console.mistral.ai) |
| Cohere | Trial gratis | [dashboard.cohere.com](https://dashboard.cohere.com) |

---

## Arsitektur Modul

### Struktur Standar Setiap Modul

```python
"""
modules/nama_modul.py — Deskripsi Singkat (Free / Pro)
Ruang Statistika v4.8
"""
import streamlit as st
from utils.auth import require_pro          # hanya untuk modul Pro penuh
from utils.auth import require_tier         # untuk guard berbasis tier
from utils.stats_helpers import require_data, require_cols

def render(ctx: dict):
    """
    ctx keys:
      license_info     — dict hasil validate_license()
      is_pro           — bool: apakah user Pro
      user_tier        — str: 'free' | 'starter' | 'premium' | 'professional'
      alpha_level      — float: tingkat signifikansi (default 0.05)
      r_tab            — tab aktif (jika ada multi-tab di modul)
      ai_enabled       — bool: apakah AI aktif
      anthropic_api_key — str: API key aktif
      ai_provider      — str: provider AI aktif
      user_name        — str: nama user untuk cover laporan
    """
    license_info = ctx["license_info"]
    user_name    = ctx.get("user_name", "")

    # Guard Pro penuh — HARUS di baris paling awal
    if not require_pro(license_info, "Nama Modul"):
        st.stop()

    # Guard berbasis tier (untuk modul dengan tier berbeda)
    # if not require_tier("premium", "Nama Modul"):
    #     st.stop()

    # ... logika modul ...

    # Simpan hasil ke session_state agar bisa diekspor
    st.session_state["nama_modul_result"] = { ... }
```

### Pipeline Export Laporan

```
utils/docx_helpers.py
  └── generate_pro_docx()
        ├── _export_normalize.py   → normalisasi hasil session_state
        ├── _docx_primitives.py    → primitive Word (heading, paragraf, tabel, gambar)
        ├── _docx_narasi.py        → narasi fallback otomatis per modul (tanpa AI)
        ├── _docx_renderers.py     → _render_XXX() per modul → isi bab hasil
        ├── _export_ai_prompt.py   → prompt builder AI per modul
        └── _export_apa_refs.py    → referensi APA 7th Edition
```

### Sistem Tier Guard

```python
from utils.auth import require_tier

# Minimal tier "premium"
if not require_tier("premium", "Nama Fitur"):
    st.stop()

# Urutan tier: free < starter < premium < professional
```

---

## Menambah Modul Baru

**1.** Buat `modules/nama_modul.py` dengan fungsi `render(ctx: dict)`.

**2.** Tambahkan entry di `app.py` → `MENU_GROUPS`:

```python
("key_unik", "🔢  Label Tampil", is_pro_required)
# is_pro_required: True = sembunyikan dari Free, False = tampilkan semua
```

**3.** Tambahkan routing di `app.py`:

```python
elif menu == "key_unik":
    from modules.nama_modul import render
    render(ctx)
```

**4.** Untuk modul Pro, panggil `require_pro(license_info, "Nama Modul")` di baris **pertama** `render()`.

**5.** Simpan hasil analisis ke `st.session_state` dengan key yang konsisten, lalu daftarkan di:
   - `utils/_export_normalize.py` → blok normalisasi hasil
   - `utils/_docx_renderers.py` → fungsi `_render_nama_modul()`
   - `utils/_export_narasi.py` → narasi fallback (opsional)
   - `utils/_export_apa_refs.py` → referensi APA (opsional)
   - `utils/_export_ai_prompt.py` → prompt AI (opsional)

---

## Alur Data & Export Laporan

```
upload.py               → st.session_state["df_clean"]
modul analisis          → st.session_state["regresi_result"]
                           st.session_state["anova_result"]
                           st.session_state["sem_result"]
                           ... (key per modul)
                                  ↓
export.py (trigger)
  └── docx_helpers.generate_pro_docx(user_name=...)
        ├── _export_normalize.py   → standarisasi semua hasil
        ├── _docx_renderers.py     → render tabel & grafik per bab
        ├── _docx_narasi.py        → narasi akademis otomatis
        ├── _export_ai_prompt.py   → minta interpretasi AI
        └── _export_apa_refs.py    → lampiran referensi APA
                                  ↓
                          .docx / .md siap download
```

---

## Referensi Effect Size

Diimplementasikan di `utils/effect_size.py`, konsisten di seluruh modul.

| Effect Size | Konteks | Kecil | Sedang | Besar |
|---|---|---|---|---|
| Cohen's d | Uji Beda (t-test) | < 0.20 | 0.20–0.50 | ≥ 0.80 |
| Eta² (η²) | ANOVA | < 0.01 | 0.01–0.06 | ≥ 0.14 |
| Cohen's f² | Regresi Linier | < 0.02 | 0.02–0.15 | ≥ 0.35 |
| Pearson r | Korelasi | < 0.10 | 0.30–0.49 | ≥ 0.50 |
| Odds Ratio | Regresi Logistik | < 1.5 | 1.5–2.5 | ≥ 4.0 |

*(Cohen, 1988; Hair et al., 2010)*

---

## Changelog

### v4.8 (Terkini)

- **Google OAuth diperbaiki:** `redirect_to` dihapus dari options `sign_in_with_oauth()` — sebelumnya menyebabkan error 403 karena URL Streamlit tidak cocok dengan Authorized Redirect URI yang terdaftar di Google Cloud. Supabase kini memakai Callback URL default-nya sendiri.
- **`handle_google_callback()`:** Dipanggil di awal `app.py` untuk menangkap token dari Google redirect via URL fragment → query params
- **Tier System:** `require_tier()` di `auth.py` — guard berbasis tier (starter / premium / professional)
- **Badge tier di sidebar:** Nama user + badge tier tampil di panel sidebar setelah login
- **`user_tier` di ctx:** Diteruskan ke semua modul untuk logika tier-aware
- **Quota fix:** Kuota laporan gratis dipindah dari file `.quota_cache.json` ke `st.session_state` — aman di Streamlit Community Cloud yang tidak mendukung file persisten
- **Bug fix:** Badge versi beranda diperbarui ke v4.8
- **Link upgrade:** Semua tombol upgrade mengarah ke `lynk.id/ruangstatistika`

### v4.5

- **Auth Supabase:** Login, Registrasi mandiri, Lupa Password — semua via Supabase Auth
- **`utils/supabase_auth.py`:** `supabase_sign_in`, `supabase_sign_up`, `supabase_forgot_password`, `restore_supabase_session`
- **Modal login baru:** Halaman login dengan 2 tab (Masuk / Daftar) + navigasi tombol ke Lupa Password, Aktivasi Pro, Coba Gratis
- **Session restore:** Token Supabase disimpan di `session_state`, di-restore otomatis saat refresh
- **`auth.py`:** Tambah `check_daily_export_quota()`, `get_quota_remaining()`, `consume_export_quota()`

### v4.4

- Auth berbasis akun: Login username + password via `users.yaml` + bcrypt (digantikan v4.5 dengan Supabase)
- `utils/auth.py`: Tambah `verify_user_login()`, `save_user_to_session()`, `logout_user()`, `load_users_config()`

### v4.3

- **Personalisasi:** Sapaan personal di Beranda, nama peneliti di cover laporan
- **Bugfix kritis `export.py`:** Berbagai perbaikan indentasi, duplikat key, dan quota handling

### v4.2

- **Modul baru:** `ols_robust.py`, `compute.py`, `scraping.py`, `power_analysis.py`, `time_series.py`
- **Navigasi:** Sidebar dikelompokkan per kategori
- **AI Provider:** Dukungan Groq, Gemini, OpenRouter, HuggingFace, Mistral, Cohere
- **Regresi, ANOVA, Logistik:** Tersedia gratis (terbatas); fitur lanjutan tetap Pro
- **Laporan gratis:** 1×/sesi tanpa narasi AI; Pro tak terbatas + narasi AI + grafik

### v4.1

- `validitas.py` ditingkatkan dengan Item-Total Statistics, CITC, α-if-deleted
- AI cache key konsisten di seluruh modul

### v4.0

- Arsitektur modular penuh
- EFA, OLS+, Mediasi, ANOVA, Moderasi, Logistik, SEM/CFA
- Export laporan multi-format (.docx / .md)

---

## Bug yang Diperbaiki

### v4.8 — Perbaikan dari sesi debugging terbaru

| File | Bug | Perbaikan |
|---|---|---|
| `utils/supabase_auth.py` | `save_supabase_session()` selalu set `role: "free"` — user Pro yang login via Supabase Auth/Google OAuth tidak dikenali sebagai Pro | Setelah login berhasil, fungsi sekarang query tabel `pro_licenses` untuk mendapatkan `role`, `tier`, `license_key`, dan `expires_at` yang benar |
| `utils/_docx_narasi.py` | Tidak ada satupun baris `import` — crash dengan `NameError: pd` saat narasi CFA/EFA/logistik digenerate | Tambah `import pandas as pd` dan `from utils._docx_primitives import _first_valid_df` |
| `utils/_docx_primitives.py` | Memanggil `_fallback_narasi()` tanpa mengimportnya — narasi fallback otomatis selalu gagal diam-diam | Tambah `from utils._docx_narasi import _fallback_narasi` |
| `utils/_export_ai_prompt.py` | Blok `time_series` (baris 126) menggunakan `system_prompt` yang baru didefinisikan di baris 163 — crash `NameError` untuk semua request AI time series | Pindahkan definisi `system_prompt` ke atas sebelum blok `time_series` |
| `modules/export.py` | Kunci `'power_result'` duplikat dalam satu dict — mapping pertama tertimpa diam-diam oleh Python | Hapus definisi pertama yang redundant, pertahankan `"Power Analysis & Sample Size"` |
| `utils/auth.py` | `from datetime import datetime, timezone` diimport ulang di dalam 3 fungsi berbeda meski sudah ada di top-level import | Tambah `timezone` ke top-level import, hapus 3 re-import lokal |

### v4.8 — Bug sebelumnya

| File | Bug | Perbaikan |
|---|---|---|
| `app.py` | Badge versi beranda masih v4.3 | Diperbarui ke v4.8 |
| `app.py`, `auth.py`, semua modul | Link upgrade mengarah ke `yogoaj.github.io` | Diubah ke `lynk.id/ruangstatistika` |
| `supabase_auth.py` | `redirect_to` menyebabkan Google OAuth 403 | Dihapus — Supabase pakai Callback URL default |
| `auth.py` | Kuota ditulis ke `.quota_cache.json` yang tidak persisten di Cloud | Dipindah ke `st.session_state` |
