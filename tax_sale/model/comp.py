"""Weighted comp-scoring per §7 of the spec.

For each live property, return the N best historical comps using a
transparent weighted similarity score rather than generic Gower distance.
Every comp carries the reasons it matched and the reasons it may be bad,
so the human can override or exclude comps manually downstream.

Score weights are tunable; the v1 defaults reflect what the dataset
actually supports (community/geography signals are sparse since
2021-2023 tender packages aren't always parsed). Missing fields reduce the
effective score via a completeness penalty, so a sparse record cannot look
like a perfect comp because it only shares one easy field.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# Default weights summing to 100. Tweak in `score_lot_similarity(weights=...)`.
DEFAULT_WEIGHTS = {
    "property_type": 30,        # has_structure (vacant vs improved) - first-order signal
    "road_access": 25,          # exact match worth full; partial credit for both-have-legal-access
    "opening_bid_bucket": 15,   # rough $-range comparability (proxy for property value)
    "title_marketable": 10,     # title-system risk signal
    "shore_privileges": 10,     # waterfront proximity / value-driver
    "encumbrances": 5,          # liens / mortgage friction
    "hst_applicable": 5,        # commercial/recreational signal
}


@dataclass
class CompResult:
    """One ranked comp with the reasoning trail attached."""
    comp: dict  # the historical lot row
    score: float  # 0-100, normalized over available fields with completeness penalty
    available_weight: int  # sum of weights actually compared
    why_matched: list[str] = field(default_factory=list)
    why_weak: list[str] = field(default_factory=list)


def _opening_bid_overlap(a: float, b: float) -> float:
    """Return a partial-credit fraction in [0,1] for how close two opening bids are."""
    if a == 0 or b == 0:
        return 0
    ratio = max(a, b) / min(a, b)
    if ratio <= 1.5:
        return 1.0
    if ratio <= 3.0:
        return 0.66
    if ratio <= 10.0:
        return 0.33
    return 0.0


def score_lot_similarity(
    target: dict, comp: dict, weights: Optional[dict] = None
) -> CompResult:
    """Return a `CompResult` ranking ``comp`` against ``target``.

    Both arguments are merged-dataset rows from `tax_sale.dataset`.
    Fields missing on either side are skipped (not penalized).
    """
    w = weights or DEFAULT_WEIGHTS
    total = 0
    score = 0.0
    matched: list[str] = []
    weak: list[str] = []

    # 1. Property type — has_structure
    t, c = target.get("has_structure"), comp.get("has_structure")
    if t is not None and c is not None:
        total += w["property_type"]
        if t == c:
            score += w["property_type"]
            matched.append(f"both {'improved' if t else 'vacant'}")
        else:
            weak.append(f"target is {'improved' if t else 'vacant'}, comp is {'improved' if c else 'vacant'}")

    # 2. Road access class — exact or partial-legal-access credit
    t, c = target.get("road_access_class"), comp.get("road_access_class")
    LEGAL = {"abuts_public", "easement_or_ROW"}
    if t and c and t != "unknown" and c != "unknown":
        total += w["road_access"]
        if t == c:
            score += w["road_access"]
            matched.append(f"both access={t}")
        elif t in LEGAL and c in LEGAL:
            score += w["road_access"] * 0.6
            matched.append("both have legal access (different mechanism)")
        else:
            weak.append(f"access differs: target={t}, comp={c}")

    # 3. Opening bid bucket — rough property-value proxy
    t, c = target.get("opening_bid"), comp.get("opening_bid")
    if t and c:
        total += w["opening_bid_bucket"]
        frac = _opening_bid_overlap(t, c)
        score += w["opening_bid_bucket"] * frac
        if frac >= 0.66:
            matched.append(f"opening-bid range close (${min(t,c):,.0f}-${max(t,c):,.0f})")
        else:
            weak.append(f"opening bids differ ${t:,.0f} vs ${c:,.0f}")

    # 4. Title marketable
    t, c = target.get("title_marketable"), comp.get("title_marketable")
    if t and c:
        total += w["title_marketable"]
        if t == c:
            score += w["title_marketable"]
            matched.append(f"both title={t}")
        else:
            weak.append(f"title differs: target={t}, comp={c}")

    # 5. Shore privileges (waterfront proxy)
    t, c = target.get("shore_privileges"), comp.get("shore_privileges")
    if t is not None and c is not None:
        total += w["shore_privileges"]
        if t == c:
            score += w["shore_privileges"]
            if t:
                matched.append("both waterfront/shore-privilege")
        else:
            weak.append(f"only one has shore privileges (target={t})")

    # 6. Encumbrances flag
    t, c = target.get("has_encumbrances"), comp.get("has_encumbrances")
    if t is not None and c is not None:
        total += w["encumbrances"]
        if t == c:
            score += w["encumbrances"]
        else:
            weak.append(f"encumbrance status differs (target={t}, comp={c})")

    # 7. HST applicable
    t, c = target.get("hst_applicable"), comp.get("hst_applicable")
    if t is not None and c is not None:
        total += w["hst_applicable"]
        if t == c:
            score += w["hst_applicable"]

    max_weight = sum(w.values())
    normalized = (100 * score / total) if total > 0 else 0
    completeness = total / max_weight if max_weight else 0
    adjusted = normalized * completeness
    return CompResult(
        comp=comp, score=adjusted, available_weight=total,
        why_matched=matched, why_weak=weak,
    )


def find_comps(
    target: dict, pool: list[dict], n: int = 5,
    weights: Optional[dict] = None,
    require_sold: bool = False,
    require_outcomes: Optional[set[str]] = None,
    require_prior_year: bool = True,
    min_available_weight: int = 30,
) -> list[CompResult]:
    """Return the top ``n`` ranked comps from ``pool`` relative to ``target``.

    Args:
        target: the merged-dataset row for the lot we're evaluating
        pool: all historical lots (typically the full dataset; target is filtered out)
        n: how many comps to return
        require_sold: convenience flag; equivalent to ``require_outcomes={"sold"}``
        require_outcomes: set of allowed outcomes. ``None`` = no filter.
            Common values: ``{"sold"}`` (exceedance curve), ``{"sold", "no_bids"}``
            (field-strength model — both are real bidding observations). Takes
            precedence over ``require_sold`` when both are supplied.
        require_prior_year: skip comps from the same year or later (avoid look-ahead bias
            during rolling-origin backtests)
        min_available_weight: drop comps where fewer than this many weight-points
            could be compared (avoids spurious "100% match on 5 weight" results)
    """
    if require_outcomes is None and require_sold:
        require_outcomes = {"sold"}

    target_key = (target.get("year"), target.get("lot_number"))
    results = []
    for comp in pool:
        comp_key = (comp.get("year"), comp.get("lot_number"))
        if comp_key == target_key:
            continue
        if require_prior_year and (comp.get("year") or 0) >= (target.get("year") or 0):
            continue
        if require_outcomes is not None and comp.get("outcome") not in require_outcomes:
            continue
        result = score_lot_similarity(target, comp, weights=weights)
        if result.available_weight < min_available_weight:
            continue
        results.append(result)
    results.sort(key=lambda r: r.score, reverse=True)
    return results[:n]


def historical_exceedance(
    candidate_bid: float,
    comps: list[CompResult],
    *,
    target: Optional[dict] = None,
    normalize_by: Optional[str] = None,
) -> dict:
    """For a candidate bid, count how many comp-set winning bids it would have exceeded.

    Returns a dict with ``cleared`` (count cleared), ``total`` (comps with a
    winning bid), and ``rate`` (cleared/total, or None if total is 0).
    Following §8 language progression: prefer raw counts under N=20.

    If ``normalize_by`` is supplied, compare bid ratios rather than raw
    dollars: ``candidate_bid / target[normalize_by]`` against each
    ``comp.winning_bid / comp[normalize_by]``. This is safer for production
    bid sheets until assessed/appraised value exists.
    """
    eligible = [c for c in comps if c.comp.get("winning_bid") is not None]
    if normalize_by is not None:
        if target is None or not target.get(normalize_by):
            return {
                "cleared": 0, "total": 0, "rate": None,
                "comp_winning_bids": [], "normalized_by": normalize_by,
            }
        eligible = [c for c in eligible if c.comp.get(normalize_by)]
    if not eligible:
        return {
            "cleared": 0, "total": 0, "rate": None,
            "comp_winning_bids": [], "normalized_by": normalize_by,
        }
    if normalize_by is None:
        cleared = sum(1 for c in eligible if candidate_bid > c.comp["winning_bid"])
    else:
        candidate_ratio = candidate_bid / target[normalize_by]
        cleared = sum(
            1 for c in eligible
            if candidate_ratio > (c.comp["winning_bid"] / c.comp[normalize_by])
        )
    return {
        "cleared": cleared,
        "total": len(eligible),
        "rate": cleared / len(eligible),
        "comp_winning_bids": sorted(c.comp["winning_bid"] for c in eligible),
        "normalized_by": normalize_by,
    }
