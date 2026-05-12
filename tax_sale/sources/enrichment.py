"""Manual-enrichment CSV loader.

PVSC search is gated behind reCAPTCHA v3 and ViewPoint is a JS-only SPA,
so fully-automated enrichment of historic + live lots isn't viable. The
user does ~22 lookups in a real browser (reCAPTCHA passes for legit
sessions) and pastes the numbers into a CSV — this module joins that
CSV into the unified dataset.

CSV format (one row per AAN, header required):

    aan,assessed_value,assessed_land,assessed_improvements,year_built,lot_acres,structure_sqft,notes
    00017183,187300,42000,145300,1971,1.8,1024,"mobile home + outbuilding"
    00190705,18900,18900,0,,5.4,,"vacant land"
    ...

Empty cells are allowed for any column except ``aan``. Numeric cells
parse as floats. The ``year_built`` and ``lot_acres`` columns are
optional structural enrichment that becomes useful for §7 comp scoring.

This file is gitignored by default (see spec §3 — personal-use PVSC
data shouldn't be republished).
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class EnrichmentRecord:
    aan: str
    assessed_value: Optional[float] = None
    assessed_land: Optional[float] = None
    assessed_improvements: Optional[float] = None
    year_built: Optional[int] = None
    lot_acres: Optional[float] = None
    structure_sqft: Optional[int] = None
    notes: Optional[str] = None
    source: str = "manual_pvsc"
    source_date: Optional[str] = None


def _to_float(s: str) -> Optional[float]:
    s = s.strip()
    if not s:
        return None
    return float(s.replace(",", "").replace("$", ""))


def _to_int(s: str) -> Optional[int]:
    f = _to_float(s)
    return int(f) if f is not None else None


def load_enrichment_csv(path: Path) -> dict[str, EnrichmentRecord]:
    """Return ``{aan -> EnrichmentRecord}``. Missing file yields an empty dict.

    Empty / blank lines are skipped. AANs are normalised to 8-digit
    zero-padded strings to match MODL listings.
    """
    if not path.exists():
        return {}
    out: dict[str, EnrichmentRecord] = {}
    with path.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            aan = (row.get("aan") or "").strip()
            if not aan:
                continue
            # Normalize AAN to 8-digit zero-padded form to match MODL listings.
            aan = aan.zfill(8)
            out[aan] = EnrichmentRecord(
                aan=aan,
                assessed_value=_to_float(row.get("assessed_value", "")),
                assessed_land=_to_float(row.get("assessed_land", "")),
                assessed_improvements=_to_float(row.get("assessed_improvements", "")),
                year_built=_to_int(row.get("year_built", "")),
                lot_acres=_to_float(row.get("lot_acres", "")),
                structure_sqft=_to_int(row.get("structure_sqft", "")),
                notes=(row.get("notes") or "").strip() or None,
                source_date=(row.get("source_date") or "").strip() or None,
            )
    return out


def write_template(path: Path, lots_needing_lookup: list[dict]) -> None:
    """Write a CSV pre-filled with the AANs that need lookup.

    Each row gets the AAN + address + community pre-populated so the user
    can identify the lot quickly in their browser. Numeric fields are
    left blank for the user to fill from PVSC.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "aan", "lot_number", "year", "display_address", "community",
            "opening_bid",
            # User fills these from PVSC:
            "assessed_value", "assessed_land", "assessed_improvements",
            "year_built", "lot_acres", "structure_sqft",
            "notes", "source_date",
        ])
        for lot in lots_needing_lookup:
            writer.writerow([
                lot.get("aan", ""),
                lot.get("lot_number", ""),
                lot.get("year", ""),
                lot.get("display_address", ""),
                lot.get("community", ""),
                lot.get("opening_bid", ""),
                "", "", "", "", "", "", "", "",
            ])


def merge_into_lot(lot_row: dict, enrichment: Optional[EnrichmentRecord]) -> dict:
    """Augment a dataset row with enrichment fields. Returns the row mutated in place."""
    if enrichment is None:
        lot_row.setdefault("assessed_value", None)
        lot_row.setdefault("assessed_land", None)
        lot_row.setdefault("assessed_improvements", None)
        lot_row.setdefault("year_built", None)
        lot_row.setdefault("lot_acres", None)
        lot_row.setdefault("structure_sqft", None)
        lot_row.setdefault("has_enrichment", False)
        return lot_row
    lot_row["assessed_value"] = enrichment.assessed_value
    lot_row["assessed_land"] = enrichment.assessed_land
    lot_row["assessed_improvements"] = enrichment.assessed_improvements
    lot_row["year_built"] = enrichment.year_built
    lot_row["lot_acres"] = enrichment.lot_acres
    lot_row["structure_sqft"] = enrichment.structure_sqft
    lot_row["has_enrichment"] = True
    # Derived: opening-bid-to-assessed ratio is a useful comp-scoring signal
    if (
        lot_row.get("opening_bid") is not None
        and enrichment.assessed_value not in (None, 0)
    ):
        lot_row["opening_to_assessed_ratio"] = lot_row["opening_bid"] / enrichment.assessed_value
    else:
        lot_row["opening_to_assessed_ratio"] = None
    return lot_row
