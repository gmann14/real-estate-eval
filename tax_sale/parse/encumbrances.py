"""Lightweight structure for legal-review encumbrance strings.

The lawyer's property-info letter gives useful lien/mortgage text, but v1
cannot safely treat all encumbrances as one binary flag. This parser extracts
coarse categories and dollar amounts while preserving the raw text for manual
review.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class EncumbranceItem:
    kind: str
    amount: Optional[float]
    raw: str


_MONEY_RE = re.compile(r"\$\s*([0-9][0-9,]*(?:\.\d{2})?)")


def _kind(raw: str) -> str:
    lowered = raw.lower()
    if "mortgage" in lowered:
        return "mortgage"
    if "cra" in lowered or "canada revenue" in lowered:
        return "tax_judgment"
    if "judgment" in lowered or "judgement" in lowered:
        return "judgment"
    if "lien" in lowered:
        return "lien"
    return "other"


def _amount(raw: str) -> Optional[float]:
    match = _MONEY_RE.search(raw)
    if not match:
        return None
    return float(match.group(1).replace(",", ""))


def parse_encumbrances(summary: Optional[str]) -> list[EncumbranceItem]:
    """Parse a legal-review encumbrance summary into coarse review items."""
    if summary is None:
        return []
    text = summary.strip()
    if not text or text.lower().startswith("none"):
        return []
    parts = [
        p.strip(" .;")
        for p in re.split(r"(?:\n+|;\s+|\s+\d+\)\s+)", text)
        if p.strip(" .;")
    ]
    if not parts:
        parts = [text]
    return [EncumbranceItem(kind=_kind(part), amount=_amount(part), raw=part) for part in parts]
