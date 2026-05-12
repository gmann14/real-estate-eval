"""Tests for the unified-dataset loader."""
from __future__ import annotations

from pathlib import Path

import pytest

from tax_sale import dataset
from tax_sale.parse.award_pdf import AwardRecord, BidRecord
from tax_sale.parse.property_info import PropertyInfo
from tax_sale.parse.tender_package import ListedLot, TenderMetadata

REPO_ROOT = Path(__file__).resolve().parents[2]
PROBE_DIR = REPO_ROOT / "data" / "probe" / "modl"

# Skip everything if the fixture directory is missing (e.g. clean clone)
pytestmark = pytest.mark.skipif(not PROBE_DIR.exists(), reason="Probe fixtures missing")


# --- Merge logic unit tests (no I/O) ---------------------------------------


def _make_listed(lot_number=2, **kwargs):
    base = dict(
        lot_number=lot_number, aan="00017183",
        display_address="1189 NORTH RIVER RD",
        community="NORTH RIVER",
        lot_description="LAND DWELLING",
        status_flags=["REDEEMABLE"],
        assessed_owners=["SABEAN BRITTANY LEANNE"],
        opening_bid=4493.31,
    )
    base.update(kwargs)
    return ListedLot(**base)


def _make_award(lot_number=2, outcome="sold", **kwargs):
    base = dict(
        lot_number=lot_number, tender_id="2025-01-004",
        owner="SABEAN, BRITTANY LEANNE", aan="00017183",
        opening_bid=4493.31, hst_applicable=False,
        tendered_at="2026-03-02", awarded_at="2026-03-02",
        outcome=outcome,
        bids=[BidRecord(1, "Winner", 30000.00, "winning"),
              BidRecord(2, "Runner-up", 12100.00, "submitted")] if outcome == "sold" else [],
    )
    base.update(kwargs)
    return AwardRecord(**base)


def _make_info(**kwargs):
    base = dict(
        tax_sale_no=2, legal_review_date="August 22, 2025",
        name_on_record="Brittany Leanne Sabean",
        aan="00017183", pid="60260882",
        civic_address="1189 North River Road",
        title_system="land_registered", title_marketable="yes",
        road_access_class="abuts_public", shore_privileges=False,
        deed_reference="Document No. 109121989",
        encumbrances_summary="None.", survey_on_file=False,
    )
    base.update(kwargs)
    return PropertyInfo(**base)


def test_merge_all_three_sources():
    row = dataset._merge_lot(
        year=2026, lot_number=2,
        tender_metadata=TenderMetadata(tender_id="2025-01-004", tender_opening="2026-03-02"),
        listed=_make_listed(),
        award=_make_award(),
        info=_make_info(),
    )
    assert row["sale_lot_id"] == "MODL-2026-2"
    assert row["aan"] == "00017183"
    assert row["pid"] == "60260882"
    assert row["outcome"] == "sold"
    assert row["winning_bid"] == 30000.00
    assert row["runner_up_bid"] == 12100.00
    assert row["runner_up_cushion"] == pytest.approx(17900.0)
    assert row["premium_over_opening"] == pytest.approx(30000 / 4493.31)
    assert row["title_ok"] is True
    assert row["access_ok"] is True
    assert row["has_encumbrances"] is False
    assert row["has_structure"] is True  # "LAND DWELLING" contains DWELLING
    assert row["has_listing_record"] is True
    assert row["has_award_record"] is True
    assert row["has_property_info_record"] is True


def test_merge_redeemed_lot_has_listing_only():
    """Lots that were listed but never awarded should be classified 'redeemed'."""
    row = dataset._merge_lot(
        year=2026, lot_number=99,
        tender_metadata=TenderMetadata(tender_id="2025-01-004", tender_opening="2026-03-02"),
        listed=_make_listed(lot_number=99),
        award=None,
        info=None,
    )
    assert row["outcome"] == "redeemed"
    assert row["bidder_count"] == 0
    assert row["winning_bid"] is None
    assert row["has_award_record"] is False
    assert row["has_listing_record"] is True


def test_merge_no_listing_falls_back_to_award_data():
    """For 2022/2023 (no tender package), award PDF supplies the listing fields."""
    row = dataset._merge_lot(
        year=2022, lot_number=19,
        tender_metadata=None,
        listed=None,
        award=_make_award(lot_number=19),
        info=_make_info(),
    )
    assert row["aan"] == "00017183"  # from award
    assert row["assessed_owners"] == "SABEAN, BRITTANY LEANNE"  # from award.owner
    assert row["opening_bid"] == 4493.31
    assert row["has_listing_record"] is False
    assert row["has_award_record"] is True


def test_merge_handles_all_none_safely():
    """Edge case: only the lot number is known (shouldn't happen in practice)."""
    row = dataset._merge_lot(
        year=2099, lot_number=1,
        tender_metadata=None, listed=None, award=None, info=None,
    )
    assert row["outcome"] == "unknown"
    assert row["aan"] is None
    assert row["bidder_count"] == 0


def test_has_structure_detects_dwelling_and_building():
    assert dataset._has_structure(_make_listed(lot_description="LAND DWELLING")) is True
    assert dataset._has_structure(_make_listed(lot_description="LOT 4, BUILDING")) is True
    assert dataset._has_structure(_make_listed(lot_description="1971 48X12")) is True
    assert dataset._has_structure(_make_listed(lot_description="LAND")) is False
    assert dataset._has_structure(_make_listed(lot_description=None)) is None


def test_has_encumbrances_recognises_none_variants():
    assert dataset._has_encumbrances(_make_info(encumbrances_summary="None")) is False
    assert dataset._has_encumbrances(_make_info(encumbrances_summary="None.")) is False
    assert dataset._has_encumbrances(_make_info(encumbrances_summary="none")) is False
    assert dataset._has_encumbrances(_make_info(encumbrances_summary="1. Mortgage in favour of CIBC...")) is True


# --- Integration tests (loads real fixtures) ------------------------------


def test_load_all_lots_returns_expected_total():
    """Total record count is stable - changes here usually mean a fixture was added/removed."""
    records = dataset.load_all_lots()
    assert len(records) >= 100  # 124 today, may grow over time
    # Should be at least one record per known sold lot
    sold = [r for r in records if r["outcome"] == "sold"]
    assert len(sold) >= 65  # 69 today


def test_load_all_lots_outcome_breakdown_sane():
    records = dataset.load_all_lots()
    from collections import Counter
    counts = Counter(r["outcome"] for r in records)
    # Sanity ranges
    assert counts["sold"] >= 65
    assert counts["no_bids"] >= 15
    assert counts["redeemed"] >= 20  # only visible in years with tender packages


def test_load_all_lots_2026_lot_2_has_full_provenance():
    records = dataset.load_all_lots()
    row = next(
        r for r in records
        if r["year"] == 2026 and r["lot_number"] == 2
    )
    assert row["outcome"] == "sold"
    assert row["aan"] == "00017183"
    assert row["pid"] == "60260882"
    assert row["winning_bid"] == 30000.00
    assert row["bidder_count"] == 4
    assert row["title_ok"] is True
    assert row["access_ok"] is True
    assert row["has_listing_record"]
    assert row["has_award_record"]
    assert row["has_property_info_record"]


def test_strict_load_year_reports_bad_award_json(tmp_path):
    year_dir = tmp_path / "2099"
    year_dir.mkdir()
    (year_dir / "award-001.json").write_text("{not json")
    with pytest.raises(RuntimeError, match="award JSON parse failed"):
        dataset.load_year(year_dir, strict=True)
