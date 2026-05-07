"""
modules/scraping.py — Web Scraping & Data Collector (Pro ★)
Ruang Statistika v4.2

Fitur utama:
- Scraping tabel HTML dari URL (requests + BeautifulSoup)
- Scraping multi-halaman dengan pagination otomatis
- Scraping API REST/JSON publik (GET dengan headers kustom)
- Import teks tidak terstruktur → parsing via AI (ekstrak entitas/nilai)
- Preview, cleaning awal, dan langsung masuk ke df_clean (siap analisis)
- Export CSV/Excel sebelum analisis
- Progress bar & log aktivitas per operasi
- AI: analisis kualitas data hasil scraping + rekomendasi kolom

Dependensi:
    pip install requests beautifulsoup4 lxml

Referensi legal:
- Hanya scraping halaman publik tanpa login
- Menghormati robots.txt (ditampilkan sebagai informasi, bukan block)
- Rate-limit bawaan antar request (1-3 detik)
"""

import io
import re
import time
import json
import textwrap
from urllib.parse import urljoin, urlparse, urlencode
from typing import Optional

import numpy as np
import pandas as pd
import streamlit as st
import requests

from utils.auth import require_pro
from utils.stats_helpers import ss_get
from utils.ai_helpers import call_ai_api

try:
    from bs4 import BeautifulSoup
    BS4_OK = True
except ImportError:
    BS4_OK = False


# ── Warna ────────────────────────────────────────────────────────────────────
BLUE  = "#185FA5"
GREEN = "#3B6D11"
RED   = "#A32D2D"
NAVY  = "#0c2340"

# ── Default headers ──────────────────────────────────────────────────────────
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# ── Rate limit ───────────────────────────────────────────────────────────────
MIN_DELAY = 1.0   # detik antar request (etika scraping)
MAX_PAGES = 20    # batas halaman pagination


# =============================================================================
# Entry point
# =============================================================================

def render(ctx: dict):
    license_info = ctx["license_info"]
    ai_enabled   = ctx["ai_enabled"]
    api_key      = ctx["anthropic_api_key"]
    ai_provider  = ctx["ai_provider"]

    st.markdown(
        '<p class="rs-section-title">🕸️ Web Scraping & Data Collector</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="rs-section-sub">'
        "Ambil data dari website, tabel HTML, atau API REST publik — "
        "langsung siap dianalisis tanpa upload manual."
        "</p>",
        unsafe_allow_html=True,
    )

    if not require_pro(license_info, "Web Scraping & Data Collector"):
        st.stop()

    if not BS4_OK:
        st.error("❌ Library **beautifulsoup4** belum terinstall.")
        st.code("pip install requests beautifulsoup4 lxml", language="bash")
        st.stop()

    # Inisialisasi state
    if "ai_cache" not in st.session_state:
        st.session_state.ai_cache = {}
    if "scraping_log" not in st.session_state:
        st.session_state.scraping_log = []

    # ── Tab navigasi ─────────────────────────────────────────────────────────
    tab_html, tab_multi, tab_api, tab_text, tab_hasil = st.tabs([
        "🌐 Tabel HTML",
        "📑 Multi-Halaman",
        "🔌 API / JSON",
        "📝 Teks → AI Parse",
        "📊 Hasil & Export",
    ])

    with tab_html:
        _tab_html_table(ai_enabled, api_key, ai_provider)

    with tab_multi:
        _tab_multi_page(ai_enabled, api_key, ai_provider)

    with tab_api:
        _tab_api_json(ai_enabled, api_key, ai_provider)

    with tab_text:
        _tab_text_parse(ai_enabled, api_key, ai_provider)

    with tab_hasil:
        _tab_hasil(ai_enabled, api_key, ai_provider)


# =============================================================================
# TAB 1 — Scraping Tabel HTML
# =============================================================================

def _tab_html_table(ai_enabled, api_key, ai_provider):
    st.markdown("### 🌐 Scraping Tabel HTML dari URL")
    st.markdown(
        '<div class="rs-narasi">'
        "Mengambil semua tabel <code>&lt;table&gt;</code> dari halaman web publik. "
        "Cocok untuk: Wikipedia, BPS, Bank Indonesia, tabel statistik pemerintah, "
        "data keuangan terbuka, dan sejenisnya."
        "</div>",
        unsafe_allow_html=True,
    )

    url = st.text_input(
        "URL Halaman:",
        placeholder="https://id.wikipedia.org/wiki/Daftar_...",
        key="scrape_html_url",
    )

    col_a, col_b = st.columns(2)
    with col_a:
        table_idx = st.number_input(
            "Indeks Tabel (0 = pertama):",
            min_value=0, max_value=50, value=0,
            help="Jika halaman memiliki beberapa tabel, pilih indeksnya.",
            key="scrape_html_idx",
        )
    with col_b:
        req_timeout = st.number_input(
            "Timeout (detik):", min_value=5, max_value=60, value=15,
            key="scrape_html_timeout",
        )

    with st.expander("⚙️ Header Kustom (opsional)"):
        custom_cookie = st.text_input("Cookie:", placeholder="session=abc123", key="scrape_html_cookie")
        custom_referer = st.text_input("Referer:", placeholder="https://example.com", key="scrape_html_ref")

    if st.button("▶ Ambil Tabel", type="primary", key="btn_html"):
        if not url.strip():
            st.warning("⚠️ Masukkan URL terlebih dahulu.")
            return

        headers = DEFAULT_HEADERS.copy()
        if custom_cookie:
            headers["Cookie"] = custom_cookie
        if custom_referer:
            headers["Referer"] = custom_referer

        with st.spinner(f"🌐 Mengambil {url} …"):
            df, msg, all_tables = _fetch_html_table(
                url.strip(), int(table_idx), headers, int(req_timeout)
            )

        _log(f"HTML Table | URL={url} | idx={table_idx} | status={msg}")

        if df is not None:
            st.success(f"✅ {msg}")
            if all_tables > 1:
                st.info(f"💡 Halaman memiliki **{all_tables}** tabel. Anda mengambil indeks {table_idx}.")
            _preview_and_save(df, source_label=f"HTML:{url[:60]}", key_suffix="html")
        else:
            st.error(f"❌ {msg}")
            _show_robots_tip(url)


# =============================================================================
# TAB 2 — Multi-Halaman (Pagination)
# =============================================================================

def _tab_multi_page(ai_enabled, api_key, ai_provider):
    st.markdown("### 📑 Scraping Multi-Halaman (Pagination)")
    st.markdown(
        '<div class="rs-narasi">'
        "Otomatis mengikuti pagination URL dengan pola <code>?page=N</code>, "
        "<code>&p=N</code>, atau offset. Cocok untuk katalog, daftar harga, "
        "direktori, dan tabel multi-page."
        "</div>",
        unsafe_allow_html=True,
    )

    url_template = st.text_input(
        "URL Template (gunakan {page} sebagai placeholder):",
        placeholder="https://example.com/data?page={page}",
        help="Contoh: https://bps.go.id/tabel?page={page}",
        key="scrape_mp_url",
    )

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        start_page = st.number_input("Halaman Awal:", min_value=0, max_value=100, value=1, key="mp_start")
    with col_b:
        end_page   = st.number_input("Halaman Akhir:", min_value=1, max_value=MAX_PAGES, value=5, key="mp_end")
    with col_c:
        table_idx  = st.number_input("Indeks Tabel:", min_value=0, max_value=20, value=0, key="mp_tidx")

    delay = st.slider(
        "Jeda antar request (detik):", min_value=1.0, max_value=5.0, value=2.0, step=0.5,
        help="Delay lebih lama = lebih etis & kecil kemungkinan di-block.",
        key="mp_delay",
    )

    if st.button("▶ Mulai Scraping Multi-Halaman", type="primary", key="btn_mp"):
        if not url_template.strip() or "{page}" not in url_template:
            st.warning("⚠️ URL harus mengandung placeholder `{page}`.")
            return

        total_pages = int(end_page) - int(start_page) + 1
        if total_pages > MAX_PAGES:
            st.error(f"❌ Maksimum {MAX_PAGES} halaman per operasi.")
            return

        all_dfs = []
        errors  = []
        prog    = st.progress(0, text="Memulai…")
        log_ph  = st.empty()

        for i, page_num in enumerate(range(int(start_page), int(end_page) + 1)):
            url = url_template.replace("{page}", str(page_num))
            prog.progress((i + 1) / total_pages, text=f"Halaman {page_num} / {int(end_page)}")
            log_ph.caption(f"📥 Mengambil: {url}")

            df, msg, _ = _fetch_html_table(url, int(table_idx), DEFAULT_HEADERS, 15)
            if df is not None and not df.empty:
                df["_page"] = page_num
                all_dfs.append(df)
                _log(f"MultiPage | page={page_num} | rows={len(df)}")
            else:
                errors.append(f"Halaman {page_num}: {msg}")
                _log(f"MultiPage | page={page_num} | ERROR={msg}")

            if i < total_pages - 1:
                time.sleep(float(delay))

        prog.empty()
        log_ph.empty()

        if all_dfs:
            combined = pd.concat(all_dfs, ignore_index=True)
            st.success(
                f"✅ Berhasil: {len(all_dfs)}/{total_pages} halaman | "
                f"{len(combined):,} baris total"
            )
            if errors:
                with st.expander(f"⚠️ {len(errors)} halaman gagal"):
                    for e in errors:
                        st.caption(e)
            _preview_and_save(combined, source_label="MultiPage", key_suffix="mp")
        else:
            st.error("❌ Tidak ada data berhasil diambil.")
            for e in errors:
                st.caption(e)


# =============================================================================
# TAB 3 — API / JSON
# =============================================================================

def _tab_api_json(ai_enabled, api_key, ai_provider):
    st.markdown("### 🔌 Scraping API REST / JSON")
    st.markdown(
        '<div class="rs-narasi">'
        "Ambil data dari endpoint API publik yang mengembalikan JSON. "
        "Mendukung GET dengan query params dan header Authorization. "
        "Cocok untuk: API BPS, OpenWeather, GitHub, Yahoo Finance, dsb."
        "</div>",
        unsafe_allow_html=True,
    )

    api_url = st.text_input(
        "Endpoint URL:",
        placeholder="https://api.example.com/v1/data",
        key="scrape_api_url",
    )

    col_a, col_b = st.columns(2)
    with col_a:
        api_key_input = st.text_input(
            "API Key / Token (opsional):",
            type="password",
            placeholder="Bearer token atau API key",
            key="scrape_api_key_val",
        )
        auth_type = st.selectbox(
            "Tipe Auth:", ["Tidak Ada", "Bearer Token", "API-Key Header", "Basic Auth"],
            key="scrape_api_auth",
        )
    with col_b:
        query_params_raw = st.text_area(
            "Query Parameters (format key=value, satu per baris):",
            placeholder="domain=7215\ntahun=2023",
            height=100,
            key="scrape_api_params",
        )

    json_path = st.text_input(
        "Path ke array data (dot-notation, kosongkan jika root array):",
        placeholder="data.records  atau  results.list",
        help="Contoh: jika JSON = {\"data\": {\"records\": [...]}}, isi: data.records",
        key="scrape_api_path",
    )

    col_h1, col_h2 = st.columns(2)
    with col_h1:
        extra_header_key = st.text_input("Header tambahan (key):", placeholder="X-Custom-Header", key="api_hk")
    with col_h2:
        extra_header_val = st.text_input("Header tambahan (value):", placeholder="value", key="api_hv")

    if st.button("▶ Fetch API", type="primary", key="btn_api"):
        if not api_url.strip():
            st.warning("⚠️ Masukkan URL endpoint.")
            return

        # Bangun headers
        headers = {"Accept": "application/json", "User-Agent": DEFAULT_HEADERS["User-Agent"]}
        if api_key_input.strip():
            if auth_type == "Bearer Token":
                headers["Authorization"] = f"Bearer {api_key_input.strip()}"
            elif auth_type == "API-Key Header":
                headers["X-Api-Key"] = api_key_input.strip()
            elif auth_type == "Basic Auth":
                import base64
                headers["Authorization"] = "Basic " + base64.b64encode(
                    api_key_input.strip().encode()
                ).decode()
        if extra_header_key.strip():
            headers[extra_header_key.strip()] = extra_header_val.strip()

        # Bangun query params
        params = {}
        for line in query_params_raw.strip().splitlines():
            if "=" in line:
                k, _, v = line.partition("=")
                params[k.strip()] = v.strip()

        with st.spinner("🔌 Menghubungi API…"):
            df, msg = _fetch_api_json(api_url.strip(), headers, params, json_path.strip())

        _log(f"API JSON | URL={api_url} | status={msg}")

        if df is not None:
            st.success(f"✅ {msg}")
            _preview_and_save(df, source_label=f"API:{api_url[:60]}", key_suffix="api")
        else:
            st.error(f"❌ {msg}")

            # Tampilkan raw JSON untuk debug
            with st.expander("🔍 Debug: Raw Response"):
                try:
                    resp = requests.get(api_url.strip(), headers=headers,
                                        params=params, timeout=15)
                    st.code(resp.text[:3000], language="json")
                except Exception as e:
                    st.caption(str(e))


# =============================================================================
# TAB 4 — Teks Tidak Terstruktur → AI Parse
# =============================================================================

def _tab_text_parse(ai_enabled, api_key, ai_provider):
    st.markdown("### 📝 Teks Tidak Terstruktur → Tabel via AI")
    st.markdown(
        '<div class="rs-narasi">'
        "Paste teks mentah (berita, laporan, tabel teks, halaman web copy-paste) "
        "dan AI akan mengekstrak data terstruktur menjadi DataFrame. "
        "Memerlukan API Key aktif."
        "</div>",
        unsafe_allow_html=True,
    )

    if not ai_enabled:
        st.error("🔒 Fitur ini memerlukan **API Key** aktif di sidebar.")
        return

    raw_text = st.text_area(
        "Paste teks di sini:",
        height=220,
        placeholder=(
            "Contoh:\n"
            "PT Astra International: Revenue Q1 Rp 89,2 T, Laba Bersih Rp 8,1 T, "
            "EPS Rp 200\n"
            "PT Unilever: Revenue Q1 Rp 11,5 T, Laba Bersih Rp 1,2 T, EPS Rp 158\n"
            "..."
        ),
        key="scrape_text_raw",
    )

    col_a, col_b = st.columns(2)
    with col_a:
        extraction_goal = st.text_input(
            "Apa yang ingin diekstrak?",
            placeholder="Nama perusahaan, revenue, laba bersih, EPS",
            key="scrape_text_goal",
        )
    with col_b:
        output_format = st.selectbox(
            "Format output:", ["Baris per entitas", "Baris per observasi-waktu"],
            key="scrape_text_fmt",
        )

    if st.button("🤖 Ekstrak Data dengan AI", type="primary", key="btn_text_parse"):
        if not raw_text.strip():
            st.warning("⚠️ Teks tidak boleh kosong.")
            return
        if not extraction_goal.strip():
            st.warning("⚠️ Tentukan apa yang ingin diekstrak.")
            return

        prompt = _build_extract_prompt(raw_text, extraction_goal, output_format)

        with st.spinner("🤖 AI mengekstrak data…"):
            ai_response = call_ai_api(prompt, api_key=api_key, provider=ai_provider)

        df, parse_msg = _parse_ai_table_response(ai_response)
        _log(f"AI Parse | goal={extraction_goal} | status={parse_msg}")

        if df is not None and not df.empty:
            st.success(f"✅ {parse_msg}")
            with st.expander("📋 Raw AI Response"):
                st.markdown(ai_response)
            _preview_and_save(df, source_label="AI-Parse", key_suffix="text")
        else:
            st.error(f"❌ Gagal parse tabel: {parse_msg}")
            st.markdown("**Raw AI Response:**")
            st.markdown(ai_response)


# =============================================================================
# TAB 5 — Hasil & Export
# =============================================================================

def _tab_hasil(ai_enabled, api_key, ai_provider):
    st.markdown("### 📊 Hasil Scraping & Kirim ke Analisis")

    scrape_result = ss_get("scraping_result")

    if scrape_result is None:
        st.info("Belum ada data hasil scraping. Gunakan salah satu tab di atas.")
        _show_scraping_log()
        return

    df       = scrape_result["df"]
    source   = scrape_result.get("source", "unknown")
    scraped_at = scrape_result.get("scraped_at", "")

    st.markdown(
        f'<div class="rs-narasi">'
        f"📦 <b>Sumber:</b> {source}<br/>"
        f"⏱️ <b>Waktu:</b> {scraped_at}<br/>"
        f"📐 <b>Ukuran:</b> {len(df):,} baris × {len(df.columns)} kolom"
        f"</div>",
        unsafe_allow_html=True,
    )

    # ── Preview ───────────────────────────────────────────────────────────────
    st.markdown("#### Preview Data")
    st.dataframe(df.head(50), use_container_width=True)

    # ── Profil kualitas data ──────────────────────────────────────────────────
    st.markdown("#### Profil Kualitas Data")
    _show_quality_profile(df)

    # ── Cleaning otomatis ─────────────────────────────────────────────────────
    st.markdown("#### ⚙️ Cleaning Otomatis")
    col_c1, col_c2, col_c3 = st.columns(3)
    with col_c1:
        do_strip    = st.checkbox("Strip whitespace kolom teks", value=True, key="cl_strip")
    with col_c2:
        do_numeric  = st.checkbox("Konversi kolom angka otomatis", value=True, key="cl_num")
    with col_c3:
        do_dedup    = st.checkbox("Hapus duplikat", value=True, key="cl_dup")

    col_d1, col_d2 = st.columns(2)
    with col_d1:
        drop_thresh = st.slider(
            "Hapus kolom dengan missing > (%):", 0, 100, 80, 5,
            key="cl_miss",
        )
    with col_d2:
        rename_cols = st.checkbox("Rename kolom: lowercase + underscore", value=False, key="cl_rename")

    if st.button("🧹 Terapkan Cleaning", key="btn_clean"):
        df_clean, clean_log = _auto_clean(
            df,
            strip_text=do_strip,
            to_numeric=do_numeric,
            dedup=do_dedup,
            drop_missing_pct=drop_thresh / 100,
            rename=rename_cols,
        )
        scrape_result["df_clean"] = df_clean
        scrape_result["clean_log"] = clean_log
        st.session_state["scraping_result"] = scrape_result
        st.success(f"✅ Cleaning selesai: {len(df_clean):,} baris × {len(df_clean.columns)} kolom")
        for entry in clean_log:
            st.caption(f"• {entry}")

    # Pilih df untuk dikirim (df_clean jika ada, df jika belum)
    df_send = scrape_result.get("df_clean", df)

    # ── Export ────────────────────────────────────────────────────────────────
    st.markdown("#### ⬇️ Export")
    col_e1, col_e2 = st.columns(2)
    with col_e1:
        csv_buf = io.StringIO()
        df_send.to_csv(csv_buf, index=False)
        st.download_button(
            "📥 Download CSV",
            data=csv_buf.getvalue(),
            file_name="scraping_result.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with col_e2:
        xlsx_buf = io.BytesIO()
        with pd.ExcelWriter(xlsx_buf, engine="openpyxl") as writer:
            df_send.to_excel(writer, index=False, sheet_name="Scraping_Result")
        xlsx_buf.seek(0)
        st.download_button(
            "📥 Download Excel",
            data=xlsx_buf,
            file_name="scraping_result.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    # ── Kirim ke df_clean ─────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 🚀 Kirim ke Analisis")
    st.info(
        "Klik tombol di bawah untuk menjadikan data ini sebagai "
        "dataset aktif (`df_clean`) yang siap dianalisis oleh semua modul lain."
    )

    col_s1, col_s2 = st.columns([2, 1])
    with col_s1:
        dataset_name = st.text_input(
            "Nama dataset (untuk laporan):",
            value=f"Scraping — {source[:40]}",
            key="scrape_ds_name",
        )
    with col_s2:
        st.markdown("<br/>", unsafe_allow_html=True)
        if st.button("✅ Kirim ke df_clean", type="primary", use_container_width=True):
            st.session_state["df_clean"]      = df_send.copy()
            st.session_state["selected_cols"] = [
                c for c in df_send.columns
                if pd.api.types.is_numeric_dtype(df_send[c])
            ]
            st.session_state["report"] = {
                "filename": dataset_name,
                "n_rows":   len(df_send),
                "n_cols":   len(df_send.columns),
                "source":   "scraping",
            }
            st.session_state["scraping_result"]["sent_to_analysis"] = True
            st.success(
                f"✅ Dataset '{dataset_name}' ({len(df_send):,} baris × "
                f"{len(df_send.columns)} kolom) berhasil dikirim ke df_clean! "
                "Navigasi ke modul analisis via sidebar."
            )
            st.balloons()

    # ── AI Quality Review ─────────────────────────────────────────────────────
    st.markdown("---")
    if ai_enabled:
        if st.button("🤖 Review Kualitas Data dengan AI", key="ai_scrape_review"):
            prompt = _build_quality_prompt(df_send, source)
            with st.spinner("🤖 AI menganalisis kualitas data…"):
                ai_review = call_ai_api(prompt, api_key=api_key, provider=ai_provider)
            st.session_state.ai_cache["scraping"] = ai_review

        if ss_get("ai_cache", {}).get("scraping"):
            st.markdown(
                f'<div class="rs-ai-narasi">'
                f'<span class="rs-ai-badge">✨ AI — {ai_provider.split("(")[0].strip()}</span><br/>'
                f'{ss_get("ai_cache", {})["scraping"].replace(chr(10), "<br/>")}'
                f"</div>",
                unsafe_allow_html=True,
            )
    else:
        st.caption("💡 Aktifkan API Key di sidebar untuk review kualitas data dengan AI.")

    # ── Simpan ke session_state export ───────────────────────────────────────
    _save_scraping_session(df_send, source)

    # ── Log ───────────────────────────────────────────────────────────────────
    _show_scraping_log()


# =============================================================================
# Engine Functions
# =============================================================================

def _fetch_html_table(
    url: str,
    table_idx: int,
    headers: dict,
    timeout: int,
) -> tuple[Optional[pd.DataFrame], str, int]:
    """Fetch tabel HTML dari URL. Returns (df, message, n_tables)."""
    try:
        resp = requests.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()
    except requests.exceptions.Timeout:
        return None, f"Timeout ({timeout}s) — coba tambah timeout atau cek koneksi.", 0
    except requests.exceptions.HTTPError as e:
        return None, f"HTTP Error: {e}", 0
    except requests.exceptions.ConnectionError:
        return None, "Koneksi gagal — periksa URL dan koneksi internet.", 0
    except Exception as e:
        return None, f"Error: {e}", 0

    soup = BeautifulSoup(resp.text, "lxml")
    tables = soup.find_all("table")
    n_tables = len(tables)

    if n_tables == 0:
        return None, "Tidak ditemukan tag <table> di halaman ini.", 0

    if table_idx >= n_tables:
        return None, (
            f"Indeks {table_idx} di luar jangkauan — "
            f"halaman hanya punya {n_tables} tabel (indeks 0–{n_tables-1})."
        ), n_tables

    try:
        # Gunakan pd.read_html pada tabel yang dipilih
        dfs = pd.read_html(str(tables[table_idx]), flavor="lxml")
        if not dfs:
            return None, "Tabel ditemukan tapi tidak bisa di-parse.", n_tables
        df = dfs[0]
        df = _basic_clean(df)
        return df, f"{len(df):,} baris × {len(df.columns)} kolom berhasil diambil.", n_tables
    except Exception as e:
        # Fallback: parse manual dari BeautifulSoup
        try:
            df = _bs4_parse_table(tables[table_idx])
            if df is not None:
                return df, f"{len(df):,} baris diambil (mode fallback).", n_tables
        except Exception:
            pass
        return None, f"Parse error: {e}", n_tables


def _bs4_parse_table(table_tag) -> Optional[pd.DataFrame]:
    """Parse <table> manual via BeautifulSoup jika pd.read_html gagal."""
    rows = table_tag.find_all("tr")
    if not rows:
        return None
    data = []
    for row in rows:
        cells = row.find_all(["td", "th"])
        data.append([c.get_text(strip=True) for c in cells])
    if not data:
        return None
    max_cols = max(len(r) for r in data)
    data = [r + [""] * (max_cols - len(r)) for r in data]
    df = pd.DataFrame(data[1:], columns=data[0])
    return df


def _fetch_api_json(
    url: str,
    headers: dict,
    params: dict,
    json_path: str,
) -> tuple[Optional[pd.DataFrame], str]:
    """Fetch JSON dari API dan konversi ke DataFrame."""
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.Timeout:
        return None, "Timeout — API tidak merespons dalam 20 detik."
    except requests.exceptions.HTTPError as e:
        return None, f"HTTP {resp.status_code}: {e}"
    except requests.exceptions.JSONDecodeError:
        return None, "Response bukan JSON valid. Cek URL dan pastikan endpoint mengembalikan JSON."
    except Exception as e:
        return None, f"Error: {e}"

    # Navigasi json_path
    if json_path.strip():
        try:
            for key in json_path.strip().split("."):
                data = data[key]
        except (KeyError, TypeError) as e:
            return None, f"Path '{json_path}' tidak ditemukan di response: {e}"

    # Konversi ke DataFrame
    try:
        if isinstance(data, list):
            if len(data) == 0:
                return None, "Response array kosong."
            # Jika list of dict
            if isinstance(data[0], dict):
                df = pd.DataFrame(data)
            else:
                df = pd.DataFrame({"value": data})
        elif isinstance(data, dict):
            # Coba flatten satu level
            df = pd.DataFrame([data])
        else:
            return None, f"Tipe data tidak dikenali: {type(data)}"

        df = _basic_clean(df)
        return df, f"{len(df):,} baris × {len(df.columns)} kolom dari API."
    except Exception as e:
        return None, f"Gagal konversi ke DataFrame: {e}"


def _build_extract_prompt(raw_text: str, goal: str, output_format: str) -> str:
    """Bangun prompt untuk AI text → table extraction."""
    return textwrap.dedent(f"""
        Anda adalah data extraction expert. Tugas Anda: ekstrak data terstruktur
        dari teks berikut dan kembalikan HANYA dalam format CSV (comma-separated).

        TARGET EKSTRAKSI: {goal}
        FORMAT OUTPUT: {output_format}

        ATURAN KETAT:
        1. Baris pertama HARUS header kolom
        2. Gunakan koma (,) sebagai separator
        3. Jika nilai mengandung koma, bungkus dengan tanda kutip ganda
        4. JANGAN tulis penjelasan apapun — HANYA CSV murni
        5. Bersihkan simbol mata uang, pisahkan angka dari satuan
        6. Gunakan titik (.) sebagai desimal, bukan koma

        TEKS INPUT:
        ---
        {raw_text[:4000]}
        ---

        OUTPUT CSV:
    """).strip()


def _parse_ai_table_response(ai_response: str) -> tuple[Optional[pd.DataFrame], str]:
    """Parse respons AI berformat CSV menjadi DataFrame."""
    # Bersihkan markdown code block jika ada
    text = re.sub(r"```(?:csv|python|text)?\n?", "", ai_response)
    text = text.replace("```", "").strip()

    # Ambil baris yang terlihat seperti CSV (ada koma)
    lines = [l for l in text.splitlines() if l.strip() and "," in l]
    if len(lines) < 2:
        return None, "AI tidak menghasilkan format CSV yang valid (kurang dari 2 baris)."

    try:
        df = pd.read_csv(io.StringIO("\n".join(lines)))
        df = _basic_clean(df)
        return df, f"{len(df):,} baris × {len(df.columns)} kolom berhasil diekstrak."
    except Exception as e:
        return None, f"Parse CSV gagal: {e}"


def _build_quality_prompt(df: pd.DataFrame, source: str) -> str:
    """Prompt AI untuk review kualitas data scraping."""
    profile = {
        "n_rows": len(df),
        "n_cols": len(df.columns),
        "dtypes": df.dtypes.astype(str).to_dict(),
        "missing": df.isnull().sum().to_dict(),
        "sample": df.head(5).to_dict(orient="records"),
        "nunique": df.nunique().to_dict(),
    }
    return textwrap.dedent(f"""
        Anda adalah Data Quality Analyst. Evaluasi kualitas dataset hasil web scraping
        dari sumber: {source}

        PROFIL DATASET:
        {json.dumps(profile, ensure_ascii=False, indent=2, default=str)[:3000]}

        Tulis evaluasi dalam Bahasa Indonesia akademis, 3 paragraf singkat:
        1. Kelengkapan & struktur data (missing values, tipe kolom, anomali)
        2. Potensi masalah kualitas (duplikat, format tidak konsisten, outlier potensial)
        3. Rekomendasi kolom untuk analisis dan metode statistik yang sesuai
    """).strip()


# =============================================================================
# Cleaning & Profiling
# =============================================================================

def _basic_clean(df: pd.DataFrame) -> pd.DataFrame:
    """Cleaning minimal: strip header, drop kolom Unnamed."""
    # Bersihkan nama kolom
    df.columns = [
        str(c).strip().replace("\n", " ").replace("\r", "")
        for c in df.columns
    ]
    # Drop kolom Unnamed
    df = df.loc[:, ~df.columns.str.match(r"^Unnamed")]
    # Drop baris yang semua kosong
    df = df.dropna(how="all").reset_index(drop=True)
    return df


def _auto_clean(
    df: pd.DataFrame,
    strip_text: bool = True,
    to_numeric: bool = True,
    dedup: bool = True,
    drop_missing_pct: float = 0.80,
    rename: bool = False,
) -> tuple[pd.DataFrame, list]:
    """Cleaning otomatis dengan log aktivitas."""
    df = df.copy()
    log = []

    n_orig = len(df)

    # 1. Hapus kolom missing tinggi
    if drop_missing_pct < 1.0:
        miss_ratio = df.isnull().mean()
        cols_drop = miss_ratio[miss_ratio > drop_missing_pct].index.tolist()
        if cols_drop:
            df = df.drop(columns=cols_drop)
            log.append(f"Hapus {len(cols_drop)} kolom (missing > {int(drop_missing_pct*100)}%): {cols_drop}")

    # 2. Strip whitespace kolom teks
    if strip_text:
        obj_cols = df.select_dtypes(include="object").columns
        for c in obj_cols:
            df[c] = df[c].str.strip()
        if len(obj_cols):
            log.append(f"Strip whitespace pada {len(obj_cols)} kolom teks.")

    # 3. Konversi kolom numerik
    if to_numeric:
        converted = []
        for c in df.select_dtypes(include="object").columns:
            # Bersihkan format angka umum: Rp, %, titik ribuan, koma desimal
            cleaned = (
                df[c]
                .str.replace(r"[Rp\$€£¥,%]", "", regex=True)
                .str.replace(r"\.", "", regex=True)   # ribuan titik
                .str.replace(",", ".", regex=False)    # desimal koma → titik
                .str.strip()
            )
            numeric_try = pd.to_numeric(cleaned, errors="coerce")
            ratio = numeric_try.notna().mean()
            if ratio >= 0.70:  # ≥70% bisa jadi angka → konversi
                df[c] = numeric_try
                converted.append(c)
        if converted:
            log.append(f"Konversi ke numerik ({len(converted)} kolom): {converted}")

    # 4. Hapus duplikat
    if dedup:
        n_before = len(df)
        df = df.drop_duplicates().reset_index(drop=True)
        n_dup = n_before - len(df)
        if n_dup > 0:
            log.append(f"Hapus {n_dup} baris duplikat.")

    # 5. Rename kolom
    if rename:
        df.columns = [
            re.sub(r"\s+", "_", str(c).lower().strip())
            for c in df.columns
        ]
        log.append("Rename kolom: lowercase + underscore.")

    total_removed = n_orig - len(df)
    if total_removed > 0:
        log.append(f"Total baris dihapus: {total_removed} (sisa: {len(df):,} baris).")

    return df, log


def _show_quality_profile(df: pd.DataFrame):
    """Tampilkan profil kualitas data ringkas."""
    n_total_cells = len(df) * len(df.columns)
    n_miss = int(df.isnull().sum().sum())
    n_dup  = int(df.duplicated().sum())
    n_num  = len(df.select_dtypes(include="number").columns)
    n_obj  = len(df.select_dtypes(include="object").columns)

    m1, m2, m3, m4, m5 = st.columns(5)
    for col, lbl, val, sub_color in [
        (m1, "Baris",        f"{len(df):,}",   BLUE),
        (m2, "Kolom",        str(len(df.columns)), BLUE),
        (m3, "Missing",      f"{n_miss:,}",    RED if n_miss > 0 else GREEN),
        (m4, "Duplikat",     f"{n_dup:,}",     RED if n_dup > 0 else GREEN),
        (m5, "Numerik/Teks", f"{n_num}/{n_obj}", BLUE),
    ]:
        col.markdown(
            f'<div class="rs-metric">'
            f'<div class="rs-metric-label">{lbl}</div>'
            f'<div class="rs-metric-value" style="color:{sub_color};font-size:1.4rem">{val}</div>'
            f"</div>",
            unsafe_allow_html=True,
        )

    # Missing per kolom
    miss_series = df.isnull().sum()
    miss_series = miss_series[miss_series > 0].sort_values(ascending=False)
    if not miss_series.empty:
        with st.expander(f"⚠️ Missing values detail ({len(miss_series)} kolom)"):
            miss_df = pd.DataFrame({
                "Kolom":   miss_series.index,
                "Missing": miss_series.values,
                "%":       (miss_series.values / len(df) * 100).round(1),
            })
            st.dataframe(miss_df, use_container_width=True, hide_index=True)

    # Tipe data
    with st.expander("📋 Tipe Data per Kolom"):
        dtype_df = pd.DataFrame({
            "Kolom":    df.columns,
            "Tipe":     [str(df[c].dtype) for c in df.columns],
            "Non-Null": [int(df[c].notna().sum()) for c in df.columns],
            "Unik":     [int(df[c].nunique()) for c in df.columns],
            "Sampel":   [str(df[c].dropna().iloc[0]) if df[c].notna().any() else "–"
                         for c in df.columns],
        })
        st.dataframe(dtype_df, use_container_width=True, hide_index=True)


# =============================================================================
# Helpers: Preview, Save, Log
# =============================================================================

def _preview_and_save(df: pd.DataFrame, source_label: str, key_suffix: str):
    """Preview DataFrame hasil scraping dan simpan ke session_state."""
    st.markdown("#### 👀 Preview Hasil")

    n_show = min(10, len(df))
    st.dataframe(df.head(n_show), use_container_width=True)
    if len(df) > n_show:
        st.caption(f"Menampilkan {n_show} dari {len(df):,} baris.")

    # Info ringkas
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Baris", f"{len(df):,}")
    col_b.metric("Kolom", len(df.columns))
    col_c.metric("Missing", int(df.isnull().sum().sum()))

    # Simpan ke session_state
    st.session_state["scraping_result"] = {
        "df":          df,
        "source":      source_label,
        "scraped_at":  time.strftime("%Y-%m-%d %H:%M:%S"),
        "n_rows":      len(df),
        "n_cols":      len(df.columns),
    }

    st.success(
        "💾 Data disimpan sementara. "
        "Buka tab **📊 Hasil & Export** untuk cleaning dan kirim ke analisis."
    )


def _show_scraping_log():
    """Tampilkan log aktivitas scraping."""
    log = st.session_state.get("scraping_log", [])
    if log:
        with st.expander(f"📋 Log Aktivitas ({len(log)} entri)"):
            for entry in reversed(log[-20:]):
                st.caption(f"• {entry}")


def _show_robots_tip(url: str):
    """Tampilkan robots.txt URL sebagai informasi."""
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    st.info(
        f"💡 Jika scraping diblok, cek kebijakan robots.txt: "
        f"[{robots_url}]({robots_url})"
    )


def _log(message: str):
    """Tambah entry ke scraping log."""
    if "scraping_log" not in st.session_state:
        st.session_state.scraping_log = []
    timestamp = time.strftime("%H:%M:%S")
    st.session_state.scraping_log.append(f"[{timestamp}] {message}")


def _save_scraping_session(df: pd.DataFrame, source: str):
    """Simpan ringkasan ke session_state untuk export.py."""
    st.session_state["scraping_session"] = {
        "n_rows":    len(df),
        "n_cols":    len(df.columns),
        "source":    source,
        "col_names": df.columns.tolist(),
        "n_numeric": len(df.select_dtypes(include="number").columns),
        "n_missing": int(df.isnull().sum().sum()),
        "n_dup":     int(df.duplicated().sum()),
    }
