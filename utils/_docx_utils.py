"""
utils/_docx_utils.py — Ruang Statistika v4.8
Utility ringan yang tidak mengimport modul internal lain.
Tujuan: memutus circular import antara _docx_primitives ↔ _docx_narasi.

Diimport oleh: utils/_docx_primitives.py DAN utils/_docx_narasi.py
JANGAN tambahkan import dari utils._docx_primitives atau utils._docx_narasi di sini.
"""


def _first_valid_df(*candidates):
    """Kembalikan DataFrame/nilai pertama yang tidak None dan tidak kosong.
    Aman digunakan sebagai pengganti `a or b` ketika salah satu bisa berupa DataFrame."""
    for c in candidates:
        if c is None:
            continue
        try:
            if not c.empty:
                return c
        except AttributeError:
            if c:
                return c
    return None
