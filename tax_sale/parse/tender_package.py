"""Parse MODL tax-sale tender-package PDFs.

The tender package is a text-extractable PDF (Microsoft Word origin) that
contains:
  - tender metadata (tender id, opening date, terms)
  - one structured block per listed lot

This module covers the listings extraction. Tender metadata is exposed via
``parse_tender_metadata`` and per-lot rows via ``parse_lots``.

Verified against fixtures from 2025 and 2026 packages. Earlier years may
need pattern additions.
"""
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class TenderMetadata:
    tender_id: str | None
    tender_opening: str | None  # raw date string from PDF
    bid_deposit_required: bool = True
    tied_bid_rebid_hours: int | None = 24


@dataclass
class ListedLot:
    lot_number: int
    aan: str
    display_address: str
    community: str | None
    lot_description: str | None
    status_flags: list[str] = field(default_factory=list)  # e.g. ["REDEEMABLE", "HST APPLICABLE"]
    assessed_owners: list[str] = field(default_factory=list)
    opening_bid: float | None = None
    raw_block: str = ""

    @property
    def hst_applicable(self) -> bool:
        return "HST APPLICABLE" in self.status_flags

    @property
    def redeemable(self) -> bool:
        return "REDEEMABLE" in self.status_flags


# --- text extraction -------------------------------------------------------


def extract_text(pdf_path: Path) -> str:
    """Shell out to ``pdftotext -layout`` and return stdout."""
    result = subprocess.run(
        ["pdftotext", "-layout", str(pdf_path), "-"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


# --- metadata --------------------------------------------------------------


_TENDER_ID_RE = re.compile(r"TENDER\s*#\s*([0-9A-Z\-]+)", re.IGNORECASE)
_OPENING_RE = re.compile(r"Tender Opening:\s*(.+?)\s*$", re.MULTILINE)


def parse_tender_metadata(text: str) -> TenderMetadata:
    tender_id_m = _TENDER_ID_RE.search(text)
    opening_m = _OPENING_RE.search(text)
    return TenderMetadata(
        tender_id=tender_id_m.group(1) if tender_id_m else None,
        tender_opening=opening_m.group(1).strip() if opening_m else None,
    )


# --- per-lot listings ------------------------------------------------------


_LIST_HEADER_RE = re.compile(r"LIST OF PROPERTIES TO BE SOLD:?", re.IGNORECASE)

# Match the start of a lot block: "N. Assessment Account Number ..."
_LOT_HEADER_RE = re.compile(
    r"^\s*(?P<num>\d+)\.\s*Assessment Account Number\s+(?P<aan>[0-9]+),\s*(?P<street>.+?)\s*$",
    re.MULTILINE,
)

_MONEY_RE = re.compile(r"\$\s?([0-9][0-9,]*\.\d{2})")
_OWNER_RE = re.compile(r"^\s*Assessed to\s+(.+?)\s*$", re.MULTILINE)
_TAXES_RE = re.compile(r"Taxes,\s*Interest and Expenses\s*\$?\s*([0-9][0-9,]*\.\d{2})")

# Known status tokens that appear comma-separated on the second line of a lot block.
_STATUS_TOKENS = {"REDEEMABLE", "HST APPLICABLE", "NOT REDEEMABLE"}


def _money_to_float(s: str) -> float:
    return float(s.replace(",", ""))


def _split_into_blocks(listings_text: str) -> list[str]:
    """Split the post-LIST section into per-lot text blocks."""
    starts: list[tuple[int, int]] = []
    for m in _LOT_HEADER_RE.finditer(listings_text):
        starts.append((m.start(), int(m.group("num"))))
    if not starts:
        return []
    blocks: list[str] = []
    for i, (pos, _) in enumerate(starts):
        end = starts[i + 1][0] if i + 1 < len(starts) else len(listings_text)
        blocks.append(listings_text[pos:end].strip())
    return blocks


def _parse_block(block: str) -> ListedLot:
    header_m = _LOT_HEADER_RE.search(block)
    assert header_m, f"block missing header: {block[:80]!r}"
    lot_number = int(header_m.group("num"))
    aan = header_m.group("aan")
    street = header_m.group("street").strip()

    # Line 2 contains community + lot description + status flags, comma-separated.
    after_header = block[header_m.end():].lstrip("\n")
    line2_end = after_header.find("\n")
    line2 = after_header[:line2_end] if line2_end != -1 else after_header
    parts = [p.strip().rstrip(".") for p in line2.split(",")]
    parts = [p for p in parts if p]

    flags = [p for p in parts if p.upper() in _STATUS_TOKENS]
    non_flag = [p for p in parts if p.upper() not in _STATUS_TOKENS]
    community = non_flag[0] if non_flag else None
    lot_description = ", ".join(non_flag[1:]) if len(non_flag) > 1 else None

    # Owners: one or more lines after "Assessed to", joined by "& ".
    owners: list[str] = []
    owner_match = _OWNER_RE.search(block)
    if owner_match:
        rest = block[owner_match.end():]
        # Each subsequent line that starts with "& " continues the owner list.
        owner_lines = [owner_match.group(1).strip()]
        for line in rest.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("& "):
                owner_lines.append(stripped[2:].strip())
            else:
                # First non-continuation, non-blank line ends the owner block.
                break
        owners = owner_lines

    # Opening bid.
    taxes_match = _TAXES_RE.search(block)
    opening_bid = _money_to_float(taxes_match.group(1)) if taxes_match else None

    return ListedLot(
        lot_number=lot_number,
        aan=aan,
        display_address=street,
        community=community,
        lot_description=lot_description,
        status_flags=flags,
        assessed_owners=owners,
        opening_bid=opening_bid,
        raw_block=block,
    )


def parse_lots(text: str) -> list[ListedLot]:
    header_match = _LIST_HEADER_RE.search(text)
    if not header_match:
        return []
    listings = text[header_match.end():]
    blocks = _split_into_blocks(listings)
    return [_parse_block(b) for b in blocks]


# --- convenience entry point ----------------------------------------------


def parse_pdf(pdf_path: Path) -> tuple[TenderMetadata, list[ListedLot]]:
    text = extract_text(pdf_path)
    return parse_tender_metadata(text), parse_lots(text)


if __name__ == "__main__":
    import sys
    metadata, lots = parse_pdf(Path(sys.argv[1]))
    print(f"Tender:    {metadata.tender_id}")
    print(f"Opening:   {metadata.tender_opening}")
    print(f"Lots:      {len(lots)}")
    print()
    for lot in lots:
        flags = "/".join(lot.status_flags) or "-"
        owners = " & ".join(lot.assessed_owners)
        print(f"  #{lot.lot_number:>4}  AAN {lot.aan}  ${lot.opening_bid:>10,.2f}  [{flags}]")
        print(f"         {lot.display_address}, {lot.community}")
        print(f"         desc: {lot.lot_description}")
        print(f"         owner: {owners}")
        print()
