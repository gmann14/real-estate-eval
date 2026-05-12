# PVSC Manual Lookup Guide

> The one-time manual step that enriches every lot with its official Nova
> Scotia assessed value, lot size, and structure data. Without this, the
> comp scorer leans on opening-bid as the only value proxy and the
> `opening_to_assessed_ratio` feature is missing.
>
> **Time:** ~30 minutes for a typical MODL year (~20 lots).
> **Tools:** Your browser + this repo's CLI. Nothing else.

---

## Why this step exists

The Nova Scotia Property Valuation Services Corporation (PVSC) publishes
the official assessed value for every property in the province. It's the
single source of truth for "what's the underlying property worth on
paper."

**What MODL gives us** (in the tender package + property-info docs):
- Opening bid (taxes + interest + expenses owed)
- Civic address, AAN, PID
- Title/access/marketability opinion from MODL's legal counsel
- Encumbrances and survey status

**What MODL does NOT give us:**
- Assessed value
- Lot size in acres
- Structure square footage / year built
- Land-vs-improvements breakdown

PVSC has all of that. MODL's tender package itself instructs bidders:
> *"For more information on properties listed, please go to www.pvsc.ca"*

So this is the sanctioned workflow. We just couldn't automate it because
PVSC's public search is gated by reCAPTCHA v3 (built to block
scraping, not legitimate per-lot lookups).

---

## Step 1 — Generate the CSV template

From the repo root:

```bash
python3 -m tax_sale enrichment-template --year 2027 \
  --out data/enrichment/pvsc-2027.csv
```

This writes one row per 2027 lot, pre-filled with:
- `aan` — Assessment Account Number (the lookup key)
- `lot_number`, `year` — for your reference
- `display_address` — so you can confirm you're looking at the right lot
- `community` — same
- `opening_bid` — what MODL is asking for

The remaining columns (`assessed_value`, `assessed_land`,
`assessed_improvements`, `year_built`, `lot_acres`, `structure_sqft`,
`notes`, `source_date`) are blank. You fill them in.

The file lives at `data/enrichment/pvsc-2027.csv`. Open it in any
spreadsheet editor (Numbers, Excel, Google Sheets) or a plain text editor.

---

## Step 2 — Open PVSC's public search

In your browser, go to:

**<https://www.pvsc.ca/find-assessment>**

Click **"Search by Assessment Account Number"** (the AAN search). You'll
see a form with a single text box and a Submit button.

You may also see a Terms of Use checkbox or a recaptcha challenge —
solve / accept as normal. The reCAPTCHA is automatic for real browser
sessions and won't slow you down.

---

## Step 3 — Look up each AAN

For each row in your CSV:

1. **Copy the AAN** from the CSV (8 digits, may have leading zeros — leading zeros are OK).
2. **Paste into the PVSC search box** and submit.
3. **Cross-check the address** that comes back against the CSV's
   `display_address` — sometimes the same AAN points to a property
   with a slightly different address; this confirms you're on the
   right record.
4. **Read these fields from the PVSC report page:**

| PVSC report field | Maps to CSV column | Notes |
|---|---|---|
| "Assessed Value" or "Total Assessment" | `assessed_value` | Current year's total assessment, in dollars |
| "Land Value" (or "Land") | `assessed_land` | Optional, skip if not shown |
| "Improvements Value" (or "Building") | `assessed_improvements` | Optional, skip if not shown |
| "Year Built" | `year_built` | Only for improved properties |
| "Lot Size" / "Parcel Size" | `lot_acres` | If shown in square feet, divide by 43,560 to get acres |
| "Building Area" / "Floor Area" | `structure_sqft` | In square feet; only if improved |

5. **Paste the numbers into your CSV row.** Don't worry about commas or `$` signs — the loader strips them.
6. **Optional:** add a note in the `notes` column if anything's worth flagging (e.g. "split assessment for adjacent parcels", "shows as exempt", "no improvements visible").
7. **Optional:** add today's date in `source_date` (format: `2027-02-15`) so you remember when you ran the lookup.

---

## Step 4 — Common cases & gotchas

### Case A: Vacant land

PVSC shows:
- Land Value: $X
- Improvements Value: $0 (or absent)
- No year built, no building area

CSV row:
```
00190705,...,18900,18900,0,,5.4,,vacant land
```

### Case B: Single-family dwelling

PVSC shows:
- Land Value: $A
- Improvements Value: $B
- Year Built: YYYY
- Floor Area: NNN sqft

CSV row:
```
00017183,...,187300,42000,145300,1971,1.8,1024,
```

### Case C: Multi-parcel lot

Sometimes MODL's property-info doc references multiple PIDs for the same
AAN (the tax-sale lot bundles multiple parcels). PVSC will only show ONE
AAN's data per lookup. Two options:

1. **Use the primary parcel's data** and note in `notes`:
   `"multi-parcel; PVSC value for primary parcel only"`
2. **Look up each PID separately** and sum the values, noting `"multi-parcel; sum across N PIDs"`

The first is fine for v1 — comp scoring tolerates rough values.

### Case D: AAN not found

Some tax-sale lots have AANs that don't return results in PVSC. This
happens when:
- The AAN was retired but still appears on MODL's roll
- The parcel is in a special-status category (Crown land, etc.)
- The PVSC database is out-of-sync with MODL

Leave assessed_value blank and add `notes`: `"PVSC: AAN not found"`. The
dataset loader handles missing values gracefully — the lot just won't
have `opening_to_assessed_ratio` available.

### Case E: Property exempt or assessed at $1

Occasionally PVSC shows $1 assessed value (placeholder) or "exempt"
status. Use $1 (the literal value) and note `"PVSC: exempt or $1 placeholder"`.

### Case F: Assessed value is from a prior year

PVSC publishes new assessments each January. If you're doing this in
February 2027, the current value is the 2027 assessment (just published).
If you're doing it in October 2027, the 2027 assessment is still the
current value (new ones come out January 2028).

Either way, paste what PVSC shows. The model doesn't care about the
specific year — what matters is having any reasonable dollar value.

---

## Step 5 — Save and verify

Save the CSV. Then from the repo root:

```bash
python3 -m tax_sale stats --strict
```

You should see the "has_enrichment" count match the number of lots
you filled in. If your 2027 list has 22 lots and you looked up 22 of
them, you should see 22 with enrichment.

If you want to verify a specific lot loaded correctly:

```bash
python3 -c "
from tax_sale.dataset import load_all_lots
records = load_all_lots()
lot = next(r for r in records if r['year'] == 2027 and r['lot_number'] == 2)
print(f'AAN: {lot[\"aan\"]}')
print(f'Assessed value: {lot.get(\"assessed_value\")}')
print(f'Opening/assessed ratio: {lot.get(\"opening_to_assessed_ratio\")}')
"
```

---

## Step 6 — Regenerate bidsheets with the new data

```bash
python3 -m tax_sale bidsheet-all --year 2027 --out-dir bidsheets/2027/ --strict
```

The bidsheets are now richer:
- Comp scoring weighs `opening_to_assessed_ratio` more heavily
- Lots with very low ratios (e.g. opening bid is 1% of assessed value)
  stand out as potential bargains in the comp set
- Risk flags include "assessment inconsistent with visible condition"
  when applicable

---

## Where the data lives

```
data/enrichment/
└── pvsc-2027.csv      ← your manually-curated CSV (per-year)
```

The file is **gitignored by default** per the spec — PVSC data shouldn't
be republished. It stays on your local machine.

If you want to back it up, copy to your private Drive / Dropbox. If you
do future enrichment for 2028, 2029, etc., each year gets its own CSV
in the same directory.

---

## Troubleshooting

**The PVSC site asks me to log in.**
You don't need to log in for the public search. If it's asking for AAN
*and* PIN, you're on the wrong page — go to
`/find-assessment` and use the "Search by Assessment Account Number"
flow, not "My Property Report".

**reCAPTCHA keeps challenging me.**
You may be hitting their rate limit. Wait 30 seconds between lookups,
or take a 5-minute break after every 10 lookups.

**The CSV is messy after I edit it.**
Open it in a plain text editor (VS Code, BBEdit, Notepad++) to verify
each line is well-formed. Numbers shouldn't have quotes around them
unless they contain commas. The loader is tolerant of `$` and `,` but
not of mixed quoting.

**I want to redo a lookup.**
Just edit the CSV — the loader picks up changes on the next CLI run.
Last write wins for any AAN.

**A historical year (2021-2026) needs enrichment too.**
The same workflow applies — `enrichment-template --year 2024 --out
data/enrichment/pvsc-2024.csv`, then look up those AANs. Multiple
year-specific CSVs are fine; the loader joins all of them.

Note: `enrichment-template` writes to one file per call. If you want
all years in one CSV for batch lookup, run it without `--year`:

```bash
python3 -m tax_sale enrichment-template --out data/enrichment/pvsc-all.csv
```

Will give you every lot across every year that doesn't yet have
enrichment.

---

## What this enrichment unlocks downstream

Once `assessed_value` is populated, the system can:

1. **Bigger / better comp matching** — currently the scorer uses
   opening-bid range as a value proxy; with assessed_value it can use
   the real value, which is more reliable.
2. **`opening_to_assessed_ratio` feature** — a strong signal for
   competition intensity (very low ratios mean MODL is selling far
   below market and attract many bidders).
3. **Better §8.3 calibration** — the historical-exceedance curve gets
   tighter because the comp set is more homogeneous in true property
   value.
4. **Manual sanity check** — "MODL is asking $4,500 for a property
   PVSC assesses at $187,300" is a quick smell test for whether the
   lot is worth investigating.

None of these are required — the system works without enrichment, just
less precisely.
