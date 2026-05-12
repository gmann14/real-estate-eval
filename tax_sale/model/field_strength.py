"""Field-strength prediction per §8.1 of the spec.

For a target lot, predict the number of bidders we'd expect to face,
plus the probability of attracting no bids at all. The v1 estimator is
deliberately **descriptive**: comp-set median/IQR + no-bid frequency.

No regression yet. Per §8, "Only add a model if it beats that baseline
in rolling-origin backtests." The validation module in
``tax_sale/model/validation.py`` runs that backtest.

Comp pool for this task: lots with outcome ∈ {sold, no_bids}. These
are real bidding observations. Redeemed lots are excluded (no bidding
happened); withdrawn lots are excluded (incomplete observation).
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Optional

from tax_sale.model.comp import CompResult, find_comps

# Outcomes that constitute a real "bidding observation"
BIDDING_OUTCOMES = frozenset({"sold", "no_bids"})


@dataclass
class FieldStrengthEstimate:
    """Descriptive prediction of competition intensity for a target lot.

    All fields are computed from a comp set (typically the top ~10 nearest
    matches). The size of the comp set governs how much trust to put in
    each statistic — under N=10 most percentile breaks are noisy.

    Multiple point estimates are exposed so the validation harness can
    compare them head-to-head. The §8.1 backtest decides which one ships.
    """
    median: Optional[float]
    mean: Optional[float]
    trimmed_mean: Optional[float]  # mean of middle 50% — outlier-resistant
    p25: Optional[float]
    p75: Optional[float]
    min: Optional[int]
    max: Optional[int]
    no_bid_rate: Optional[float]  # fraction of comps that got zero bids
    n_comps: int  # total comps considered
    n_with_bids: int  # comps with at least 1 bid
    comp_bidder_counts: list[int] = field(default_factory=list)

    def is_thin(self, threshold: int = 5) -> bool:
        """Below this comp count, percentile estimates are noisy — flag for user."""
        return self.n_comps < threshold

    def point_estimate(self, name: str = "median") -> Optional[float]:
        """Look up a named point estimate ('median' / 'mean' / 'trimmed_mean')."""
        return getattr(self, name)


def predict_field_strength(
    target: dict,
    pool: list[dict],
    *,
    n_comps: int = 10,
    require_prior_year: bool = True,
    min_available_weight: int = 30,
) -> FieldStrengthEstimate:
    """Return a descriptive bidder-count prediction for ``target``.

    Larger comp set (n=10 default) than the 5-comp bid sheet because we're
    aggregating a count statistic, not picking representative examples.
    """
    comps = find_comps(
        target, pool, n=n_comps,
        require_outcomes=BIDDING_OUTCOMES,
        require_prior_year=require_prior_year,
        min_available_weight=min_available_weight,
    )
    return _summarise_field_strength(comps)


def _trimmed_mean(values: list[int], trim_pct: float = 0.25) -> float:
    """Mean of the middle ``(1 - 2*trim_pct)`` fraction of values.

    With default 25% trim and n=10: discard 2 lowest + 2 highest, average
    the middle 6. With n<4, trimming would remove everything; we fall
    back to the regular mean.
    """
    sorted_v = sorted(values)
    n = len(sorted_v)
    trim_count = int(n * trim_pct)
    if trim_count == 0:
        return statistics.mean(sorted_v)
    trimmed = sorted_v[trim_count:n - trim_count]
    if not trimmed:
        return statistics.mean(sorted_v)
    return statistics.mean(trimmed)


def _summarise_field_strength(comps: list[CompResult]) -> FieldStrengthEstimate:
    counts = [int(c.comp.get("bidder_count", 0)) for c in comps]
    if not counts:
        return FieldStrengthEstimate(
            median=None, mean=None, trimmed_mean=None, p25=None, p75=None,
            min=None, max=None, no_bid_rate=None,
            n_comps=0, n_with_bids=0,
        )
    n_with_bids = sum(1 for c in counts if c > 0)
    no_bid_rate = (len(counts) - n_with_bids) / len(counts)
    sorted_counts = sorted(counts)
    n = len(sorted_counts)
    return FieldStrengthEstimate(
        median=statistics.median(sorted_counts),
        mean=statistics.mean(sorted_counts),
        trimmed_mean=_trimmed_mean(sorted_counts, trim_pct=0.25),
        p25=sorted_counts[max(0, (n - 1) // 4)],
        p75=sorted_counts[min(n - 1, (3 * (n - 1)) // 4)],
        min=sorted_counts[0],
        max=sorted_counts[-1],
        no_bid_rate=no_bid_rate,
        n_comps=n,
        n_with_bids=n_with_bids,
        comp_bidder_counts=sorted_counts,
    )


def format_estimate(est: FieldStrengthEstimate) -> str:
    """Human-readable one-line summary for the bid sheet."""
    if est.n_comps == 0:
        return "no comparable bidding observations"
    if est.median is None:
        return f"({est.n_comps} comps, but no usable bidder counts)"
    thin = " (sample is thin)" if est.is_thin() else ""
    no_bid_pct = f"{est.no_bid_rate:.0%}" if est.no_bid_rate is not None else "?"
    return (
        f"median {est.median:.0f} bidders "
        f"(P25={est.p25}, P75={est.p75}, range {est.min}-{est.max}); "
        f"no-bid rate {no_bid_pct} ({est.n_comps} comps){thin}"
    )
