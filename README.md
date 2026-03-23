# Real Estate Evaluation Tool

Drop in a listing URL → get a full investment analysis.

## How to Use

1. Paste a listing URL (realtor.ca, viewpoint.ca, etc.) to Alfred
2. Sub-agent pulls the listing, populates the input template
3. Full scenario analysis runs automatically
4. Clean report with tables, stress tests, and bottom-line recommendation

## Scenarios Analyzed

| Scenario | Description |
|----------|-------------|
| A | Owner-occupies larger unit, smaller unit as LTR |
| B | Owner-occupies larger unit, smaller unit as Airbnb ⭐ |
| C | Both units as LTR (pure investment) |
| D | Both units as Airbnb (pure investment) |
| E | Owner-occupies + Airbnb summer only |
| F | Dual-occupancy (split costs with family/partner) |

Each scenario modeled at both 5% and 20% down.

## What's Included

- Upfront costs (closing, furnishing, CMHC)
- Monthly out-of-pocket for every scenario
- 10-year return projections (years 1, 3, 5, 7, 10)
- Rent-vs-buy crossover analysis
- Stress tests (low occupancy, rate hikes, flat market)
- Risk assessment and bottom-line recommendation

## Structure

```
evaluations/           # One folder per property
  property-name/
    input.md           # Listing data + assumptions
    analysis.md        # Full analysis output
templates/
  evaluation-template.md   # Blank input template
config/
  ns-defaults.md       # Nova Scotia tax rates, CMHC tables, etc.
```
