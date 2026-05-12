"""Render a per-lot bid sheet in the §11 Markdown format.

Takes a target lot (a merged-dataset row from ``tax_sale.dataset``) and a
historical pool, finds the nearest comps, computes the historical
exceedance curve, and produces a human-readable markdown block.

This is the user-facing artifact — what the bidder will read on the
morning before tendering. Keep it tight, honest about uncertainty, and
faithful to §8's language progression: raw counts for thin target-level
comp sets, and probability language only when calibration evidence is strong
enough for the specific use case.

**Bidder-count source:** per the §8.1 backtest, comp-based bidder-count
prediction loses to a naive prior-year median. The bidsheet uses the
naive baseline as primary and shows the comp range as exploratory.
"""
from __future__ import annotations

import statistics
from typing import Optional

from tax_sale.model.comp import CompResult, find_comps, historical_exceedance

# §8.1 backtest finding: this set of outcomes constitutes a real bidding observation
# for the naive baseline.
_BIDDING_OUTCOMES = frozenset({"sold", "no_bids"})

# §8 language-progression threshold: below this comp count, the per-target
# exceedance result is reported as raw counts only ("cleared 3 of 5"). Above
# it, percentage language is still descriptive until the current
# normalization choice passes backtesting with acceptable uncertainty.
EXCEEDANCE_PROBABILITY_THRESHOLD = 20
DECISION_MIN_COMPS = 10


def _naive_bidder_count_baseline(
    target: dict, pool: list[dict], *, n_lookback_years: int = 2,
) -> Optional[dict]:
    """Median bidder count from all prior-year bidding lots within the lookback window.

    This is the v1 primary field-strength display because it has better
    coverage and lower bias than the comp-based variant. Returns ``None`` if
    no usable pool is available.
    """
    target_year = target.get("year")
    if target_year is None:
        return None
    cutoff = target_year - n_lookback_years
    pool_lots = [
        l for l in pool
        if l.get("year") is not None
        and cutoff <= l["year"] < target_year
        and l.get("outcome") in _BIDDING_OUTCOMES
    ]
    if not pool_lots:
        return None
    counts = sorted(int(l.get("bidder_count", 0)) for l in pool_lots)
    no_bid_lots = sum(1 for c in counts if c == 0)
    return {
        "median": statistics.median(counts),
        "p25": counts[max(0, (len(counts) - 1) // 4)],
        "p75": counts[min(len(counts) - 1, (3 * (len(counts) - 1)) // 4)],
        "no_bid_rate": no_bid_lots / len(counts),
        "n": len(counts),
        "lookback_years": n_lookback_years,
    }


def _safe_money(v) -> str:
    return f"${v:,.0f}" if v is not None else "—"


def _safe_pct(numerator, denominator) -> str:
    if denominator in (None, 0):
        return "—"
    return f"{100 * numerator / denominator:.1f}%"


def _risk_flags(target: dict) -> list[str]:
    """Per §10: obvious mechanical flags only."""
    flags = []
    if target.get("redeemable_at_publication") is True:
        flags.append("REDEEMABLE: may be pulled before deadline")
    if target.get("hst_applicable") is True:
        flags.append("HST APPLICABLE: buyer pays HST on top of winning bid")
    if target.get("title_marketable") == "no":
        flags.append("TITLE NOT MARKETABLE: legal counsel flagged unmarketable title")
    elif target.get("title_marketable") == "qualified":
        flags.append("TITLE QUALIFIED: marketability hedged with conditions")
    if target.get("road_access_class") == "no_access":
        flags.append("NO ACCESS: legal counsel found no abutting road / no ROW")
    elif target.get("road_access_class") == "easement_or_ROW":
        flags.append("EASEMENT/ROW: access via right-of-way only; extent not searched")
    elif target.get("road_access_class") == "unknown":
        flags.append("ACCESS UNKNOWN: not addressed in legal review")
    if target.get("has_encumbrances") is True:
        summary = target.get("encumbrances_summary") or ""
        flags.append(f"ENCUMBRANCES: {summary[:120]}")
    if target.get("survey_on_file") is False:
        flags.append("NO SURVEY: no modern survey plan on file at Land Registration")
    if target.get("has_structure") is True:
        flags.append("IMPROVED PROPERTY: structure present; occupancy/condition not verified")
    return flags


def _risk_level(target: dict) -> tuple[str, list[str]]:
    """Coarse action gate for bid-sheet readability."""
    blockers: list[str] = []
    diligence: list[str] = []
    if target.get("title_marketable") == "no":
        blockers.append("title not marketable")
    if target.get("road_access_class") == "no_access":
        blockers.append("no apparent legal access")
    if target.get("has_encumbrances") is True:
        diligence.append("encumbrances require review")
    if target.get("title_marketable") == "qualified":
        diligence.append("qualified title opinion")
    if target.get("road_access_class") in {"easement_or_ROW", "unknown"}:
        diligence.append("access requires review")
    if target.get("survey_on_file") is False:
        diligence.append("no modern survey on file")
    if target.get("redeemable_at_publication") is True:
        diligence.append("may redeem before deadline")
    if blockers:
        return "PASS / MANUAL OVERRIDE ONLY", blockers + diligence
    if len(diligence) >= 3:
        return "HIGH DILIGENCE", diligence
    if diligence:
        return "DILIGENCE REQUIRED", diligence
    return "BID-ELIGIBLE ON MECHANICAL FLAGS", []


def _comp_estimates(comps: list[CompResult]) -> dict:
    """Aggregate comp metrics for the Estimates block."""
    wins = [c.comp["winning_bid"] for c in comps if c.comp.get("winning_bid") is not None]
    bidder_counts = [c.comp["bidder_count"] for c in comps
                     if c.comp.get("bidder_count") is not None]
    cushions = [c.comp["runner_up_cushion"] for c in comps
                if c.comp.get("runner_up_cushion") is not None]
    return {
        "median_winning": statistics.median(wins) if wins else None,
        "min_winning": min(wins) if wins else None,
        "max_winning": max(wins) if wins else None,
        "median_bidders": statistics.median(bidder_counts) if bidder_counts else None,
        "min_bidders": min(bidder_counts) if bidder_counts else None,
        "max_bidders": max(bidder_counts) if bidder_counts else None,
        "median_cushion": statistics.median(cushions) if cushions else None,
        "n_with_winning_bid": len(wins),
    }


def _format_exceedance(bid: float, comps: list[CompResult], *, target: dict) -> str:
    """Per §8 language progression.

    Production display uses opening-bid-normalized exceedance because assessed
    value/appraised value is not consistently available yet.
    """
    result = historical_exceedance(
        bid, comps, target=target, normalize_by="opening_bid",
    )
    if result["total"] == 0:
        return "no comparable winning-bid comps"
    cleared = result["cleared"]
    total = result["total"]
    rate = result["rate"]
    if total < EXCEEDANCE_PROBABILITY_THRESHOLD:
        return (
            f"cleared {cleared} of {total} comps "
            f"(opening-bid-normalized; thin sample)"
        )
    return (
        f"cleared {cleared} of {total} comps "
        f"({rate:.0%} historical exceedance; opening-bid-normalized)"
    )


def render_bidsheet(
    target: dict,
    pool: list[dict],
    *,
    n_comps: int = 5,
    decision_n_comps: int = 10,
    private_ceiling: Optional[float] = None,
    scenario_thresholds: tuple = (0.20, 0.50, 0.80),
) -> str:
    """Produce the §11 markdown block for ``target`` against ``pool``."""
    lot_id = target.get("sale_lot_id", "?")
    addr = target.get("display_address") or target.get("aan") or "address unknown"
    aan = target.get("aan") or "AAN uncertain"
    opening = target.get("opening_bid")
    out: list[str] = []

    out.append(f"### {lot_id} — {addr} (AAN {aan})")
    out.append("")
    out.append(f"Opening bid: {_safe_money(opening)}")
    if target.get("hst_applicable"):
        out.append(f"HST: applicable on top of winning bid")
    out.append(f"Status: {target.get('outcome', 'unknown')}")
    if target.get("tendered_at"):
        out.append(f"Tender opens: {target['tendered_at']}")
    out.append("")

    # Property summary
    out.append("**Property summary:**")
    desc_parts = []
    if target.get("lot_description"):
        desc_parts.append(target["lot_description"])
    if target.get("community"):
        desc_parts.append(target["community"])
    if target.get("title_system"):
        desc_parts.append(f"title: {target['title_system']}")
    if target.get("road_access_class"):
        desc_parts.append(f"access: {target['road_access_class']}")
    if target.get("shore_privileges"):
        desc_parts.append("shore/waterfront privileges noted")
    if target.get("has_structure"):
        desc_parts.append("improved (structure present)")
    elif target.get("has_structure") is False:
        desc_parts.append("vacant land")
    for p in desc_parts:
        out.append(f"- {p}")
    out.append("")

    # Risk gate
    level, reasons = _risk_level(target)
    out.append("**Risk gate:**")
    out.append(f"- {level}")
    for reason in reasons[:5]:
        out.append(f"- {reason}")
    out.append("")

    # Risk flags
    flags = _risk_flags(target)
    if flags:
        out.append("**Risk flags:**")
        for f in flags:
            out.append(f"- ⚠ {f}")
        out.append("")

    # Comp set
    comps = find_comps(target, pool, n=n_comps, require_sold=True, require_prior_year=True)
    if not comps:
        out.append("_No comparable historical comps found (insufficient feature overlap)._")
        return "\n".join(out)

    out.append(f"**Top {len(comps)} historical comps:**")
    out.append("")
    out.append("| Score | Lot | Opening | Winning | Bidders | Cushion | Why matched | Why weak |")
    out.append("|------:|-----|--------:|--------:|--------:|--------:|-------------|----------|")
    for c in comps:
        cmp = c.comp
        out.append(
            f"| {c.score:.0f} | {cmp.get('sale_lot_id','?')} "
            f"| {_safe_money(cmp.get('opening_bid'))} "
            f"| {_safe_money(cmp.get('winning_bid'))} "
            f"| {cmp.get('bidder_count', '—')} "
            f"| {_safe_money(cmp.get('runner_up_cushion'))} "
            f"| {'; '.join(c.why_matched) or '—'} "
            f"| {'; '.join(c.why_weak) or '—'} |"
        )
    out.append("")

    # WINNING-BID PREDICTION (THE PRIMARY OUTPUT)
    est = _comp_estimates(comps)
    out.append("## 🎯 Winning-bid prediction")
    out.append("")
    if est["median_winning"] is not None:
        out.append(f"**Most likely winning bid:** {_safe_money(est['median_winning'])} "
                   f"(comp median across {est['n_with_winning_bid']} comparable historical auctions)")
        out.append(f"**Range:** {_safe_money(est['min_winning'])} – {_safe_money(est['max_winning'])}")
        out.append("")

        # Historical-exceedance table: descriptive, not a live win-probability table.
        wins_sorted = sorted(
            c.comp["winning_bid"] for c in comps
            if c.comp.get("winning_bid") is not None
        )
        if wins_sorted:
            out.append("**Bid -> historical raw-dollar exceedance** _(descriptive; use normalized scenario lines below for decisions)_:")
            out.append("")
            out.append("| Your bid would need to be... | ...to historically win this fraction |")
            out.append("|------------------------------|----------------------------------|")
            thresholds = [0.10, 0.25, 0.50, 0.75, 0.90]
            for p in thresholds:
                idx = min(len(wins_sorted) - 1, int(p * len(wins_sorted)))
                bid = wins_sorted[idx] + 0.01
                out.append(f"| {_safe_money(bid)} | {p:.0%} of comparable auctions |")
            out.append("")

    if est["median_cushion"] is not None:
        out.append(f"_Comp median winner-vs-runner-up cushion: {_safe_money(est['median_cushion'])} - "
                   f"the typical margin above second place, not proof of overpayment._")
    if est["n_with_winning_bid"] < EXCEEDANCE_PROBABILITY_THRESHOLD:
        out.append(f"_Comp set is thin (N={est['n_with_winning_bid']}); "
                   f"§8 language progression keeps per-target exceedance as point estimates with caveats._")
    out.append("")

    # Field strength (separate question: HOW MANY bidders, not HOW MUCH they bid)
    out.append("## 👥 Field-strength estimate (expected bidder count)")
    out.append("")
    naive = _naive_bidder_count_baseline(target, pool)
    if naive is not None:
        out.append(
            f"**Expected bidders: {naive['median']:.0f}** "
            f"(P25-P75: {naive['p25']}-{naive['p75']}; no-bid rate: {naive['no_bid_rate']:.0%}). "
            f"Source: naive prior-{naive['lookback_years']}-year median from {naive['n']} bidding lots - "
            f"this baseline has better coverage and lower bias than the comp-based variant."
        )
    if est["median_bidders"] is not None:
        out.append("")
        out.append(f"_Comp-set bidder counts (exploratory only): median {est['median_bidders']:.0f}, "
                   f"range {est['min_bidders']}–{est['max_bidders']}. Treat this as secondary: "
                   f"coverage is lower and bias is higher than the naive baseline._")
    out.append("")

    # Decision scenarios (only if private ceiling provided)
    if private_ceiling is not None and est["median_winning"] is not None:
        out.append("## 💸 Decision scenarios (against your ceiling)")
        out.append("")
        out.append(f"- Private ceiling: {_safe_money(private_ceiling)}")
        decision_comps = find_comps(
            target, pool, n=max(decision_n_comps, n_comps),
            require_sold=True, require_prior_year=True,
        )
        decision_ratios = sorted(
            c.comp["winning_bid"] / c.comp["opening_bid"]
            for c in decision_comps
            if c.comp.get("winning_bid") is not None and c.comp.get("opening_bid")
        )
        if len(decision_ratios) < DECISION_MIN_COMPS:
            out.append(
                f"- Scenario bids suppressed: only {len(decision_ratios)} usable "
                f"opening-bid-normalized sold comps; require at least {DECISION_MIN_COMPS}."
            )
            out.append(f"- Low comp anchor: {_safe_money(est['min_winning'])}")
            out.append(f"- Median comp anchor: {_safe_money(est['median_winning'])}")
            out.append(f"- High comp anchor: {_safe_money(est['max_winning'])}")
            out.append("")
            out.append("_Set private value from external appraisal/PVSC/drive-by diligence before bidding._")
            return "\n".join(out)
        # Build a candidate bid for each scenario by walking up the sorted comp
        # normalized winning-bid ratios until we hit the target exceedance threshold.
        opening = target.get("opening_bid") or 0
        for label, threshold in zip(
            ("Opportunistic", "Serious", "Must-win"), scenario_thresholds
        ):
            # Smallest bid that clears at least `threshold` fraction
            target_clears = int(threshold * len(decision_ratios))
            if target_clears >= len(decision_ratios):
                # Would need to exceed every comp; bid 1¢ above the max
                bid = decision_ratios[-1] * opening + 0.01
            else:
                # Bid just above the (target_clears)-th smallest, to "clear" it
                bid = decision_ratios[target_clears] * opening + 0.01
            ceiling_limited = bid > private_ceiling
            actual_bid = min(bid, private_ceiling)
            exceedance = _format_exceedance(actual_bid, decision_comps, target=target)
            note = " [CEILING-LIMITED]" if ceiling_limited else ""
            out.append(f"- {label} ({_safe_money(actual_bid)}): {exceedance}{note}")
        out.append("")
        out.append("_Suggested submission is **not** a model output — the user picks "
                   "the scenario based on external private value and risk tolerance._")
    elif est["median_winning"] is not None:
        out.append("**Decision scenarios:** _(set `private_ceiling` to enable)_")

    return "\n".join(out)


if __name__ == "__main__":
    import sys
    from tax_sale.dataset import load_all_lots

    records = load_all_lots()
    # Default demo: 2026 Lot 2 (Sabean — clean reference case)
    args = sys.argv[1:]
    year = int(args[0]) if len(args) > 0 else 2026
    lot_no = int(args[1]) if len(args) > 1 else 2
    ceiling = float(args[2]) if len(args) > 2 else None

    target = next(
        (r for r in records if r["year"] == year and r["lot_number"] == lot_no),
        None,
    )
    if target is None:
        print(f"No lot found for year={year}, lot={lot_no}", file=sys.stderr)
        sys.exit(1)

    print(render_bidsheet(target, records, private_ceiling=ceiling))
