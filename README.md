# Real Estate Evaluation Tool

A Claude-Code-driven framework for evaluating residential investment
properties in Canada. Paste a listing, get a full investment analysis:
scenarios, projections, stress tests, enhancement ROI, and a bottom-line
recommendation with a specific max price.

> **Status:** v0.1 — works as a markdown + Claude-agent framework. The
> deterministic TypeScript financial engine described in `SPEC.md` is on the
> roadmap (see `SPEC.md` §11). Current version relies on the AI agent for
> both data gathering and calculations; a self-audit step catches most
> drift, but always verify the math on any decision you'd actually make.

## Quickstart

### 1. Install as a Claude Code project

```bash
git clone https://github.com/<you>/real-estate-eval.git
cd real-estate-eval
```

The skill at `.claude/skills/evaluate-property/` is picked up automatically
when Claude Code runs in this directory.

Optional — install the TypeScript tooling if you plan to run tests or
contribute to the deterministic helpers:

```bash
npm install
npm test
```

### 2. Configure your owner profile (optional but recommended)

```bash
cp config/owner-profile.example.md config/owner-profile.md
# Edit with your province, tax rate, investment horizon, etc.
```

`config/owner-profile.md` is gitignored — your personal financials stay local.

### 3. (Optional) Define your criteria

```bash
cp config/criteria.example.md config/criteria.md
# Edit hard filters (units, price cap, allowed municipalities, lot size)
# and soft signals (ADU potential, upgrade paths, condition flags)
```

`config/criteria.md` is gitignored. A parser and screener live in
`src/utils/` with vitest coverage — the orchestrating `/ingest-listing`
skill that calls them end-to-end is the next step (see Roadmap).

### 4. Evaluate a property

Ask Claude one of:

> Evaluate this property: https://www.realtor.ca/real-estate/...

> Evaluate 123 Main St, Halifax — asking $450K duplex, 2BR + 1BR,
> owner-occupy 2BR with smaller as Airbnb

The agent (`.claude/skills/evaluate-property/SKILL.md`) will:

1. Fetch the listing (or prompt you to fill `templates/evaluation-template.md`)
2. Gather comps (LTR rents, Airbnb ADR/occupancy), mortgage rates, assessment
3. Confirm assumptions with you
4. Write a full `evaluations/<slug>/analysis.md`
5. Write a property-specific `enhancements.md`
6. Offer to draft a questions-for-realtor email

> **Coming soon:** a `/ingest-listing` skill that wraps this with
> URL-aware source adapters, the criteria screener, and an auto-appended
> watchlist at `evaluations/INDEX.md`. See
> [docs/phase-3-plan.md](docs/phase-3-plan.md) for the design and
> [Roadmap](#roadmap) below for shipping status.

## What you get

Each evaluation produces:

```
evaluations/<slug>/
  input.md              # Filled template (kept for reproducibility)
  analysis.md           # Full analysis (see structure below)
  enhancements.md       # Tiered ROI improvement recommendations
  email-to-realtor.md   # Optional — targeted diligence questions
```

### Analysis structure

- **TL;DR** — primary scenario in 6 metrics + final verdict
- **Critical issues** — things that can kill the deal (CMHC, insurance, structural)
- **Assumptions framework** — base / conservative / optimistic, with sources
- **Upfront costs** — cash to close at 5% / 10% / 20% down
- **Monthly out-of-pocket** — 6 scenarios × 2 financing levels
- **Price sensitivity** — 5+ price points with 5-yr and 10-yr returns
- **Returns if sold** — year-by-year to 10 years
- **Rent vs. buy** — crossover analysis with 7% investment alternative
- **Risk analysis** — risk matrix + 4 stress tests
- **Tax considerations** — T776, principal residence, HST threshold
- **ROI enhancements** — tiered by capital required
- **Bottom line** — offer strategy with specific price bands

## Scenarios always modeled

| Scenario | Description |
|----------|-------------|
| A | Owner-occupies larger unit, smaller unit as LTR |
| B | Owner-occupies larger unit, smaller unit as Airbnb ⭐ |
| C | Both units as LTR (pure investment) |
| D | Both units as Airbnb (pure investment) |
| E | Owner-occupies + Airbnb summer only |
| F | Dual-occupancy (split costs with family/partner) |

Each at 5% down (if CMHC-eligible), 10% down, and 20% down.

## Repo structure

```
real-estate-eval/
├── SPEC.md                              # Full technical specification + roadmap
├── README.md                            # This file
├── LICENSE                              # MIT
├── DISCLAIMER.md                        # Not financial advice
├── CONTRIBUTING.md                      # How to add provinces / contribute
├── .claude/
│   └── skills/
│       └── evaluate-property/           # Full analysis workflow
│           └── SKILL.md
├── templates/
│   ├── evaluation-template.md           # Blank input
│   ├── analysis-template.md             # Analysis report skeleton
│   ├── enhancements-template.md         # ROI enhancement skeleton
│   └── sheet-design-reference.md        # Google Sheet export reference
├── config/
│   ├── defaults.md                      # Generic default assumptions
│   ├── cmhc-premiums.md                 # CMHC rules + premium tables
│   ├── criteria.example.md              # Copy to criteria.md (gitignored) to pre-screen
│   ├── owner-profile.example.md         # Copy to owner-profile.md (gitignored)
│   ├── municipalities/
│   │   ├── modl.md                      # Lunenburg south-shore cluster
│   │   ├── hrm.md                       # Halifax Regional Municipality
│   │   └── montreal.md                  # Placeholder (Phase 3.1)
│   └── provinces/
│       └── ns.md                        # Nova Scotia defaults + rules
├── src/
│   └── utils/                           # Deterministic TS helpers (slug, validate,
│                                        # criteria, screen, index-md, collision, municipal)
├── docs/
│   └── phase-3-plan.md                  # Ingestion pipeline design + TDD plan
└── evaluations/
    ├── README.md                        # Folder conventions
    └── <property-slug>/                 # One per property (gitignored)
        ├── input.md
        ├── analysis.md
        ├── enhancements.md
        └── email-to-realtor.md
```

## Coverage today

- **Provinces:** Nova Scotia (full). Add yours by contributing
  `config/provinces/<code>.md` — see `CONTRIBUTING.md`.
- **Property types:** single-family, duplex, triplex, fourplex, mixed-use,
  condo. Scenarios are tuned for owner-occupy + 1 rental unit setups.
- **Listings sources:** the `evaluate-property` skill fetches URLs
  opportunistically (Viewpoint, realtor.ca) and falls back to asking
  you to paste the listing text when sites block. URL-aware source
  adapters + a `/ingest-listing` entry point are designed in
  [docs/phase-3-plan.md](docs/phase-3-plan.md) and are the next
  shipping target.
- **Financing:** Canadian semi-annual mortgage compounding, CMHC premiums up
  to $1.5M insurable cap, 5% / 10% / 20% down modeled, investment minimum
  20% for non-owner-occupied.
- **Does NOT cover:** US properties, commercial > 4 units, leasehold, new-
  construction warranty programs, pre-construction assignments, rent-to-own.

## Roadmap

- **Phase 3 · Mode A (in progress):** `/ingest-listing` skill + source
  adapters + criteria pre-screen + `INDEX.md` watchlist. Deterministic
  TS foundation (slug, validator, criteria parser + screener,
  index-md appender, collision detector, municipal loader) is
  shipped under `src/utils/` with 67 vitest cases. Still to build:
  the source-adapter prompts (`listings/sources/*.md`) and the
  orchestrating `.claude/skills/ingest-listing/SKILL.md`. See
  [docs/phase-3-plan.md](docs/phase-3-plan.md).
- **Phase 3.1 — after Mode A:** scheduled discovery ("Mode B") —
  daily scan of configured sources, criteria filter, auto-analyze
  matches, email / Telegram digest. Also Centris.ca (QC) adapter +
  `config/provinces/qc.md`.
- **Phase 2:** replace the AI for financial math with a deterministic
  TypeScript engine + unit tests (foundation already in `src/utils/`).

See `SPEC.md` for the full vision and `CONTRIBUTING.md` to help.

## Not financial advice

See `DISCLAIMER.md`. Consult a licensed mortgage broker, real estate lawyer,
CPA, and home inspector before any purchase decision.

## License

MIT. See `LICENSE`.
