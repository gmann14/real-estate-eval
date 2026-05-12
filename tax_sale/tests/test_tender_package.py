"""Tests for the MODL tender-package parser.

Fixtures live at ``data/probe/modl/{year}/tender-package.pdf`` — the live
PDFs scraped during the Phase 2a probe. If a fixture is missing the test
is skipped rather than failing, so the package can be cloned without the
data archive.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from tax_sale.parse import tender_package as tp

REPO_ROOT = Path(__file__).resolve().parents[2]
PROBE_DIR = REPO_ROOT / "data" / "probe" / "modl"


def _fixture(year: int) -> Path:
    path = PROBE_DIR / str(year) / "tender-package.pdf"
    if not path.exists():
        pytest.skip(f"Fixture not present: {path}")
    return path


def test_parse_2026_tender_metadata():
    metadata, _ = tp.parse_pdf(_fixture(2026))
    assert metadata.tender_id == "2025-01-004"
    assert metadata.tender_opening == "Monday, March 2, 2026"


def test_parse_2026_lots_count():
    _, lots = tp.parse_pdf(_fixture(2026))
    # 2026 published 22 lots total (including ones later redeemed pre-deadline).
    assert len(lots) == 22


def test_parse_2026_first_lot_fields():
    _, lots = tp.parse_pdf(_fixture(2026))
    lot = lots[0]
    assert lot.lot_number == 2
    assert lot.aan == "00017183"
    assert lot.display_address == "1189 NORTH RIVER RD"
    assert lot.community == "NORTH RIVER"
    assert lot.lot_description == "1971 48X12"
    assert lot.redeemable is True
    assert lot.hst_applicable is False
    assert lot.assessed_owners == ["SABEAN BRITTANY LEANNE"]
    assert lot.opening_bid == pytest.approx(4493.31)


def test_parse_2026_handles_trailing_period_status():
    """Lot 5 had 'REDEEMABLE.' (with trailing period) — must still flag."""
    _, lots = tp.parse_pdf(_fixture(2026))
    lot = next(l for l in lots if l.lot_number == 5)
    assert lot.redeemable is True


def test_parse_2026_handles_hst_flag():
    _, lots = tp.parse_pdf(_fixture(2026))
    lot = next(l for l in lots if l.lot_number == 3)
    assert lot.hst_applicable is True
    assert lot.redeemable is True


def test_parse_2025_tender_metadata():
    metadata, _ = tp.parse_pdf(_fixture(2025))
    assert metadata.tender_id == "2024-01-001"
    assert metadata.tender_opening == "Monday, March 3, 2025"


def test_parse_2025_joint_owners_multiline():
    """Lot 3 in 2025 has joint owners across two lines with '& ' continuation."""
    _, lots = tp.parse_pdf(_fixture(2025))
    lot = next(l for l in lots if l.lot_number == 3)
    assert lot.assessed_owners == ["SMITH MAXINE ALICE", "SMITH JAMES ALBERT"]


def test_parse_2025_joint_owners_inline():
    """Lot 101 in 2025 has joint owners on a single comma-separated line."""
    _, lots = tp.parse_pdf(_fixture(2025))
    lot = next(l for l in lots if l.lot_number == 101)
    assert lot.assessed_owners == ["ARMSTRONG JASMINE & ARMSTRONG JASON"]


def test_parse_returns_in_lot_number_order():
    """Lots should be ordered by ascending lot number (matches PDF order)."""
    _, lots = tp.parse_pdf(_fixture(2026))
    nums = [l.lot_number for l in lots]
    assert nums == sorted(nums)
