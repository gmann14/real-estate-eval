"""Tests for the comp-scoring layer (§7)."""
from __future__ import annotations

import pytest

from tax_sale.model.comp import (
    DEFAULT_WEIGHTS,
    _opening_bid_overlap,
    find_comps,
    historical_exceedance,
    score_lot_similarity,
)


# --- helper -----------------------------------------------------------------

def lot(**overrides) -> dict:
    """Build a minimal dataset-style lot dict with defaults."""
    base = dict(
        year=2026, lot_number=1,
        aan="00000001", pid="60000001",
        opening_bid=10_000.0, hst_applicable=False,
        has_structure=False, road_access_class="abuts_public",
        title_marketable="yes", shore_privileges=False,
        has_encumbrances=False,
        outcome="sold", winning_bid=20_000.0, bidder_count=5,
    )
    base.update(overrides)
    # Derive sale_lot_id from year/lot_number unless explicitly set
    base.setdefault("sale_lot_id", f"MODL-{base['year']}-{base['lot_number']}")
    return base


# --- opening_bid_overlap ----------------------------------------------------


def test_opening_bid_overlap_exact():
    assert _opening_bid_overlap(10_000, 10_000) == 1.0


def test_opening_bid_overlap_within_50_pct():
    assert _opening_bid_overlap(10_000, 12_000) == 1.0  # ratio 1.2


def test_opening_bid_overlap_partial():
    assert _opening_bid_overlap(10_000, 25_000) == pytest.approx(0.66)  # ratio 2.5


def test_opening_bid_overlap_loose():
    assert _opening_bid_overlap(10_000, 80_000) == pytest.approx(0.33)  # ratio 8


def test_opening_bid_overlap_far():
    assert _opening_bid_overlap(1_000, 50_000) == 0.0  # ratio 50


# --- score_lot_similarity ---------------------------------------------------


def test_identical_lots_score_100():
    a = lot()
    b = lot(lot_number=2, sale_lot_id="MODL-2026-2")
    result = score_lot_similarity(a, b)
    assert result.score == 100.0
    assert result.available_weight == sum(DEFAULT_WEIGHTS.values())


def test_property_type_mismatch_drops_score():
    a = lot(has_structure=False)
    b = lot(lot_number=2, has_structure=True)
    result = score_lot_similarity(a, b)
    # Loses 30 points out of 100 for property type
    assert result.score == pytest.approx(70.0)
    assert any("vacant" in r and "improved" in r for r in result.why_weak)


def test_partial_legal_access_credit():
    a = lot(road_access_class="abuts_public")
    b = lot(lot_number=2, road_access_class="easement_or_ROW")
    result = score_lot_similarity(a, b)
    # Should give 60% of the 25-point access weight = 15 points
    expected = 100 * (75 + 15) / 100
    assert result.score == pytest.approx(expected)
    assert any("both have legal access" in m for m in result.why_matched)


def test_sparse_comps_get_completeness_penalty():
    """A comp that matches on opening_bid only shouldn't look like a perfect comp.

    The score is normalized over comparable fields THEN scaled by how complete
    the comparison was (available_weight / max_weight), so a single-field
    match scores ~15 rather than 100.
    """
    a = lot()
    # Comp has only opening bid available
    b = {"year": 2025, "lot_number": 1, "opening_bid": 10_000}
    result = score_lot_similarity(a, b)
    # 100% of comparable fields match, but only 15 of 100 max weight was comparable
    # → score = 100 * (15/100) = 15
    assert result.score == pytest.approx(15.0)
    assert result.available_weight == DEFAULT_WEIGHTS["opening_bid_bucket"]


def test_unknown_access_treated_as_missing():
    a = lot(road_access_class="abuts_public")
    b = lot(lot_number=2, road_access_class="unknown")
    result = score_lot_similarity(a, b)
    # Access dimension should be skipped, score is computed over remaining dimensions
    assert result.available_weight == sum(DEFAULT_WEIGHTS.values()) - DEFAULT_WEIGHTS["road_access"]


def test_shore_privileges_match_gives_credit():
    a = lot(shore_privileges=True)
    b = lot(lot_number=2, shore_privileges=True)
    result = score_lot_similarity(a, b)
    assert any("waterfront" in m for m in result.why_matched)


def test_opening_bid_far_apart_logged_as_weak():
    a = lot(opening_bid=5_000)
    b = lot(lot_number=2, opening_bid=200_000)
    result = score_lot_similarity(a, b)
    assert any("opening bids differ" in r for r in result.why_weak)


# --- find_comps -------------------------------------------------------------


def test_find_comps_excludes_target_itself():
    target = lot(year=2026, lot_number=5)
    pool = [target, lot(year=2025, lot_number=10)]
    results = find_comps(target, pool, n=5, require_prior_year=True)
    assert all(r.comp["sale_lot_id"] != target["sale_lot_id"] for r in results)


def test_find_comps_require_prior_year_filters_same_or_later():
    target = lot(year=2024)
    pool = [
        lot(year=2023, lot_number=1, sale_lot_id="OLD"),
        lot(year=2024, lot_number=2, sale_lot_id="SAME"),
        lot(year=2025, lot_number=3, sale_lot_id="LATER"),
    ]
    results = find_comps(target, pool, n=5, require_prior_year=True)
    assert {r.comp["sale_lot_id"] for r in results} == {"OLD"}


def test_find_comps_require_sold_excludes_no_bids():
    target = lot(year=2026)
    pool = [
        lot(year=2025, lot_number=1, sale_lot_id="SOLD", outcome="sold"),
        lot(year=2025, lot_number=2, sale_lot_id="NO_BID", outcome="no_bids", winning_bid=None),
    ]
    results = find_comps(target, pool, n=5, require_sold=True)
    assert {r.comp["sale_lot_id"] for r in results} == {"SOLD"}


def test_find_comps_drops_below_min_available_weight():
    """Tiny comps with only 1-2 comparable fields shouldn't appear in results."""
    target = lot(year=2026)
    pool = [
        # Comp with only opening_bid (15 pts) — below default 30-pt minimum
        {"year": 2025, "lot_number": 1, "opening_bid": 10_000, "outcome": "sold", "winning_bid": 1},
        # Comp with full data
        lot(year=2025, lot_number=2),
    ]
    results = find_comps(target, pool, n=5)
    assert all(r.available_weight >= 30 for r in results)


def test_find_comps_ranks_by_score_descending():
    target = lot(year=2026, has_structure=False, road_access_class="abuts_public")
    pool = [
        lot(year=2025, lot_number=1, sale_lot_id="MATCH", has_structure=False),
        lot(year=2025, lot_number=2, sale_lot_id="MISMATCH", has_structure=True),
    ]
    results = find_comps(target, pool, n=5)
    assert results[0].comp["sale_lot_id"] == "MATCH"
    assert results[0].score > results[1].score


# --- historical_exceedance --------------------------------------------------


class _Wrap:
    """Minimal CompResult stand-in for testing exceedance."""
    def __init__(self, comp):
        self.comp = comp


def test_exceedance_counts_cleared_comps():
    comps = [
        _Wrap({"winning_bid": 10_000}),
        _Wrap({"winning_bid": 20_000}),
        _Wrap({"winning_bid": 30_000}),
        _Wrap({"winning_bid": 40_000}),
    ]
    result = historical_exceedance(25_000, comps)
    assert result["cleared"] == 2  # cleared 10k and 20k
    assert result["total"] == 4
    assert result["rate"] == 0.5


def test_exceedance_ignores_comps_without_winning_bid():
    comps = [
        _Wrap({"winning_bid": 10_000}),
        _Wrap({"winning_bid": None}),  # no-bid lot in the comp set
    ]
    result = historical_exceedance(15_000, comps)
    assert result["cleared"] == 1
    assert result["total"] == 1  # the None-winning-bid comp is excluded


def test_exceedance_empty_comps_returns_none_rate():
    result = historical_exceedance(10_000, [])
    assert result["total"] == 0
    assert result["rate"] is None


def test_exceedance_can_normalize_by_opening_bid():
    comps = [
        _Wrap({"winning_bid": 20_000, "opening_bid": 10_000}),  # 2x
        _Wrap({"winning_bid": 50_000, "opening_bid": 10_000}),  # 5x
        _Wrap({"winning_bid": 12_000, "opening_bid": 2_000}),   # 6x
    ]
    target = {"opening_bid": 4_000}
    result = historical_exceedance(
        12_000, comps, target=target, normalize_by="opening_bid",
    )
    assert result["cleared"] == 1  # 3x clears only the 2x comp
    assert result["total"] == 3
