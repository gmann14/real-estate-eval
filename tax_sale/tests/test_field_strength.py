"""Tests for the §8.1 field-strength predictor."""
from __future__ import annotations

import pytest

from tax_sale.model.field_strength import (
    FieldStrengthEstimate,
    _summarise_field_strength,
    _trimmed_mean,
    format_estimate,
    predict_field_strength,
)
from tax_sale.model.comp import CompResult


def _wrap(comp_dict, score=80, weight=80) -> CompResult:
    """Build a CompResult around a dict, for direct _summarise testing."""
    return CompResult(comp=comp_dict, score=score, available_weight=weight)


def _lot(**overrides) -> dict:
    base = dict(
        year=2026, lot_number=1, sale_lot_id="MODL-2026-1",
        opening_bid=10_000.0, has_structure=False,
        road_access_class="abuts_public", title_marketable="yes",
        shore_privileges=False, hst_applicable=False, has_encumbrances=False,
        outcome="sold", winning_bid=20_000.0, bidder_count=5,
    )
    base.update(overrides)
    base.setdefault("sale_lot_id", f"MODL-{base['year']}-{base['lot_number']}")
    return base


# --- _summarise_field_strength --------------------------------------------


def test_summarise_empty_comps_returns_nones():
    est = _summarise_field_strength([])
    assert est.median is None
    assert est.n_comps == 0


def test_summarise_basic_stats():
    comps = [_wrap({"bidder_count": c}) for c in [2, 4, 5, 7, 10]]
    est = _summarise_field_strength(comps)
    assert est.n_comps == 5
    assert est.median == 5
    assert est.mean == pytest.approx(5.6)
    assert est.min == 2
    assert est.max == 10
    assert est.no_bid_rate == 0


def test_summarise_no_bid_rate():
    comps = [_wrap({"bidder_count": c}) for c in [0, 0, 3, 5, 7]]
    est = _summarise_field_strength(comps)
    assert est.n_comps == 5
    assert est.n_with_bids == 3
    assert est.no_bid_rate == pytest.approx(0.4)


def test_summarise_handles_missing_bidder_count():
    """Missing bidder_count defaults to 0 (treated as no-bid)."""
    comps = [_wrap({}), _wrap({"bidder_count": 5})]
    est = _summarise_field_strength(comps)
    assert est.min == 0
    assert est.max == 5
    assert est.no_bid_rate == 0.5


# --- predict_field_strength (integration with find_comps) -----------------


def test_predict_excludes_redeemed_lots_from_pool():
    """Redeemed lots have no bidding observation; they shouldn't influence the prediction."""
    target = _lot(year=2026, lot_number=99)
    pool = [
        _lot(year=2025, lot_number=1, bidder_count=10, outcome="sold"),
        _lot(year=2025, lot_number=2, bidder_count=0, outcome="redeemed"),
        _lot(year=2025, lot_number=3, bidder_count=5, outcome="sold"),
    ]
    est = predict_field_strength(target, pool)
    assert est.n_comps == 2  # the redeemed lot is excluded
    assert est.median == 7.5  # median of [5, 10]


def test_predict_includes_no_bid_lots():
    """no_bids lots ARE real bidding observations — zero competition is data."""
    target = _lot(year=2026, lot_number=99)
    pool = [
        _lot(year=2025, lot_number=1, bidder_count=8, outcome="sold"),
        _lot(year=2025, lot_number=2, bidder_count=0, outcome="no_bids", winning_bid=None),
    ]
    est = predict_field_strength(target, pool)
    assert est.n_comps == 2
    assert est.no_bid_rate == 0.5


def test_predict_requires_prior_years():
    """Default is require_prior_year=True; same-year comps don't help us."""
    target = _lot(year=2026, lot_number=99)
    pool = [
        _lot(year=2026, lot_number=1, bidder_count=5, outcome="sold"),  # same year
        _lot(year=2025, lot_number=1, bidder_count=8, outcome="sold"),  # prior year
    ]
    est = predict_field_strength(target, pool)
    assert est.n_comps == 1
    assert est.median == 8


def test_thin_sample_flag():
    target = _lot(year=2026, lot_number=99)
    pool = [_lot(year=2025, lot_number=i, bidder_count=5, outcome="sold")
            for i in range(3)]
    est = predict_field_strength(target, pool)
    assert est.is_thin(threshold=5) is True
    assert est.is_thin(threshold=2) is False


def test_format_estimate_includes_thin_warning():
    target = _lot(year=2026, lot_number=99)
    pool = [_lot(year=2025, lot_number=i, bidder_count=5, outcome="sold")
            for i in range(3)]
    est = predict_field_strength(target, pool)
    text = format_estimate(est)
    assert "thin" in text
    assert "3 comps" in text


def test_format_estimate_no_data():
    est = FieldStrengthEstimate(
        median=None, mean=None, trimmed_mean=None, p25=None, p75=None,
        min=None, max=None, no_bid_rate=None,
        n_comps=0, n_with_bids=0,
    )
    assert "no comparable" in format_estimate(est)


# --- trimmed mean ---------------------------------------------------------


def test_trimmed_mean_with_default_25pct_trim():
    """For n=10 with 25% trim, discard 2 lowest + 2 highest, mean of middle 6."""
    values = list(range(1, 11))  # 1..10
    # Middle 6: 3..8 → mean = 5.5
    assert _trimmed_mean(values, trim_pct=0.25) == pytest.approx(5.5)


def test_trimmed_mean_falls_back_to_regular_mean_below_4_values():
    values = [1, 2, 3]
    # 25% of 3 = 0 → no trimming, regular mean
    assert _trimmed_mean(values, trim_pct=0.25) == pytest.approx(2.0)


def test_trimmed_mean_handles_pathological_trim():
    """If trim_pct is high enough to remove everything, fall back to regular mean."""
    values = [1, 2]
    # Even if we'd trim everything, the fallback keeps us safe
    assert _trimmed_mean(values, trim_pct=0.5) == pytest.approx(1.5)


def test_summarise_includes_trimmed_mean():
    comps = [_wrap({"bidder_count": c}) for c in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]]
    est = _summarise_field_strength(comps)
    assert est.trimmed_mean == pytest.approx(5.5)
    # And the other point estimates are still computed
    assert est.median == 5.5
    assert est.mean == 5.5


def test_point_estimate_lookup_by_name():
    comps = [_wrap({"bidder_count": c}) for c in [1, 2, 3, 4, 5]]
    est = _summarise_field_strength(comps)
    assert est.point_estimate("median") == est.median
    assert est.point_estimate("mean") == est.mean
    assert est.point_estimate("trimmed_mean") == est.trimmed_mean
