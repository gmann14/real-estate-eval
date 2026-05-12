"""Tests for the rolling-origin field-strength backtest."""
from __future__ import annotations

import pytest

from tax_sale.model.validation import (
    ExceedanceCalibrationResult,
    FieldStrengthBacktest,
    FieldStrengthFoldResult,
    compare_predictors,
    format_backtest,
    format_exceedance_calibration,
    naive_prior_years_median,
    rolling_origin_exceedance,
    rolling_origin_field_strength,
)


def _lot(year, lot_no, bidder_count, outcome="sold", **overrides):
    base = dict(
        year=year, lot_number=lot_no,
        sale_lot_id=f"MODL-{year}-{lot_no}",
        opening_bid=10_000.0, has_structure=False,
        road_access_class="abuts_public", title_marketable="yes",
        shore_privileges=False, hst_applicable=False, has_encumbrances=False,
        outcome=outcome, winning_bid=20_000.0 if outcome == "sold" else None,
        bidder_count=bidder_count,
    )
    base.update(overrides)
    return base


def test_rolling_origin_skips_earliest_year():
    """The earliest year has no prior data; it should be skipped."""
    lots = [
        _lot(2024, 1, 5),
        _lot(2025, 1, 6),
        _lot(2026, 1, 7),
    ]
    bt = rolling_origin_field_strength(lots)
    years = {f.target_year for f in bt.folds}
    assert 2024 not in years  # earliest is skipped
    assert 2025 in years or 2026 in years


def test_rolling_origin_skips_non_bidding_outcomes():
    """Held-out targets must be sold or no_bids (real bidding outcomes)."""
    lots = [
        _lot(2024, 1, 5),
        _lot(2024, 2, 8),
        _lot(2025, 1, 0, outcome="redeemed"),  # skipped as held-out
        _lot(2025, 2, 5),
    ]
    bt = rolling_origin_field_strength(lots)
    fold_2025 = next((f for f in bt.folds if f.target_year == 2025), None)
    assert fold_2025 is not None
    # Only lot 2 should be in held-out (lot 1 was redeemed)
    assert fold_2025.n_target_lots == 1


def test_rolling_origin_emits_per_lot_records():
    lots = [
        _lot(2024, 1, 5),
        _lot(2024, 2, 7),
        _lot(2025, 1, 6),
    ]
    bt = rolling_origin_field_strength(lots, n_comps=10)
    fold = next(f for f in bt.folds if f.target_year == 2025)
    assert len(fold.per_lot) == 1
    rec = fold.per_lot[0]
    assert rec["lot"] == 1
    assert rec["actual"] == 6


def test_rolling_origin_format_runs_without_errors():
    """Smoke test the formatter against a sparse setup."""
    bt = rolling_origin_field_strength([
        _lot(2024, 1, 5),
        _lot(2025, 1, 6),
    ])
    text = format_backtest(bt)
    assert "rolling-origin" in text.lower() or "year" in text.lower()


def test_rolling_origin_empty_input():
    bt = rolling_origin_field_strength([])
    assert bt.folds == []
    assert bt.n_total_predictions == 0


def test_rolling_origin_correct_overall_metrics():
    """When folds report errors, overall metrics aggregate correctly."""
    # Build a tiny dataset where predictions will be made
    lots = []
    # 2024 training data: 5 lots, all 5 bidders
    for i in range(5):
        lots.append(_lot(2024, i+1, 5))
    # 2025 held-out: 2 lots, actual bidders 5 and 7
    lots.append(_lot(2025, 1, 5))
    lots.append(_lot(2025, 2, 7))
    bt = rolling_origin_field_strength(lots, n_comps=10)
    fold = next(f for f in bt.folds if f.target_year == 2025)
    # Predicted = median of comp set = 5 for both targets
    # Errors: |5-5|=0, |5-7|=2 → MAE = 1.0
    assert fold.mae == pytest.approx(1.0)
    assert bt.overall_mae == pytest.approx(1.0)


# --- predictor comparison + naive baseline ---------------------------------


def test_compare_predictors_returns_one_backtest_per_name():
    lots = [_lot(2024, i+1, 5) for i in range(5)] + [_lot(2025, 1, 6)]
    results = compare_predictors(lots, predictors=("median", "mean", "trimmed_mean"))
    assert set(results.keys()) == {"median", "mean", "trimmed_mean"}
    for bt in results.values():
        assert bt.n_total_predictions >= 0


def test_naive_baseline_uses_pool_median():
    """Predict every held-out lot's bidder count as the median of pool lots."""
    # Pool: 4 lots in 2024 with bidder counts 2, 4, 6, 8 → median = 5
    lots = [_lot(2024, i+1, c) for i, c in enumerate([2, 4, 6, 8])]
    # Held-out: 2025 lot with actual bidder count 7
    lots.append(_lot(2025, 1, 7))
    bt = naive_prior_years_median(lots, n_lookback_years=1)
    fold = next(f for f in bt.folds if f.target_year == 2025)
    assert fold.per_lot[0]["predicted"] == 5
    assert fold.per_lot[0]["error"] == -2  # predicted 5, actual 7
    assert fold.mae == pytest.approx(2.0)


def test_naive_baseline_skips_redeemed_lots():
    """Redeemed lots aren't bidding observations and shouldn't enter the pool median."""
    lots = [
        _lot(2024, 1, 4),
        _lot(2024, 2, 6),
        _lot(2024, 3, 0, outcome="redeemed"),  # ignored
        _lot(2025, 1, 5),
    ]
    bt = naive_prior_years_median(lots, n_lookback_years=1)
    fold = next(f for f in bt.folds if f.target_year == 2025)
    # Pool median should be from [4, 6] only → 5
    assert fold.per_lot[0]["predicted"] == 5


def test_naive_baseline_respects_lookback_window():
    """With lookback=1, only 2024 lots contribute to 2025's prediction (not 2022)."""
    lots = [
        _lot(2022, 1, 50),  # outlier year, should be ignored
        _lot(2024, 1, 5),
        _lot(2024, 2, 5),
        _lot(2025, 1, 5),
    ]
    bt = naive_prior_years_median(lots, n_lookback_years=1)
    fold = next(f for f in bt.folds if f.target_year == 2025)
    assert fold.per_lot[0]["predicted"] == 5  # not 50


def test_naive_baseline_no_pool_yields_no_predictions():
    """If a target year has no prior bidding data within the lookback, skip the fold."""
    lots = [_lot(2025, 1, 5)]  # only year present
    bt = naive_prior_years_median(lots, n_lookback_years=1)
    assert bt.n_total_predictions == 0


# --- exceedance calibration ------------------------------------------------


def _sold_lot(year, lot_no, winning_bid, **overrides):
    """Build a sold lot suitable for the exceedance backtest."""
    return _lot(year, lot_no, bidder_count=3, outcome="sold",
                winning_bid=winning_bid, **overrides)


def test_exceedance_backtest_returns_per_percentile_rates():
    lots = []
    # Training pool: 10 prior-year lots with winning bids 1000..10000
    for i, wb in enumerate(range(1000, 11000, 1000)):
        lots.append(_sold_lot(2024, i + 1, wb))
    # Held-out: a target lot in 2025 with a known winning bid
    lots.append(_sold_lot(2025, 1, 5000))
    result = rolling_origin_exceedance(lots, n_comps=10, min_comps=3)
    assert result.n_held_out_lots == 1
    # Per-percentile breakdown is populated
    for p in (0.10, 0.25, 0.50, 0.75, 0.90):
        assert p in result.by_percentile
        assert result.by_percentile[p]["n"] == 1


def test_exceedance_backtest_skips_no_bids_lots():
    lots = [_sold_lot(2024, i + 1, 5000) for i in range(5)]
    # Held-out lot has no_bids — shouldn't be in the held-out set
    lots.append(_lot(2025, 1, 0, outcome="no_bids", winning_bid=None))
    result = rolling_origin_exceedance(lots, n_comps=10, min_comps=3)
    assert result.n_held_out_lots == 0


def test_exceedance_backtest_skips_thin_comp_sets():
    """If fewer than min_comps prior comps survive, the lot is skipped."""
    lots = [
        _sold_lot(2024, 1, 5000),  # only 1 prior comp
        _sold_lot(2025, 1, 7000),
    ]
    result = rolling_origin_exceedance(lots, n_comps=10, min_comps=3)
    assert result.n_held_out_lots == 0  # 1 < min_comps=3


def test_format_exceedance_calibration_runs():
    result = ExceedanceCalibrationResult(
        n_held_out_lots=5,
        by_percentile={0.5: {"n": 5, "wins": 2, "win_rate": 0.4}},
        per_lot=[],
    )
    text = format_exceedance_calibration(result)
    assert "calibration" in text.lower()
    assert "N held-out lots: 5" in text


def test_exceedance_well_calibrated_when_target_drawn_from_comp_distribution():
    """If held-out winners are drawn from the same distribution as comps,
    the calibration gap should be small at the median percentile."""
    # 20 prior-year lots with winning bids 1000..20000
    lots = [_sold_lot(2024, i + 1, 1000 + i * 1000) for i in range(20)]
    # 10 held-out lots with similar distribution
    for i in range(10):
        lots.append(_sold_lot(2025, i + 1, 1000 + i * 2000))
    result = rolling_origin_exceedance(lots, n_comps=10, min_comps=3,
                                       test_percentiles=(0.5,))
    rate = result.by_percentile[0.5]["win_rate"]
    # Should be roughly 50% — allow generous tolerance for small N
    assert rate is not None
    assert 0.2 < rate < 0.8
