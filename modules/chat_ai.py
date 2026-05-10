"""
modules/chat_ai.py — Chat AI Analyst (Free, butuh API Key)
Ruang Statistika v4.0
"""

import streamlit as st

from utils.stats_helpers import (
    require_data, require_cols, ss_get,
    descriptive_stats, normality_test,
    pearson_validity, calc_cronbach,
)
from utils.ai_helpers import ai_chat_analyst


def render(ctx: dict):
    r_tab       = ctx["r_tab"]
    ai_enabled  = ctx["ai_enabled"]
    api_key     = ctx["anthropic_api_key"]
    ai_provider = ctx["ai_provider"]

    st.markdown('<p class="rs-section-title">🤖 Chat AI Analyst</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="rs-section-sub">Tanyakan apapun tentang data Anda kepada AI — seperti konsultan statistik pribadi.</p>',
        unsafe_allow_html=True,
    )

    if not ai_enabled:
        st.error("🔒 Fitur ini memerlukan **API Key**. Masukkan di sidebar untuk mengaktifkan Chat AI.")
        from utils.ai_helpers import FREE_PROVIDER_KEYS, TRIAL_PROVIDER_KEYS
        st.info(
            "**Provider GRATIS yang bisa kamu pakai:** \n"
            "- ⚡ **Groq** → [console.groq.com](https://console.groq.com)\n"
            "- ✨ **Gemini** → [aistudio.google.com](https://aistudio.google.com)\n"
            "- 🌐 **OpenRouter** → [openrouter.ai](https://openrouter.ai)\n"
            "- 🤗 **HuggingFace** → [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)\n\n"
            "**Trial Gratis:** 🌊 Mistral ([console.mistral.ai](https://console.mistral.ai)) · "
            "🔗 Cohere ([dashboard.cohere.com](https://dashboard.cohere.com))"
        )
        st.stop()

    df = require_data()
    if df is None:
        st.stop()
    cols = require_cols(df)

    # Bangun konteks dari analisis yang sudah dijalankan
    context = {
        "dataset_info": f"{len(df)} baris, {len(df.columns)} kolom, variabel: {', '.join(cols or [])}"
    }
    if cols:
        context["desc_df"]      = descriptive_stats(df, cols)
        context["norm_df"]      = normality_test(df, cols)
        if len(cols) >= 2:
            context["val_df"]      = pearson_validity(df, cols, r_tab)
            context["alpha_result"] = calc_cronbach(df, cols)
            context["corr"]        = df[cols].corr()

    # Inisialisasi riwayat chat
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # ── Tampilkan riwayat ──
    if st.session_state.chat_history:
        chat_html = '<div class="chat-container">'
        for msg in st.session_state.chat_history:
            if msg["role"] == "user":
                chat_html += '<div class="chat-label" style="text-align:right;">Anda</div>'
                chat_html += f'<div class="chat-bubble-user">{msg["content"]}</div>'
            else:
                chat_html += '<div class="chat-label">🤖 StatAI</div>'
                chat_html += (
                    f'<div class="chat-bubble-ai">'
                    f'{msg["content"].replace(chr(10), "<br/>")}'
                    f"</div>"
                )
        chat_html += "</div>"
        st.markdown(chat_html, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style='text-align:center; padding:2rem; color:#5f8ab5; background:#f7faff;
                    border:1px solid #d0e4f7; border-radius:12px; margin-bottom:1rem;'>
            <div style='font-size:2rem;'>🤖</div>
            <p style='margin:0.5rem 0 0;'>Halo! Saya <b>StatAI</b>, asisten analisis data Anda.<br/>
            Tanyakan apapun tentang dataset atau hasil statistik yang sudah dianalisis.</p>
        </div>
        """, unsafe_allow_html=True)

    # ── Pertanyaan cepat ──
    st.markdown("**💡 Pertanyaan cepat:**")
    quick_cols = st.columns(3)
    quick_questions = [
        "Bagaimana kualitas data secara keseluruhan?",
        "Variabel mana yang paling perlu diperhatikan?",
        "Apa rekomendasi analisis selanjutnya?",
    ]
    for i, (col, q) in enumerate(zip(quick_cols, quick_questions)):
        with col:
            if st.button(q, key=f"quick_{i}", use_container_width=True):
                st.session_state.pending_question = q

    # ── Input ──
    user_input = st.chat_input("Ketik pertanyaan Anda tentang data...")

    question = None
    if "pending_question" in st.session_state:
        question = st.session_state.pop("pending_question")
    elif user_input:
        question = user_input

    if question:
        st.session_state.chat_history.append({"role": "user", "content": question})
        with st.spinner("🤖 StatAI sedang berpikir..."):
            ai_response = ai_chat_analyst(question, context, api_key, ai_provider)
        st.session_state.chat_history.append({"role": "assistant", "content": ai_response})
        st.rerun()

    if st.session_state.chat_history:
        if st.button("🗑️ Hapus Riwayat Chat"):
            st.session_state.chat_history = []
            st.rerun()
