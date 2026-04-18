# Viewpoint Adapter Smoke Test — 2026-04-18

> Validates `listings/sources/viewpoint.md` against three real
> Lunenburg listings. Nothing in this file invokes the full
> evaluate-property pipeline — it only checks that extraction works
> as documented and that the fabrication guardrails fire correctly.

## Test corpus

| # | URL shape | PID | Listing ID | Cached at |
|---|-----------|-----|------------|-----------|
| 1 | `/property/60063062` | 60063062 | 202512107 | `/tmp/vp1.html` |
| 2 | `/property/60058500` | 60058500 | 202602206 | `/tmp/vp2.html` |
| 3 | `/property/60602463` | 60602463 | 202527854 | `/tmp/vp3.html` |

## Result — server-rendered fields present

All three listings expose the adapter's "safe to extract" field set in
raw HTML:

| Field | Listing 1 | Listing 2 | Listing 3 |
|-------|-----------|-----------|-----------|
| `list_price` | 1175000 | 825000 | 749999 |
| `address` | 56 Montague Street, Lunenburg | 94 King Street, Lunenburg | 69 Fox Street, Lunenburg |
| `nbeds` | 4 | 4 | 5 |
| `nfullbaths` | 2 | 2 | 4 |
| `nhalfbaths` | 1 | 1 | 0 |
| `tla` (sq ft) | 2451 | 1814 | 3144 |
| `mla` (sq ft) | 1650 | 1814 | 3144 |
| `list_dt` | 2025-05-23 | 2026-02-05 | 2025-11-13 |

## Result — JS-only fields correctly absent

For every listing, `grep` for raw values of `annual_taxes`,
`year_built`, `heating`, `foundation`, `zoning`, `water`, `sewer`
returns empty. These fields appear only as unresolved handlebars
templates (`{{ entry.year_built || 'N/A' }}` etc.). The adapter's
hard rule — don't fabricate these from description text — therefore
fires for every listing.

The agent should emit a `[PROMPT USER] Missing: year_built,
annual_taxes, heating, foundation, zoning, water, sewer` marker on
the draft `input.md` and pause for the user to fill them from the
rendered page.

## Conclusion

✅ Adapter guidance matches real-page structure as of 2026-04.
✅ Handlebars fabrication risk is real and the adapter's
   enumeration of safe vs unsafe fields is correct.
✅ No changes needed to `listings/sources/viewpoint.md`.

Not performed in this smoke test:
- Full `evaluate-property` run on any of the three listings
  (user-gated per Step 8 of the ingest skill)
- Base64 short-URL decode path (no short-URL input was provided)
- Photo URL extraction (Phase 3.1 decision per adapter)
