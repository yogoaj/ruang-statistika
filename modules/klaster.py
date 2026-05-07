"""
modules/klaster.py — Analisis Klaster (Free)
Ruang Statistika v4.2

Fitur:
  • K-Means clustering dengan elbow method (inertia + KneeLocator)
  • Agglomerative Hierarchical Clustering + dendrogram (plotly)
  • Silhouette Score & Silhouette Plot per sampel
  • Cluster Profiling: statistik deskriptif per klaster + radar chart
  • Interpretasi AI (opsional)
  • Simpan hasil ke st.session_state["klaster_result"] untuk export.py

Integrasi app.py:
  1. Tambahkan ke MENU_GROUPS (grup "── Eksplorasi Data" atau baru):
       ("Klaster", "🗂️  Analisis Klaster", False),

  2. Tambahkan routing:
       elif menu == "Klaster":
           from modules.klaster import render
           render(ctx)
"""

import warnings
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
from scipy.cluster.hierarchy import dendrogram, linkage, fcluster
from scipy.spatial.distance import pdist
from sklearn.cluster import KMeans, AgglomerativeClustering
from sklearn.metrics import silhouette_score, silhouette_samples
from sklearn.preprocessing import StandardScaler

from utils.stats_helpers import require_data, require_cols, ss_get

warnings.filterwarnings("ignore")

# ── Palet warna konsisten dengan aplikasi ─────────────────────────────────────
PALETTE = [
    "#185FA5", "#3B6D11", "#A32D2D", "#8B5CF6",
    "#D97706", "#0891B2", "#DB2777", "#059669",
]


# ══════════════════════════════════════════════════════════════════════════════
# HELPER: Preprocessing
# ══════════════════════════════════════════════════════════════════════════════

def _prepare_matrix(df: pd.DataFrame, cols: list[str]) -> tuple[np.ndarray, pd.DataFrame]:
    """
    Pilih kolom numerik, imputasi median, standardisasi → return (X_scaled, df_clean).
    """
    sub = df[cols].copy()
    for c in sub.columns:
        if sub[c].isna().any():
            sub[c] = sub[c].fillna(sub[c].median())
    scaler = StandardScaler()
    X = scaler.fit_transform(sub)
    return X, sub


# ══════════════════════════════════════════════════════════════════════════════
# HELPER: Elbow & Silhouette
# ══════════════════════════════════════════════════════════════════════════════

def _compute_elbow(X: np.ndarray, k_max: int = 10) -> tuple[list, list, list]:
    """Hitung inertia dan silhouette score untuk k = 2..k_max."""
    ks, inertias, sil_scores = [], [], []
    for k in range(2, k_max + 1):
        km = KMeans(n_clusters=k, random_state=42, n_init="auto")
        labels = km.fit_predict(X)
        ks.append(k)
        inertias.append(km.inertia_)
        sil_scores.append(silhouette_score(X, labels))
    return ks, inertias, sil_scores


def _suggest_k(inertias: list) -> int:
    """
    Deteksi siku (elbow) dengan metode perbedaan kedua (second difference).
    Fallback ke k=3 jika tidak terdeteksi.
    """
    if len(inertias) < 3:
        return 2
    diffs   = np.diff(inertias)
    diffs2  = np.diff(diffs)
    idx     = int(np.argmax(np.abs(diffs2)))   # posisi perubahan terbesar
    return idx + 2 + 1   # +2 karena k dimulai dari 2, +1 karena indeks perbedaan


def _plot_elbow(ks: list, inertias: list, sil_scores: list, k_opt: int) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=ks, y=inertias, mode="lines+markers", name="Inertia (WSS)",
        line=dict(color="#185FA5", width=2.5),
        marker=dict(size=7, color="#185FA5"),
        yaxis="y1",
    ))
    fig.add_trace(go.Scatter(
        x=ks, y=sil_scores, mode="lines+markers", name="Silhouette Score",
        line=dict(color="#3B6D11", width=2.5, dash="dot"),
        marker=dict(size=7, color="#3B6D11"),
        yaxis="y2",
    ))
    fig.add_vline(
        x=k_opt, line_dash="dash", line_color="#A32D2D",
        annotation_text=f"k rekomendasi = {k_opt}",
        annotation_position="top right",
    )
    fig.update_layout(
        title="Elbow Method & Silhouette Score",
        xaxis=dict(title="Jumlah Klaster (k)", dtick=1),
        yaxis=dict(title="Inertia (WSS)", titlefont=dict(color="#185FA5")),
        yaxis2=dict(
            title="Silhouette Score",
            titlefont=dict(color="#3B6D11"),
            overlaying="y", side="right",
            range=[0, 1],
        ),
        legend=dict(x=0.6, y=1.02, orientation="h"),
        template="plotly_white", height=380,
        margin=dict(l=40, r=40, t=55, b=35),
    )
    return fig


# ══════════════════════════════════════════════════════════════════════════════
# HELPER: Silhouette Plot
# ══════════════════════════════════════════════════════════════════════════════

def _plot_silhouette(X: np.ndarray, labels: np.ndarray, k: int) -> go.Figure:
    sil_vals  = silhouette_samples(X, labels)
    avg_score = silhouette_score(X, labels)

    fig  = go.Figure()
    y_lo = 10
    tick_vals, tick_text = [], []

    for cl in range(k):
        cl_sil = np.sort(sil_vals[labels == cl])
        y_hi   = y_lo + len(cl_sil)
        color  = PALETTE[cl % len(PALETTE)]
        fig.add_trace(go.Bar(
            x=cl_sil,
            y=list(range(y_lo, y_hi)),
            orientation="h",
            name=f"Klaster {cl + 1}",
            marker_color=color,
            showlegend=True,
        ))
        tick_vals.append((y_lo + y_hi) / 2)
        tick_text.append(f"K{cl + 1}")
        y_lo = y_hi + 10

    fig.add_vline(
        x=avg_score, line_dash="dash", line_color="#A32D2D",
        annotation_text=f"Rata-rata = {avg_score:.3f}",
        annotation_position="top right",
    )
    fig.update_layout(
        title=f"Silhouette Plot (k = {k})",
        xaxis=dict(title="Silhouette Coefficient", range=[-0.2, 1.0]),
        yaxis=dict(
            title="Klaster",
            tickvals=tick_vals,
            ticktext=tick_text,
            showgrid=False,
        ),
        barmode="overlay",
        template="plotly_white", height=420,
        margin=dict(l=50, r=30, t=55, b=35),
    )
    return fig


# ══════════════════════════════════════════════════════════════════════════════
# HELPER: Dendrogram (via scipy → plotly)
# ══════════════════════════════════════════════════════════════════════════════

def _plot_dendrogram(X: np.ndarray, method: str = "ward", k: int = 3) -> go.Figure:
    """Buat dendrogram plotly dari linkage scipy."""
    Z = linkage(X, method=method)
    dend = dendrogram(Z, no_plot=True, color_threshold=0)

    # Ambil koordinat garis
    icoord = np.array(dend["icoord"])
    dcoord = np.array(dend["dcoord"])

    # Hitung cut level untuk k klaster
    if k >= 2:
        # Jarak ke-k dari atas linkage matrix
        last_k_merges = Z[-(k - 1):, 2]
        cut_level     = (last_k_merges[0] + Z[-(k), 2]) / 2 if k <= len(Z) else None
    else:
        cut_level = None

    fig = go.Figure()
    for xs, ys in zip(icoord, dcoord):
        fig.add_trace(go.Scatter(
            x=xs, y=ys,
            mode="lines",
            line=dict(color="#185FA5", width=1.2),
            showlegend=False,
            hoverinfo="skip",
        ))

    if cut_level is not None:
        fig.add_hline(
            y=cut_level, line_dash="dash", line_color="#A32D2D",
            annotation_text=f"Cut — {k} klaster",
            annotation_position="right",
        )

    fig.update_layout(
        title=f"Dendrogram Hierarkikal ({method.capitalize()})",
        xaxis=dict(title="Indeks Sampel (skalabel)", showticklabels=False),
        yaxis=dict(title="Jarak (Linkage Distance)"),
        template="plotly_white", height=420,
        margin=dict(l=40, r=40, t=55, b=30),
    )
    return fig


# ══════════════════════════════════════════════════════════════════════════════
# HELPER: Cluster Profiling
# ══════════════════════════════════════════════════════════════════════════════

def _cluster_profile(df_orig: pd.DataFrame, cols: list[str],
                     labels: np.ndarray) -> pd.DataFrame:
    """Statistik deskriptif per klaster (mean & std) untuk setiap variabel."""
    tmp = df_orig[cols].copy()
    tmp["Klaster"] = labels + 1   # 1-based label

    rows = []
    for cl in sorted(tmp["Klaster"].unique()):
        sub = tmp[tmp["Klaster"] == cl][cols]
        row = {"Klaster": f"Klaster {cl}", "N": len(sub)}
        for c in cols:
            row[f"{c} (mean)"] = round(sub[c].mean(), 3)
            row[f"{c} (std)"]  = round(sub[c].std(), 3)
        rows.append(row)

    # Global
    row_all = {"Klaster": "Keseluruhan", "N": len(tmp)}
    for c in cols:
        row_all[f"{c} (mean)"] = round(tmp[c].mean(), 3)
        row_all[f"{c} (std)"]  = round(tmp[c].std(), 3)
    rows.append(row_all)

    return pd.DataFrame(rows)


def _plot_radar(profile_df: pd.DataFrame, cols: list[str], k: int) -> go.Figure:
    """Radar chart profil rata-rata per klaster (normalized 0-1)."""
    mean_cols = [f"{c} (mean)" for c in cols]
    # Ambil baris klaster saja (bukan keseluruhan)
    profile   = profile_df[profile_df["Klaster"] != "Keseluruhan"].copy()

    # Normalisasi 0-1 per variabel
    raw = profile[mean_cols].values.astype(float)
    col_min  = raw.min(axis=0)
    col_max  = raw.max(axis=0)
    col_rng  = np.where(col_max - col_min == 0, 1, col_max - col_min)
    norm     = (raw - col_min) / col_rng

    categories = cols + [cols[0]]   # tutup loop

    fig = go.Figure()
    for i, row in enumerate(norm):
        vals = list(row) + [row[0]]
        fig.add_trace(go.Scatterpolar(
            r=vals,
            theta=categories,
            fill="toself",
            name=f"Klaster {i + 1}",
            line=dict(color=PALETTE[i % len(PALETTE)]),
            fillcolor=PALETTE[i % len(PALETTE)],
            opacity=0.25,
        ))

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
        title="Radar Chart Profil Klaster (Ternormalisasi 0-1)",
        template="plotly_white", height=440,
        margin=dict(l=50, r=50, t=60, b=30),
    )
    return fig


def _plot_scatter2d(df_pca: pd.DataFrame, labels: np.ndarray,
                    k: int, mode: str = "kmeans") -> go.Figure:
    """Scatter 2D dari 2 komponen PCA pertama, diwarnai per klaster."""
    tmp = pd.DataFrame(df_pca, columns=["PC1", "PC2"])
    tmp["Klaster"] = [f"Klaster {l + 1}" for l in labels]

    fig = px.scatter(
        tmp, x="PC1", y="PC2", color="Klaster",
        color_discrete_sequence=PALETTE,
        title=f"Scatter Klaster via PCA ({mode.upper()})",
        template="plotly_white",
    )
    fig.update_traces(marker=dict(size=8, opacity=0.75))
    fig.update_layout(height=400, margin=dict(l=30, r=30, t=55, b=30))
    return fig


# ══════════════════════════════════════════════════════════════════════════════
# HELPER: AI Narasi
# ══════════════════════════════════════════════════════════════════════════════

def _ai_interpret_klaster(
    method: str, k: int, sil: float,
    profile_df: pd.DataFrame, cols: list[str],
    api_key: str, ai_provider: str,
) -> str:
    """Generate narasi akademis interpretasi hasil klaster."""
    from utils.ai_helpers import call_ai_api

    profile_md = profile_df.to_markdown(index=False)
    prompt = (
        f"Berikut adalah hasil **Analisis Klaster** menggunakan metode **{method}** "
        f"dengan **k = {k} klaster** pada {len(cols)} variabel: "
        f"{', '.join(cols)}.\n\n"
        f"**Silhouette Score rata-rata: {sil:.4f}**\n\n"
        f"**Tabel Profil Klaster (Mean & Std per Variabel):**\n{profile_md}\n\n"
        "Tugas Anda:\n"
        "1. Interpretasikan kualitas pengelompokan berdasarkan silhouette score.\n"
        "2. Deskripsikan karakteristik unik setiap klaster berdasarkan profil mean-nya — "
        "   beri nama/label deskriptif yang representatif untuk setiap klaster.\n"
        "3. Bahas implikasi temuan untuk riset pemasaran, pendidikan, atau sosial "
        "   (sesuaikan dengan nama variabel yang diberikan).\n"
        "4. Rekomendasikan tindak lanjut analisis atau strategi per segmen.\n"
        "Tulis dalam Bahasa Indonesia akademis, format paragraf mengalir, tanpa bullet points."
    )
    return call_ai_api(prompt, api_key, ai_provider)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN RENDER
# ══════════════════════════════════════════════════════════════════════════════

def render(ctx: dict):
    ai_enabled  = ctx["ai_enabled"]
    api_key     = ctx["anthropic_api_key"]
    ai_provider = ctx["ai_provider"]

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown(
        '<p class="rs-section-title">🗂️ Analisis Klaster</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="rs-section-sub">'
        "Segmentasi responden/objek menggunakan K-Means dan Hierarchical Clustering — "
        "lengkap dengan elbow method, silhouette score, dendrogram, dan profil klaster."
        "</p>",
        unsafe_allow_html=True,
    )

    # ── Require data ──────────────────────────────────────────────────────────
    df = require_data()
    if df is None:
        st.stop()

    num_cols = df.select_dtypes(include="number").columns.tolist()
    if len(num_cols) < 2:
        st.error("❌ Dibutuhkan minimal **2 kolom numerik** untuk analisis klaster.")
        st.stop()

    # ── Sidebar konfigurasi ───────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("---")
        st.markdown(
            "<span style='font-size:0.75rem;color:#5f8ab5;letter-spacing:0.06em;"
            "text-transform:uppercase;'>⚙️ Klaster</span>",
            unsafe_allow_html=True,
        )

    # ── Panel konfigurasi ─────────────────────────────────────────────────────
    with st.expander("⚙️ Konfigurasi Analisis", expanded=True):
        col_a, col_b = st.columns([2, 1])

        with col_a:
            sel_cols = st.multiselect(
                "Pilih variabel untuk clustering",
                options=num_cols,
                default=num_cols[:min(5, len(num_cols))],
                help="Pilih minimal 2 variabel numerik.",
            )

        with col_b:
            method_km = st.radio(
                "Metode",
                ["K-Means", "Hierarchical", "Keduanya"],
                index=2,
                help="Pilih algoritma clustering.",
            )

        col_c, col_d, col_e = st.columns(3)
        with col_c:
            k_max = st.slider("k maksimum (elbow)", 3, 15, 10, 1)
        with col_d:
            k_fixed = st.slider("k klaster final", 2, 15, 3, 1,
                                help="Jumlah klaster yang digunakan untuk analisis akhir.")
        with col_e:
            linkage_method = st.selectbox(
                "Metode linkage (Hierarchical)",
                ["ward", "complete", "average", "single"],
                index=0,
            )

    if len(sel_cols) < 2:
        st.warning("⚠️ Pilih minimal 2 variabel.")
        st.stop()

    # ── Preprocessing ─────────────────────────────────────────────────────────
    X, df_sub = _prepare_matrix(df, sel_cols)

    # PCA 2D untuk visualisasi
    from sklearn.decomposition import PCA
    pca    = PCA(n_components=2, random_state=42)
    X_pca  = pca.fit_transform(X)
    var_exp = pca.explained_variance_ratio_ * 100

    # ══════════════════════════════════════════════════════════════════════════
    # TAB UTAMA
    # ══════════════════════════════════════════════════════════════════════════

    tab_elbow, tab_kmeans, tab_hier, tab_profile, tab_ai = st.tabs([
        "📈 Elbow & Silhouette",
        "🔵 K-Means",
        "🌳 Hierarchical",
        "📊 Profil Klaster",
        "🤖 Interpretasi AI",
    ])

    # ── [1] Elbow & Silhouette ─────────────────────────────────────────────────
    with tab_elbow:
        st.markdown("### 📈 Elbow Method & Silhouette Score")
        st.markdown(
            "Grafik di bawah menampilkan **Inertia (WSS)** dan **Silhouette Score** "
            f"untuk k = 2 hingga {k_max}. Pilih k pada titik siku inertia atau "
            "puncak silhouette score."
        )

        with st.spinner("Menghitung elbow..."):
            ks, inertias, sil_scores = _compute_elbow(X, k_max=k_max)
            k_sug = _suggest_k(inertias)

        st.plotly_chart(_plot_elbow(ks, inertias, sil_scores, k_sug),
                        use_container_width=True)

        col_m1, col_m2, col_m3 = st.columns(3)
        with col_m1:
            st.markdown(f"""<div class="rs-metric">
                <div class="rs-metric-label">k Rekomendasi Otomatis</div>
                <div class="rs-metric-value">{k_sug}</div>
                <div class="rs-metric-sub">Metode second-difference</div>
            </div>""", unsafe_allow_html=True)
        with col_m2:
            best_sil_idx = int(np.argmax(sil_scores))
            st.markdown(f"""<div class="rs-metric">
                <div class="rs-metric-label">Silhouette Tertinggi</div>
                <div class="rs-metric-value">{sil_scores[best_sil_idx]:.3f}</div>
                <div class="rs-metric-sub">k = {ks[best_sil_idx]}</div>
            </div>""", unsafe_allow_html=True)
        with col_m3:
            st.markdown(f"""<div class="rs-metric">
                <div class="rs-metric-label">k yang Digunakan</div>
                <div class="rs-metric-value">{k_fixed}</div>
                <div class="rs-metric-sub">Atur di panel konfigurasi</div>
            </div>""", unsafe_allow_html=True)

        # Tabel inertia & silhouette
        with st.expander("📋 Tabel Lengkap Inertia & Silhouette"):
            df_elbow = pd.DataFrame({
                "k": ks,
                "Inertia (WSS)": [round(v, 2) for v in inertias],
                "Silhouette Score": [round(v, 4) for v in sil_scores],
            })
            st.dataframe(df_elbow, use_container_width=True, hide_index=True)

        # Panduan interpretasi
        st.markdown(
            '<div class="rs-narasi">'
            "📖 <b>Panduan Interpretasi:</b><br/>"
            "• <b>Elbow (Siku Inertia):</b> Titik di mana penambahan k tidak lagi mengurangi "
            "inertia secara signifikan — itulah k optimal.<br/>"
            "• <b>Silhouette Score:</b> Berkisar 0–1. "
            "Nilai &gt; 0.5 = klaster terpisah baik; &gt; 0.7 = sangat baik; "
            "nilai negatif = sampel mungkin salah klaster.<br/>"
            "• Pilih k yang memaksimalkan silhouette <i>sekaligus</i> berada di siku inertia."
            "</div>",
            unsafe_allow_html=True,
        )

    # ── [2] K-Means ────────────────────────────────────────────────────────────
    with tab_kmeans:
        st.markdown(f"### 🔵 K-Means Clustering (k = {k_fixed})")

        with st.spinner("Menjalankan K-Means..."):
            km_model  = KMeans(n_clusters=k_fixed, random_state=42, n_init="auto")
            km_labels = km_model.fit_predict(X)
            km_sil    = silhouette_score(X, km_labels)

        # Metrik
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"""<div class="rs-metric">
                <div class="rs-metric-label">Silhouette Score</div>
                <div class="rs-metric-value">{km_sil:.4f}</div>
                <div class="rs-metric-sub">{"Baik ✓" if km_sil >= 0.5 else "Cukup" if km_sil >= 0.3 else "Rendah"}</div>
            </div>""", unsafe_allow_html=True)
        with col2:
            st.markdown(f"""<div class="rs-metric">
                <div class="rs-metric-label">Inertia (WSS)</div>
                <div class="rs-metric-value">{km_model.inertia_:.1f}</div>
                <div class="rs-metric-sub">Within-cluster sum of squares</div>
            </div>""", unsafe_allow_html=True)
        with col3:
            counts = pd.Series(km_labels).value_counts().sort_index()
            sizes  = " | ".join([f"K{i+1}={c}" for i, c in enumerate(counts)])
            st.markdown(f"""<div class="rs-metric">
                <div class="rs-metric-label">Ukuran Klaster</div>
                <div class="rs-metric-value">{k_fixed}</div>
                <div class="rs-metric-sub">{sizes}</div>
            </div>""", unsafe_allow_html=True)

        c_left, c_right = st.columns(2)
        with c_left:
            st.plotly_chart(
                _plot_scatter2d(X_pca, km_labels, k_fixed, "kmeans"),
                use_container_width=True,
            )
            st.caption(
                f"PCA variance explained: PC1 = {var_exp[0]:.1f}%, PC2 = {var_exp[1]:.1f}%"
            )
        with c_right:
            st.plotly_chart(
                _plot_silhouette(X, km_labels, k_fixed),
                use_container_width=True,
            )

        # Distribusi klaster
        dist_df = pd.DataFrame({
            "Klaster": [f"Klaster {i + 1}" for i in counts.index],
            "Jumlah (N)": counts.values,
            "Persentase (%)": [f"{v / len(km_labels) * 100:.1f}%" for v in counts.values],
        })
        st.markdown("**Distribusi Anggota per Klaster:**")
        st.dataframe(dist_df, use_container_width=True, hide_index=True)

        # Simpan label K-Means ke session
        st.session_state["_km_labels"]  = km_labels
        st.session_state["_km_sil"]     = km_sil
        st.session_state["_km_profile"] = _cluster_profile(df, sel_cols, km_labels)

    # ── [3] Hierarchical ───────────────────────────────────────────────────────
    with tab_hier:
        st.markdown(f"### 🌳 Hierarchical Clustering (k = {k_fixed}, linkage = {linkage_method})")

        with st.spinner("Menghitung dendrogram..."):
            # Dendrogram
            fig_dend = _plot_dendrogram(X, method=linkage_method, k=k_fixed)

            # Klaster label via AgglomerativeClustering
            agg_model  = AgglomerativeClustering(
                n_clusters=k_fixed, linkage=linkage_method
            )
            agg_labels = agg_model.fit_predict(X)
            agg_sil    = silhouette_score(X, agg_labels)

        # Metrik
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"""<div class="rs-metric">
                <div class="rs-metric-label">Silhouette Score</div>
                <div class="rs-metric-value">{agg_sil:.4f}</div>
                <div class="rs-metric-sub">{"Baik ✓" if agg_sil >= 0.5 else "Cukup" if agg_sil >= 0.3 else "Rendah"}</div>
            </div>""", unsafe_allow_html=True)
        with col2:
            agg_counts = pd.Series(agg_labels).value_counts().sort_index()
            sizes_agg  = " | ".join([f"K{i+1}={c}" for i, c in enumerate(agg_counts)])
            st.markdown(f"""<div class="rs-metric">
                <div class="rs-metric-label">Ukuran Klaster</div>
                <div class="rs-metric-value">{k_fixed}</div>
                <div class="rs-metric-sub">{sizes_agg}</div>
            </div>""", unsafe_allow_html=True)
        with col3:
            better = "K-Means" if st.session_state.get("_km_sil", 0) > agg_sil else "Hierarchical"
            st.markdown(f"""<div class="rs-metric">
                <div class="rs-metric-label">Metode Lebih Baik</div>
                <div class="rs-metric-value" style="font-size:1.1rem;">{better}</div>
                <div class="rs-metric-sub">Berdasarkan silhouette</div>
            </div>""", unsafe_allow_html=True)

        st.plotly_chart(fig_dend, use_container_width=True)

        c_left2, c_right2 = st.columns(2)
        with c_left2:
            st.plotly_chart(
                _plot_scatter2d(X_pca, agg_labels, k_fixed, "hierarchical"),
                use_container_width=True,
            )
        with c_right2:
            st.plotly_chart(
                _plot_silhouette(X, agg_labels, k_fixed),
                use_container_width=True,
            )

        st.session_state["_agg_labels"]  = agg_labels
        st.session_state["_agg_sil"]     = agg_sil
        st.session_state["_agg_profile"] = _cluster_profile(df, sel_cols, agg_labels)

        st.markdown(
            '<div class="rs-narasi">'
            "📖 <b>Cara membaca dendrogram:</b> Garis horizontal pada ketinggian tinggi "
            "merepresentasikan merger dua klaster besar. Garis putus-putus merah adalah "
            "<i>cut-off</i> untuk memperoleh jumlah klaster yang dipilih. "
            "Semakin panjang garis vertikal, semakin berbeda dua klaster yang digabungkan — "
            "artinya pengelompokan di bawahnya lebih homogen."
            "</div>",
            unsafe_allow_html=True,
        )

    # ── [4] Profil Klaster ─────────────────────────────────────────────────────
    with tab_profile:
        st.markdown("### 📊 Profil Klaster")

        sel_method_profile = st.radio(
            "Tampilkan profil dari metode:",
            ["K-Means", "Hierarchical"],
            horizontal=True,
            key="profile_method_sel",
        )

        labels_for_profile = (
            st.session_state.get("_km_labels", None)
            if sel_method_profile == "K-Means"
            else st.session_state.get("_agg_labels", None)
        )

        if labels_for_profile is None:
            # Hitung ulang jika belum ada (tab diakses pertama kali)
            if sel_method_profile == "K-Means":
                km_tmp = KMeans(n_clusters=k_fixed, random_state=42, n_init="auto")
                labels_for_profile = km_tmp.fit_predict(X)
            else:
                agg_tmp = AgglomerativeClustering(n_clusters=k_fixed, linkage=linkage_method)
                labels_for_profile = agg_tmp.fit_predict(X)

        profile_df = _cluster_profile(df, sel_cols, labels_for_profile)

        st.markdown(f"**Statistik Deskriptif per Klaster ({sel_method_profile}):**")
        st.dataframe(profile_df, use_container_width=True, hide_index=True)

        # Radar chart (butuh ≥ 3 variabel untuk bermakna)
        if len(sel_cols) >= 3:
            st.plotly_chart(
                _plot_radar(profile_df, sel_cols, k_fixed),
                use_container_width=True,
            )
        else:
            # Bar chart sederhana jika hanya 2 variabel
            mean_cols = [c for c in profile_df.columns if "(mean)" in c]
            fig_bar = go.Figure()
            for i, col in enumerate(mean_cols):
                var_name = col.replace(" (mean)", "")
                fig_bar.add_trace(go.Bar(
                    name=var_name,
                    x=profile_df[profile_df["Klaster"] != "Keseluruhan"]["Klaster"],
                    y=profile_df[profile_df["Klaster"] != "Keseluruhan"][col],
                    marker_color=PALETTE[i % len(PALETTE)],
                ))
            fig_bar.update_layout(
                barmode="group", title="Profil Rata-rata per Klaster",
                template="plotly_white", height=380,
                margin=dict(l=30, r=30, t=55, b=30),
            )
            st.plotly_chart(fig_bar, use_container_width=True)

        # Download label klaster
        st.markdown("---")
        st.markdown("**💾 Download Dataset dengan Label Klaster:**")
        df_labeled = df.copy()
        df_labeled[f"Klaster_{sel_method_profile}"] = labels_for_profile + 1
        csv_bytes = df_labeled.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️ Download CSV dengan Label Klaster",
            data=csv_bytes,
            file_name=f"data_klaster_{sel_method_profile.lower().replace('-','_')}.csv",
            mime="text/csv",
        )

        # Simpan ke session state untuk export.py
        sil_final = (
            st.session_state.get("_km_sil", 0)
            if sel_method_profile == "K-Means"
            else st.session_state.get("_agg_sil", 0)
        )

        st.session_state["klaster_result"] = {
            "method":       sel_method_profile,
            "k":            k_fixed,
            "cols":         sel_cols,
            "labels":       labels_for_profile,
            "silhouette":   sil_final,
            "profile_df":   profile_df,
            "linkage":      linkage_method,
        }

    # ── [5] Interpretasi AI ────────────────────────────────────────────────────
    with tab_ai:
        st.markdown("### 🤖 Interpretasi AI")

        if not ai_enabled:
            st.error(
                "🔒 Fitur interpretasi AI memerlukan **API Key**. "
                "Masukkan di sidebar untuk mengaktifkan."
            )
            st.info("Dapatkan API Key di [console.anthropic.com](https://console.anthropic.com)")
            st.stop()

        # Pastikan ada hasil yang bisa diinterpretasikan
        km_labels_ai  = st.session_state.get("_km_labels", None)
        km_sil_ai     = st.session_state.get("_km_sil", None)
        km_profile_ai = st.session_state.get("_km_profile", None)

        if km_labels_ai is None:
            # Jalankan K-Means jika user langsung ke tab AI
            km_tmp = KMeans(n_clusters=k_fixed, random_state=42, n_init="auto")
            km_labels_ai  = km_tmp.fit_predict(X)
            km_sil_ai     = silhouette_score(X, km_labels_ai)
            km_profile_ai = _cluster_profile(df, sel_cols, km_labels_ai)

        ai_method_sel = st.radio(
            "Interpretasikan hasil dari:",
            ["K-Means", "Hierarchical"],
            horizontal=True,
            key="ai_method_sel",
        )

        if ai_method_sel == "K-Means":
            interp_labels  = km_labels_ai
            interp_sil     = km_sil_ai
            interp_profile = km_profile_ai
        else:
            interp_labels  = st.session_state.get("_agg_labels", km_labels_ai)
            interp_sil     = st.session_state.get("_agg_sil", km_sil_ai)
            interp_profile = st.session_state.get("_agg_profile", km_profile_ai)
            if interp_labels is None:
                agg_tmp = AgglomerativeClustering(n_clusters=k_fixed, linkage=linkage_method)
                interp_labels  = agg_tmp.fit_predict(X)
                interp_sil     = silhouette_score(X, interp_labels)
                interp_profile = _cluster_profile(df, sel_cols, interp_labels)

        # Key "klaster" konsisten dengan export.py collect_session_results()
        if "ai_cache" not in st.session_state:
            st.session_state.ai_cache = {}

        if st.button("🤖 Generate Interpretasi AI", type="primary"):
            with st.spinner("🤖 AI sedang menganalisis profil klaster..."):
                narasi = _ai_interpret_klaster(
                    method=ai_method_sel,
                    k=k_fixed,
                    sil=interp_sil,
                    profile_df=interp_profile,
                    cols=sel_cols,
                    api_key=api_key,
                    ai_provider=ai_provider,
                )
            st.session_state.ai_cache["klaster"] = narasi

        if st.session_state.ai_cache.get("klaster"):
            st.markdown(
                f'<div class="rs-ai-narasi">'
                f'<span class="rs-ai-badge">✨ AI — {ai_provider.split("(")[0].strip()}</span><br/>'
                + st.session_state.ai_cache["klaster"].replace("\n", "<br/>")
                + "</div>",
                unsafe_allow_html=True,
            )
        else:
            st.info(
                "💡 Klik tombol di atas untuk mendapatkan narasi akademis otomatis "
                "tentang karakteristik dan implikasi setiap klaster."
            )

        # Referensi metodologis
        with st.expander("📚 Referensi Metodologi"):
            st.markdown("""
**K-Means Clustering** (MacQueen, 1967; Lloyd, 1982):
- Algoritma iteratif yang meminimalkan *within-cluster sum of squares* (WCSS/Inertia).
- Elbow Method: identifikasi k optimal pada titik siku kurva inertia (Thorndike, 1953).
- Asumsi: klaster berbentuk bulat, ukuran relatif seimbang.

**Agglomerative Hierarchical Clustering** (Ward, 1963):
- *Bottom-up*: setiap sampel awalnya klaster sendiri, lalu digabungkan secara hierarkikal.
- Linkage Ward meminimalkan varians dalam klaster — umumnya menghasilkan klaster paling kompak.

**Silhouette Score** (Rousseeuw, 1987):
- s(i) = (b(i) − a(i)) / max{a(i), b(i)}, di mana a = jarak rata-rata dalam klaster, b = jarak ke klaster terdekat.
- Rentang −1 sampai 1. Nilai > 0.5 umumnya diterima; > 0.7 sangat baik.

**Referensi APA:**
> MacQueen, J. (1967). *Some methods for classification and analysis of multivariate observations.* Proceedings of the Fifth Berkeley Symposium on Mathematical Statistics and Probability, 1, 281–297.

> Rousseeuw, P. J. (1987). Silhouettes: A graphical aid to the interpretation and validation of cluster analysis. *Journal of Computational and Applied Mathematics, 20*, 53–65.

> Ward, J. H. (1963). Hierarchical grouping to optimize an objective function. *Journal of the American Statistical Association, 58*(301), 236–244.
            """)
