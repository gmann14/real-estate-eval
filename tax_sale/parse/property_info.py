"""Parse MODL property-info ("reporting letter") PDFs - page 1 only.

These multi-page PDFs are produced by MODL's legal counsel before each
tax sale. Page 1 is a text-extractable title-review letter; pages 2-N
are scanned attachments (deed, plan, parcel map). This module only
handles page 1. Pages 2-N are OCR work and live in ``award_pdf.py``-style
visual readers.

Page 1 yields most of the §5 property-info fields: PID, civic address,
title system, marketability, road-access class, shore privileges,
encumbrances, survey-on-file, deed reference.

Verified against fixtures from 2024, 2025, 2026. Earlier-year docs may
have formatting drift.
"""
from __future__ import annotations

import json
import re
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional, Protocol


@dataclass
class PropertyInfo:
    tax_sale_no: int | None
    legal_review_date: str | None  # raw "Month DD, YYYY"
    name_on_record: str | None  # MODL's "Name:" line — owner per their files
    aan: str | None
    pid: str | None
    civic_address: str | None
    title_system: str | None  # "land registered" / "registry" / None
    title_marketable: str | None  # "yes" / "qualified" / "no" / None
    road_access_class: str | None  # see _classify_road_access
    shore_privileges: bool
    deed_reference: str | None  # "Document No. X" or "Book Y, Page Z"
    encumbrances_summary: str | None
    survey_on_file: bool | None
    raw_page1: str = ""  # populated when extracted from a text-PDF; empty for hand-OCR'd
    source_pdf: Optional[str] = None  # filename of the source PDF
    ocr_notes: Optional[str] = None  # free-text notes from OCR pass (hand-OCR'd only)


# --- text extraction -------------------------------------------------------


def extract_page1_text(pdf_path: Path) -> str:
    result = subprocess.run(
        ["pdftotext", "-layout", "-f", "1", "-l", "1", str(pdf_path), "-"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def _normalize(text: str) -> str:
    """Collapse runs of whitespace inside lines; keep newlines for paragraph cues."""
    lines = []
    for line in text.splitlines():
        collapsed = re.sub(r"[ \t]+", " ", line).strip()
        lines.append(collapsed)
    return "\n".join(lines)


def _flatten(text: str) -> str:
    """Single-line flattening for free-text pattern matching."""
    return re.sub(r"\s+", " ", text).strip()


# --- field extractors ------------------------------------------------------


_TAX_SALE_NO_RE = re.compile(r"Tax\s*Sale\s*No\.?\s*(\d+)", re.IGNORECASE)
_DATE_RE = re.compile(
    r"^\s*Date:\s*([A-Z][a-z]+ \d{1,2},\s*\d{4})",
    re.MULTILINE,
)
_NAME_RE = re.compile(r"^\s*Name:\s*(.+?)\s*$", re.MULTILINE)
_AAN_RE = re.compile(r"Assessment\s*Account\s*No\.?\s*:\s*(\d+)", re.IGNORECASE)
# Allow "PID" or OCR-mangled variants (e.g. "PM") in the Property: line.
# Capture the first 8-digit number that follows the "Property:" label.
_PID_RE = re.compile(r"Property\s*:\s*\S{2,4}\s+(\d{8})", re.IGNORECASE)
# Civic address: comes after "PID NNNNNNNN -" or "PID NNNNNNNN —", potentially wrapped onto multiple lines.
_PROPERTY_BLOCK_RE = re.compile(
    r"Property:\s*PID\s+\d{8}\s*[-–—]\s*(?P<addr>.+?)(?=\n\s*\n|\nTitle\b|$)",
    re.IGNORECASE | re.DOTALL,
)

_DEED_DOC_RE = re.compile(r"Document\s*No\.?\s*(\d{6,})", re.IGNORECASE)
_DEED_BOOK_RE = re.compile(r"Book\s*(\d+),?\s*Page\s*(\d+)", re.IGNORECASE)

_ENCUMBRANCES_RE = re.compile(
    r"Encumbrances:\s*(.+?)(?=\n\s*\n|\n[A-Z][a-zA-Z ]+:|\Z)",
    re.IGNORECASE | re.DOTALL,
)
_SURVEY_RE = re.compile(
    r"Survey:\s*(.+?)(?=\n\s*\n|\n[A-Z][a-zA-Z ]+:|\Z)",
    re.IGNORECASE | re.DOTALL,
)


def _classify_title_system(flat_text: str) -> Optional[str]:
    if re.search(r"\bthe title is not land registered\b", flat_text, re.IGNORECASE):
        return "registry"
    if re.search(r"\bthe title is land registered\b", flat_text, re.IGNORECASE):
        return "land_registered"
    return None


def _classify_title_marketable(flat_text: str) -> Optional[str]:
    # Explicit negative first.
    if re.search(r"may not be marketable|title is not marketable|unmarketable", flat_text, re.IGNORECASE):
        return "no"
    # Find any "marketable" mention near a "paper title" / "title" subject.
    # Allow flexible phrasing: "paper title ... appears (to be) marketable" or
    # "title ... appears marketable". The legal counsel inserts varying amounts
    # of subject-narrowing text ("paper title to the subject property", etc).
    if not re.search(
        r"paper title[^.]{0,80}appears(?:\s+to\s+be)?\s+marketable"
        r"|title appears(?:\s+to\s+be)?\s+marketable",
        flat_text, re.IGNORECASE,
    ):
        return None
    # Qualified: "marketable, subject to..." or "marketable but..." within ~80 chars.
    if re.search(
        r"marketable[,;]?\s*(?:subject\s+to|but\b|however\b|provided\s+that\b|conditional)",
        flat_text, re.IGNORECASE,
    ):
        return "qualified"
    return "yes"


def _classify_road_access(flat_text: str) -> Optional[str]:
    """Return one of: abuts_public / easement_or_ROW / no_access / unknown / None."""
    # 1. Explicit easement/ROW (must come BEFORE generic "abuts" check)
    if re.search(
        r"does not appear to abut the public highway.*easement.{0,40}right of way",
        flat_text, re.IGNORECASE,
    ) or re.search(r"benefit of an easement.{0,40}right of way to the public", flat_text, re.IGNORECASE):
        return "easement_or_ROW"
    # 2. Landlocked or no access
    if re.search(
        r"does not appear to abut the public highway.*not.*access|landlocked|no apparent access",
        flat_text, re.IGNORECASE,
    ):
        return "no_access"
    # 3. Standard abutting access (allow stray "at" inserted by pdftotext layout)
    if re.search(
        r"appears to abut(?:\s+at)?\s+the\s+public\s+highway",
        flat_text, re.IGNORECASE,
    ) and not re.search(r"does not appear to abut", flat_text, re.IGNORECASE):
        return "abuts_public"
    if re.search(r"\babuts\s+(?:at\s+)?the\s+public\s+highway", flat_text, re.IGNORECASE) and not re.search(
        r"does not abut", flat_text, re.IGNORECASE
    ):
        return "abuts_public"
    return "unknown"


def _detect_shore_privileges(flat_text: str) -> bool:
    return bool(re.search(r"shore privileges|waterfront privileges", flat_text, re.IGNORECASE))


def _classify_survey_on_file(survey_text: str) -> Optional[bool]:
    if not survey_text:
        return None
    flat = _flatten(survey_text)
    # Negative patterns. Allow "tobe" / "to be" because pdftotext sometimes
    # smushes whitespace away (`to\s*be`), and allow extra words between
    # "appear" and "plans" for phrasing drift.
    if re.search(
        r"no survey plans? on file"
        r"|no plans? on file"
        r"|do not appear\s+to\s*be\s+any\s+plans?\s+on\s+file"
        r"|not\s+appear.{0,25}plans?\s+on\s+file",
        flat, re.IGNORECASE,
    ):
        return False
    # Positive patterns
    if re.search(r"survey plan.{0,30}(on file|filed)|plan.{0,30}filed", flat, re.IGNORECASE):
        return True
    return None


def _clean_address(raw: str) -> str:
    """Tidy the multi-line address chunk into a single canonical string."""
    flat = _flatten(raw)
    # Strip provincial suffix duplication: "..., Nova Scotia" appears most of the time
    return flat


# --- entry points ----------------------------------------------------------


def parse_text(page1_text: str) -> PropertyInfo:
    norm = _normalize(page1_text)
    flat = _flatten(norm)

    tax_sale_match = _TAX_SALE_NO_RE.search(norm)
    date_match = _DATE_RE.search(norm)
    name_match = _NAME_RE.search(norm)
    aan_match = _AAN_RE.search(norm)
    pid_match = _PID_RE.search(norm)
    property_match = _PROPERTY_BLOCK_RE.search(norm)
    deed_doc_match = _DEED_DOC_RE.search(flat)
    deed_book_match = _DEED_BOOK_RE.search(flat)
    encumbrances_match = _ENCUMBRANCES_RE.search(norm)
    survey_match = _SURVEY_RE.search(norm)

    deed_ref: Optional[str] = None
    if deed_doc_match:
        deed_ref = f"Document No. {deed_doc_match.group(1)}"
    elif deed_book_match:
        deed_ref = f"Book {deed_book_match.group(1)}, Page {deed_book_match.group(2)}"

    encumbrances_summary: Optional[str] = None
    if encumbrances_match:
        encumbrances_summary = _flatten(encumbrances_match.group(1))

    survey_on_file = _classify_survey_on_file(survey_match.group(1)) if survey_match else None

    return PropertyInfo(
        tax_sale_no=int(tax_sale_match.group(1)) if tax_sale_match else None,
        legal_review_date=date_match.group(1).strip() if date_match else None,
        name_on_record=name_match.group(1).strip() if name_match else None,
        aan=aan_match.group(1) if aan_match else None,
        pid=pid_match.group(1) if pid_match else None,
        civic_address=_clean_address(property_match.group("addr")) if property_match else None,
        title_system=_classify_title_system(flat),
        title_marketable=_classify_title_marketable(flat),
        road_access_class=_classify_road_access(flat),
        shore_privileges=_detect_shore_privileges(flat),
        deed_reference=deed_ref,
        encumbrances_summary=encumbrances_summary,
        survey_on_file=survey_on_file,
        raw_page1=page1_text,
    )


def parse_pdf(pdf_path: Path) -> PropertyInfo:
    return parse_text(extract_page1_text(pdf_path))


# --- JSON serialisation ----------------------------------------------------


_JSON_OMIT_FIELDS = {"raw_page1"}  # large, redundant when persisting


def to_json(info: PropertyInfo) -> str:
    payload = {k: v for k, v in asdict(info).items() if k not in _JSON_OMIT_FIELDS}
    return json.dumps(payload, indent=2, ensure_ascii=False)


def from_json(text: str) -> PropertyInfo:
    payload = json.loads(text)
    # Tolerate either presence or absence of optional fields.
    return PropertyInfo(
        tax_sale_no=payload.get("tax_sale_no"),
        legal_review_date=payload.get("legal_review_date"),
        name_on_record=payload.get("name_on_record"),
        aan=payload.get("aan"),
        pid=payload.get("pid"),
        civic_address=payload.get("civic_address"),
        title_system=payload.get("title_system"),
        title_marketable=payload.get("title_marketable"),
        road_access_class=payload.get("road_access_class"),
        shore_privileges=payload.get("shore_privileges", False),
        deed_reference=payload.get("deed_reference"),
        encumbrances_summary=payload.get("encumbrances_summary"),
        survey_on_file=payload.get("survey_on_file"),
        source_pdf=payload.get("source_pdf"),
        ocr_notes=payload.get("ocr_notes"),
        raw_page1="",
    )


def from_json_file(path: Path) -> PropertyInfo:
    return from_json(path.read_text())


# --- OCR backend protocol --------------------------------------------------


class OCRBackend(Protocol):
    """Strategy for turning a property-info PDF into a `PropertyInfo`."""

    def parse(self, pdf_path: Path) -> PropertyInfo: ...


class TextBackend:
    """Page-1 `pdftotext` extraction. Works only on text-extractable PDFs
    (cleanly 100% of 2026, 93% of 2025, but 0% of 2024 and ~30% of 2022/2023)."""

    def parse(self, pdf_path: Path) -> PropertyInfo:
        return parse_pdf(pdf_path)


@dataclass
class JSONFixtureBackend:
    """Load a hand-OCR'd JSON sibling of the PDF (e.g. ``property-019.json``).

    Used for scan-only PDFs where ``pdftotext`` returns nothing.
    """

    def parse(self, pdf_path: Path) -> PropertyInfo:
        json_path = pdf_path.with_suffix(".json")
        if not json_path.exists():
            raise FileNotFoundError(
                f"No hand-OCR'd JSON for {pdf_path}; expected at {json_path}. "
                f"Either generate the fixture or use TextBackend if the PDF is text-extractable."
            )
        return from_json_file(json_path)


@dataclass
class AutoBackend:
    """Try text extraction first; fall back to JSON fixture if text yields nothing useful.

    A "useful" text extraction is one where at least the AAN or PID was parsed.
    """

    def parse(self, pdf_path: Path) -> PropertyInfo:
        try:
            text_info = TextBackend().parse(pdf_path)
            if text_info.aan or text_info.pid:
                return text_info
        except Exception:
            pass
        return JSONFixtureBackend().parse(pdf_path)


if __name__ == "__main__":
    import sys
    info = parse_pdf(Path(sys.argv[1]))
    print(f"Tax Sale #:        {info.tax_sale_no}")
    print(f"Legal review date: {info.legal_review_date}")
    print(f"Name on record:    {info.name_on_record}")
    print(f"AAN:               {info.aan}")
    print(f"PID:               {info.pid}")
    print(f"Civic address:     {info.civic_address}")
    print(f"Title system:      {info.title_system}")
    print(f"Marketable:        {info.title_marketable}")
    print(f"Road access:       {info.road_access_class}")
    print(f"Shore privileges:  {info.shore_privileges}")
    print(f"Deed reference:    {info.deed_reference}")
    print(f"Encumbrances:      {info.encumbrances_summary}")
    print(f"Survey on file:    {info.survey_on_file}")
