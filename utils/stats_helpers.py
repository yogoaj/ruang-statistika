"""
utils/stats_helpers.py — Reusable statistical computation functions
Ruang Statistika v4.0 (Enhanced with Categorical Encoding)
"""

import numpy as np
import pandas as pd
from scipy import stats
import streamlit as st
from typing import Optional, List, Tuple


# ── Data Loading ──────────────────────────────────────────────────────────────

def load_data(uploaded_file) -> Optional[pd.DataFrame]:
    """Memuat file CSV, Excel, SPSS (.sav), Stata (.dta), atau teks (.txt)."""
    name = uploaded_file.name.lower()

    # ── CSV ──────────────────────────────────────────────────────────────────
    if name.endswith(".csv"):
        for enc in ["utf-8", "latin-1", "iso-8859-1"]:
            try:
                return pd.read_csv(uploaded_file, encoding=enc)
            except Exception:
                uploaded_file.seek(0)

    # ── Excel ─────────────────────────────────────────────────────────────────
    elif name.endswith((".xlsx", ".xls")):
        return pd.read_excel(uploaded_file)

    # ── SPSS (.sav) ───────────────────────────────────────────────────────────
    elif name.endswith(".sav"):
        try:
            import pyreadstat
            import tempfile, os
            raw_bytes = uploaded_file.read()
            with tempfile.NamedTemporaryFile(suffix=".sav", delete=False) as tmp:
                tmp.write(raw_bytes)
                tmp_path = tmp.name
            try:
                df, meta = pyreadstat.read_sav(tmp_path)
                # Terapkan value labels SPSS sebagai string bila ada
                if meta.variable_value_labels:
                    for col, labels in meta.variable_value_labels.items():
                        if col in df.columns:
                            df[col] = df[col].map(labels).fillna(df[col])
                return df
            finally:
                os.unlink(tmp_path)
        except ImportError:
            st.error(
                "❌ Paket **pyreadstat** belum terinstall. "
                "Jalankan `pip install pyreadstat` lalu restart aplikasi."
            )
        except Exception as e:
            st.error(f"❌ Gagal membaca file SPSS: {e}")

    # ── Stata (.dta) ──────────────────────────────────────────────────────────
    elif name.endswith(".dta"):
        try:
            return pd.read_stata(uploaded_file)
        except Exception as e:
            st.error(f"❌ Gagal membaca file Stata: {e}")

    # ── Teks (.txt) — deteksi delimiter otomatis ──────────────────────────────
    elif name.endswith(".txt"):
        for sep in ["\t", ";", "|", ","]:
            try:
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file, sep=sep, encoding="utf-8")
                if df.shape[1] > 1:          # minimal 2 kolom = delimiter ditemukan
                    return df
            except Exception:
                pass
        # Fallback: coba latin-1
        for sep in ["\t", ";", "|", ","]:
            try:
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file, sep=sep, encoding="latin-1")
                if df.shape[1] > 1:
                    return df
            except Exception:
                pass
        # Fallback terakhir: whitespace
        try:
            uploaded_file.seek(0)
            return pd.read_csv(uploaded_file, sep=r"\s+", engine="python", encoding="utf-8")
        except Exception as e:
            st.error(f"❌ Gagal membaca file TXT (delimiter tidak dikenali): {e}")

    return None


@st.cache_data
def auto_clean(df: pd.DataFrame) -> Tuple[pd.DataFrame, dict]:
    """Pembersihan data otomatis: hanya hapus duplikat, biarkan missing."""
    report = {
        "original_rows": len(df),
        "original_cols": len(df.columns),
    }
    missing = df.isnull().sum()
    report["total_missing"] = int(missing.sum())
    report["missing_per_col"] = missing[missing > 0].to_dict()
    report["duplicates"] = int(df.duplicated().sum())

    df_clean = df.drop_duplicates().copy()
    
    # Deteksi kolom numerik asli[cite: 8]
    numeric_cols = df_clean.select_dtypes(include=[np.number]).columns.tolist()
    
    # Deteksi kolom non-numerik[cite: 8]
    non_numeric = [c for c in df_clean.columns if c not in numeric_cols]
    
    # Identifikasi kolom kategorik potensial (nilai unik < 15) untuk di-encode[cite: 9]
    encodable_cols = [c for c in non_numeric if df_clean[c].nunique() < 15]
    
    report["numeric_cols"] = numeric_cols
    report["non_numeric_cols"] = non_numeric
    report["encodable_cols"] = encodable_cols
    report["rows_after_clean"] = len(df_clean)
    
    return df_clean, report


# ── Encoding Helper (Fungsi yang sebelumnya menyebabkan error) ────────────────

def encode_categorical(df: pd.DataFrame, target_cols: list) -> Tuple[pd.DataFrame, dict]:
    """
    Mengubah kolom teks menjadi angka (Label Encoding) dan MEMASTIKAN tipe data numerik.
    """
    df_encoded = df.copy()
    mapping_log = {}
    
    for col in target_cols:
        if col in df.columns:
            # Ambil nilai unik dan buat mapping
            unique_vals = sorted(df[col].dropna().unique())
            mapping = {val: i for i, val in enumerate(unique_vals)}
            
            # 1. Map nilainya
            df_encoded[col] = df_encoded[col].map(mapping)
            
            # 2. PAKSA tipe data menjadi numerik (Sangat Penting!)
            df_encoded[col] = pd.to_numeric(df_encoded[col], errors='coerce')
            
            mapping_log[col] = mapping
            
    return df_encoded, mapping_log

# ── Descriptive & Normality ───────────────────────────────────────────────────

@st.cache_data
def descriptive_stats(df: pd.DataFrame, cols: list) -> pd.DataFrame:
    rows = []
    for c in cols:
        # Konversi ke numerik secara paksa untuk menangani hasil encoding[cite: 8]
        s = pd.to_numeric(df[c], errors='coerce').dropna()
        if len(s) == 0:
            continue
        rows.append({
            "Variabel": c,
            "N": int(len(s)),
            "Mean": round(float(s.mean()), 3),
            "Median": round(float(s.median()), 3),
            "Std Dev": round(float(s.std()), 3),
            "Min": round(float(s.min()), 3),
            "Max": round(float(s.max()), 3),
            "Skewness": round(float(stats.skew(s)), 3),
            "Kurtosis": round(float(stats.kurtosis(s)), 3),
        })
    return pd.DataFrame(rows)


@st.cache_data
def normality_test(df: pd.DataFrame, cols: list) -> pd.DataFrame:
    rows = []
    for c in cols:
        s = pd.to_numeric(df[c], errors='coerce').dropna()
        if len(s) < 3:
            continue
        samp = s if len(s) <= 5000 else s.sample(5000, random_state=42)
        stat_w, p = stats.shapiro(samp)
        rows.append({
            "Variabel": c,
            "Statistik W": round(float(stat_w), 4),
            "p-value": round(float(p), 4),
            "Normal (α=0.05)": "Ya ✓" if p > 0.05 else "Tidak ✗",
        })
    return pd.DataFrame(rows)


# ── Validity & Reliability ────────────────────────────────────────────────────

@st.cache_data
def pearson_validity(df: pd.DataFrame, cols: list, r_tabel: float = 0.3) -> pd.DataFrame:
    if len(cols) < 2:
        return pd.DataFrame()
    subset = df[cols].apply(pd.to_numeric, errors='coerce').dropna()
    total = subset.sum(axis=1)
    rows = []
    for c in cols:
        try:
            if subset[c].std() == 0:
                rows.append({
                    "Butir": c, "r-hitung": 0.0, "r-tabel": r_tabel,
                    "p-value": 1.0, "Status": "Tidak Valid (Varian 0)"
                })
                continue
            r, p = stats.pearsonr(subset[c], total)
            rows.append({
                "Butir": c,
                "r-hitung": round(float(r), 4),
                "r-tabel": r_tabel,
                "p-value": round(float(p), 4),
                "Status": "Valid ✓" if r >= r_tabel else "Tidak Valid ✗",
            })
        except Exception:
            rows.append({
                "Butir": c, "r-hitung": 0, "r-tabel": r_tabel,
                "p-value": 1, "Status": "Error"
            })
    return pd.DataFrame(rows)


@st.cache_data
def calc_cronbach(df: pd.DataFrame, cols: list) -> Optional[float]:
    subset = df[cols].apply(pd.to_numeric, errors='coerce').dropna()
    if subset.shape[1] < 2:
        return None
    try:
        k = subset.shape[1]
        item_var = subset.var(axis=0, ddof=1).sum()
        total_var = subset.sum(axis=1).var(ddof=1)
        if total_var == 0:
            return 0.0
        return round(float((k / (k - 1)) * (1 - item_var / total_var)), 4)
    except Exception:
        return 0.0


# ── OLS & Mediation ───────────────────────────────────────────────────────────

def ols_advanced(df: pd.DataFrame, y_col: str, X_vars: list):
    import statsmodels.api as sm
    from statsmodels.stats.outliers_influence import variance_inflation_factor

    # Konversi ke numerik untuk mendukung data hasil encoding[cite: 8]
    subset = df[[y_col] + X_vars].apply(pd.to_numeric, errors='coerce').dropna()
    X = subset[X_vars]
    y = subset[y_col]
    X_const = sm.add_constant(X)
    model = sm.OLS(y, X_const).fit()

    vif = pd.DataFrame({
        "Variabel": X_const.columns,
        "VIF": [variance_inflation_factor(X_const.values, i)
                for i in range(X_const.shape[1])]
    })
    vif = vif[vif["Variabel"] != "const"].reset_index(drop=True)
    vif["VIF"] = vif["VIF"].round(4)
    vif["Multikolinear?"] = vif["VIF"].apply(
        lambda v: "⚠️ Ya (VIF>10)" if v > 10 else "✓ Tidak"
    )

    abs_resid = np.abs(model.resid)
    glejser = sm.OLS(abs_resid, X_const).fit()

    return model, vif, glejser


def run_mediation(df: pd.DataFrame, x_col: str, m_col: str, y_col: str) -> tuple:
    import statsmodels.api as sm

    subset = df[[x_col, m_col, y_col]].apply(pd.to_numeric, errors='coerce').dropna()

    X1 = sm.add_constant(subset[[x_col]])
    m_model = sm.OLS(subset[m_col], X1).fit()

    X2 = sm.add_constant(subset[[x_col, m_col]])
    y_model = sm.OLS(subset[y_col], X2).fit()

    X3 = sm.add_constant(subset[[x_col]])
    c_model = sm.OLS(subset[y_col], X3).fit()

    a = m_model.params[x_col]
    b = y_model.params[m_col]
    sa = m_model.bse[x_col]
    sb = y_model.bse[m_col]
    indirect = a * b
    se_indirect = np.sqrt(b ** 2 * sa ** 2 + a ** 2 * sb ** 2)
    z_sobel = indirect / se_indirect if se_indirect > 0 else 0
    p_sobel = 2 * (1 - stats.norm.cdf(abs(z_sobel)))

    mediation_info = {
        "a (X→M)": round(a, 4),
        "b (M→Y|X)": round(b, 4),
        "c (total X→Y)": round(c_model.params[x_col], 4),
        "c' (direct X→Y)": round(y_model.params[x_col], 4),
        "Indirect (a×b)": round(indirect, 4),
        "SE Indirect": round(se_indirect, 4),
        "z Sobel": round(z_sobel, 4),
        "p Sobel": round(p_sobel, 4),
    }
    return m_model, y_model, c_model, mediation_info


# ── Narasi Rule-Based ─────────────────────────────────────────────────────────

def interpret_skew(sk: float) -> str:
    if abs(sk) < 0.5:
        return "distribusi mendekati simetris"
    return "distribusi condong ke kanan (positif)" if sk > 0.5 else "distribusi condong ke kiri (negatif)"


def narrate_descriptive(stats_df: pd.DataFrame) -> str:
    lines = []
    for _, row in stats_df.iterrows():
        lines.append(
            f"**{row['Variabel']}** — Mean = {row['Mean']}, SD = {row['Std Dev']}. "
            f"Dengan skewness = {row['Skewness']}, {interpret_skew(row['Skewness'])}."
        )
    return "\n\n".join(lines)


def narrate_validity(val_df: pd.DataFrame, r_tabel: float) -> str:
    n_valid = (val_df["Status"].str.contains("Valid ✓")).sum()
    invalid = val_df[val_df["Status"].str.contains("Tidak Valid")]["Butir"].tolist()
    txt = f"Dari {len(val_df)} butir, **{n_valid}** dinyatakan valid (r-hitung ≥ {r_tabel}). "
    if invalid:
        txt += f"Butir **{', '.join(invalid)}** tidak lolos uji validitas dan perlu ditinjau ulang."
    else:
        txt += "Seluruh butir lolos uji validitas."
    return txt


def narrate_alpha(alpha: Optional[float]) -> str:
    if alpha is None:
        return "Gagal menghitung Alpha."
    if alpha >= 0.9:
        kat = "sangat tinggi (excellent)"
    elif alpha >= 0.8:
        kat = "tinggi (good)"
    elif alpha >= 0.7:
        kat = "cukup (acceptable)"
    elif alpha >= 0.6:
        kat = "kurang (questionable)"
    else:
        kat = "rendah (poor)"
    status = "reliabel" if alpha >= 0.7 else "tidak reliabel"
    return (
        f"Berdasarkan kriteria Ghozali (2018), instrumen dinyatakan reliabel jika "
        f"Cronbach's Alpha > 0.70. Hasil menunjukkan α = **{alpha}** (kategori **{kat}**), "
        f"sehingga instrumen ini dinyatakan **{status}**."
    )


def narrate_correlation(corr: pd.DataFrame) -> str:
    cols = corr.columns.tolist()
    pairs = []
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            r = corr.iloc[i, j]
            if abs(r) >= 0.7:
                arah = "positif" if r > 0 else "negatif"
                pairs.append(f"**{cols[i]}** & **{cols[j]}** (r = {r:.3f}, kuat {arah})")
    if not pairs:
        return "Tidak ditemukan hubungan yang sangat kuat (|r| ≥ 0.7) antar variabel."
    return "Hubungan kuat ditemukan antara: " + "; ".join(pairs) + "."


# ── Session state helpers ─────────────────────────────────────────────────────

def ss_get(key: str, default=None):
    return st.session_state.get(key, default)


def require_data():
    df = ss_get("df_clean")
    if df is None:
        st.warning("⚠️ Silakan unggah data terlebih dahulu melalui menu **📁 Upload & Cleaning**.")
    return df


def require_cols(df: pd.DataFrame, include_categorical: bool = False) -> Optional[list]:
    cols = ss_get("selected_cols", [])
    if not cols and df is not None:
        cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if include_categorical:
            cols += df.select_dtypes(include=['object']).columns.tolist()
            
    if not cols:
        st.warning("⚠️ Pilih minimal 1 kolom pada menu Upload & Cleaning.")
        return None
    return cols