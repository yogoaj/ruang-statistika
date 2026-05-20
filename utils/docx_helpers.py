"""
utils/docx_helpers.py — Ruang Statistika v4.8
Entry point publik untuk generate laporan Word (.docx) dan Markdown.

Sub-modul (internal, JANGAN diimport langsung):
  _docx_primitives.py  — StyleProfile, _add_XXX, table/image helpers
  _docx_narasi.py      — _fallback_narasi per modul (narasi tanpa AI)
  _docx_renderers.py   — _render_XXX per modul + _MODULE_RENDERERS

API publik (diimport dari luar):
  generate_pro_docx(...)         → io.BytesIO (.docx)
  generate_markdown_report(...)  → str (Markdown)
"""

import io
import datetime
import re
import numpy as np
import pandas as pd

from docx import Document
from docx.shared import Pt, Cm, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

# ── Import sub-modul internal ─────────────────────────────────────────────────
from utils._docx_primitives import (
    StyleProfile,
    _first_valid_df,
    _get_profile,
    _set_doc_defaults,
    _add_para,
    _add_heading,
    _remove_tbl_borders,
    _set_cell_hline,
    _set_cell_bg,
    _fmt_val,
    _tbl_caption,
    _style_table,
    _embed_image,
    _clean_ai_text,
    _add_ai_narasi,
    _add_model_equation_box,
    _add_title_page,
    _add_references_section,
)
from utils._docx_narasi    import _fallback_narasi
from utils._docx_renderers import _MODULE_RENDERERS

def generate_pro_docx(
    df,
    report: dict,
    desc_df,
    norm_df,
    val_df,
    alpha_val,
    corr_matrix,
    cols: list,
    r_tabel: float,
    figs: dict | None = None,
    figs_png: dict | None = None,
    ai_texts: dict | None = None,
    report_style: str = "APA 7th Edition",
    data_type: str = "Data Primer (Kuesioner / Survei)",
    session_results: dict | None = None,
    user_name: str = "",
) -> io.BytesIO:

    try:
        from utils.stats_helpers import narrate_descriptive, narrate_validity
        _has_narr = True
    except ImportError:
        _has_narr = False

    if figs            is None: figs            = {}
    if figs_png        is None: figs_png        = {}
    if ai_texts        is None: ai_texts        = {}
    if session_results is None: session_results = {}

    profile = _get_profile(report_style)

    for key, fig in figs.items():
        if key not in figs_png:
            try:
                figs_png[key] = fig.to_image(format="png", width=700, height=400, scale=1.5)
            except Exception:
                pass

    doc = Document()
    _set_doc_defaults(doc, profile)

    fig_ctr = 1
    bab_ctr = 1

    _add_title_page(doc, profile, report, cols, report_style, data_type, user_name=user_name)

    # BAB 1: Ringkasan Data
    _add_heading(doc, profile, f"{bab_ctr}. Ringkasan Data dan Pembersihan", level=1)
    bab_ctr += 1
    rows_orig  = report.get("original_rows",   len(df))
    cols_orig  = report.get("original_cols",   len(df.columns))
    rows_clean = report.get("rows_after_clean", len(df))
    missing    = report.get("missing_per_col",  {})

    _add_para(doc, profile,
        f"Dataset awal memiliki {rows_orig} baris dan {cols_orig} kolom. "
        f"Setelah pembersihan data, terdapat {rows_clean} baris yang valid untuk dianalisis.",
        first_indent=True, is_last_in_block=True)

    if missing:
        _add_para(doc, profile,
            "Nilai yang hilang ditemukan pada variabel: " +
            ", ".join([f"{k} ({v} nilai)" for k,v in missing.items()]) + ".",
            first_indent=True, is_last_in_block=True)
    else:
        _add_para(doc, profile,
            "Tidak ditemukan nilai yang hilang (missing values) pada dataset.",
            first_indent=True, is_last_in_block=True)

    _style_table(doc,
        pd.DataFrame({
            "Keterangan": ["Baris Awal","Baris Valid","Kolom","Variabel Analisis"],
            "Jumlah":     [rows_orig, rows_clean, cols_orig, len(cols)],
        }), profile, "Tabel 1.1. Ringkasan Dataset")

    # BAB 2: Deskriptif
    if desc_df is not None and not desc_df.empty:
        _add_heading(doc, profile, f"{bab_ctr}. Statistik Deskriptif", level=1)
        bab_no = bab_ctr; bab_ctr += 1
        _style_table(doc, desc_df, profile, f"Tabel {bab_no}.1. Statistik Deskriptif Variabel")
        narr = ai_texts.get("descriptive","")
        if not narr and _has_narr:
            try: narr = narrate_descriptive(desc_df).replace("**","")
            except Exception: narr = ""
        _add_ai_narasi(doc, profile, narr, "Interpretasi Statistik Deskriptif")
        if figs_png.get("histogram"):
            _embed_image(doc, profile, figs_png["histogram"],
                         f"Gambar {fig_ctr}. Distribusi Variabel Penelitian"); fig_ctr += 1

    # BAB 3: Normalitas
    if norm_df is not None and not norm_df.empty:
        _add_heading(doc, profile, f"{bab_ctr}. Uji Normalitas (Shapiro-Wilk)", level=1)
        bab_no = bab_ctr; bab_ctr += 1
        _add_para(doc, profile,
            "Uji Shapiro-Wilk digunakan untuk menguji asumsi normalitas. "
            "H\u2080 ditolak apabila nilai p < .05.",
            first_indent=True, is_last_in_block=True)
        _style_table(doc, norm_df, profile,
                     f"Tabel {bab_no}.1. Hasil Uji Normalitas Shapiro-Wilk")
        # Fallback narasi normalitas otomatis
        narr = ai_texts.get("normality","")
        if not narr:
            try:
                normals = norm_df[norm_df.iloc[:,2].astype(str).str.lower().isin(["ya","yes","normal","true"])].iloc[:,0].tolist() \
                          if norm_df.shape[1] >= 3 else []
                all_n   = norm_df.shape[0]
                if len(normals) == all_n:
                    narr = "Hasil uji Shapiro-Wilk menunjukkan bahwa seluruh variabel berdistribusi normal (p > .05), sehingga asumsi normalitas terpenuhi untuk analisis parametrik selanjutnya."
                elif normals:
                    narr = (f"Sebagian variabel ({', '.join(normals)}) berdistribusi normal (p > .05). "
                            f"Variabel lainnya tidak memenuhi asumsi normalitas, sehingga perlu dipertimbangkan penggunaan uji non-parametrik.")
                else:
                    narr = "Hasil uji Shapiro-Wilk menunjukkan bahwa seluruh variabel tidak berdistribusi normal (p < .05). Pertimbangkan penggunaan metode non-parametrik atau transformasi data."
            except Exception:
                narr = ""
        _add_ai_narasi(doc, profile, narr, "Interpretasi Normalitas")

    # BAB 4: Validitas
    if val_df is not None:
        try:
            val_empty = val_df.empty if hasattr(val_df,"empty") else not val_df
        except Exception:
            val_empty = True
        if not val_empty:
            _add_heading(doc, profile,
                         f"{bab_ctr}. Uji Validitas (Korelasi Pearson)", level=1)
            bab_no = bab_ctr; bab_ctr += 1
            _add_para(doc, profile,
                f"Butir dinyatakan valid apabila r-hitung \u2265 r-tabel = {r_tabel:.3f} (p < .05).",
                first_indent=True, is_last_in_block=True)
            df_val = val_df.to_frame() if isinstance(val_df, pd.Series) else pd.DataFrame(val_df)
            _style_table(doc, df_val, profile, f"Tabel {bab_no}.1. Hasil Uji Validitas Pearson")
            narr = ai_texts.get("validity","")
            if not narr and _has_narr:
                try: narr = narrate_validity(val_df, r_tabel).replace("**","")
                except Exception: narr = ""
            if not narr:
                try:
                    r_col  = next((c for c in df_val.columns if "r-hitung" in c.lower() or "r_hitung" in c.lower()), None)
                    ket_col= next((c for c in df_val.columns if "ket" in c.lower()), None)
                    if ket_col:
                        n_valid = (df_val[ket_col].str.lower() == "valid").sum()
                        n_total = len(df_val)
                        narr = (f"Seluruh {n_total} butir instrumen dinyatakan valid (r-hitung \u2265 {r_tabel:.3f})."
                                if n_valid == n_total else
                                f"Dari {n_total} butir instrumen, {n_valid} butir dinyatakan valid dan {n_total-n_valid} butir tidak valid (r-hitung < {r_tabel:.3f}).")
                except Exception:
                    narr = ""
            _add_ai_narasi(doc, profile, narr, "Interpretasi Validitas")

    # BAB 5: Reliabilitas
    if alpha_val is not None:
        try:
            alpha_f = float(alpha_val)
            _add_heading(doc, profile,
                         f"{bab_ctr}. Uji Reliabilitas (Cronbach's Alpha)", level=1)
            bab_no = bab_ctr; bab_ctr += 1
            status = "reliabel" if alpha_f >= 0.7 else "tidak reliabel"
            _add_para(doc, profile,
                f"Hasil pengujian menunjukkan Cronbach's Alpha (\u03b1) = {alpha_f:.3f}, "
                f"sehingga instrumen dinyatakan {status} (\u03b1 \u2265 .70).",
                first_indent=True, is_last_in_block=True)
            _style_table(doc,
                pd.DataFrame([{
                    "Cronbach's Alpha (\u03b1)": round(alpha_f,4),
                    "Keterangan": "Reliabel" if alpha_f >= 0.7 else "Tidak Reliabel",
                }]), profile, f"Tabel {bab_no}.1. Hasil Uji Reliabilitas")
        except Exception:
            pass

    # BAB 6: Korelasi
    if corr_matrix is not None:
        try:
            corr_empty = corr_matrix.empty
        except Exception:
            corr_empty = True
        if not corr_empty:
            _add_heading(doc, profile,
                         f"{bab_ctr}. Analisis Korelasi (Pearson)", level=1)
            bab_no = bab_ctr; bab_ctr += 1
            _add_para(doc, profile,
                "Matriks korelasi Pearson menggambarkan hubungan linier antar variabel.",
                first_indent=True, is_last_in_block=True)
            corr_display = corr_matrix.round(3).reset_index().rename(
                columns={"index":"Variabel"})
            _style_table(doc, corr_display, profile,
                         f"Tabel {bab_no}.1. Matriks Korelasi Pearson")
            narr = ai_texts.get("correlation","")
            if not narr:
                try:
                    pairs = []
                    cols_c = corr_matrix.columns.tolist()
                    for i, c1 in enumerate(cols_c):
                        for c2 in cols_c[i+1:]:
                            r = corr_matrix.loc[c1,c2]
                            if abs(r) >= 0.5:
                                arah = "positif" if r > 0 else "negatif"
                                pairs.append(f"{c1}\u2013{c2} (r = {r:.3f}, {arah})")
                    if pairs:
                        narr = ("Terdapat korelasi yang kuat (|r| \u2265 .50) antara: " +
                                "; ".join(pairs) + ". "
                                "Korelasi antar variabel prediktor perlu diperhatikan untuk menghindari masalah multikolinearitas.")
                    else:
                        narr = "Tidak ditemukan korelasi yang kuat (|r| \u2265 .50) antar variabel. Hubungan antar variabel tergolong lemah hingga sedang."
                except Exception:
                    narr = ""
            _add_ai_narasi(doc, profile, narr, "Interpretasi Korelasi")
            if figs_png.get("heatmap"):
                _embed_image(doc, profile, figs_png["heatmap"],
                             f"Gambar {fig_ctr}. Heatmap Korelasi Antar Variabel"); fig_ctr += 1
            sc = ai_texts.get("_scatter_meta", {})
            # Fix 6: accept both "scatter" and "korelasi_scatter" keys
            _scatter_png = figs_png.get("scatter") or figs_png.get("korelasi_scatter")
            if sc and _scatter_png:
                vx, vy = sc.get("var_x","X"), sc.get("var_y","Y")
                rv, pv = sc.get("r_val"), sc.get("p_val")
                _add_heading(doc, profile, f"{bab_no}.2. Scatter Plot: {vx} dan {vy}", level=2)
                if rv is not None and pv is not None:
                    sig = "signifikan" if float(pv) < 0.05 else "tidak signifikan"
                    _add_para(doc, profile,
                        f"Korelasi antara {vx} dan {vy} sebesar r = {float(rv):.3f} "
                        f"(p = {float(pv):.3f}), yang berarti {sig}.",
                        first_indent=True, is_last_in_block=True)
                _embed_image(doc, profile,
                             figs_png.get("scatter") or figs_png.get("korelasi_scatter"),
                             f"Gambar {fig_ctr}. Scatter Plot {vx} vs {vy}"); fig_ctr += 1

    # BAB 7+: Modul Lanjutan
    for mod_key, info in session_results.items():
        mod_data = info.get("data",{}) if isinstance(info,dict) else {}
        if not mod_data:
            continue
        renderer = _MODULE_RENDERERS.get(mod_key)
        if renderer is None:
            continue
        fig_ctr = renderer(doc, profile, mod_data, figs_png, fig_ctr, bab_ctr, ai_texts)
        bab_ctr += 1

    # Kesimpulan
    if ai_texts.get("kesimpulan"):
        _add_heading(doc, profile,
                     f"{bab_ctr}. Kesimpulan dan Rekomendasi", level=1)
        paras = [l.strip() for l in _clean_ai_text(ai_texts["kesimpulan"]).split("\n") if l.strip()]
        for i, pt in enumerate(paras):
            _add_para(doc, profile, pt, first_indent=True,
                      is_last_in_block=(i == len(paras)-1))

    # Referensi
    apa_refs = ai_texts.get("apa_references")
    if apa_refs:
        doc.add_page_break()
        _add_references_section(doc, profile, apa_refs)

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf


# =============================================================================
# MARKDOWN GENERATOR
# =============================================================================

def generate_markdown_report(
    df, report, desc_df, norm_df, val_df, alpha_val, corr_matrix,
    cols, r_tabel,
    ai_texts=None, report_style="APA 7th Edition",
    data_type="Data Primer (Kuesioner / Survei)",
    session_results=None,
    user_name: str = "",
) -> str:
    if ai_texts        is None: ai_texts        = {}
    if session_results is None: session_results = {}
    lines = [
        "# Laporan Analisis Statistik","",
        "**Ruang Statistika \u2014 AI-Powered Research & Stats Reporting**","",
        "| Keterangan | Detail |","|---|---|",
        f"| Format | {report_style} |",
        f"| Tipe Data | {data_type.split('(')[0].strip()} |",
        f"| Total Responden | {report.get('rows_after_clean', len(df))} |",
        f"| Variabel Analisis | {len(cols)} |",
        *([ f"| Peneliti | {user_name} |" ] if user_name else []),
        f"| Tanggal | {datetime.date.today().strftime('%d %B %Y')} |",
        "","---","",
    ]
    bab = 1
    lines += [f"## {bab}. Ringkasan Data","",
              f"Dataset awal: **{report.get('original_rows','?')}** baris. "
              f"Setelah pembersihan: **{report.get('rows_after_clean', len(df))}** baris valid.",""]
    missing = report.get("missing_per_col",{})
    lines.append("Missing values: " + ", ".join([f"**{k}** ({v})" for k,v in missing.items()])
                 if missing else "Tidak ditemukan missing values.")
    bab += 1

    if desc_df is not None and not desc_df.empty:
        lines += ["", f"## {bab}. Statistik Deskriptif",""]
        lines.append(desc_df.to_markdown(index=False))
        narr = ai_texts.get("descriptive","")
        if narr:
            lines += ["","> **Interpretasi:**",""]
            for l in narr.split("\n"):
                if l.strip(): lines.append(f"> {l}")
        bab += 1

    if norm_df is not None and not norm_df.empty:
        lines += ["", f"## {bab}. Uji Normalitas","",
                  "H\u2080: data berdistribusi normal. Ditolak jika p < .05.",""]
        lines.append(norm_df.to_markdown(index=False))
        narr = ai_texts.get("normality","")
        if narr:
            lines += ["","> **Interpretasi:**",""]
            for l in narr.split("\n"):
                if l.strip(): lines.append(f"> {l}")
        bab += 1

    if val_df is not None:
        try:
            val_empty = val_df.empty if hasattr(val_df,"empty") else not val_df
        except Exception:
            val_empty = True
        if not val_empty:
            lines += ["", f"## {bab}. Uji Validitas","",
                      f"Butir valid: r-hitung \u2265 r-tabel = **{r_tabel}**",""]
            try: lines.append(val_df.to_markdown(index=False))
            except Exception: lines.append(str(val_df))
            bab += 1

    if alpha_val is not None:
        try:
            af = float(alpha_val)
            lines += ["", f"## {bab}. Uji Reliabilitas","",
                      f"**Cronbach's Alpha (\u03b1) = {af:.4f}** \u2014 "
                      f"[{'RELIABEL' if af >= 0.7 else 'TIDAK RELIABEL'}]",""]
            bab += 1
        except Exception: pass

    if corr_matrix is not None:
        try:
            corr_empty = corr_matrix.empty
        except Exception:
            corr_empty = True
        if not corr_empty:
            lines += ["", f"## {bab}. Analisis Korelasi",""]
            corr_md = corr_matrix.round(3).reset_index().rename(columns={"index":"Variabel"})
            lines.append(corr_md.to_markdown(index=False))
            narr = ai_texts.get("correlation","")
            if narr:
                lines += ["","> **Interpretasi:**",""]
                for l in narr.split("\n"):
                    if l.strip(): lines.append(f"> {l}")
            bab += 1

    _MD_LABELS = {
        "regresi":"Analisis Regresi Linier","ols_plus":"Regresi OLS (Diagnostik)",
        "logistik":"Regresi Logistik","mediasi":"Analisis Mediasi",
        "moderasi":"Analisis Moderasi","anova":"ANOVA & Post-hoc",
        "uji_beda":"Uji Beda","outlier":"Deteksi Outlier",
        "sem":"SEM & CFA","kelompok":"Analisis Kelompok",
    }
    for mod_key, info in session_results.items():
        mod_data = info.get("data",{}) if isinstance(info,dict) else {}
        if not mod_data: continue
        sec_title = _MD_LABELS.get(mod_key, info.get("label", mod_key))
        lines += ["", f"## {bab}. {sec_title}",""]
        for data_key, label in [
            ("coef_table","Koefisien"),("anova_table","Tabel ANOVA"),
            ("posthoc_table","Post-hoc"),("path_table","Koefisien Jalur"),
            ("fit_indices","Indeks Kecocokan"),("loadings","Factor Loadings"),
            ("path_estimates","Estimasi Jalur"),("outlier_table","Daftar Outlier"),
            ("group_stats","Statistik Kelompok"),
        ]:
            sub_df = mod_data.get(data_key)
            if sub_df is not None and not sub_df.empty:
                lines += [f"**{label}**",""]
                try: lines.append(sub_df.round(4).to_markdown(index=False))
                except Exception: lines.append(str(sub_df))
                lines.append("")
        # Fallback narasi MD
        narr = ai_texts.get(mod_key,"")
        if not narr:
            try: narr = _fallback_narasi(mod_key, mod_data)
            except Exception: narr = ""
        if narr:
            lines += ["",f"> **Interpretasi \u2014 {sec_title}:**",""]
            for l in _clean_ai_text(narr).split("\n"):
                if l.strip(): lines.append(f"> {l}")
            lines.append("")
        bab += 1

    if ai_texts.get("kesimpulan"):
        lines += ["","---",f"## {bab}. Kesimpulan dan Rekomendasi","",
                  _clean_ai_text(ai_texts["kesimpulan"])]

    apa_refs = ai_texts.get("apa_references")
    if apa_refs:
        lines += ["","---","## Referensi",""]
        refs = apa_refs if isinstance(apa_refs,list) else \
               [l for l in str(apa_refs).split("\n") if l.strip()]
        for r in refs: lines.append(f"{r.strip()}  ")

    lines += ["","---",
              "*Laporan dihasilkan otomatis oleh Ruang Statistika*",
              f"*Format: {report_style} | Powered by Python, Streamlit & AI*"]
    return "\n".join(lines)
