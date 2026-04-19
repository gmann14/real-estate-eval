# Real Estate Investment Evaluation Tool — Specification

> A reusable, AI-powered framework for evaluating residential investment properties.
> Given a listing URL or manual input, produces a complete investment analysis report + Google Sheet.

**Version:** 0.1 (Draft Spec)
**Date:** March 20, 2026
**Gold Standard:** [9 Prince Street, Lunenburg analysis](evaluations/9-prince-street-lunenburg/analysis.md)

---

## ⚠️ Current Status vs. Full Spec

This document describes the **full target architecture**, including a
deterministic TypeScript engine that does not yet exist. What's built today is
a **markdown + Claude-Code-agent** framework that produces the same analysis
quality but relies on the agent (not compiled code) for financial math.

| Component | Current State | Target State |
|-----------|---------------|--------------|
| Input template | ✅ `templates/evaluation-template.md` | same |
| Analysis template | ✅ `templates/analysis-template.md` | same |
| Enhancement template | ✅ `templates/enhancements-template.md` | same |
| Province config (NS) | ✅ `config/provinces/ns.md` | same |
| CMHC config | ✅ `config/cmhc-premiums.md` | same |
| Default assumptions | ✅ `config/defaults.md` | same |
| Owner profile | ✅ example + gitignored personal | same |
| Agent workflow | ✅ `.claude/skills/evaluate-property/SKILL.md` | same + calls deterministic engine |
| Ingestion skill | ✅ `.claude/skills/ingest-listing/SKILL.md` (Mode A — paste/URL) | + Mode B scheduled scan |
| Source adapters | ✅ paste, viewpoint, realtor.ca (`listings/sources/`) | + centris.ca full |
| Tier-B extractor (login-gated VP fields) | ✅ `src/ingest/viewpoint-tier-b.ts` + Playwright + macOS Keychain | + realtor.ca / centris.ca analogues |
| Criteria pre-screen | ✅ `config/criteria.example.md` + agent logic | + TS `src/utils/criteria.ts` already in place |
| Deterministic helpers | 🟡 `src/utils/` (slug, validate, criteria, screen, index-md, collision, municipal) with vitest | + financial engine |
| Municipal configs | 🟡 MODL + HRM (NS); Montreal placeholder | + ON/BC/AB + per-borough QC |
| Watchlist | ✅ `evaluations/INDEX.md` auto-appended per ingest | + filter/sort views |
| Financial math | ❌ done by agent | TypeScript engine with unit tests (`src/analysis/*`) |
| Google Sheets export | ❌ not built | TypeScript module (`src/output/google-sheets.ts`) |
| Telegram TL;DR | ❌ not built | TypeScript module (`src/output/telegram.ts`) |
| CLI (`npx real-estate-eval`) | ❌ not built | Thin TypeScript CLI over the engine |
| Scheduled scan (Mode B) | ❌ not built | `.claude/scheduled/scan-listings.md` + notification |
| Multi-province | 🟡 NS only | Add files to `config/provinces/` |

**Read this spec as a roadmap.** Sections 2–9 describe what the tool will do
once Phase 2 (deterministic engine) and Phase 3 (personal-use features) are
built. Sections 3, 7, 8.1, and 10 describe what works today.

See the repo-level `README.md` for what's actually usable right now.

### Known gaps (as of 2026-04)

- **URL → analysis.md is not end-to-end automated.** The current flow is
  URL → `input.md` (via `/ingest-listing` + Tier-B extractor). The
  `analysis.md` file is still authored by the `/evaluate-property` agent
  across multiple passes. Full URL → analysis.md automation waits on
  Phase 2 (deterministic financial engine).
- **Zoning is not surfaced by any current adapter.** ViewPoint doesn't
  expose zoning in its Tier-A or Tier-B fields. Marked `[PROMPT USER]`
  in the input template until a MODL / HRM / municipal-GIS adapter is
  built (Phase 3.1 candidate).
- **Heritage designation is extracted heuristically** from listing
  description text (e.g., "Provincial Heritage Property" regex). Always
  flagged as "extracted — verify with municipality" in the analysis.
- **Listing agent is unreliable on non-VP brokerages** until the
  extractor is cross-verified against the `LISTED BY` brokerage field.
  Fix in progress — see [docs/tdd-fix-plan.md](docs/tdd-fix-plan.md).
- **`src/ingest/` lacks unit tests** — being backfilled; see the TDD
  fix plan document.

---

---

## Table of Contents

1. [Overview](#1-overview)
2. [Architecture](#2-architecture)
3. [Input System](#3-input-system)
4. [Core Analysis Engine](#4-core-analysis-engine)
5. [Regulation Module](#5-regulation-module)
6. [ROI Enhancement Module](#6-roi-enhancement-module)
7. [Owner Profile System](#7-owner-profile-system)
8. [Output Formats](#8-output-formats)
9. [Data Sources](#9-data-sources)
10. [Open-Source Structure](#10-open-source-structure)
11. [MVP vs Full Version](#11-mvp-vs-full-version)
12. [Edge Cases & Limitations](#12-edge-cases--limitations)
13. [Stress Test of This Spec](#13-stress-test-of-this-spec)

---

## 1. Overview

### What This Tool Does

Takes a property listing (URL or manual data) and produces a comprehensive investment analysis covering:

- Every financing scenario with real monthly costs
- Owner-occupy vs. pure investment vs. hybrid scenarios
- 10-year return projections with annualized ROI
- Rent-vs-buy crossover analysis
- Risk matrix and stress tests
- Regulatory landscape (STR bylaws, zoning, heritage)
- ROI enhancement recommendations specific to the property
- Tax implications (Canadian context)
- Bottom-line recommendation with max price calculations
- Questions to ask the seller

### What This Tool Is NOT

- Not a property search tool (you bring the listing)
- Not a mortgage broker (it models scenarios, doesn't originate loans)
- Not legal or tax advice (it flags considerations, says "talk to your accountant")
- Not an automated scraper farm (it uses AI agents + available APIs, not bulk scraping)

### How It Works

```
┌─────────────┐     ┌──────────────┐     ┌───────────────┐     ┌──────────┐
│  Input       │ ──▶ │  AI Agent    │ ──▶ │  Analysis     │ ──▶ │  Output  │
│  (URL/manual)│     │  (data       │     │  Engine       │     │  (MD,    │
│              │     │   gathering) │     │  (calculations│     │   Sheet, │
│              │     │              │     │   + narrative) │     │   TL;DR) │
└─────────────┘     └──────────────┘     └───────────────┘     └──────────┘
                           │                      │
                    ┌──────┴──────┐        ┌──────┴──────┐
                    │ Data Sources│        │ Modules     │
                    │ (listing,   │        │ (regulation,│
                    │  comps,     │        │  ROI enhance│
                    │  municipal) │        │  ment, tax) │
                    └─────────────┘        └─────────────┘
```

The tool is an **AI agent orchestration framework**. A sub-agent reads the listing, gathers data from configured sources, runs calculations through deterministic financial models, and produces a narrative report. The AI handles data gathering + narrative; the math is deterministic code.

---

## 2. Architecture

### Directory Structure

```
real-estate-eval/
├── SPEC.md                          # This file
├── README.md                        # Usage guide
├── config/
│   ├── owner-profile.yaml           # Personal config (gitignored)
│   ├── owner-profile.example.yaml   # Template for new users
│   ├── cmhc-premiums.yaml           # CMHC insurance premium table
│   ├── provinces/
│   │   ├── ns.yaml                  # Nova Scotia tax rates, rules, programs
│   │   ├── on.yaml                  # Ontario
│   │   ├── bc.yaml                  # British Columbia
│   │   └── ...                      # Other provinces
│   └── defaults.yaml                # Default assumptions (appreciation, inflation, etc.)
├── src/
│   ├── input/
│   │   ├── parser.ts                # Listing URL parser (realtor.ca, viewpoint, etc.)
│   │   ├── manual-input.ts          # Interactive manual input prompts
│   │   └── schema.ts                # Property input data schema/validation
│   ├── analysis/
│   │   ├── financing.ts             # Mortgage calculations, CMHC, closing costs
│   │   ├── scenarios.ts             # Scenario generator (owner-occupy, LTR, STR, hybrid)
│   │   ├── projections.ts           # Multi-year return projections
│   │   ├── rent-vs-buy.ts           # Rent-vs-buy crossover analysis
│   │   ├── risk.ts                  # Risk matrix and stress tests
│   │   └── tax.ts                   # Tax implications engine
│   ├── regulation/
│   │   ├── municipality.ts          # Municipal regulation lookup
│   │   ├── provincial.ts            # Provincial rules engine
│   │   └── registry.ts              # Known regulation database
│   ├── enhancement/
│   │   ├── quick-wins.ts            # < $5K improvements
│   │   ├── medium-investments.ts    # $5K-$25K improvements
│   │   ├── major-value-adds.ts      # $25K+ improvements
│   │   ├── revenue-strategy.ts      # Revenue optimization suggestions
│   │   └── feasibility.ts           # Property-specific feasibility checks
│   ├── output/
│   │   ├── markdown.ts              # Markdown report generator
│   │   ├── google-sheets.ts         # Google Sheets export
│   │   └── telegram.ts              # TL;DR summary formatter
│   └── agent/
│       ├── orchestrator.ts          # Main agent workflow
│       ├── data-gatherer.ts         # AI agent for pulling comps, municipal data
│       └── narrative.ts             # AI agent for report narrative sections
├── evaluations/
│   └── [property-slug]/
│       ├── input.md                 # Raw input data
│       ├── analysis.md              # Full analysis report
│       ├── enhancements.md          # ROI enhancement recommendations
│       └── sheet-link.md            # Google Sheet URL
├── tests/
│   ├── financing.test.ts            # Unit tests for mortgage math
│   ├── scenarios.test.ts            # Scenario calculation tests
│   ├── projections.test.ts          # Projection accuracy tests
│   └── fixtures/                    # Test properties with known-good outputs
│       └── 9-prince-street.json     # Gold standard fixture
└── scripts/
    ├── evaluate.ts                  # CLI entry point
    └── batch-evaluate.ts            # Run multiple properties
```

### Tech Stack

- **Language:** TypeScript (Node.js)
- **AI Agent:** OpenClaw sub-agent (Claude) for data gathering + narrative
- **Calculations:** Deterministic TypeScript — no AI for math
- **Config:** YAML for human-editable configs, JSON for data
- **Google Sheets:** Google Sheets API v4 (service account or OAuth)
- **Testing:** Vitest

### Design Principles

1. **AI for intelligence, code for math.** The AI agent gathers data and writes narrative. Financial calculations are deterministic functions with unit tests.
2. **Config-driven.** Province-specific rules, tax rates, and CMHC tables are config files, not hardcoded. Adding a new province = adding a YAML file.
3. **Scenario-based.** Every property gets analyzed under multiple scenarios. The user doesn't pick one — they see all of them and decide.
4. **Conservative by default.** All assumptions err toward conservative. Appreciation at 3%, not 5%. Vacancy at 5%, not 2%. The user can override.
5. **Reproducible.** Given the same inputs, the tool produces the same outputs. AI narrative may vary, but all numbers are deterministic.

---

## 3. Input System

### Input Methods

#### Method 1: Listing URL

```bash
npx real-estate-eval https://www.realtor.ca/real-estate/...
```

The agent scrapes the listing page and extracts structured data. Supported sources:

| Source | Coverage | Data Quality |
|--------|----------|-------------|
| realtor.ca | National (Canada) | High — structured MLS data |
| viewpoint.ca | Nova Scotia | High — includes assessment history, sales history |
| centris.ca | Quebec | High — structured |
| Manual fallback | Anywhere | User provides data via prompts |

#### Method 2: Manual Input

```bash
npx real-estate-eval --manual
```

Interactive prompts walk the user through entering property details. Also accepts a pre-filled `input.md` or `input.yaml` file:

```bash
npx real-estate-eval --input ./my-property/input.yaml
```

### Input Data Schema

Every evaluation requires this minimum data (asterisks = required):

```yaml
# Property Basics
address*: "9 Prince Street, Lunenburg, NS B0J2C0"
asking_price*: 499900
type*: duplex                    # single | duplex | triplex | fourplex | mixed-use | condo
year_built: 1761
lot_size_acres: 0.0517
previous_sale_price: 395000
previous_sale_date: "2022-07-29"

# Units (array — one entry per unit)
units*:
  - name: "Main Unit"
    bedrooms*: 2
    bathrooms: 1
    sq_ft: null                  # If unknown
    level: "main"
    has_kitchen: true
    has_laundry: false
    separate_entrance: true
    current_use: "str"           # owner | ltr | str | vacant
    current_rent: null           # If LTR
    airbnb_url: null             # If STR, for pulling actual data
  - name: "Studio"
    bedrooms*: 0
    bathrooms: 1
    sq_ft: null
    level: "main"
    has_kitchen: true
    has_laundry: false
    separate_entrance: true
    current_use: "str"

# Building Features
heating_type: "oil + heat pump"
roof_type: "metal"
foundation_type: "stone"
parking: "gravel, 2 spots"
heritage_designated: true
recent_renovations:
  - "new siding"
  - "updated plumbing"
  - "updated electrical"
  - "new kitchens and baths"

# Municipal
municipality: "Town of Lunenburg"
province*: "NS"
water_sewer: "municipal"

# Optional Overrides (if user has better numbers than defaults)
property_tax_override: 5504
insurance_override: 2400
heating_cost_override: 2800
electricity_override: 2400

# Agent / Seller Info
listing_agent: "Mark Seamone & Cheri Young"
agent_phone: "902-521-5752"
days_on_market: 0
```

### Data Enrichment (Agent-Driven)

After parsing input, the AI agent enriches it with:

1. **Comparable rentals** — searches Kijiji, rentals.ca, Facebook Marketplace for similar units in the area
2. **Comparable Airbnb listings** — searches AirDNA or Airbnb directly for ADR/occupancy data
3. **Municipal tax rate** — looks up from PVSC or municipal website
4. **Property assessment** — PVSC assessed value
5. **Current mortgage rates** — best available 5-year fixed from rate comparison sites
6. **Recent sales** — comparable properties sold in last 12 months

The agent stores enriched data alongside the input for reproducibility.

---

## 4. Core Analysis Engine

This is the heart of the tool. Every calculation described here is deterministic code, not AI-generated.

### 4.1 Financing Calculator

**Inputs:** Purchase price, down payment %, mortgage rate, amortization period, province

**Outputs:**

| Field | Calculation |
|-------|-------------|
| Down payment ($) | Price × down% |
| CMHC premium | Lookup from `cmhc-premiums.yaml` based on down%, LTV, price bracket |
| Total mortgage | (Price - down) + CMHC premium |
| Monthly payment | Canadian mortgage formula (semi-annual compounding) |
| Annual payment | Monthly × 12 |

**CMHC Rules to Encode:**

```yaml
# config/cmhc-premiums.yaml
rules:
  max_price: 1499999              # CMHC insurable limit as of 2025
  min_down_payment:
    - { up_to: 500000, rate: 0.05 }
    - { from: 500001, to: 1499999, rate: 0.10 }  # On the portion above $500K
  premiums:
    - { ltv_min: 0.8001, ltv_max: 0.85, rate: 0.028 }   # 15-19.99% down
    - { ltv_min: 0.8501, ltv_max: 0.90, rate: 0.031 }   # 10-14.99% down
    - { ltv_min: 0.9001, ltv_max: 0.95, rate: 0.040 }   # 5-9.99% down
  owner_occupy_required: true     # CMHC only for owner-occupied
  max_amortization_insured: 25    # 30yr only for uninsured
  multi_unit_rules:
    duplex: { max_ltv: 0.95 }     # Owner-occupy duplex ok at 5% down
    triplex: { max_ltv: 0.90 }    # Triplex needs 10% down minimum
    fourplex: { max_ltv: 0.90 }   # Fourplex needs 10% down minimum
    non_owner: { max_ltv: 0.80 }  # Investment property = 20% minimum
```

**Canadian Mortgage Math:**

```
Semi-annual rate = (1 + annual_rate/2)^(1/6) - 1
Monthly payment = P × r × (1+r)^n / ((1+r)^n - 1)
where P = principal, r = monthly rate, n = months
```

This is NOT the same as US monthly compounding. Must use semi-annual compounding convention.

**Financing Scenarios to Always Generate:**

| Scenario | Down % | CMHC? | Notes |
|----------|--------|-------|-------|
| Low leverage | 5% | Yes | Minimum cash, maximum leverage |
| Medium leverage | 10% | Yes | Lower CMHC premium |
| Conventional | 20% | No | No insurance, lower monthly |
| Investment minimum | 20% | No | Required for non-owner-occupied |

For properties over $500K (up to $1.5M), calculate the split down payment (5% on first $500K + 10% on remainder).

### 4.2 Closing Cost Calculator

**Province-specific. Loaded from config.**

```yaml
# config/provinces/ns.yaml (excerpt)
closing_costs:
  deed_transfer_tax:
    type: "flat_rate"
    rate: 0.015                   # 1.5% in most NS municipalities
    municipal_variations:
      halifax: 0.015
      lunenburg: 0.015
  legal_fees:
    range: [2000, 3500]
    default: 2500
  home_inspection:
    range: [400, 700]
    default: 500
  appraisal:
    required_for: "insured"       # Only needed for CMHC-insured
    cost: 350
  title_insurance:
    cost: 350
  pst_on_cmhc:                   # Some provinces charge PST on CMHC premium
    applicable: false
```

**Output:** Table of closing costs per scenario + total cash to close.

### 4.3 Operating Expense Estimator

**Method:** Start with defaults from provincial config, override with user-provided actuals.

| Expense | Default Source | Override Method |
|---------|---------------|-----------------|
| Property tax | PVSC assessment × municipal rate | User provides actual bill |
| Insurance | Estimate by property type + age + heritage | User provides quote |
| Heating | Climate zone × sq_ft × heating_type | User provides actual bills |
| Electricity | Province avg × unit count | User provides actual bills |
| Water/sewer | Municipal rate schedule | User provides actual bills |
| Internet | $90/mo default if landlord-provided | User override |
| Snow removal | Climate zone default | User override |
| Lawn/grounds | Lot size based | User override |
| Maintenance reserve | 0.5-1.0% of property value/yr (higher for older/heritage) | Configurable % |
| CapEx reserve | 0.3-0.7% of property value/yr | Configurable % |
| Accounting | $800/yr if rental income | Only if rental scenarios |

**Heritage/Age Adjustment:**

```
maintenance_multiplier:
  built_before_1900: 1.5
  built_1900_1950: 1.3
  built_1950_1980: 1.1
  built_after_1980: 1.0
  heritage_designated: +0.2 additional
```

### 4.4 Revenue Estimator

#### Long-Term Rental (LTR)

For each unit:
```
monthly_ltr_gross = comparable_rent (from comps or user input)
monthly_ltr_net = monthly_ltr_gross × (1 - vacancy_rate)
annual_ltr_net = monthly_ltr_net × 12
```

Default vacancy: 5% (tight market) to 8% (softer market). Configurable.

#### Short-Term Rental (STR / Airbnb)

For each unit:
```
annual_str_gross = ADR × 365 × occupancy_rate
platform_fees = annual_str_gross × platform_fee_rate (default 3% host-only)
cleaning_revenue = cleaning_fee × turnovers_per_year  # Charged to guests
cleaning_costs = cleaning_cost × turnovers_per_year   # Paid to cleaner
supplies = $750/unit/year (default)
furnishing_amortized = furnishing_cost / amortization_years (default 5)
str_registration = province-specific annual fee

annual_str_net = annual_str_gross - platform_fees - cleaning_costs + cleaning_revenue - supplies - furnishing_amortized - str_registration
monthly_str_net = annual_str_net / 12
```

**Turnover estimation:**
```
avg_stay_nights = estimate by unit type:
  studio: 2.5-3 nights
  1-bed: 3-4 nights
  2-bed: 3.5-4.5 nights
  3+ bed: 4-6 nights

turnovers_per_year = (365 × occupancy_rate) / avg_stay_nights
```

**Seasonal variant (summer-only STR):**
```
active_months = user-defined (default 6, May-Oct)
seasonal_occupancy = higher rate during active months (default +10-15%)
annual_str_net = (monthly_str_net_at_seasonal_occ × active_months) + 0 for inactive months
monthly_str_net_annualized = annual_str_net / 12
```

#### STR Breakeven Occupancy

Calculate the occupancy rate where STR net = LTR net:

```
ADR × 365 × X × (1 - platform_fee) - variable_costs(X) = annual_ltr_net
Solve for X
```

This is a key decision metric. If breakeven occupancy is below 30%, STR is almost always the right call.

### 4.5 Scenario Generator

For a given property, automatically generate all applicable scenarios:

| Scenario | Applies When | Description |
|----------|-------------|-------------|
| **Owner + LTR** | Multi-unit | Owner occupies largest unit, rent remaining units as LTR |
| **Owner + STR** | Multi-unit | Owner occupies largest unit, remaining units as STR |
| **Owner + Hybrid** | Multi-unit | Owner occupies largest unit, remaining as STR in summer / LTR in winter |
| **Pure LTR** | Any | All units as LTR (investment property) |
| **Pure STR** | Any | All units as STR (investment property) |
| **Dual Occupancy** | Multi-unit | Multiple family members / co-owners occupy units |
| **House Hack** | Single w/ suite potential | Owner occupies, rents room/basement |
| **Owner-Occupy Single** | Single family | Owner lives there, no rental income |

For each scenario, calculate:
- Monthly out-of-pocket (owner scenarios) or monthly cashflow (investor scenarios)
- Annual net operating income
- Cash-on-cash return (year 1)
- Which financing options are available (CMHC restrictions by scenario)

**Output:** A comparison table like the Prince Street analysis — all scenarios side by side with both financing levels.

### 4.6 Multi-Year Projection Engine

For each scenario, project years 1, 3, 5, 7, and 10:

```yaml
growth_assumptions:
  rent_increase_annual: 0.03       # 3% (check if province has rent control)
  adr_increase_annual: 0.03        # 3% STR rate growth
  expense_inflation: 0.025         # 2.5% CPI
  property_appreciation: 0.03      # 3% conservative
  selling_costs: 0.05              # 5% of sale price (agent + legal)
```

**For each projection year, calculate:**

| Metric | Formula |
|--------|---------|
| Property value | purchase_price × (1 + appreciation)^year |
| Mortgage balance | Amortization schedule lookup |
| Gross equity | property_value × (1 - selling_costs) - mortgage_balance |
| Cumulative rental income | Sum of annual net income with growth |
| Cumulative housing costs | Sum of annual costs with inflation |
| Net rental benefit | cumulative_income - cumulative_costs (for owner scenarios) |
| Total return | gross_equity + net_rental_benefit - total_cash_invested |
| Annualized ROI | (total_return / cash_invested)^(1/years) - 1 |

**Amortization schedule:** Must use Canadian semi-annual compounding. Generate a full 25/30-year schedule and store it for lookups.

### 4.7 Rent-vs-Buy Analysis

**The question:** "If I rent instead and invest my down payment + monthly savings in index funds, when does buying pull ahead?"

**Renter's wealth accumulation:**

```
initial_investment = total_cash_to_close + one_time_furnishing_costs
monthly_savings = max(0, monthly_cost_of_owning - monthly_cost_of_renting)
market_return = 0.07  # 7% annual nominal return on index funds

renter_wealth(year) = future_value(initial_investment, market_return, year)
                    + future_value_of_annuity(monthly_savings, market_return/12, year×12)
```

**Buyer's net equity:**

```
buyer_equity(year) = property_value(year) × 0.95 - mortgage_balance(year)
```

**Crossover:** Find the month where buyer_equity > renter_wealth. Report as "Buying beats renting at month X (~Y years)."

**Sensitivity:** Run at 5%, 7%, and 9% market returns to show range.

### 4.8 Risk Matrix

#### Static Risk Assessment

For each property, evaluate and rate (Low / Medium / High severity × Low / Medium / High likelihood):

| Risk Category | Factors |
|---------------|---------|
| **Structural** | Age, foundation type, heritage status, recent renovations |
| **Market** | Location liquidity, market cycle position, recent price trends |
| **Interest rate** | Current rate vs historical average, years to renewal |
| **Regulatory** | STR bylaw status, zoning, heritage restrictions |
| **Vacancy / Tenant** | Local vacancy rates, rental demand, rent control |
| **Insurance** | Heritage, age, flood zone, coastal |
| **Operational** | Self-manage vs. property management, distance from owner |

Each risk gets a severity, likelihood, and specific mitigation strategy.

#### Quantitative Stress Tests

Run four mandatory stress tests and report the impact on monthly costs:

**1. Low occupancy (STR at 40% instead of base):**
```
Recalculate STR revenue at 40% occupancy
Report new monthly cost and delta from base
```

**2. Rate increase at renewal (base + 2%):**
```
At year 5, recalculate monthly payment with (base_rate + 2%)
on remaining mortgage balance with remaining amortization
Report new monthly cost and delta
```

**3. Flat market (0% appreciation):**
```
Recalculate year-5 and year-10 equity with 0% appreciation
Compare total return to renting alternative
```

**4. Combined stress (low occupancy + rate increase):**
```
Apply both #1 and #2 simultaneously
Report monthly cost and whether the investment is still survivable
Include fallback analysis: "If you convert STR to LTR in this scenario, costs become $X/mo"
```

### 4.9 Tax Engine

**Canadian-specific. Province-pluggable.**

#### Rental Income (T776)

When any unit is rented:
```
Deductible expenses (proportional to rental sq_ft / total sq_ft):
  - Mortgage interest (not principal)
  - Property tax
  - Insurance
  - Utilities
  - Maintenance / repairs
  - Accounting fees
  - Advertising
  - Optional: CCA (capital cost allowance)

taxable_rental_income = gross_rent - deductible_expenses
tax_impact = taxable_rental_income × marginal_rate (from owner profile)
```

#### Principal Residence Exemption

```
if owner_occupied:
  owner_unit_portion = owner_sq_ft / total_sq_ft
  exempt_gain = total_gain × owner_unit_portion
  taxable_gain = total_gain × (1 - owner_unit_portion)
  capital_gains_tax = taxable_gain × 0.5 × marginal_rate  # 50% inclusion (first $250K)
                    + max(0, taxable_gain - 250000) × 0.667 × marginal_rate  # 66.7% inclusion above $250K
```

#### GST/HST on STR

```
if annual_str_gross > 30000:
  must_register_for_gst_hst = true
  hst_rate = province.hst_rate  # 15% in NS
  # Complex: may be able to claim ITCs on expenses
  flag: "STR revenue exceeds $30K threshold — GST/HST registration likely required. Consult accountant."
```

#### First-Time Buyer Programs

If owner profile indicates first-time buyer:
```
federal:
  - Home Buyers' Plan (HBP): withdraw up to $60K from RRSP tax-free for down payment
  - First Home Savings Account (FHSA): up to $40K tax-deductible savings
  - Home Buyers' Tax Credit: $10K non-refundable credit ($1,500 tax reduction)

provincial (NS):
  - No additional first-time buyer rebate as of 2025
  - Down Payment Assistance Program (income-qualified)
```

### 4.10 Bottom Line Generator

Synthesize all analysis into:

**1. Price opinion by scenario:**
```
For each scenario, calculate the maximum purchase price where:
  - 5-year annualized ROI > hurdle_rate (default 7%, the index fund alternative)
  - Monthly out-of-pocket < equivalent_rent × 1.5 (owner scenarios)
  - Cash-on-cash return > 0% in year 1 (investor scenarios)
```

**2. Recommendation matrix:**

| Price Range | Verdict | Rationale |
|-------------|---------|-----------|
| Below X | Strong buy | Numbers work for all scenarios |
| X to Y | Fair deal | Primary scenario works, investor scenarios marginal |
| Y to Z | Marginal | Only works if [specific conditions] |
| Above Z | Pass | Numbers don't support at any scenario |

**3. Questions to ask the seller/agent:**

Auto-generated based on property characteristics:
- Heritage property → ask about designation restrictions, structural assessments
- STR units → ask for 12+ months of booking data
- Recent sale → ask why selling, what improvements were made
- Old building → ask about foundation, insulation, electrical panel age
- Multi-unit → ask about separate metering, tenant agreements
- Always: insurance quotes, actual utility bills, zoning confirmation

---

## 5. Regulation Module

### Purpose

Automatically detect and report regulatory factors that affect the investment thesis. This is critical for STR-dependent scenarios — a single bylaw can kill the entire revenue model.

### Municipality Detection

```
Input: property address
Steps:
  1. Parse municipality from address (postal code → municipality mapping)
  2. Check config/municipalities/ for known regulation data
  3. If not found, flag for AI agent to research
```

### Regulation Checks

For each property, research and report:

| Category | What to Check | Impact |
|----------|--------------|--------|
| **STR Bylaws** | Is STR permitted? Licensed? Restricted to primary residence? Cap on licenses? | Can kill STR scenarios entirely |
| **Zoning** | Residential, mixed-use, commercial? Multi-unit permitted? | Affects unit conversion possibilities |
| **Heritage Designation** | Federal, provincial, or municipal heritage? What restrictions? | Limits renovations, may require approval for changes |
| **Building Permits** | What requires a permit in this municipality? ADU regulations? | Affects ROI enhancement feasibility |
| **STR Registration** | Required? Cost? Annual renewal? | Operating cost + compliance burden |
| **Rent Control** | Province has rent control? Vacancy decontrol? Annual cap? | Affects LTR revenue projections |
| **Eviction Rules** | Notice periods, grounds for eviction, tenant protections | Risk factor for LTR scenarios |
| **Deed Transfer Tax** | Municipal rate, any exemptions (first-time buyer, etc.) | Closing cost calculation |

### Provincial Rules Database

```yaml
# config/provinces/ns.yaml
str_rules:
  registration_required: true
  registration_body: "Tourism Nova Scotia"
  registration_act: "Tourism Accommodation Registration Act"
  registration_cost: 50                # Annual
  primary_residence_restriction: false  # NS does not restrict to primary residence (as of 2025)
  platform_tax_collection: true         # Airbnb collects marketing levy in NS

rent_control:
  active: false                         # NS rent control ended Dec 31, 2025
  vacancy_decontrol: true
  notes: "No rent control. Landlord can increase rent with 4 months notice, any amount."

eviction:
  notice_period_months: 2               # For no-fault eviction
  grounds: ["non-payment", "breach", "landlord-use", "renovation", "demolition"]
  tribunal: "Residential Tenancies Program"

tax:
  deed_transfer_tax_rate: 0.015
  hst_rate: 0.15
  income_tax_brackets:                  # Provincial brackets (federal is separate)
    - { up_to: 29590, rate: 0.0879 }
    - { up_to: 59180, rate: 0.1495 }
    - { up_to: 93000, rate: 0.1667 }
    - { up_to: 150000, rate: 0.175 }
    - { above: 150000, rate: 0.21 }
```

### Red Flag System

The regulation module outputs a prominent red-flags section:

```
🔴 RED FLAGS:
  - None detected

🟡 CAUTION:
  - Heritage designation — renovations require municipal approval
  - STR registration required — $50/yr, register before listing

🟢 FAVORABLE:
  - No rent control — can adjust LTR rents freely
  - No STR restrictions — both units can operate as STR
  - No pending bylaw changes detected (as of [date])
```

---

## 6. ROI Enhancement Module

### Purpose

For each property, analyze what specific improvements could boost returns and estimate the ROI of each. This turns the tool from "should I buy this?" into "how do I maximize this?"

### Enhancement Categories

#### 6a. Quick Wins (< $5K, Immediate Impact)

| Enhancement | Est. Cost | Expected Impact | Payback Period | Risk |
|-------------|-----------|-----------------|----------------|------|
| **Professional STR photos** | $300-$800 | +15-25% ADR boost, +10% occupancy | 1-2 months | Very low |
| **Listing copy optimization** | $0-$200 | +5-10% conversion rate | Immediate | None |
| **Dynamic pricing tool** (PriceLabs, Wheelhouse) | $20-40/mo per listing | +10-20% revenue optimization | 1 month | Very low |
| **Keyless entry** (smart locks) | $200-$400/lock | Enables self-check-in, saves key handoff time | 3-6 months | Low |
| **Smart thermostat** | $200-$300 | 10-15% heating cost reduction | 12-18 months | Low |
| **Noise monitor** (Minut, NoiseAware) | $150-$200 + $10/mo | Prevents neighbor complaints, protects investment | Indirect | Low |
| **Quality linens + towels** | $500-$1,500/unit | +$10-20 ADR, better reviews | 3-6 months | Very low |
| **Welcome package setup** | $100-$300 setup + $10-20/guest | Better reviews → higher ranking → more bookings | 2-4 months | Very low |
| **Interior paint refresh** | $1,000-$3,000 | Improved photos, higher ADR | 6-12 months | Low |
| **Updated fixtures + lighting** | $500-$2,000 | Better aesthetics, photo appeal | 6-12 months | Low |

#### 6b. Medium Investments ($5K-$25K)

| Enhancement | Est. Cost | Expected Impact | Payback Period | Risk | Feasibility Check |
|-------------|-----------|-----------------|----------------|------|-------------------|
| **Hot tub** | $5,000-$12,000 installed | +$30-60 ADR, huge in maritime/rural markets | 12-24 months | Medium (maintenance, liability) | Need outdoor space, electrical capacity, insurance rider |
| **Outdoor sauna** | $5,000-$15,000 | +$25-50 ADR, year-round appeal | 12-24 months | Medium | Need outdoor space, setback compliance |
| **Deck / patio** | $5,000-$15,000 | +$15-30 ADR, outdoor living space | 18-36 months | Low | Check heritage restrictions, lot coverage limits |
| **Fire pit area** | $1,000-$5,000 | +$10-20 ADR, especially for groups | 6-12 months | Low | Municipal fire regulations, setbacks |
| **Kitchen refresh** | $8,000-$20,000 | +$20-40 ADR, much better photos | 18-36 months | Low | Heritage approval if designated |
| **Bathroom refresh** | $5,000-$15,000 | +$15-30 ADR, cleanliness perception | 18-36 months | Low | Heritage approval if designated |
| **Insulation upgrade** | $5,000-$15,000 | 20-40% heating cost reduction | 24-48 months | Very low | Heritage restrictions on exterior changes |
| **EV charger (Level 2)** | $2,000-$5,000 installed | +$10-15 ADR, growing demand, differentiator | 24-48 months | Low | Need 240V electrical capacity, parking |
| **In-unit laundry** | $3,000-$8,000 | +$10-20 ADR, reduces turnover friction | 18-36 months | Low | Need plumbing access, space |

#### 6c. Major Value-Adds ($25K+)

| Enhancement | Est. Cost | Expected Impact | Payback Period | Risk | Feasibility Check |
|-------------|-----------|-----------------|----------------|------|-------------------|
| **ADU (accessory dwelling unit)** | $50,000-$150,000 | +$1,000-$2,500/mo revenue (new unit) | 36-72 months | High | Zoning, lot size, setbacks, services capacity |
| **Basement conversion** | $30,000-$80,000 | +$800-$1,500/mo revenue | 36-60 months | High | Ceiling height, moisture, egress windows, code |
| **Garage conversion** | $25,000-$60,000 | +$800-$1,200/mo revenue | 36-60 months | Medium | Zoning, loss of parking, permits |
| **Addition/extension** | $100,000-$300,000+ | Increased property value + revenue | 60-120 months | High | Heritage restrictions, zoning, engineering |
| **Full energy retrofit** | $25,000-$60,000 | 40-60% energy cost reduction, rebates available | 48-84 months | Low | May qualify for Greener Homes Grant, provincial rebates |
| **Heat pump upgrade** | $5,000-$15,000 | Replace oil heat, 30-50% cost reduction | 24-48 months | Low | Sizing, electrical capacity, NS rebates available |
| **Solar panels** | $15,000-$30,000 | Offset electricity, net metering | 72-120 months | Low | Roof orientation, heritage restrictions, NS Power net metering |

#### 6d. Revenue Strategy Optimizations

| Strategy | Setup Cost | Expected Impact | Risk |
|----------|-----------|-----------------|------|
| **Seasonal pricing** | $0 (time only) | +10-20% annual revenue | Low — just pricing intelligence |
| **Mid-term rentals** (1-3 month stays) | $0-$500 (Furnished Finder listing) | More stable income, lower turnover costs, winter occupancy | Low — reduces management burden |
| **Experience packages** | $200-$500 (partnerships) | +$20-50 per booking, differentiation | Low — no capital required |
| **Pet-friendly premium** | $200-$500 (covers, cleaners) | +$25-50/stay fee, wider market reach | Low-Medium (damage risk, mitigated by deposit) |
| **Event hosting** | $1,000-$5,000 (setup/permits) | +$500-$2,000/event | Medium — liability, neighbor relations, permits |
| **Multi-platform listing** | $0 (time + management) | +15-25% occupancy from wider reach | Low — channel manager recommended ($10-30/mo) |
| **Direct booking website** | $500-$2,000 setup | Save 3-15% platform fees on repeat guests | Low — long-term play |

### Enhancement Output Format

For each property evaluation, the enhancement module produces:

```markdown
## ROI Enhancement Analysis

### Property-Specific Feasibility Summary
- Lot size: 0.0517 acres (small — ADU unlikely)
- Heritage designated: Yes (renovation approvals required)
- Zoning: Residential
- Parking: 2 gravel spots (EV charger feasible)
- Outdoor space: Limited (small lot constrains hot tub/sauna)
- Basement: Full unfinished, stone foundation (conversion unlikely due to heritage + stone)

### Recommended Enhancements (Priority Order)

#### Tier 1 — Do Immediately (ROI > 200% year 1)
1. Professional photos: $500 → +$3,000-$5,000/yr revenue
2. Dynamic pricing tool: $480/yr → +$4,000-$6,000/yr revenue
3. Keyless entry: $400 → operational efficiency + guest satisfaction
...

#### Tier 2 — Do Within 6 Months (ROI > 100% year 1)
...

#### Tier 3 — Consider for Year 2+ (ROI > 50% by year 2)
...

### Enhancement ROI Summary Table
| Enhancement | Cost | Annual Impact | Payback | Feasible? | Notes |
...

### Total Enhancement Potential
- Combined Tier 1 investment: $X
- Expected annual revenue increase: $Y
- New monthly STR net (post-enhancements): $Z (vs. $W baseline)
- Revised scenario B monthly cost: $V
```

### Feasibility Scoring

Each enhancement gets a feasibility score (0-100) based on property-specific factors:

```typescript
interface FeasibilityCheck {
  enhancement: string;
  score: number;           // 0-100
  blockers: string[];      // e.g., ["Heritage designation requires approval"]
  requirements: string[];  // e.g., ["240V electrical", "2 parking spots"]
  applicable: boolean;     // false if property can't support this at all
}
```

Factors affecting feasibility:
- Lot size (too small for ADU/sauna/hot tub?)
- Heritage designation (approval required for exterior changes?)
- Zoning (ADU permitted? Short-term rental permitted?)
- Building characteristics (basement ceiling height? Foundation type?)
- Municipal regulations (fire pit allowed? Noise bylaws?)
- Electrical capacity (EV charger? Heat pump?)
- Budget alignment with owner profile risk tolerance

---

## 7. Owner Profile System

### Purpose

Personalize analysis based on the buyer's specific situation. Different buyers have different priorities: a first-time buyer cares about CMHC and first-time programs; an experienced investor cares about cash-on-cash return and portfolio diversification.

### Profile Schema

```yaml
# config/owner-profile.yaml (gitignored — private)

personal:
  name: "Graham Mann"
  province: "NS"
  municipality: "Halifax"              # Where owner currently lives/pays tax
  
financial:
  annual_income: null                  # Used for tax bracket estimation
  marginal_tax_rate: 0.43             # Or provide income and calculate
  risk_tolerance: "moderate"          # conservative | moderate | aggressive
  investment_horizon_years: 7          # How long they plan to hold
  liquid_capital_available: null       # For down payment + reserves
  
real_estate:
  existing_properties: 0               # Number of properties owned
  first_time_buyer: true               # Enables first-time buyer programs
  primary_residence_owned: false       # Affects CMHC eligibility
  
preferences:
  preferred_scenarios:                 # Which scenarios to emphasize
    - "owner_occupy_str"
    - "owner_occupy_ltr"
  self_manage: true                    # false adds property management fee (typically 10-20%)
  min_cash_on_cash: 0.05              # 5% minimum acceptable year-1 return
  max_monthly_housing_cost: null       # Hard limit on what they'll spend monthly
  hurdle_rate: 0.07                   # Index fund alternative return rate
  
tax:
  rrsp_room: null                     # Available for HBP
  fhsa_balance: null                  # First Home Savings Account
  corporation_owned: false             # Buying through a corp changes tax treatment
  
notes: |
  First investment property consideration.
  Currently renting. Open to owner-occupying a multi-unit.
  Interested in Lunenburg/South Shore area.
```

### Default Profile

Ships with a generic default profile for someone who doesn't want to configure everything:

```yaml
# config/owner-profile.example.yaml
personal:
  province: "ON"                       # Most common
financial:
  marginal_tax_rate: 0.40
  risk_tolerance: "moderate"
  investment_horizon_years: 5
real_estate:
  existing_properties: 0
  first_time_buyer: true
preferences:
  self_manage: true
  hurdle_rate: 0.07
```

### How Profile Affects Analysis

| Profile Field | Analysis Impact |
|---------------|-----------------|
| `first_time_buyer: true` | Highlights HBP, FHSA, Home Buyers' Credit |
| `province` | Loads correct tax rates, closing costs, regulations |
| `risk_tolerance: conservative` | Uses lower appreciation (2%), higher vacancy (8%), adds stress test weight |
| `risk_tolerance: aggressive` | Uses moderate appreciation (4%), lower vacancy (3%), emphasizes upside |
| `self_manage: false` | Adds 15% management fee to all scenarios |
| `existing_properties > 0` | Disables first-time buyer programs, notes portfolio considerations |
| `investment_horizon_years` | Changes which projection years to emphasize |
| `corporation_owned: true` | Flags corporate tax treatment, deductibility changes |
| `marginal_tax_rate` | Calculates actual tax impact of rental income/losses |

---

## 8. Output Formats

### 8.1 Markdown Report (Primary)

Stored at `evaluations/[property-slug]/analysis.md`

**Required sections (in order):**

1. **Header** — Property address, type, asking price, date
2. **TL;DR** — 5-10 line summary of the primary scenario with key numbers
3. **Upfront Costs** — Cash to close table for each financing level
4. **Monthly Out-of-Pocket** — Building blocks (OPEX, mortgage, revenue) then scenario comparison table
5. **Returns if Sold in Year X** — Projection tables for primary + investor scenarios
6. **Rent vs. Buy** — Crossover analysis with table
7. **Risk Analysis** — Risk matrix + all four stress tests
8. **Tax Considerations** — T776, principal residence, GST/HST
9. **Regulation Summary** — STR rules, zoning, heritage, red flags
10. **ROI Enhancements** — Top recommendations with feasibility and ROI
11. **Bottom Line** — Price opinion by scenario, max price table, recommendation
12. **Questions for Seller** — Auto-generated list
13. **Appendix** — Scenario matrix, amortization reference, assumptions used

**Tone:** Direct, opinionated, human-readable. Not a spreadsheet dump. Each section should tell a story and make clear what the numbers mean for the buyer's decision. See the Prince Street analysis for the gold standard.

### 8.2 Google Sheet Export

Auto-generated Google Sheet with tabs:

| Tab | Contents |
|-----|----------|
| **Summary** | Key metrics dashboard — price, monthly cost per scenario, ROI, recommendation |
| **Financing** | All financing scenarios with CMHC, closing costs, monthly payments |
| **Scenarios** | Full scenario comparison table (A through F) |
| **Projections** | Year 1-10 projections for each scenario |
| **Rent vs Buy** | Crossover analysis with chart |
| **Stress Tests** | All four stress test results |
| **Enhancements** | ROI enhancement table with costs, impact, payback |
| **Assumptions** | All inputs and assumptions used (for auditability) |

**Implementation:** Use Google Sheets API v4 with service account. Create from a template sheet that has formatting/charts pre-built. Populate with data.

**Sheet link stored at:** `evaluations/[property-slug]/sheet-link.md`

### 8.3 TL;DR Summary (Telegram)

Concise summary suitable for messaging. Max ~500 characters.

Format:
```
🏠 [Address] — [Type]
💰 [Asking] → modeled at [Offer]
📊 Primary scenario: [description]
  └ Monthly: $X | ROI (5yr): Y%
  └ Rent crossover: ~Z months
⚠️ Key risk: [top risk]
✅ Verdict: [one-line recommendation]
📋 Full report: [link]
```

---

## 9. Data Sources

### 9.1 Listing Data

| Source | Method | Data Available |
|--------|--------|---------------|
| **realtor.ca** | Web scrape (agent) | Price, address, type, features, photos, agent info, MLS# |
| **viewpoint.ca** | Web scrape (agent) | NS only: assessment history, sales history, lot details, tax info |
| **centris.ca** | Web scrape (agent) | Quebec: similar to realtor.ca |
| **Manual input** | User provides | Whatever the user knows |

**Note:** No official APIs for Canadian real estate listings. The AI agent accesses these like a human user would — viewing the listing page and extracting structured data. This is for individual property evaluation, not bulk scraping.

### 9.2 Rental Comps

| Source | Method | Data Available |
|--------|--------|---------------|
| **Kijiji** | Web search/scrape | LTR listings with asking rent |
| **Facebook Marketplace** | Browser (limited) | LTR listings, often more casual |
| **rentals.ca** | Web search | National rental listings, rent reports |
| **CMHC Rental Market Report** | Public PDF/data | Average rents by market, vacancy rates |
| **Padmapper** | Web search | Rental listings with map |

### 9.3 STR Comps

| Source | Method | Data Available |
|--------|--------|---------------|
| **AirDNA** | API (paid) or web scrape | ADR, occupancy, revenue estimates, seasonal data |
| **Airbnb search** | Web browse (agent) | Comparable listing prices, reviews, amenities |
| **VRBO search** | Web browse (agent) | Alternative platform comps |
| **AllTheRooms** | API (paid) | STR analytics |

**Fallback:** If no comp data available, use provincial/regional STR benchmarks from tourism reports.

### 9.4 Municipal / Government Data

| Source | Method | Data Available |
|--------|--------|---------------|
| **PVSC** (NS) | Web lookup | Property assessment value, assessment history |
| **MPAC** (ON) | Web lookup | Ontario property assessments |
| **BC Assessment** | Web lookup | BC property assessments |
| **Municipal websites** | Web browse (agent) | Tax rates, bylaws, zoning maps |
| **CMHC** | Public tables | Insurance premium schedules |
| **StatsCan** | Public data | Demographics, economic data |

### 9.5 Mortgage Rates

| Source | Method | Data Available |
|--------|--------|---------------|
| **ratehub.ca** | Web scrape | Best available rates by term and type |
| **nesto.ca** | Web scrape | Competitive online rates |
| **Bank of Canada** | Public data | Benchmark rates, posted rates |

### 9.6 Data Freshness

All externally sourced data is timestamped. The report includes a "Data as of" section showing when each data point was fetched. Stale data (> 30 days for rates, > 90 days for comps) generates a warning.

---

## 10. Open-Source Structure

### What Stays Private (gitignored)

```
config/owner-profile.yaml          # Personal financial info
evaluations/*/                     # Individual property analyses
.env                               # API keys
```

### What's Generic (committed)

```
config/owner-profile.example.yaml  # Template
config/cmhc-premiums.yaml          # Public CMHC tables
config/provinces/*.yaml            # Tax rates, rules (public info)
config/defaults.yaml               # Default assumptions
src/**                             # All code
tests/**                           # Tests + fixtures
scripts/**                         # CLI tools
README.md                          # Usage guide
SPEC.md                            # This spec
```

### Province Pluggability

Adding a new province requires:
1. Create `config/provinces/[code].yaml` with tax rates, closing costs, rental rules, STR regulations
2. Add province-specific data sources to the data gatherer
3. Run tests against a fixture property in that province

The analysis engine reads all province-specific values from config. No province is hardcoded in the calculation logic.

### Country Extensibility

The current design assumes Canada (semi-annual compounding, CMHC, HST, T776). To support another country:

1. Create `config/countries/[code].yaml` with mortgage conventions, insurance programs, tax framework
2. Implement country-specific mortgage calculator (US uses monthly compounding, different amortization norms)
3. Implement country-specific tax engine
4. Province/state configs follow the same pattern

**MVP is Canada-only.** Country extensibility is a design consideration, not a build requirement.

### Fork-Friendly Design

- All calculations are pure functions with clear inputs/outputs
- No hardcoded assumptions — everything lives in config
- Owner profile is separate from analysis logic
- Province configs are self-contained
- Test fixtures with known-good outputs for regression testing

---

## 11. MVP vs Full Version

### MVP (v0.1) — "It works for Graham"

**Scope:** Produce an analysis equivalent to the Prince Street report for any NS property.

| Feature | Status |
|---------|--------|
| Manual input (YAML file) | ✅ Build |
| Financing calculator (CMHC, closing costs, mortgage) | ✅ Build |
| Scenario generator (all 6 scenario types) | ✅ Build |
| Multi-year projections (1, 3, 5, 7, 10 year) | ✅ Build |
| Rent-vs-buy crossover | ✅ Build |
| Risk matrix + 4 stress tests | ✅ Build |
| Tax considerations (T776, PRE, GST/HST) | ✅ Build |
| Markdown report output | ✅ Build |
| TL;DR summary for Telegram | ✅ Build |
| NS province config | ✅ Build |
| Owner profile (Graham's defaults) | ✅ Build |
| Test suite with Prince Street fixture | ✅ Build |
| Listing URL parser (realtor.ca) | ❌ Defer |
| AI agent data gathering (comps, rates) | ❌ Defer |
| Google Sheets export | ❌ Defer |
| Regulation module | ❌ Defer |
| ROI enhancement module | ❌ Defer |
| Other province configs | ❌ Defer |

**MVP deliverable:** `npx real-estate-eval --input ./property.yaml` produces a complete analysis.md

**Effort estimate:** 2-3 focused coding sessions.

### v0.2 — "AI-powered data gathering"

| Feature | Status |
|---------|--------|
| Listing URL parser (realtor.ca, viewpoint.ca) | ✅ Build |
| AI agent comp gathering (rental + STR) | ✅ Build |
| Auto-populate input from listing URL | ✅ Build |
| Google Sheets export | ✅ Build |

**Deliverable:** `npx real-estate-eval https://www.realtor.ca/...` produces analysis + Sheet.

### v0.3 — "Regulation + Enhancements"

| Feature | Status |
|---------|--------|
| Regulation module (STR bylaws, zoning, heritage) | ✅ Build |
| ROI enhancement module (all 4 categories) | ✅ Build |
| Enhancement feasibility scoring | ✅ Build |

### v0.4 — "Multi-province + Open Source"

| Feature | Status |
|---------|--------|
| ON, BC, AB province configs | ✅ Build |
| Generalized closing cost calculator | ✅ Build |
| Open-source packaging (README, examples, CI) | ✅ Build |
| Province contribution guide | ✅ Build |

### v1.0 — "Production"

| Feature | Status |
|---------|--------|
| All Canadian provinces | ✅ Build |
| Batch evaluation (compare multiple properties) | ✅ Build |
| Historical analysis (track property over time) | ✅ Build |
| Web UI (optional) | Consider |
| US support | Consider |

---

## 12. Edge Cases & Limitations

### Property Types That Need Special Handling

| Type | Challenge | Approach |
|------|-----------|----------|
| **Condo** | Monthly condo fees, special assessments, reserve fund health | Add condo_fees to OPEX, flag reserve fund status, adjust maintenance reserve |
| **Mixed-use (commercial + residential)** | Different financing rules, commercial vacancy patterns, zoning complexity | Separate revenue streams, flag commercial mortgage requirements (typically 25%+ down, different rates) |
| **Vacant land** | No rental income, no OPEX, pure speculation | Simplified model: purchase cost + carry cost (tax, interest) vs appreciation. Enhancement module focuses on development potential |
| **Co-op** | Not real ownership, different financing, board approval | Flag as fundamentally different structure. Most mortgage calculations don't apply |
| **New construction** | GST/HST on new builds, builder warranties, no comp history | Add HST to purchase price (or rebate if applicable), different risk profile |
| **Mobile/manufactured home** | Different depreciation, lot lease, financing restrictions | Flag depreciation risk, lot lease as ongoing cost, limited mortgage options |
| **Rooming house** | Many units, different regulations, higher management burden | Per-room revenue model, higher vacancy, higher management costs |
| **Farm / rural with acreage** | Agricultural use, different assessment, different zoning | Out of scope for MVP. Flag and suggest specialized analysis |

### Assumptions That Could Break

| Assumption | When It Breaks | Mitigation |
|------------|----------------|------------|
| **3% appreciation** | Market crash, overheated market, rural decline | Stress test at 0%. Allow user override. Show sensitivity analysis |
| **Semi-annual compounding** | US mortgages, private lenders | Country-specific mortgage engine. Flag non-standard terms |
| **5% selling costs** | Discount brokerages (1-2%), FSBO (0-1%) | Allow override. Note range in report |
| **CMHC rules as of 2025** | Government changes program (happens frequently) | Date-stamp CMHC config. Note "as of" date in reports |
| **Self-management** | Owner lives far away, has no time | Profile flag. Add property management fee option |
| **Single mortgage** | Vendor take-back, private second, HELOC | Out of scope for MVP. Note in report limitations |
| **Stable interest rates** | Dramatic rate moves between analysis and purchase | Always show rate sensitivity. Add "if rates change by X" table |

### Known Limitations

1. **No real-time market data.** The tool doesn't maintain a live database. Data is gathered per-evaluation by the AI agent.
2. **Comp quality varies.** In small markets (like Lunenburg), there may be very few comparable rentals or STR listings. The report should note sample size.
3. **Regulation data goes stale.** Bylaws change. The tool should timestamp all regulatory lookups and warn if data is older than 6 months.
4. **Not a legal or tax substitute.** The tool flags considerations but explicitly says "consult a professional" for tax planning, legal structure, and mortgage advice.
5. **Canadian mortgage convention only (MVP).** US, UK, Australian mortgages compound differently and have different insurance/tax structures.

---

## 13. Stress Test of This Spec

### Does this spec hold up? Let me pick it apart.

**Q: What edge cases would break the core analysis?**

- **Properties over $1.5M:** CMHC doesn't insure above this. The tool should detect this and only show 20%+ down scenarios. ✅ Addressed in CMHC rules.
- **Properties in municipalities with no PVSC data:** Assessment-based tax estimates fail. Fallback: ask user for actual tax bill. ✅ Addressed via overrides.
- **Furnished vs. unfurnished LTR:** Furnished rentals get higher rent but cost more. Not currently modeled as a separate scenario. **Gap — add furnished LTR as a scenario variant in v0.2.**
- **Properties with existing tenants:** Can't convert to STR immediately. Need to model transition period. **Gap — add "existing lease" input field and model lease expiry timeline.**
- **Seasonal markets where LTR comps don't exist:** Some tourism towns have almost no year-round LTR market. **Addressed by using STR-heavy scenarios, but should flag when LTR comp data is thin.**

**Q: What assumptions are baked in that shouldn't be?**

- **Canada-only:** Yes, but intentionally. The architecture supports other countries via config, but MVP is Canada. ✅
- **NS-only for MVP:** Yes, and that's fine. Province configs are pluggable. ✅
- **Residential only:** Commercial properties need fundamentally different analysis. Out of scope, clearly stated. ✅
- **Individual buyer:** Corporate purchases have different tax treatment. ✅ Flagged in owner profile.
- **Single property analysis:** No portfolio-level analysis (how does this property fit with others?). **Acceptable for MVP. Consider for v1.0.**

**Q: What's the MVP?**

Manual input → deterministic calculations → markdown report. No AI agent, no scraping, no Google Sheets. Just `input.yaml` → `analysis.md`. Can be built in 2-3 sessions and immediately useful.

**Q: What would make this genuinely useful as open-source?**

1. **Province configs as community contributions.** Each province is a self-contained YAML file. People contribute their province's tax rates, rules, and regulations.
2. **Test fixtures with known-good outputs.** Anyone can verify the math by running tests against real evaluated properties.
3. **Clear separation of "engine" from "data."** The calculation engine is reusable. The data gathering is the hard part and varies by market.
4. **Opinionated defaults.** Don't make users configure everything. Ship with sensible defaults that work for 80% of Canadian buyers.
5. **Real narrative output.** Most real estate calculators output spreadsheets. This tool outputs a human-readable analysis with opinions and recommendations. That's the differentiator.

**Q: What are the biggest risks to this project?**

1. **Scope creep.** The enhancement module alone could be its own product. Keep MVP tight.
2. **Data gathering reliability.** Scraping realtor.ca and Airbnb is fragile. Design for graceful degradation when scraping fails (fall back to manual input).
3. **Regulation accuracy.** Wrong regulatory info could lead to bad investment decisions. Always timestamp, always caveat, always say "verify with municipality."
4. **Mortgage math errors.** Canadian mortgage math is non-trivial (semi-annual compounding). Unit tests against known mortgage calculator outputs are essential.
5. **Staleness.** CMHC rules, tax brackets, and provincial regulations change. The tool needs a clear "last updated" on all config files and a process for keeping them current.

---

## Appendix A: Canadian Mortgage Formula Reference

**Semi-annual compounding (Canadian convention):**

```
Given: annual_rate, principal, amortization_months

# Convert annual rate to effective monthly rate
semi_annual_rate = annual_rate / 2
monthly_rate = (1 + semi_annual_rate)^(1/6) - 1

# Monthly payment
payment = principal × monthly_rate × (1 + monthly_rate)^n / ((1 + monthly_rate)^n - 1)
where n = amortization_months

# Balance after k payments
balance(k) = principal × (1 + monthly_rate)^k - payment × ((1 + monthly_rate)^k - 1) / monthly_rate
```

**Verification:** For $479,180 at 4.2% over 25 years:
- semi_annual_rate = 0.021
- monthly_rate = (1.021)^(1/6) - 1 = 0.003471
- payment = $479,180 × 0.003471 × (1.003471)^300 / ((1.003471)^300 - 1) = ~$2,583/mo ✓

## Appendix B: CMHC Premium Schedule (as of 2025)

| LTV Ratio | Down Payment | Premium (% of mortgage) |
|-----------|-------------|------------------------|
| Up to 65% | 35%+ | 0.60% |
| 65.01-75% | 25-34.99% | 1.70% |
| 75.01-80% | 20-24.99% | 2.40% |
| 80.01-85% | 15-19.99% | 2.80% |
| 85.01-90% | 10-14.99% | 3.10% |
| 90.01-95% | 5-9.99% | 4.00% |

**Notes:**
- Maximum purchase price: $1,499,999 (as of Dec 15, 2024 change from $999,999)
- Owner-occupied only
- Maximum amortization: 25 years (insured), 30 years for first-time buyers on new builds (as of Aug 2024)
- Multi-unit (3-4 units): 10% minimum down payment
- Self-employed surcharge: additional 0.75% if income not traditionally verifiable

## Appendix C: Gold Standard Reference

The 9 Prince Street, Lunenburg analysis (`evaluations/9-prince-street-lunenburg/analysis.md`) serves as the gold standard for output quality. Key characteristics to replicate:

1. **TL;DR first** — Lead with the bottom line, not the methodology
2. **Building blocks visible** — Show how monthly costs are constructed before showing scenarios
3. **Every number traceable** — Footnotes explain how calculations were derived
4. **Opinionated narrative** — "The numbers work" / "Not a screaming deal" / "This is the real pain scenario"
5. **Scenario comparison table** — All scenarios in one table, both financing levels
6. **Stress tests are specific** — Not generic "what if rates go up" but exact numbers: "If rates are 6% at renewal, payment becomes $X, which is $Y more per month"
7. **Crossover analysis** — Don't just say "buying is better" — show exactly when it becomes better
8. **Actionable questions** — Seller questions are specific to this property, not generic checklists
9. **Appendix with raw math** — For people who want to verify

---

*This spec is a living document. Update it as the tool evolves.*
