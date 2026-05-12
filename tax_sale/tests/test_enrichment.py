"""Tests for the PVSC manual-enrichment CSV loader and the dataset join."""
from __future__ import annotations

import csv
from pathlib import Path

import pytest

from tax_sale.sources.enrichment import (
    EnrichmentRecord,
    _to_float,
    _to_int,
    load_enrichment_csv,
    merge_into_lot,
    write_template,
)


# --- numeric parsing -------------------------------------------------------


def test_to_float_strips_dollar_and_commas():
    assert _to_float("$187,300") == 187300.0
    assert _to_float(" 1,024 ") == 1024.0
    assert _to_float("") is None
    assert _to_float("   ") is None


def test_to_int_rounds_floats_safely():
    assert _to_int("1971") == 1971
    assert _to_int("") is None


# --- load_enrichment_csv ---------------------------------------------------


def test_load_missing_file_returns_empty():
    assert load_enrichment_csv(Path("/no/such/path.csv")) == {}


def test_load_parses_basic_row(tmp_path):
    p = tmp_path / "pvsc.csv"
    p.write_text(
        "aan,assessed_value,assessed_land,year_built\n"
        "00017183,187300,42000,1971\n"
    )
    rows = load_enrichment_csv(p)
    assert "00017183" in rows
    r = rows["00017183"]
    assert r.assessed_value == 187300.0
    assert r.assessed_land == 42000.0
    assert r.year_built == 1971


def test_load_normalizes_aan_to_8_digits(tmp_path):
    """User might type AAN without leading zeros; loader should normalize."""
    p = tmp_path / "pvsc.csv"
    p.write_text("aan,assessed_value\n17183,187300\n")
    rows = load_enrichment_csv(p)
    assert "00017183" in rows
    assert "17183" not in rows


def test_load_tolerates_missing_columns(tmp_path):
    """Empty cells should map to None for optional fields."""
    p = tmp_path / "pvsc.csv"
    p.write_text(
        "aan,assessed_value,assessed_land\n"
        "00190705,18900,\n"
    )
    rows = load_enrichment_csv(p)
    r = rows["00190705"]
    assert r.assessed_value == 18900.0
    assert r.assessed_land is None


def test_load_skips_blank_aan_rows(tmp_path):
    p = tmp_path / "pvsc.csv"
    p.write_text("aan,assessed_value\n,12345\n00017183,99\n")
    rows = load_enrichment_csv(p)
    assert "00017183" in rows
    assert len(rows) == 1


def test_load_preserves_notes_and_source_date(tmp_path):
    p = tmp_path / "pvsc.csv"
    p.write_text(
        "aan,assessed_value,notes,source_date\n"
        "00017183,187300,mobile home,2026-05-12\n"
    )
    r = load_enrichment_csv(p)["00017183"]
    assert r.notes == "mobile home"
    assert r.source_date == "2026-05-12"


# --- merge_into_lot --------------------------------------------------------


def test_merge_with_none_sets_default_fields():
    lot = {"aan": "00017183", "opening_bid": 4493.31}
    merge_into_lot(lot, None)
    assert lot["assessed_value"] is None
    assert lot["has_enrichment"] is False


def test_merge_with_enrichment_populates_and_derives_ratio():
    lot = {"aan": "00017183", "opening_bid": 4493.31}
    enrichment = EnrichmentRecord(
        aan="00017183", assessed_value=187300.0,
        assessed_land=42000.0, assessed_improvements=145300.0,
        year_built=1971, lot_acres=1.8, structure_sqft=1024,
    )
    merge_into_lot(lot, enrichment)
    assert lot["assessed_value"] == 187300.0
    assert lot["assessed_improvements"] == 145300.0
    assert lot["year_built"] == 1971
    assert lot["has_enrichment"] is True
    # Derived ratio: opening_bid / assessed_value
    assert lot["opening_to_assessed_ratio"] == pytest.approx(4493.31 / 187300.0)


def test_merge_handles_zero_assessed_value():
    """Some PVSC lookups may have $0 assessed (vacant parcel issues). Don't div-by-zero."""
    lot = {"aan": "00017183", "opening_bid": 4493.31}
    enrichment = EnrichmentRecord(aan="00017183", assessed_value=0)
    merge_into_lot(lot, enrichment)
    assert lot["opening_to_assessed_ratio"] is None


# --- write_template --------------------------------------------------------


def test_write_template_includes_pre_filled_identity(tmp_path):
    path = tmp_path / "template.csv"
    write_template(path, [
        {"aan": "00017183", "lot_number": 2, "year": 2026,
         "display_address": "1189 NORTH RIVER RD",
         "community": "NORTH RIVER", "opening_bid": 4493.31},
    ])
    with path.open() as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 1
    assert rows[0]["aan"] == "00017183"
    assert rows[0]["lot_number"] == "2"
    assert rows[0]["display_address"] == "1189 NORTH RIVER RD"
    # Numeric fields the user fills in should be blank
    assert rows[0]["assessed_value"] == ""
    assert rows[0]["assessed_improvements"] == ""


# --- dataset.load_all_lots integration -------------------------------------


def test_dataset_picks_up_enrichment(tmp_path):
    """End-to-end: a CSV file passed to load_all_lots joins per AAN."""
    from tax_sale.dataset import load_all_lots

    # Build an enrichment CSV for one known lot
    csv_path = tmp_path / "pvsc.csv"
    csv_path.write_text(
        "aan,assessed_value,year_built\n"
        "00017183,187300,1971\n"
    )
    records = load_all_lots(enrichment_csv=csv_path)
    target = next(r for r in records if r["aan"] == "00017183")
    assert target["assessed_value"] == 187300.0
    assert target["year_built"] == 1971
    assert target["has_enrichment"] is True
    assert target["opening_to_assessed_ratio"] == pytest.approx(
        target["opening_bid"] / 187300.0
    )


def test_dataset_without_enrichment_still_works():
    """Passing None disables enrichment without breaking the loader."""
    from tax_sale.dataset import load_all_lots

    records = load_all_lots(enrichment_csv=None)
    assert len(records) > 0
    for r in records:
        assert r.get("has_enrichment") is False
