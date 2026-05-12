"""Rolling-origin backtests for the field-strength model (§8 validation).

For each target year Y, fit the predictor on lots from years strictly < Y
and evaluate on the lots in Y. This is the right validation strategy at
small N: LOYO produces ~5 noisy folds and the most recent year (which
matters most for the live workflow) gets the most training history.

Per §8: "Report median absolute dollar error, bidder-count prediction
error, empirical interval coverage, exceedance/probability calibration,
and a decision simulation."

This v1 module covers bidder-count prediction. Exceedance and dollar-bid
calibration land in follow-up work.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Optional

from tax_sale.model.field_strength import (
    BIDDING_OUTCOMES,
    FieldStrengthEstimate,
    predict_field_strength,
)


@dataclass
class FieldStrengthFoldResult:
    """One year of held-out validation."""
    target_year: int
    n_target_lots: int
    n_with_prediction: int  # lots where we had ≥1 usable comp
    mae: Optional[float]  # mean absolute error in bidder count
    median_ae: Optional[float]  # median absolute error
    rmse: Optional[float]
    bias: Optional[float]  # mean signed error (predicted - actual)
    no_bid_predicted_rate: Optional[float]  # mean of predicted no_bid_rate
    no_bid_actual_rate: Optional[float]  # actual fraction with bidder_count=0
    per_lot: list[dict] = field(default_factory=list)


@dataclass
class FieldStrengthBacktest:
    """Aggregate of all rolling-origin folds."""
    folds: list[FieldStrengthFoldResult]
    overall_mae: Optional[float]
    overall_median_ae: Optional[float]
    overall_bias: Optional[float]
    n_total_predictions: int


def rolling_origin_field_strength(
    all_lots: list[dict],
    *,
    n_comps: int = 10,
    min_year: Optional[int] = None,
    point_estimate: str = "median",
) -> FieldStrengthBacktest:
    """Run year-by-year backtests of the descriptive field-strength predictor.

    For each year present in ``all_lots`` (greater than ``min_year`` if given,
    and only when the year has ≥2 earlier years available for training):
      - filter pool to strictly-prior years
      - predict bidder_count for each held-out lot in that year
      - score predicted vs actual

    Args:
        all_lots: the unified dataset from ``tax_sale.dataset.load_all_lots()``
        n_comps: how many nearest comps to aggregate per prediction
        min_year: skip folds for years ≤ this (default: skip the earliest year)
        point_estimate: which ``FieldStrengthEstimate`` attribute to use
            as the point prediction. ``"median"`` (default), ``"mean"``,
            or ``"trimmed_mean"`` (outlier-resistant).
    """
    years_sorted = sorted({lot["year"] for lot in all_lots})
    if not years_sorted:
        return FieldStrengthBacktest(folds=[], overall_mae=None,
                                     overall_median_ae=None, overall_bias=None,
                                     n_total_predictions=0)

    earliest = years_sorted[0]
    folds: list[FieldStrengthFoldResult] = []
    all_errors: list[float] = []
    all_signed: list[float] = []

    for target_year in years_sorted:
        if target_year == earliest:
            continue  # No training data
        if min_year is not None and target_year <= min_year:
            continue

        held_out = [l for l in all_lots if l["year"] == target_year
                    and l.get("outcome") in BIDDING_OUTCOMES]
        if not held_out:
            continue

        # Pool = lots from prior years
        pool = [l for l in all_lots if l["year"] < target_year]

        per_lot = []
        errors: list[float] = []
        no_bid_preds: list[float] = []
        actual_no_bids = 0

        for target in held_out:
            est = predict_field_strength(target, pool, n_comps=n_comps,
                                         require_prior_year=False)
            actual = int(target.get("bidder_count", 0))
            if est.n_comps == 0:
                per_lot.append({
                    "year": target["year"], "lot": target["lot_number"],
                    "actual": actual, "predicted": None, "error": None,
                    "n_comps": 0,
                })
                continue
            predicted = est.point_estimate(point_estimate)
            if predicted is None:
                per_lot.append({
                    "year": target["year"], "lot": target["lot_number"],
                    "actual": actual, "predicted": None, "error": None,
                    "n_comps": est.n_comps,
                })
                continue
            err = predicted - actual
            errors.append(abs(err))
            all_errors.append(abs(err))
            all_signed.append(err)
            no_bid_preds.append(est.no_bid_rate or 0)
            if actual == 0:
                actual_no_bids += 1
            per_lot.append({
                "year": target["year"], "lot": target["lot_number"],
                "actual": actual, "predicted": predicted, "error": err,
                "n_comps": est.n_comps,
            })

        n_predicted = len(errors)
        fold = FieldStrengthFoldResult(
            target_year=target_year,
            n_target_lots=len(held_out),
            n_with_prediction=n_predicted,
            mae=statistics.mean(errors) if errors else None,
            median_ae=statistics.median(errors) if errors else None,
            rmse=(sum(e**2 for e in errors) / len(errors)) ** 0.5 if errors else None,
            bias=statistics.mean(p - a for p, a in
                                 [(per["predicted"], per["actual"])
                                  for per in per_lot if per["predicted"] is not None])
                 if errors else None,
            no_bid_predicted_rate=statistics.mean(no_bid_preds) if no_bid_preds else None,
            no_bid_actual_rate=actual_no_bids / len(held_out) if held_out else None,
            per_lot=per_lot,
        )
        folds.append(fold)

    return FieldStrengthBacktest(
        folds=folds,
        overall_mae=statistics.mean(all_errors) if all_errors else None,
        overall_median_ae=statistics.median(all_errors) if all_errors else None,
        overall_bias=statistics.mean(all_signed) if all_signed else None,
        n_total_predictions=len(all_errors),
    )


def format_backtest(bt: FieldStrengthBacktest) -> str:
    """Pretty-print a backtest summary."""
    lines = ["Field-strength rolling-origin backtest:"]
    lines.append(f"  {'year':<6}{'lots':>6}{'predicted':>11}{'MAE':>8}{'medAE':>8}{'bias':>8}{'no-bid pred':>13}{'no-bid actual':>15}")
    for f in bt.folds:
        mae = f"{f.mae:.2f}" if f.mae is not None else "—"
        med = f"{f.median_ae:.2f}" if f.median_ae is not None else "—"
        bias = f"{f.bias:+.2f}" if f.bias is not None else "—"
        nbp = f"{f.no_bid_predicted_rate:.0%}" if f.no_bid_predicted_rate is not None else "—"
        nba = f"{f.no_bid_actual_rate:.0%}" if f.no_bid_actual_rate is not None else "—"
        lines.append(
            f"  {f.target_year:<6}{f.n_target_lots:>6}{f.n_with_prediction:>11}"
            f"{mae:>8}{med:>8}{bias:>8}{nbp:>13}{nba:>15}"
        )
    overall_mae = f"{bt.overall_mae:.2f}" if bt.overall_mae is not None else "—"
    overall_med = f"{bt.overall_median_ae:.2f}" if bt.overall_median_ae is not None else "—"
    overall_bias = f"{bt.overall_bias:+.2f}" if bt.overall_bias is not None else "—"
    lines.append(f"  {'OVERALL':<6}{'':>6}{bt.n_total_predictions:>11}"
                 f"{overall_mae:>8}{overall_med:>8}{overall_bias:>8}")
    return "\n".join(lines)


def compare_predictors(
    all_lots: list[dict],
    predictors: tuple[str, ...] = ("median", "mean", "trimmed_mean"),
    n_comps: int = 10,
) -> dict[str, FieldStrengthBacktest]:
    """Run the rolling-origin backtest for several predictors and return all results."""
    return {
        name: rolling_origin_field_strength(all_lots, n_comps=n_comps, point_estimate=name)
        for name in predictors
    }


@dataclass
class ExceedanceCalibrationResult:
    """Calibration of the historical-exceedance curve on held-out years.

    For each tested exceedance level (e.g. P=0.50 meaning "candidate bid
    at the median of comp winning bids"), we count how often that bid
    would have actually won the held-out auction. A well-calibrated
    curve has predicted_p ≈ actual_win_rate for every p tested.
    """
    n_held_out_lots: int
    by_percentile: dict[float, dict]  # P → {"n", "wins", "win_rate"}
    per_lot: list[dict]


def rolling_origin_exceedance(
    all_lots: list[dict],
    *,
    n_comps: int = 10,
    min_comps: int = 3,
    test_percentiles: tuple[float, ...] = (0.10, 0.25, 0.50, 0.75, 0.90),
) -> ExceedanceCalibrationResult:
    """Backtest the historical-exceedance curve (§8.3).

    For each held-out sold lot L:
      1. Build a comp set from strictly-prior-year sold lots.
      2. For each tested exceedance percentile P (e.g. 0.50), compute the
         candidate bid from the P'th quantile of comp winning-bid/opening-bid
         ratios, then back-transform through the target opening bid.
      3. Check whether that candidate bid would have won the held-out auction
         (i.e. whether it exceeds the actual winning bid).
      4. Aggregate across all held-out lots: per-percentile actual-win rate.

    Well-calibrated curve: at P=0.5 the candidate "median-of-comps" bid should
    actually win ~50% of held-out auctions. Calibration miss tells us whether
    the comp-set winning-bid distribution is representative of the target's
    auction distribution.
    """
    from tax_sale.model.comp import find_comps

    years_sorted = sorted({l["year"] for l in all_lots})
    earliest = years_sorted[0] if years_sorted else None

    per_pct = {p: {"n": 0, "wins": 0} for p in test_percentiles}
    per_lot: list[dict] = []
    n_held_out = 0

    for target in all_lots:
        if target.get("outcome") != "sold":
            continue
        if target.get("winning_bid") is None:
            continue
        if not target.get("opening_bid"):
            continue
        year = target.get("year")
        if year is None or year == earliest:
            continue

        comps = find_comps(target, all_lots, n=n_comps,
                           require_outcomes={"sold"}, require_prior_year=True)
        comp_bid_ratios = sorted(
            c.comp["winning_bid"] / c.comp["opening_bid"] for c in comps
            if c.comp.get("winning_bid") is not None and c.comp.get("opening_bid")
        )
        if len(comp_bid_ratios) < min_comps:
            continue

        n_held_out += 1
        actual_winner = target["winning_bid"]
        row = {"year": year, "lot": target["lot_number"],
               "actual_winner": actual_winner, "n_comps": len(comp_bid_ratios),
               "predictions": {}}

        for p in test_percentiles:
            # Candidate bid: target opening bid multiplied by the P-quantile
            # of comp winning/opening ratios. This avoids comparing raw bids
            # across lots with very different minimum bids.
            idx = min(len(comp_bid_ratios) - 1, int(p * len(comp_bid_ratios)))
            candidate = comp_bid_ratios[idx] * target["opening_bid"] + 0.01
            actual_win = candidate > actual_winner
            per_pct[p]["n"] += 1
            if actual_win:
                per_pct[p]["wins"] += 1
            row["predictions"][p] = {
                "candidate_bid": candidate, "actual_win": actual_win,
            }
        per_lot.append(row)

    by_pct = {}
    for p, agg in per_pct.items():
        rate = agg["wins"] / agg["n"] if agg["n"] else None
        by_pct[p] = {**agg, "win_rate": rate}

    return ExceedanceCalibrationResult(
        n_held_out_lots=n_held_out,
        by_percentile=by_pct,
        per_lot=per_lot,
    )


def format_exceedance_calibration(result: ExceedanceCalibrationResult) -> str:
    lines = ["Historical-exceedance calibration (rolling-origin backtest):"]
    lines.append(f"  N held-out lots: {result.n_held_out_lots}")
    lines.append("")
    lines.append(f"  {'predicted P':>13}  {'actual win rate':>17}  "
                 f"{'(wins/n)':>12}  {'calibration gap':>17}")
    for p in sorted(result.by_percentile):
        agg = result.by_percentile[p]
        rate = agg["win_rate"]
        if rate is None:
            lines.append(f"  {p:>13.2f}  {'—':>17}  {'(no data)':>12}")
            continue
        # A well-calibrated bid at predicted exceedance P should win at rate P.
        # gap = actual_win_rate - predicted_P (positive = our P was conservative;
        # negative = our P was optimistic / overstated win probability).
        gap = rate - p
        wins = agg["wins"]
        n = agg["n"]
        ratio_str = f"({wins}/{n})"
        lines.append(
            f"  {p:>13.2f}  {rate:>17.2%}  "
            f"{ratio_str:>12}  {gap:>+17.2%}"
        )
    return "\n".join(lines)


def naive_prior_years_median(
    all_lots: list[dict],
    *,
    n_lookback_years: int = 1,
    min_year: Optional[int] = None,
) -> FieldStrengthBacktest:
    """Naive baseline: predict every held-out lot's bidder count as the median
    of all bidding-outcome lots from the prior ``n_lookback_years`` years.

    This ignores comp similarity entirely. If it ties or beats the comp-based
    predictors in MAE, the comp matching layer isn't earning its complexity
    for field-strength prediction (§8.1 "comp baseline must outperform" rule).
    """
    years_sorted = sorted({lot["year"] for lot in all_lots})
    if not years_sorted:
        return FieldStrengthBacktest(folds=[], overall_mae=None,
                                     overall_median_ae=None, overall_bias=None,
                                     n_total_predictions=0)

    earliest = years_sorted[0]
    folds: list[FieldStrengthFoldResult] = []
    all_errors: list[float] = []
    all_signed: list[float] = []

    for target_year in years_sorted:
        if target_year == earliest:
            continue
        if min_year is not None and target_year <= min_year:
            continue

        held_out = [l for l in all_lots if l["year"] == target_year
                    and l.get("outcome") in BIDDING_OUTCOMES]
        if not held_out:
            continue

        # Pool: last n_lookback_years strictly prior to target
        cutoff = target_year - n_lookback_years
        pool = [l for l in all_lots
                if cutoff <= l["year"] < target_year
                and l.get("outcome") in BIDDING_OUTCOMES]
        if not pool:
            continue
        pool_median = statistics.median(int(l.get("bidder_count", 0)) for l in pool)

        per_lot = []
        errors: list[float] = []
        signed: list[float] = []
        for target in held_out:
            actual = int(target.get("bidder_count", 0))
            err = pool_median - actual
            errors.append(abs(err))
            signed.append(err)
            all_errors.append(abs(err))
            all_signed.append(err)
            per_lot.append({
                "year": target["year"], "lot": target["lot_number"],
                "actual": actual, "predicted": pool_median, "error": err,
                "n_comps": len(pool),
            })

        actual_no_bids = sum(1 for l in held_out if int(l.get("bidder_count", 0)) == 0)
        folds.append(FieldStrengthFoldResult(
            target_year=target_year,
            n_target_lots=len(held_out),
            n_with_prediction=len(errors),
            mae=statistics.mean(errors) if errors else None,
            median_ae=statistics.median(errors) if errors else None,
            rmse=(sum(e**2 for e in errors) / len(errors)) ** 0.5 if errors else None,
            bias=statistics.mean(signed) if signed else None,
            no_bid_predicted_rate=None,  # this baseline doesn't predict no-bid rate
            no_bid_actual_rate=actual_no_bids / len(held_out),
            per_lot=per_lot,
        ))

    return FieldStrengthBacktest(
        folds=folds,
        overall_mae=statistics.mean(all_errors) if all_errors else None,
        overall_median_ae=statistics.median(all_errors) if all_errors else None,
        overall_bias=statistics.mean(all_signed) if all_signed else None,
        n_total_predictions=len(all_errors),
    )


def format_predictor_comparison(results: dict[str, FieldStrengthBacktest]) -> str:
    """One-table head-to-head of predictor performance."""
    lines = [f"  {'predictor':<16}{'n_pred':>8}{'MAE':>8}{'medAE':>8}{'bias':>8}"]
    for name, bt in results.items():
        mae = f"{bt.overall_mae:.2f}" if bt.overall_mae is not None else "—"
        med = f"{bt.overall_median_ae:.2f}" if bt.overall_median_ae is not None else "—"
        bias = f"{bt.overall_bias:+.2f}" if bt.overall_bias is not None else "—"
        lines.append(
            f"  {name:<16}{bt.n_total_predictions:>8}{mae:>8}{med:>8}{bias:>8}"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    from tax_sale.dataset import load_all_lots

    records = load_all_lots()
    print("=== Comp-based predictors (year-by-year) ===")
    bt = rolling_origin_field_strength(records)
    print(format_backtest(bt))
    print()

    print("=== Head-to-head: all predictors ===")
    results = compare_predictors(records)
    # Add naive baselines
    results["naive_prior_year"] = naive_prior_years_median(records, n_lookback_years=1)
    results["naive_prior_2yr"] = naive_prior_years_median(records, n_lookback_years=2)
    results["naive_all_prior"] = naive_prior_years_median(records, n_lookback_years=10)
    print(format_predictor_comparison(results))
    print()
    print("=== Historical-exceedance calibration (§8.3) ===")
    excd = rolling_origin_exceedance(records, n_comps=10, min_comps=3)
    print(format_exceedance_calibration(excd))
