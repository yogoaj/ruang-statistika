"""
utils/ai_helpers.py — AI API integration (8 Provider)
Ruang Statistika v4.5

Provider yang didukung:
  ✅ Gratis  : Groq (Llama 3.3 70B, Mixtral 8x7B, Gemma2 9B)
  ✅ Gratis  : Gemini 2.0 Flash (Google)
  ✅ Gratis  : OpenRouter — model :free (Llama, Gemma, DeepSeek)
  ✅ Gratis  : HuggingFace (Qwen 2.5 72B, Phi-3.5)
  ✅ Trial   : Mistral AI (Nemo, Mixtral 8x7B)
  ✅ Trial   : Cohere (Command-R, Command-R+)
  💳 Berbayar: Claude / Anthropic (Sonnet 4, Haiku)
  💳 Berbayar: ChatGPT / OpenAI (GPT-4o, GPT-4o-mini)

Changelog v4.5:
- Tambah OpenRouter, Mistral AI, Cohere sebagai provider baru
- Update HuggingFace: Qwen 2.5 72B & Phi-3.5 (model lebih kuat)
- Update Gemini ke gemini-2.0-flash
- Update Claude ke claude-sonnet-4-20250514
- FREE_PROVIDER_KEYS: set untuk deteksi badge Gratis/Trial di app.py

Changelog v4.1:
- Tambah ai_generate_model_equation() untuk hasilkan persamaan model dari setiap analisis
- Tambah ai_interpret_regresi(), ai_interpret_ols(), ai_interpret_anova(),
  ai_interpret_mediasi(), ai_interpret_moderasi(), ai_interpret_sem()
- Semua interpretasi konsisten mengikuti format akademis
- ai_raw_interpret() diperkuat dengan fallback
"""

import json
import requests
import pandas as pd


# ─────────────────────────────────────────────────────────────────────────────
# System prompt akademis — digunakan di SEMUA fungsi interpretasi laporan
# ─────────────────────────────────────────────────────────────────────────────

ACADEMIC_SYSTEM_PROMPT = (
    "Anda adalah seorang Peneliti Data Senior, Akademisi, dan Statistikawan Ahli. "
    "Tugas Anda adalah menulis narasi laporan penelitian ilmiah yang orisinal, komprehensif, "
    "akademis, dan siap dipublikasikan (format jurnal/skripsi) berdasarkan data hasil analisis statistik. "

    "INSTRUKSI PENULISAN — WAJIB DIPATUHI SEPENUHNYA: "

    "1. ORISINALITAS & ANTI-TEMPLATE: Tuliskan narasi dengan gaya bahasa yang unik dan natural. "
    "HINDARI frasa klise AI seperti: 'penting untuk dicatat', 'secara keseluruhan', "
    "'dapat disimpulkan bahwa', 'perlu diperhatikan bahwa', 'menunjukkan bahwa', "
    "'hasil penelitian menunjukkan'. Gunakan struktur kalimat yang variatif dan dinamis. "

    "2. SINTESIS, BUKAN REPETISI: JANGAN memindahkan angka dari tabel secara mentah-mentah "
    "ke dalam kalimat. Berikan MAKNA dan SINTESIS. Contoh yang SALAH: 'Sebanyak 85,3% responden...'. "
    "Contoh yang BENAR: 'Mayoritas responden dalam sampel ini...'. "
    "Gunakan angka hanya untuk statistik kunci yang benar-benar memperkuat argumen. "

    "3. GAYA BAHASA AKADEMIS BAKU: "
    "- Gunakan Bahasa Indonesia formal, baku, dan objektif. "
    "- Hindari kata ganti orang pertama (aku, saya, kami, kita). "
    "- Gunakan sinonim dan padanan kata akademis untuk menghindari pengulangan. "
    "- Variasikan panjang dan struktur kalimat — campurkan kalimat pendek tegas dengan kalimat "
    "  panjang yang mengalir untuk ritme yang enak dibaca. "
    "- Pilih diksi yang presisi: hindari kata umum seperti 'bagus', 'jelek', 'besar', 'kecil' "
    "  tanpa kualifikasi statistik. "

    "4. MENULIS SEPERTI PENELITI ASLI: "
    "Bayangkan Anda sedang menyusun Bab 4 (Hasil) dan Bab 5 (Pembahasan) dari sebuah riset "
    "asli dengan target skor kemiripan Turnitin di bawah 10%. "
    "Argumentasikan MENGAPA suatu hasil terjadi, bukan hanya APA hasilnya. "
    "Hubungkan temuan statistik dengan implikasi nyata atau teoritis. "

    "5. FORMAT OUTPUT: "
    "- Gunakan format Markdown: **bold** untuk istilah kunci, heading dengan ##, "
    "  dan bullet points hanya jika diminta secara eksplisit. "
    "- Untuk narasi utama: tulis dalam paragraf mengalir, BUKAN bullet points. "
    "- Setiap paragraf harus memiliki fokus argumen yang jelas dan mengalir ke paragraf berikutnya."
)

# ─────────────────────────────────────────────────────────────────────────────
# Konstanta model per provider
# ─────────────────────────────────────────────────────────────────────────────

CLAUDE_MODEL    = "claude-sonnet-4-20250514"
CLAUDE_HAIKU    = "claude-haiku-4-5-20251001"
OPENAI_MODEL    = "gpt-4o"
OPENAI_MINI     = "gpt-4o-mini"
GEMINI_MODEL    = "gemini-2.0-flash"

GROQ_MODELS = {
    "⚡ Groq — Llama 3.3 70B":   "llama-3.3-70b-versatile",
    "⚡ Groq — Mixtral 8x7B":    "mixtral-8x7b-32768",
    "⚡ Groq — Gemma2 9B":       "gemma2-9b-it",
}

HF_MODELS = {
    "🤗 HuggingFace — Qwen 2.5 72B": "Qwen/Qwen2.5-72B-Instruct",
    "🤗 HuggingFace — Phi-3.5":      "microsoft/Phi-3.5-mini-instruct",
}

MISTRAL_MODELS = {
    "🌊 Mistral AI — Nemo":         "open-mistral-nemo",
    "🌊 Mistral AI — Mixtral 8x7B": "open-mixtral-8x7b",
}

COHERE_MODELS = {
    "🔗 Cohere — Command-R":  "command-r",
    "🔗 Cohere — Command-R+": "command-r-plus",
}

OPENROUTER_MODELS = {
    "🌐 OpenRouter — Llama 4 Scout": "meta-llama/llama-4-scout:free",
    "🌐 OpenRouter — DeepSeek R1":   "deepseek/deepseek-r1:free",
    "🌐 OpenRouter — Gemma 3 27B":   "google/gemma-3-27b-it:free",
}

ALL_PROVIDERS = [
    # ── ✅ Gratis ──────────────────────────────────────────────────────────────
    "⚡ Groq — Llama 3.3 70B",
    "⚡ Groq — Mixtral 8x7B",
    "⚡ Groq — Gemma2 9B",
    "✨ Gemini — 2.0 Flash",
    "🌐 OpenRouter — Llama 4 Scout",
    "🌐 OpenRouter — DeepSeek R1",
    "🌐 OpenRouter — Gemma 3 27B",
    "🤗 HuggingFace — Qwen 2.5 72B",
    "🤗 HuggingFace — Phi-3.5",
    # ── 🟡 Trial Gratis ────────────────────────────────────────────────────────
    "🌊 Mistral AI — Nemo",
    "🌊 Mistral AI — Mixtral 8x7B",
    "🔗 Cohere — Command-R",
    "🔗 Cohere — Command-R+",
    # ── 💳 Berbayar ────────────────────────────────────────────────────────────
    "🤖 Claude — Sonnet 4",
    "🤖 Claude — Haiku",
    "💬 ChatGPT — GPT-4o",
    "💬 ChatGPT — GPT-4o-mini",
]

# Digunakan app.py untuk menampilkan badge di sidebar
FREE_PROVIDER_KEYS  = {"Groq", "Gemini", "OpenRouter", "HuggingFace"}
TRIAL_PROVIDER_KEYS = {"Mistral", "Cohere"}

PROVIDER_KEY_INFO = {
    # Groq
    "⚡ Groq — Llama 3.3 70B":        ("Groq API Key (Gratis)",          "console.groq.com"),
    "⚡ Groq — Mixtral 8x7B":          ("Groq API Key (Gratis)",          "console.groq.com"),
    "⚡ Groq — Gemma2 9B":             ("Groq API Key (Gratis)",          "console.groq.com"),
    # Gemini
    "✨ Gemini — 2.0 Flash":           ("Gemini API Key (Gratis)",        "aistudio.google.com"),
    # OpenRouter
    "🌐 OpenRouter — Llama 4 Scout":   ("OpenRouter API Key (Gratis)",    "openrouter.ai"),
    "🌐 OpenRouter — DeepSeek R1":     ("OpenRouter API Key (Gratis)",    "openrouter.ai"),
    "🌐 OpenRouter — Gemma 3 27B":     ("OpenRouter API Key (Gratis)",    "openrouter.ai"),
    # HuggingFace
    "🤗 HuggingFace — Qwen 2.5 72B":  ("HuggingFace Token (Gratis)",     "huggingface.co/settings/tokens"),
    "🤗 HuggingFace — Phi-3.5":        ("HuggingFace Token (Gratis)",     "huggingface.co/settings/tokens"),
    # Mistral
    "🌊 Mistral AI — Nemo":            ("Mistral API Key (Trial Gratis)", "console.mistral.ai"),
    "🌊 Mistral AI — Mixtral 8x7B":    ("Mistral API Key (Trial Gratis)", "console.mistral.ai"),
    # Cohere
    "🔗 Cohere — Command-R":           ("Cohere API Key (Trial Gratis)",  "dashboard.cohere.com"),
    "🔗 Cohere — Command-R+":          ("Cohere API Key (Trial Gratis)",  "dashboard.cohere.com"),
    # Claude
    "🤖 Claude — Sonnet 4":            ("Anthropic API Key",              "console.anthropic.com"),
    "🤖 Claude — Haiku":               ("Anthropic API Key",              "console.anthropic.com"),
    # ChatGPT
    "💬 ChatGPT — GPT-4o":             ("OpenAI API Key",                 "platform.openai.com"),
    "💬 ChatGPT — GPT-4o-mini":        ("OpenAI API Key",                 "platform.openai.com"),
}


# ─────────────────────────────────────────────────────────────────────────────
# Core dispatcher
# ─────────────────────────────────────────────────────────────────────────────

def call_ai_api(
    prompt: str,
    system: str = "",
    provider: str = "⚡ Groq — Llama 3.3 70B",
    api_key: str = "",
) -> str:
    """
    Dispatcher utama ke semua provider AI.
    Routing berdasarkan emoji/nama provider di string.
    """
    if not api_key:
        return "❌ API Key tidak tersedia. Masukkan API Key di sidebar."

    _system = system if (system and system.strip()) else ACADEMIC_SYSTEM_PROMPT

    if "Groq" in provider:
        model_id = GROQ_MODELS.get(provider, "llama-3.3-70b-versatile")
        return _call_groq(prompt, _system, api_key, model_id)

    elif "Gemini" in provider:
        return _call_gemini(prompt, _system, api_key)

    elif "OpenRouter" in provider:
        model_id = OPENROUTER_MODELS.get(provider, "meta-llama/llama-4-scout:free")
        return _call_openrouter(prompt, _system, api_key, model_id)

    elif "HuggingFace" in provider:
        model_id = HF_MODELS.get(provider, "Qwen/Qwen2.5-72B-Instruct")
        return _call_huggingface(prompt, _system, api_key, model_id)

    elif "Mistral" in provider:
        model_id = MISTRAL_MODELS.get(provider, "open-mistral-nemo")
        return _call_mistral(prompt, _system, api_key, model_id)

    elif "Cohere" in provider:
        model_id = COHERE_MODELS.get(provider, "command-r-plus")
        return _call_cohere(prompt, _system, api_key, model_id)

    elif "Claude" in provider:
        model_id = CLAUDE_HAIKU if "Haiku" in provider else CLAUDE_MODEL
        return _call_claude(prompt, _system, api_key, model_id)

    elif "ChatGPT" in provider or "OpenAI" in provider or "GPT" in provider:
        model_id = OPENAI_MINI if "mini" in provider.lower() else OPENAI_MODEL
        return _call_openai(prompt, _system, api_key, model_id)

    return "❌ Provider AI tidak dikenali. Pilih provider lain di sidebar."


# ─────────────────────────────────────────────────────────────────────────────
# Provider implementations
# ─────────────────────────────────────────────────────────────────────────────

def _call_claude(prompt: str, system: str, api_key: str, model_id: str = None) -> str:
    model_id = model_id or CLAUDE_MODEL
    try:
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": model_id,
            "max_tokens": 2500,
            "system": system,
            "messages": [{"role": "user", "content": prompt}],
        }
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers, json=payload, timeout=60,
        )
        if resp.status_code == 200:
            return resp.json()["content"][0]["text"]
        elif resp.status_code == 401:
            return "❌ Anthropic API Key tidak valid."
        elif resp.status_code == 429:
            return "⚠️ Rate limit Anthropic tercapai. Tunggu sebentar lalu coba lagi."
        return f"❌ Error Claude ({resp.status_code}): {resp.text}"
    except Exception as e:
        return f"⚠️ Error Koneksi Claude: {str(e)}"


def _call_openai(prompt: str, system: str, api_key: str, model_id: str = None) -> str:
    model_id = model_id or OPENAI_MODEL
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model_id,
            "max_tokens": 2500,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user",   "content": prompt},
            ],
        }
        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers, json=payload, timeout=60,
        )
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"]
        elif resp.status_code == 401:
            return "❌ OpenAI API Key tidak valid."
        elif resp.status_code == 429:
            return "⚠️ Rate limit OpenAI tercapai. Tunggu sebentar lalu coba lagi."
        return f"❌ Error OpenAI ({resp.status_code}): {resp.text}"
    except Exception as e:
        return f"⚠️ Error Koneksi OpenAI: {str(e)}"


def _call_gemini(prompt: str, system: str, api_key: str) -> str:
    try:
        full_prompt = f"System: {system}\n\nUser: {prompt}" if system else prompt
        payload = {
            "contents": [{"parts": [{"text": full_prompt}]}],
            "generationConfig": {"maxOutputTokens": 2500, "temperature": 0.7},
        }
        model_name = GEMINI_MODEL
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model_name}:generateContent?key={api_key}"
        )
        resp = requests.post(url, json=payload, timeout=60)
        if resp.status_code == 200:
            result = resp.json()
            if "candidates" in result and result["candidates"][0].get("content"):
                return result["candidates"][0]["content"]["parts"][0]["text"]
            return "⚠️ Respons Gemini kosong."
        elif resp.status_code == 400:
            return "❌ Gemini: permintaan tidak valid. Periksa API Key atau panjang prompt."
        elif resp.status_code == 403:
            return "❌ Gemini API Key tidak valid atau quota habis."
        elif resp.status_code == 404:
            return f"❌ Error 404: Model '{model_name}' tidak tersedia di Gemini."
        return f"⚠️ Error Gemini ({resp.status_code}): {resp.text}"
    except Exception as e:
        return f"⚠️ Error Koneksi Gemini: {str(e)}"


def _call_openrouter(prompt: str, system: str, api_key: str, model_id: str) -> str:
    """OpenRouter — gateway ke ratusan model, termasuk model :free."""
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://ruang-statistika.streamlit.app",
            "X-Title": "Ruang Statistika",
        }
        payload = {
            "model": model_id,
            "max_tokens": 2500,
            "temperature": 0.7,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user",   "content": prompt},
            ],
        }
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers, json=payload, timeout=90,
        )
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"]
        elif resp.status_code == 401:
            return "❌ OpenRouter API Key tidak valid."
        elif resp.status_code == 429:
            return "⚠️ Rate limit OpenRouter tercapai. Tunggu sebentar lalu coba lagi."
        elif resp.status_code == 402:
            return "⚠️ Saldo OpenRouter habis. Topup di openrouter.ai atau pakai model :free."
        return f"❌ Error OpenRouter ({resp.status_code}): {resp.text[:300]}"
    except Exception as e:
        return f"⚠️ Error Koneksi OpenRouter: {str(e)}"


def _call_mistral(prompt: str, system: str, api_key: str, model_id: str) -> str:
    """Mistral AI — API endpoint resmi (trial gratis tersedia)."""
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model_id,
            "max_tokens": 2500,
            "temperature": 0.7,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user",   "content": prompt},
            ],
        }
        resp = requests.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers=headers, json=payload, timeout=60,
        )
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"]
        elif resp.status_code == 401:
            return "❌ Mistral API Key tidak valid. Daftar di console.mistral.ai"
        elif resp.status_code == 429:
            return "⚠️ Rate limit Mistral AI tercapai. Tunggu sebentar lalu coba lagi."
        return f"❌ Error Mistral ({resp.status_code}): {resp.text[:300]}"
    except Exception as e:
        return f"⚠️ Error Koneksi Mistral AI: {str(e)}"


def _call_cohere(prompt: str, system: str, api_key: str, model_id: str) -> str:
    """Cohere — Command-R & Command-R+ (trial gratis tersedia)."""
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        # Cohere Chat API v2
        payload = {
            "model": model_id,
            "max_tokens": 2500,
            "temperature": 0.7,
            "system": system,
            "messages": [
                {"role": "user", "content": prompt},
            ],
        }
        resp = requests.post(
            "https://api.cohere.com/v2/chat",
            headers=headers, json=payload, timeout=60,
        )
        if resp.status_code == 200:
            data = resp.json()
            # Cohere v2 response: message.content[0].text
            try:
                return data["message"]["content"][0]["text"]
            except (KeyError, IndexError):
                return str(data)
        elif resp.status_code == 401:
            return "❌ Cohere API Key tidak valid. Daftar di dashboard.cohere.com"
        elif resp.status_code == 429:
            return "⚠️ Rate limit Cohere tercapai. Tunggu sebentar lalu coba lagi."
        return f"❌ Error Cohere ({resp.status_code}): {resp.text[:300]}"
    except Exception as e:
        return f"⚠️ Error Koneksi Cohere: {str(e)}"


def _call_groq(prompt: str, system: str, api_key: str, model_id: str) -> str:
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model_id,
            "max_tokens": 2500,
            "temperature": 0.7,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user",   "content": prompt},
            ],
        }
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers, json=payload, timeout=60,
        )
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"]
        elif resp.status_code == 429:
            return "⚠️ Rate limit Groq tercapai. Tunggu sebentar lalu coba lagi."
        elif resp.status_code == 401:
            return "❌ Groq API Key tidak valid."
        return f"❌ Error Groq ({resp.status_code}): {resp.text}"
    except Exception as e:
        return f"⚠️ Error Koneksi Groq: {str(e)}"


def _call_huggingface(prompt: str, system: str, api_key: str, model_id: str) -> str:
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model_id,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user",   "content": prompt},
            ],
            "max_tokens": 2500,
            "temperature": 0.7,
        }
        resp = requests.post(
            "https://router.huggingface.co/v1/chat/completions",
            headers=headers, json=payload, timeout=90,
        )
        if resp.status_code == 200:
            data = resp.json()
            if "choices" in data:
                return data["choices"][0]["message"]["content"]
            if isinstance(data, list) and data:
                return data[0].get("generated_text", str(data))
            return str(data)
        elif resp.status_code == 401:
            return "❌ HuggingFace Token tidak valid."
        elif resp.status_code == 404:
            return f"❌ Model '{model_id}' tidak mendukung Serverless Inference."
        elif resp.status_code == 503:
            return "⏳ Model sedang dimuat (cold start). Tunggu 20-30 detik lalu coba lagi."
        elif resp.status_code == 429:
            return "⚠️ Batas pemakaian harian HuggingFace tercapai."
        return f"❌ Error HuggingFace ({resp.status_code}): {resp.text[:300]}"
    except Exception as e:
        return f"⚠️ Error Koneksi HuggingFace: {str(e)}"


# ─────────────────────────────────────────────────────────────────────────────
# BARU: Generate persamaan model sesuai hasil penelitian
# ─────────────────────────────────────────────────────────────────────────────

def ai_generate_model_equation(
    analysis_type: str,
    result_data: dict,
    api_key: str,
    provider: str,
) -> str:
    """
    Hasilkan persamaan/model matematis berdasarkan hasil analisis.
    Digunakan di docx_helpers untuk menyisipkan persamaan model ke laporan.

    analysis_type: 'regresi' | 'ols_plus' | 'logistik' | 'mediasi' |
                   'moderasi' | 'anova' | 'sem'
    result_data  : dict data hasil analisis (dari session_state)
    """
    if not api_key:
        return ""

    if analysis_type in ("regresi", "ols_plus"):
        dep_var  = result_data.get("y", "Y")
        ind_vars = result_data.get("x", [])
        coef_table = result_data.get("coef_table")
        r2       = result_data.get("r2", 0)
        adj_r2   = result_data.get("adj_r2", 0)
        f_pvalue = result_data.get("f_pvalue", 1)

        coef_str = ""
        if coef_table is not None and hasattr(coef_table, "iterrows"):
            rows = []
            for _, row in coef_table.iterrows():
                param = row.get("Parameter", row.iloc[0])
                coef  = row.get("β (Koefisien)", row.get("Koefisien (β)", row.iloc[1]))
                pval  = row.get("p-value", "?")
                sig   = row.get("Signifikan", "")
                rows.append(f"  {param}: β = {coef}, p = {pval} {sig}")
            coef_str = "\n".join(rows)

        prompt = f"""
Berdasarkan hasil regresi linier berikut:
Variabel dependen (Y): {dep_var}
Variabel independen (X): {', '.join(ind_vars)}

Koefisien:
{coef_str}

R² = {r2:.4f}, R² Adjusted = {adj_r2:.4f}, F p-value = {f_pvalue:.4f}

Tuliskan:
1. Persamaan regresi matematis lengkap dalam notasi standar:
   Ŷ = a + b₁X₁ + b₂X₂ + ... (gunakan nilai koefisien aktual)
2. Persamaan dalam format naratif: "Persamaan regresi dalam penelitian ini adalah..."
3. Interpretasi singkat persamaan (1 paragraf) — variabel mana yang paling berpengaruh?

Gunakan Bahasa Indonesia. Jangan tambahkan informasi di luar data yang diberikan.
"""

    elif analysis_type == "logistik":
        dep_var  = result_data.get("y", "Y")
        ind_vars = result_data.get("x", [])
        coef_table = result_data.get("coef_table") or result_data.get("odds_df")
        auc      = result_data.get("auc", 0)
        pseudo_r2 = result_data.get("pseudo_r2", 0)

        coef_str = ""
        if coef_table is not None and hasattr(coef_table, "iterrows"):
            rows = []
            for _, row in coef_table.iterrows():
                param = row.iloc[0]
                beta  = row.get("β", row.iloc[1] if len(row) > 1 else "?")
                or_   = row.get("OR (exp β)", "?")
                pval  = row.get("p-value", "?")
                rows.append(f"  {param}: β = {beta}, OR = {or_}, p = {pval}")
            coef_str = "\n".join(rows)

        prompt = f"""
Berdasarkan hasil regresi logistik berikut:
Variabel dependen (Y, biner): {dep_var}
Variabel independen: {', '.join(ind_vars)}

Koefisien & Odds Ratio:
{coef_str}

AUC = {auc:.4f}, Pseudo R² (McFadden) = {pseudo_r2:.4f}

Tuliskan:
1. Model persamaan logistik: ln[P/(1-P)] = a + b₁X₁ + b₂X₂ + ... (nilai aktual)
2. Interpretasi odds ratio yang signifikan (1 paragraf naratif)
3. Kemampuan prediksi model berdasarkan AUC

Gunakan Bahasa Indonesia. Format akademis skripsi/tesis.
"""

    elif analysis_type == "mediasi":
        x = result_data.get("x", "X")
        m = result_data.get("m", "M")
        y = result_data.get("y", "Y")
        med_info = result_data.get("med_info", {})
        indirect = result_data.get("indirect_effect",
                   med_info.get("Indirect (a×b)", "?"))
        direct   = result_data.get("direct_effect",
                   med_info.get("c' (direct X→Y)", "?"))
        total    = result_data.get("total_effect",
                   med_info.get("c (total X→Y)", "?"))
        boot_ci  = result_data.get("bootstrap_ci", [])
        jenis    = result_data.get("jenis_mediasi", "")

        prompt = f"""
Berdasarkan hasil analisis mediasi:
X (independen): {x}
M (mediator)  : {m}
Y (dependen)  : {y}

Jalur:
- Efek tidak langsung (a×b) = {indirect}
- Efek langsung (c') = {direct}
- Efek total (c) = {total}
- Bootstrap CI = {boot_ci if boot_ci else 'tidak tersedia'}
- Jenis mediasi: {jenis if jenis else 'belum ditentukan'}

Tuliskan:
1. Diagram jalur dalam notasi: {x} → {m} → {y}, dengan nilai koefisien jalur
2. Pernyataan kesimpulan mediasi sesuai Baron & Kenny / Hayes: apakah mediasi penuh,
   sebagian, atau tidak ada mediasi?
3. Paragraf narasi akademis tentang model mediasi ini (3-4 kalimat)

Gunakan Bahasa Indonesia. Format skripsi/jurnal.
"""

    elif analysis_type == "moderasi":
        x = result_data.get("x", "X")
        z = result_data.get("z", "Z")
        y = result_data.get("y", "Y")
        coef_table = result_data.get("coef_table")
        r2   = result_data.get("r2", 0)
        b0   = result_data.get("b0", "a")
        b1   = result_data.get("b1", "b₁")
        b2   = result_data.get("b2", "b₂")
        b3   = result_data.get("b3", "b₃")
        jn   = result_data.get("johnson_neyman")

        prompt = f"""
Berdasarkan hasil analisis moderasi/interaksi:
X (independen): {x}
Z (moderator) : {z}
Y (dependen)  : {y}

Persamaan model:
Ŷ = {b0} + {b1}·{x} + {b2}·{z} + {b3}·({x}×{z})

R² = {r2:.4f}
Johnson-Neyman point = {jn if jn is not None else 'tidak tersedia'}

Tuliskan:
1. Persamaan moderasi lengkap dengan nilai koefisien aktual
2. Interpretasi efek interaksi ({x}×{z}): apakah moderasi signifikan?
3. Jika ada Johnson-Neyman point, jelaskan maknanya
4. Paragraf narasi akademis model moderasi (3-4 kalimat)

Gunakan Bahasa Indonesia. Format skripsi/jurnal.
"""

    elif analysis_type == "anova":
        num_col  = result_data.get("num_col", "Y")
        cat_col  = result_data.get("cat_col", "Kelompok")
        f_stat   = result_data.get("f_stat", "?")
        p_value  = result_data.get("p_value", "?")
        eta2     = result_data.get("eta_squared")
        n_groups = result_data.get("n_groups", "?")
        posthoc  = result_data.get("posthoc_method", "Tukey HSD")

        prompt = f"""
Berdasarkan hasil ANOVA satu arah:
Variabel dependen: {num_col}
Variabel kelompok: {cat_col}
Jumlah kelompok  : {n_groups}

F-statistik = {f_stat}, p-value = {p_value}
Eta squared (η²) = {eta2 if eta2 is not None else 'tidak tersedia'}
Post-hoc        = {posthoc}

Tuliskan:
1. Hipotesis statistik: H₀ dan H₁ secara formal
2. Keputusan statistik berdasarkan F dan p-value
3. Ukuran efek (η²) dan interpretasinya (kecil/sedang/besar — Cohen, 1988)
4. Paragraf narasi kesimpulan ANOVA (3-4 kalimat akademis)

Gunakan Bahasa Indonesia. Format skripsi/jurnal.
"""

    elif analysis_type == "sem":
        fit_df   = result_data.get("fit_indices")
        load_df  = result_data.get("loadings")
        path_df  = result_data.get("path_estimates")

        fit_str  = fit_df.to_string(index=False) if fit_df is not None else "tidak tersedia"
        load_str = load_df.to_string(index=False) if load_df is not None else "tidak tersedia"
        path_str = path_df.to_string(index=False) if path_df is not None else "tidak tersedia"

        prompt = f"""
Berdasarkan hasil SEM & CFA:

INDEKS FIT MODEL:
{fit_str}

FACTOR LOADINGS:
{load_str}

ESTIMASI JALUR:
{path_str}

Tuliskan:
1. Evaluasi kecocokan model (goodness of fit): apakah model fit?
   Acuan: CFI ≥ 0.90, RMSEA ≤ 0.08, SRMR ≤ 0.08, χ²/df ≤ 2.0
2. Interpretasi factor loadings: indikator mana yang paling kuat?
3. Hasil estimasi jalur struktural utama
4. Paragraf narasi model SEM/CFA (3-4 kalimat akademis)

Gunakan Bahasa Indonesia. Format jurnal/tesis.
"""

    else:
        # Fallback generic
        prompt = f"""
Berdasarkan data analisis berikut:
{json.dumps(result_data, default=str, indent=2)[:2000]}

Tuliskan model/persamaan hasil penelitian dan interpretasinya dalam Bahasa Indonesia.
Format: narasi akademis 3-4 paragraf.
"""

    return call_ai_api(prompt, system="", api_key=api_key, provider=provider)


# ─────────────────────────────────────────────────────────────────────────────
# Domain-specific helpers (existing + new)
# ─────────────────────────────────────────────────────────────────────────────

def ai_interpret_descriptive(stats_df: pd.DataFrame, norm_df: pd.DataFrame,
                              api_key: str, provider: str) -> str:
    stats_json = stats_df.to_dict(orient="records")
    norm_json  = norm_df.to_dict(orient="records") if not norm_df.empty else []
    prompt = f"""
Berikut adalah hasil statistik deskriptif dari dataset penelitian:

STATISTIK DESKRIPTIF:
{json.dumps(stats_json, ensure_ascii=False, indent=2)}

UJI NORMALITAS SHAPIRO-WILK:
{json.dumps(norm_json, ensure_ascii=False, indent=2)}

Berikan interpretasi komprehensif dalam Bahasa Indonesia mencakup:
1. Gambaran umum distribusi setiap variabel (mean, variabilitas, skewness)
2. Hasil uji normalitas dan implikasinya terhadap pemilihan uji statistik selanjutnya
3. Rekomendasi analisis yang tepat berdasarkan distribusi data
Tulis dalam 3-4 paragraf yang mengalir, gaya akademis namun mudah dipahami.
"""
    return call_ai_api(prompt, system="", api_key=api_key, provider=provider)


def ai_interpret_validity_reliability(val_df: pd.DataFrame, alpha_val: float,
                                       r_tabel: float, api_key: str, provider: str) -> str:
    val_json = val_df.to_dict(orient="records") if val_df is not None else []
    prompt = f"""
Hasil uji validitas dan reliabilitas instrumen penelitian:

UJI VALIDITAS PEARSON (r-tabel = {r_tabel}):
{json.dumps(val_json, ensure_ascii=False, indent=2)}

CRONBACH'S ALPHA: {alpha_val}

Berikan interpretasi dalam Bahasa Indonesia mencakup:
1. Evaluasi kualitas butir-butir instrumen (mana yang valid dan tidak valid)
2. Analisis tingkat reliabilitas berdasarkan standar Ghozali (2018)
3. Rekomendasi konkret: apakah instrumen layak digunakan? Butir mana yang perlu direvisi?
Tulis dalam 3-4 paragraf, gaya penulisan skripsi/laporan penelitian.
"""
    return call_ai_api(prompt, system="", api_key=api_key, provider=provider)


def ai_interpret_correlation(corr_matrix: pd.DataFrame, api_key: str, provider: str) -> str:
    corr_json = corr_matrix.round(3).to_dict()
    prompt = f"""
Berikut matriks korelasi Pearson antar variabel penelitian:

{json.dumps(corr_json, ensure_ascii=False, indent=2)}

Berikan interpretasi mendalam dalam Bahasa Indonesia mencakup:
1. Identifikasi pasangan variabel dengan korelasi kuat, sedang, dan lemah
2. Pola hubungan yang menarik atau tidak terduga
3. Implikasi terhadap analisis lebih lanjut (risiko multikolinearitas, dll)
4. Rekomendasi variabel yang paling relevan untuk fokus analisis
Tulis dalam 3-4 paragraf yang informatif dan akademis.
"""
    return call_ai_api(prompt, system="", api_key=api_key, provider=provider)


def ai_interpret_regresi(result_data: dict, api_key: str, provider: str) -> str:
    """Interpretasi khusus regresi linier — dipanggil dari modul regresi.py."""
    dep_var    = result_data.get("y", "Y")
    ind_vars   = result_data.get("x", [])
    r2         = result_data.get("r2", 0)
    adj_r2     = result_data.get("adj_r2", 0)
    f_pvalue   = result_data.get("f_pvalue", 1)
    rmse       = result_data.get("rmse", 0)
    coef_table = result_data.get("coef_table")
    coef_str   = coef_table.to_string(index=False) if coef_table is not None else ""

    sig = "signifikan" if float(f_pvalue) < 0.05 else "tidak signifikan"

    prompt = f"""
Hasil regresi linier untuk variabel dependen: {dep_var}
Variabel independen: {', '.join(ind_vars)}

RINGKASAN MODEL:
- R² = {r2:.4f} (model menjelaskan {r2*100:.1f}% variansi {dep_var})
- R² Adjusted = {adj_r2:.4f}
- F-test: {sig} (p = {f_pvalue:.4f})
- RMSE = {rmse:.4f}

KOEFISIEN REGRESI:
{coef_str}

Berikan interpretasi komprehensif dalam Bahasa Indonesia:
1. Kualitas dan signifikansi model (R², F-test) — apakah model baik?
2. Interpretasi koefisien yang signifikan beserta maknanya secara substantif
3. Persamaan regresi lengkap dan artinya bagi penelitian
4. Rekomendasi: apakah asumsi klasik perlu diperiksa? Analisis lanjutan apa?
Format: 4 paragraf akademis. Jangan gunakan bullet points.
"""
    return call_ai_api(prompt, system="", api_key=api_key, provider=provider)


def ai_interpret_ols(result_data: dict, api_key: str, provider: str) -> str:
    """Interpretasi OLS+ dengan uji asumsi klasik."""
    dep_var    = result_data.get("y", "Y")
    ind_vars   = result_data.get("x", [])
    r2         = result_data.get("r2", 0)
    adj_r2     = result_data.get("adj_r2", 0)
    f_pvalue   = result_data.get("f_pvalue", 1)
    dw         = result_data.get("durbin_watson")
    vif_max    = result_data.get("vif_max")
    white_p    = result_data.get("white_pvalue")
    shapiro_p  = result_data.get("shapiro_residual_p")
    coef_table = result_data.get("coef_table")
    coef_str   = coef_table.to_string(index=False) if coef_table is not None else ""

    asumsi_lines = []
    if dw is not None:
        ok = "✓ terpenuhi (DW dalam 1.5–2.5)" if 1.5 <= float(dw) <= 2.5 else "⚠️ perlu diperiksa"
        asumsi_lines.append(f"- Autokorelasi (Durbin-Watson = {dw:.4f}): {ok}")
    if vif_max is not None:
        ok = "✓ terpenuhi (VIF ≤ 10)" if float(vif_max) <= 10 else "⚠️ ada multikolinearitas"
        asumsi_lines.append(f"- Multikolinearitas (VIF maks = {vif_max:.2f}): {ok}")
    if white_p is not None:
        ok = "✓ homoskedastisitas" if float(white_p) >= 0.05 else "⚠️ ada heteroskedastisitas"
        asumsi_lines.append(f"- Heteroskedastisitas (White test p = {white_p:.4f}): {ok}")
    if shapiro_p is not None:
        ok = "✓ residual normal" if float(shapiro_p) >= 0.05 else "⚠️ residual tidak normal"
        asumsi_lines.append(f"- Normalitas residual (Shapiro p = {shapiro_p:.4f}): {ok}")

    asumsi_str = "\n".join(asumsi_lines) if asumsi_lines else "Data asumsi tidak tersedia."

    prompt = f"""
Hasil regresi OLS+ untuk variabel dependen: {dep_var}
Variabel independen: {', '.join(ind_vars)}

MODEL:
- R² = {r2:.4f}, R² Adjusted = {adj_r2:.4f}
- F p-value = {f_pvalue:.4f}

KOEFISIEN:
{coef_str}

UJI ASUMSI KLASIK:
{asumsi_str}

Berikan interpretasi komprehensif dalam Bahasa Indonesia:
1. Kualitas model dan signifikansi keseluruhan (R², F-test)
2. Interpretasi koefisien signifikan dan maknanya
3. Evaluasi uji asumsi klasik satu per satu — apakah semua terpenuhi?
4. Rekomendasi: jika ada asumsi yang dilanggar, apa solusinya?
Format: 4 paragraf akademis. Jangan bullet points.
"""
    return call_ai_api(prompt, system="", api_key=api_key, provider=provider)


def ai_interpret_logistik(result_data: dict, api_key: str, provider: str) -> str:
    """Interpretasi regresi logistik."""
    dep_var    = result_data.get("y", "Y")
    ind_vars   = result_data.get("x", [])
    auc        = result_data.get("auc", 0)
    pseudo_r2  = result_data.get("pseudo_r2", 0)
    aic        = result_data.get("aic", 0)
    bic        = result_data.get("bic", 0)
    odds_df    = result_data.get("odds_df") 
    if odds_df is None: 
        odds_df = result_data.get("coef_table")
    odds_str   = odds_df.to_string(index=False) if odds_df is not None else ""
    cr         = result_data.get("cr", {})

    auc_interp = (
        "sangat baik (AUC ≥ 0.90)" if auc >= 0.90 else
        "baik (AUC ≥ 0.80)" if auc >= 0.80 else
        "cukup (AUC ≥ 0.70)" if auc >= 0.70 else "lemah (AUC < 0.70)"
    )

    prompt = f"""
Hasil regresi logistik biner:
Variabel dependen (Y, biner 0/1): {dep_var}
Variabel independen: {', '.join(ind_vars)}

MODEL FIT:
- AUC = {auc:.4f} → kualitas model: {auc_interp}
- Pseudo R² (McFadden) = {pseudo_r2:.4f}
- AIC = {aic:.2f}, BIC = {bic:.2f}

KOEFISIEN & ODDS RATIO:
{odds_str}

CLASSIFICATION:
Precision/Recall/F1 tersedia dari output model.

Berikan interpretasi komprehensif dalam Bahasa Indonesia:
1. Kualitas model (AUC, Pseudo R²) — apakah model prediktif yang baik?
2. Interpretasi odds ratio yang signifikan — variabel mana yang meningkatkan/menurunkan
   probabilitas outcome?
3. Evaluasi performa klasifikasi
4. Rekomendasi dan limitasi model untuk penelitian
Format: 4 paragraf akademis. Jangan bullet points.
"""
    return call_ai_api(prompt, system="", api_key=api_key, provider=provider)


def ai_interpret_anova_full(result_data: dict, api_key: str, provider: str) -> str:
    """Interpretasi ANOVA lengkap dengan post-hoc."""
    num_col    = result_data.get("num_col", "Y")
    cat_col    = result_data.get("cat_col", "Kelompok")
    f_stat     = result_data.get("f_stat", "?")
    p_value    = result_data.get("p_value", "?")
    eta2       = result_data.get("eta_squared")
    anova_df   = result_data.get("anova_table")
    posthoc_df = result_data.get("posthoc_table")
    group_stats = result_data.get("group_stats")
    method     = result_data.get("test_name", "One-Way ANOVA")
    posthoc_m  = result_data.get("posthoc_method", "Tukey HSD")

    anova_str  = anova_df.to_string(index=False) if anova_df is not None else ""
    posthoc_str = posthoc_df.to_string(index=False) if posthoc_df is not None else "tidak tersedia"
    group_str  = group_stats.to_string(index=False) if group_stats is not None else ""

    eta_interp = ""
    if eta2 is not None:
        eta_interp = (
            "efek kecil" if float(eta2) < 0.06 else
            "efek sedang" if float(eta2) < 0.14 else "efek besar"
        )

    prompt = f"""
Hasil {method} untuk variabel dependen: {num_col}
Variabel kelompok: {cat_col}

TABEL ANOVA:
{anova_str}

STATISTIK PER KELOMPOK:
{group_str}

F-statistik = {f_stat}, p-value = {p_value}
Eta squared (η²) = {eta2:.4f if eta2 is not None else '?'} ({eta_interp})

POST-HOC ({posthoc_m}):
{posthoc_str}

Berikan interpretasi komprehensif dalam Bahasa Indonesia:
1. Hasil uji F dan keputusan H₀ — apakah ada perbedaan signifikan antar kelompok?
2. Ukuran efek (η²) dan maknanya praktis (Cohen, 1988)
3. Hasil post-hoc: kelompok mana yang berbeda secara signifikan? (jika ada)
4. Implikasi temuan bagi penelitian dan rekomendasi
Format: 4 paragraf akademis. Jangan bullet points.
"""
    return call_ai_api(prompt, system="", api_key=api_key, provider=provider)


def ai_interpret_mediasi_full(result_data: dict, api_key: str, provider: str) -> str:
    """Interpretasi analisis mediasi lengkap."""
    x        = result_data.get("x", "X")
    m        = result_data.get("m", "M")
    y        = result_data.get("y", "Y")
    med_info = result_data.get("med_info", {})
    boot     = result_data.get("boot", {})
    indirect = result_data.get("indirect_effect",
               med_info.get("Indirect (a×b)", "?"))
    direct   = result_data.get("direct_effect",
               med_info.get("c' (direct X→Y)", "?"))
    total    = result_data.get("total_effect",
               med_info.get("c (total X→Y)", "?"))
    jenis    = result_data.get("jenis_mediasi", "")
    boot_ci  = result_data.get("bootstrap_ci",
               [boot.get("ci_lower"), boot.get("ci_upper")])
    sobel_p  = med_info.get("Sobel p-value")

    ci_str = (f"[{boot_ci[0]:.4f}, {boot_ci[1]:.4f}]"
              if boot_ci and None not in boot_ci else "tidak tersedia")
    sig_med = ""
    if boot_ci and None not in boot_ci:
        lo, hi = float(boot_ci[0]), float(boot_ci[1])
        sig_med = "signifikan (CI tidak mencakup nol)" if (lo > 0 or hi < 0) else \
                  "tidak signifikan (CI mencakup nol)"

    prompt = f"""
Hasil analisis mediasi (Preacher & Hayes):
X (independen): {x}
M (mediator)  : {m}
Y (dependen)  : {y}

JALUR:
- a (X→M)         = {med_info.get("a (X→M)", "?")}
- b (M→Y|X)       = {med_info.get("b (M→Y|X)", "?")}
- c' (langsung)   = {direct}
- c (total)       = {total}
- a×b (tidak langsung) = {indirect}

BOOTSTRAP CI (5000 sampel): {ci_str} — {sig_med}
Sobel p-value: {sobel_p if sobel_p else 'tidak tersedia'}
Jenis mediasi: {jenis if jenis else 'belum ditentukan'}

Berikan interpretasi komprehensif dalam Bahasa Indonesia:
1. Interpretasi setiap jalur (a, b, c, c') dan maknanya
2. Apakah efek tidak langsung signifikan? (berdasarkan Bootstrap CI)
3. Jenis mediasi (penuh/sebagian/tidak ada) dan alasan berdasarkan Baron & Kenny / Hayes
4. Implikasi teoritis dan praktis dari hasil mediasi
Format: 4 paragraf akademis. Jangan bullet points.
"""
    return call_ai_api(prompt, system="", api_key=api_key, provider=provider)


def ai_interpret_moderasi_full(result_data: dict, api_key: str, provider: str) -> str:
    """Interpretasi analisis moderasi lengkap."""
    x        = result_data.get("x", "X")
    z        = result_data.get("z", "Z")
    y        = result_data.get("y", "Y")
    r2       = result_data.get("r2", 0)
    adj_r2   = result_data.get("adj_r2", 0)
    b0       = result_data.get("b0", "?")
    b1       = result_data.get("b1", "?")
    b2       = result_data.get("b2", "?")
    b3       = result_data.get("b3", "?")
    jn       = result_data.get("johnson_neyman")
    coef_df  = result_data.get("coef_table")
    coef_str = coef_df.to_string(index=False) if coef_df is not None else ""

    prompt = f"""
Hasil analisis moderasi/interaksi:
X (independen): {x}
Z (moderator) : {z}
Y (dependen)  : {y}

MODEL: Ŷ = {b0} + {b1}·{x} + {b2}·{z} + {b3}·({x}×{z})
R² = {r2:.4f}, R² Adj = {adj_r2:.4f}

KOEFISIEN:
{coef_str}

JOHNSON-NEYMAN POINT: {jn:.4f if jn is not None else 'tidak tersedia'}

Berikan interpretasi komprehensif dalam Bahasa Indonesia:
1. Apakah efek interaksi (X×Z) signifikan? Apa artinya?
2. Interpretasi substantif: bagaimana {z} memoderasi hubungan {x}→{y}?
3. Jika ada Johnson-Neyman point, jelaskan rentang nilai {z} di mana efek {x} signifikan
4. Implikasi teoritis dan rekomendasi praktis
Format: 4 paragraf akademis. Jangan bullet points.
"""
    return call_ai_api(prompt, system="", api_key=api_key, provider=provider)


def ai_interpret_sem_full(result_data: dict, api_key: str, provider: str) -> str:
    """Interpretasi SEM & CFA lengkap."""
    fit_df   = result_data.get("fit_indices")
    load_df  = result_data.get("loadings")
    path_df  = result_data.get("path_estimates")
    fit_str  = fit_df.to_string(index=False) if fit_df is not None else "tidak tersedia"
    load_str = load_df.to_string(index=False) if load_df is not None else "tidak tersedia"
    path_str = path_df.to_string(index=False) if path_df is not None else "tidak tersedia"

    prompt = f"""
Hasil Structural Equation Modeling (SEM) & CFA:

INDEKS KECOCOKAN MODEL:
{fit_str}
Acuan: CFI ≥ 0.90, TLI ≥ 0.90, RMSEA ≤ 0.08, SRMR ≤ 0.08, χ²/df ≤ 2.0 (Hair et al., 2010)

FACTOR LOADINGS (CFA):
{load_str}
Acuan loading ≥ 0.50 (Hair et al., 2010)

ESTIMASI JALUR STRUKTURAL:
{path_str}

Berikan interpretasi komprehensif dalam Bahasa Indonesia:
1. Evaluasi kecocokan model (fit indices) — apakah model fit dengan data?
2. Kualitas pengukuran CFA: loading mana yang kuat/lemah?
3. Hasil jalur struktural: hipotesis mana yang didukung?
4. Kesimpulan keseluruhan dan limitasi model
Format: 4 paragraf akademis. Jangan bullet points.
"""
    return call_ai_api(prompt, system="", api_key=api_key, provider=provider)


def ai_interpret_efa_full(result_data: dict, api_key: str, provider: str) -> str:
    """
    Interpretasi mendalam hasil EFA untuk laporan.
    Dipanggil dari export.py via _build_module_ai_prompt (mod_key='efa').
    """
    kmo        = result_data.get("kmo", "–")
    kmo_label  = result_data.get("kmo_label", "–")
    bart_p     = result_data.get("bartlett_p", "–")
    n_factors  = result_data.get("n_factors", "–")
    rotation   = result_data.get("rotation", "varimax")
    total_var  = result_data.get("total_var", "–")

    loading_df = result_data.get("loading_df")
    loading_info = ""
    if loading_df is not None and hasattr(loading_df, "to_string"):
        try:
            loading_info = loading_df.head(15).to_string(index=False)
        except Exception:
            loading_info = ""

    variance_df = result_data.get("variance_df")
    variance_info = ""
    if variance_df is not None and hasattr(variance_df, "to_string"):
        try:
            variance_info = variance_df.to_string(index=False)
        except Exception:
            variance_info = ""

    # Jika sudah ada teks AI dari sesi EFA, gunakan langsung
    ai_text_cached = result_data.get("ai_text", "")
    if ai_text_cached:
        return ai_text_cached

    prompt = f"""
Anda adalah statistikawan akademis. Berikut ringkasan hasil Analisis Faktor Eksploratori (EFA):

── UJI KELAYAKAN ───────────────────────────────────────────
KMO Overall = {kmo} → Kategori: {kmo_label}
Bartlett's Test p-value = {bart_p}

── STRUKTUR FAKTOR ─────────────────────────────────────────
Jumlah faktor yang diekstrak: {n_factors}
Metode rotasi: {rotation.capitalize()}
Total variance explained: {total_var:.1f}% (jika numerik)

── FACTOR LOADING MATRIX ───────────────────────────────────
{loading_info or '(tidak tersedia)'}

── VARIANCE EXPLAINED PER FAKTOR ──────────────────────────
{variance_info or '(tidak tersedia)'}

Tugas: Buat interpretasi EFA yang komprehensif dalam Bahasa Indonesia untuk laporan akademis:
1. Evaluasi kelayakan data (KMO & Bartlett) — apakah data layak untuk EFA?
2. Jumlah faktor yang tepat dan dasar pengambilan keputusan (Kaiser criterion, cumulative variance ≥ 60%)
3. Interpretasi struktur faktor — variabel mana memuat faktor apa? Adakah makna konseptual?
4. Rekomendasi: apakah perlu CFA berikutnya? Variabel mana yang perlu ditinjau ulang?

Format: 4 paragraf akademis formal. Jangan bullet points. Bahasa Indonesia baku.
"""
    return call_ai_api(prompt, system="", api_key=api_key, provider=provider)


def ai_chat_analyst(user_question: str, context: dict, api_key: str, provider: str) -> str:
    ctx_parts = []
    if context.get("desc_df") is not None and not context["desc_df"].empty:
        ctx_parts.append("STATISTIK DESKRIPTIF:\n" + context["desc_df"].to_string(index=False))
    if context.get("norm_df") is not None and not context["norm_df"].empty:
        ctx_parts.append("UJI NORMALITAS:\n" + context["norm_df"].to_string(index=False))
    if context.get("val_df") is not None and not context["val_df"].empty:
        ctx_parts.append("VALIDITAS:\n" + context["val_df"].to_string(index=False))
    if context.get("alpha_result") is not None:
        ctx_parts.append(f"CRONBACH'S ALPHA: {context['alpha_result']}")
    if context.get("corr") is not None:
        ctx_parts.append("MATRIKS KORELASI:\n" + context["corr"].round(3).to_string())
    if context.get("dataset_info"):
        ctx_parts.append(f"INFO DATASET: {context['dataset_info']}")

    system = (
        "Kamu adalah asisten riset statistik bernama StatAI, terhubung dengan Ruang Statistika. "
        "Kamu memiliki akses ke hasil analisis data pengguna. "
        "Jawab pertanyaan pengguna berdasarkan data yang tersedia dengan akurat dan dalam Bahasa Indonesia."
    )
    context_text = "\n\n".join(ctx_parts) if ctx_parts else "Belum ada data yang dianalisis."
    prompt = f"""
DATA ANALISIS YANG TERSEDIA:
{context_text}

PERTANYAAN PENGGUNA:
{user_question}
"""
    return call_ai_api(prompt, system=system, api_key=api_key, provider=provider)


def ai_generate_kesimpulan(df_info: dict, desc_df, norm_df, val_df, alpha_val,
                            corr, api_key: str, provider: str) -> str:
    parts = [f"Dataset: {df_info.get('rows', '?')} baris, {df_info.get('cols', '?')} kolom"]
    if desc_df is not None and not desc_df.empty:
        parts.append("STATISTIK DESKRIPTIF:\n" + desc_df.to_string(index=False))
    if norm_df is not None and not norm_df.empty:
        parts.append("NORMALITAS:\n" + norm_df.to_string(index=False))
    if val_df is not None and not val_df.empty:
        parts.append("VALIDITAS:\n" + val_df.to_string(index=False))
    if alpha_val is not None:
        parts.append(f"CRONBACH'S ALPHA: {alpha_val}")
    if corr is not None:
        parts.append("KORELASI:\n" + corr.round(3).to_string())

    active_mods = df_info.get("active_modules", [])
    if active_mods:
        parts.append("MODUL ANALISIS: " + ", ".join(active_mods))

    prompt = f"""
Berikut rangkuman lengkap hasil analisis statistik penelitian:

{chr(10).join(parts)}

Buatlah KESIMPULAN DAN REKOMENDASI KOMPREHENSIF dalam Bahasa Indonesia mencakup:
1. Kualitas Data: distribusi, kelengkapan, kebersihan
2. Instrumen Penelitian: validitas dan reliabilitas secara keseluruhan
3. Temuan Utama: pola dan hubungan terpenting dari semua analisis
4. Rekomendasi Analisis Lanjutan
5. Catatan Metodologis dan keterbatasan penelitian

Format: paragraf mengalir, gaya bagian "Kesimpulan dan Saran" pada skripsi/tesis.
Minimum 5 paragraf. Jangan gunakan bullet points.
"""
    return call_ai_api(prompt, system="", api_key=api_key, provider=provider)


def ai_raw_interpret(prompt: str, api_key: str, provider: str = "Claude (Anthropic)") -> str:
    """Helper generik untuk modul export — kirim prompt mentah ke AI."""
    if not api_key:
        return ""
    return call_ai_api(prompt, system="", api_key=api_key, provider=provider)


def ai_interpret_heatmap(corr_matrix: pd.DataFrame, api_key: str, provider: str) -> str:
    corr_json = corr_matrix.round(3).to_dict()
    n_vars = len(corr_matrix.columns)

    pairs = []
    cols = list(corr_matrix.columns)
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            r = round(float(corr_matrix.iloc[i, j]), 3)
            pairs.append({"var_x": cols[i], "var_y": cols[j], "r": r})
    pairs_sorted = sorted(pairs, key=lambda x: abs(x["r"]), reverse=True)
    top_pairs    = pairs_sorted[:min(5, len(pairs_sorted))]

    prompt = f"""
Berikut adalah matriks korelasi Pearson dari {n_vars} variabel penelitian
yang divisualisasikan sebagai heatmap:

MATRIKS KORELASI:
{json.dumps(corr_json, ensure_ascii=False, indent=2)}

5 PASANGAN KORELASI TERKUAT:
{json.dumps(top_pairs, ensure_ascii=False, indent=2)}

Berikan interpretasi visual heatmap dalam Bahasa Indonesia yang mencakup:
1. Pembacaan heatmap — area mana yang berwarna gelap/terang? Apa artinya secara visual?
2. Cluster variabel — apakah ada kelompok variabel yang saling berkorelasi kuat?
3. Pasangan dominan — identifikasi 2-3 pasangan variabel dengan korelasi terkuat
4. Potensi multikolinieritas — apakah ada variabel yang terlalu berkorelasi (|r| > 0.8)?
Tulis dalam 3 paragraf, gaya deskriptif-analitis.
"""
    return call_ai_api(prompt, system="", api_key=api_key, provider=provider)


def ai_interpret_normality(norm_df: pd.DataFrame, alpha_level: float,
                           api_key: str, provider: str) -> str:
    norm_json = norm_df.to_dict(orient="records") if norm_df is not None else []
    n_total  = len(norm_json)
    n_normal = sum(1 for r in norm_json if "Ya" in str(r.get("Normal (α=0.05)", "")))

    prompt = f"""
Berikut adalah hasil uji normalitas Shapiro-Wilk untuk {n_total} variabel (α = {alpha_level}):

{json.dumps(norm_json, ensure_ascii=False, indent=2)}

RINGKASAN: {n_normal} dari {n_total} variabel berdistribusi normal (p ≥ {alpha_level}).

Berikan interpretasi mendalam dalam Bahasa Indonesia yang mencakup:
1. Evaluasi per variabel — variabel mana yang normal/tidak normal
2. Implikasi metodologis — uji statistik apa yang tepat (parametrik vs non-parametrik)
3. Langkah lanjutan — apakah perlu transformasi data atau Central Limit Theorem berlaku?
Tulis dalam 3 paragraf.
"""
    return call_ai_api(prompt, system="", api_key=api_key, provider=provider)


def ai_interpret_plots(var_stats, api_key: str, provider: str,
                       same_var: bool = False) -> str:
    if isinstance(var_stats, dict):
        vars_info = [var_stats]
    else:
        vars_info = var_stats

    var_json = json.dumps(vars_info, ensure_ascii=False, indent=2)

    if same_var:
        focus = f"Kedua grafik menampilkan variabel yang sama: **{vars_info[0].get('variabel', 'X')}**."
    else:
        focus = f"Histogram dan Q-Q Plot variabel penelitian."

    prompt = f"""
Berikut adalah data statistik dari histogram dan Q-Q plot:
{focus}

DATA STATISTIK:
{var_json}

Berikan interpretasi visual dalam Bahasa Indonesia yang mencakup:
1. Pembacaan histogram — bentuk distribusi, skewness, pola
2. Pembacaan Q-Q Plot — apakah titik mendekati garis diagonal?
3. Kesesuaian dengan uji Shapiro-Wilk
4. Rekomendasi — transformasi atau uji non-parametrik?
Tulis dalam 3 paragraf.
"""
    return call_ai_api(prompt, system="", api_key=api_key, provider=provider)


def ai_interpret_validity_bar(val_stats: dict, api_key: str, provider: str) -> str:
    r_tabel  = val_stats.get("r_tabel", 0.3)
    n_butir  = val_stats.get("n_butir", 0)
    n_valid  = val_stats.get("n_valid")
    butir    = val_stats.get("butir", [])

    valid_items   = [b for b in butir if "Valid" in str(b.get("Status", ""))]
    invalid_items = [b for b in butir if "Tidak" in str(b.get("Status", "")) or
                     "Gugur" in str(b.get("Status", ""))]
    n_valid_calc = n_valid if n_valid is not None else len(valid_items)

    prompt = f"""
Data grafik bar validitas Pearson:
r-TABEL = {r_tabel} | TOTAL BUTIR = {n_butir}
BUTIR VALID = {n_valid_calc} | BUTIR TIDAK VALID = {n_butir - n_valid_calc}

DETAIL: {json.dumps(butir[:20], ensure_ascii=False, indent=2)}

Berikan interpretasi visual dalam Bahasa Indonesia:
1. Gambaran visual bar chart — dominan di atas atau bawah r-tabel?
2. Butir bermasalah — mana yang sangat rendah atau borderline?
3. Kualitas instrumen — apakah baik, cukup, atau perlu revisi?
Tulis dalam 3 paragraf.
"""
    return call_ai_api(prompt, system="", api_key=api_key, provider=provider)


def ai_interpret_cronbach_gauge(cronbach_stats: dict, api_key: str, provider: str) -> str:
    alpha    = cronbach_stats.get("alpha", 0)
    n_butir  = cronbach_stats.get("n_butir", 0)
    n_sampel = cronbach_stats.get("n_sampel", 0)
    reliabel = cronbach_stats.get("reliabel", False)
    level    = cronbach_stats.get("level", "")
    acuan    = cronbach_stats.get("acuan", "Ghozali (2018): α ≥ 0.70 = reliabel")

    prompt = f"""
Hasil uji reliabilitas Cronbach's Alpha (gauge chart):
α = {alpha} | Kategori = {level} | Status = {"RELIABEL" if reliabel else "TIDAK RELIABEL"}
N Butir = {n_butir} | N Sampel = {n_sampel} | Acuan = {acuan}

Berikan interpretasi dalam Bahasa Indonesia:
1. Pembacaan gauge — posisi α dalam rentang 0-1
2. Makna substantif — konsistensi internal instrumen
3. Implikasi dan rekomendasi
Tulis dalam 3 paragraf.
"""
    return call_ai_api(prompt, system="", api_key=api_key, provider=provider)

# ══════════════════════════════════════════════════════════════════════════════
# PATCH utils/ai_helpers.py — Tambahkan fungsi ai_interpret_compute()
# Ruang Statistika v4.0 — Modul Compute
#
# Tambahkan fungsi berikut di AKHIR file ai_helpers.py,
# sebelum atau sesudah fungsi ai_interpret_scatter().
# ══════════════════════════════════════════════════════════════════════════════

def ai_interpret_compute(compute_log: list, df_before_info: dict,
                         df_after_info: dict,
                         api_key: str, provider: str) -> str:
    """
    Interpretasi AI untuk modul Compute Variabel.
    Menjelaskan variabel baru yang dibuat, rasionalisasi transformasi,
    dan implikasi terhadap analisis selanjutnya.

    Args:
        compute_log    : list of dicts {"new_col", "method", "source"}
        df_before_info : {"rows": int, "cols": int, "col_names": list}
        df_after_info  : {"rows": int, "cols": int, "new_col_stats": dict}
        api_key        : API key
        provider       : provider name
    """
    import json as _json

    n_ops = len(compute_log)
    if n_ops == 0:
        return "Belum ada variabel baru yang dibuat."

    log_str = _json.dumps(compute_log, ensure_ascii=False, indent=2)

    new_col_stats = df_after_info.get("new_col_stats", {})
    stats_str = ""
    if new_col_stats:
        rows = []
        for col, stats in new_col_stats.items():
            rows.append(
                f"  {col}: mean={stats.get('mean', '?'):.4f}, "
                f"std={stats.get('std', '?'):.4f}, "
                f"min={stats.get('min', '?'):.4f}, "
                f"max={stats.get('max', '?'):.4f}"
            )
        stats_str = "\n".join(rows)

    prompt = f"""
Berikut adalah ringkasan operasi compute variabel baru yang dilakukan pada dataset penelitian:

DATASET AWAL: {df_before_info.get('rows', '?')} baris, {df_before_info.get('cols', '?')} kolom
DATASET AKHIR: {df_after_info.get('rows', '?')} baris, {df_after_info.get('cols', '?')} kolom
JUMLAH OPERASI COMPUTE: {n_ops}

LOG OPERASI:
{log_str}

STATISTIK VARIABEL BARU:
{stats_str if stats_str else '(tidak tersedia)'}

Berikan penjelasan akademis dalam Bahasa Indonesia yang mencakup:
1. Rasionalisasi setiap operasi compute — mengapa transformasi/komputasi ini diperlukan?
2. Implikasi metodologis — bagaimana variabel baru ini akan digunakan dalam analisis?
3. Potensi masalah yang perlu diwaspadai (missing values, outlier pasca-transformasi, dll.)
4. Rekomendasi analisis lanjutan dengan variabel baru ini

Format: 3-4 paragraf akademis, gaya penulisan metodologi penelitian.
"""
    return call_ai_api(prompt, system="", api_key=api_key, provider=provider)

def ai_interpret_scatter(scatter_stats: dict, api_key: str, provider: str) -> str:
    var_x  = scatter_stats.get("var_x", "X")
    var_y  = scatter_stats.get("var_y", "Y")
    r      = scatter_stats.get("r", 0)
    p      = scatter_stats.get("p", 1)
    r2     = scatter_stats.get("r2", 0)
    n      = scatter_stats.get("n", 0)
    sig    = scatter_stats.get("signifikan", p < 0.05)

    abs_r = abs(r)
    kekuatan = (
        "kuat" if abs_r >= 0.7 else
        "sedang" if abs_r >= 0.4 else
        "lemah" if abs_r >= 0.2 else "sangat lemah"
    )
    arah     = "positif" if r >= 0 else "negatif"
    sig_txt  = f"signifikan (p = {p:.4f})" if sig else f"tidak signifikan (p = {p:.4f})"

    prompt = f"""
Scatter plot antara dua variabel:
X = {var_x} | Y = {var_y} | N = {n}
r = {r} ({kekuatan}, {arah}) | p = {p} — {sig_txt} | R² = {r2:.4f}

Berikan interpretasi dalam Bahasa Indonesia:
1. Kekuatan & arah hubungan
2. Pembacaan scatter plot — pola visual yang diharapkan
3. Koefisien determinasi R²
4. Kesimpulan & rekomendasi
Tulis dalam 3-4 paragraf.
"""
    return call_ai_api(prompt, system="", api_key=api_key, provider=provider)


def ai_interpret_alpha_if_deleted(payload: dict, api_key: str, provider: str) -> str:
    """
    Interpretasi AI untuk Item-Total Statistics & Alpha jika Item Dihapus.
    Dipanggil dari modules/validitas.py — Tab 3 (Pro).

    payload keys:
        alpha_overall, n_items, n_sampel, n_bad_citc, n_raise_alpha,
        mean_iic, item_stats (list of dicts), problem_items (list)
    """
    import json as _json

    alpha_overall  = payload.get("alpha_overall", 0)
    n_items        = payload.get("n_items", 0)
    n_sampel       = payload.get("n_sampel", 0)
    n_bad_citc     = payload.get("n_bad_citc", 0)
    n_raise_alpha  = payload.get("n_raise_alpha", 0)
    mean_iic       = payload.get("mean_iic", 0)
    item_stats     = payload.get("item_stats", [])
    problem_items  = payload.get("problem_items", [])

    # Ringkas item dengan masalah untuk prompt yang lebih fokus
    problem_detail = [
        r for r in item_stats
        if r.get("Butir") in problem_items
    ]
    # Ambil maks 15 item untuk efisiensi token
    sample_stats = item_stats[:15]

    prompt = f"""
Berikut adalah hasil analisis Item-Total Statistics & Alpha Cronbach jika Item Dihapus
untuk instrumen kuesioner dengan {n_items} butir dan {n_sampel} responden.

RINGKASAN KESELURUHAN:
- α Cronbach keseluruhan        = {alpha_overall}
- Total item dianalisis          = {n_items}
- Item dengan CITC < 0.30        = {n_bad_citc} (item lemah — Nunnally, 1978)
- Item yang jika dihapus naikan α = {n_raise_alpha} (kandidat revisi/hapus)
- Mean inter-item correlation    = {mean_iic:.4f} (ideal: 0.15–0.50, Clark & Watson 1995)

ITEM BERMASALAH:
{_json.dumps(problem_detail, ensure_ascii=False, indent=2)}

SAMPEL DATA LENGKAP (maks 15 item):
{_json.dumps(sample_stats, ensure_ascii=False, indent=2)}

Berikan interpretasi mendalam dalam Bahasa Indonesia yang mencakup:
1. **Kualitas Keseluruhan Instrumen** — evaluasi α dan mean inter-item correlation
2. **Analisis Item Bermasalah** — jelaskan secara spesifik tiap item kandidat hapus/revisi,
   berapa besar potensi peningkatan α, dan saran perbaikan redaksional
3. **CITC & Kontribusi Item** — item mana yang paling berkontribusi pada reliabilitas?
4. **Rekomendasi Konkret** — apakah instrumen perlu revisi, berapa item yang disarankan dipertahankan?
5. **Implikasi Metodologis** — efek terhadap validitas konstruk dan kesimpulan penelitian

Tulis dalam 4–5 paragraf akademis, gaya Bab 4 skripsi/tesis, Bahasa Indonesia baku.
Hindari bullet points, tulis dalam paragraf mengalir.
Referensi: Nunnally (1978), Ghozali (2018), Clark & Watson (1995), Field (2018).
"""
    return call_ai_api(prompt, system="", api_key=api_key, provider=provider)


# ══════════════════════════════════════════════════════════════════════════════
# PATCH v4.2 — Regresi Robust & WLS (modules/ols_robust.py)
# ══════════════════════════════════════════════════════════════════════════════

def ai_interpret_robust(
    dep_var: str,
    ind_vars: list,
    coef_df,
    n_changed: int,
    n_low_weight: int,
    n_obs: int,
    estimator: str,
    api_key: str,
    provider: str,
) -> str:
    """
    Interpretasi AI untuk Tab 1 Regresi Robust (RLM Huber-M / Bisquare).
    Dipanggil dari modules/ols_robust.py Tab 1 dan utils/export.py.
    """
    import json as _json
    coef_json = coef_df.to_dict(orient="records") if hasattr(coef_df, "to_dict") else []

    prompt = f"""
Berikut adalah hasil Regresi Robust ({estimator}) dibandingkan dengan OLS biasa.
Variabel dependen: {dep_var}
Variabel independen: {', '.join(ind_vars)}
N observasi: {n_obs}
Estimator Robust: {estimator}

TABEL PERBANDINGAN KOEFISIEN OLS vs {estimator}:
{_json.dumps(coef_json[:15], ensure_ascii=False, indent=2)}

RINGKASAN:
- Jumlah koefisien berubah >10% (tidak robust): {n_changed}
- Observasi dengan bobot rendah (<0.5): {n_low_weight} ({round(n_low_weight / max(n_obs, 1) * 100, 1)}%)

Berikan interpretasi mendalam dalam Bahasa Indonesia yang mencakup:
1. **Mengapa Regresi Robust Dipilih** — kondisi data (outlier/leverage/heteroskedastisitas) yang menjadi alasan
2. **Perbandingan Koefisien** — koefisien mana yang berubah signifikan dan apa implikasinya terhadap kesimpulan?
3. **Observasi Berpengaruh** — seberapa banyak downweighting terjadi dan apakah ada pola sistematis?
4. **Kualitas Model Robust** — kelebihan dan keterbatasan dibanding OLS untuk konteks ini
5. **Rekomendasi** — apakah model robust lebih sesuai? kapan OLS masih lebih baik?

Tulis dalam 4–5 paragraf akademis, gaya Bab 4 skripsi/tesis, Bahasa Indonesia baku.
Hindari bullet points, tulis dalam paragraf mengalir.
Referensi: Huber (1973), Hampel et al. (1986), Greene (2012).
"""
    return call_ai_api(prompt, system="", api_key=api_key, provider=provider)


def ai_interpret_wls_robust(
    dep_var: str,
    ind_vars: list,
    coef_df,
    ols_glejser_p: float,
    wls_glejser_p: float,
    ols_rmse: float,
    wls_rmse: float,
    weight_method: str,
    n_obs: int,
    api_key: str,
    provider: str,
) -> str:
    """
    Interpretasi AI untuk Tab 2 Weighted Least Squares (WLS).
    Dipanggil dari modules/ols_robust.py Tab 2 dan utils/export.py.
    """
    import json as _json
    coef_json = coef_df.to_dict(orient="records") if hasattr(coef_df, "to_dict") else []
    heterosked_before = "terdeteksi" if ols_glejser_p < 0.05 else "tidak terdeteksi"
    heterosked_after  = "masih ada"  if wls_glejser_p < 0.05 else "berkurang/hilang"

    prompt = f"""
Berikut adalah hasil Regresi WLS (Weighted Least Squares) dibandingkan OLS.
Variabel dependen: {dep_var}
Variabel independen: {', '.join(ind_vars)}
N observasi: {n_obs}
Metode pembobotan: {weight_method}

TABEL PERBANDINGAN KOEFISIEN OLS vs WLS:
{_json.dumps(coef_json[:15], ensure_ascii=False, indent=2)}

EVALUASI HETEROSKEDASTISITAS (Glejser):
- Sebelum WLS (OLS): p = {ols_glejser_p:.4f} → heteroskedastisitas {heterosked_before}
- Sesudah WLS: p = {wls_glejser_p:.4f} → heteroskedastisitas {heterosked_after}

RMSE: OLS = {ols_rmse:.4f} | WLS = {wls_rmse:.4f}

Berikan interpretasi mendalam dalam Bahasa Indonesia yang mencakup:
1. **Alasan Penggunaan WLS** — konteks heteroskedastisitas yang menjadi motivasi
2. **Efektivitas WLS** — apakah WLS berhasil mereduksi heteroskedastisitas? (bandingkan Glejser sebelum/sesudah)
3. **Perubahan Koefisien** — koefisien mana yang berubah secara substantif dan mengapa?
4. **Perbandingan Efisiensi** — RMSE dan implikasinya terhadap akurasi prediksi
5. **Rekomendasi Publikasi** — haruskah laporan menggunakan WLS atau robust SE?

Tulis dalam 4–5 paragraf akademis, Bahasa Indonesia baku. Hindari bullet points.
Referensi: Greene (2012), Wooldridge (2010), White (1980).
"""
    return call_ai_api(prompt, system="", api_key=api_key, provider=provider)


def ai_interpret_model_comparison(
    comparison_df,
    best_model: str,
    dep_var: str,
    api_key: str,
    provider: str,
) -> str:
    """
    Interpretasi AI untuk Tab 3 Perbandingan Model (OLS / RLM-Huber / RLM-Bisquare / WLS).
    Dipanggil dari modules/ols_robust.py Tab 3 dan utils/export.py.
    """
    import json as _json
    comp_json = comparison_df.to_dict(orient="records") if hasattr(comparison_df, "to_dict") else []

    prompt = f"""
Berikut perbandingan komprehensif semua model regresi untuk variabel dependen: {dep_var}

TABEL PERBANDINGAN (OLS, RLM Huber-M, RLM Bisquare, WLS):
{_json.dumps(comp_json, ensure_ascii=False, indent=2)}

Model terbaik berdasarkan RMSE: {best_model}

Berikan rekomendasi pemilihan model dalam Bahasa Indonesia yang mencakup:
1. Evaluasi tiap model berdasarkan R², RMSE, AIC/BIC — mana yang paling efisien?
2. Kondisi data spesifik mana yang membuat masing-masing model paling sesuai
3. Rekomendasi final: model mana yang sebaiknya dilaporkan dan alasan metodologisnya
4. Trade-off interpretabilitas vs ketepatan statistik untuk keperluan publikasi ilmiah

Tulis 3–4 paragraf akademis ringkas, Bahasa Indonesia baku.
Referensi: Greene (2012), Huber (1973), Hampel et al. (1986), Wooldridge (2010).
"""
    return call_ai_api(prompt, system="", api_key=api_key, provider=provider)
