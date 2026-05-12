# 2027 MODL Tax Sale Runbook

> **Read this first when MODL posts the 2027 list.** Every step has the
> exact command. No reading the spec required.

Estimated total time: **~3 hours** spread over 2–3 weeks (the tender window).

---

## Timeline overview

| When | What |
|---|---|
| Sale list drops (late Jan / early Feb 2027) | Steps 1–4 below: scrape + parse + enrich |
| First weekend after list drops | Step 5: generate bidsheets for every lot |
| Following weekend | Step 6: shortlist + drive-by lots that look interesting |
| Final week before deadline | Step 7: set per-lot ceilings + submit tenders |
| Deadline day | Step 8: wait for awards to be posted, then archive |

---

## STEP 1 — Find the 2027 MODL page URL

MODL changes its URL slug every year. Look it up in their sidebar:

1. Open `https://www.modl.ca/2026-tax-sales.html` in a browser
2. Click "2027 Tax Sale Awards" in the left sidebar (or "2027 Tax Sales" if the awards haven't been posted yet)
3. Copy the URL — it'll be something like `https://www.modl.ca/2027-tax-sales.html` or `https://www.modl.ca/tax-sales-27.html`

---

## STEP 2 — Add 2027 to the download script

Edit `data/probe/modl/_download.sh` and add the new year:

```bash
# Inside _download.sh, near the year loop:
for y in 2027 2026 2025 2024 2023 2022 2021; do
  download_year "$y"
done
```

Then cache the page and run the downloader:

```bash
cd data/probe/modl
mkdir -p 2027
curl -sSL -o 2027/_page.html "https://www.modl.ca/THE-URL-FROM-STEP-1"
bash _download.sh
```

You should now have:
```
data/probe/modl/2027/
├── _page.html
├── tender-package.pdf
├── bid-form.pdf
├── faqs.pdf
├── property-NNN.pdf       (one per lot ≈ 20–25 files)
└── (no award files yet — awards are posted AFTER the tender closes)
```

---

## STEP 3 — Verify the tender package parses

```bash
python3 -m tax_sale.parse.tender_package data/probe/modl/2027/tender-package.pdf
```

You should see one block per listed lot with: lot #, AAN, opening bid,
owner, HST flag, redeemable status. If anything is missing, the MODL
template changed — check the parser's regexes in `parse/tender_package.py`.

---

## STEP 4 — OCR scan-only property-info docs

MODL's property-info PDFs are sometimes text-extractable (cleanly parsed by
`AutoBackend`) and sometimes scanned images that need visual OCR. Check
which is which:

```bash
for f in data/probe/modl/2027/property-*.pdf; do
  chars=$(pdftotext -f 1 -l 1 "$f" - 2>/dev/null | wc -c)
  if [[ "$chars" -lt 200 ]]; then echo "SCAN-ONLY: $f"; fi
done
```

For each scan-only PDF, you need a hand-OCR'd JSON fixture alongside it.
**Two options:**

### Option A — Spawn Claude Code agents (recommended)

Open a Claude Code session in this repo and run:

> "OCR the page 1 of each scan-only property-info PDF for 2027 and write JSON fixtures alongside them, matching the schema in tax_sale/parse/property_info.py. Reference fixture: data/probe/modl/2026/property-002.json. Skip pages 2+. Process serially, validate each with `python3 -c \"from pathlib import Path; from tax_sale.parse.property_info import from_json_file; print(from_json_file(Path('PATH')).pid)\"`."

This is exactly the workflow used to OCR 37 PDFs during the historical
dataset build (see git history for the pattern).

### Option B — Hand-transcribe

Open each scan PDF in Preview. For each, write
`property-NNN.json` matching the schema. Fields needed:
`tax_sale_no`, `aan`, `pid`, `civic_address`, `title_system`,
`title_marketable`, `road_access_class`, `shore_privileges`,
`deed_reference`, `encumbrances_summary`, `survey_on_file`.

Use 2026/property-002.json or 2025/property-003.json as the template.

### Verify

```bash
python3 -m tax_sale stats --strict
```

Should show 2027 in the per-year breakdown with lot counts matching the
MODL tender package.

---

## STEP 5 — Generate the bidsheets

```bash
python3 -m tax_sale bidsheet-all --year 2027 --out-dir bidsheets/2027/ --strict
```

This writes one markdown file per lot (e.g. `lot-002.md`, `lot-013.md`).
Each file contains a comp-based bid worksheet. It does not replace PVSC/manual
valuation or drive-by diligence.

### What the bidsheet tells you

Open `bidsheets/2027/lot-NNN.md` and scroll down. Every lot has four
sections:

1. **Property summary** — what the lot is (lot description, address, title system, access class).
2. **⚠ Risk flags** — REDEEMABLE, HST, no access, unmarketable title, encumbrances, no survey. Read these first; they tell you what could go wrong.
3. **Top 5 historical comps** — the 5 most similar prior-year sold lots, ranked by weighted similarity, with their winning bids.
4. **Winning-bid estimate** — two descriptive anchors:
    - **"Most likely winning bid"** = median of comp winning bids
    - **"Bid -> historical raw-dollar exceedance" table** — for each row, the bid amount that would have cleared that share of the displayed comps. This is descriptive, not a live win probability.
5. **👥 Field-strength estimate** — how many bidders to expect (point estimate + P25-P75 range + no-bid probability).

### Example annotated output

```
## 🎯 Winning-bid prediction

**Most likely winning bid:** $52,000 (comp median across 5 comparable historical auctions)
**Range:** $22,990 – $221,112

**Bid -> historical raw-dollar exceedance** (descriptive):

| Your bid would need to be... | ...to historically win this fraction |
|------------------------------|----------------------------------|
| $22,990                      | 10% of comparable auctions       |
| $31,500                      | 25% of comparable auctions       |
| $52,000                      | 50% of comparable auctions       |  ← median-bid line
| $90,000                      | 75% of comparable auctions       |
| $221,112                     | 90% of comparable auctions       |
```

Reading it: **$52,000** is the median displayed comp winner, not a guaranteed
50% live win chance. Use it as a reference point after setting your private
ceiling from valuation and diligence.

---

## STEP 6 — Shortlist + drive-by

Read all 22 bidsheets. Note the ~5–10 with characteristics you'd
actually want to own. For each shortlist lot:

- Open Google Maps / Street View and look at the property
- Drive by if possible (rural Lunenburg lots benefit from this hugely)
- Check the access situation in person (especially for lots flagged
  with "EASEMENT/ROW" or "NO ACCESS" — the lawyer's opinion is
  cautious; reality is sometimes worse, sometimes better)
- If the property is improved, look for occupancy signs / condition
  problems

Stop visiting any lot that fails diligence — even if the comp set
suggested it was a good deal.

---

## STEP 7 — Enrich with PVSC (optional but improves accuracy)

📖 **Follow [PVSC-LOOKUP-GUIDE.md](PVSC-LOOKUP-GUIDE.md) — it has the
full step-by-step.** Quick version:

```bash
python3 -m tax_sale enrichment-template --year 2027 \
  --out data/enrichment/pvsc-2027.csv
```

Then look up each AAN at <https://www.pvsc.ca/find-assessment> in your
browser, paste the numbers into the CSV, save, and verify:

```bash
python3 -m tax_sale stats --strict   # has_enrichment count should match #lots looked up
```

PVSC's public search is gated by reCAPTCHA so this step is manual —
~30 minutes for a typical 20-lot year. See the guide for handling
multi-parcel lots, vacant land, AAN-not-found, and other gotchas.

---

## STEP 8 — Set per-lot ceilings + render final bidsheets

For each shortlist lot, decide your private maximum bid (the amount
beyond which you'd rather lose). This is YOUR call, not the model's —
it depends on your investment thesis, holding cost, expected
exit value, risk tolerance.

Then render with the ceiling:

```bash
python3 -m tax_sale bidsheet --year 2027 --lot 17 --ceiling 38000 --strict
```

This adds a **Decision scenarios** section when there are at least 10 usable
opening-bid-normalized sold comps:
- Opportunistic: smallest bid that clears the low scenario threshold
- Serious: middle scenario threshold, capped at your ceiling
- Must-win: upper scenario threshold, capped at your ceiling

If a scenario is marked `[CEILING-LIMITED]`, the comp-derived bid would
have exceeded your ceiling. You either raise the ceiling (revisit your
investment thesis) or accept a lower historical exceedance count.

---

## STEP 9 — Submit tenders

This is manual. For each lot you decide to bid on:

1. Print MODL's bid submission form (`bid-form.pdf`).
2. Fill in: your name, address, telephone, AAN, lot number, bid amount,
   tenure type.
3. Get a bank draft / certified cheque equal to the **minimum opening
   bid** for that lot (this is the deposit, not your bid).
4. Seal in an envelope marked
   `Municipality of The District of Lunenburg Tax Sale Property, Tender # 2026-01-XXX`.
5. Mail or hand-deliver to:
   Municipality of the District of Lunenburg, 10 Allee Champlain Drive,
   Cookville NS, B4V 9E4 — **by 10:00 a.m. on the tender date**.

---

## STEP 10 — After the tender closes

MODL posts the award PDFs a few days later. To archive them:

```bash
# Add 2027 award URLs to _download.sh (they'll be linked from the same page)
bash data/probe/modl/_download.sh
```

Then OCR them via the same agent flow as step 4 (or hand-transcribe).
Once done:

```bash
python3 -m tax_sale stats         # 2027 sold lots show up
python3 -m tax_sale backtest      # rolling-origin runs now include 2027
```

The 2027 data feeds into the 2028 backtest. Compound learning.

---

## Troubleshooting

**Parser fails on tender package.** MODL changed the template. Check
the regexes in `parse/tender_package.py`. Compare with the working
2025/2026 fixtures.

**Some lot is missing from `stats`.** Check that the PDF actually
downloaded (`ls data/probe/modl/2027/`). If the property-info PDF is
scanned, you need the corresponding JSON fixture.

**`bidsheet-all` errors on one lot.** Run `bidsheet --year 2027 --lot N`
for that specific lot to see the error in isolation.

**The naive bidder-count baseline says "5" but the comp set says "27".**
That's the §8.1 backtest finding in action — the comp-set count was
inflated by a few high-bidder outlier years (2021–2022). Trust the
naive baseline.

**A bid in the comp set looks wrong.** Check the corresponding
`award-NNN.json` fixture. Handwritten 2022 awards have transcription
uncertainty noted in their `ocr_notes` field — verify against the PDF
if a comp is doing heavy lifting in your decision.

---

## What this runbook does NOT cover

- Legal title research beyond what's in the property-info doc. For a
  serious bid, get a lawyer to do an independent title search.
- Tax-sale law in NS regarding lien survival (e.g. does the tax-sale
  deed extinguish prior mortgages?). The data suggests buyers often
  win lots with substantial liens — get a lawyer's opinion before
  bidding on an encumbered lot.
- Auto-submission of tenders. Tool is decision-support, not transaction.
