"""Tests for the §11 bid-sheet renderer."""
from __future__ import annotations

import pytest

from tax_sale.model.bidsheet import render_bidsheet, _risk_flags, _risk_level


def _lot(**overrides) -> dict:
    base = dict(
        year=2026, lot_number=2,
        sale_lot_id="MODL-2026-2",
        aan="00017183", pid="60260882",
        display_address="1189 NORTH RIVER RD",
        community="NORTH RIVER", lot_description="LAND DWELLING",
        opening_bid=4_493.31, hst_applicable=False,
        redeemable_at_publication=True,
        tendered_at="Monday, March 2, 2026",
        title_system="land_registered", title_marketable="yes",
        road_access_class="abuts_public", shore_privileges=False,
        encumbrances_summary="None", survey_on_file=True,
        has_structure=True, has_encumbrances=False,
        title_ok=True, access_ok=True,
        outcome="sold", awarded_at="2026-03-02",
        winning_bid=30_000.0, runner_up_bid=12_100.0,
        runner_up_cushion=17_900.0, bidder_count=4,
        premium_over_opening=6.68,
    )
    base.update(overrides)
    return base


def _comp(year, lot_number, **overrides) -> dict:
    """Build a sold comp lot for the pool."""
    return _lot(year=year, lot_number=lot_number, sale_lot_id=f"MODL-{year}-{lot_number}",
                **overrides)


# --- risk flag rules -------------------------------------------------------


def test_redeemable_flag():
    assert any("REDEEMABLE" in f for f in _risk_flags(_lot(redeemable_at_publication=True)))


def test_unmarketable_title_flag():
    flags = _risk_flags(_lot(title_marketable="no"))
    assert any("TITLE NOT MARKETABLE" in f for f in flags)


def test_qualified_title_flag():
    flags = _risk_flags(_lot(title_marketable="qualified"))
    assert any("TITLE QUALIFIED" in f for f in flags)


def test_no_access_flag():
    flags = _risk_flags(_lot(road_access_class="no_access"))
    assert any("NO ACCESS" in f for f in flags)


def test_easement_or_row_flag():
    flags = _risk_flags(_lot(road_access_class="easement_or_ROW"))
    assert any("EASEMENT/ROW" in f for f in flags)


def test_encumbrances_flag_includes_summary():
    target = _lot(has_encumbrances=True,
                  encumbrances_summary="1) Mortgage in favour of CIBC face amount $161,280.00")
    flags = _risk_flags(target)
    assert any("ENCUMBRANCES" in f and "CIBC" in f for f in flags)


def test_no_survey_flag():
    flags = _risk_flags(_lot(survey_on_file=False))
    assert any("NO SURVEY" in f for f in flags)


def test_no_risk_flags_on_clean_lot():
    # Clean lot — no risk markers should fire
    clean = _lot(
        redeemable_at_publication=False, hst_applicable=False,
        title_marketable="yes", road_access_class="abuts_public",
        has_encumbrances=False, survey_on_file=True, has_structure=False,
    )
    flags = _risk_flags(clean)
    assert flags == []


def test_risk_level_blocks_no_access():
    level, reasons = _risk_level(_lot(road_access_class="no_access"))
    assert level == "PASS / MANUAL OVERRIDE ONLY"
    assert any("access" in r for r in reasons)


# --- bid-sheet render ------------------------------------------------------


def test_renders_basic_lot_header():
    target = _lot()
    pool = [_comp(2025, 100, opening_bid=4_000, winning_bid=25_000)]
    sheet = render_bidsheet(target, pool)
    assert "MODL-2026-2" in sheet
    assert "1189 NORTH RIVER RD" in sheet
    assert "AAN 00017183" in sheet
    assert "$4,493" in sheet  # opening bid


def test_renders_comp_table_when_comps_found():
    target = _lot()
    pool = [_comp(y, i, opening_bid=4000, winning_bid=20000) for y, i in [(2025,1),(2024,2),(2023,3)]]
    sheet = render_bidsheet(target, pool)
    assert "Top" in sheet and "historical comps" in sheet
    # Should include comp lot IDs
    assert "MODL-2025-1" in sheet
    assert "MODL-2024-2" in sheet


def test_render_with_no_comps_emits_explainer():
    target = _lot(year=2021)  # nothing in pool predates it
    pool = []
    sheet = render_bidsheet(target, pool)
    assert "No comparable historical comps found" in sheet


def test_decision_scenarios_appear_when_ceiling_given():
    target = _lot()
    pool = [_comp(2025 - (i % 3), i, opening_bid=4000 + i, winning_bid=15000 + i * 1000)
            for i in range(10)]
    sheet = render_bidsheet(target, pool, private_ceiling=50_000)
    assert "Decision scenarios" in sheet
    assert "Private ceiling" in sheet
    assert "Opportunistic" in sheet
    assert "Serious" in sheet
    assert "Must-win" in sheet


def test_decision_scenarios_ceiling_limited_flag():
    """When the comp-derived bid would exceed the ceiling, the line marks CEILING-LIMITED."""
    target = _lot()
    # Comps with high winning bids will push must-win above any modest ceiling
    pool = [_comp(2025 - (i % 3), i, opening_bid=5000, winning_bid=100_000 + i * 1000)
            for i in range(10)]
    sheet = render_bidsheet(target, pool, private_ceiling=20_000)
    assert "CEILING-LIMITED" in sheet


def test_thin_sample_warning():
    """Per §8 language progression, N<20 reverts to raw counts."""
    target = _lot()
    pool = [_comp(2025, i, opening_bid=4000, winning_bid=20000) for i in range(3)]
    sheet = render_bidsheet(target, pool, private_ceiling=30_000)
    assert "thin" in sheet  # warning fires (text may say "Comp set is thin")
    assert "Scenario bids suppressed" in sheet
