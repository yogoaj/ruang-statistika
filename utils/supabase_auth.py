"""
utils/supabase_auth.py — Ruang Statistika v4.9
Sistem autentikasi via Supabase:
  - Sign In (email + password) → cek Supabase Auth dulu, fallback ke pro_licenses
  - Sign In Google (OAuth) → redirect ke Google, tangkap callback
  - Sign Up (registrasi mandiri)
  - Forgot Password (kirim email reset)
  - Sign Out
  - Restore session dari st.session_state
  - Handle Google OAuth callback dari URL query params

Perubahan v4.9 — Fix Google OAuth 403:
  - supabase_sign_in_google(): HAPUS redirect_to dari options.
    Dulu redirect_to diisi URL Streamlit → Google reject karena tidak cocok
    dengan Authorized Redirect URI yang terdaftar (URL Supabase).
    Sekarang biarkan Supabase pakai Callback URL default-nya sendiri.
  - handle_google_callback(): lebih robust, tangkap error dengan jelas.
  - JS fragment reader dipindah sepenuhnya ke app.py (tidak berubah).
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

    Di Streamlit Cloud, isi Secrets seperti ini:
        [supabase]
        url = "https://xxxxxx.supabase.co"
        anon_key = "eyJhbGci..."
    """
    try:
        from supabase import create_client
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
    meta      = getattr(user_obj, "user_metadata", {}) or {}
    full_name = (
        meta.get("full_name")
        or meta.get("name")
        or user_obj.email.split("@")[0]
    )
    email   = getattr(user_obj, "email", "")
    user_id = str(getattr(user_obj, "id", ""))

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
        "role":        "free",
        "license_key": "",
        "active":      True,
    }

    if session_obj:
        st.session_state["_supabase_access_token"]  = session_obj.access_token
        st.session_state["_supabase_refresh_token"] = session_obj.refresh_token


def restore_supabase_session() -> bool:
    """
    Coba restore session dari access_token yang tersimpan di session_state.
    Dipanggil di awal app.py sebelum render apapun.
    Return True jika berhasil restore, False jika token expired/tidak ada.
    """
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

    for k in ["_supabase_access_token", "_supabase_refresh_token"]:
        st.session_state.pop(k, None)
    return False


def get_current_user() -> Optional[dict]:
    """Return dict data user yang sedang login, atau None."""
    if not st.session_state.get("user_logged_in"):
        return None
    return st.session_state.get("_user_data")


# ══════════════════════════════════════════════════════════════════════════════
# GOOGLE OAUTH  ← DIPERBAIKI TOTAL v4.9
# ══════════════════════════════════════════════════════════════════════════════

def supabase_sign_in_google() -> tuple[bool, str]:
    """
    Inisiasi login Google via OAuth.

    PERBAIKAN v4.9:
      - redirect_to DIHAPUS dari options.
      - Dulu redirect_to diisi URL Streamlit (app_url dari secrets).
        Ini menyebabkan 403 dari Google karena URL yang dikirim sebagai
        redirect_uri ke Google adalah URL Streamlit, sedangkan yang terdaftar
        di Google Cloud Authorized Redirect URIs adalah URL Supabase callback
        (https://xxx.supabase.co/auth/v1/callback).
      - Sekarang Supabase otomatis memakai Callback URL default-nya sendiri
        yang sudah terdaftar di Google Cloud → tidak ada mismatch → tidak 403.

    Alur setelah fix:
      1. Fungsi ini dipanggil saat user klik "Lanjutkan dengan Google"
      2. Supabase generate URL redirect ke halaman consent Google
         (dengan redirect_uri = https://xxx.supabase.co/auth/v1/callback)
      3. User pilih akun Google
      4. Google redirect ke Supabase callback URL
      5. Supabase redirect ke Site URL (ruang-statistika.streamlit.app)
         dengan token di URL fragment (#access_token=...)
      6. JS snippet di app.py membaca fragment → konversi ke query_params
      7. handle_google_callback() membaca query_params → set session

    Return:
      (True, url_google)   → berhasil, app.py redirect browser ke url ini
      (False, pesan_error) → gagal
    """
    sb = get_supabase()
    if not sb:
        return False, "Koneksi ke Supabase gagal."

    try:
        resp = sb.auth.sign_in_with_oauth({
            "provider": "google",
            "options": {
                # TIDAK ada redirect_to — Supabase pakai Callback URL default
                "query_params": {
                    "access_type": "offline",
                    "prompt":      "select_account",
                },
            },
        })

        if resp and resp.url:
            return True, resp.url

        return False, "Gagal generate URL login Google. Coba lagi."

    except Exception as e:
        return False, f"❌ Login Google gagal: {e}"


def handle_google_callback() -> bool:
    """
    Tangkap token dari URL setelah redirect balik dari Google/Supabase.

    HARUS dipanggil di paling awal app.py, SEBELUM restore_supabase_session()
    dan SEBELUM st.set_page_config().

    Alur:
      - Supabase OAuth mengirim token via URL fragment (#access_token=...).
      - Fragment tidak dikirim ke server — hanya ada di browser.
      - JS snippet di app.py membaca fragment dan mengonversinya ke
        query_params (?access_token=...) agar Streamlit bisa membacanya.
      - Fungsi ini membaca query_params tersebut dan men-set session Supabase.

    Return True jika berhasil set session dari callback Google.
    """
    if st.session_state.get("user_logged_in"):
        return True

    params        = st.query_params
    access_token  = params.get("access_token")
    refresh_token = params.get("refresh_token", "")

    if not access_token:
        return False

    sb = get_supabase()
    if not sb:
        return False

    try:
        resp = sb.auth.set_session(access_token, refresh_token)
        if resp and resp.user:
            save_supabase_session(resp.user, resp.session)
            # Bersihkan token dari URL agar tidak tampil di address bar
            st.query_params.clear()
            return True
    except Exception as e:
        # Token tidak valid atau expired — bersihkan saja
        pass

    st.query_params.clear()
    return False


# ══════════════════════════════════════════════════════════════════════════════
# HELPER INTERNAL — cek keberadaan email di Supabase Auth
# ══════════════════════════════════════════════════════════════════════════════

def _email_exists_in_supabase_auth(sb, email: str) -> Optional[bool]:
    """
    Probe apakah email terdaftar di Supabase Auth tanpa Service Role Key.

    Teknik: coba sign_in dengan password dummy →
      - "Invalid login credentials" → user ADA (password salah)
      - "Email not confirmed"       → user ADA (belum konfirmasi)
      - "User not found" / lainnya  → user TIDAK ADA
      - Exception lain              → tidak bisa ditentukan (return None)
    """
    try:
        sb.auth.sign_in_with_password({"email": email, "password": "__probe_rs__"})
        return True
    except Exception as e:
        msg = str(e).lower()
        if "invalid login credentials" in msg:
            return True
        if "email not confirmed" in msg:
            return True
        if "user not found" in msg or "no user" in msg:
            return False
        return None


# ══════════════════════════════════════════════════════════════════════════════
# SIGN IN — Fallback via pro_licenses
# ══════════════════════════════════════════════════════════════════════════════

def _sign_in_via_pro_licenses(sb, email: str, password: str) -> tuple[bool, str]:
    """
    Fallback login via tabel pro_licenses.

    HANYA dipanggil jika sudah dipastikan email TIDAK ADA di Supabase Auth.
    Ini mencegah user bypass password Supabase Auth dengan password lama
    dari pro_licenses.
    """
    from datetime import datetime, timezone

    try:
        resp = (
            sb.table("pro_licenses")
            .select("email, name, password, license_key, expires_at, is_active, tier")
            .eq("email", email.strip().lower())
            .single()
            .execute()
        )
    except Exception:
        return False, "❌ Email atau password salah."

    row = resp.data if resp else None
    if not row:
        return False, "❌ Email atau password salah."

    if row.get("password", "") != password:
        return False, "❌ Email atau password salah."

    if not row.get("is_active", True):
        return False, "❌ Akun kamu sudah dinonaktifkan. Hubungi admin."

    expires_str = row.get("expires_at")
    if expires_str:
        try:
            expires_dt = datetime.fromisoformat(expires_str.replace("Z", "+00:00"))
            if datetime.now(timezone.utc) > expires_dt:
                return False, (
                    "⏰ Masa akses Pro kamu sudah habis. "
                    "Silakan perpanjang di lynk.id/ruangstatistika"
                )
        except Exception:
            pass

    name = row.get("name") or email.split("@")[0]
    tier = row.get("tier") or "starter"

    st.session_state["user_logged_in"]  = True
    st.session_state["user_name"]       = name
    st.session_state["username"]        = email
    st.session_state["_auth_provider"]  = "pro_licenses"
    st.session_state["_user_data"] = {
        "username":    email,
        "name":        name,
        "email":       email,
        "role":        "pro",
        "tier":        tier,
        "license_key": row.get("license_key", ""),
        "active":      True,
        "expires_at":  expires_str,
    }
    st.session_state["_modal_license_key"] = row.get("license_key", "")

    return True, ""


# ══════════════════════════════════════════════════════════════════════════════
# SIGN IN — Email + Password
# ══════════════════════════════════════════════════════════════════════════════

def supabase_sign_in(email: str, password: str) -> tuple[bool, str]:
    """
    Login dengan email + password.

    Alur:
      1. Coba Supabase Auth
         - Berhasil → selesai
         - "Email not confirmed" → STOP, suruh konfirmasi
         - "Invalid login credentials" → STOP, suruh reset password
           (jangan fallback — user ADA di Supabase Auth, hanya password salah)
         - Error lain → lanjut ke langkah 2
      2. Fallback ke pro_licenses (user Pro Lynk.id yang belum sign_up mandiri)
    """
    sb = get_supabase()
    if not sb:
        return False, "Koneksi ke Supabase gagal."

    email = email.strip().lower()

    try:
        resp = sb.auth.sign_in_with_password({"email": email, "password": password})
        if resp and resp.user:
            save_supabase_session(resp.user, resp.session)
            return True, ""
    except Exception as e:
        msg_lower = str(e).lower()

        if "email not confirmed" in msg_lower:
            return False, (
                "📧 Email kamu belum dikonfirmasi. "
                "Cek inbox (atau folder spam) dan klik link konfirmasi, "
                "lalu coba masuk lagi."
            )

        if "invalid login credentials" in msg_lower:
            return False, (
                "❌ Password salah. "
                "Gunakan tombol **Lupa password?** jika lupa password kamu."
            )

        # Error lain → user kemungkinan tidak ada di Supabase Auth
        # Lanjut fallback ke pro_licenses

    return _sign_in_via_pro_licenses(sb, email, password)


# ══════════════════════════════════════════════════════════════════════════════
# SIGN UP — Registrasi Baru
# ══════════════════════════════════════════════════════════════════════════════

def supabase_sign_up(email: str, password: str, full_name: str) -> tuple[bool, str]:
    """
    Daftar akun baru via Supabase Auth.

    Deteksi konflik: jika email sudah ada di pro_licenses, beri peringatan
    bahwa password yang berlaku setelah konfirmasi adalah password baru
    (bukan password dari email Lynk.id).
    """
    sb = get_supabase()
    if not sb:
        return False, "Koneksi ke Supabase gagal."

    email = email.strip().lower()

    if len(password) < 6:
        return False, "❌ Password minimal 6 karakter."

    _in_pro_licenses = False
    try:
        _pl = (
            sb.table("pro_licenses")
            .select("email")
            .eq("email", email)
            .maybeSingle()
            .execute()
        )
        _in_pro_licenses = bool(_pl and _pl.data)
    except Exception:
        pass

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
            identities = getattr(resp.user, "identities", [])
            if identities is not None and len(identities) == 0:
                return False, "❌ Email ini sudah terdaftar. Silakan login."

            if _in_pro_licenses:
                return True, (
                    "✅ Pendaftaran berhasil! "
                    "Cek email kamu dan klik link konfirmasi.\n\n"
                    "⚠️ **Perhatian:** Kamu memiliki akun Pro dari pembelian sebelumnya. "
                    "Setelah konfirmasi email, gunakan **password yang baru saja kamu buat** "
                    "saat login — bukan password dari email pembelian Lynk.id."
                )

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
    Kirim email reset password.

    Deteksi jalur akun:
      - Email hanya di pro_licenses → reset Supabase tidak berlaku,
        arahkan ke email Lynk.id atau hubungi admin
      - Email di Supabase Auth → kirim reset normal
    """
    sb = get_supabase()
    if not sb:
        return False, "Koneksi ke Supabase gagal."

    email = email.strip().lower()

    _in_pro_licenses = False
    try:
        _pl = (
            sb.table("pro_licenses")
            .select("email")
            .eq("email", email)
            .maybeSingle()
            .execute()
        )
        _in_pro_licenses = bool(_pl and _pl.data)
    except Exception:
        pass

    _in_supabase_auth = _email_exists_in_supabase_auth(sb, email)

    if _in_pro_licenses and _in_supabase_auth is False:
        return False, (
            "⚠️ Email ini terdaftar sebagai akun Pro dari pembelian Lynk.id, "
            "bukan sebagai akun Ruang Statistika biasa.\n\n"
            "Gunakan **password yang ada di email konfirmasi pembelian** dari Lynk.id. "
            "Jika tidak punya email tersebut, hubungi admin via "
            "**WhatsApp 087887533149**."
        )

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
            if _in_pro_licenses:
                return False, (
                    "⚠️ Email ini terdaftar sebagai akun Pro dari pembelian Lynk.id. "
                    "Hubungi admin via WhatsApp 087887533149 untuk bantuan reset password."
                )
            return True, "📧 Jika email terdaftar, link reset password akan dikirim."
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
            pass

    keys_to_clear = [
        "user_logged_in", "user_name", "username",
        "_user_data", "_supabase_uid", "_supabase_email",
        "_supabase_access_token", "_supabase_refresh_token",
        "_auth_provider", "_modal_license_key", "sidebar_license_key",
        "_login_error", "modal_tab",
    ]
    for key in keys_to_clear:
        st.session_state.pop(key, None)
