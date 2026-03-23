# Google Sheet Export — Design Reference

Based on Graham's 9 Prince Street spreadsheet (the gold standard).

## Tab Structure

### 1. Summary (the "Should You Buy It?" tab)
- Property headline: name + unit descriptions + year built + price
- Down payment / scenario context line
- For each scenario (best first), four sections:
  - ① UPFRONT COST — cash to close, vs alternative down payment
  - ② MONTHLY OUT-OF-POCKET — year-by-year (Yr 0-10) showing Revenue, OPEX, Monthly Cost
  - ③ WHAT DO YOU MAKE IF YOU SELL? — year-by-year: property value, mortgage balance, selling costs (6.5%), cumulative cash flow, cash profit (PRE vs non-PRE), annualized return
  - ④ vs RENTING + INVESTING — year-by-year: rent portfolio growth, cumulative rent paid, rent net wealth vs buy net wealth, "YOU'RE BETTER OFF BUYING BY" line
- ⑤ KEY RISKS — severity-rated (🔴🟡🟢) one-liner risks
- BOTTOM LINE — Buy IF / Consider / Don't buy IF

### 2. Assumptions
- All editable inputs in one place (yellow cells)
- Sections: Purchase & Financing, Closing Costs, Annual Operating Expenses, Revenue Assumptions, Growth Assumptions
- Two scenario columns (20% down, 5% down) with notes column
- Every assumption has a note explaining the source/reasoning

### 3. Scenarios (separate tabs per down payment)
- "Scenarios 20pct Down" and "Scenarios 5pct Down"
- Full scenario matrix with all combinations

### 4. 10-Year Projections (separate tabs per down payment)
- Year-by-year detailed projections
- Mortgage amortization details

### 5. Price Sensitivity
- Purchase prices across columns ($450K → $575K in increments)
- For each scenario: Net Revenue, OPEX, NOI, Annual Cash Flow, Monthly OOP
- Key metrics: Equivalent Monthly Rent (Yr 0 and Yr 5), Cap Rate, Cash-on-Cash Return

### 6. STR Upgrades & ROI
- Tiered structure: Tier 1 (free/low), Tier 2 (moderate), Tier 3 (major), Tier 4 (strategy)
- Columns: #, Upgrade, Cost, Annual OPEX, ADR Lift %, Rev Uplift/Year, Payback, ROI Yr 1, Notes
- Current baseline context at top
- Total potential uplift summary at bottom

### 7. Tax Notes
- Province-specific tax considerations
- Primary residence exemption rules
- Rental income treatment (LTR vs STR)
- HST threshold
- Municipal/provincial specific taxes (DTT, PDTT, CAP)
- CMHC considerations
- Disclaimer

### 8. Rent vs Buy (detailed)
- Extended comparison with multiple rent levels

## Design Principles

1. **Summary first** — the TL;DR tab answers "should I buy?" without opening any other tab
2. **Year-by-year, not snapshots** — show Yr 0-10 for every projection
3. **Dual framing** — show both "what does it cost me monthly" AND "what if I sell in year X"
4. **Rent-vs-buy as wealth comparison** — not just "is buying cheaper per month" but "am I wealthier buying or renting over time"
5. **Risk-rated** — 🔴🟡🟢 severity on all risks
6. **Editable inputs** — yellow cells on Assumptions tab drive all calculations
7. **Price sensitivity** — don't just model one price, show how the numbers change across a range
8. **Enhancement ROI** — show specific upgrades with payback periods, not just "consider improvements"
9. **6.5% selling costs** (not 5%) — more realistic for Canadian market
10. **8% investment return** for rent-vs-buy alternative — reasonable long-term equity index assumption

## What to Add (from audit)

- Revised assumptions column (insurance $4,500, maintenance $9K, occupancy ramp)
- Conservative / Base / Optimistic scenarios
- CMHC eligibility flag
- Combined stress test scenario
- Model sensitivity table (what breaks the deal)
- Dual-occupancy scenario
