"""Tests for the award-PDF schema, JSON serialisation, and bid-derived fields.

These tests use hand-OCR'd JSON fixtures alongside the PDFs in
``data/probe/modl/{year}/award-NNN.json``. Real vision-OCR integration is
out of scope for this layer - see ``award_pdf.OCRBackend`` notes.

Fixtures used:
- 2026 #2:   clean 4-bidder typed case
- 2026 #51:  disqualified top bid, 2-day delayed award, numbered-company joint bid
- 2026 #140: no-bid lot
- 2025 #3:   highly competitive 13-bidder lot
- 2022 #19:  handwritten form, withdrawn bidder, cancelled-then-reawarded
"""
from __future__ import annotations

from pathlib import Path

import pytest

from tax_sale.parse import award_pdf

REPO_ROOT = Path(__file__).resolve().parents[2]
PROBE_DIR = REPO_ROOT / "data" / "probe" / "modl"


def _record(year: int, lot: int) -> award_pdf.AwardRecord:
    pdf = PROBE_DIR / str(year) / f"award-{lot:03d}.pdf"
    if not pdf.exists():
        pytest.skip(f"PDF fixture missing: {pdf}")
    json_path = pdf.with_suffix(".json")
    if not json_path.exists():
        pytest.skip(f"JSON fixture missing: {json_path}")
    return award_pdf.JSONFixtureBackend().parse(pdf)


# --- Schema validation ----------------------------------------------------


def test_invalid_bid_status_rejected():
    with pytest.raises(ValueError, match="bid_status must be one of"):
        award_pdf.BidRecord(
            submission_rank=1, bidder_label="x", bid_amount=1.0, bid_status="bogus",
        )


def test_invalid_outcome_rejected():
    with pytest.raises(ValueError, match="outcome must be one of"):
        award_pdf.AwardRecord(
            lot_number=1, tender_id=None, owner=None, aan=None,
            opening_bid=1.0, hst_applicable=None, tendered_at=None,
            awarded_at=None, outcome="bogus",
        )


def test_sold_outcome_requires_exactly_one_winner():
    with pytest.raises(ValueError, match="exactly one bid with status='winning'"):
        award_pdf.AwardRecord(
            lot_number=1, tender_id=None, owner=None, aan=None,
            opening_bid=1.0, hst_applicable=None, tendered_at=None,
            awarded_at=None, outcome="sold",
            bids=[award_pdf.BidRecord(1, "x", 1.0, "submitted")],
        )


def test_no_bids_outcome_must_have_empty_bids():
    with pytest.raises(ValueError, match="outcome='no_bids' requires bids to be empty"):
        award_pdf.AwardRecord(
            lot_number=1, tender_id=None, owner=None, aan=None,
            opening_bid=1.0, hst_applicable=None, tendered_at=None,
            awarded_at=None, outcome="no_bids",
            bids=[award_pdf.BidRecord(1, "x", 1.0, "submitted")],
        )


# --- 2026 #2: clean baseline ---------------------------------------------


def test_2026_002_basic_fields():
    r = _record(2026, 2)
    assert r.lot_number == 2
    assert r.aan == "00017183"
    assert r.tender_id == "2025-01-004"
    assert r.opening_bid == 4493.31
    assert r.outcome == "sold"
    assert r.bidder_count == 4
    assert r.tendered_at == r.awarded_at  # same-day award


def test_2026_002_derived_bid_metrics():
    r = _record(2026, 2)
    assert r.winning_bid == 30000.00
    assert r.runner_up_bid == 12100.00
    assert r.runner_up_cushion == pytest.approx(17900.00)


# --- 2026 #51: disqualified top bid -------------------------------------


def test_2026_051_disqualified_top_bid_does_not_win():
    """The highest *submitted* bid was disqualified; runner-up actually won."""
    r = _record(2026, 51)
    # Highest submitted-or-winning amount = the disqualified one, but winner is the runner-up
    submitted_amounts = sorted(
        (b.bid_amount for b in r.bids), reverse=True,
    )
    assert submitted_amounts[0] == 69696.96  # disqualified Rafuse bid
    assert r.winning_bid == 52020.00  # Rhodenizer


def test_2026_051_runner_up_excludes_disqualified():
    """`runner_up_bid` is defined as highest *eligible* non-winning bid.
    The disqualified bid does not count, so runner-up should be $51,000."""
    r = _record(2026, 51)
    assert r.runner_up_bid == 51000.00
    # Cushion above eligible runner-up
    assert r.runner_up_cushion == pytest.approx(1020.00)


def test_2026_051_delayed_award_date():
    r = _record(2026, 51)
    assert r.tendered_at == "2026-03-02"
    assert r.awarded_at == "2026-03-04"


def test_2026_051_bidder_count_includes_disqualified():
    """All bids count toward field strength regardless of status."""
    r = _record(2026, 51)
    assert r.bidder_count == 6


# --- 2026 #140: no-bid lot ----------------------------------------------


def test_2026_140_no_bids_outcome():
    r = _record(2026, 140)
    assert r.outcome == "no_bids"
    assert r.bidder_count == 0
    assert r.winning_bid is None
    assert r.runner_up_bid is None
    assert r.runner_up_cushion is None
    assert r.awarded_at is None


# --- 2025 #3: high-competition lot ---------------------------------------


def test_2025_003_thirteen_bidders():
    r = _record(2025, 3)
    assert r.bidder_count == 13
    assert r.winning_bid == 40200.00
    assert r.runner_up_bid == 23799.83
    assert r.runner_up_cushion == pytest.approx(16400.17)


def test_2025_003_lowest_bid_matches_minimum():
    """Final-rank bidder bid exactly at the published minimum - common pattern."""
    r = _record(2025, 3)
    last = r.bids[-1]
    assert last.bid_amount == r.opening_bid


# --- 2022 #19: handwritten, withdrawn bidder, multi-award attempt -------


def test_2022_019_handwritten_outcome():
    """Even with a withdrawn bidder and a cancelled award stamp, the final
    award is unambiguous and the schema captures it cleanly."""
    r = _record(2022, 19)
    assert r.outcome == "sold"
    assert r.winning_bid == 25900.00
    assert r.awarded_at == "2022-03-14"
    assert r.tendered_at == "2022-03-07"  # award delayed 7 days


def test_2022_019_withdrawn_bid_status():
    r = _record(2022, 19)
    withdrew = [b for b in r.bids if b.bid_status == "withdrawn"]
    assert len(withdrew) == 1
    assert withdrew[0].bidder_label == "Ken Anthony"


def test_2022_019_runner_up_is_second_highest_eligible():
    """Highest non-winning eligible bid is Kyle & Mary Jayne Wyman at
    $24,777.66 (not Chantal Bouthier $24,222 or the withdrawn Ken Anthony)."""
    r = _record(2022, 19)
    assert r.runner_up_bid == 24777.66


# --- Round-trip JSON -----------------------------------------------------


def test_json_round_trip():
    r = _record(2026, 2)
    serialized = award_pdf.to_json(r)
    restored = award_pdf.from_json(serialized)
    assert restored.lot_number == r.lot_number
    assert restored.winning_bid == r.winning_bid
    assert len(restored.bids) == len(r.bids)


def test_missing_json_raises_helpful_error():
    """Backend should raise FileNotFoundError pointing to the missing JSON."""
    fake_pdf = Path("/tmp/nonexistent-award-999.pdf")
    fake_pdf.write_bytes(b"")
    try:
        with pytest.raises(FileNotFoundError, match="No hand-OCR'd JSON"):
            award_pdf.JSONFixtureBackend().parse(fake_pdf)
    finally:
        fake_pdf.unlink()
