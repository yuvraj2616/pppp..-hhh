"""Chunking. Owner: Arnav (F4).

Two strategies so the eval can compare them (R12):
  - "section": split on clause/section headings ("7.2", "Clause 7.3", "Section 4", "Rule 12(a)"),
    keep the heading as `section`, carry the page where the section starts; split long sections
    with overlap but keep the same `section` label.
  - "fixed": ~800 characters with 120 overlap, `section` = nearest heading seen so far.
Tables become their own chunks (one per table, rows as pipe-separated lines) with the
surrounding section label, so fee/grading tables are retrievable.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Page:
    page_no: int
    text: str
    tables: list[list[list[str]]]  # tables -> rows -> cells
    ocr: bool = False


@dataclass
class RawChunk:
    text: str
    section: str | None
    page: int | None
    kind: str = "text"  # text | table


def chunk_pages(pages: list[Page], strategy: str = "section") -> list[RawChunk]:
    """TODO (F4): implement both strategies described in the module docstring."""
    raise NotImplementedError("F4: chunk_pages")
