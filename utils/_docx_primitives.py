"""
utils/_docx_primitives.py — Ruang Statistika v4.8
Primitive helpers untuk generate_pro_docx:
  - StyleProfile dataclass
  - Document primitives (_add_para, _add_heading, _add_title_page, _add_references_section)
  - Table helpers (_remove_tbl_borders, _set_cell_hline, _set_cell_bg, _style_table, dll)
  - Image embed (_embed_image)
  - Text utils (_clean_ai_text, _fmt_val, _first_valid_df)

Diimport oleh: utils/docx_helpers.py
JANGAN diimport langsung dari modul lain — gunakan docx_helpers.py.
"""

"""
utils/docx_helpers.py — Word document generation, multi-style
Ruang Statistika v6.1

Perbaikan v6.1:
- TIDAK ada _add_blank() — jarak antar elemen pakai space_before/space_after saja
- Heading pakai space_before=Pt(18) dan space_after=Pt(6), bukan blank paragraf
- Spacer tabel hanya space_after=Pt(6) pada elemen terakhir tabel
- Narasi AI fallback: jika ai_texts[modul] kosong, dibuat narasi otomatis dari data statistik
- Paragraf kosong hanya muncul di title page (by design)

Style didukung:
  APA 7th Edition | Skripsi/Tesis Indonesia (DIKTI) | Vancouver (Medis/Kesehatan)
  Jurnal Ilmiah Umum | Laporan Bisnis/Kantor
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
from utils._docx_utils import _first_valid_df
from utils._docx_narasi import _fallback_narasi



# =============================================================================
# STYLE PROFILES
# =============================================================================

class StyleProfile:
    def __init__(
        self,
        font, font_size_pt, line_spacing_mult,
        margin_cm, left_margin_cm, first_line_indent_cm,
        para_space_after_pt,          # jarak antar paragraf (pengganti blank line)
        h1_center, h1_bold, h1_upper, h1_color,
        h1_space_before_pt, h1_space_after_pt,
        h2_bold, h2_italic, h2_color,
        h2_space_before_pt, h2_space_after_pt,
        tbl_has_color_header, tbl_header_hex, tbl_header_txt_hex,
        tbl_font_size_pt, tbl_space_before_pt, tbl_space_after_pt,
        tbl_caption_above,
        tbl_caption_bold_label, tbl_caption_italic_desc,
        fig_space_after_pt,
        fig_caption_bold_label, fig_caption_italic_desc,
        ref_hanging_indent, ref_label,
        ai_show_label, ai_label_level,
    ):
        self.font                   = font
        self.font_size              = Pt(font_size_pt)
        self.line_spacing           = line_spacing_mult
        self.margin                 = Cm(margin_cm)
        self.left_margin            = Cm(left_margin_cm)
        self.first_line_indent      = Cm(first_line_indent_cm)
        self.para_space_after       = Pt(para_space_after_pt)
        self.h1_center              = h1_center
        self.h1_bold                = h1_bold
        self.h1_upper               = h1_upper
        self.h1_color               = RGBColor(*h1_color)
        self.h1_space_before        = Pt(h1_space_before_pt)
        self.h1_space_after         = Pt(h1_space_after_pt)
        self.h2_bold                = h2_bold
        self.h2_italic              = h2_italic
        self.h2_color               = RGBColor(*h2_color)
        self.h2_space_before        = Pt(h2_space_before_pt)
        self.h2_space_after         = Pt(h2_space_after_pt)
        self.tbl_has_color_header   = tbl_has_color_header
        self.tbl_header_hex         = tbl_header_hex
        self.tbl_header_txt_hex     = tbl_header_txt_hex
        self.tbl_font_size          = Pt(tbl_font_size_pt)
        self.tbl_space_before       = Pt(tbl_space_before_pt)
        self.tbl_space_after        = Pt(tbl_space_after_pt)
        self.tbl_caption_above      = tbl_caption_above
        self.tbl_caption_bold_label = tbl_caption_bold_label
        self.tbl_caption_italic_desc= tbl_caption_italic_desc
        self.fig_space_after        = Pt(fig_space_after_pt)
        self.fig_caption_bold_label = fig_caption_bold_label
        self.fig_caption_italic_desc= fig_caption_italic_desc
        self.ref_hanging_indent     = ref_hanging_indent
        self.ref_label              = ref_label
        self.ai_show_label          = ai_show_label
        self.ai_label_level         = ai_label_level


STYLE_PROFILES = {
    # ------------------------------------------------------------------
    # APA 7th Edition
    # ------------------------------------------------------------------
    "APA 7th Edition": StyleProfile(
        font="Times New Roman", font_size_pt=12,
        line_spacing_mult=2.0,
        margin_cm=2.54, left_margin_cm=2.54,
        first_line_indent_cm=1.27,
        para_space_after_pt=0,
        h1_center=True, h1_bold=True, h1_upper=False, h1_color=(0,0,0),
        h1_space_before_pt=24, h1_space_after_pt=0,
        h2_bold=True, h2_italic=False, h2_color=(0,0,0),
        h2_space_before_pt=12, h2_space_after_pt=0,
        tbl_has_color_header=False,
        tbl_header_hex="FFFFFF", tbl_header_txt_hex="000000",
        tbl_font_size_pt=12,
        tbl_space_before_pt=12, tbl_space_after_pt=12,
        tbl_caption_above=True,
        tbl_caption_bold_label=True, tbl_caption_italic_desc=True,
        fig_space_after_pt=12,
        fig_caption_bold_label=True, fig_caption_italic_desc=True,
        ref_hanging_indent=True, ref_label="References",
        ai_show_label=True, ai_label_level=3,
    ),

    # ------------------------------------------------------------------
    # Skripsi / Tesis Indonesia (DIKTI)
    # ------------------------------------------------------------------
    "Skripsi / Tesis Indonesia (DIKTI)": StyleProfile(
        font="Times New Roman", font_size_pt=12,
        line_spacing_mult=2.0,
        margin_cm=3.0, left_margin_cm=4.0,
        first_line_indent_cm=1.25,
        para_space_after_pt=0,
        h1_center=True, h1_bold=True, h1_upper=True, h1_color=(0,0,0),
        h1_space_before_pt=24, h1_space_after_pt=0,
        h2_bold=True, h2_italic=False, h2_color=(0,0,0),
        h2_space_before_pt=12, h2_space_after_pt=0,
        tbl_has_color_header=False,
        tbl_header_hex="FFFFFF", tbl_header_txt_hex="000000",
        tbl_font_size_pt=11,
        tbl_space_before_pt=12, tbl_space_after_pt=12,
        tbl_caption_above=True,
        tbl_caption_bold_label=True, tbl_caption_italic_desc=False,
        fig_space_after_pt=12,
        fig_caption_bold_label=True, fig_caption_italic_desc=False,
        ref_hanging_indent=True, ref_label="Daftar Pustaka",
        ai_show_label=True, ai_label_level=3,
    ),

    # ------------------------------------------------------------------
    # Vancouver (Medis / Kesehatan)
    # ------------------------------------------------------------------
    "Vancouver (Medis / Kesehatan)": StyleProfile(
        font="Arial", font_size_pt=11,
        line_spacing_mult=1.5,
        margin_cm=2.5, left_margin_cm=2.5,
        first_line_indent_cm=0.0,
        para_space_after_pt=6,
        h1_center=False, h1_bold=True, h1_upper=False, h1_color=(44,110,73),
        h1_space_before_pt=18, h1_space_after_pt=6,
        h2_bold=True, h2_italic=False, h2_color=(44,110,73),
        h2_space_before_pt=12, h2_space_after_pt=4,
        tbl_has_color_header=True,
        tbl_header_hex="2C6E49", tbl_header_txt_hex="FFFFFF",
        tbl_font_size_pt=10,
        tbl_space_before_pt=10, tbl_space_after_pt=10,
        tbl_caption_above=True,
        tbl_caption_bold_label=True, tbl_caption_italic_desc=True,
        fig_space_after_pt=10,
        fig_caption_bold_label=False, fig_caption_italic_desc=True,
        ref_hanging_indent=False, ref_label="References",
        ai_show_label=True, ai_label_level=3,
    ),

    # ------------------------------------------------------------------
    # Jurnal Ilmiah Umum
    # ------------------------------------------------------------------
    "Jurnal Ilmiah Umum": StyleProfile(
        font="Times New Roman", font_size_pt=11,
        line_spacing_mult=1.1,
        margin_cm=2.5, left_margin_cm=2.5,
        first_line_indent_cm=0.5,
        para_space_after_pt=4,
        h1_center=False, h1_bold=True, h1_upper=True, h1_color=(74,74,74),
        h1_space_before_pt=16, h1_space_after_pt=4,
        h2_bold=True, h2_italic=False, h2_color=(74,74,74),
        h2_space_before_pt=10, h2_space_after_pt=2,
        tbl_has_color_header=True,
        tbl_header_hex="4A4A4A", tbl_header_txt_hex="FFFFFF",
        tbl_font_size_pt=10,
        tbl_space_before_pt=8, tbl_space_after_pt=8,
        tbl_caption_above=True,
        tbl_caption_bold_label=True, tbl_caption_italic_desc=True,
        fig_space_after_pt=8,
        fig_caption_bold_label=True, fig_caption_italic_desc=True,
        ref_hanging_indent=True, ref_label="References",
        ai_show_label=True, ai_label_level=3,
    ),

    # ------------------------------------------------------------------
    # Laporan Bisnis / Kantor
    # ------------------------------------------------------------------
    "Laporan Bisnis / Kantor": StyleProfile(
        font="Calibri", font_size_pt=11,
        line_spacing_mult=1.15,
        margin_cm=2.5, left_margin_cm=2.5,
        first_line_indent_cm=0.0,
        para_space_after_pt=8,
        h1_center=False, h1_bold=True, h1_upper=False, h1_color=(24,95,165),
        h1_space_before_pt=16, h1_space_after_pt=6,
        h2_bold=True, h2_italic=False, h2_color=(24,95,165),
        h2_space_before_pt=10, h2_space_after_pt=4,
        tbl_has_color_header=True,
        tbl_header_hex="185FA5", tbl_header_txt_hex="FFFFFF",
        tbl_font_size_pt=10,
        tbl_space_before_pt=8, tbl_space_after_pt=8,
        tbl_caption_above=False,
        tbl_caption_bold_label=True, tbl_caption_italic_desc=False,
        fig_space_after_pt=10,
        fig_caption_bold_label=True, fig_caption_italic_desc=False,
        ref_hanging_indent=False, ref_label="Referensi",
        ai_show_label=False, ai_label_level=3,
    ),
}

_DEFAULT_PROFILE = STYLE_PROFILES["APA 7th Edition"]


def _get_profile(report_style: str) -> StyleProfile:
    return STYLE_PROFILES.get(report_style, _DEFAULT_PROFILE)


# =============================================================================
# DOCUMENT SETUP
# =============================================================================

def _set_doc_defaults(doc: Document, p: StyleProfile):
    for section in doc.sections:
        section.top_margin    = p.margin
        section.bottom_margin = p.margin
        section.left_margin   = p.left_margin
        section.right_margin  = p.margin
    normal = doc.styles["Normal"]
    normal.font.name                          = p.font
    normal.font.size                          = p.font_size
    normal.paragraph_format.line_spacing      = p.line_spacing
    normal.paragraph_format.space_before      = Pt(0)
    normal.paragraph_format.space_after       = Pt(0)
    normal.paragraph_format.line_spacing_rule = WD_LINE_SPACING.MULTIPLE


# =============================================================================
# PARAGRAPH — tidak ada blank line, pakai space_after
# =============================================================================

def _add_para(doc: Document, p: StyleProfile, text: str = "",
              bold=False, italic=False,
              align=WD_ALIGN_PARAGRAPH.JUSTIFY,
              first_indent=True, is_last_in_block=False):
    """
    Tambah paragraf teks.
    is_last_in_block=True → tambah para_space_after sebagai jarak ke elemen berikutnya.
    """
    para = doc.add_paragraph()
    para.alignment = align
    fmt = para.paragraph_format
    fmt.line_spacing      = p.line_spacing
    fmt.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    fmt.space_before      = Pt(0)
    fmt.space_after       = p.para_space_after if is_last_in_block else Pt(0)
    if first_indent and p.first_line_indent > Pt(0):
        fmt.first_line_indent = p.first_line_indent
    else:
        fmt.first_line_indent = Pt(0)
    if text:
        run = para.add_run(text)
        run.font.name  = p.font
        run.font.size  = p.font_size
        run.bold       = bold
        run.italic     = italic
    return para


# =============================================================================
# HEADING — space_before/after sudah termasuk, tidak perlu blank paragraf
# =============================================================================

def _add_heading(doc: Document, p: StyleProfile, text: str, level: int = 1):
    para = doc.add_paragraph()
    fmt  = para.paragraph_format
    fmt.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    fmt.line_spacing      = p.line_spacing
    fmt.first_line_indent = Pt(0)

    if level == 1:
        fmt.space_before = p.h1_space_before
        fmt.space_after  = p.h1_space_after
        para.alignment   = WD_ALIGN_PARAGRAPH.CENTER if p.h1_center else WD_ALIGN_PARAGRAPH.LEFT
        display          = text.upper() if p.h1_upper else text
        run = para.add_run(display)
        run.font.name = p.font; run.font.size = p.font_size
        run.bold = p.h1_bold; run.italic = False
        run.font.color.rgb = p.h1_color
    elif level == 2:
        fmt.space_before = p.h2_space_before
        fmt.space_after  = p.h2_space_after
        para.alignment   = WD_ALIGN_PARAGRAPH.LEFT
        run = para.add_run(text)
        run.font.name = p.font; run.font.size = p.font_size
        run.bold = p.h2_bold; run.italic = p.h2_italic
        run.font.color.rgb = p.h2_color
    else:  # level 3+
        fmt.space_before = p.h2_space_before
        fmt.space_after  = p.h2_space_after
        para.alignment   = WD_ALIGN_PARAGRAPH.LEFT
        run = para.add_run(text)
        run.font.name = p.font; run.font.size = p.font_size
        run.bold = True; run.italic = True
        run.font.color.rgb = p.h2_color
    return para


# =============================================================================
# TABLE HELPERS
# =============================================================================

def _remove_tbl_borders(tbl):
    tbl_el = tbl._tbl
    tbl_pr = tbl_el.find(qn("w:tblPr"))
    if tbl_pr is None:
        tbl_pr = OxmlElement("w:tblPr")
        tbl_el.insert(0, tbl_pr)
    for old in tbl_pr.findall(qn("w:tblBorders")):
        tbl_pr.remove(old)
    brd = OxmlElement("w:tblBorders")
    for side in ("top","left","bottom","right","insideH","insideV"):
        el = OxmlElement(f"w:{side}")
        el.set(qn("w:val"), "none")
        brd.append(el)
    tbl_pr.append(brd)


def _set_cell_hline(cell, *, top=False, bottom=False, thick=False, color="000000"):
    tc    = cell._tc
    tc_pr = tc.find(qn("w:tcPr"))
    if tc_pr is None:
        tc_pr = OxmlElement("w:tcPr"); tc.insert(0, tc_pr)
    for old in tc_pr.findall(qn("w:tcBorders")):
        tc_pr.remove(old)
    brd = OxmlElement("w:tcBorders")
    sz  = "12" if thick else "6"
    for side in ("top","bottom","left","right","insideH","insideV"):
        el = OxmlElement(f"w:{side}")
        if (side == "top" and top) or (side == "bottom" and bottom):
            el.set(qn("w:val"),   "single")
            el.set(qn("w:sz"),    sz)
            el.set(qn("w:space"), "0")
            el.set(qn("w:color"), color)
        else:
            el.set(qn("w:val"), "none")
        brd.append(el)
    tc_pr.append(brd)


def _set_cell_bg(cell, hex_color: str):
    tc    = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    for old in tc_pr.findall(qn("w:shd")):
        tc_pr.remove(old)
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"),   "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"),  hex_color)
    tc_pr.append(shd)


def _fmt_val(val) -> str:
    if isinstance(val, float):
        if abs(val) < 0.001 and val != 0:
            return "< .001"
        return f"{val:.3f}"
    return "" if val is None else str(val)


def _tbl_caption(doc: Document, p: StyleProfile, title: str, above: bool):
    """Render caption tabel. Tidak ada baris kosong — semua pakai space_before/after."""
    if not title:
        return
    parts = title.split(".", 1)
    lbl   = parts[0].strip()
    desc  = parts[1].strip() if len(parts) > 1 else ""

    p_lbl = doc.add_paragraph()
    p_lbl.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p_lbl.paragraph_format.line_spacing      = 1.0   # single di caption
    p_lbl.paragraph_format.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    p_lbl.paragraph_format.space_before      = p.tbl_space_before if above else Pt(4)
    p_lbl.paragraph_format.space_after       = Pt(0)
    p_lbl.paragraph_format.first_line_indent = Pt(0)
    r = p_lbl.add_run(lbl)
    r.font.name = p.font; r.font.size = p.tbl_font_size
    r.bold = p.tbl_caption_bold_label

    if desc:
        p_dsc = doc.add_paragraph()
        p_dsc.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p_dsc.paragraph_format.line_spacing      = 1.0
        p_dsc.paragraph_format.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
        p_dsc.paragraph_format.space_before      = Pt(0)
        p_dsc.paragraph_format.space_after       = Pt(2)
        p_dsc.paragraph_format.first_line_indent = Pt(0)
        r2 = p_dsc.add_run(desc)
        r2.font.name = p.font; r2.font.size = p.tbl_font_size
        r2.italic = p.tbl_caption_italic_desc


def _style_table(doc: Document, dataframe: pd.DataFrame,
                 profile: StyleProfile, title: str = "") -> None:
    if dataframe is None or dataframe.empty:
        return

    if profile.tbl_caption_above and title:
        _tbl_caption(doc, profile, title, above=True)

    tbl = doc.add_table(rows=1, cols=len(dataframe.columns))
    tbl.alignment = WD_TABLE_ALIGNMENT.LEFT
    _remove_tbl_borders(tbl)

    hdr_txt_rgb = RGBColor(
        int(profile.tbl_header_txt_hex[0:2], 16),
        int(profile.tbl_header_txt_hex[2:4], 16),
        int(profile.tbl_header_txt_hex[4:6], 16),
    )

    # Header
    for i, col_name in enumerate(dataframe.columns):
        cell = tbl.rows[0].cells[i]
        cell.text = ""
        para = cell.paragraphs[0]
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        para.paragraph_format.space_before      = Pt(3)
        para.paragraph_format.space_after       = Pt(3)
        para.paragraph_format.line_spacing      = 1.0
        para.paragraph_format.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
        para.paragraph_format.first_line_indent = Pt(0)
        run = para.add_run(str(col_name))
        run.font.name = profile.font; run.font.size = profile.tbl_font_size
        run.bold = True; run.font.color.rgb = hdr_txt_rgb

        if profile.tbl_has_color_header:
            _set_cell_bg(cell, profile.tbl_header_hex)
            _set_cell_hline(cell, top=True, bottom=True, thick=False,
                            color=profile.tbl_header_hex)
        else:
            _set_cell_hline(cell, top=True, bottom=True, thick=False, color="000000")
            tc_pr  = cell._tc.find(qn("w:tcPr"))
            tc_brd = tc_pr.find(qn("w:tcBorders"))
            if tc_brd is not None:
                top_el = tc_brd.find(qn("w:top"))
                if top_el is not None:
                    top_el.set(qn("w:sz"), "12")

    # Data rows
    rows_list = list(dataframe.iterrows())
    for row_idx, (_, row_data) in enumerate(rows_list):
        is_last  = (row_idx == len(rows_list) - 1)
        is_even  = (row_idx % 2 == 1)
        new_cells = tbl.add_row().cells
        for i, val in enumerate(row_data):
            cell = new_cells[i]
            cell.text = ""
            para = cell.paragraphs[0]
            para.alignment = (WD_ALIGN_PARAGRAPH.LEFT if i == 0
                              else WD_ALIGN_PARAGRAPH.CENTER)
            para.paragraph_format.space_before      = Pt(2)
            para.paragraph_format.space_after       = Pt(2)
            para.paragraph_format.line_spacing      = 1.0
            para.paragraph_format.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
            para.paragraph_format.first_line_indent = Pt(0)
            run = para.add_run(_fmt_val(val))
            run.font.name = profile.font; run.font.size = profile.tbl_font_size
            if profile.tbl_has_color_header and is_even:
                _set_cell_bg(cell, "F2F2F2")
            if is_last:
                _set_cell_hline(cell, bottom=True, thick=True, color="000000")
            else:
                _set_cell_hline(cell)

    # Spacer setelah tabel — space_after saja, BUKAN blank paragraf
    sp = doc.add_paragraph()
    sp.paragraph_format.space_before      = Pt(0)
    sp.paragraph_format.space_after       = profile.tbl_space_after
    sp.paragraph_format.line_spacing      = 1.0
    sp.paragraph_format.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    sp.paragraph_format.first_line_indent = Pt(0)

    if not profile.tbl_caption_above and title:
        _tbl_caption(doc, profile, title, above=False)


# =============================================================================
# GAMBAR / FIGURE
# =============================================================================

def _embed_image(doc: Document, profile: StyleProfile, png_bytes: bytes, label: str):
    try:
        doc.add_picture(io.BytesIO(png_bytes), width=Inches(5.5))
        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER

        parts   = label.split(".", 1)
        fig_lbl = parts[0].strip()
        fig_dsc = parts[1].strip() if len(parts) > 1 else ""

        p_cap = doc.add_paragraph()
        p_cap.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p_cap.paragraph_format.space_before      = Pt(2)
        p_cap.paragraph_format.space_after       = profile.fig_space_after
        p_cap.paragraph_format.line_spacing      = 1.0
        p_cap.paragraph_format.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
        p_cap.paragraph_format.first_line_indent = Pt(0)
        r1 = p_cap.add_run(fig_lbl + ". ")
        r1.font.name = profile.font; r1.font.size = profile.tbl_font_size
        r1.bold   = profile.fig_caption_bold_label
        r1.italic = profile.fig_caption_italic_desc
        if fig_dsc:
            r2 = p_cap.add_run(fig_dsc)
            r2.font.name = profile.font; r2.font.size = profile.tbl_font_size
            r2.italic = profile.fig_caption_italic_desc
    except Exception as e:
        _add_para(doc, profile, f"[Gambar tidak dapat ditampilkan: {e}]",
                  first_indent=False)


# =============================================================================
# NARASI AI + FALLBACK OTOMATIS
# =============================================================================

def _clean_ai_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace("**", "").replace("*", "")
    emoji_re = re.compile(
        "[\U00010000-\U0010ffff\U0001F600-\U0001F64F\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\u2702-\u27B0\u24C2-\U0001F251]+",
        flags=re.UNICODE,
    )
    text = emoji_re.sub("", text)
    for sym in ["✓","✗","⚠️","❌","📐","🤖"]:
        text = text.replace(sym, "")
    return text.strip()




def _add_ai_narasi(doc: Document, profile: StyleProfile,
                   ai_text: str, title: str,
                   mod_key: str = "", data: dict = None):
    """
    Tambah narasi interpretasi.
    Jika ai_text kosong, gunakan _fallback_narasi() dari data statistik.
    """
    clean = ""
    if ai_text and not str(ai_text).startswith(("❌","⚠️")):
        clean = _clean_ai_text(ai_text)

    # Fallback ke narasi otomatis dari data
    if not clean and mod_key and data:
        try:
            clean = _fallback_narasi(mod_key, data)
        except Exception:
            clean = ""

    if not clean:
        return

    if profile.ai_show_label:
        _add_heading(doc, profile, title, level=profile.ai_label_level)

    paras = [l.strip() for l in clean.split("\n") if l.strip()]
    for i, para_text in enumerate(paras):
        _add_para(doc, profile, para_text, first_indent=True,
                  is_last_in_block=(i == len(paras) - 1))


def _add_model_equation_box(doc: Document, profile: StyleProfile, equation_text: str):
    if not equation_text or str(equation_text).startswith(("❌","⚠️")):
        return
    clean = _clean_ai_text(equation_text)
    if not clean:
        return
    _add_heading(doc, profile, "Model Persamaan", level=3)
    indent = profile.first_line_indent if profile.first_line_indent > Pt(0) else Cm(1.0)
    for line in [l.strip() for l in clean.split("\n") if l.strip()]:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        fmt = p.paragraph_format
        fmt.left_indent       = indent
        fmt.first_line_indent = Pt(0)
        fmt.space_before      = Pt(0)
        fmt.space_after       = Pt(0)
        fmt.line_spacing      = profile.line_spacing
        fmt.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
        run = p.add_run(line)
        run.font.name = profile.font; run.font.size = profile.font_size
        run.italic = True


# =============================================================================
# MODULE RENDERERS
# =============================================================================




def _add_title_page(doc: Document, p: StyleProfile,
                    report, cols, report_style, data_type,
                    user_name: str = ""):
    # Gunakan space_before besar di paragraf judul, bukan blank lines
    pt = doc.add_paragraph()
    pt.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pt.paragraph_format.space_before      = Pt(120)   # ~4 baris vertikal
    pt.paragraph_format.space_after       = Pt(0)
    pt.paragraph_format.line_spacing      = p.line_spacing
    pt.paragraph_format.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    pt.paragraph_format.first_line_indent = Pt(0)
    r = pt.add_run("LAPORAN ANALISIS STATISTIK" if p.h1_upper else "Laporan Analisis Statistik")
    r.font.name = p.font; r.font.size = p.font_size
    r.bold = True; r.font.color.rgb = p.h1_color

    _cover_lines = [
        f"Format: {report_style}",
        f"Tipe Data: {data_type.split('(')[0].strip()}",
        f"Total Responden: {report.get('rows_after_clean','?')}",
        f"Variabel Analisis: {len(cols)}",
        f"Tanggal: {datetime.date.today().strftime('%d %B %Y')}",
        "Ruang Statistika \u2014 AI-Powered Research & Stats Reporting",
    ]
    if user_name:
        _cover_lines.insert(4, f"Peneliti: {user_name}")

    for i, line in enumerate(_cover_lines):
        pi = doc.add_paragraph()
        pi.alignment = WD_ALIGN_PARAGRAPH.CENTER
        pi.paragraph_format.space_before      = Pt(24) if i == 0 else Pt(0)
        pi.paragraph_format.space_after       = Pt(0)
        pi.paragraph_format.line_spacing      = p.line_spacing
        pi.paragraph_format.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
        pi.paragraph_format.first_line_indent = Pt(0)
        ri = pi.add_run(line)
        ri.font.name = p.font; ri.font.size = p.font_size
    doc.add_page_break()


# =============================================================================
# REFERENCES
# =============================================================================

def _add_ref_run(para, text: str, italic: bool, font_name: str, font_size):
    """Tambahkan run ke paragraf referensi dengan format italic jika perlu."""
    run = para.add_run(text)
    run.font.name  = font_name
    run.font.size  = font_size
    run.font.italic = italic


def _add_references_section(doc: Document, p: StyleProfile, apa_refs):
    import re
    _add_heading(doc, p, p.ref_label, level=1)

    # Pisahkan menjadi baris, buang header ## dan baris kosong
    raw_lines = apa_refs if isinstance(apa_refs, list) else str(apa_refs).split("\n")
    refs = [l.strip() for l in raw_lines
            if l.strip() and not l.strip().startswith("## ")]

    for idx, ref in enumerate(refs, 1):
        para = doc.add_paragraph()
        para.alignment = WD_ALIGN_PARAGRAPH.LEFT
        fmt = para.paragraph_format
        fmt.line_spacing      = p.line_spacing
        fmt.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
        fmt.space_before      = Pt(0)
        fmt.space_after       = Pt(4)
        if p.ref_hanging_indent:
            fmt.first_line_indent = -Cm(1.27)
            fmt.left_indent       = Cm(1.27)
            run_text = ref
        else:
            fmt.first_line_indent = Pt(0)
            run_text = f"{idx}. {ref}"

        # Parse *italic* spans dan tambahkan sebagai run terpisah
        parts = re.split(r"(\*[^*]+\*)", run_text)
        for part in parts:
            if part.startswith("*") and part.endswith("*") and len(part) > 2:
                _add_ref_run(para, part[1:-1], italic=True,
                             font_name=p.font, font_size=p.font_size)
            elif part:
                _add_ref_run(para, part, italic=False,
                             font_name=p.font, font_size=p.font_size)


# =============================================================================
# MAIN GENERATOR
# =============================================================================

