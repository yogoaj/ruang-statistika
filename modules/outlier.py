"""
modules/outlier.py — Deteksi Outlier (Free)
Ruang Statistika v4.0
"""

import numpy as np
import streamlit as st
import plotly.graph_objects as go
from scipy import stats

from utils.stats_helpers import require_data, require_cols, ss_get
from utils.ai_helpers import call_ai_api


def render(ctx: dict):
    ai_enabled  = ctx["ai_enabled"]
    api_key     = ctx["anthropic_api_key"]
    ai_provider = ctx["ai_provider"]

    if "ai_cache" not in st.session_state:
        st.session_state.ai_cache = {}

    st.markdown('<p class="rs-section-title">🎯 Deteksi Outlier (Pencilan)</p>',
        unsafe_allow_html=True,
    )

    df = require_data()
    if df is None:
        st.stop()
    cols = require_cols(df)
    if cols is None:
        st.stop()

    method  = st.radio("Metode Deteksi:", ["IQR (Interquartile Range)", "Z-Score (|z| > 3)"],
                       horizontal=True)
    col_sel = st.selectbox("Pilih variabel:", cols)
    s       = df[col_sel].dropna()

    if "IQR" in method:
        Q1, Q3 = s.quantile(0.25), s.quantile(0.75)
        IQR    = Q3 - Q1
        lower, upper = Q1 - 1.5 * IQR, Q3 + 1.5 * IQR
        is_out  = (s < lower) | (s > upper)
        outliers = s[is_out]

        fig = go.Figure()
        fig.add_trace(go.Box(y=s, name=col_sel, boxpoints=False,
                             line_color="#0c2340", fillcolor="#E6F1FB"))
        point_colors = ["#E24B4A" if o else "#185FA5" for o in is_out]
        fig.add_trace(go.Scatter(
            x=[col_sel] * len(s), y=s.values,
            mode="markers", marker=dict(color=point_colors, size=5, opacity=0.7),
            name="Data Points", showlegend=False,
        ))
        fig.update_layout(title=f"Boxplot + Strip: {col_sel}",
                          yaxis_title=col_sel, template="plotly_white", height=420,
                          margin=dict(l=30, r=30, t=50, b=30))
        st.plotly_chart(fig, use_container_width=True)

        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f"""<div class="rs-metric">
                <div class="rs-metric-label">Batas Bawah IQR</div>
                <div class="rs-metric-value" style="font-size:1.3rem">{lower:.3f}</div></div>""",
                unsafe_allow_html=True)
        with c2:
            st.markdown(f"""<div class="rs-metric">
                <div class="rs-metric-label">Batas Atas IQR</div>
                <div class="rs-metric-value" style="font-size:1.3rem">{upper:.3f}</div></div>""",
                unsafe_allow_html=True)
        with c3:
            col_out = "#a32d2d" if len(outliers) > 0 else "#3b6d11"
            st.markdown(f"""<div class="rs-metric">
                <div class="rs-metric-label">Outlier Ditemukan</div>
                <div class="rs-metric-value" style="color:{col_out}">{len(outliers)}</div></div>""",
                unsafe_allow_html=True)

        if len(outliers) > 0:
            st.markdown(
                f'<div class="rs-narasi">💬 Ditemukan <b>{len(outliers)}</b> outlier pada '
                f"variabel <b>{col_sel}</b> (IQR method). Nilai di luar rentang "
                f"[{lower:.3f}, {upper:.3f}]. "
                f"Periksa apakah ini kesalahan input atau data ekstrem yang valid.</div>",
                unsafe_allow_html=True,
            )
            with st.expander(f"Lihat {len(outliers)} data outlier"):
                st.dataframe(df.loc[outliers.index], use_container_width=True)

            # ── Hapus outlier langsung ──
            if st.button("🗑️ Hapus Outlier & Simpan Dataset Bersih", type="secondary"):
                df_bersih = df.drop(index=outliers.index).copy()
                st.session_state["df_clean_no_outlier"] = df_bersih
                st.success(
                    f"✅ Dataset bersih disimpan ({len(df_bersih)} baris). "
                    "Gunakan di modul lain dengan mengakses session state `df_clean_no_outlier`."
                )
        else:
            st.markdown(
                f'<div class="rs-narasi">✅ Tidak ditemukan outlier pada variabel '
                f"<b>{col_sel}</b> dengan metode IQR.</div>",
                unsafe_allow_html=True,
            )

    else:  # Z-Score
        z_scores = np.abs(stats.zscore(s))
        is_out   = z_scores > 3
        outliers = s[is_out]

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=list(range(len(s))), y=s.values,
            mode="markers",
            marker=dict(color=["#E24B4A" if o else "#185FA5" for o in is_out], size=6),
            name=col_sel,
        ))
        fig.add_hline(y=s.mean() + 3 * s.std(), line_dash="dash",
                      line_color="#E24B4A", annotation_text="+3 SD")
        fig.add_hline(y=s.mean() - 3 * s.std(), line_dash="dash",
                      line_color="#E24B4A", annotation_text="-3 SD")
        fig.update_layout(title=f"Z-Score Scatter: {col_sel} (merah = |z| > 3)",
                          xaxis_title="Indeks Observasi", yaxis_title=col_sel,
                          template="plotly_white", height=420,
                          margin=dict(l=30, r=30, t=50, b=30))
        st.plotly_chart(fig, use_container_width=True)

        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"""<div class="rs-metric">
                <div class="rs-metric-label">Rata-rata ± 3 SD</div>
                <div class="rs-metric-value" style="font-size:1.1rem">
                    [{s.mean()-3*s.std():.2f}, {s.mean()+3*s.std():.2f}]</div></div>""",
                unsafe_allow_html=True)
        with c2:
            col_out = "#a32d2d" if len(outliers) > 0 else "#3b6d11"
            st.markdown(f"""<div class="rs-metric">
                <div class="rs-metric-label">Outlier Ditemukan</div>
                <div class="rs-metric-value" style="color:{col_out}">{len(outliers)}</div></div>""",
                unsafe_allow_html=True)

        st.markdown(
            f'<div class="rs-narasi">💬 Ditemukan <b>{len(outliers)}</b> outlier pada '
            f"variabel <b>{col_sel}</b> dengan metode Z-Score (threshold |z| > 3). "
            f'{"Pertimbangkan untuk menghapus atau menginvestigasi data tersebut." if len(outliers) > 0 else "Data tergolong bersih dari outlier ekstrem."}'
            f"</div>",
            unsafe_allow_html=True,
        )
        if len(outliers) > 0:
            with st.expander(f"Lihat {len(outliers)} data outlier"):
                out_info = df.loc[outliers.index].copy()
                out_info["z-score"] = z_scores[is_out]
                st.dataframe(out_info, use_container_width=True)

    # ── Simpan hasil ke session_state untuk export ──────────────────────────
    st.session_state["outlier_result"] = {
        "variabel":      col_sel,
        "method":        method,
        "n_total":       int(len(s)),
        "total_outliers": int(len(outliers)),
        "pct_outliers":  round(len(outliers) / len(s) * 100, 2) if len(s) > 0 else 0,
    }

    # ── AI Interpretasi ──────────────────────────────────────────────────────
    st.markdown("---")
    if ai_enabled:
        cache_key = f"outlier_{col_sel}_{method[:3]}"
        if st.button("🤖 Interpretasi Outlier dengan AI", key="ai_outlier_btn"):
            method_label = "IQR (Interquartile Range)" if "IQR" in method else "Z-Score (|z| > 3)"
            prompt = f"""
Berikut adalah hasil deteksi outlier pada variabel penelitian:

VARIABEL  : {col_sel}
METODE    : {method_label}
N DATA    : {len(s)}
OUTLIER   : {len(outliers)} ({round(len(outliers)/len(s)*100, 1) if len(s) > 0 else 0}% dari total data)

STATISTIK VARIABEL:
- Mean    : {s.mean():.4f}
- Std Dev : {s.std():.4f}
- Min     : {s.min():.4f}
- Max     : {s.max():.4f}

Berikan interpretasi dalam Bahasa Indonesia yang mencakup:
1. **Evaluasi keberadaan outlier** — apakah {len(outliers)} outlier ({round(len(outliers)/len(s)*100, 1) if len(s) > 0 else 0}%)
   tergolong banyak atau wajar untuk data penelitian ini?
2. **Kemungkinan penyebab** — apa yang mungkin menyebabkan nilai ekstrem ini?
   Apakah kesalahan input, nilai valid tapi tidak biasa, atau kasus khusus?
3. **Rekomendasi penanganan** — haruskah outlier dihapus, ditransformasi, atau dianalisis
   terpisah? Apa dampaknya terhadap validitas analisis regresi/korelasi?
Tulis dalam 3 paragraf, gaya analisis data penelitian.
"""
            with st.spinner("🤖 AI sedang menganalisis outlier..."):
                ai_out = call_ai_api(prompt, api_key=api_key, provider=ai_provider)
            st.session_state.ai_cache[cache_key] = ai_out

        if ss_get("ai_cache", {}).get(cache_key):
            st.markdown(
                f'<div class="rs-ai-narasi">'
                f'<span class="rs-ai-badge">✨ AI — {ai_provider.split("(")[0].strip()}'
                f' | {col_sel}</span><br/>'
                f'{ss_get("ai_cache", {}).get(cache_key, "").replace(chr(10), "<br/>")}'
                f"</div>",
                unsafe_allow_html=True,
            )
    else:
        st.caption("💡 Aktifkan API Key di sidebar untuk interpretasi AI.")
