"""Generate anonymized copies of award + property-info JSON fixtures.

Why:
    Hand-OCR'd JSONs contain real bidder/owner names transcribed from MODL's
    publicly-posted PDFs. Republishing them in a searchable public repo is a
    different privacy posture than MODL's per-property disclosure (§13.8 of
    the spec). This script produces ``*.anonymized.json`` copies where:

      - ``bidder_label`` → deterministic salted hash like ``BIDDER_a3f72b91``
      - ``owner`` → ``OWNER_<hash>``
      - ``name_on_record`` → ``OWNER_<hash>``

    Same name always maps to the same hash, so repeat-bidder analysis still
    works on the anonymized data. Public officials in ``attendees`` are
    left intact — they're on-the-record municipal staff doing their jobs.

Usage:
    python3 tax_sale/scripts/anonymize_fixtures.py
    python3 tax_sale/scripts/anonymize_fixtures.py --dry-run   # report only

Output:
    For each ``award-NNN.json`` / ``property-NNN.json``, writes a sibling
    ``award-NNN.anonymized.json`` / ``property-NNN.anonymized.json``.
    Originals are untouched.

The anonymized files are still gitignored by the default ``data/`` rule.
Promote them to a committable directory (e.g. ``tax_sale/fixtures/``) when
ready to share, after a manual spot-check that no PII leaked through.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Optional

# A stable, well-known salt prevents two different anonymizers from producing
# different hashes for the same name (useful if multiple people run this).
# It does NOT defend against a targeted attacker who knows a small candidate
# set of names — that's a real limitation; treat the output as "minimization
# for public posting", not anonymization in the formal-privacy sense.
SALT = "modl-tax-sale-v1"

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROBE_DIR = REPO_ROOT / "data" / "probe" / "modl"


def hash_name(name: Optional[str], *, prefix: str = "BIDDER") -> Optional[str]:
    """Return a stable short-hash label, or None for falsy input."""
    if not name:
        return None
    normalized = name.strip().lower()
    if not normalized:
        return None
    digest = hashlib.sha256((SALT + ":" + normalized).encode("utf-8")).hexdigest()
    return f"{prefix}_{digest[:8]}"


def anonymize_award(data: dict) -> dict:
    """Mutate a parsed award JSON in place; return it for chaining."""
    if data.get("owner"):
        data["owner"] = hash_name(data["owner"], prefix="OWNER")
    for bid in data.get("bids", []):
        if bid.get("bidder_label"):
            bid["bidder_label"] = hash_name(bid["bidder_label"], prefix="BIDDER")
    return data


def anonymize_property(data: dict) -> dict:
    if data.get("name_on_record"):
        data["name_on_record"] = hash_name(data["name_on_record"], prefix="OWNER")
    return data


def _is_already_anonymized(path: Path) -> bool:
    return ".anonymized" in path.name


def process_dir(probe_dir: Path, *, dry_run: bool = False) -> dict:
    awards = 0
    properties = 0
    skipped = 0
    for path in sorted(probe_dir.glob("*/award-*.json")):
        if _is_already_anonymized(path):
            skipped += 1
            continue
        out_path = path.with_name(path.stem + ".anonymized.json")
        if dry_run:
            print(f"DRY  {path.relative_to(probe_dir)}  ->  {out_path.name}")
        else:
            data = anonymize_award(json.loads(path.read_text()))
            out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        awards += 1
    for path in sorted(probe_dir.glob("*/property-*.json")):
        if _is_already_anonymized(path):
            skipped += 1
            continue
        out_path = path.with_name(path.stem + ".anonymized.json")
        if dry_run:
            print(f"DRY  {path.relative_to(probe_dir)}  ->  {out_path.name}")
        else:
            data = anonymize_property(json.loads(path.read_text()))
            out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        properties += 1
    return {"awards": awards, "properties": properties, "skipped": skipped}


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--probe-dir", type=Path, default=DEFAULT_PROBE_DIR,
        help=f"Directory containing year/award-*.json files (default: {DEFAULT_PROBE_DIR})",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Don't write files; report what would happen",
    )
    args = parser.parse_args(argv)

    if not args.probe_dir.exists():
        print(f"No probe dir at {args.probe_dir}", file=sys.stderr)
        return 1

    stats = process_dir(args.probe_dir, dry_run=args.dry_run)
    label = "Would anonymize" if args.dry_run else "Anonymized"
    print(
        f"{label} {stats['awards']} award fixture(s) and "
        f"{stats['properties']} property fixture(s) "
        f"(skipped {stats['skipped']} already-anonymized)."
    )
    if not args.dry_run:
        print(
            "Output: *.anonymized.json alongside each source. "
            "Spot-check a few before promoting to a committable directory."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
