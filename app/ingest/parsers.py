"""File parsers. Owner: Arnav (F5).

Heavy libraries (fitz/PyMuPDF, pdfplumber, pytesseract) are imported inside functions so CI,
which does not install them, can still import this module.
"""

from __future__ import annotations

from pathlib import Path

from app.ingest.chunking import Page

SCANNED_TEXT_THRESHOLD = 50  # chars; below this a PDF page is treated as scanned and OCR'd


def extract_pages(path: Path) -> list[Page]:
    """Return one Page per page/section of the file.

    TODO (F4): .pdf via PyMuPDF text per page; .txt/.md as a single page; .docx via python-docx (optional).
    TODO (F5): scanned pages -> render at 300 dpi -> pytesseract (Page.ocr = True);
               tables via pdfplumber page.extract_tables(); images (.png/.jpg) -> OCR.
    """
    raise NotImplementedError("F4/F5: extract_pages")
