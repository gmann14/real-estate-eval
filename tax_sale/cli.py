"""Command-line entry for the tax-sale toolkit.

Usage:
    python -m tax_sale bidsheet --year 2026 --lot 2 [--ceiling 45000]
    python -m tax_sale bidsheet-all --year 2026 [--ceiling 50000] [--out-dir DIR]
    python -m tax_sale stats
    python -m tax_sale backtest [--kind field-strength|exceedance|both]
    python -m tax_sale enrichment-template --year 2027 --out FILE
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path
from typing import Optional


def _load_records(*, strict: bool = False):
    """Lazy import so test discovery doesn't pay the parse cost."""
    from tax_sale.dataset import load_all_lots
    return load_all_lots(strict=strict)


# --- subcommand: bidsheet --------------------------------------------------


def cmd_bidsheet(args: argparse.Namespace) -> int:
    from tax_sale.model.bidsheet import render_bidsheet
    records = _load_records(strict=args.strict)
    target = next(
        (r for r in records if r["year"] == args.year and r["lot_number"] == args.lot),
        None,
    )
    if target is None:
        print(f"No lot found for year={args.year}, lot={args.lot}", file=sys.stderr)
        return 1
    print(render_bidsheet(target, records, private_ceiling=args.ceiling))
    return 0


# --- subcommand: bidsheet-all ---------------------------------------------


def cmd_bidsheet_all(args: argparse.Namespace) -> int:
    from tax_sale.model.bidsheet import render_bidsheet
    records = _load_records(strict=args.strict)
    year_records = [r for r in records if r["year"] == args.year]
    if not year_records:
        print(f"No lots found for year={args.year}", file=sys.stderr)
        return 1

    out_dir: Optional[Path] = args.out_dir
    if out_dir is not None:
        out_dir.mkdir(parents=True, exist_ok=True)

    written = 0
    for target in sorted(year_records, key=lambda r: r["lot_number"]):
        sheet = render_bidsheet(target, records, private_ceiling=args.ceiling)
        if out_dir is None:
            print(sheet)
            print("\n---\n")
        else:
            path = out_dir / f"lot-{target['lot_number']:03d}.md"
            path.write_text(sheet)
            written += 1
    if out_dir is not None:
        print(f"Wrote {written} bid sheets to {out_dir}", file=sys.stderr)
    return 0


# --- subcommand: stats ----------------------------------------------------


def cmd_stats(args: argparse.Namespace) -> int:
    records = _load_records(strict=args.strict)
    print(f"=== Dataset summary ===")
    print(f"Total lot records: {len(records)}")

    # Outcomes
    outcomes = Counter(r["outcome"] for r in records)
    print(f"\nOutcomes:")
    for o, c in outcomes.most_common():
        print(f"  {o:<12} {c:>4}")

    # Per-year sold counts
    sold_by_year = Counter(r["year"] for r in records if r["outcome"] == "sold")
    print(f"\nSold lots per year:")
    for y in sorted(sold_by_year):
        print(f"  {y}: {sold_by_year[y]}")

    # Provenance
    print(f"\nProvenance (listing / award / property-info):")
    sources = Counter()
    for r in records:
        key = (
            r.get("has_listing_record", False),
            r.get("has_award_record", False),
            r.get("has_property_info_record", False),
        )
        sources[key] += 1
    for (l, a, p), c in sorted(sources.items(), key=lambda kv: -kv[1]):
        parts = [s for s, ok in zip(("list", "award", "info"), (l, a, p)) if ok]
        label = " + ".join(parts) or "(none)"
        print(f"  {label:<30} {c:>4}")

    # Bid totals
    total_bids = sum(r["bidder_count"] for r in records)
    print(f"\nTotal submitted bids: {total_bids:,}")
    return 0


# --- subcommand: backtest -------------------------------------------------


def cmd_backtest(args: argparse.Namespace) -> int:
    from tax_sale.model.validation import (
        compare_predictors,
        format_backtest,
        format_exceedance_calibration,
        format_predictor_comparison,
        naive_prior_years_median,
        rolling_origin_exceedance,
        rolling_origin_field_strength,
    )
    records = _load_records(strict=args.strict)

    if args.kind in ("field-strength", "both"):
        print("=== §8.1 Field-strength backtest ===")
        bt = rolling_origin_field_strength(records)
        print(format_backtest(bt))
        print()
        print("=== Head-to-head predictor comparison ===")
        results = compare_predictors(records)
        results["naive_prior_year"] = naive_prior_years_median(records, n_lookback_years=1)
        results["naive_prior_2yr"] = naive_prior_years_median(records, n_lookback_years=2)
        results["naive_all_prior"] = naive_prior_years_median(records, n_lookback_years=10)
        print(format_predictor_comparison(results))
        print()

    if args.kind in ("exceedance", "both"):
        print("=== §8.3 Historical-exceedance calibration ===")
        excd = rolling_origin_exceedance(records, n_comps=10, min_comps=3)
        print(format_exceedance_calibration(excd))

    return 0


# --- subcommand: enrichment-template ---------------------------------------


def cmd_enrichment_template(args: argparse.Namespace) -> int:
    """Write a CSV template for the user to fill in from PVSC public search."""
    from tax_sale.dataset import lots_missing_enrichment
    from tax_sale.sources.enrichment import write_template

    records = _load_records()
    missing = lots_missing_enrichment(records, only_year=args.year)
    if not missing:
        print(f"All lots already have enrichment data; nothing to write.", file=sys.stderr)
        return 0

    out_path: Path = args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_template(out_path, missing)
    print(
        f"Wrote {len(missing)} lots to {out_path}.\n"
        f"Look each AAN up at https://www.pvsc.ca/find-assessment in your browser, "
        f"paste the values into the CSV, then re-run any tax_sale command — "
        f"the enrichment is picked up automatically.",
        file=sys.stderr,
    )
    return 0


# --- main ------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tax_sale", description=__doc__)
    subs = parser.add_subparsers(dest="cmd", required=True)

    # bidsheet
    bs = subs.add_parser("bidsheet", help="Render a bid sheet for one target lot")
    bs.add_argument("--year", type=int, required=True)
    bs.add_argument("--lot", type=int, required=True)
    bs.add_argument("--ceiling", type=float, default=None,
                    help="Private ceiling (max rational bid) for the decision scenarios")
    bs.add_argument("--strict", action="store_true",
                    help="Fail on parser errors or missing OCR fixtures instead of dropping records")
    bs.set_defaults(func=cmd_bidsheet)

    # bidsheet-all
    bsa = subs.add_parser("bidsheet-all", help="Render bid sheets for every lot in a year")
    bsa.add_argument("--year", type=int, required=True)
    bsa.add_argument("--ceiling", type=float, default=None,
                     help="Default private ceiling applied to all lots")
    bsa.add_argument("--out-dir", type=Path, default=None,
                     help="If set, write one .md file per lot; otherwise print to stdout")
    bsa.add_argument("--strict", action="store_true",
                     help="Fail on parser errors or missing OCR fixtures instead of dropping records")
    bsa.set_defaults(func=cmd_bidsheet_all)

    # stats
    st = subs.add_parser("stats", help="Print dataset summary statistics")
    st.add_argument("--strict", action="store_true",
                    help="Fail on parser errors or missing OCR fixtures instead of dropping records")
    st.set_defaults(func=cmd_stats)

    # backtest
    bt = subs.add_parser("backtest", help="Run validation backtests (§8.1 and §8.3)")
    bt.add_argument("--kind", choices=["field-strength", "exceedance", "both"],
                    default="both")
    bt.add_argument("--strict", action="store_true",
                    help="Fail on parser errors or missing OCR fixtures instead of dropping records")
    bt.set_defaults(func=cmd_backtest)

    # enrichment-template
    et = subs.add_parser(
        "enrichment-template",
        help="Write a CSV template of lots needing PVSC lookup",
    )
    et.add_argument("--year", type=int, default=None,
                    help="Only include lots from this year (defaults to all years)")
    et.add_argument("--out", type=Path, required=True,
                    help="Destination CSV path")
    et.set_defaults(func=cmd_enrichment_template)

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
