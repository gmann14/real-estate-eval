# Default Assumptions

> Generic defaults used when the evaluation input doesn't override them.
> Deliberately conservative — intended to bias the analysis toward cautious
> recommendations. Override in the input template when you have better data.

## Financial Defaults

| Field | Default | Rationale |
|-------|---------|-----------|
| Mortgage rate (5yr fixed) | Use current market rate at analysis time | Pull from ratehub.ca / nesto.ca |
| Amortization (insured, < 20% down) | 25 years | CMHC standard |
| Amortization (uninsured, 20%+ down) | 25 years | Can extend to 30 if needed |
| Property appreciation | 3.0%/yr | Below long-run avg; Canadian market typically 4–5% |
| Annual rent increase (LTR) | 3.0%/yr | Province-specific — may be capped (ON, BC, QC) |
| Annual ADR increase (STR) | 3.0%/yr | Tracks tourism inflation |
| Annual expense inflation | 2.5%/yr | Slightly above CPI target |
| Selling costs | 6.5% of sale price | Commissions + legal + marketing, Canadian market |
| Investment hurdle rate (rent-vs-buy alternative) | 7.0%/yr | Long-run equity index return (real + inflation) |

## Operating Expense Defaults (if no overrides)

| Field | Default |
|-------|---------|
| Maintenance + CapEx reserve (post-1990 building) | 1.0% of property value/yr |
| Maintenance + CapEx reserve (pre-1990 / heritage) | 1.5–2.0% of property value/yr |
| Property management fee (if `self_manage: false`) | 10% of gross rental revenue (LTR); 20–25% (STR) |
| LTR vacancy allowance | 5% |
| STR platform fee (host-only, Airbnb) | 3% |
| Accounting (with rental income) | $600–$1,000/yr |
| Internet (landlord-provided) | $90/mo |

## STR Assumptions

| Field | Default |
|-------|---------|
| Occupancy Year 1 (new listing) | 45% |
| Occupancy Year 2 (building reviews) | 50% |
| Occupancy Year 3+ (mature listing) | 55–65% depending on market |
| Cleaning fee per turnover (studio/1BR) | $75–$100 |
| Cleaning fee per turnover (2BR+) | $100–$150 |
| Supplies + linen per unit | $750/yr |
| Furnishing (one-time, studio) | $2,000 |
| Furnishing (one-time, 2BR) | $3,000–$5,000 |
| Furnishing amortization | 5 years |

## Scenario Defaults

Scenarios always modeled (unless input says otherwise):

- **A** — Owner-occupy larger unit, smaller as LTR
- **B** — Owner-occupy larger unit, smaller as Airbnb ⭐
- **C** — Both units as LTR (investor)
- **D** — Both units as Airbnb (investor)
- **E** — Owner-occupy + summer-only Airbnb
- **F** — Dual-occupancy (no rental)

Financing levels always modeled: **5% down**, **10% down**, **20% down**
(5% only if owner-occupied and CMHC-eligible).

## Rent-vs-Buy Defaults

| Field | Default |
|-------|---------|
| Renter's alternative investment return | 7.0%/yr (after fees) |
| Hold period for crossover analysis | 10 years |
| Rent escalation for renter | 3.0%/yr |

## Risk-Tolerance Profiles

Override via `config/owner-profile.md`:

| Profile | Appreciation | Vacancy | Occupancy (STR) | Rate Stress |
|---------|--------------|---------|-----------------|-------------|
| Conservative | 2% | 8% | Base − 10pts | +1.5% at renewal |
| Moderate (default) | 3% | 5% | Base | +1.0% at renewal |
| Aggressive | 4% | 3% | Base + 5pts | +0.5% at renewal |

## Conventions

- **All figures in CAD** unless otherwise stated.
- **Mortgage compounding**: Canadian semi-annual (NOT US monthly). Formula:
  ```
  semi_annual_rate = (1 + annual_rate / 2)^(1/6) - 1
  monthly_payment = P × r × (1+r)^n / ((1+r)^n - 1)
  ```
- **All assumptions documented in the analysis**. Every number should trace to
  a source: comp, config file, or input override.
