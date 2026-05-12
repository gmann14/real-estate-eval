# Tax Sale Bid Decision Sheet - Spec

> Personal-use decision-support tool for municipal sealed-tender tax sales in
> Nova Scotia, starting with the Municipality of the District of Lunenburg
> (MODL). The tool is not a bid oracle. It is an appraisal-first comp workbook
> plus a disciplined sealed-bid decision sheet.
>
> **Created:** 2026-05-12
> **Status:** Spec draft, revised after hostile review.
> **Next live opportunity:** MODL 2027 sale.

---

## 1. Core thesis

MODL tax-sale data can support useful personal decisions when the system stays
honest about its constraints:

1. **The sample is small.** MODL likely has only ~75-150 awarded lots from
   2021-2025. Important subgroups may have N < 10.
2. **All submitted bids are publicly disclosed per lot,** not just the winner.
   This means bidder counts and bid distributions can be measured from
   historical records rather than guessed. The user has verified bid-level
   disclosure for MODL. The parser still needs to confirm the exact disclosure
   form across all source years: amounts vs. amounts + names, sold lots vs.
   all listed lots, and no-sale lots included or not.
3. **Key enrichment sources are legally and operationally constrained.** PVSC
   and Property Online data are useful, but should not be treated as normal
   scrape targets.

The useful v1 product is therefore:

- a clean historic MODL tax-sale record including every submitted bid;
- a legally acquired, manually auditable property-enrichment table;
- a 5-nearest-comp appraisal sheet;
- a historical comp-exceedance curve over the comp set;
- a sealed-bid strategy worksheet based on the user's private value and risk
  tolerance.

The tool should help answer: **"What is this property worth to me, what has
similar tax-sale inventory attracted before, and what bid has historically
cleared comparable lots at an acceptable margin?"**

---

## 2. Scope

### In scope for v1

- **Geography:** MODL only.
- **History:** 2021-2025 awarded sales, plus the 2027 live list once
  published.
- **Primary artifact:** `evaluations/tax-sales/{year}/bid-sheet.md` and
  `master.csv`.
- **Method:** comparable-sales/appraisal workflow first; prediction only as a
  calibration layer.
- **Automation:** local scripts and browser-assisted workflows where allowed.
  Chrome/Playwright/Claude/Codex automation may be used to reduce repetitive
  navigation, but not to bypass site terms or turn prohibited bulk scraping
  into "automation."
- **Risk:** obvious mechanical flags only, plus a manual diligence checklist.

### Out of scope for v1

- Full legal/title/risk module.
- Automated PVSC or Property Online scraping unless written permission or a
  compatible licensed data path exists.
- Predicting redemption as a trained model.
- Auto-submitting tender packages.
- Other municipalities.
- A Bayesian hierarchical model.

---

## 3. Data-access rules

These rules are a gating requirement, not a nice-to-have.

### MODL public tax-sale pages and PDFs

MODL public documents are the only default automated scrape targets. Archive
all downloaded raw files under `data/raw/modl/{year}/`. Verified inventory
per year (probe of 2026):

- **Yearly tax-sale HTML page** (e.g. `/2026-tax-sales.html`): index of links
  only; not the primary data source.
- **Tender Package PDF** (`{year}-tax-sale-tender-package`): 4-page
  text-extractable PDF containing the legal notice, terms, and the full
  per-lot property list (AAN, civic address, community, lot description,
  status flags like `REDEEMABLE` / `HST APPLICABLE`, assessed owner,
  minimum bid). This is the primary listings source.
- **Bid Submission Form PDF** (`{year}-tender-bid-submission-form`): the
  blank form bidders fill in. One-time reference, not per-lot data.
- **Per-lot Award PDFs** (`tax-sale-award-{N}` or `tax-sale-award-{N}-1`):
  single-page scanned image PDFs (300dpi JPEGs, **not text-extractable**)
  with a ranked bid table (up to 20 slots), bidder names, amounts, winner
  highlight + signature + award-date stamp. Multimodal OCR required.
- **Per-lot Property Info PDFs** (`tax-sale-{N}-reporting-letter-attachments`):
  multi-page PDFs. Page 1 is a text-extractable legal-counsel title report
  (PID, civic address, title-system, marketability opinion, deed reference,
  road-access opinion). Pages 2–N are scanned attachments (deed, plan of
  survey, parcel map, photos) — OCR required for the visual content.
- **Tax Sale Surplus History PDF**: consolidated multi-year list of surplus
  payouts. Sanity check against `winning_bid - opening_bid`.

The naming slug `reporting-letter-attachments` is MODL's standard label for
the pre-sale property-info doc; do not interpret it as a flag for
disqualification or special cases. When an award has irregularities (e.g.
top bid disqualified, delayed award date), MODL may reuse the property-info
doc URL as the award link rather than producing a separate award PDF.

### PVSC

PVSC public property search data is useful, but the terms prohibit screen
scraping/database scraping and prohibit collecting, storing, reorganizing,
manipulating, merging, or publishing page data in ways beyond permitted private
individual page use.

Implication: `sources/pvsc.py` must not be a bulk scraper in v1.

Allowed v1 approaches:

- Manual lookup and human-entered fields.
- Browser-assisted individual lookup if the user is actively driving or has
  confirmed the workflow is permitted.
- A permissioned/API/licensed path if one is obtained.
- Storing minimal personal-use derived notes needed for the bid sheet, not a
  republished PVSC database.

### NS Property Online / parcel data

Property Online is a paid, agreement-governed service. It may be useful for
manual diligence, but it should not be assumed to provide freely scrapeable
parcel polygons.

Allowed v1 approaches:

- Use open Nova Scotia geodata where legally available.
- Use manual POL checks for shortlisted properties.
- Track unresolved parcel geometry in a manual queue.

### Browser automation policy

Chrome/Playwright automation can still be valuable:

- open the next AAN/PID lookup;
- pre-fill forms;
- screenshot pages for personal diligence notes only where the source terms
  allow saved local copies;
- maintain a review queue;
- prevent transcription errors by keeping source URLs and timestamps.

It cannot be the legal theory for prohibited scraping.

---

## 4. Architecture

```
tax_sale/
+-- __init__.py
+-- __main__.py
+-- cli.py                         # parse, review, enrich, comps, calibrate, bidsheet
+-- sources/
|   +-- modl.py                    # MODL HTML + PDF downloader/parser
|   +-- open_geo.py                # legal open geodata only
|   +-- browser_assist.py          # human-in-loop lookup helpers
|   +-- manual_import.py           # CSV import for user-entered fields
+-- parse/
|   +-- tender_package.py          # text-extractable per-lot listings (built; tested)
|   +-- award_pdf.py               # scanned-image award PDF parser; multimodal OCR
|   +-- property_info.py           # mixed-format property-info PDFs: page-1 text + later-page OCR
|   +-- surplus_pdf.py             # surplus PDF parser
+-- model/
|   +-- features.py                # conservative feature engineering
|   +-- comp.py                    # weighted comp score
|   +-- calibration.py             # rolling-origin backtests, optional regression
|   +-- decision.py                # value ceiling + bid shading scenarios
|   +-- bidsheet.py                # Markdown/CSV output
+-- data/
|   +-- raw/                       # downloaded public source files, gitignored
|   +-- parsed/                    # parsed MODL records
|   +-- manual/                    # user-entered enrichment CSVs, gitignored by default
|   +-- enriched/                  # joined local working tables, gitignored by default
+-- tests/
    +-- test_parse_award.py
    +-- test_comp.py
    +-- test_calibration.py
    +-- test_decision.py
```

The CLI should avoid the word `train` for v1. Use `calibrate`. The model is
not learning a stable market law; it is checking whether comp-derived
estimates have been directionally useful in prior years.

---

## 5. Data model

The primary key is **sale lot**, not AAN.

One tax-sale lot can involve multiple AANs or PIDs, and AAN/PID links can be
missing, retired, subdivided, consolidated, or inconsistent. Store identity as
a parent/child relation.

### `sale_lots`

| field | source | notes |
|---|---|---|
| `sale_lot_id` | derived | `{municipality}-{year}-{lot_number}` if possible |
| `municipality` | MODL | v1 = MODL |
| `year` | MODL | sale year |
| `lot_number` | tender package | "Tax Sale #" |
| `tender_id` | tender package | e.g. "2025-01-004" — MODL's internal tender reference |
| `display_address` | tender package | street line |
| `community` | tender package | locality (e.g. "NORTH RIVER") |
| `lot_description` | tender package | "LAND" / "LAND DWELLING" / structure dimensions like "1971 48X12" |
| `assessed_owners` | tender package | list of owner names from MODL listing; joint owners may span multiple `& ` continuation lines |
| `opening_bid` | tender package | taxes + interest + expenses |
| `hst_applicable` | tender package / award PDF | T/F/unknown |
| `status_at_publication` | tender package | redeemable/other/unknown |
| `tendered_at` | tender package | bid-opening date |
| `pid` | property-info PDF page 1 | parcel identifier; primary join key to geo data |
| `title_system` | property-info PDF page 1 | "land registered" / "registry" |
| `title_marketable` | property-info PDF page 1 | legal-counsel opinion (yes / qualified / no) |
| `road_access_class` | property-info PDF page 1 | `abuts_public` / `easement_or_ROW` / `no_access` / `unknown` — captured from legal-counsel language like "abuts the public highway" vs. "easement/right of way to the public highway" vs. "no apparent access" |
| `shore_privileges` | property-info PDF page 1 | boolean — title report mentions shore/waterfront privileges in the legal description |
| `encumbrances_summary` | property-info PDF page 1 | "None" or listed encumbrances per legal-counsel pre-sale review; pulls forward the lien/mortgage risk data previously deferred to v2 |
| `survey_on_file` | property-info PDF page 1 | T/F — modern survey plan filed at Land Registration; F is a buildability/title-clarity risk |
| `deed_document_no` | property-info PDF page 1 | reference for chain-of-title lookups |
| `legal_review_date` | property-info PDF page 1 | date of pre-sale title review |
| `outcome` | award PDF | sold/redeemed/no-bids/withdrawn/unknown |
| `awarded_at` | award PDF | actual award stamp date; usually = `tendered_at` but can differ on irregular awards |
| `winning_bid` | award PDF | sold lots only |
| `runner_up_bid` | award PDF | second-highest *eligible* submitted bid, if any |
| `bidder_count` | award PDF | number of bids received (any status); 0 on no-bid lots |
| `runner_up_cushion` | derived | `winning_bid - runner_up_bid`; cushion above second place |
| `surplus` | surplus PDF | sanity check |
| `premium_over_opening` | derived | descriptive only |
| `notes_public` | public docs | no private details |

### `sale_lot_identifiers`

| field | source | notes |
|---|---|---|
| `sale_lot_id` | derived | parent key |
| `identifier_type` | MODL/PVSC/POL/manual | AAN, PID, plan, parcel label |
| `identifier_value` | source | raw value |
| `confidence` | manual/parser | exact/probable/uncertain |

### `sale_lot_bids`

One row per submitted bid. Joins to `sale_lots` via `sale_lot_id`.

| field | source | notes |
|---|---|---|
| `sale_lot_id` | derived | parent key |
| `submission_rank` | award PDF | order in which bid appears on the form (1-20) |
| `bid_amount` | award PDF | dollars |
| `bidder_label` | award PDF if disclosed | nullable; omit or hash by default for v1 privacy |
| `bid_status` | award PDF | `submitted` / `winning` / `withdrawn` / `disqualified` / `tied_rebid` |
| `is_winning` | derived | `bid_status == 'winning'` |

The highest-ranked submitted bid is not always the winner. MODL practice
(observed on Award #51, 2026): bids may be **struck through** on the award
form when the bidder withdraws or is disqualified, with the award stamp
placed on the next eligible row. The parser must detect strikethrough
visual cues and assign `bid_status` accordingly — not assume rank-1 wins.

A separate `tied_rebid` status exists for the 24-hour re-bid rule described
in the tender package: when two bids are received at the same amount,
bidders are contacted and given 24 hours to submit a final bid. Until the
re-bid resolves, tied bids carry `tied_rebid` status; the final award PDF
should resolve them to `winning` / `submitted`.

### `enrichment`

Fields are separated by acquisition status. Every enriched value must carry
`source`, `source_date`, and `confidence`.

| field | notes |
|---|---|
| `assessed_value` | manually acquired or permissioned source |
| `assessed_land` | manually acquired or permissioned source |
| `assessed_improvements` | manually acquired or permissioned source |
| `has_structure` | derived from `lot_description` (e.g. "LAND DWELLING") or manually confirmed |
| `lot_size_bucket` | exact acres if reliable, otherwise bucket |
| `waterfront_class` | none/ocean/lake/river/unknown; exact metres optional. **Refinement of `sale_lots.shore_privileges`** — legal opinion is a hint, not ground truth; geographic verification overrides |
| `access_class` | public road/private/ROW/landlocked/unknown. **Refinement of `sale_lots.road_access_class`** — same hierarchy: MODL legal opinion is the v1 default, replaced by geographic verification when available |
| `service_centre_band` | near/mid/far, not false-precision km unless geocoded |
| `zoning_class` | broad class; exact zoning if readily available |
| `prior_market_evidence` | MLS/sale/assessment/manual comp note |
| `manual_review_required` | T/F |

Avoid making exact `waterfront_frontage_m` and `frontage_road_m` required for
v1. They are expensive, brittle, and can create fake precision.

---

## 6. Feature philosophy

Use features that a human appraiser would trust at small N:

- broad property type: vacant land / improved residential / commercial /
  unknown;
- assessment band and land/improvement split;
- opening bid as dollars and as opening-to-assessed ratio;
- waterfront/access class;
- geography band;
- HST flag;
- prior market evidence;
- obvious risk flags.

Do not explode categories unless the sample supports it. No target encoding in
v1. No large one-hot matrix. No high-cardinality road/zoning taxonomy unless it
is used only for display.

`premium_over_opening = winning_bid / opening_bid` remains useful for
descriptive sorting only. It is not one of the §8 modeling targets — tiny
opening bids can create enormous ratios that distort both regression and comp
scoring.

---

## 7. Comparable method

Phase 4 is the heart of the product.

For each live property, return the five best historical comps using a
transparent weighted score rather than generic Gower distance.

Default score:

| component | weight | notes |
|---|---:|---|
| property type match | 25 | vacant vs improved is first-order |
| waterfront/access class | 25 | split if both are known |
| assessment/value band | 20 | assessed value or appraisal proxy |
| geography band | 10 | service centre and local market |
| opening-to-assessed ratio | 10 | competition/latent spread signal |
| lot size bucket | 5 | broad bucket only |
| HST/prior market evidence | 5 | tie-breakers |

Every comp row should display the reasons it matched and the reasons it may be
bad. The user must be able to override or exclude comps manually.

Output values:

- comp median winning bid;
- comp low/high range;
- comp median as % of assessed/appraised value;
- comp median bidder count and range (field strength signal);
- comp median winner-vs-runner-up cushion;
- the full submitted-bid vector across comps, retained for the
  historical exceedance calculation in section 8;
- notes on sample depth: e.g. "3 usable waterfront land comps; 2 weak
  geography matches."

---

## 8. Modeling layer

Per-lot bid disclosure makes the modeling layer more useful, but it does not
magically solve the small-N problem. The model should estimate field strength,
characterize normalized bid distributions, and compute historical comp
exceedance rates. It may print calibrated win probabilities only after
rolling-origin backtests show that probability language is reliable.

**Language progression.** The bid sheet defaults to raw historical counts
and descriptive exceedance. It may upgrade to probability language only when
the exact normalization and comp-selection method passes rolling-origin
calibration with acceptable uncertainty. If calibration degrades on a future
run, the language reverts to raw counts.

### Three modeling tasks

1. **Field-strength model.** Predict bidder count from lot characteristics.
   Start descriptive: comp median/IQR bidder count and no-sale frequency.
   Only add a model if it beats that baseline in rolling-origin backtests.
   If modeled, use a count-aware or ordinal approach, not a default
   `log(1 + bidder_count)` regression. No-sale lots (`bidder_count = 0`) are
   kept because zero-bidder outcomes are informative.

   **Backtest finding (current implementation):** the comp-based median now
   has lower MAE on the lots it can score, but it covers fewer lots and
   remains positively biased. The bidsheet ships the naive prior-year
   baseline as the primary field-strength display because it has broader
   coverage and lower bias; comp-set bidder count is shown as secondary.
2. **Bid-level distribution.** For each comp-matched lot, retain the full
   submitted-bid vector, but normalize before aggregating across comps.
   Raw dollars from a $20k land lot and a $200k improved waterfront lot are
   not comparable. Preferred normalized views:
   `bid_amount / assessed_value`, `bid_amount / appraisal_proxy`, and
   `bid_amount / opening_bid`. Back-transform normalized summaries to the
   subject property for display.
3. **Historical comp-exceedance curve.** For any candidate bid B and selected
   comp set, compute the fraction of historical comparable auctions in which
   B, after normalization/back-transforming, would have exceeded the actual
   winning bid. This is non-parametric and decision-relevant, but it is a
   historical exceedance rate until calibrated.

   **Backtest finding (current implementation):** opening-bid-normalized
   exceedance is directionally useful but not tightly calibrated enough to
   call live win probability. The current rolling-origin run uses N=37
   held-out sold lots; median and upper-percentile lines are conservative by
   double-digit percentage points. The bid sheet therefore uses historical
   count/exceedance language rather than probability promises.

The exceedance curve is the headline quantitative output. The first two tasks
explain *why* the curve looks the way it does.

### Candidate baselines

Before any regression:

- median of top-5 comp winning bids;
- comp-set historical exceedance curve as a function of normalized bid amount;
- bidder-count median and IQR of the comp set;
- assessed-value percentage by property class.

Optional regression layer only if it beats the baselines, using a small fixed
feature set:

- `log_opening_bid`;
- `log_assessed_value`;
- `opening_to_assessed_ratio`;
- `property_type`;
- `waterfront_access_class`;
- `hst_applicable`;
- `geography_band`.

Small fixed one-hot encoding is fine at N around 100. No target encoding, no
high-cardinality features. The same feature set serves both the field-strength
model and the bid-level model.

### Validation

Do not rely on leave-one-year-out as the headline validation. With five years,
LOYO produces five noisy folds and can look more rigorous than it is.

Use rolling-origin backtests:

1. Calibrate on 2021-2022, predict 2023.
2. Calibrate on 2021-2023, predict 2024.
3. Calibrate on 2021-2024, predict 2025.

Report:

- median absolute dollar error vs. actual winning bid;
- bidder-count prediction error;
- empirical interval coverage (does the P90 of predicted bids actually
  exceed 90% of observed winning bids?);
- exceedance calibration: of bids the tool labeled 50%
  historical exceedance, what fraction actually would have won in held-out
  years?
- decision simulation: for each opportunistic/serious/must-win scenario,
  count counterfactual wins, average implied surplus, and average
  cushion above runner-up.

If these metrics are unstable, the bid sheet must say so plainly.

---

## 9. Decision strategy

The bid recommendation must separate four different numbers:

1. **Market/appraisal estimate:** what the property might be worth after tax
   sale frictions.
2. **Expected winning bid:** what the public historical data suggests might win.
3. **Private ceiling:** maximum rational bid after legal, repair, liquidity,
   time, and personal-use adjustments.
4. **Suggested submission:** one possible first-price sealed-bid strategy below
   the private ceiling.

Because per-lot bids are public (section 1.2), the suggested submission can be
anchored on historical comp exceedance rather than a guessed percentage of the
ceiling - i.e. the historical frequency with which a comparable normalized bid
would have exceeded every other bid on comparable lots. This becomes a printed
win probability only if rolling-origin calibration supports that language.

Produce scenario bids anchored on historical comp exceedance (section 8.3):

| scenario | intent | bid level |
|---|---|---|
| pass | avoid weak/unknown deals | no bid if ceiling <= minimum or diligence incomplete |
| opportunistic | only win with large margin | smallest bid clearing at least 20% of comparable historical auctions |
| serious | meaningful win chance, still shaded | smallest bid clearing at least 50% of comparable historical auctions |
| must-win | high conviction on this lot | smallest bid clearing at least 80% of comparable historical auctions, capped at private ceiling |

The 20% / 50% / 80% thresholds are user-tunable defaults and should be
revisited after the first rolling-origin backtest. Every scenario bid is
capped by the private ceiling - if a threshold cannot be reached without
exceeding the ceiling, the tool reports "ceiling-limited" rather than
silently fudging the number.

The user chooses the scenario. The tool should flag when all scenarios exceed
the private ceiling, when the comp set is too thin to support a stable
exceedance curve, or when bid-level disclosure was missing for too many comps
to compute a curve at all. With fewer than 20 genuinely comparable historical
auctions, print counts such as "cleared 3 of 7 comps," not percentage-style
probabilities.

---

## 10. Risk and diligence

v1 risk flags are obvious signals, not legal advice.

### Automatic or semi-automatic flags

- `REDEEMABLE` at publication.
- HST applicable.
- Improved property with unknown occupancy.
- Road access unknown/private/ROW/landlocked. (Cross-check `sale_lots.road_access_class`
  from MODL's legal opinion against any geographic refinement in
  `enrichment.access_class`; flag if the two disagree.)
- `title_marketable` flagged as qualified or `no` by MODL's legal review.
- Waterfront or wetland adjacency where buildability may be constrained.
- Assessment/improvements inconsistent with visible condition.
- Multi-parcel or uncertain AAN/PID mapping.
- No civic address or failed geocode.
- Sold/no-bid history on same or nearby parcel.
- Large opening bid relative to apparent value.
- **Conflict of interest** (§144 MGA): municipal council, MODL employees,
  their spouses, and majority-owned companies cannot bid. The bid sheet
  must surface this rule as a one-time reminder, not a per-lot flag.

### Manual diligence checklist

For every shortlisted lot:

- verify current tax-sale status close to tender deadline;
- verify AAN/PID mapping;
- check whether lot is one parcel or a package;
- review map, access, frontage, and apparent buildability;
- inspect Street View/satellite and drive by if practical;
- check for obvious occupancy, debris, commercial use, wetlands, dumps, or
  access disputes;
- decide private ceiling before looking at suggested submission.

The bid sheet should make incomplete diligence visible. It should never hide
unknowns behind a precise-looking interval.

---

## 11. Output

For the 2027 list, produce:

- `evaluations/tax-sales/2027/bid-sheet.md`;
- `evaluations/tax-sales/2027/master.csv`;
- `evaluations/tax-sales/2027/review-queue.csv`.

Example section:

```markdown
### Lot 12 - 1234 Maders Cove Road (AAN uncertain)

Opening bid: $4,820
Assessment/appraisal proxy: $187,300
Opening/appraisal ratio: 2.6%
Status: redeemable at publication

Property summary:
- 1-3 acre improved rural lot
- possible saltwater frontage; exact frontage not verified
- gravel/public road access appears likely; confirm
- no recent market evidence found

Data confidence:
- AAN/PID match: probable
- assessment: manually entered, source date 2026-05-12
- parcel geometry: unresolved

Risk flags:
- REDEEMABLE: may be pulled before deadline
- improved property: occupancy/condition unknown
- waterfront/buildability not verified

Five best comps:

| Score | Year | Address | Opening | Winning | Why matched | Why weak |
|---:|---:|---|---:|---:|---|---|
| 82 | 2024 | ... | ... | ... | improved waterfront rural | farther west |

Estimates:
- Comp median winning bid: $52,000
- Comp range: $34,000-$94,000
- Comp median bidder count: 3 (range 2-5)
- Comp median winner-vs-runner-up cushion: $8,400 (~16% over runner-up)
- Calibration note: waterfront + structure sample is thin (N=4)

Decision:
- Private ceiling: $62,000
- Opportunistic ($40,000): cleared 2 of 9 comparable historic auctions
- Serious ($52,500): cleared 5 of 9 comparable historic auctions
- Must-win ($62,000): cleared 8 of 9 comparable historic auctions
- Recommendation: serious only if drive-by confirms access and condition.
```

---

## 12. Six-phase build plan

Each phase must produce a useful artifact if the project stops there.

| Phase | Deliverable | Stop here if |
|---|---|---|
| 1 | Data-access/legal spike + source inventory + allowed automation plan | PVSC/POL access is blocked or must be manual |
| 2a | Inspect one award PDF from each source format/year; lock bid-disclosure schema and parser fixtures | Award PDFs are too inconsistent for acceptable manual correction time |
| 2b | MODL historic record: parsed 2021-2025 public lists/awards/surplus with `sale_lot_bids` populated per section 5 | You only need the public historical ledger |
| 3 | Manual/browser-assisted enrichment workbook + review queue | You want a comp browser with human-entered facts |
| 4 | Weighted comp bid sheet (section 7) for historical and live lots | You trust appraisal-style comps and don't need bid-distribution analytics |
| 5 | Modeling layer (section 8): historical comp-exceedance curve (section 8.3); field-strength and bid-level distribution summaries/models (sections 8.1, 8.2); rolling-origin calibration with decision-simulation backtest | Exceedance calibration is unstable, or parametric models fail to beat comp baselines on rolling-origin metrics |
| 6 | Decision strategy layer + shortlist diligence workflow consuming section 5 outputs | You want final bid scenarios for the 2027 tender |

If Phase 2a reveals that bid-level disclosure is inconsistent across years,
keep all disclosed bid rows but make section 8.3 operate only on lots with complete
bid vectors. If a live property's comp set has too few complete bid vectors,
fall back to the weighted-comp product in section 7.

Post-v1 only:

- second municipality adapter;
- bidder-identity FOI if names are not disclosed in award PDFs and
  repeat-bidder behaviour becomes worth modelling;
- redemption likelihood model;
- full title/risk module;
- hierarchical model across municipalities.

---

## 13. Day-one implementation risks

These should be handled before writing prediction code.

1. **Award PDFs vary by year.** Build parser fixtures from every year first.
2. **Lots can be pulled or redeemed after publication.** Add status refresh
   close to deadline and preserve timestamped snapshots.
3. **AAN/PID matching may fail.** Use a manual resolution queue.
4. **Rural addresses may not geocode.** Support parcel-first/manual geocoding.
5. **Multi-parcel sale lots exist.** Do not assume one AAN = one lot.
6. **Opening bids can change or include HST differently.** Store raw text and
   parsed dollars separately.
7. **No-bid properties matter.** Keep them for opportunity/risk context even
   if excluded from winning-bid calibration.
8. **Verify bid-disclosure consistency across years before bulk parsing.**
   The user has verified that all submitted bids are public, but the parser
   still needs to confirm that each source format exposes amounts, bidder
   labels, no-sale lots, below-reserve lots, and rank ordering consistently.
   `bidder_label` should default to null or a local hash; names are not needed
   for v1.
9. **Award PDFs are scanned image JPEGs, not text PDFs.** `pdftotext` returns
   nothing. The parser must use multimodal OCR (Read tool or equivalent
   visual-language model) — Tesseract alone will struggle with the
   handwritten signatures, stamps, and strikethrough marks that carry
   semantic meaning (winning row vs. disqualified row).
10. **Property-info PDFs are mixed-format AND year-dependent.** Page 1 of
    text-extractable docs is a legal-counsel title report yielding PID,
    title system, marketability opinion, road-access opinion, shore-privileges
    language, encumbrances summary, survey-on-file status, and deed reference
    in one `pdftotext` pass. Pages 2–N are always scanned attachments.
    **However**, page 1 itself is text-extractable in only ~48% of historical
    docs (verified May 2026):

    | Year | Text-extractable | Scan-only |
    |---|---:|---:|
    | 2022 | 7 / 24 | 17 |
    | 2023 | 3 / 8  | 5  |
    | 2024 | 0 / 15 | 15 |
    | 2025 | 13 / 14 | 1 |
    | 2026 | 12 / 12 | 0 |

    Older years and all of 2024 require multimodal OCR even for page 1.
    The text-only parser ships first (35 lots of historical coverage);
    visual-OCR enrichment of the remaining 38 lots is a separate batch of
    work and must complete before §7 comps can be drawn from those years.
11. **Tied bids trigger a 24-hour rebid.** When two bids match exactly, the
    award PDF cannot resolve them on the day of the tender. For the live
    workflow (2027+), the scraper must re-check award URLs in the days
    following the tender date and treat day-of and day-after PDFs as
    superseding earlier snapshots. For historical 2021–2025 data this is
    already settled — the archived PDFs reflect the final award.
12. **Award files and property-info files share URL slugs occasionally.**
    The standard convention is `tax-sale-award-{N}` for awards and
    `tax-sale-{N}-reporting-letter-attachments` for property info, but
    MODL has reused the property-info URL as the award link on irregular
    lots. The scraper should track both URLs per lot and treat duplicates
    as a manual-review trigger, not a data error.

---

## 14. Kill criteria

The project should downscope to a manual spreadsheet if any of these are true:

- legal data access prevents reliable enrichment;
- MODL public records cannot be parsed with acceptable manual correction time;
- manual enrichment of 20 representative lots takes more time than the bid
  process can justify;
- rolling-origin backtests do not beat simple comp medians;
- the 2027 live workflow cannot be completed before the tender deadline.

In that case, the correct v1 is a Saturday-workflow spreadsheet:

1. parse public MODL list;
2. manually enrich only the top 15 candidate lots;
3. build a comp table;
4. drive by the short list;
5. set private ceilings;
6. submit only bids with a clear margin of safety.

---

## 15. Sources and references

- [MODL 2026 Tax Sales](https://www.modl.ca/2026-tax-sales.html)
- [MODL Tax Sale Awards archive](https://modl.ca/index.php?option=com_docman&view=list&slug=tax-sale-awards&Itemid=102&layout=default)
- [MODL Tax Sale Surplus History](https://www.modl.ca/tax-sale-surplus-history.html)
- [PVSC public property search terms](https://webapi.pvsc.ca/Home/Tos)
- [Nova Scotia Property Online subscription](https://www.novascotia.ca/programs-and-services/land-and-property)
- [Property Online user guide](https://www.novascotia.ca/sns/pdf/ans-property-pol-user-guide.pdf)
- First-price sealed-bid auction theory: use as framing only. MODL
  bid-level disclosure improves the empirical footing, but historical bids
  still need normalization, comp selection, and calibration before they should
  be described as live win probabilities.
- [Existing repo: deal-finder-mvp.md](deal-finder-mvp.md)
