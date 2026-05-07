"""
modules/uji_nonparametrik.py — Uji Non-Parametrik Lengkap (Free)
Ruang Statistika v4.2

Uji yang tersedia:
  Tab 1 — Dua Sampel Berhubungan  : Wilcoxon Signed-Rank (pre-post)
  Tab 2 — k Sampel Berhubungan    : Friedman Test + post-hoc Nemenyi
  Tab 3 — Nominal 2×2             : McNemar Test
  Tab 4 — Nominal k Kondisi       : Cochran Q Test
  Tab 5 — Korelasi Ordinal        : Spearman ρ + Kendall τ (heatmap)
"""

from __future__ import annotations

import itertools

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
from scipy import stats

from utils.stats_helpers import require_data, require_cols, ss_get
from utils.ai_helpers import call_ai_api

# ── Palet warna konsisten ────────────────────────────────────────────────────
BLUE  = "#185FA5"
GREEN = "#3B6D11"
RED   = "#A32D2D"
RED2  = "#E24B4A"
PURPLE= "#6B21A8"


# ═══════════════════════════════════════════════════════════════════════════════
# Helper utilities
# ═══════════════════════════════════════════════════════════════════════════════

def _metric_card(label: str, value, col_obj=None):
    html = (
        f'<div class="rs-metric">'
        f'<div class="rs-metric-label">{label}</div>'
        f'<div class="rs-metric-value" style="font-size:1.35rem">{value}</div>'
        f'</div>'
    )
    if col_obj:
        col_obj.markdown(html, unsafe_allow_html=True)
    else:
        st.markdown(html, unsafe_allow_html=True)


def _narasi(text: str, color: str = BLUE):
    st.markdown(
        f'<div class="rs-narasi" style="border-left-color:{color};">{text}</div>',
        unsafe_allow_html=True,
    )


def _sig_badge(p_val: float, alpha: float) -> tuple[str, str]:
    """Return (label, color)."""
    if p_val < alpha:
        return "✅ Signifikan", GREEN
    return "❌ Tidak Signifikan", RED


def _rank_biserial_wilcoxon(w_stat: float, n: int) -> float:
    """Effect size rank-biserial r untuk Wilcoxon signed-rank."""
    max_w = n * (n + 1) / 2
    return round(w_stat / max_w, 4) if max_w > 0 else 0.0


def _kendall_w(data_matrix: np.ndarray) -> float:
    """Hitung Kendall's W (concordance) dari matrix (subjects × raters/conditions)."""
    n, k = data_matrix.shape
    ranks = np.apply_along_axis(stats.rankdata, 0, data_matrix)
    rank_sums = ranks.sum(axis=1)
    s = np.sum((rank_sums - rank_sums.mean()) ** 2)
    w = 12 * s / (k ** 2 * (n ** 3 - n))
    return round(float(w), 4)


def _nemenyi_pairwise(groups: list[np.ndarray]) -> pd.DataFrame:
    """
    Post-hoc Nemenyi approximation (Conover, 1999) setelah Friedman.
    Menggunakan critical difference berbasis distribusi normal.
    """
    k   = len(groups)
    n   = len(groups[0])
    all_data = np.column_stack(groups)                   # n × k
    # Rank setiap baris (setiap subjek)
    ranked = np.apply_along_axis(stats.rankdata, 1, all_data)
    rank_means = ranked.mean(axis=0)

    rows = []
    cd_factor = np.sqrt(k * (k + 1) / (6 * n))
    for i, j in itertools.combinations(range(k), 2):
        diff = abs(rank_means[i] - rank_means[j])
        z    = diff / cd_factor
        p    = float(2 * (1 - stats.norm.cdf(z)))
        rows.append({
            "Kelompok A": f"K{i+1}",
            "Kelompok B": f"K{j+1}",
            "|Δ Rank Mean|": round(diff, 3),
            "z": round(z, 3),
            "p-value": round(p, 4),
        })
    return pd.DataFrame(rows)


# ═══════════════════════════════════════════════════════════════════════════════
# Tab 1 — Wilcoxon Signed-Rank (dua sampel berhubungan)
# ═══════════════════════════════════════════════════════════════════════════════

def _tab_wilcoxon(df: pd.DataFrame, cols: list[str], alpha: float,
                  ai_enabled: bool, api_key: str, ai_provider: str):
    st.markdown("#### 🔁 Wilcoxon Signed-Rank Test")
    st.caption(
        "Uji non-parametrik untuk dua sampel berpasangan (pre-post, matched-pairs). "
        "Alternatif dari paired t-test ketika data tidak berdistribusi normal."
    )

    if len(cols) < 2:
        st.warning("⚠️ Diperlukan minimal 2 kolom numerik.")
        return

    c1, c2 = st.columns(2)
    with c1:
        pre_col  = st.selectbox("Kolom Pre (sebelum):", cols, key="wsr_pre")
    with c2:
        post_col = st.selectbox(
            "Kolom Post (sesudah):",
            [c for c in cols if c != pre_col] or cols,
            key="wsr_post",
        )
    alt = st.radio(
        "Hipotesis:",
        ["two-sided", "less (pre < post)", "greater (pre > post)"],
        horizontal=True, key="wsr_alt",
    )
    alt_map = {"two-sided": "two-sided", "less (pre < post)": "less",
               "greater (pre > post)": "greater"}

    paired = df[[pre_col, post_col]].dropna()
    if len(paired) < 5:
        st.warning("⚠️ Minimal 5 pasangan data valid diperlukan.")
        return

    pre_arr  = paired[pre_col].values
    post_arr = paired[post_col].values
    diff_arr = post_arr - pre_arr

    w_stat, p_val = stats.wilcoxon(pre_arr, post_arr, alternative=alt_map[alt])
    n_valid        = len(paired)
    r_eff          = _rank_biserial_wilcoxon(w_stat, n_valid)
    sig_lbl, sig_col = _sig_badge(p_val, alpha)

    # ── Simpan ke session_state ──────────────────────────────────────────────
    st.session_state["uji_beda_result"] = {
        "uji_type":    "Wilcoxon Signed-Rank",
        "num_col":     f"{pre_col} vs {post_col}",
        "g1_name":     pre_col,
        "g2_name":     post_col,
        "g1_mean":     round(float(np.median(pre_arr)), 4),
        "g2_mean":     round(float(np.median(post_arr)), 4),
        "statistic":   round(float(w_stat), 4),
        "p_value":     round(float(p_val), 4),
        "effect_size": r_eff,
        "signifikan":  p_val < alpha,
        "alpha":       alpha,
    }

    # ── Metrik ──────────────────────────────────────────────────────────────
    m1, m2, m3, m4, m5 = st.columns(5)
    _metric_card("n Pasangan", n_valid, m1)
    _metric_card(f"Median {pre_col}", round(float(np.median(pre_arr)), 3), m2)
    _metric_card(f"Median {post_col}", round(float(np.median(post_arr)), 3), m3)
    _metric_card("W Statistik", round(float(w_stat), 3), m4)
    _metric_card("p-value", round(float(p_val), 4), m5)

    _narasi(
        f"💬 <b>Wilcoxon Signed-Rank</b>: W = {w_stat:.3f}, p = {p_val:.4f} "
        f"<span style='color:{sig_col}; font-weight:700;'>{sig_lbl}</span> pada α = {alpha}.<br/>"
        f"Effect size rank-biserial r = {r_eff} "
        f"({'kecil' if abs(r_eff) < 0.3 else 'sedang' if abs(r_eff) < 0.5 else 'besar'} — "
        f"acuan: kecil < 0.3, sedang 0.3–0.5, besar ≥ 0.5).",
        sig_col,
    )

    # ── Visualisasi: boxplot + distribusi selisih ────────────────────────────
    col_v1, col_v2 = st.columns(2)
    with col_v1:
        fig = go.Figure()
        for arr, name, color in [(pre_arr, pre_col, BLUE), (post_arr, post_col, RED2)]:
            fig.add_trace(go.Box(y=arr, name=name, marker_color=color, boxpoints="outliers"))
        fig.update_layout(title="Boxplot Pre vs Post", template="plotly_white",
                          height=340, margin=dict(l=20, r=20, t=45, b=20))
        st.plotly_chart(fig, use_container_width=True)

    with col_v2:
        fig2 = go.Figure(go.Histogram(
            x=diff_arr, nbinsx=20, marker_color=BLUE, opacity=0.75,
        ))
        fig2.add_vline(x=0, line_dash="dash", line_color=RED2,
                       annotation_text="Tidak ada perubahan")
        fig2.update_layout(title="Distribusi Selisih (Post − Pre)",
                           xaxis_title="Selisih", yaxis_title="Frekuensi",
                           template="plotly_white", height=340,
                           margin=dict(l=20, r=20, t=45, b=20))
        st.plotly_chart(fig2, use_container_width=True)

    # ── Tabel deskriptif ──────────────────────────────────────────────────────
    with st.expander("📋 Statistik Deskriptif & Tabel Berpasangan"):
        desc = pd.DataFrame({
            "Variabel": [pre_col, post_col, "Selisih (Post−Pre)"],
            "N":        [n_valid, n_valid, n_valid],
            "Median":   [np.median(pre_arr), np.median(post_arr), np.median(diff_arr)],
            "Mean":     [pre_arr.mean(), post_arr.mean(), diff_arr.mean()],
            "SD":       [pre_arr.std(ddof=1), post_arr.std(ddof=1), diff_arr.std(ddof=1)],
            "Min":      [pre_arr.min(), post_arr.min(), diff_arr.min()],
            "Max":      [pre_arr.max(), post_arr.max(), diff_arr.max()],
        }).round(4)
        st.dataframe(desc, use_container_width=True, hide_index=True)

    # ── AI ────────────────────────────────────────────────────────────────────
    _render_ai_block(
        key="wilcoxon",
        prompt=f"""
Hasil Wilcoxon Signed-Rank Test:
- Pre: {pre_col} | Post: {post_col}
- n pasangan = {n_valid}
- Median pre = {np.median(pre_arr):.3f}, median post = {np.median(post_arr):.3f}
- W = {w_stat:.3f}, p = {p_val:.4f}
- Hipotesis: {alt}
- Rank-biserial r = {r_eff}
- Kesimpulan: {'Signifikan' if p_val < alpha else 'Tidak Signifikan'} pada α = {alpha}

Berikan interpretasi dalam Bahasa Indonesia (2–3 paragraf akademis) mencakup:
1. Arti hasil uji dan perubahan pre-post
2. Makna effect size rank-biserial r
3. Implikasi praktis dan rekomendasi analisis lanjutan
""",
        ai_enabled=ai_enabled, api_key=api_key, ai_provider=ai_provider,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Tab 2 — Friedman Test (k sampel berhubungan)
# ═══════════════════════════════════════════════════════════════════════════════

def _tab_friedman(df: pd.DataFrame, cols: list[str], alpha: float,
                  ai_enabled: bool, api_key: str, ai_provider: str):
    st.markdown("#### 🔀 Friedman Test (k Sampel Berhubungan)")
    st.caption(
        "Uji non-parametrik untuk membandingkan tiga atau lebih kondisi/waktu "
        "pada subjek yang sama. Alternatif dari repeated-measures ANOVA."
    )

    if len(cols) < 3:
        st.warning("⚠️ Diperlukan minimal 3 kolom untuk Friedman Test.")
        return

    selected = st.multiselect(
        "Pilih kolom kondisi (minimal 3, urutan waktu/kondisi):",
        cols, default=cols[:min(4, len(cols))], key="frm_cols",
    )
    if len(selected) < 3:
        st.info("Pilih minimal 3 kolom.")
        return

    sub = df[selected].dropna()
    if len(sub) < 5:
        st.warning("⚠️ Minimal 5 baris valid diperlukan.")
        return

    data_matrix = sub.values   # n × k
    k           = len(selected)
    n           = len(sub)

    chi2_stat, p_val = stats.friedmanchisquare(*[data_matrix[:, i] for i in range(k)])
    kendall_w        = _kendall_w(data_matrix)
    sig_lbl, sig_col = _sig_badge(p_val, alpha)
    df_stat          = k - 1

    # ── Simpan ──────────────────────────────────────────────────────────────
    st.session_state.setdefault("uji_beda_result", {})
    st.session_state["uji_beda_result"] = {
        "uji_type":    "Friedman Test",
        "num_col":     ", ".join(selected),
        "statistic":   round(float(chi2_stat), 4),
        "p_value":     round(float(p_val), 4),
        "effect_size": kendall_w,
        "signifikan":  p_val < alpha,
        "alpha":       alpha,
        "k":           k, "n": n,
    }

    # ── Metrik ──────────────────────────────────────────────────────────────
    m1, m2, m3, m4, m5 = st.columns(5)
    _metric_card("n Subjek", n, m1)
    _metric_card("k Kondisi", k, m2)
    _metric_card("χ² Friedman", round(float(chi2_stat), 3), m3)
    _metric_card("p-value", round(float(p_val), 4), m4)
    _metric_card("Kendall's W", kendall_w, m5)

    _narasi(
        f"💬 <b>Friedman Test</b>: χ²({df_stat}) = {chi2_stat:.3f}, p = {p_val:.4f} "
        f"<span style='color:{sig_col}; font-weight:700;'>{sig_lbl}</span> pada α = {alpha}.<br/>"
        f"Kendall's W = {kendall_w} (effect size konkordansi: 0=tidak konkord, 1=sempurna).",
        sig_col,
    )

    # ── Boxplot per kondisi ──────────────────────────────────────────────────
    fig = go.Figure()
    palette = px.colors.qualitative.Set2
    for i, col in enumerate(selected):
        fig.add_trace(go.Box(
            y=sub[col].values, name=col,
            marker_color=palette[i % len(palette)], boxpoints="outliers",
        ))
    fig.update_layout(title="Boxplot per Kondisi / Waktu",
                      template="plotly_white", height=360,
                      margin=dict(l=20, r=20, t=50, b=20))
    st.plotly_chart(fig, use_container_width=True)

    # ── Rank means ───────────────────────────────────────────────────────────
    ranked = np.apply_along_axis(stats.rankdata, 1, data_matrix)
    rank_means = ranked.mean(axis=0)
    fig_rm = go.Figure(go.Bar(
        x=selected, y=rank_means, marker_color=BLUE,
        text=[f"{v:.2f}" for v in rank_means], textposition="outside",
    ))
    fig_rm.update_layout(
        title="Rata-Rata Rank per Kondisi",
        yaxis_title="Rata-Rata Rank", template="plotly_white", height=320,
        margin=dict(l=20, r=20, t=50, b=20),
    )
    st.plotly_chart(fig_rm, use_container_width=True)

    # ── Post-hoc Nemenyi ──────────────────────────────────────────────────────
    if p_val < alpha:
        st.markdown("##### 🔬 Post-Hoc: Nemenyi Pairwise (Conover, 1999)")
        st.caption("Ditampilkan karena hasil Friedman signifikan.")
        groups = [data_matrix[:, i] for i in range(k)]
        nemenyi_df = _nemenyi_pairwise(groups)
        # Ganti nama kolom K1, K2, ... dengan nama kolom asli
        name_map = {f"K{i+1}": selected[i] for i in range(k)}
        nemenyi_df["Kelompok A"] = nemenyi_df["Kelompok A"].map(name_map)
        nemenyi_df["Kelompok B"] = nemenyi_df["Kelompok B"].map(name_map)
        nemenyi_df["Signifikan"] = nemenyi_df["p-value"].apply(
            lambda p: "✅ Ya" if p < alpha else "❌ Tidak"
        )

        def _color_sig(row):
            return ["background-color:#eaf3de" if row["Signifikan"] == "✅ Ya"
                    else "background-color:#fcebeb"] * len(row)

        st.dataframe(
            nemenyi_df.style.apply(_color_sig, axis=1),
            use_container_width=True, hide_index=True,
        )
    else:
        st.info("ℹ️ Post-hoc tidak diperlukan karena hasil Friedman tidak signifikan.")

    # ── AI ────────────────────────────────────────────────────────────────────
    _render_ai_block(
        key="friedman",
        prompt=f"""
Hasil Friedman Test:
- Kondisi yang diuji: {', '.join(selected)}
- n subjek = {n}, k kondisi = {k}
- χ²({df_stat}) = {chi2_stat:.3f}, p = {p_val:.4f}
- Kendall's W = {kendall_w}
- Rata-rata rank: {dict(zip(selected, [round(float(r),2) for r in rank_means]))}
- Kesimpulan: {'Signifikan' if p_val < alpha else 'Tidak Signifikan'} pada α = {alpha}

Berikan interpretasi dalam Bahasa Indonesia (2–3 paragraf akademis) mencakup:
1. Arti hasil uji Friedman dan perbedaan antar kondisi
2. Kondisi mana yang paling menonjol berdasarkan rata-rata rank
3. Makna Kendall's W sebagai effect size
4. Implikasi dan rekomendasi analisis lanjutan
""",
        ai_enabled=ai_enabled, api_key=api_key, ai_provider=ai_provider,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Tab 3 — McNemar Test (2×2 nominal)
# ═══════════════════════════════════════════════════════════════════════════════

def _tab_mcnemar(df: pd.DataFrame, alpha: float,
                 ai_enabled: bool, api_key: str, ai_provider: str):
    st.markdown("#### 🔲 McNemar Test (Nominal 2×2 Berpasangan)")
    st.caption(
        "Uji perubahan klasifikasi biner pada dua titik waktu yang sama (pre-post). "
        "Contoh: jumlah responden yang berubah pendapat Ya→Tidak atau Tidak→Ya."
    )

    all_cols = df.columns.tolist()
    c1, c2 = st.columns(2)
    with c1:
        col_pre  = st.selectbox("Kolom Pre (biner/nominal):", all_cols, key="mcn_pre")
    with c2:
        col_post = st.selectbox(
            "Kolom Post:",
            [c for c in all_cols if c != col_pre] or all_cols,
            key="mcn_post",
        )

    paired = df[[col_pre, col_post]].dropna()
    if len(paired) < 10:
        st.warning("⚠️ Minimal 10 pasangan diperlukan.")
        return

    ct = pd.crosstab(paired[col_pre], paired[col_post])
    st.markdown("**Tabel Kontingensi:**")
    st.dataframe(ct, use_container_width=True)

    if ct.shape != (2, 2):
        st.error(
            "❌ McNemar membutuhkan tabel 2×2. Pastikan kedua kolom hanya memiliki 2 kategori unik."
        )
        return

    vals = ct.values
    b = vals[0, 1]   # pre=0, post=1
    c = vals[1, 0]   # pre=1, post=0

    # Koreksi kontinuitas jika n kecil
    if (b + c) < 25:
        chi2_stat = (abs(b - c) - 1) ** 2 / (b + c) if (b + c) > 0 else 0
        st.caption("ℹ️ Koreksi kontinuitas (Edwards) diterapkan karena b+c < 25.")
    else:
        chi2_stat = (b - c) ** 2 / (b + c) if (b + c) > 0 else 0

    p_val            = float(stats.chi2.sf(chi2_stat, df=1))
    sig_lbl, sig_col = _sig_badge(p_val, alpha)
    # Effect size: phi koefisien McNemar
    n_total = vals.sum()
    phi_eff  = round(np.sqrt(chi2_stat / n_total), 4) if n_total > 0 else 0.0

    # ── Metrik ──────────────────────────────────────────────────────────────
    m1, m2, m3, m4, m5 = st.columns(5)
    _metric_card("n Total", int(n_total), m1)
    _metric_card("b (0→1)", int(b), m2)
    _metric_card("c (1→0)", int(c), m3)
    _metric_card("χ² McNemar", round(chi2_stat, 3), m4)
    _metric_card("p-value", round(p_val, 4), m5)

    _narasi(
        f"💬 <b>McNemar Test</b>: χ² = {chi2_stat:.3f}, p = {p_val:.4f} "
        f"<span style='color:{sig_col}; font-weight:700;'>{sig_lbl}</span> pada α = {alpha}.<br/>"
        f"Sel b (berubah 0→1) = {b}, sel c (berubah 1→0) = {c}. "
        f"Effect size φ = {phi_eff} (kecil < 0.1, sedang 0.1–0.3, besar ≥ 0.3).",
        sig_col,
    )

    # ── Visualisasi perubahan ────────────────────────────────────────────────
    change_data = {
        "Kategori": ["Tidak Berubah (a+d)", "Berubah 0→1 (b)", "Berubah 1→0 (c)"],
        "Frekuensi": [int(vals[0, 0] + vals[1, 1]), int(b), int(c)],
        "Warna": [BLUE, GREEN, RED2],
    }
    fig = go.Figure(go.Bar(
        x=change_data["Kategori"], y=change_data["Frekuensi"],
        marker_color=change_data["Warna"],
        text=change_data["Frekuensi"], textposition="outside",
    ))
    fig.update_layout(title="Pola Perubahan Klasifikasi",
                      yaxis_title="Frekuensi", template="plotly_white",
                      height=320, margin=dict(l=20, r=20, t=50, b=20))
    st.plotly_chart(fig, use_container_width=True)

    # ── AI ────────────────────────────────────────────────────────────────────
    _render_ai_block(
        key="mcnemar",
        prompt=f"""
Hasil McNemar Test:
- Kolom pre = {col_pre}, kolom post = {col_post}
- n total = {int(n_total)}, b (berubah 0→1) = {b}, c (berubah 1→0) = {c}
- χ² = {chi2_stat:.3f}, p = {p_val:.4f}
- Effect size φ = {phi_eff}
- Kesimpulan: {'Signifikan' if p_val < alpha else 'Tidak Signifikan'} pada α = {alpha}

Berikan interpretasi Bahasa Indonesia (2 paragraf akademis) mencakup:
1. Apakah ada perubahan proporsi yang signifikan dari pre ke post
2. Arah perubahan (lebih banyak 0→1 atau 1→0) dan implikasinya
""",
        ai_enabled=ai_enabled, api_key=api_key, ai_provider=ai_provider,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Tab 4 — Cochran Q Test (k kondisi biner)
# ═══════════════════════════════════════════════════════════════════════════════

def _tab_cochran_q(df: pd.DataFrame, alpha: float,
                   ai_enabled: bool, api_key: str, ai_provider: str):
    st.markdown("#### 🔁 Cochran Q Test (k Kondisi Biner Berhubungan)")
    st.caption(
        "Generalisasi McNemar untuk ≥ 3 kondisi biner pada subjek yang sama. "
        "Cocok untuk data dikotomis (0/1) yang diukur berulang."
    )

    all_cols = df.columns.tolist()
    selected = st.multiselect(
        "Pilih kolom biner (0/1) — minimal 3 kondisi:",
        all_cols, default=all_cols[:min(4, len(all_cols))], key="cq_cols",
    )
    if len(selected) < 3:
        st.info("Pilih minimal 3 kolom.")
        return

    sub = df[selected].dropna()
    # Pastikan semua kolom biner
    for col in selected:
        uniq = sub[col].unique()
        if not set(uniq).issubset({0, 1, 0.0, 1.0, True, False}):
            st.error(f"❌ Kolom **{col}** bukan biner (0/1). Pastikan semua nilai adalah 0 atau 1.")
            return

    sub = sub.astype(int)
    n, k = sub.shape
    if n < 5:
        st.warning("⚠️ Minimal 5 baris valid diperlukan.")
        return

    # Hitung Cochran Q manual (scipy tidak punya built-in)
    col_sums  = sub.sum(axis=0).values      # L_j
    row_sums  = sub.sum(axis=1).values      # L_i
    grand_sum = int(col_sums.sum())

    q_num = k * (k - 1) * np.sum((col_sums - grand_sum / k) ** 2)
    q_den = k * grand_sum - np.sum(row_sums ** 2)
    q_stat = q_num / q_den if q_den > 0 else 0.0
    df_q   = k - 1
    p_val  = float(stats.chi2.sf(q_stat, df=df_q))
    sig_lbl, sig_col = _sig_badge(p_val, alpha)

    # Proporsi per kondisi
    props = (sub.mean(axis=0) * 100).round(2)

    # ── Metrik ──────────────────────────────────────────────────────────────
    m1, m2, m3, m4 = st.columns(4)
    _metric_card("n Subjek", n, m1)
    _metric_card("k Kondisi", k, m2)
    _metric_card("Q Statistik", round(q_stat, 3), m3)
    _metric_card("p-value", round(p_val, 4), m4)

    _narasi(
        f"💬 <b>Cochran Q Test</b>: Q({df_q}) = {q_stat:.3f}, p = {p_val:.4f} "
        f"<span style='color:{sig_col}; font-weight:700;'>{sig_lbl}</span> pada α = {alpha}.<br/>"
        f"Proporsi '1' per kondisi: "
        + ", ".join([f"{c}: {v}%" for c, v in props.items()]),
        sig_col,
    )

    # ── Bar chart proporsi ───────────────────────────────────────────────────
    fig = go.Figure(go.Bar(
        x=selected, y=props.values,
        marker_color=BLUE,
        text=[f"{v:.1f}%" for v in props.values], textposition="outside",
    ))
    fig.add_hline(y=50, line_dash="dash", line_color=RED2,
                  annotation_text="50% (referensi)")
    fig.update_layout(
        title="Proporsi Respons Positif (1) per Kondisi",
        yaxis_title="Proporsi (%)", yaxis_range=[0, 110],
        template="plotly_white", height=320,
        margin=dict(l=20, r=20, t=50, b=20),
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── Post-hoc McNemar pairwise jika signifikan ────────────────────────────
    if p_val < alpha:
        st.markdown("##### 🔬 Post-Hoc: McNemar Pairwise")
        rows = []
        for i, j in itertools.combinations(range(k), 2):
            ca, cb = selected[i], selected[j]
            pair   = sub[[ca, cb]].values
            b_ij   = int(((pair[:, 0] == 0) & (pair[:, 1] == 1)).sum())
            c_ij   = int(((pair[:, 0] == 1) & (pair[:, 1] == 0)).sum())
            denom  = b_ij + c_ij
            if denom < 2:
                p_ij = 1.0
            else:
                chi2_ij = (abs(b_ij - c_ij) - 1) ** 2 / denom if denom < 25 else (b_ij - c_ij)**2/denom
                p_ij = float(stats.chi2.sf(chi2_ij, 1))
            # Bonferroni correction
            n_pairs     = k * (k - 1) / 2
            p_adj       = min(p_ij * n_pairs, 1.0)
            rows.append({
                "Kondisi A": ca, "Kondisi B": cb,
                "b": b_ij, "c": c_ij,
                "p (unadjusted)": round(p_ij, 4),
                "p (Bonferroni)": round(p_adj, 4),
                "Signifikan (Bonferroni)": "✅ Ya" if p_adj < alpha else "❌ Tidak",
            })
        ph_df = pd.DataFrame(rows)

        def _color_sig(row):
            return ["background-color:#eaf3de" if row["Signifikan (Bonferroni)"] == "✅ Ya"
                    else "background-color:#fcebeb"] * len(row)

        st.dataframe(
            ph_df.style.apply(_color_sig, axis=1),
            use_container_width=True, hide_index=True,
        )

    # ── AI ────────────────────────────────────────────────────────────────────
    _render_ai_block(
        key="cochran_q",
        prompt=f"""
Hasil Cochran Q Test:
- Kondisi: {', '.join(selected)}
- n subjek = {n}, k kondisi = {k}
- Q({df_q}) = {q_stat:.3f}, p = {p_val:.4f}
- Proporsi positif per kondisi: {dict(zip(selected, [f'{v}%' for v in props.values]))}
- Kesimpulan: {'Signifikan' if p_val < alpha else 'Tidak Signifikan'} pada α = {alpha}

Interpretasi dalam Bahasa Indonesia (2 paragraf akademis):
1. Apakah ada perbedaan proporsi signifikan antar kondisi, kondisi mana yang menonjol
2. Implikasi praktis dari pola proporsi ini
""",
        ai_enabled=ai_enabled, api_key=api_key, ai_provider=ai_provider,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Tab 5 — Korelasi Ordinal: Spearman ρ + Kendall τ
# ═══════════════════════════════════════════════════════════════════════════════

def _tab_korelasi_ordinal(df: pd.DataFrame, cols: list[str], alpha: float,
                          ai_enabled: bool, api_key: str, ai_provider: str):
    st.markdown("#### 🔗 Korelasi Ordinal: Spearman ρ & Kendall τ")
    st.caption(
        "Korelasi berbasis rank untuk data ordinal atau data yang melanggar asumsi normalitas. "
        "Spearman ρ lebih umum; Kendall τ lebih robust untuk sampel kecil."
    )

    if len(cols) < 2:
        st.warning("⚠️ Diperlukan minimal 2 kolom numerik/ordinal.")
        return

    method = st.radio(
        "Metode Korelasi:", ["Spearman ρ", "Kendall τ-b", "Keduanya"],
        horizontal=True, key="ord_method",
    )

    # ── Mode: dua variabel spesifik ──────────────────────────────────────────
    mode = st.radio("Mode:", ["Semua variabel (heatmap)", "Dua variabel spesifik"],
                    horizontal=True, key="ord_mode")

    if mode == "Dua variabel spesifik":
        c1, c2 = st.columns(2)
        with c1:
            var_x = st.selectbox("Variabel X:", cols, key="ord_x")
        with c2:
            var_y = st.selectbox("Variabel Y:", [c for c in cols if c != var_x] or cols,
                                 key="ord_y")

        pair = df[[var_x, var_y]].dropna()
        x, y = pair[var_x].values, pair[var_y].values

        results = []
        if method in ["Spearman ρ", "Keduanya"]:
            r_s, p_s = stats.spearmanr(x, y)
            results.append(("Spearman ρ", r_s, p_s))
        if method in ["Kendall τ-b", "Keduanya"]:
            r_k, p_k = stats.kendalltau(x, y)
            results.append(("Kendall τ-b", r_k, p_k))

        for met_name, r_val, p_val in results:
            sig_lbl, sig_col = _sig_badge(p_val, alpha)
            _narasi(
                f"💬 <b>{met_name}</b> ({var_x} × {var_y}): "
                f"r = {r_val:.4f}, p = {p_val:.4f} "
                f"<span style='color:{sig_col}; font-weight:700;'>{sig_lbl}</span>.",
                sig_col,
            )

        # Scatter plot dengan rank
        x_rank = stats.rankdata(x)
        y_rank = stats.rankdata(y)
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=x_rank, y=y_rank, mode="markers",
            marker=dict(color=BLUE, size=7, opacity=0.7),
            name="Rank",
        ))
        # Trendline manual
        slope, intercept, _, _, _ = stats.linregress(x_rank, y_rank)
        x_line = np.linspace(x_rank.min(), x_rank.max(), 100)
        fig.add_trace(go.Scatter(
            x=x_line, y=slope * x_line + intercept,
            mode="lines", line=dict(color=RED2, width=2), name="Trendline Rank",
        ))
        r_disp = results[0][1] if results else 0
        fig.update_layout(
            title=f"Scatter Rank: {var_x} vs {var_y} | ρ ≈ {r_disp:.3f}",
            xaxis_title=f"Rank {var_x}", yaxis_title=f"Rank {var_y}",
            template="plotly_white", height=380,
            margin=dict(l=30, r=30, t=50, b=30),
        )
        st.plotly_chart(fig, use_container_width=True)

        # ── AI ────────────────────────────────────────────────────────────────
        res_str = "; ".join([f"{nm}: r={rv:.4f}, p={pv:.4f}" for nm, rv, pv in results])
        _render_ai_block(
            key="korelasi_ordinal",
            prompt=f"""
Hasil Korelasi Ordinal:
- Variabel: {var_x} × {var_y}
- n = {len(pair)}
- {res_str}
- Alpha = {alpha}

Interpretasi Bahasa Indonesia (2 paragraf akademis):
1. Kekuatan dan arah hubungan ordinal, signifikansi
2. Perbedaan hasil Spearman vs Kendall (jika keduanya digunakan), rekomendasi
""",
            ai_enabled=ai_enabled, api_key=api_key, ai_provider=ai_provider,
        )

    else:
        # ── Heatmap semua variabel ───────────────────────────────────────────
        sub = df[cols].dropna()
        if len(sub) < 5:
            st.warning("⚠️ Minimal 5 baris valid diperlukan.")
            return

        if method in ["Spearman ρ", "Keduanya"]:
            corr_s = sub.corr(method="spearman")
            fig_s = go.Figure(go.Heatmap(
                z=corr_s.values, x=corr_s.columns, y=corr_s.columns,
                colorscale="RdBu", zmin=-1, zmax=1,
                text=np.round(corr_s.values, 3),
                texttemplate="%{text}", textfont={"size": 10},
                colorbar={"title": "ρ"},
            ))
            fig_s.update_layout(title="Heatmap Korelasi Spearman ρ",
                                template="plotly_white", height=480,
                                margin=dict(l=10, r=10, t=50, b=10))
            st.plotly_chart(fig_s, use_container_width=True)

        if method in ["Kendall τ-b", "Keduanya"]:
            corr_k = sub.corr(method="kendall")
            fig_k = go.Figure(go.Heatmap(
                z=corr_k.values, x=corr_k.columns, y=corr_k.columns,
                colorscale="RdBu", zmin=-1, zmax=1,
                text=np.round(corr_k.values, 3),
                texttemplate="%{text}", textfont={"size": 10},
                colorbar={"title": "τ"},
            ))
            fig_k.update_layout(title="Heatmap Korelasi Kendall τ-b",
                                template="plotly_white", height=480,
                                margin=dict(l=10, r=10, t=50, b=10))
            st.plotly_chart(fig_k, use_container_width=True)

        _narasi(
            "ℹ️ Heatmap menampilkan korelasi berbasis rank antar semua variabel numerik yang dipilih. "
            "Pilih mode <b>Dua variabel spesifik</b> untuk uji signifikansi dan visualisasi scatter.",
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Shared AI block renderer
# ═══════════════════════════════════════════════════════════════════════════════

def _render_ai_block(key: str, prompt: str, ai_enabled: bool,
                     api_key: str, ai_provider: str):
    if not ai_enabled:
        st.caption("💡 Aktifkan API Key di sidebar untuk interpretasi AI.")
        return

    btn_label = f"🤖 Interpretasi dengan AI"
    if st.button(btn_label, key=f"ai_btn_{key}"):
        with st.spinner("🤖 AI sedang menganalisis..."):
            ai_result = call_ai_api(prompt, api_key=api_key, provider=ai_provider)
        if "ai_cache" not in st.session_state:
            st.session_state.ai_cache = {}
        st.session_state.ai_cache[key] = ai_result

    cached = ss_get("ai_cache", {}).get(key)
    if cached:
        st.markdown(
            f'<div class="rs-ai-narasi">'
            f'<span class="rs-ai-badge">✨ AI — {ai_provider.split("(")[0].strip()}</span><br/>'
            f'{cached.replace(chr(10), "<br/>")}'
            f"</div>",
            unsafe_allow_html=True,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Entry point
# ═══════════════════════════════════════════════════════════════════════════════

def render(ctx: dict):
    alpha_level = ctx["alpha_level"]
    ai_enabled  = ctx["ai_enabled"]
    api_key     = ctx["anthropic_api_key"]
    ai_provider = ctx["ai_provider"]

    st.markdown(
        '<p class="rs-section-title">📊 Uji Non-Parametrik Lengkap</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="rs-section-sub">'
        'Wilcoxon Signed-Rank · Friedman · McNemar · Cochran Q · Spearman ρ & Kendall τ'
        '</p>',
        unsafe_allow_html=True,
    )

    df = require_data()
    if df is None:
        st.stop()

    # Kolom numerik saja (untuk uji berbasis rank)
    num_cols = df.select_dtypes(include="number").columns.tolist()

    # ── Tab utama ─────────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🔁 Wilcoxon",
        "🔀 Friedman",
        "🔲 McNemar",
        "🔁 Cochran Q",
        "🔗 Korelasi Ordinal",
    ])

    with tab1:
        _tab_wilcoxon(df, num_cols, alpha_level, ai_enabled, api_key, ai_provider)

    with tab2:
        _tab_friedman(df, num_cols, alpha_level, ai_enabled, api_key, ai_provider)

    with tab3:
        _tab_mcnemar(df, alpha_level, ai_enabled, api_key, ai_provider)

    with tab4:
        _tab_cochran_q(df, alpha_level, ai_enabled, api_key, ai_provider)

    with tab5:
        _tab_korelasi_ordinal(df, num_cols, alpha_level, ai_enabled, api_key, ai_provider)
