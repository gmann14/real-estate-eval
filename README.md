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

`config/criteria.md` is gitignored. When present, it pre-screens every
ingest: listings that fail a hard filter are marked `reject` and skip
the full analysis, so you don't burn tokens on properties that don't
fit your mandate.

### 4. Ingest a listing

Ask Claude one of:

> /ingest-listing https://www.viewpoint.ca/property/12345

> /ingest-listing
> *(then paste the listing text when prompted)*

> Evaluate 123 Main St, Halifax — asking $450K duplex, 2BR + 1BR

The `ingest-listing` skill will:

1. Route to the right source adapter (Viewpoint, realtor.ca, paste, …)
2. Extract structured fields — address, price, units, year built, taxes,
   description — into a draft `evaluations/<slug>/input.md`
3. Check for an existing evaluation at that slug (collision: overwrite /
   v2 / diff / skip)
4. If `config/criteria.md` exists, pre-screen against your hard filters
5. Load the matching municipal config (e.g. `modl.md`, `hrm.md`) so the
   analysis picks up local tax and bylaw rules
6. Show a summary and wait for your confirmation
7. Delegate to `/evaluate-property` for the full analysis
8. Append a row to `evaluations/INDEX.md` as a running watchlist

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
│       ├── evaluate-property/           # Full analysis workflow
│       │   └── SKILL.md
│       └── ingest-listing/              # URL/paste → routed extraction → eval
│           └── SKILL.md
├── templates/
│   ├── evaluation-template.md           # Blank input
│   ├── analysis-template.md             # Analysis report skeleton
│   ├── enhancements-template.md         # ROI enhancement skeleton
│   └── sheet-design-reference.md        # Google Sheet export reference
├── listings/
│   └── sources/                         # Source adapters (paste, viewpoint, realtor.ca, …)
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
│   ├── ingest/                          # Tier-B extractor (Playwright + macOS Keychain)
│   │   ├── keychain.ts
│   │   ├── viewpoint-auth.ts
│   │   └── viewpoint-tier-b.ts
│   └── utils/                           # Deterministic TS helpers (slug, validate,
│                                        # criteria, screen, index-md, collision, municipal)
├── docs/
│   └── phase-3-plan.md                  # Ingestion pipeline design + TDD plan
└── evaluations/
    ├── README.md                        # Folder conventions
    ├── INDEX.md                         # Watchlist (created on first ingest; gitignored)
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
- **Listings sources:** viewpoint.ca (NS, primary), realtor.ca
  (Canada-wide, best-effort — falls back to paste on anti-bot blocks),
  centris.ca (QC, placeholder — routes to paste for now), raw paste
  (always works). See `listings/sources/`.
- **Financing:** Canadian semi-annual mortgage compounding, CMHC premiums up
  to $1.5M insurable cap, 5% / 10% / 20% down modeled, investment minimum
  20% for non-owner-occupied.
- **Does NOT cover:** US properties, commercial > 4 units, leasehold, new-
  construction warranty programs, pre-construction assignments, rent-to-own.

## Roadmap

- **Phase 3 · Mode A (shipped):** `/ingest-listing` skill + source
  adapters + criteria pre-screen + INDEX.md watchlist.
  See [docs/phase-3-plan.md](docs/phase-3-plan.md).
- **Phase 3.1 — next:** scheduled discovery ("Mode B") — daily scan of
  configured sources, criteria filter, auto-analyze matches, email /
  Telegram digest. Also Centris.ca (QC) adapter + `config/provinces/qc.md`.
- **Phase 2:** replace the AI for financial math with a deterministic
  TypeScript engine + unit tests (foundation already in `src/utils/`).

See `SPEC.md` for the full vision and `CONTRIBUTING.md` to help.

## Not financial advice

See `DISCLAIMER.md`. Consult a licensed mortgage broker, real estate lawyer,
CPA, and home inspector before any purchase decision.

## License

MIT. See `LICENSE`.
