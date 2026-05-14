"""
utils/auth.py — Ruang Statistika v4.4
Sistem autentikasi: login per-user + license key validation + Pro guard.

Perubahan v4.4:
- Tambah load_users_config() → baca users.yaml
- Tambah verify_user_login() → bcrypt check
- Tambah get_user_from_session() → ambil data user aktif
- render_license_sidebar() tetap ada untuk backward compat
- LICENSE_REGISTRY tetap dipertahankan (untuk validasi key manual jika perlu)
"""

from __future__ import annotations

import json
import os
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import bcrypt
import streamlit as st
import yaml

# ── Quota cache ───────────────────────────────────────────────────────────────
QUOTA_CACHE_FILE = ".quota_cache.json"
DAILY_FREE_QUOTA = 1

# ── License Registry ──────────────────────────────────────────────────────────
# Tetap dipertahankan untuk validasi key manual / backward compat
LICENSE_REGISTRY: dict[str, dict] = {
    #"PRO-STAT":       {"expires": None,         "label": "Permanent"},
    "PRO-STAT-2026":  {"expires": "2026-12-06", "label": "Akademisi Pro 2026"},
    # Tambah key baru di sini:
    # "MY-NEW-KEY": {"expires": "2027-03-31", "label": "Custom Key"},
}


# ══════════════════════════════════════════════════════════════════════════════
# USER AUTH — baca users.yaml
# ══════════════════════════════════════════════════════════════════════════════

def _get_users_config_path() -> Path:
    """Cari users.yaml — di root project atau di .streamlit/."""
    candidates = [
        Path("users.yaml"),
        Path(".streamlit/users.yaml"),
    ]
    for p in candidates:
        if p.exists():
            return p
    return Path("users.yaml")  # default (mungkin belum ada)


def load_users_config() -> Optional[dict]:
    """
    Load konfigurasi user.

    Prioritas pembacaan:
      1. Streamlit Secrets → st.secrets["users_yaml"]["content"]
         (digunakan saat deploy di Streamlit Community Cloud)
      2. File users.yaml lokal
         (digunakan saat development di komputer sendiri)

    Format YAML yang diharapkan:
        credentials:
          usernames:
            username_key:
              name: Nama Lengkap
              email: email@domain.com
              password: $2b$12$...   # bcrypt hash
              role: free | pro | admin
              license_key: PRO-STAT-XXXX
              active: true | false
        cookie:
          name: ...
          key: ...
          expiry_days: 7
    """
    # ── Prioritas 1: Baca dari Streamlit Secrets (untuk deploy) ──────────────
    try:
        yaml_content = st.secrets["users_yaml"]["content"]
        config = yaml.safe_load(yaml_content)
        if config and "credentials" in config:
            return config
    except (KeyError, FileNotFoundError, Exception):
        pass  # Secrets tidak ada → lanjut ke file lokal

    # ── Prioritas 2: Baca dari file users.yaml lokal (untuk development) ─────
    config_path = _get_users_config_path()
    if not config_path.exists():
        st.error(
            "⚠️ File users.yaml tidak ditemukan dan Streamlit Secrets belum diatur. "
            "Lihat PANDUAN_IMPLEMENTASI.md untuk cara setup."
        )
        return None
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception as e:
        st.warning(f"⚠️ Gagal membaca users.yaml: {e}")
        return None


def verify_user_login(username: str, password: str) -> tuple[bool, Optional[dict]]:
    """
    Verifikasi username + password terhadap users.yaml.

    Return:
        (True, user_data_dict)  → login berhasil
        (False, None)           → gagal (user tidak ada / password salah / nonaktif)
    """
    config = load_users_config()
    if not config:
        return False, None

    usernames = config.get("credentials", {}).get("usernames", {})
    user_key = username.strip().lower()

    if user_key not in usernames:
        return False, None

    user = usernames[user_key]

    # Cek status aktif
    if not user.get("active", True):
        return False, None

    # Verifikasi password dengan bcrypt
    stored_hash = user.get("password", "")
    try:
        match = bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8"))
    except Exception:
        return False, None

    if not match:
        return False, None

    return True, {
        "username":    user_key,
        "name":        user.get("name", username),
        "email":       user.get("email", ""),
        "role":        user.get("role", "free"),
        "license_key": user.get("license_key", ""),
        "active":      user.get("active", True),
    }


def get_user_from_session() -> Optional[dict]:
    """Ambil data user yang sedang login dari session state."""
    if not st.session_state.get("user_logged_in"):
        return None
    return st.session_state.get("_user_data")


def save_user_to_session(user_data: dict) -> None:
    """Simpan data user ke session state setelah login berhasil."""
    st.session_state["_user_data"]     = user_data
    st.session_state["user_logged_in"] = True
    st.session_state["user_name"]      = user_data.get("name", "")
    st.session_state["username"]       = user_data.get("username", "")

    # Auto-set license key jika user punya
    license_key = user_data.get("license_key", "")
    if license_key:
        st.session_state["_modal_license_key"] = license_key
        st.session_state["sidebar_license_key"] = license_key


def logout_user() -> None:
    """Hapus semua data user dari session state."""
    for key in [
        "_user_data", "user_logged_in", "user_name", "username",
        "_modal_license_key", "sidebar_license_key",
    ]:
        st.session_state.pop(key, None)


# ══════════════════════════════════════════════════════════════════════════════
# LICENSE VALIDATION (dipertahankan dari versi sebelumnya)
# ══════════════════════════════════════════════════════════════════════════════

def validate_license(key: str) -> dict:
    """
    Validasi license key.
    Return dict dengan keys: status ('pro'/'free'/'expired'), label, expires.
    """
    key = key.strip().upper()
    if key not in LICENSE_REGISTRY:
        return {"status": "free", "label": "—", "expires": None}

    entry = LICENSE_REGISTRY[key]
    expires_str = entry.get("expires")

    if expires_str is None:
        return {"status": "pro", "label": entry["label"], "expires": None}

    try:
        exp_date = date.fromisoformat(expires_str)
        if date.today() <= exp_date:
            return {"status": "pro", "label": entry["label"], "expires": exp_date}
        else:
            return {"status": "expired", "label": entry["label"], "expires": exp_date}
    except ValueError:
        return {"status": "free", "label": "—", "expires": None}


def render_license_sidebar() -> dict:
    """
    Render input license key di sidebar + return license_info dict.
    Tetap dipertahankan untuk backward compat dengan app.py.
    """
    # Jika sudah ada license dari login user, gunakan itu
    auto_key = st.session_state.get("_modal_license_key", "")

    key_input = st.text_input(
        "🔑 License Key",
        value=auto_key,
        type="password",
        key="sidebar_license_key",
        placeholder="PRO-STAT-XXXX",
        help="Masukkan license key Pro Anda",
    )

    # Jika user login via pro_licenses / Supabase dengan role pro,
    # tampilkan Pro Aktif langsung tanpa validasi ke LICENSE_REGISTRY
    _session_user = st.session_state.get("_user_data", {})
    _session_is_pro = _session_user.get("role") == "pro"

    if _session_is_pro:
        # Cek masa berlaku dari session jika ada
        from datetime import datetime, timezone
        expires_str = _session_user.get("expires_at")
        _expired = False
        exp_txt = ""
        if expires_str:
            try:
                exp_dt = datetime.fromisoformat(expires_str.replace("Z", "+00:00"))
                if datetime.now(timezone.utc) > exp_dt:
                    _expired = True
                else:
                    exp_txt = f" · exp {exp_dt.strftime('%d %b %Y')}"
            except Exception:
                pass

        if _expired:
            st.markdown(
                "<span class='badge-invalid'>⚠️ Akses Pro Expired</span>",
                unsafe_allow_html=True,
            )
            info = {"status": "free", "label": "—", "expires": None}
        else:
            st.markdown(
                f"<span class='badge-valid'>✅ Pro Aktif{exp_txt}</span>",
                unsafe_allow_html=True,
            )
            info = {"status": "pro", "label": "Pro via Login", "expires": None}

    elif key_input:
        info = validate_license(key_input)
        if info["status"] == "pro":
            exp_txt = (
                f" · exp {info['expires'].strftime('%d %b %Y')}"
                if info["expires"] else ""
            )
            st.markdown(
                f"<span class='badge-valid'>✅ Pro Aktif{exp_txt}</span>",
                unsafe_allow_html=True,
            )
        elif info["status"] == "expired":
            st.markdown(
                "<span class='badge-invalid'>⚠️ Key Expired</span>",
                unsafe_allow_html=True,
            )
            info = {"status": "free", "label": "—", "expires": None}
        else:
            st.markdown(
                "<span class='badge-invalid'>❌ Key Tidak Valid</span>",
                unsafe_allow_html=True,
            )
            info = {"status": "free", "label": "—", "expires": None}
    else:
        info = {"status": "free", "label": "—", "expires": None}

    return info


# ══════════════════════════════════════════════════════════════════════════════
# PRO GUARD
# ══════════════════════════════════════════════════════════════════════════════

def require_pro(license_info: dict, feature_name: str = "Fitur ini") -> bool:
    """
    Guard untuk modul Pro. Panggil di baris pertama render() modul Pro.
    Return True jika Pro, tampilkan pesan upgrade dan return False jika Free.

    Cek status Pro dari dua sumber (prioritas urut):
      1. Session state — user login via pro_licenses (dari Lynk.id)
      2. license_info dict — user input license key manual
    """
    # Cek dari session state dulu (user Pro dari Lynk.id)
    user_data = st.session_state.get("_user_data", {})
    if user_data.get("role") == "pro":
        # Pastikan masa akses belum habis
        expires_at = user_data.get("expires_at")
        if expires_at:
            from datetime import datetime, timezone
            try:
                exp_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                if datetime.now(timezone.utc) <= exp_dt:
                    return True
            except Exception:
                return True  # kalau parse gagal, anggap masih valid
        else:
            return True  # tidak ada expires = permanent

    # Fallback: cek dari license_info (input manual)
    if license_info.get("status") == "pro":
        return True

    st.markdown(f"""
    <div style='
        background: linear-gradient(135deg, #0c2340 0%, #185FA5 100%);
        border-radius: 16px; padding: 2rem 2.5rem; text-align: center;
        color: white; margin: 2rem 0;
    '>
        <div style='font-size: 2.5rem; margin-bottom: 0.5rem;'>🔒</div>
        <h3 style='color: white; margin: 0 0 0.5rem; font-size: 1.3rem;'>
            {feature_name} — Fitur Pro
        </h3>
        <p style='color: #85b7eb; margin: 0 0 1.2rem; font-size: 0.9rem;'>
            Fitur ini memerlukan License Key Pro aktif.
        </p>
        <a href='https://yogoaj.github.io' target='_blank'
           style='background: white; color: #0c2340; padding: 8px 24px;
                  border-radius: 20px; font-weight: 600; font-size: 0.9rem;
                  text-decoration: none;'>
            Dapatkan License Key →
        </a>
    </div>
    """, unsafe_allow_html=True)
    return False


# ══════════════════════════════════════════════════════════════════════════════
# QUOTA SYSTEM (tidak berubah dari v4.3)
# ══════════════════════════════════════════════════════════════════════════════

def _load_quota_cache() -> dict:
    if not os.path.exists(QUOTA_CACHE_FILE):
        return {}
    try:
        with open(QUOTA_CACHE_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_quota_cache(cache: dict) -> None:
    try:
        with open(QUOTA_CACHE_FILE, "w") as f:
            json.dump(cache, f)
    except Exception:
        pass


def check_export_quota(session_id: str) -> tuple[bool, int]:
    """
    Cek apakah user masih punya kuota export gratis hari ini.
    Return (can_export: bool, used_today: int)
    """
    cache = _load_quota_cache()
    today = date.today().isoformat()
    key = f"{session_id}:{today}"
    used = cache.get(key, 0)
    return used < DAILY_FREE_QUOTA, used


def check_daily_export_quota(session_id: str = "") -> tuple[bool, int]:
    """
    Alias untuk check_export_quota — kompatibel dengan export.py.
    Jika session_id kosong, ambil dari st.session_state.
    """
    if not session_id:
        import streamlit as _st
        session_id = _st.session_state.get("_session_id", "default")
    return check_export_quota(session_id)


def get_quota_remaining(session_id: str = "") -> int:
    """
    Return sisa kuota export harian. Digunakan di export.py untuk tampilan UI.
    """
    if not session_id:
        import streamlit as _st
        session_id = _st.session_state.get("_session_id", "default")
    _, used = check_export_quota(session_id)
    return max(0, DAILY_FREE_QUOTA - used)


def consume_export_quota(session_id: str = "") -> None:
    """Kurangi kuota export gratis harian."""
    if not session_id:
        import streamlit as _st
        session_id = _st.session_state.get("_session_id", "default")
    cache = _load_quota_cache()
    today = date.today().isoformat()
    key = f"{session_id}:{today}"
    cache[key] = cache.get(key, 0) + 1
    _save_quota_cache(cache)
