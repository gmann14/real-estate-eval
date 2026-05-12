"""Unified historical-dataset loader.

Joins MODL tax-sale artifacts (tender-package listings, award PDFs,
property-info reporting letters) into a single record set keyed by
``(year, lot_number)``. Returns a list of dicts ready for direct
``pd.DataFrame()`` consumption - we don't import pandas at the parser
layer to keep the dependency optional.

The unit of analysis is **one tax-sale lot**, not one AAN. A lot can
bundle multiple AANs/PIDs; that's tracked via ``sale_lot_id`` per §5
of the spec. For v1 we collapse to one AAN/PID per lot row.

Outcome convention:
  - ``sold`` / ``no_bids`` / ``withdrawn`` come from the award PDF
  - ``redeemed`` is the default when a lot appears in the tender
    package but has no corresponding award PDF (the owner paid the
    back taxes before the deadline)
  - ``unknown`` if we have neither award nor tender listing (shouldn't
    happen in practice)
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, Optional

from tax_sale.parse.award_pdf import AwardRecord
from tax_sale.parse.award_pdf import from_json_file as load_award
from tax_sale.parse.encumbrances import parse_encumbrances
from tax_sale.parse.property_info import AutoBackend, PropertyInfo, extract_page1_text
from tax_sale.parse.tender_package import ListedLot, TenderMetadata
from tax_sale.parse.tender_package import parse_pdf as parse_tender
from tax_sale.sources.enrichment import (
    EnrichmentRecord,
    load_enrichment_csv,
    merge_into_lot,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROBE_DIR = REPO_ROOT / "data" / "probe" / "modl"
DEFAULT_ENRICHMENT_CSV = REPO_ROOT / "data" / "enrichment" / "pvsc-manual.csv"

_STRUCTURE_KEYWORDS = ("DWELLING", "BUILDING", "MOBILE", "HOUSE", "COTTAGE")


def _has_structure(listed: Optional[ListedLot]) -> Optional[bool]:
    if listed is None or not listed.lot_description:
        return None
    desc = listed.lot_description.upper()
    if re.search(r"\b(19|20)\d{2}\b.*\b\d{1,3}\s*X\s*\d{1,3}\b", desc):
        return True
    if desc.strip() in {"LAND", "VACANT LAND"}:
        return False
    return any(kw in desc for kw in _STRUCTURE_KEYWORDS)


def _has_encumbrances(info: Optional[PropertyInfo]) -> Optional[bool]:
    if info is None or info.encumbrances_summary is None:
        return None
    return not info.encumbrances_summary.strip().lower().startswith("none")


def _title_ok(info: Optional[PropertyInfo]) -> Optional[bool]:
    if info is None or info.title_marketable is None:
        return None
    return info.title_marketable in {"yes", "qualified"}


def _access_ok(info: Optional[PropertyInfo]) -> Optional[bool]:
    if info is None or info.road_access_class is None:
        return None
    return info.road_access_class in {"abuts_public", "easement_or_ROW"}


def _looks_like_award_form(pdf_path: Path) -> bool:
    """Return True when a misclassified property PDF is actually an award form."""
    try:
        text = extract_page1_text(pdf_path)
    except Exception:
        return False
    lowered = text.lower()
    return "name of bidder" in lowered and "bid amount" in lowered


def _merge_lot(
    *,
    year: int,
    lot_number: int,
    tender_metadata: Optional[TenderMetadata],
    listed: Optional[ListedLot],
    award: Optional[AwardRecord],
    info: Optional[PropertyInfo],
) -> dict:
    """Build a single merged record. None-safe across all three sources."""

    # Outcome: prefer the award's explicit value; fall back to "redeemed"
    # when a lot was listed but never awarded.
    if award is not None:
        outcome = award.outcome
    elif listed is not None:
        outcome = "redeemed"
    else:
        outcome = "unknown"

    # AAN / PID resolution: take the first non-null across sources.
    aan = None
    for source in (listed, award, info):
        if source is not None and getattr(source, "aan", None):
            aan = getattr(source, "aan")
            break

    # Tender ID: prefer the parsed tender-package metadata, else the award PDF header.
    tender_id = (tender_metadata.tender_id if tender_metadata else None) or (
        award.tender_id if award else None
    )

    # Tendered date: similar precedence
    tendered_at = (
        (tender_metadata.tender_opening if tender_metadata else None)
        or (award.tendered_at if award else None)
    )

    # Display address: tender-package is canonical, fall back to property-info civic_address.
    display_address = (
        listed.display_address if listed else None
    ) or (info.civic_address if info else None)

    # Owner names: tender package has the formal list; award PDF has a flat string.
    if listed and listed.assessed_owners:
        owners = " & ".join(listed.assessed_owners)
    elif award and award.owner:
        owners = award.owner
    else:
        owners = None

    # Opening bid: prefer tender package, else award PDF header.
    opening_bid = None
    if listed is not None and listed.opening_bid is not None:
        opening_bid = listed.opening_bid
    elif award is not None:
        opening_bid = award.opening_bid

    # HST: tender package's bool, else award's
    hst = None
    if listed is not None:
        hst = listed.hst_applicable if listed.hst_applicable else None
    if hst is None and award is not None:
        hst = award.hst_applicable

    # Derived bid metrics
    winning_bid = award.winning_bid if award else None
    runner_up = award.runner_up_bid if award else None
    cushion = award.runner_up_cushion if award else None
    bidder_count = award.bidder_count if award else 0
    premium = (
        winning_bid / opening_bid
        if (winning_bid is not None and opening_bid not in (None, 0))
        else None
    )

    return {
        # Identity
        "year": year,
        "lot_number": lot_number,
        "sale_lot_id": f"MODL-{year}-{lot_number}",
        "tender_id": tender_id,
        "aan": aan,
        "pid": info.pid if info else None,
        # Listing (tender package)
        "display_address": display_address,
        "community": listed.community if listed else None,
        "lot_description": listed.lot_description if listed else None,
        "assessed_owners": owners,
        "opening_bid": opening_bid,
        "hst_applicable": hst,
        "redeemable_at_publication": listed.redeemable if listed else None,
        "tendered_at": tendered_at,
        # Property-info (legal counsel review)
        "title_system": info.title_system if info else None,
        "title_marketable": info.title_marketable if info else None,
        "road_access_class": info.road_access_class if info else None,
        "shore_privileges": info.shore_privileges if info else None,
        "deed_reference": info.deed_reference if info else None,
        "encumbrances_summary": info.encumbrances_summary if info else None,
        "encumbrance_items": [
            item.__dict__ for item in parse_encumbrances(info.encumbrances_summary if info else None)
        ],
        "survey_on_file": info.survey_on_file if info else None,
        "legal_review_date": info.legal_review_date if info else None,
        # Award outcome
        "outcome": outcome,
        "awarded_at": award.awarded_at if award else None,
        "winning_bid": winning_bid,
        "runner_up_bid": runner_up,
        "runner_up_cushion": cushion,
        "bidder_count": bidder_count,
        "premium_over_opening": premium,
        # Derived feature flags
        "has_structure": _has_structure(listed),
        "title_ok": _title_ok(info),
        "access_ok": _access_ok(info),
        "has_encumbrances": _has_encumbrances(info),
        # Provenance
        "has_listing_record": listed is not None,
        "has_award_record": award is not None,
        "has_property_info_record": info is not None,
    }


def load_year(
    year_dir: Path,
    *,
    property_info_backend: Optional[AutoBackend] = None,
    strict: bool = False,
) -> list[dict]:
    """Load every lot for one year, joining tender / award / property-info."""
    year = int(year_dir.name)
    backend = property_info_backend or AutoBackend()
    errors: list[str] = []

    # Tender package (optional - 2022/2023 may not have one)
    tender_metadata: Optional[TenderMetadata] = None
    listed_lots: dict[int, ListedLot] = {}
    tender_pdf = year_dir / "tender-package.pdf"
    if tender_pdf.exists():
        try:
            tender_metadata, lots = parse_tender(tender_pdf)
            listed_lots = {lot.lot_number: lot for lot in lots}
        except Exception as exc:
            errors.append(f"{tender_pdf}: tender parse failed: {exc}")

    # Awards (JSON fixtures from OCR)
    awards: dict[int, AwardRecord] = {}
    for jp in sorted(year_dir.glob("award-*.json")):
        try:
            r = load_award(jp)
            awards[r.lot_number] = r
        except Exception as exc:
            errors.append(f"{jp}: award JSON parse failed: {exc}")
    if strict:
        for pdf in sorted(year_dir.glob("award-*.pdf")):
            jp = pdf.with_suffix(".json")
            if not jp.exists():
                errors.append(f"{pdf}: missing hand-OCR award JSON fixture {jp.name}")

    # Property-info (text or JSON)
    infos: dict[int, PropertyInfo] = {}
    for pp in sorted(year_dir.glob("property-*.pdf")):
        if pp.stat().st_size < 2048:  # skip corrupted stubs
            continue
        try:
            info = backend.parse(pp)
            lot_num = int(pp.stem.split("-")[1])
            infos[lot_num] = info
        except Exception as exc:
            if _looks_like_award_form(pp):
                continue
            errors.append(f"{pp}: property-info parse failed: {exc}")

    if strict and errors:
        joined = "\n".join(f"  - {e}" for e in errors)
        raise RuntimeError(f"Failed to load {year_dir} in strict mode:\n{joined}")

    all_lots = sorted(set(listed_lots) | set(awards) | set(infos))
    records = []
    for lot_num in all_lots:
        records.append(_merge_lot(
            year=year,
            lot_number=lot_num,
            tender_metadata=tender_metadata,
            listed=listed_lots.get(lot_num),
            award=awards.get(lot_num),
            info=infos.get(lot_num),
        ))
    return records


def load_all_lots(
    probe_dir: Path = DEFAULT_PROBE_DIR,
    *,
    enrichment_csv: Optional[Path] = DEFAULT_ENRICHMENT_CSV,
    strict: bool = False,
) -> list[dict]:
    """Return every lot across every year as a list of merged dicts.

    Convert to a DataFrame with ``pd.DataFrame(load_all_lots())``.

    If ``enrichment_csv`` exists, PVSC-sourced assessed-value fields are
    joined per AAN. Pass ``None`` to disable enrichment. In ``strict`` mode,
    any parse failure or missing award JSON fixture raises instead of being
    treated as absent data.
    """
    backend = AutoBackend()
    records = []
    for year_dir in sorted(probe_dir.iterdir()):
        if not year_dir.is_dir():
            continue
        if not year_dir.name.isdigit():
            continue
        records.extend(load_year(year_dir, property_info_backend=backend, strict=strict))

    # Join PVSC enrichment by AAN where available
    enrichment: dict[str, EnrichmentRecord] = {}
    if enrichment_csv is not None:
        enrichment = load_enrichment_csv(enrichment_csv)
    for row in records:
        aan = row.get("aan")
        merge_into_lot(row, enrichment.get(aan) if aan else None)
    return records


def lots_missing_enrichment(
    records: list[dict],
    *,
    only_year: Optional[int] = None,
) -> list[dict]:
    """Return the subset of records that don't yet have a PVSC enrichment row.

    Useful for generating the lookup template — pass the result to
    ``sources.enrichment.write_template``.
    """
    return [
        r for r in records
        if not r.get("has_enrichment")
        and r.get("aan") is not None
        and (only_year is None or r.get("year") == only_year)
    ]


if __name__ == "__main__":
    records = load_all_lots()
    print(f"Loaded {len(records)} lot records.\n")
    # Quick provenance breakdown
    sources = {
        "listing only": 0, "award only": 0, "info only": 0,
        "listing+award": 0, "listing+info": 0, "award+info": 0,
        "all three": 0,
    }
    for r in records:
        l, a, p = r["has_listing_record"], r["has_award_record"], r["has_property_info_record"]
        key = (
            "all three" if l and a and p else
            "listing+award" if l and a else
            "listing+info" if l and p else
            "award+info" if a and p else
            "listing only" if l else
            "award only" if a else
            "info only" if p else "unknown"
        )
        sources[key] = sources.get(key, 0) + 1
    print("Provenance breakdown:")
    for k, v in sources.items():
        print(f"  {k:<16} {v:>4}")

    print("\nOutcome breakdown:")
    from collections import Counter
    for o, c in Counter(r["outcome"] for r in records).most_common():
        print(f"  {o:<12} {c:>4}")

    print("\nSample row (first sold lot with full provenance):")
    sample = next(r for r in records if r["outcome"] == "sold" and r["has_property_info_record"])
    for k, v in sample.items():
        v_str = str(v)
        if len(v_str) > 70:
            v_str = v_str[:67] + "..."
        print(f"  {k:<30} {v_str}")
