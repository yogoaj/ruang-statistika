"""
utils/supabase_auth.py — Ruang Statistika v4.6
Sistem autentikasi via Supabase:
  - Sign In (email + password) → cek Supabase Auth dulu, fallback ke pro_licenses
  - Sign Up (registrasi mandiri)
  - Forgot Password (kirim email reset)
  - Sign Out
  - Restore session dari st.session_state
  - [🔜] Login Google — aktifkan via Supabase Dashboard → Auth → Providers

Cara pakai di app.py:
    from utils.supabase_auth import (
        supabase_sign_in, supabase_sign_up,
        supabase_sign_out, supabase_forgot_password,
        restore_supabase_session, get_current_user,
        save_supabase_session,
    )

Perubahan v4.6:
  - supabase_sign_in: tambah fallback login via tabel pro_licenses
  - Jika login lewat pro_licenses: role otomatis jadi 'pro', cek expires_at
  - Siap untuk tambahan Google login (tidak perlu ubah kode ini)
"""

from __future__ import annotations

from typing import Optional
import streamlit as st


# ══════════════════════════════════════════════════════════════════════════════
# INISIALISASI SUPABASE CLIENT
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_resource
def _get_supabase_client():
    """
    Buat Supabase client sekali, di-cache supaya tidak reconnect tiap rerun.
    Membaca kredensial dari Streamlit Secrets.

    Di Streamlit Cloud, isi Secrets seperti ini:
        [supabase]
        url = "https://xxxxxx.supabase.co"
        anon_key = "eyJhbGci..."

    Di lokal, buat file .streamlit/secrets.toml dengan isi yang sama.
    """
    try:
        from supabase import create_client, Client
        url      = st.secrets["supabase"]["url"]
        anon_key = st.secrets["supabase"]["anon_key"]
        return create_client(url, anon_key)
    except KeyError:
        st.error(
            "⚠️ Konfigurasi Supabase belum diatur. "
            "Tambahkan [supabase] url dan anon_key ke Streamlit Secrets."
        )
        return None
    except Exception as e:
        st.error(f"⚠️ Gagal koneksi ke Supabase: {e}")
        return None


def get_supabase():
    """Shortcut ambil client. Return None jika belum dikonfigurasi."""
    return _get_supabase_client()


# ══════════════════════════════════════════════════════════════════════════════
# SESSION MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════

def save_supabase_session(user_obj, session_obj=None) -> None:
    """
    Simpan data user Supabase ke st.session_state setelah login berhasil.
    Kompatibel dengan format ctx["user_name"] yang sudah ada di app.py.
    """
    # Ambil metadata user — bisa dari user_metadata atau dari tabel profiles
    meta        = getattr(user_obj, "user_metadata", {}) or {}
    full_name   = (
        meta.get("full_name")
        or meta.get("name")
        or user_obj.email.split("@")[0]  # fallback: bagian sebelum @
    )
    email       = getattr(user_obj, "email", "")
    user_id     = str(getattr(user_obj, "id", ""))

    # Simpan ke session state (kompatibel dengan app.py yang sudah ada)
    st.session_state["user_logged_in"]   = True
    st.session_state["user_name"]        = full_name
    st.session_state["username"]         = email
    st.session_state["_supabase_uid"]    = user_id
    st.session_state["_supabase_email"]  = email
    st.session_state["_auth_provider"]   = "supabase"
    st.session_state["_user_data"] = {
        "username":    email,
        "name":        full_name,
        "email":       email,
        "role":        "free",   # default; bisa diupdate dari tabel profiles
        "license_key": "",
        "active":      True,
    }

    # Simpan access token untuk restore session nanti
    if session_obj:
        st.session_state["_supabase_access_token"]  = session_obj.access_token
        st.session_state["_supabase_refresh_token"] = session_obj.refresh_token


def restore_supabase_session() -> bool:
    """
    Coba restore session dari access_token yang tersimpan di session_state.
    Dipanggil di awal app.py sebelum render apapun.
    Return True jika berhasil restore, False jika token expired/tidak ada.
    """
    # Kalau sudah login, skip
    if st.session_state.get("user_logged_in"):
        return True

    access_token  = st.session_state.get("_supabase_access_token")
    refresh_token = st.session_state.get("_supabase_refresh_token")

    if not access_token:
        return False

    sb = get_supabase()
    if not sb:
        return False

    try:
        resp = sb.auth.set_session(access_token, refresh_token or "")
        if resp and resp.user:
            save_supabase_session(resp.user, resp.session)
            return True
    except Exception:
        pass

    # Token expired — bersihkan
    for k in ["_supabase_access_token", "_supabase_refresh_token"]:
        st.session_state.pop(k, None)
    return False


def get_current_user() -> Optional[dict]:
    """Return dict data user yang sedang login, atau None."""
    if not st.session_state.get("user_logged_in"):
        return None
    return st.session_state.get("_user_data")


# ══════════════════════════════════════════════════════════════════════════════
# SIGN IN — Email + Password
# ══════════════════════════════════════════════════════════════════════════════

def _sign_in_via_pro_licenses(
    sb, email: str, password: str
) -> tuple[bool, str]:
    """
    Fallback login: cek email + password langsung ke tabel pro_licenses.
    Dipanggil hanya jika login Supabase Auth gagal.

    Juga mengecek:
      - apakah akun masih aktif (is_active = true)
      - apakah masa akses belum habis (expires_at > sekarang)
    """
    from datetime import datetime, timezone

    try:
        resp = (
            sb.table("pro_licenses")
            .select("email, name, password, license_key, expires_at, is_active")
            .eq("email", email.strip().lower())
            .single()
            .execute()
        )
    except Exception:
        return False, "❌ Email atau password salah."

    row = resp.data if resp else None
    if not row:
        return False, "❌ Email atau password salah."

    # Cek password (plain text — sesuai yang kita generate di Edge Function)
    if row.get("password", "") != password:
        return False, "❌ Email atau password salah."

    # Cek status aktif
    if not row.get("is_active", True):
        return False, "❌ Akun kamu sudah dinonaktifkan. Hubungi admin."

    # Cek masa berlaku
    expires_str = row.get("expires_at")
    if expires_str:
        try:
            expires_dt = datetime.fromisoformat(expires_str.replace("Z", "+00:00"))
            if datetime.now(timezone.utc) > expires_dt:
                return False, (
                    "⏰ Masa akses Pro kamu sudah habis. "
                    "Silakan perpanjang di yogoaj.github.io"
                )
        except Exception:
            pass

    # Login berhasil via pro_licenses — simpan ke session
    name = row.get("name") or email.split("@")[0]
    st.session_state["user_logged_in"]  = True
    st.session_state["user_name"]       = name
    st.session_state["username"]        = email
    st.session_state["_auth_provider"]  = "pro_licenses"
    st.session_state["_user_data"] = {
        "username":    email,
        "name":        name,
        "email":       email,
        "role":        "pro",   # semua user di pro_licenses = Pro
        "license_key": row.get("license_key", ""),
        "active":      True,
        "expires_at":  expires_str,
    }
    # Set license key otomatis ke session (agar sidebar Pro aktif)
    st.session_state["_modal_license_key"] = row.get("license_key", "")

    return True, ""


def supabase_sign_in(email: str, password: str) -> tuple[bool, str]:
    """
    Login dengan email + password.

    Alur:
      1. Coba login via Supabase Auth (user biasa / Google nanti)
      2. Kalau gagal → coba login via tabel pro_licenses (user Pro dari Lynk.id)

    Return: (berhasil: bool, pesan_error: str)
    """
    sb = get_supabase()
    if not sb:
        return False, "Koneksi ke Supabase gagal."

    # ── Langkah 1: Coba Supabase Auth ────────────────────────────────────────
    try:
        resp = sb.auth.sign_in_with_password({"email": email, "password": password})
        if resp and resp.user:
            save_supabase_session(resp.user, resp.session)
            return True, ""
    except Exception as e:
        msg = str(e)
        # Kalau email belum dikonfirmasi → jangan fallback, langsung info user
        if "Email not confirmed" in msg:
            return False, "📧 Email belum dikonfirmasi. Cek inbox kamu."

    # ── Langkah 2: Fallback ke tabel pro_licenses ─────────────────────────────
    return _sign_in_via_pro_licenses(sb, email, password)


# ══════════════════════════════════════════════════════════════════════════════
# SIGN UP — Registrasi Baru
# ══════════════════════════════════════════════════════════════════════════════

def supabase_sign_up(
    email: str,
    password: str,
    full_name: str,
) -> tuple[bool, str]:
    """
    Daftar akun baru.
    Return: (berhasil: bool, pesan: str)

    Supabase akan kirim email konfirmasi ke user.
    Setelah klik link di email, user baru bisa login.
    """
    sb = get_supabase()
    if not sb:
        return False, "Koneksi ke Supabase gagal."

    if len(password) < 6:
        return False, "❌ Password minimal 6 karakter."

    try:
        resp = sb.auth.sign_up({
            "email":    email,
            "password": password,
            "options": {
                "data": {
                    "full_name": full_name,
                    "name":      full_name,
                }
            },
        })

        if resp and resp.user:
            # Cek apakah email konfirmasi diaktifkan
            # Jika identities kosong → email sudah terdaftar sebelumnya
            identities = getattr(resp.user, "identities", [])
            if identities is not None and len(identities) == 0:
                return False, "❌ Email ini sudah terdaftar. Silakan login."
            return True, (
                "✅ Pendaftaran berhasil! "
                "Cek email kamu dan klik link konfirmasi sebelum login."
            )

        return False, "Pendaftaran gagal. Coba lagi."
    except Exception as e:
        msg = str(e)
        if "already registered" in msg or "already been registered" in msg:
            return False, "❌ Email ini sudah terdaftar. Silakan login."
        if "Password should be" in msg:
            return False, "❌ Password terlalu lemah. Gunakan minimal 6 karakter."
        return False, f"❌ Pendaftaran gagal: {msg}"


# ══════════════════════════════════════════════════════════════════════════════
# FORGOT PASSWORD — Kirim Email Reset
# ══════════════════════════════════════════════════════════════════════════════

def supabase_forgot_password(email: str, redirect_url: str = "") -> tuple[bool, str]:
    """
    Kirim email reset password ke user.
    redirect_url: URL yang dibuka setelah user klik link di email.
    Return: (berhasil: bool, pesan: str)
    """
    sb = get_supabase()
    if not sb:
        return False, "Koneksi ke Supabase gagal."

    try:
        options = {}
        if redirect_url:
            options["redirect_to"] = redirect_url

        sb.auth.reset_password_email(email, options=options if options else None)
        return True, (
            "📧 Link reset password telah dikirim ke email kamu. "
            "Cek inbox (dan folder spam jika tidak ada)."
        )
    except Exception as e:
        msg = str(e)
        if "User not found" in msg:
            # Demi keamanan, tetap tampilkan pesan sukses (tidak bocorkan info)
            return True, (
                "📧 Jika email terdaftar, link reset password akan dikirim."
            )
        return False, f"❌ Gagal mengirim email: {msg}"


# ══════════════════════════════════════════════════════════════════════════════
# SIGN OUT
# ══════════════════════════════════════════════════════════════════════════════

def supabase_sign_out() -> None:
    """Logout user dan bersihkan semua session state."""
    sb = get_supabase()
    if sb:
        try:
            sb.auth.sign_out()
        except Exception:
            pass  # Tetap lanjut bersihkan local state meski API gagal

    # Bersihkan semua key auth dari session state
    keys_to_clear = [
        "user_logged_in", "user_name", "username",
        "_user_data", "_supabase_uid", "_supabase_email",
        "_supabase_access_token", "_supabase_refresh_token",
        "_auth_provider", "_modal_license_key", "sidebar_license_key",
        "_login_error", "modal_tab",
    ]
    for key in keys_to_clear:
        st.session_state.pop(key, None)
