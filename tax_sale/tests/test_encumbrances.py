"""Tests for structuring encumbrance summaries."""
from __future__ import annotations

from tax_sale.parse.encumbrances import parse_encumbrances


def test_none_summary_has_no_items():
    assert parse_encumbrances("None.") == []


def test_mortgage_amount_is_extracted():
    items = parse_encumbrances("1) Mortgage in favour of CIBC face amount $161,280.00")
    assert len(items) == 1
    assert items[0].kind == "mortgage"
    assert items[0].amount == 161_280.00


def test_judgment_kind_is_extracted():
    items = parse_encumbrances("CRA judgment registered for $12,345.67")
    assert items[0].kind == "tax_judgment"
    assert items[0].amount == 12_345.67
