"""
utils/supabase_auth.py — Ruang Statistika v4.9.1 (clean)
Sistem autentikasi via Supabase:
  - Sign In (email + password) → cek Supabase Auth dulu, fallback ke pro_licenses
  - Sign In Google (OAuth) → redirect ke Google, tangkap callback
  - Sign Up (registrasi mandiri)
  - Forgot Password (kirim email reset)
  - Sign Out
  - Restore session dari st.session_state
  - Handle Google OAuth callback dari URL query params

Perubahan v4.9.1 — Clean & Stabil:
  - save_supabase_session(): normalisasi email ke lowercase + fallback eq()
    untuk mengatasi collation/index issue di pro_licenses
  - _sign_in_via_pro_licenses(): perbaiki typo 'name = name =', konsisten lowercase
  - supabase_sign_in_google(): tetap tanpa redirect_to (fix 403 Google OAuth)
  - Semua query pro_licenses sekarang pakai email.strip().lower()
  - Tidak mengubah signature fungsi → 100% kompatibel dengan app.py v4.9
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
        url = st.secrets["supabase"]["url"]
        anon_key = st.secrets["supabase"]["anon_key"]
        return create_client(url, anon_key)
    except KeyError:
        st.error(
            "⚠ Konfigurasi Supabase belum diatur. "
            "Tambahkan [supabase] url and anon_key ke Streamlit Secrets."
        )
        return None
    except Exception as e:
        st.error(f"⚠ Gagal koneksi ke Supabase: {e}")
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

    PERBAIKAN v4.9.1: Setelah login Supabase Auth berhasil, cek tabel pro_licenses
    untuk mendapatkan role, tier, dan expires_at yang benar.
    """
    meta = getattr(user_obj, "user_metadata", {}) or {}
    full_name = (
        meta.get("full_name")
        or meta.get("name")
        or user_obj.email.split("@")[0]
    )
    email = getattr(user_obj, "email", "")
    user_id = str(getattr(user_obj, "id", ""))

    # Default: free
    role = "free"
    tier = "starter"
    license_key = ""
    expires_at = None

    # Cek pro_licenses untuk status Pro
    try:
        sb = get_supabase()
        if sb:
            from datetime import datetime, timezone

            # Normalisasi email — kunci perbaikan
            clean_email = email.strip().lower()

            resp = (
                sb.table("pro_licenses")
                .select("license_key, expires_at, is_active, tier")
                .ilike("email", clean_email)
                .maybeSingle()
                .execute()
            )
            row = resp.data if resp else None

            # Fallback jika ilike tidak kena karena collation
            if not row:
                resp_alt = (
                    sb.table("pro_licenses")
                    .select("license_key, expires_at, is_active, tier")
                    .eq("email", clean_email)
                    .maybeSingle()
                    .execute()
                )
                row = resp_alt.data if resp_alt else None

            if row and row.get("is_active", True):
                expires_str = row.get("expires_at")
                _expired = False
                if expires_str:
                    try:
                        exp_dt = datetime.fromisoformat(expires_str.replace("Z", "+00:00"))
                        if datetime.now(timezone.utc) > exp_dt:
                            _expired = True
                    except Exception:
                        pass
                if not _expired:
                    role = "pro"
                    tier = row.get("tier") or "starter"
                    license_key = row.get("license_key", "")
                    expires_at = expires_str
    except Exception:
        pass  # Gagal cek pro_licenses → tetap free, tidak crash

    st.session_state["user_logged_in"] = True
    st.session_state["user_name"] = full_name
    st.session_state["username"] = email
    st.session_state["_supabase_uid"] = user_id
    st.session_state["_supabase_email"] = email
    st.session_state["_auth_provider"] = "supabase"
    st.session_state["_user_data"] = {
        "username": email,
        "name": full_name,
        "email": email,
        "role": role,
        "tier": tier,
        "license_key": license_key,
        "expires_at": expires_at,
        "active": True,
    }
    if license_key:
        st.session_state["_modal_license_key"] = license_key

    if session_obj:
        st.session_state["_supabase_access_token"] = session_obj.access_token
        st.session_state["_supabase_refresh_token"] = session_obj.refresh_token


def restore_supabase_session() -> bool:
    """
    Coba restore session dari access_token yang tersimpan di session_state.
    Dipanggil di awal app.py sebelum render apapun.
    Return True jika berhasil restore, False jika token expired/tidak ada.
    """
    if st.session_state.get("user_logged_in"):
        return True

    access_token = st.session_state.get("_supabase_access_token")
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
# GOOGLE OAUTH
# ══════════════════════════════════════════════════════════════════════════════

def supabase_sign_in_google() -> tuple[bool, str]:
    """
    Inisiasi login Google via OAuth.

    v4.9: redirect_to DIHAPUS agar tidak 403.
    Supabase pakai Callback URL default yang sudah terdaftar di Google Cloud.
    """
    sb = get_supabase()
    if not sb:
        return False, "Koneksi ke Supabase gagal."

    try:
        resp = sb.auth.sign_in_with_oauth({
            "provider": "google",
            "options": {
                "query_params": {
                    "access_type": "offline",
                    "prompt": "select_account",
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
    HARUS dipanggil di paling awal app.py, SEBELUM restore_supabase_session().
    """
    if st.session_state.get("user_logged_in"):
        return True

    params = st.query_params
    access_token = params.get("access_token")
    refresh_token = params.get("refresh_token", "")
    token_type = params.get("type", "")

    if not access_token:
        return False

    # Token recovery (reset password)
    if token_type == "recovery":
        st.session_state["_recovery_access_token"] = access_token
        st.session_state["_recovery_refresh_token"] = refresh_token
        st.session_state["modal_tab"] = "reset_password"
        st.query_params.clear()
        return False

    sb = get_supabase()
    if not sb:
        return False

    try:
        resp = sb.auth.set_session(access_token, refresh_token)
        if resp and resp.user:
            save_supabase_session(resp.user, resp.session)
            st.query_params.clear()
            return True
    except Exception:
        pass

    st.query_params.clear()
    return False


def supabase_update_password(new_password: str) -> tuple[bool, str]:
    """Update password user dalam sesi recovery."""
    if len(new_password) < 6:
        return False, "❌ Password minimal 6 karakter."

    access_token = st.session_state.get("_recovery_access_token", "")
    refresh_token = st.session_state.get("_recovery_refresh_token", "")

    if not access_token:
        return False, "❌ Sesi reset tidak valid. Minta link reset baru."

    sb = get_supabase()
    if not sb:
        return False, "Koneksi ke Supabase gagal."

    try:
        sb.auth.set_session(access_token, refresh_token)
        sb.auth.update_user({"password": new_password})
        st.session_state.pop("_recovery_access_token", None)
        st.session_state.pop("_recovery_refresh_token", None)
        return True, "✅ Password berhasil diperbarui. Silakan masuk dengan password baru."
    except Exception as e:
        return False, f"❌ Gagal memperbarui password: {e}"


# ══════════════════════════════════════════════════════════════════════════════
# HELPER INTERNAL
# ══════════════════════════════════════════════════════════════════════════════

def _email_exists_in_supabase_auth(sb, email: str) -> Optional[bool]:
    """
    Probe apakah email terdaftar di Supabase Auth tanpa Service Role Key.
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
    HANYA dipanggil jika email TIDAK ADA di Supabase Auth.
    """
    from datetime import datetime, timezone

    clean_email = email.strip().lower()

    try:
        resp = (
            sb.table("pro_licenses")
            .select("email, name, password, license_key, expires_at, is_active, tier")
            .ilike("email", clean_email)
            .maybeSingle()
            .execute()
        )
    except Exception:
        return False, "❌ Email atau password salah."

    row = resp.data if resp else None
    if not row:
        # Fallback eq
        try:
            resp2 = (
                sb.table("pro_licenses")
                .select("email, name, password, license_key, expires_at, is_active, tier")
                .eq("email", clean_email)
                .maybeSingle()
                .execute()
            )
            row = resp2.data if resp2 else None
        except Exception:
            row = None

    if not row:
        return False, "❌ Email atau password salah."

    if not row.get("is_active", True):
        return False, "❌ Akun kamu sudah dinonaktifkan. Hubungi admin."

    if row.get("password", "") != password:
        return False, "❌ Email atau password salah."

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

    st.session_state["user_logged_in"] = True
    st.session_state["user_name"] = name
    st.session_state["username"] = email
    st.session_state["_auth_provider"] = "pro_licenses"
    st.session_state["_user_data"] = {
        "username": email,
        "name": name,
        "email": email,
        "role": "pro",
        "tier": tier,
        "license_key": row.get("license_key", ""),
        "active": True,
        "expires_at": expires_str,
    }
    st.session_state["_modal_license_key"] = row.get("license_key", "")

    return True, ""


# ══════════════════════════════════════════════════════════════════════════════
# SIGN IN — Email + Password
# ══════════════════════════════════════════════════════════════════════════════

def supabase_sign_in(email: str, password: str) -> tuple[bool, str]:
    """
    Login dengan email + password.
    1. Coba Supabase Auth
    2. Fallback ke pro_licenses jika belum terdaftar
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
            # Coba fallback untuk user Lynk.id yang belum sign up
            _ok_pl, _msg_pl = _sign_in_via_pro_licenses(sb, email, password)
            if _ok_pl:
                return True, ""

            # Cek apakah ada di pro_licenses
            _is_pro_lynk = False
            try:
                _pl = (
                    sb.table("pro_licenses")
                    .select("email")
                    .ilike("email", email)
                    .maybeSingle()
                    .execute()
                )
                _is_pro_lynk = bool(_pl and _pl.data)
            except Exception:
                pass

            if _is_pro_lynk:
                return False, (
                    "❌ Password salah.

"
                    "Gunakan **password yang tertulis di email konfirmasi pembelian** "
                    "dari Lynk.id. Atau klik **Lupa password?** untuk reset."
                )

            return False, (
                "❌ Email atau password tidak dikenali.

"
                "**Sudah beli di Lynk.id?** Kemungkinan akunmu belum terdaftar di sistem. Coba:
"
                "1. Klik tab **Daftar** → buat akun dengan **email yang sama** dengan pembelian
"
                "2. Konfirmasi email, lalu **Masuk** — status Pro otomatis aktif

"
                "Atau hubungi admin via WhatsApp **087887533149** untuk bantuan aktivasi."
            )

    return _sign_in_via_pro_licenses(sb, email, password)


# ══════════════════════════════════════════════════════════════════════════════
# SIGN UP
# ══════════════════════════════════════════════════════════════════════════════

def supabase_sign_up(email: str, password: str, full_name: str) -> tuple[bool, str]:
    """Daftar akun baru via Supabase Auth."""
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
            .ilike("email", email)
            .maybeSingle()
            .execute()
        )
        _in_pro_licenses = bool(_pl and _pl.data)
    except Exception:
        pass

    try:
        resp = sb.auth.sign_up({
            "email": email,
            "password": password,
            "options": {
                "data": {
                    "full_name": full_name,
                    "name": full_name,
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
                    "Cek email kamu dan klik link konfirmasi.

"
                    "⚠ **Perhatian:** Kamu memiliki akun Pro dari pembelian sebelumnya. "
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
# FORGOT PASSWORD
# ══════════════════════════════════════════════════════════════════════════════

def supabase_forgot_password(email: str, redirect_url: str = "") -> tuple[bool, str]:
    """Kirim email reset password."""
    sb = get_supabase()
    if not sb:
        return False, "Koneksi ke Supabase gagal."

    email = email.strip().lower()

    _in_pro_licenses = False
    try:
        _pl = (
            sb.table("pro_licenses")
            .select("email")
            .ilike("email", email)
            .maybeSingle()
            .execute()
        )
        _in_pro_licenses = bool(_pl and _pl.data)
    except Exception:
        pass

    _in_supabase_auth = _email_exists_in_supabase_auth(sb, email)

    if _in_pro_licenses and _in_supabase_auth is False:
        return False, (
            "⚠ Email ini terdaftar dari pembelian di **Lynk.id**, "
            "tapi belum memiliki akun di aplikasi ini.

"
            "**Untuk bisa login, kamu perlu membuat akun dulu:**
"
            "1. Klik tab **Daftar** di atas
"
            "2. Daftar menggunakan **email yang sama** dengan pembelian
"
            "3. Buat password baru sesukamu
"
            "4. Cek email dan klik link konfirmasi, lalu **Masuk**

"
            "Status Pro kamu akan otomatis aktif setelah berhasil masuk. ✅

"
            "Butuh bantuan? Hubungi admin via WhatsApp **087887533149**."
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
                    "⚠ Email ini terdaftar sebagai akun Pro dari pembelian Lynk.id. "
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
        "_auth_provider",
        "_modal_license_key", "sidebar_license_key",
        "_recovery_access_token", "_recovery_refresh_token", "_recovery_token",
        "modal_tab", "_lupa_email_sent",
        "_auth_msg_error", "_auth_msg_success",
        "_login_error",
    ]
    for key in keys_to_clear:
        st.session_state.pop(key, None)
