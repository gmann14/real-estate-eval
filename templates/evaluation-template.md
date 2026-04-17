# [Property Address] — Evaluation Input

> Fill in the sections below, then ask Claude to run the analysis.
> Fields marked `*` are required. Fields left blank or marked `?` will be
> inferred by the agent from listing data or provincial defaults.

---

## Listing Details

- **Address\*:** [street, city, province, postal code]
- **Asking Price\*:** $
- **Listing URL:** [realtor.ca / viewpoint.ca / centris.ca / other]
- **Type\*:** [single | duplex | triplex | fourplex | mixed-use | condo]
- **Year Built:** [e.g., 1890]
- **Land:** [acres or sq ft]
- **Previous Sale Price:** $ ([date])
- **Days on Market:** [number]
- **Listing Agent:** [name, brokerage, phone]

## Units

> One row per unit. Leave fields blank if unknown.

| # | Name | Beds | Baths | Sq Ft | Level | Kitchen | Laundry | Separate Entry | Current Use | Current Rent | Airbnb URL |
|---|------|------|-------|-------|-------|---------|---------|----------------|-------------|--------------|------------|
| 1 |      |      |       |       |       |         |         |                | [owner/ltr/str/vacant] |              |            |
| 2 |      |      |       |       |       |         |         |                |             |              |            |

## Building Features

- **Heating:** [oil / gas / electric / heat pump / dual]
- **Roof:** [metal / asphalt / rubber / slate] ([age, if known])
- **Foundation:** [concrete / stone / block / pier]
- **Parking:** [spots + type — paved/gravel/street]
- **Heritage Designated:** [yes/no]
- **Basement:** [finished / unfinished / crawl / none]
- **Known Issues:** [moisture, asbestos, lead, knob-and-tube, etc.]

## Recent Renovations (since previous sale)

- [item 1]
- [item 2]

## Municipal

- **Municipality\*:** [e.g., Town of Lunenburg]
- **Province\*:** [NS / ON / BC / …]
- **Water/Sewer:** [municipal / well / septic / mixed]
- **Zoning:** [residential / mixed / commercial]
- **STR Permitted:** [yes / no / restricted — cite bylaw if known]

## Actual Operating Data (if seller-provided)

> Leave blank if not yet received. Strongly preferred to drive the analysis off
> real numbers, not estimates.

| Year | Gross Revenue | Operating Expenses | Net Profit (pre-depreciation) |
|------|---------------|--------------------|-------------------------------|
|      | $             | $                  | $                             |

**Revenue breakdown by unit / channel:** [paste / link]
**Expense breakdown line items:** [paste / link]

## Optional Overrides (only if you have better numbers than defaults)

- **Property Tax Override:** $ /yr
- **Insurance Override:** $ /yr
- **Heating Override:** $ /yr
- **Electricity Override:** $ /yr
- **Water/Sewer Override:** $ /yr

## Revenue Assumptions (will be enriched from comps if blank)

| Field | Your Value | Notes |
|-------|-----------|-------|
| 2-Bed LTR Monthly Rent |  | Comp range: |
| Studio LTR Monthly Rent |  | Comp range: |
| 2-Bed Airbnb ADR |  |  |
| 2-Bed Airbnb Occupancy |  |  |
| Studio Airbnb ADR |  |  |
| Studio Airbnb Occupancy |  |  |
| Airbnb Active Months | 12 |  |
| Airbnb Platform Fee % | 3 | Host-only |
| Cleaning Fee / Turnover |  |  |
| Turnovers / Year |  |  |
| Supplies / Linen (per unit) | $750/yr |  |
| Furnishing (one-time, per unit) | $2,000–$3,000 |  |
| LTR Vacancy Allowance | 5% |  |
| Property Management Fee | 0% | Self-managed |

## Growth Assumptions (override only if you disagree with defaults)

| Item | Default | Your Value |
|------|---------|------------|
| Annual Rent Increase (LTR) | 3.0% |  |
| Annual ADR Increase (Airbnb) | 3.0% |  |
| Annual Expense Inflation | 2.5% |  |
| Annual Property Appreciation | 3.0% |  |
| Mortgage Rate (5yr fixed) | [market] |  |
| Amortization | 25 years |  |

## Scenarios to Model (default: all)

- [ ] A — Owner-occupies larger unit, smaller unit as LTR
- [ ] B — Owner-occupies larger unit, smaller unit as Airbnb ⭐
- [ ] C — Both units as LTR (pure investment)
- [ ] D — Both units as Airbnb (pure investment)
- [ ] E — Owner-occupies + Airbnb summer only
- [ ] F — Dual-occupancy (split costs with family/partner)

## Owner Profile (pulls from `config/owner-profile.md` if present)

- **Investment Horizon:** [years]
- **Risk Tolerance:** [conservative / moderate / aggressive]
- **Self-Manage:** [yes / no]
- **First-Time Buyer:** [yes / no]
- **Max Monthly Housing Cost:** $ [or blank]
- **Marginal Tax Rate:** [e.g., 0.43]
- **Hurdle Rate for Rent-vs-Buy:** [default 7%]

## Notes / Open Questions for the Agent

- [Any context the agent should know — specific concerns, comparable properties you're weighing, deadline for the decision, etc.]
