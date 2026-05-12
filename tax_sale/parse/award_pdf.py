"""Parse MODL tax-sale award PDFs.

All MODL award PDFs are scanned image PDFs - text extraction returns
nothing - so visual OCR is required. The template also drifts:

- **2025-2026**: typed 20-slot bid table. Highlight + signature + "Award
  YYYY-MM-DD" stamp marks the winner. Strikethrough marks
  disqualified/withdrawn bids.
- **2022 (+ probably earlier years)**: handwritten bid amounts and names,
  variable-length list, check-marks for verified bids, inline annotations
  ("Bidder withdrew YYYY-MM-DD"), occasionally multiple award attempts
  on one form (final stamp wins; earlier stamps are crossed out).

This module is deliberately split into two layers:

1. **In-memory schema** (`AwardRecord` + `BidRecord` dataclasses) and JSON
   serialisation. This is the contract between the OCR layer and the
   downstream database/modelling layer.
2. **OCR backend protocol** (`OCRBackend`) with a working
   `JSONFixtureBackend` for tests. A production
   `AnthropicVisionBackend` is a TODO - see `pipeline/` notes.

This split means we can ship the parser today against hand-OCR'd JSON
fixtures, validate end-to-end behaviour, and slot in real OCR later
without touching the downstream code.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable, Optional, Protocol

# Bid statuses match §5 sale_lot_bids.bid_status enum.
BID_STATUS_VALUES = frozenset({
    "submitted", "winning", "withdrawn", "disqualified", "tied_rebid",
})

OUTCOME_VALUES = frozenset({
    "sold", "redeemed", "no_bids", "withdrawn", "unknown",
})


@dataclass
class BidRecord:
    submission_rank: int  # 1-indexed; order on the award form
    bidder_label: Optional[str]  # may be null for v1 privacy; raw OCR'd name otherwise
    bid_amount: float
    bid_status: str  # one of BID_STATUS_VALUES
    notes: Optional[str] = None  # e.g. "withdrew 2022-03-10", "verified ✓"

    def __post_init__(self) -> None:
        if self.bid_status not in BID_STATUS_VALUES:
            raise ValueError(
                f"bid_status must be one of {sorted(BID_STATUS_VALUES)}, "
                f"got {self.bid_status!r}"
            )

    @property
    def is_winning(self) -> bool:
        return self.bid_status == "winning"


@dataclass
class AwardRecord:
    lot_number: int
    tender_id: Optional[str]  # e.g. "2025-01-004"
    owner: Optional[str]  # MODL listing's owner; may differ from PVSC
    aan: Optional[str]  # 8-digit assessment account number
    opening_bid: float
    hst_applicable: Optional[bool]  # None when not determinable from form
    tendered_at: Optional[str]  # ISO date string
    awarded_at: Optional[str]  # final award stamp date; may differ from tendered_at
    outcome: str  # one of OUTCOME_VALUES
    bids: list[BidRecord] = field(default_factory=list)
    attendees: list[str] = field(default_factory=list)
    source_pdf: Optional[str] = None  # filename of the OCR'd PDF
    ocr_notes: Optional[str] = None  # free-text notes from the OCR pass

    def __post_init__(self) -> None:
        if self.outcome not in OUTCOME_VALUES:
            raise ValueError(
                f"outcome must be one of {sorted(OUTCOME_VALUES)}, "
                f"got {self.outcome!r}"
            )
        # Cross-consistency: a sold outcome must have exactly one winning bid;
        # no_bids must have an empty bids list.
        winners = [b for b in self.bids if b.is_winning]
        if self.outcome == "sold" and len(winners) != 1:
            raise ValueError(
                f"outcome='sold' requires exactly one bid with status='winning', "
                f"found {len(winners)}"
            )
        if self.outcome == "no_bids" and self.bids:
            raise ValueError("outcome='no_bids' requires bids to be empty")

    @property
    def bidder_count(self) -> int:
        return len(self.bids)

    @property
    def winning_bid(self) -> Optional[float]:
        for b in self.bids:
            if b.is_winning:
                return b.bid_amount
        return None

    @property
    def runner_up_bid(self) -> Optional[float]:
        """Highest *eligible* (submitted/winning) bid that is NOT the winner."""
        eligible = [
            b for b in self.bids
            if b.bid_status in {"submitted", "winning"}
        ]
        if len(eligible) < 2:
            return None
        sorted_amounts = sorted((b.bid_amount for b in eligible), reverse=True)
        return sorted_amounts[1]

    @property
    def runner_up_cushion(self) -> Optional[float]:
        if self.winning_bid is None or self.runner_up_bid is None:
            return None
        return self.winning_bid - self.runner_up_bid


# --- JSON serialisation ----------------------------------------------------


def to_json(record: AwardRecord) -> str:
    return json.dumps(asdict(record), indent=2, ensure_ascii=False)


def from_json(text: str) -> AwardRecord:
    payload = json.loads(text)
    bid_payloads = payload.pop("bids", [])
    attendees = payload.pop("attendees", [])
    bids = [BidRecord(**b) for b in bid_payloads]
    return AwardRecord(bids=bids, attendees=attendees, **payload)


def from_json_file(path: Path) -> AwardRecord:
    return from_json(path.read_text())


# --- OCR backend protocol --------------------------------------------------


class OCRBackend(Protocol):
    """Strategy for turning a scanned award PDF into an `AwardRecord`."""

    def parse(self, pdf_path: Path) -> AwardRecord: ...


@dataclass
class JSONFixtureBackend:
    """Looks up hand-OCR'd JSON next to the PDF for offline / test use.

    For ``2026/award-002.pdf`` it looks for ``2026/award-002.json``. Useful
    for shipping the parser pipeline before the real vision OCR is wired up.
    """
    fixtures_root: Optional[Path] = None  # default: alongside the PDF

    def parse(self, pdf_path: Path) -> AwardRecord:
        if self.fixtures_root is not None:
            json_path = self.fixtures_root / pdf_path.with_suffix(".json").name
        else:
            json_path = pdf_path.with_suffix(".json")
        if not json_path.exists():
            raise FileNotFoundError(
                f"No hand-OCR'd JSON for {pdf_path}; expected at {json_path}. "
                f"Either generate the fixture or wire up a real vision backend."
            )
        return from_json_file(json_path)


# --- Bulk loader -----------------------------------------------------------


def load_year(year_dir: Path, backend: OCRBackend) -> list[AwardRecord]:
    """Load every ``award-*.pdf`` under ``year_dir`` via the given backend."""
    records: list[AwardRecord] = []
    for pdf in sorted(year_dir.glob("award-*.pdf")):
        records.append(backend.parse(pdf))
    return records


if __name__ == "__main__":
    import sys
    json_path = Path(sys.argv[1])
    record = from_json_file(json_path)
    print(f"Lot #{record.lot_number}  ({record.outcome})")
    print(f"  Tender:    {record.tender_id}")
    print(f"  Owner:     {record.owner}")
    print(f"  AAN:       {record.aan}")
    print(f"  Opening:   ${record.opening_bid:,.2f}  HST={record.hst_applicable}")
    print(f"  Tendered:  {record.tendered_at}")
    print(f"  Awarded:   {record.awarded_at}")
    print(f"  Bids ({record.bidder_count}):")
    for bid in record.bids:
        marker = "→" if bid.is_winning else " "
        note = f"  [{bid.notes}]" if bid.notes else ""
        print(f"   {marker} #{bid.submission_rank:>2}  ${bid.bid_amount:>10,.2f}  "
              f"{bid.bid_status:<12}  {bid.bidder_label}{note}")
    if record.winning_bid is not None and record.runner_up_bid is not None:
        print(f"  Cushion:   ${record.runner_up_cushion:,.2f} above runner-up")
