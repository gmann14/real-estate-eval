# Manual Data Tasks

> Things only you can do to harden the dataset before the 2027 sale. None
> of these are urgent. None of them are the 2027 workflow itself — that
> lives in [RUNBOOK-2027.md](RUNBOOK-2027.md).
>
> Total effort: ~3-4 hours, spread however you like across the next 8-9
> months. Doing them now means February 2027 is purely about reading bid
> sheets, not about plumbing.

---

## 1. Back up your local `data/` directory ⚠️ DO FIRST

**Why:** The 392 MB of working data (MODL PDFs + hand-OCR'd JSON fixtures
+ any PVSC CSVs you build) lives only on your laptop. If the laptop dies,
re-scraping is mechanical but re-OCRing the 92 historical award PDFs is
~1-2 hours of agent work. Worth a one-time backup.

**Options, easiest first:**

- **Google Drive / Dropbox** — drag the `data/` folder in. ~10 min upload.
  Re-do whenever you've made significant changes (after running the
  scraper or after a PVSC enrichment session).
- **rsync to a private server** if you have one.
- **Encrypted tarball to S3 / Backblaze** for paranoia-grade:
  ```bash
  tar czf - data/ | openssl enc -aes-256-cbc -pbkdf2 -pass pass:YOUR_PASS \
    > tax-sale-data-$(date +%Y%m%d).tar.gz.enc
  # Upload the .enc file wherever
  ```

**Verify the backup occasionally** — at least once before the 2027 sale window.

---

## 2. PVSC enrichment for historical lots (the highest-value job)

**Why:** Right now, none of the 124 lots in the dataset have PVSC-sourced
`assessed_value`. The comp scorer leans on `opening_bid` as the only
value proxy. Adding assessed values will:

- Tighten comp matching (similar `opening_to_assessed_ratio` is a real signal)
- Improve the §8.3 historical-exceedance calibration (currently only
  "directionally useful" because the normalization is weak without a
  reliable value anchor)
- Let you spot bargain lots in past data (MODL asking 2% of assessed → low
  bid wins; MODL asking 50% of assessed → fierce bidding) — pattern
  recognition before the live sale

**Effort:** ~30 minutes per year × 5 years with bidding outcomes ≈ 2.5
hours. Split across multiple sittings as you prefer.

### 📋 The actual checklist

**Auto-generated from the current dataset:** [`PVSC-CHECKLIST.md`](PVSC-CHECKLIST.md)

That file has one row per lot you need to look up, organized by year,
with the **AAN**, **PID**, **civic address**, **community**, **opening
bid**, **outcome**, and **lot description** all visible. Tick the
checkbox column as you go. Re-generate after each session to shrink the
list:

```bash
python3 tax_sale/scripts/generate_pvsc_checklist.py --out tax_sale/PVSC-CHECKLIST.md
```

(Lots that already have enrichment data are filtered out automatically,
so the checklist gets shorter each pass.)

### Priority order

1. **2026** first — most recent, freshest assessments, smallest year (12 lots, ~20 min)
2. **2025** — same template as 2026 (13 lots, ~20 min)
3. **2024** — useful comps for 2027 (15 lots, ~25 min)
4. **2023** — only 7 lots; quick win
5. **2022** — 16 sold + 8 no-bid lots, longest year (~40 min)
6. **2021** — 16 sold + 4 no-bid lots; no property-info docs so PIDs missing (~30 min)

### Process per year

```bash
# 1. Generate the empty CSV (or re-generate if already done)
python3 -m tax_sale enrichment-template --year 2026 \
  --out data/enrichment/pvsc-2026.csv

# 2. Open both the CSV and tax_sale/PVSC-CHECKLIST.md side by side.

# 3. For each row in the checklist:
#    a. Copy the AAN
#    b. Paste into https://www.pvsc.ca/find-assessment (Search by AAN)
#    c. Solve the reCAPTCHA, hit Submit
#    d. Cross-check the address PVSC shows matches the checklist's Civic Address
#    e. Read off assessed_value (+ assessed_land, year_built, lot_acres,
#       structure_sqft if shown); paste into the CSV
#    f. Tick the checkbox in PVSC-CHECKLIST.md

# 4. Save the CSV. Verify it loaded:
python3 -m tax_sale stats   # has_enrichment count should jump by however many rows you filled in
```

Detailed gotchas (multi-parcel, AAN-not-found, vacant land vs improved,
etc.) are in [PVSC-LOOKUP-GUIDE.md](PVSC-LOOKUP-GUIDE.md).

---

## 3. Audit a sample of handwritten 2022 award OCR transcriptions

**Why:** The 2022 award PDFs were handwritten on paper forms. Claude Code
agents transcribed them visually during the dataset build. The agents
flagged uncertain readings in `ocr_notes`, but didn't catch silent errors
(e.g. a "3" mis-read as an "8" with no flag). For any 2022 comp doing
heavy lifting in a 2027 bid decision, errors compound.

**Effort:** ~5 minutes per lot × ~5-10 high-leverage lots = ~30-60 min.

**How to pick which lots to audit:** these have shown up repeatedly in
comp sets for 2025/2026 lots, so their values matter most:

- **2022 Lot 88** (49 bidders, Jim Sunderland $221k winner) — appears in
  many comp sets as the "high competition" anchor
- **2022 Lot 89** (27 bidders, $176k) — Sunderland again
- **2022 Lot 31** (36 bidders, $31.5k)
- **2022 Lot 57** (34 bidders, $31.5k) — note the disqualified top bidder
  was flagged in `ocr_notes`; verify the final assignment
- **2022 Lot 34** (19 bidders, $53k)
- **2022 Lot 21** (11 bidders, $26.5k)

**Process for each:**

1. Open `data/probe/modl/2022/award-NNN.pdf` (visually, in Preview)
2. Open `data/probe/modl/2022/award-NNN.json` next to it
3. Cross-check: lot number, owner, AAN, opening bid, each bid amount,
   winner (highlighted on the form)
4. If you spot an error, edit the JSON and save
5. Re-run `python3 -m pytest tax_sale/tests/test_award_pdf.py` to confirm
   schema still validates

**Same applies for 2021** lots that are big comps — Lot 168 (47 bidders,
$352k Elynor Sutherland), Lot 169 (35 bidders, $126k Elynor Sunderland),
Lot 170 (32 bidders, $126k Elynor Sunderland). The Sutherland/Sunderland
spelling inconsistency is worth resolving — same person or different
people? Affects whether they count as a single repeat-bidder pattern.

---

## 4. Decide on a privacy posture for the JSON fixtures

**Current state:** 92 award JSONs + 42 property-info JSONs sit in your
local `data/probe/modl/` containing real bidder/owner names. Gitignored
from the public repo by `.gitignore` rules. Not committed anywhere.

**Two scenarios where this becomes a real choice:**

### A. You want a collaborator to use the toolkit

They can't run the bidsheet without the fixtures. Options:

1. **Share the raw JSONs privately** (encrypted tarball, private repo,
   shared cloud folder). Trust them with the original names.
2. **Share the anonymized JSONs only.** Run
   `python3 tax_sale/scripts/anonymize_fixtures.py` — it writes
   `*.anonymized.json` next to each source, with bidder names replaced
   by stable hashes (`BIDDER_a3f72b91`). Same name → same hash, so
   repeat-bidder patterns still work; real names are gone.
3. **Have them re-OCR.** Tedious; only viable if they have Claude Code.

### B. You want to make the toolkit fully reproducible publicly

Same anonymization step, then promote the `*.anonymized.json` files
into a committable directory (e.g. `tax_sale/fixtures/`) and add to
git. Update `dataset.load_year` to fall back to the anonymized fixtures
when the original ones are absent.

**For now, neither is necessary** — the toolkit works locally with the
real names, and the public repo has enough content for someone to
understand what the project does without the data.

**The anonymizer script is already there and tested.** When you want it,
one command:

```bash
python3 tax_sale/scripts/anonymize_fixtures.py
# writes 92 award + 42 property anonymized JSONs alongside originals
```

Output stays gitignored under the default `data/` rule. Promote
selectively if you decide to.

---

## 5. (Optional) Inspect the property-info pages 2-N for richer data

The hand-OCR'd property-info JSONs cover **page 1 only** — the
legal-counsel title report. Pages 2-N of each PDF contain scanned
attachments: deed photocopies, plan of survey, parcel map, property
photos. We haven't extracted anything from those.

Useful fields we'd gain by OCR'ing the attachments:

- **Parcel boundary polygon** (from the plan of survey) — would let us
  compute frontage on water, distance to nearest road
- **Lot dimensions** as drawn — sanity-check against the PVSC `lot_acres`
- **Deed text** — already-typed legal description with metes-and-bounds
- **Photos** — current condition, structure visible, neighbours

**Effort:** ~1-2 minutes per page × ~5-10 pages per doc × ~70 docs =
~10-20 hours. **Not worth doing systematically.** Worth doing ad-hoc for
specific 2027 shortlist lots before bidding.

When you want this for a single lot, the workflow is just:

> "Read pages 2-9 of data/probe/modl/2027/property-NNN.pdf and tell me
> the lot dimensions, deed reference, and any visible structures."

To a Claude Code agent. Single-shot, no automation needed.

---

## Suggested cadence

| Task | When |
|---|---|
| 1. Back up `data/` | **This week** |
| 2. PVSC enrichment (start with 2026) | Spread across weekends Jun–Dec 2026 |
| 3. Audit handwritten 2022 OCR | One sitting, ~1 hour, any time before Feb 2027 |
| 4. Anonymize fixtures | Only when you decide to share / make public |
| 5. Deep-OCR property-info pages 2-N | Ad-hoc per shortlist lot during 2027 bid window |

If you only do **#1 + #2**, the 2027 sale will be substantially better
prepared than today. Everything else is incremental polish.
