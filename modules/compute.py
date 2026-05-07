"""
modules/compute.py — Compute Variabel Baru (Free)
Ruang Statistika v4.0

Fitur:
- Buat variabel baru dari ekspresi matematis (formula builder)
- Aggregate items menjadi skor komposit (sum, mean, min, max)
- Recode variabel (manual mapping atau kondisional)
- Standardize / Normalize (Z-score, Min-Max)
- Lag / Difference untuk data time-series
- Log / Power transform
- Preview & konfirmasi sebelum simpan ke dataset
"""

import re
import numpy as np
import pandas as pd
import streamlit as st

from utils.stats_helpers import require_data, ss_get


# ─────────────────────────────────────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────────────────────────────────────

def _safe_colname(name: str) -> str:
    """Bersihkan nama kolom: hapus karakter aneh, ganti spasi dengan _."""
    name = name.strip()
    name = re.sub(r"[^\w\s]", "", name)
    name = re.sub(r"\s+", "_", name)
    return name


def _validate_colname(new_name: str, df: pd.DataFrame) -> tuple[bool, str]:
    """Validasi nama kolom baru. Return (ok, pesan)."""
    if not new_name:
        return False, "Nama variabel tidak boleh kosong."
    if new_name[0].isdigit():
        return False, "Nama variabel tidak boleh diawali angka."
    if new_name in df.columns:
        return False, f"Kolom '{new_name}' sudah ada. Pilih nama lain atau centang 'Timpa kolom'."
    return True, ""


def _apply_formula(df: pd.DataFrame, formula: str) -> pd.Series:
    """
    Evaluasi formula menggunakan kolom df sebagai variabel lokal.
    Fungsi yang tersedia: np (numpy), abs, log, exp, sqrt, round.
    """
    # Buat namespace aman: kolom df + fungsi numpy umum
    local_ns = {col: pd.to_numeric(df[col], errors="coerce") for col in df.columns}
    local_ns.update({
        "np": np, "abs": np.abs, "log": np.log, "log10": np.log10,
        "exp": np.exp, "sqrt": np.sqrt, "round": np.round,
        "sin": np.sin, "cos": np.cos, "tan": np.tan,
        "mean": np.mean, "std": np.std, "sum": np.sum,
        "nan": np.nan, "inf": np.inf,
    })
    result = eval(formula, {"__builtins__": {}}, local_ns)  # noqa: S307
    return pd.Series(result, index=df.index)


def _compute_composite(df: pd.DataFrame, cols: list, method: str,
                        weight_map: dict | None = None) -> pd.Series:
    """Hitung skor komposit dari beberapa kolom."""
    subset = df[cols].apply(pd.to_numeric, errors="coerce")
    if weight_map:
        weights = pd.Series({c: weight_map.get(c, 1.0) for c in cols})
        weighted = subset.multiply(weights, axis=1)
        return weighted.sum(axis=1) / weights.sum()
    if method == "sum":
        return subset.sum(axis=1)
    elif method == "mean":
        return subset.mean(axis=1)
    elif method == "min":
        return subset.min(axis=1)
    elif method == "max":
        return subset.max(axis=1)
    elif method == "median":
        return subset.median(axis=1)
    elif method == "std":
        return subset.std(axis=1)
    raise ValueError(f"Method tidak dikenal: {method}")


def _recode_manual(series: pd.Series, mapping_text: str) -> pd.Series:
    """
    Recode nilai berdasarkan mapping teks format:
    nilai_lama -> nilai_baru (satu per baris)
    Contoh:
        1 -> Rendah
        2 -> Sedang
        3 -> Tinggi
    """
    mapping = {}
    for line in mapping_text.strip().splitlines():
        line = line.strip()
        if not line or "->" not in line:
            continue
        left, right = line.split("->", 1)
        left, right = left.strip(), right.strip()
        # Coba konversi numerik
        try:
            left = float(left) if "." in left else int(left)
        except ValueError:
            pass
        try:
            right = float(right) if "." in right else int(right)
        except ValueError:
            pass
        mapping[left] = right

    # Coba map numerik dulu, lalu string
    result = series.copy()
    try:
        numeric_s = pd.to_numeric(series, errors="coerce")
        result = numeric_s.map(mapping)
        # Fallback ke string jika ada NaN dari mapping
        if result.isna().any():
            str_map = {str(k): v for k, v in mapping.items()}
            result = result.fillna(series.astype(str).map(str_map))
    except Exception:
        result = series.astype(str).map({str(k): v for k, v in mapping.items()})

    return result


def _recode_conditional(df: pd.DataFrame, source_col: str,
                         conditions: list[tuple]) -> pd.Series:
    """
    Recode berdasarkan kondisi numerik bertingkat.
    conditions: list of (operator, threshold, new_label)
    Operator: '<', '<=', '>', '>=', '==', '!='
    """
    s = pd.to_numeric(df[source_col], errors="coerce")
    result = pd.Series(np.nan, index=df.index, dtype=object)

    OPS = {
        "<":  lambda x, v: x < v,
        "<=": lambda x, v: x <= v,
        ">":  lambda x, v: x > v,
        ">=": lambda x, v: x >= v,
        "==": lambda x, v: x == v,
        "!=": lambda x, v: x != v,
    }

    for op, threshold, label in conditions:
        if op not in OPS:
            continue
        try:
            mask = OPS[op](s, float(threshold))
            result = result.where(~mask, other=label)
        except Exception:
            pass
    return result


def _zscore(series: pd.Series) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce")
    return (s - s.mean()) / s.std()


def _minmax(series: pd.Series, new_min: float = 0.0,
            new_max: float = 1.0) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce")
    s_min, s_max = s.min(), s.max()
    if s_max == s_min:
        return s - s_min
    return (s - s_min) / (s_max - s_min) * (new_max - new_min) + new_min


def _log_transform(series: pd.Series, base: str = "natural",
                   shift: float = 0.0) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce") + shift
    if base == "natural":
        return np.log(s)
    elif base == "log10":
        return np.log10(s)
    elif base == "log2":
        return np.log2(s)
    raise ValueError(f"Base tidak dikenal: {base}")


def _lag_diff(series: pd.Series, periods: int = 1,
              mode: str = "lag") -> pd.Series:
    s = pd.to_numeric(series, errors="coerce")
    if mode == "lag":
        return s.shift(periods)
    elif mode == "lead":
        return s.shift(-periods)
    elif mode == "diff":
        return s.diff(periods)
    elif mode == "pct_change":
        return s.pct_change(periods)
    raise ValueError(f"Mode tidak dikenal: {mode}")


# ─────────────────────────────────────────────────────────────────────────────
# Log Riwayat Compute
# ─────────────────────────────────────────────────────────────────────────────

def _log_compute(entry: dict):
    """Tambah entri ke log riwayat compute di session_state."""
    if "compute_log" not in st.session_state:
        st.session_state.compute_log = []
    st.session_state.compute_log.append(entry)


def _render_compute_log():
    log = st.session_state.get("compute_log", [])
    if not log:
        return
    with st.expander(f"📋 Riwayat Compute ({len(log)} operasi)", expanded=False):
        for i, entry in enumerate(reversed(log), 1):
            st.markdown(
                f"**{i}.** `{entry['new_col']}` ← {entry['method']} "
                f"({entry.get('source', '')})"
            )
        if st.button("🗑️ Hapus Log", key="clear_compute_log"):
            st.session_state.compute_log = []
            st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# Preview helper
# ─────────────────────────────────────────────────────────────────────────────

def _preview_series(series: pd.Series, new_name: str, df: pd.DataFrame,
                    n_rows: int = 8):
    """Tampilkan preview kolom baru vs data asli."""
    st.markdown("**👁️ Preview (8 baris pertama):**")
    preview_df = df.head(n_rows).copy()
    preview_df[f"[BARU] {new_name}"] = series.head(n_rows).values
    st.dataframe(
        preview_df[[f"[BARU] {new_name}"] + list(df.columns[:4])],
        use_container_width=True,
        hide_index=True,
    )
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Non-null", int(series.notna().sum()))
    with col2:
        st.metric("Missing", int(series.isna().sum()))
    if pd.api.types.is_numeric_dtype(series):
        c1, c2, c3 = st.columns(3)
        c1.metric("Mean", f"{series.mean():.4f}")
        c2.metric("Min", f"{series.min():.4f}")
        c3.metric("Max", f"{series.max():.4f}")


def _save_to_dataset(df: pd.DataFrame, new_name: str, series: pd.Series,
                     overwrite: bool = False) -> pd.DataFrame:
    """Simpan kolom baru ke dataframe dan update session_state."""
    if new_name in df.columns and not overwrite:
        st.error(f"Kolom '{new_name}' sudah ada. Aktifkan 'Timpa kolom' untuk mengganti.")
        return df
    df = df.copy()
    df[new_name] = series.values
    st.session_state["df_clean"] = df
    # Jika ada selected_cols, tambahkan kolom baru
    selected = st.session_state.get("selected_cols", [])
    if selected and new_name not in selected:
        st.session_state["selected_cols"] = selected + [new_name]
    return df


# ─────────────────────────────────────────────────────────────────────────────
# RENDER UTAMA
# ─────────────────────────────────────────────────────────────────────────────

def render(ctx: dict):
    st.markdown(
        '<p class="rs-section-title">🧮 Compute Variabel Baru</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="rs-section-sub">'
        "Buat variabel baru dari data yang ada: formula kustom, skor komposit, "
        "recode, transformasi, standardisasi, dan lebih banyak lagi."
        "</p>",
        unsafe_allow_html=True,
    )

    df = require_data()
    if df is None:
        st.stop()

    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    all_cols = df.columns.tolist()

    # ── Info dataset ──────────────────────────────────────────────────────────
    ci1, ci2, ci3 = st.columns(3)
    ci1.metric("Total Baris", len(df))
    ci2.metric("Total Kolom", len(all_cols))
    ci3.metric("Kolom Numerik", len(num_cols))

    st.markdown("---")

    # ── Tab method ────────────────────────────────────────────────────────────
    tabs = st.tabs([
        "📐 Formula",
        "∑  Skor Komposit",
        "🔄 Recode",
        "📏 Standardisasi",
        "🪵 Transformasi",
        "⏱️ Lag / Diff",
    ])

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 1 — Formula Builder
    # ══════════════════════════════════════════════════════════════════════════
    with tabs[0]:
        st.markdown("#### 📐 Formula Builder")
        st.markdown(
            "Tulis ekspresi matematis menggunakan nama kolom. "
            "Fungsi tersedia: `abs`, `log`, `log10`, `exp`, `sqrt`, `round`, "
            "`sin`, `cos`, `np.where`, dan semua fungsi `numpy`."
        )

        with st.expander("💡 Contoh Formula", expanded=False):
            st.code(
                "# Hitung BMI dari berat dan tinggi\n"
                "berat / (tinggi / 100) ** 2\n\n"
                "# Skor total dari 5 butir\n"
                "item1 + item2 + item3 + item4 + item5\n\n"
                "# Log transform\n"
                "log(pendapatan + 1)\n\n"
                "# Kondisional\n"
                "np.where(usia >= 18, 1, 0)\n\n"
                "# Interaksi\n"
                "motivasi * kompetensi"
            )

        formula = st.text_area(
            "Formula",
            placeholder="contoh: (item1 + item2 + item3) / 3",
            height=80,
            key="compute_formula",
        )
        new_name_f = st.text_input(
            "Nama variabel baru",
            placeholder="contoh: skor_total",
            key="compute_formula_name",
        )
        overwrite_f = st.checkbox("Timpa kolom jika sudah ada", key="overwrite_f")

        col_ref, _ = st.columns([3, 1])
        with col_ref:
            st.caption("📋 Kolom tersedia: " + ", ".join(f"`{c}`" for c in all_cols[:12])
                       + ("..." if len(all_cols) > 12 else ""))

        if st.button("▶️ Hitung & Preview", key="btn_formula"):
            new_name_f = _safe_colname(new_name_f)
            ok, msg = _validate_colname(new_name_f, df) if not overwrite_f else (True, "")
            if not formula.strip():
                st.error("Formula tidak boleh kosong.")
            elif not new_name_f:
                st.error("Nama variabel tidak boleh kosong.")
            elif not ok:
                st.error(msg)
            else:
                try:
                    result_series = _apply_formula(df, formula.strip())
                    st.session_state["_compute_preview"] = {
                        "series": result_series,
                        "name": new_name_f,
                        "method": "formula",
                        "source": formula.strip(),
                        "overwrite": overwrite_f,
                    }
                except Exception as e:
                    st.error(f"❌ Error pada formula: {e}")

        if st.session_state.get("_compute_preview", {}).get("method") == "formula":
            p = st.session_state["_compute_preview"]
            _preview_series(p["series"], p["name"], df)
            if st.button("✅ Simpan ke Dataset", key="save_formula"):
                df = _save_to_dataset(df, p["name"], p["series"], p["overwrite"])
                _log_compute({"new_col": p["name"], "method": "formula",
                              "source": p["source"]})
                del st.session_state["_compute_preview"]
                st.success(f"✅ Kolom `{p['name']}` berhasil ditambahkan!")
                st.rerun()

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 2 — Skor Komposit
    # ══════════════════════════════════════════════════════════════════════════
    with tabs[1]:
        st.markdown("#### ∑ Skor Komposit")
        st.markdown(
            "Gabungkan beberapa kolom menjadi satu skor komposit. "
            "Cocok untuk menghitung total skor kuesioner, rata-rata butir, dll."
        )

        selected_items = st.multiselect(
            "Pilih kolom/butir",
            options=num_cols,
            key="composite_cols",
        )
        composite_method = st.selectbox(
            "Metode agregasi",
            ["mean", "sum", "min", "max", "median", "std"],
            format_func=lambda x: {
                "mean": "Mean (rata-rata)",
                "sum":  "Sum (total)",
                "min":  "Min (nilai minimum)",
                "max":  "Max (nilai maksimum)",
                "median": "Median",
                "std":  "Std Dev",
            }.get(x, x),
            key="composite_method",
        )
        use_weight = st.checkbox("Gunakan bobot per kolom", key="use_weight")

        weight_map = {}
        if use_weight and selected_items:
            st.markdown("**Bobot per kolom** (default = 1.0):")
            w_cols = st.columns(min(4, len(selected_items)))
            for i, col in enumerate(selected_items):
                with w_cols[i % len(w_cols)]:
                    w = st.number_input(col, min_value=0.0, value=1.0,
                                        step=0.1, key=f"w_{col}")
                    weight_map[col] = w

        new_name_c = st.text_input(
            "Nama variabel baru",
            placeholder="contoh: skor_total_X",
            key="composite_name",
        )
        overwrite_c = st.checkbox("Timpa kolom jika sudah ada", key="overwrite_c")

        if st.button("▶️ Hitung & Preview", key="btn_composite"):
            new_name_c = _safe_colname(new_name_c)
            ok, msg = _validate_colname(new_name_c, df) if not overwrite_c else (True, "")
            if len(selected_items) < 1:
                st.error("Pilih minimal 1 kolom.")
            elif not new_name_c:
                st.error("Nama variabel tidak boleh kosong.")
            elif not ok:
                st.error(msg)
            else:
                try:
                    result_series = _compute_composite(
                        df, selected_items, composite_method,
                        weight_map if use_weight else None,
                    )
                    st.session_state["_compute_preview"] = {
                        "series": result_series,
                        "name": new_name_c,
                        "method": "composite",
                        "source": f"{composite_method}({', '.join(selected_items)})",
                        "overwrite": overwrite_c,
                    }
                except Exception as e:
                    st.error(f"❌ Error: {e}")

        if st.session_state.get("_compute_preview", {}).get("method") == "composite":
            p = st.session_state["_compute_preview"]
            _preview_series(p["series"], p["name"], df)
            if st.button("✅ Simpan ke Dataset", key="save_composite"):
                df = _save_to_dataset(df, p["name"], p["series"], p["overwrite"])
                _log_compute({"new_col": p["name"], "method": "composite",
                              "source": p["source"]})
                del st.session_state["_compute_preview"]
                st.success(f"✅ Kolom `{p['name']}` berhasil ditambahkan!")
                st.rerun()

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 3 — Recode
    # ══════════════════════════════════════════════════════════════════════════
    with tabs[2]:
        st.markdown("#### 🔄 Recode Variabel")

        source_col_r = st.selectbox(
            "Kolom sumber",
            options=all_cols,
            key="recode_source",
        )
        recode_mode = st.radio(
            "Mode recode",
            ["Manual (nilai lama → nilai baru)", "Kondisional (berdasarkan rentang)"],
            horizontal=True,
            key="recode_mode",
        )

        if "Manual" in recode_mode:
            st.markdown(
                "Tulis satu aturan per baris: `nilai_lama -> nilai_baru`"
            )
            # Tampilkan nilai unik sebagai referensi
            uniq = df[source_col_r].dropna().unique()[:20]
            st.caption("Nilai unik: " + ", ".join(str(u) for u in uniq))
            mapping_text = st.text_area(
                "Mapping",
                placeholder="1 -> Rendah\n2 -> Sedang\n3 -> Tinggi",
                height=140,
                key="recode_mapping",
            )
        else:
            st.markdown("Kondisi dievaluasi dari atas ke bawah (first-match).")
            n_cond = st.number_input("Jumlah kondisi", min_value=1, max_value=10,
                                      value=3, key="n_conditions")
            conditions = []
            for i in range(int(n_cond)):
                cc1, cc2, cc3 = st.columns([2, 2, 3])
                with cc1:
                    op = st.selectbox(
                        f"Operator {i+1}", ["<", "<=", ">", ">=", "==", "!="],
                        key=f"cond_op_{i}",
                    )
                with cc2:
                    thr = st.number_input(
                        f"Nilai {i+1}", value=0.0, key=f"cond_thr_{i}"
                    )
                with cc3:
                    label = st.text_input(
                        f"Label {i+1}", placeholder="Rendah",
                        key=f"cond_lbl_{i}",
                    )
                conditions.append((op, thr, label))

        new_name_r = st.text_input(
            "Nama variabel baru",
            placeholder="contoh: kategori_skor",
            key="recode_name",
        )
        overwrite_r = st.checkbox("Timpa kolom jika sudah ada", key="overwrite_r")

        if st.button("▶️ Hitung & Preview", key="btn_recode"):
            new_name_r = _safe_colname(new_name_r)
            ok, msg = _validate_colname(new_name_r, df) if not overwrite_r else (True, "")
            if not new_name_r:
                st.error("Nama variabel tidak boleh kosong.")
            elif not ok:
                st.error(msg)
            else:
                try:
                    if "Manual" in recode_mode:
                        result_series = _recode_manual(df[source_col_r], mapping_text)
                    else:
                        result_series = _recode_conditional(
                            df, source_col_r, conditions
                        )
                    st.session_state["_compute_preview"] = {
                        "series": result_series,
                        "name": new_name_r,
                        "method": "recode",
                        "source": f"recode({source_col_r})",
                        "overwrite": overwrite_r,
                    }
                except Exception as e:
                    st.error(f"❌ Error: {e}")

        if st.session_state.get("_compute_preview", {}).get("method") == "recode":
            p = st.session_state["_compute_preview"]
            _preview_series(p["series"], p["name"], df)
            st.markdown("**Distribusi nilai baru:**")
            vc = p["series"].value_counts()
            st.dataframe(
                vc.rename_axis("Nilai").reset_index(name="Frekuensi"),
                use_container_width=True, hide_index=True,
            )
            if st.button("✅ Simpan ke Dataset", key="save_recode"):
                df = _save_to_dataset(df, p["name"], p["series"], p["overwrite"])
                _log_compute({"new_col": p["name"], "method": "recode",
                              "source": p["source"]})
                del st.session_state["_compute_preview"]
                st.success(f"✅ Kolom `{p['name']}` berhasil ditambahkan!")
                st.rerun()

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 4 — Standardisasi
    # ══════════════════════════════════════════════════════════════════════════
    with tabs[3]:
        st.markdown("#### 📏 Standardisasi & Normalisasi")

        source_col_s = st.selectbox(
            "Kolom sumber",
            options=num_cols,
            key="std_source",
        )
        std_method = st.radio(
            "Metode",
            ["Z-score (Standardisasi)", "Min-Max (Normalisasi)"],
            horizontal=True,
            key="std_method",
        )

        if "Min-Max" in std_method:
            sc1, sc2 = st.columns(2)
            new_min = sc1.number_input("Nilai minimum baru", value=0.0, key="mm_min")
            new_max = sc2.number_input("Nilai maksimum baru", value=1.0, key="mm_max")

        new_name_s = st.text_input(
            "Nama variabel baru",
            value=f"{source_col_s}_z" if "Z-score" in std_method
                  else f"{source_col_s}_norm",
            key="std_name",
        )
        overwrite_s = st.checkbox("Timpa kolom jika sudah ada", key="overwrite_s")

        if st.button("▶️ Hitung & Preview", key="btn_std"):
            new_name_s = _safe_colname(new_name_s)
            ok, msg = _validate_colname(new_name_s, df) if not overwrite_s else (True, "")
            if not ok:
                st.error(msg)
            else:
                try:
                    if "Z-score" in std_method:
                        result_series = _zscore(df[source_col_s])
                        src = f"zscore({source_col_s})"
                    else:
                        result_series = _minmax(df[source_col_s], new_min, new_max)
                        src = f"minmax({source_col_s}, {new_min}, {new_max})"
                    st.session_state["_compute_preview"] = {
                        "series": result_series,
                        "name": new_name_s,
                        "method": "standardize",
                        "source": src,
                        "overwrite": overwrite_s,
                    }
                except Exception as e:
                    st.error(f"❌ Error: {e}")

        if st.session_state.get("_compute_preview", {}).get("method") == "standardize":
            p = st.session_state["_compute_preview"]
            _preview_series(p["series"], p["name"], df)
            if st.button("✅ Simpan ke Dataset", key="save_std"):
                df = _save_to_dataset(df, p["name"], p["series"], p["overwrite"])
                _log_compute({"new_col": p["name"], "method": "standardize",
                              "source": p["source"]})
                del st.session_state["_compute_preview"]
                st.success(f"✅ Kolom `{p['name']}` berhasil ditambahkan!")
                st.rerun()

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 5 — Transformasi
    # ══════════════════════════════════════════════════════════════════════════
    with tabs[4]:
        st.markdown("#### 🪵 Transformasi Variabel")
        st.markdown(
            "Terapkan transformasi matematis untuk menangani skewness, "
            "outlier, atau memenuhi asumsi normalitas."
        )

        source_col_t = st.selectbox(
            "Kolom sumber",
            options=num_cols,
            key="trans_source",
        )
        trans_method = st.selectbox(
            "Jenis transformasi",
            [
                "Log natural (ln)",
                "Log basis 10",
                "Log basis 2",
                "Akar kuadrat (√x)",
                "Kuadrat (x²)",
                "Pangkat kustom (xⁿ)",
                "Inverse (1/x)",
                "Absolute value (|x|)",
            ],
            key="trans_method",
        )

        shift_val = 0.0
        power_val = 2.0
        if "Log" in trans_method:
            shift_val = st.number_input(
                "Konstanta shift (+c sebelum log, untuk hindari log(0))",
                min_value=0.0, value=0.0, step=0.1, key="log_shift",
            )
        if "Pangkat kustom" in trans_method:
            power_val = st.number_input("Pangkat (n)", value=2.0, step=0.5,
                                         key="power_val")

        new_name_t = st.text_input(
            "Nama variabel baru",
            placeholder=f"contoh: log_{source_col_t}",
            key="trans_name",
        )
        overwrite_t = st.checkbox("Timpa kolom jika sudah ada", key="overwrite_t")

        if st.button("▶️ Hitung & Preview", key="btn_trans"):
            new_name_t = _safe_colname(new_name_t)
            ok, msg = _validate_colname(new_name_t, df) if not overwrite_t else (True, "")
            if not new_name_t:
                st.error("Nama variabel tidak boleh kosong.")
            elif not ok:
                st.error(msg)
            else:
                try:
                    s = pd.to_numeric(df[source_col_t], errors="coerce")
                    if "Log natural" in trans_method:
                        result_series = _log_transform(df[source_col_t], "natural", shift_val)
                        src = f"ln({source_col_t}+{shift_val})"
                    elif "Log basis 10" in trans_method:
                        result_series = _log_transform(df[source_col_t], "log10", shift_val)
                        src = f"log10({source_col_t}+{shift_val})"
                    elif "Log basis 2" in trans_method:
                        result_series = _log_transform(df[source_col_t], "log2", shift_val)
                        src = f"log2({source_col_t}+{shift_val})"
                    elif "Akar kuadrat" in trans_method:
                        result_series = np.sqrt(s)
                        src = f"sqrt({source_col_t})"
                    elif "Pangkat kustom" in trans_method:
                        result_series = s ** power_val
                        src = f"{source_col_t}^{power_val}"
                    elif "Kuadrat" in trans_method:
                        result_series = s ** 2
                        src = f"{source_col_t}^2"
                    elif "Inverse" in trans_method:
                        result_series = 1 / s
                        src = f"1/{source_col_t}"
                    elif "Absolute" in trans_method:
                        result_series = s.abs()
                        src = f"|{source_col_t}|"
                    else:
                        raise ValueError("Metode tidak dikenal.")

                    st.session_state["_compute_preview"] = {
                        "series": result_series,
                        "name": new_name_t,
                        "method": "transform",
                        "source": src,
                        "overwrite": overwrite_t,
                    }
                except Exception as e:
                    st.error(f"❌ Error: {e}")

        if st.session_state.get("_compute_preview", {}).get("method") == "transform":
            p = st.session_state["_compute_preview"]
            _preview_series(p["series"], p["name"], df)
            if st.button("✅ Simpan ke Dataset", key="save_trans"):
                df = _save_to_dataset(df, p["name"], p["series"], p["overwrite"])
                _log_compute({"new_col": p["name"], "method": "transform",
                              "source": p["source"]})
                del st.session_state["_compute_preview"]
                st.success(f"✅ Kolom `{p['name']}` berhasil ditambahkan!")
                st.rerun()

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 6 — Lag / Diff
    # ══════════════════════════════════════════════════════════════════════════
    with tabs[5]:
        st.markdown("#### ⏱️ Lag / Lead / Difference")
        st.markdown(
            "Berguna untuk data time-series atau panel: buat versi lag/lead "
            "atau hitung selisih antar periode."
        )

        source_col_l = st.selectbox(
            "Kolom sumber",
            options=num_cols,
            key="lag_source",
        )
        lag_mode = st.selectbox(
            "Mode",
            ["lag", "lead", "diff", "pct_change"],
            format_func=lambda x: {
                "lag":        "Lag (mundur n periode)",
                "lead":       "Lead (maju n periode)",
                "diff":       "Difference (selisih antar periode)",
                "pct_change": "Pct Change (perubahan persentase)",
            }.get(x, x),
            key="lag_mode",
        )
        periods = st.number_input("Jumlah periode (n)", min_value=1,
                                   max_value=50, value=1, key="lag_periods")

        new_name_l = st.text_input(
            "Nama variabel baru",
            value=f"{source_col_l}_{lag_mode}{int(periods)}",
            key="lag_name",
        )
        overwrite_l = st.checkbox("Timpa kolom jika sudah ada", key="overwrite_l")

        if st.button("▶️ Hitung & Preview", key="btn_lag"):
            new_name_l = _safe_colname(new_name_l)
            ok, msg = _validate_colname(new_name_l, df) if not overwrite_l else (True, "")
            if not ok:
                st.error(msg)
            else:
                try:
                    result_series = _lag_diff(df[source_col_l], int(periods), lag_mode)
                    st.session_state["_compute_preview"] = {
                        "series": result_series,
                        "name": new_name_l,
                        "method": "lag_diff",
                        "source": f"{lag_mode}({source_col_l}, {periods})",
                        "overwrite": overwrite_l,
                    }
                except Exception as e:
                    st.error(f"❌ Error: {e}")

        if st.session_state.get("_compute_preview", {}).get("method") == "lag_diff":
            p = st.session_state["_compute_preview"]
            _preview_series(p["series"], p["name"], df)
            if st.button("✅ Simpan ke Dataset", key="save_lag"):
                df = _save_to_dataset(df, p["name"], p["series"], p["overwrite"])
                _log_compute({"new_col": p["name"], "method": "lag/diff",
                              "source": p["source"]})
                del st.session_state["_compute_preview"]
                st.success(f"✅ Kolom `{p['name']}` berhasil ditambahkan!")
                st.rerun()

    # ── Riwayat & Dataset saat ini ────────────────────────────────────────────
    st.markdown("---")
    _render_compute_log()

    with st.expander("📊 Dataset saat ini (setelah compute)", expanded=False):
        current_df = st.session_state.get("df_clean", df)
        st.dataframe(current_df.head(20), use_container_width=True)
        st.caption(f"{len(current_df)} baris × {len(current_df.columns)} kolom")

        # Download dataset yang sudah diupdate
        csv_bytes = current_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Download Dataset (CSV)",
            data=csv_bytes,
            file_name="dataset_computed.csv",
            mime="text/csv",
        )

    st.markdown("""
    <div class="rs-narasi">
    💡 <b>Tips Compute:</b>
    Variabel baru yang disimpan akan langsung tersedia di semua modul analisis lainnya
    (Deskriptif, Korelasi, Regresi, dll.) tanpa perlu upload ulang.
    Gunakan <b>📐 Formula</b> untuk ekspresi bebas, <b>∑ Skor Komposit</b> untuk
    menjumlahkan/merata-ratakan butir kuesioner, dan <b>🔄 Recode</b> untuk
    mengkategorikan variabel kontinu.
    </div>
    """, unsafe_allow_html=True)
