# tax_sale — MODL tax-sale bid-decision toolkit

Personal-use decision-support for the Municipality of the District of Lunenburg
(MODL) sealed-tender tax sale. Given the historical record and the current-year
tender package, produces a per-lot bid sheet with comp set, risk flags, and
historical bid-exceedance scenarios. It is not a valuation engine; you still
need to set a private ceiling from PVSC/manual appraisal and diligence.

📖 **For the 2027 sale, follow [RUNBOOK-2027.md](RUNBOOK-2027.md) step-by-step.**
📖 **For PVSC assessed-value enrichment, follow [PVSC-LOOKUP-GUIDE.md](PVSC-LOOKUP-GUIDE.md).**

Design spec: [`docs/specs/tax-sale-bid-predictor.md`](../docs/specs/tax-sale-bid-predictor.md).

## What it does

For each lot in a tax-sale year:

1. Joins three data sources: tender-package listings, per-lot legal-counsel
   property-info reports, and (for historical lots) award PDFs.
2. Finds the 5 nearest historical comps using a weighted similarity score
   over title-marketability, road access, opening-bid range, structure
   presence, and shore privileges.
3. Computes a historical-exceedance curve: "a bid at $X would have cleared
   N of M comparable historical auctions."
4. Surfaces obvious mechanical risk flags: REDEEMABLE, HST, no access,
   unmarketable title, encumbrances, no survey on file.
5. Reports an honest **naive bidder-count baseline** for field strength
   (the comp-based version failed its rolling-origin backtest; see
   §8.1 in the spec).
6. Optionally renders decision scenarios (opportunistic / serious /
   must-win) against a user-supplied private ceiling.

## Prerequisites

- Python 3.9+
- `poppler` tools on PATH (`pdftotext`, `pdfimages`, `pdfinfo`) for the
  text-extractable PDFs. On macOS: `brew install poppler`.
- `pytest` for the test suite (`pip install pytest`).
- An `Read`-style multimodal vision capability for scanned-image PDF OCR.
  Today this is handled out-of-band by spawning Claude Code agents that
  read each PDF and emit a JSON fixture; see the OCR section below.

## Quick start

```bash
# From the repo root
python3 -m pytest tax_sale/tests/                             # 146 tests
python3 -m tax_sale stats --strict                            # dataset summary, fail on parser/OCR gaps
python3 -m tax_sale bidsheet --year 2026 --lot 2 --ceiling 45000 --strict
python3 -m tax_sale bidsheet-all --year 2026 --out-dir /tmp/bs --strict
python3 -m tax_sale backtest --strict                         # §8.1 + §8.3
```

## CLI reference

### `stats`

```
python3 -m tax_sale stats [--strict]
```

Prints the dataset summary: total records, outcome breakdown, sold lots per
year, provenance (which lots have which sources), total submitted bids. Use
`--strict` for live-year work so parser failures and missing OCR fixtures stop
the run instead of silently dropping records.

### `bidsheet`

```
python3 -m tax_sale bidsheet --year YEAR --lot LOT [--ceiling DOLLARS] [--strict]
```

Render the §11 markdown bid sheet for one target lot. Without `--ceiling`,
the decision-scenario block is omitted.

### `bidsheet-all`

```
python3 -m tax_sale bidsheet-all --year YEAR [--ceiling DOLLARS] [--out-dir DIR] [--strict]
```

Render bid sheets for every lot in a year. If `--out-dir` is set, writes
one `lot-NNN.md` file per lot; otherwise prints all sheets to stdout
separated by `---`.

### `backtest`

```
python3 -m tax_sale backtest [--kind field-strength|exceedance|both] [--strict]
```

Run the §8 rolling-origin backtests. `field-strength` compares comp-based
median/mean/trimmed-mean predictors against naive prior-year baselines.
`exceedance` checks whether the opening-bid-normalized historical-exceedance
curve is directionally calibrated. Current results are useful but not tight
enough to treat per-lot lines as live win probabilities.

## The live 2027 workflow

The pipeline expects the MODL tax-sale page for each year to be downloaded
into `data/probe/modl/{year}/`. Steps when the 2027 list drops:

1. **Locate the year's page URL.** MODL's URL slugs change year-to-year
   (`tax-sales-25.html`, `2023-tax-sale.html`, etc). One-time add to
   `data/probe/modl/_download.sh`.
2. **Download the package.** `bash data/probe/modl/_download.sh` —
   pulls the tender package PDF, the bid submission form, the per-lot
   property-info PDFs, and (post-tender) the per-lot award PDFs.
3. **OCR scanned PDFs.** Text-extractable property-info docs work
   directly; scanned ones need a JSON fixture written by hand or by
   Claude Code agents. See the OCR section.
4. **Sanity-check the parse.** `python3 -m tax_sale stats --strict` —
   confirms the new year shows up and fails on parser/OCR gaps.
5. **Generate bid sheets.** `python3 -m tax_sale bidsheet-all --year 2027
   --ceiling 50000 --out-dir bidsheets/2027/ --strict`.
6. **Read, drive, shortlist.** Visit lots that pass diligence; revise
   private ceilings; re-run `bidsheet --lot N --ceiling X` per lot.
7. **Submit tenders.** Manually fill the MODL bid form per lot. Tool
   does not auto-submit.

## Data architecture

```
data/probe/modl/{year}/
├── _page.html                                # archived MODL page
├── tender-package.pdf                        # text PDF, listings + terms
├── bid-form.pdf                              # blank bidder form (one-time)
├── property-{NNN}.pdf                        # per-lot legal-counsel report
├── property-{NNN}.json                       # hand-OCR'd JSON (scan-only fixtures)
├── award-{NNN}.pdf                           # per-lot bid record (post-tender)
└── award-{NNN}.json                          # hand-OCR'd JSON (all of them)
```

| Year | Awards | Property-info | Text-extractable rate (page 1) |
|---|---:|---:|---:|
| 2021 | 20 | 0 | n/a (MODL didn't publish property-info docs in 2021) |
| 2022 | 24 | 24 | 29% |
| 2023 | 8 | 8 | 37% |
| 2024 | 15 | 15 | **0%** (all scanned) |
| 2025 | 13 | 14 | 93% |
| 2026 | 12 | 12 | 100% |

## Module map

| File | Role |
|---|---|
| `parse/tender_package.py` | Parse the text-PDF tender package → per-lot `ListedLot` |
| `parse/property_info.py` | `AutoBackend` — text extraction when possible, JSON fallback otherwise |
| `parse/award_pdf.py` | `AwardRecord` + `BidRecord` schema with strict validation; OCR is a pluggable backend (production via JSON fixtures; vision-API integration is on the roadmap) |
| `parse/encumbrances.py` | Coarse structure for mortgage/judgment/lien strings while preserving raw legal text |
| `dataset.py` | Join layer: tender + award + property-info → unified row per `(year, lot)` |
| `model/comp.py` | Weighted similarity score, comp set retrieval, historical exceedance |
| `model/field_strength.py` | Bidder-count estimators (median / mean / trimmed_mean) |
| `model/validation.py` | Rolling-origin backtests for §8.1 (field strength) and §8.3 (exceedance) |
| `model/bidsheet.py` | §11 markdown renderer with risk gate, comp table, and normalized historical-exceedance scenarios |
| `cli.py` + `__main__.py` | argparse subcommands |

## OCR for scanned PDFs

Scanned-image award PDFs and pre-2025 property-info docs are not
text-extractable. We solved this by spawning Claude Code subagents to
read each PDF visually and emit a JSON fixture alongside it (e.g.
`award-002.json` next to `award-002.pdf`). The `AutoBackend` for
property-info checks for text first, then falls back to JSON. The
`award_pdf` module always loads from JSON.

For 2027 the user has three options:

1. **Repeat the agent-OCR workflow.** Open a Claude Code session in this
   repo, paste each scan-only PDF path to a fresh agent, and ask it to
   transcribe to the documented JSON schema. ~10-30 minutes for a 22-lot
   year.
2. **Wire the Anthropic Vision API.** The `OCRBackend` protocol in
   `parse/award_pdf.py` is set up for this — add a
   `parse/anthropic_ocr.py` that sends each PDF to Claude vision with a
   strict JSON-output prompt. Estimated cost: $1-2 for a full year's
   PDFs. Documented as a future task; not built.
3. **Hand-transcribe.** Open each PDF, write the JSON. Viable at this
   scale (60-100 PDFs total) for someone with a Saturday.

## Calibration findings

Both backtests are run in `model/validation.py`. The headline:

- **§8.1 field strength (bidder count):** the comp-based predictor now has
  lower MAE on the lots it can score, but it covers fewer lots and remains
  positively biased. The bidsheet keeps the naive prior-year bidder-count
  baseline as primary because it has broader coverage and lower bias; the
  comp-set count is shown as exploratory.
- **§8.3 historical exceedance:** opening-bid-normalized exceedance is
  directionally useful but not calibrated tightly enough to call live win
  probability. The 2021-2026 rolling-origin backtest has N=37 held-out sold
  lots; median and upper-percentile lines are conservative by double-digit
  percentage points. The bidsheet uses count/exceedance language, not
  probability promises.

Interpretation: the comp matcher is useful for finding relevant historical
auction outcomes, but the sample is still small. Treat output as a disciplined
bid worksheet, not a model that knows the 2027 bidder field.

## What's NOT in the pipeline

- **PVSC dollar-value assessments.** The unified dataset includes opening
  bid (taxes + interest + expenses) and PID (parcel join key), but not
  the official PVSC assessed value. Manual lookup at
  [pvsc.ca](https://www.pvsc.ca) per lot is the v1 workaround;
  cross-referencing ViewPoint.ca listings is the next-cheapest
  automation path.
- **NS Property Online (POL) parcel polygons.** POL is paid; we use it
  manually for shortlisted lots only. See spec §3.
- **Bid-distribution model (§8.2).** Every individual bid is stored in
  `sale_lot_bids` with status, but we don't yet model the conditional
  distribution. Spec calls for normalization by opening-bid before
  aggregating across comps.
- **Other municipalities.** Adapter pattern in place but only MODL
  implemented. Adding Chester / Queens / HRM requires per-municipality
  page-URL discovery and template-difference handling.
- **Auto-submission.** Spec explicitly excludes this.
