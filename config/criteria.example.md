# My Evaluation Criteria — Example

> Copy this file to `config/criteria.md` (gitignored) and edit it. The
> ingestion skill parses this on every run to decide whether a listing
> is worth a full analysis, a light analysis, or should be skipped.

## Hard filters

> If any of these fail, the listing is rejected before full analysis.

- **Units:** >= 2
- **Price:** <= 600000
- **Location:** in MODL, HRM
- **Lot size acres:** >= 0.08
- **Excluded zones:** not_in flood, industrial, arterial

## Soft signals

> These don't reject a listing. They surface as flags in the analysis
> so you can weight them yourself.

### ADU potential

- Basement height >= 7ft
- Separate entrance present or feasible
- Lot acres >= 0.2

### Upgrade potential

- Kitchen described as original
- Year built between 1900 and 1950
- Electrical panel not upgraded

### Condition signals

- Roof age <= 10
- Heat pump installed
- Foundation poured concrete
