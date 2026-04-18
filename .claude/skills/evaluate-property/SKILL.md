---
name: evaluate-property
description: Produce a full real estate investment analysis (TL;DR, scenarios, projections, rent-vs-buy, stress tests, enhancement ROI) for a residential property given a listing URL or filled input template. Use when the user pastes a listing link, says "evaluate this property", or asks for a buy/hold/walk recommendation on a specific address.
---

# Real Estate Evaluation Skill

You are about to evaluate a residential investment property for the user. The
goal is a rigorous, conservative, opinionated analysis that gives them a
clear buy / fair-offer / walk-away recommendation.

## Inputs you might receive

1. **Listing URL** (realtor.ca, viewpoint.ca, centris.ca, or similar) —
   fetch and extract structured data
2. **Filled input file** at `evaluations/<slug>/input.md` — use it directly
3. **Free-form description** — prompt the user to fill
   `templates/evaluation-template.md`
4. **"Update the analysis"** — re-run against an existing
   `evaluations/<slug>/input.md` with new data (e.g., seller-provided
   financials arrived)

## Workflow

### Step 1 — Gather & normalize input

1. If given a URL: fetch the listing (WebFetch), extract price, address, type,
   year built, units, features, listing agent. Flag anything missing.
2. Create a property slug (`<number>-<street>-<city>`, lowercase, hyphenated)
3. Create `evaluations/<slug>/input.md` from
   `templates/evaluation-template.md`, filling in everything you know
4. Load province defaults from `config/provinces/<province>.md`
5. Load generic defaults from `config/defaults.md`
6. Load CMHC rules from `config/cmhc-premiums.md`
7. Load owner profile from `config/owner-profile.md` if it exists;
   otherwise use `config/owner-profile.example.md` as the generic default
8. Enrich input by searching for:
   - Comparable LTR rents (Kijiji, rentals.ca, Facebook Marketplace)
   - Comparable STR ADR + occupancy (Airbnb search, AirDNA if available)
   - Current 5-year fixed mortgage rate (ratehub.ca, nesto.ca)
   - Property assessment (PVSC for NS, MPAC for ON, BC Assessment for BC)
   - Recent comparable sales

### Step 2 — Confirm before running

Before producing the full analysis, show the user the filled input and the
key assumptions. Ask whether to proceed, or whether they want to override any
numbers. This prevents a 700-line analysis built on wrong inputs.

### Step 3 — Run the analysis

Produce `evaluations/<slug>/analysis.md` following `templates/analysis-template.md`.

**All financial math uses Canadian semi-annual mortgage compounding** (not US
monthly). Do NOT compute payments by hand — call the authoritative helper:

```
npx tsx src/analysis/cli.ts <price> <down-fraction> <annual-rate> <amort-years>
# e.g. npx tsx src/analysis/cli.ts 485000 0.05 0.042 25
```

The JSON output gives you `downPayment`, `cmhcPremium`, `totalMortgage`, and
`monthlyPayment` — use those numbers verbatim in the analysis. A manually
computed payment that differs by more than $1/mo from the CLI output is a
bug (usually from slipping into US monthly compounding, `r/12`). Re-check
the CLI before publishing.

**Always generate six scenarios** (A–F) at two financing levels (5% down if
owner-occupy CMHC-eligible, 20% down). Show both Year 1 and steady-state
(Year 3+) monthly cost.

**Always produce a price-sensitivity table** across at least 5 price points
spanning low-ball offer to "walk away" territory.

**Always include stress tests:**
- Occupancy drop (STR to 35%)
- Rate increase at renewal (+1.5% to +1.8%)
- Combined worst case (low occupancy + high rate + high insurance)
- Flat appreciation (0%)

**Always include a rent-vs-buy crossover analysis** with a 7% alternative
investment return assumption and the user's actual equivalent rent.

**Always flag critical issues** that could kill the deal independently. For
heritage/pre-1900/unusual properties, this almost always includes (a) CMHC
insurability, (b) insurance quotes, (c) structural assessment.

### Step 4 — Enhancement analysis

Produce `evaluations/<slug>/enhancements.md` following
`templates/enhancements-template.md`. Score each enhancement's feasibility
against *this specific property's* constraints (lot size, heritage, zoning,
basement type, electrical capacity), not generic best practices.

### Step 5 — Self-audit

Before handing back the result, **run an audit pass** on your own output:

1. Are the base-case assumptions aggressive or conservative? Err conservative.
2. Did you verify CMHC eligibility for the property type + down payment combo?
3. Is the mortgage payment the exact figure returned by
   `npx tsx src/analysis/cli.ts ...` for your (price, down, rate, amort)?
   Run it again and diff if you're unsure — hand-computed payments are a
   frequent source of bugs.
4. Does the monthly OPEX total sum correctly?
5. Are the price-sensitivity cells internally consistent (higher price →
   higher cash to close, longer crossover)?
6. Did you include stress tests?
7. Did you flag at least the top 2–3 property-specific risks?
8. Is the bottom-line recommendation tied to specific numbers, or hand-wavy?

If any of these fail, fix before surfacing the analysis. Include an audit
trail appendix in the analysis noting what you verified and what you
revised.

### Step 6 — Optional outputs

Ask the user if they want any of:

- `email-to-realtor.md` — 10–15 targeted questions to send the listing agent
  (use the Prince Street example as a model: one question per line of
  concern; no fluff)
- `tldr.md` — 5-line SMS-friendly summary they can forward
- Updated `evaluations/INDEX.md` entry (if the file exists — roadmap item,
  see Phase 3)

## Principles

- **Opinionated, not wishy-washy.** Give a clear buy/fair/walk recommendation
  with a specific max price. The user can argue with a number; they can't
  argue with "it depends."
- **Every number traceable.** Each assumption must cite a source: config
  file, user override, or comp.
- **Conservative base case.** Aggressive scenarios are for the
  optimistic column, not the recommendation.
- **Be honest about uncertainty.** Where data is soft (e.g., insurance for
  heritage property), say so and widen the range.
- **Audit yourself.** The analysis has a known failure mode: AI-generated
  projections drifting over-optimistic. Build the audit step into every run.

## Golden reference

The gold standard for analysis quality is
`evaluations/9-prince-street-lunenburg/analysis.md` — in particular the
revision structure (Original → Audit Revised → Final Actual-Based) and the
Critical Issues section at the top. Study its structure before writing.

## When to refuse or pause

- **User provides no location/price:** you cannot evaluate. Ask for at minimum
  address + asking price.
- **Property is outside Canada:** flag that the tax/CMHC/DTT logic doesn't
  apply; ask whether to proceed with US or generic assumptions (tool is
  Canada-tuned).
- **User asks for a guarantee or a prediction:** remind them that all figures
  are projections, point them at `DISCLAIMER.md`, and proceed.

## When the data is thin

If you can't find good comps or the listing is sparse:

- Still produce the analysis, but with explicit `?` placeholders and a
  prominent "data confidence: low" banner at the top
- Expand the assumption ranges (conservative / base / optimistic) to reflect
  the wider uncertainty
- Push harder on the stress-test section
- Generate a longer email-to-realtor with the specific data you need
