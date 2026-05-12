"""Tests for the MODL property-info (reporting-letter) page-1 parser.

Format coverage:
- 2025 / 2026: clean text-extractable PDFs (Word-origin)
- 2023: clean text, but some fixtures include real encumbrances
- 2026 (some): OCR'd scans with imperfect text ("PM" for "PID", "tobe" for "to be")
- 2022 / 2024: pure scanned images with no extractable text -> parser must
  gracefully return mostly-None and not crash
"""
from __future__ import annotations

from pathlib import Path

import pytest

from tax_sale.parse import property_info as pi

REPO_ROOT = Path(__file__).resolve().parents[2]
PROBE_DIR = REPO_ROOT / "data" / "probe" / "modl"


def _fixture(year: int, lot: int) -> Path:
    path = PROBE_DIR / str(year) / f"property-{lot:03d}.pdf"
    if not path.exists():
        pytest.skip(f"Fixture not present: {path}")
    return path


# --- 2026 #2: clean reference case ----------------------------------------


def test_2026_002_basic_identity():
    info = pi.parse_pdf(_fixture(2026, 2))
    assert info.tax_sale_no == 2
    assert info.aan == "00017183"
    assert info.pid == "60260882"
    assert info.legal_review_date == "August 22, 2025"


def test_2026_002_title_block():
    info = pi.parse_pdf(_fixture(2026, 2))
    assert info.title_system == "land_registered"
    assert info.title_marketable == "yes"
    assert info.road_access_class == "abuts_public"
    assert info.shore_privileges is False
    assert info.deed_reference == "Document No. 109121989"


def test_2026_002_encumbrances_and_survey():
    info = pi.parse_pdf(_fixture(2026, 2))
    assert info.encumbrances_summary is not None
    assert info.encumbrances_summary.lower().startswith("none")
    assert info.survey_on_file is False


# --- 2025 #3: registry title + easement/ROW + shore privileges -------------


def test_2025_003_registry_with_row_and_shore():
    info = pi.parse_pdf(_fixture(2025, 3))
    assert info.tax_sale_no == 3
    assert info.pid == "60532645"
    assert info.title_system == "registry"
    assert info.title_marketable == "yes"
    assert info.road_access_class == "easement_or_ROW"
    assert info.shore_privileges is True
    assert info.survey_on_file is False  # "no survey plans on file"
    assert info.deed_reference == "Book 708, Page 371"


# --- 2025 #9: "paper title TO THE SUBJECT PROPERTY appears..." -------------


def test_2025_009_marketable_with_inserted_subject():
    """Counsel sometimes inserts narrowing words between 'title' and 'appears'."""
    info = pi.parse_pdf(_fixture(2025, 9))
    assert info.title_marketable == "yes"


# --- 2025 #98: "Paper title appears marketable." (no "to be") --------------


def test_2025_098_marketable_without_to_be():
    info = pi.parse_pdf(_fixture(2025, 98))
    assert info.title_marketable == "yes"


# --- 2026 #99: OCR-mangled scan ("PM" for "PID", qualified marketable) -----


def test_2026_099_ocr_mangled_pid_recovered():
    """The PID label was OCR'd as 'PM' but the 8-digit number is correct."""
    info = pi.parse_pdf(_fixture(2026, 99))
    assert info.pid == "60316965"


def test_2026_099_qualified_marketability():
    """`appears marketable, subject to the survey status' -> qualified, not yes."""
    info = pi.parse_pdf(_fixture(2026, 99))
    assert info.title_marketable == "qualified"


# --- 2023 #21: real encumbrance (mortgage with face value) -----------------


def test_2023_021_encumbrance_with_mortgage():
    info = pi.parse_pdf(_fixture(2023, 21))
    assert info.encumbrances_summary is not None
    assert "Mortgage" in info.encumbrances_summary
    assert "First National Financial" in info.encumbrances_summary


# --- 2022 + 2024: scanned-image PDFs, no extractable text -----------------


def test_2022_scanned_doc_graceful_none():
    """2022 property-info docs are pure scans; parser should not crash and
    should return None for fields that depend on text extraction."""
    info = pi.parse_pdf(_fixture(2022, 19))
    # Identity fields are None because there's no text
    assert info.tax_sale_no is None
    assert info.pid is None
    assert info.title_system is None
    # Boolean fields have a defined default (shore_privileges -> False)
    assert info.shore_privileges is False
    # road_access_class falls back to "unknown" rather than None
    assert info.road_access_class == "unknown"


def test_2024_scanned_doc_graceful_none():
    info = pi.parse_pdf(_fixture(2024, 1))
    assert info.tax_sale_no is None
    assert info.pid is None
    assert info.title_system is None
