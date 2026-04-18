# 142 Maple Lane, Mahone Bay — Full Investment Analysis

> 🧪 **Synthetic example.** Address, agent, and financials are fictional.
> Numbers are plausible for a 2026 Mahone Bay duplex but invented to
> illustrate the tool's output structure.

**Property:** Duplex (2BR + 1BR), built 1908, concrete foundation, non-heritage
**Asking Price:** $425,000 | **Modeled Offer:** $412,000
**Date:** 2026-04-17 | **Revision:** v1.1 (2026-04-18 math correction pass)

---

## TL;DR — The Primary Scenario

**Owner-occupies 2BR, 1BR as Airbnb, 5% down at $412,000:**

| Metric | Value |
|--------|-------|
| Cash to close | $33,500 |
| Monthly cost Year 1 | $1,839 |
| Monthly cost Year 3+ | $1,426 |
| Premium over $1,800 rent | +$39/mo Yr 1, −$374/mo Yr 3+ |
| Rent-vs-buy crossover | **~early Year 4 (~month 38)** |
| 5-year total return | ~$102K |
| 10-year total return | ~$227K |
| Annualized 10-yr ROI | ~26% |

**Final Verdict:** Strong buy at $412,000. Well-maintained, non-heritage,
concrete foundation reduces the major-CapEx tail risk that plagues older
Maritime duplexes. The 1BR unit as Airbnb covers most of the mortgage + OPEX
by Year 3, and the Scenario B monthly cost falls **below equivalent rent**
from Year 2 onward. The 2022–2024 seller upgrades (heat pumps, kitchen) mean
you inherit a cash-flowing property with near-term CapEx already spent.

**Offer guidance:**
- **At $395–$405K:** Strong buy. Crossover at ~Year 3.
- **At $412K (modeled offer):** Good buy. Solid margins.
- **At asking ($425K):** Fair. Still works but closer to thin on stress scenarios.
- **Above $445K:** Walk away. Better Mahone Bay comps available at this price.

---

## 🟡 Items to Resolve Before Offer

Non-critical but worth confirming before going firm:

### 1. STR Insurance Rider
Current seller insurance ($1,800/yr) is LTR-only. Converting Unit B to STR
requires a rider or commercial policy. Budget **$2,200–$2,800/yr**. Get one
quote before firm-up.

### 2. Mahone Bay STR Bylaw Status
As of 2026-04, Mahone Bay has no STR-specific restrictions in residential
zones, but heritage overlay could add them. Confirm with town office;
also confirm no pending amendments.

### 3. Basement Moisture (Minor)
Sump pump installed 2019 is a positive signal, but ask seller for pump
service history and any remaining moisture episodes. Budget $1,500 for
dehumidifier + minor waterproofing touch-up.

---

## 1. Assumptions Framework

| Assumption | Base | Conservative | Optimistic | Source |
|------------|------|--------------|------------|--------|
| Insurance (with STR rider) | $2,400/yr | $2,800/yr | $2,000/yr | Seller + STR rider estimate |
| Maintenance + CapEx | $4,250/yr | $5,500/yr | $3,500/yr | 1.0% of value; well-maintained |
| 1BR STR occupancy (Yr1/Yr2/Yr3+) | 42%/47%/52% | 38%/42%/47% | 47%/52%/57% | Mahone Bay Airbnb comps |
| Appreciation | 3%/yr | 2%/yr | 4%/yr | NS South Shore trend |
| 1BR STR ADR | $140 | $125 | $155 | Mahone Bay comps $125–$155 |
| Mortgage rate (5yr) | 4.2% | 4.8% | 4.0% | Market 2026-04 |

### Monthly OPEX (Scenario B)

| Item | $/yr | $/mo | Notes |
|------|------|------|-------|
| Property tax | 4,100 | 342 | Seller-provided |
| Insurance (w/ STR rider) | 2,400 | 200 | Estimate |
| Heating (common) | 1,400 | 117 | Electric + heat pumps |
| Water/sewer | 900 | 75 | |
| Internet (landlord for STR) | 720 | 60 | Unit B guest-facing |
| Maintenance + CapEx | 4,250 | 354 | 1.0% of $425K |
| Landscaping/snow | 1,500 | 125 | |
| Accounting | 700 | 58 | T776 |
| STR supplies/linen | 750 | 63 | Unit B |
| Furnishing amort (5yr) | 400 | 33 | $2K one-time |
| NS STR registration | 50 | 4 | |
| Misc | 200 | 17 | |
| **Total** | **17,370** | **1,448** | |

---

## 2. Upfront Costs

| Item | 5% Down | 20% Down |
|------|---------|----------|
| Down payment | $20,600 | $82,400 |
| CMHC premium (4.0%) | $15,656 (in mortgage) | $0 |
| Deed transfer tax (1.5%) | $6,180 | $6,180 |
| Legal | $2,500 | $2,500 |
| Home inspection | $500 | $500 |
| Appraisal | $350 | $0 |
| Title insurance | $350 | $350 |
| Furnishing (Unit B) | $2,000 | $2,000 |
| Basement moisture touch-up | $500 | $500 |
| Lead/asbestos screening | $500 | $500 |
| **Total cash to close** | **~$33,480** | **~$94,930** |

---

## 3. Monthly Out-of-Pocket

### Revenue streams (Scenario B)

| Source | Monthly Net |
|--------|-------------|
| Unit B LTR (after 5% vacancy) | $1,140 |
| Unit B Airbnb Year 1 (42%) | $1,735 |
| Unit B Airbnb Year 2 (47%) | $1,942 |
| Unit B Airbnb Year 3+ (52%) | $2,148 |
| Unit A LTR (after 5% vacancy) | $1,568 |
| Unit A Airbnb (58%, for Scenario D) | $3,167 |

### Mortgage (Canadian semi-annual, 25yr) — verified via `src/analysis/cli.ts`

- **5% down** ($407,056 mortgage = $391,400 base + $15,656 CMHC): **$2,186/mo**
- **20% down** ($329,600 mortgage): **$1,770/mo**

### Scenario comparison — 5% down

| Scenario | Year 1 | Year 3+ |
|----------|--------|---------|
| A — Owner 2BR + 1BR LTR | $2,558 | $2,558 |
| B — Owner 2BR + 1BR Airbnb ⭐ | **$1,839** | **$1,426** |
| C — Both LTR (investor) | −$966 (loss/mo) | −$966 |
| D — Both Airbnb (investor) | +$194 (near breakeven) | +$1,578 (profit) |

### Same scenarios — 20% down

| Scenario | Year 1 | Year 3+ |
|----------|--------|---------|
| A | $2,142 | $2,142 |
| B ⭐ | $1,423 | $1,010 |
| C | −$550 | −$550 |
| D | +$610 | +$1,994 |

### Takeaways

1. **Scenario B crosses below $1,800 equivalent rent in Year 3.** Unlike
   higher-priced heritage properties, this deal's economics work without
   requiring 7+ year holds.
2. **LTR-only (C) still loses money** — $966/mo at 5% down. Not a pure
   investment play.
3. **Full Airbnb (D) is marginal Year 1 but solidly profitable by Year 3.**
   If you don't need to live there, this is the highest-return scenario.
4. **20% down is materially better monthly** but ties up $95K. Trade-off:
   $62K of extra capital tied up for ~$416/mo savings = **8.1% effective
   return** on that extra capital.

---

## 4. Price Sensitivity (Scenario B, 5% down)

| Metric | $395K | $405K | $412K | $425K | $445K |
|--------|-------|-------|-------|-------|-------|
| Cash to close | $32,375 | $33,025 | $33,480 | $34,325 | $35,625 |
| Monthly P&I | $2,095 | $2,148 | $2,186 | $2,255 | $2,361 |
| OOP Year 1 | $1,748 | $1,801 | $1,839 | $1,908 | $2,014 |
| OOP Year 3+ | $1,335 | $1,388 | $1,426 | $1,495 | $1,601 |
| Crossover month | ~32 | ~35 | ~38 | ~42 | ~50 |
| 5-Yr Total Return | ~$108K | ~$105K | ~$102K | ~$98K | ~$91K |
| 10-Yr Total Return | ~$234K | ~$230K | ~$227K | ~$222K | ~$213K |
| Verdict | ✅ Strong buy | ✅ Strong buy | ✅ Good buy | ⚠️ Fair | ❌ Overpriced |

**Key insight:** Crossover timing is highly sensitive to price in this range.
At $395K you beat renting after ~32 months; at $445K it takes ~50 months.
Target the $405–$415K range.

---

## 5. Returns If Sold — Primary Scenario at $412K, 5% down

**Cash invested:** $33,480

| | Year 1 | Year 3 | Year 5 | Year 7 | Year 10 |
|---|--------|--------|--------|--------|---------|
| Property value | $424,360 | $450,326 | $477,868 | $507,090 | $554,127 |
| Less 6.5% selling costs | −$27,583 | −$29,271 | −$31,061 | −$32,961 | −$36,018 |
| Net sale proceeds | $396,777 | $421,055 | $446,807 | $474,129 | $518,109 |
| Mortgage balance | $397,599 | $377,463 | $355,582 | $331,805 | $292,218 |
| **Net equity at sale** | −$822 | $43,592 | $91,225 | $142,324 | $225,891 |
| Cum. Airbnb income | $20,820 | $70,548 | $125,876 | $186,456 | $282,348 |
| Cum. out-of-pocket | −$22,068 | −$58,020 | −$90,336 | −$120,840 | −$164,760 |
| Net rental benefit | −$1,248 | +$12,528 | +$35,540 | +$65,616 | +$117,588 |
| **Total return** | −$35,550 | +$22,640 | +$93,285 | +$174,460 | +$310,000 |
| **Annualized ROI** | — | ~19% | ~30% | ~30% | ~26% |

---

## 6. Rent vs. Buy Comparison (7% alternative return)

| Year | Renter's Wealth | Buyer's Equity | Winner |
|------|-----------------|----------------|--------|
| 1 | $36,400 | −$822 | 🏠 Rent |
| 2 | $42,100 | ~$21,000 | 🏠 Rent (narrowing) |
| 3 | $45,800 | $43,592 | 🏠 Rent barely (~$2K) |
| **~3.1** | **~$46K** | **~$46K** | **⚖️ Crossover early Yr 4** |
| 5 | $56,100 | $91,225 | 🏡 Buy (+$35,100) |
| 10 | $81,200 | $225,891 | 🏡 Buy (+$144,700) |

*Renter invests $33K + monthly premium at 7%. Premium goes negative from
Year 2 onward (buying cheaper than renting), so "premium invested" becomes
minimal past Year 2.*

### If you plan to stay...

| Horizon | 5% Down | 20% Down |
|---------|---------|----------|
| < 2 years | 🏠 Rent | 🏠 Rent |
| 2–5 years | 🏡 Buy | 🏡 Buy |
| 5+ years | 🏡 Buy clearly | 🏡 Buy decisively |

---

## 7. Risk Analysis

| Risk | Severity | Likelihood | Mitigation |
|------|----------|------------|------------|
| STR bylaw change in Mahone Bay | 🟡 Medium | Low–Med | Scenario B degrades to A (+$1,132/mo) |
| Interest rate at renewal | 🟡 Medium | Medium | Stressed at 6%, see below |
| Basement moisture recurrence | 🟢 Low | Low | Post-2019 waterproofing; budget $1,500 |
| 1BR STR underperforms | 🟡 Medium | Medium | 25% occupancy break-even vs LTR |
| Insurance re-quote higher | 🟢 Low | Low–Med | Non-heritage, concrete foundation → standard market |
| Seller asbestos/lead discovered | 🟢 Low | Medium | $500 testing pre-offer |

### Stress tests

**1BR Airbnb at 32% occupancy:**
- Revenue: $140 × 365 × 0.32 × 0.97 − $1,200 = $14,651/yr = $1,221/mo
- Scenario B: $2,186 + $1,448 − $1,221 = **$2,413/mo** (+$613 over rent)
- Still beats Scenario A by $145/mo.

**Rates rise to 6% at renewal:**
- Balance at renewal (Yr5): $355,582
- New payment at 6% over 20yr: ~$2,532
- Scenario B steady: $2,532 + $1,448 − $2,148 = **$1,832/mo**
- Premium over $1,800 rent: +$32/mo. Still solid.

**Combined stress (32% occ + 6% rate + $2,800 insurance):**
- Scenario B: $2,532 + $1,481 − $1,221 = **$2,792/mo**
- Premium over rent: $992. Painful but serviceable.

**0% appreciation through Year 5:**
- Net equity at Yr5 (instead of $80K): ~$41K
- Net position vs. renting: still positive by ~$15K (because rental benefit
  is strong from Year 2+). Deal still works without appreciation.

### Break-even
1BR Airbnb breaks even with LTR at **~25% occupancy**. Strong floor.

---

## 8. Model Sensitivity

| Assumption | Base | −20% stress | Monthly impact | Decision impact |
|------------|------|-------------|----------------|------------------|
| 1BR ADR | $140 | $112 | +$273/mo → $1,699 | 🟢 Still beats rent |
| 1BR Occupancy Y3+ | 52% | 42% | +$200/mo → $1,626 | 🟢 Still beats rent |
| Mortgage rate | 4.2% | 5.0% | +$193/mo → $1,619 | 🟢 Manageable |
| Appreciation | 3% | 0% | No monthly impact; delays crossover | 🟢 Still works by Yr 3 |
| Maintenance | $4,250 | $5,500 | +$104/mo → $1,530 | 🟢 Manageable |

**No single 20% shock kills this deal.** Significantly more robust than
heritage-property comparables.

---

## 9. Top ROI Enhancements (summary)

| # | Enhancement | Cost | Annual Lift | Payback |
|---|-------------|------|-------------|---------|
| 1 | Professional photos + staging | $800 | +$2,500 | 4 mo |
| 2 | Dynamic pricing tool | $300/yr | +$2,200 | 2 mo |
| 3 | Multi-platform (VRBO + Booking) | $360/yr | +$3,000 | 2 mo |
| 4 | Unit A turnover to $1,800 rent | $0 | +$1,800 | Immediate |
| 5 | Smart lock | $250 | Operational | 6 mo |

**Combined Tier 1 impact:** Scenario B monthly cost drops from $1,426 →
**~$863/mo** steady state. Full enhancement analysis in `enhancements.md`.

---

## 10. Tax Considerations (NS / Canada)

- Unit B rental income on **T776**. Deductions ~40% of shared costs (studio
  is 45% of total sq ft; use market-rent-proportional allocation).
- **Principal residence exemption** on Unit A at sale; Unit B is taxable
  capital gain on the rental portion (~40%).
- At $142K of 10-year appreciation: ~$57K taxable, ~$28.5K capital gain,
  ~$12K in tax at 43% marginal rate.
- STR revenue ~$26K/yr (Unit B only) — **under the $30K HST threshold**. No
  HST registration required unless Scenario D (both units).

---

## 11. Bottom Line Recommendation

### Maximum Price by Scenario (7-year hold, 7% hurdle)

| Scenario | Max Price (5% down) | Max Price (20% down) |
|----------|--------------------|--------------------|
| A — Owner + 1BR LTR | ~$395K | ~$410K |
| B — Owner + 1BR Airbnb ⭐ | **~$440K** | **~$455K** |
| C — Both LTR (investor) | ~$350K | ~$370K |
| D — Both Airbnb (investor) | ~$460K | ~$475K |

### Offer Strategy

| Price | Assessment |
|-------|------------|
| $395–$405K | Strong offer. Opens low, expect counter. |
| $410–$415K | Target. Solid margins at 5% down. |
| $425K (asking) | Only if STR bylaw and insurance come back clean. |
| $440K+ | Pass. |

### Questions for the seller

1. Why selling after 8 years?
2. Can we see 2022–2024 full utility + maintenance records?
3. Sump pump service history?
4. Any seasonal rent fluctuations in the current LTR tenancies?
5. Lead-based paint disclosure on pre-1978 portions of the building?
6. Are current tenants on month-to-month or fixed-term leases?
7. Any pending municipal assessments (water, road, sewer)?

---

## Appendix A — Full Scenario Matrix (5% down)

| Scenario | Yr1 OOP | Yr3+ OOP | Notes |
|----------|---------|----------|-------|
| A | $2,558 | $2,558 | Owner + 1BR LTR |
| B ⭐ | $1,839 | $1,426 | Owner + 1BR STR |
| C | −$966 | −$966 | Both LTR investor |
| D | +$194 | +$1,578 | Both STR investor |

## Appendix B — Amortization (5% down, $407,056 @ 4.2%, 25yr)

| Year | Balance | Principal Paid (cum) | Interest Paid (cum) |
|------|---------|---------------------|---------------------|
| 1 | $397,599 | $9,457 | $16,770 |
| 3 | $377,463 | $29,593 | $49,087 |
| 5 | $355,582 | $51,474 | $79,660 |
| 7 | $331,805 | $75,251 | $108,336 |
| 10 | $292,218 | $114,838 | $147,430 |

## Appendix C — Audit Trail

v1.0 → v1.1 correction pass (2026-04-18): the original 5%-down numbers
mixed the $412K offer price with the $425K asking-price mortgage total
and used US `r/12` compounding in places. Refreshed all 5%-down arithmetic
against `src/analysis/cli.ts` at $412K:

| Item | v1.0 | v1.1 |
|------|------|------|
| 5% down mortgage total | $419,406 | **$407,056** (= $391,400 + $15,656 CMHC) |
| 5% down P&I | $2,253 | **$2,186** |
| 20% down mortgage total | $340,000 | **$329,600** |
| 20% down P&I | $1,825 | **$1,770** |
| Cash-to-close (5% down, $412K) | ~$33,000 | **~$33,480** |

| Item | Status | Notes |
|------|--------|-------|
| CMHC premium rate | ✅ 4.0% at 95% LTV confirmed (v1.1) |
| Mortgage payment (semi-annual) | ✅ v1.1 uses `npx tsx src/analysis/cli.ts` output verbatim |
| 1BR ADR | ✅ $140 within $125–$155 Mahone Bay range |
| 1BR occupancy ramp | ✅ 42%/47%/52% conservative vs 55% steady comp |
| OPEX total | ✅ Sums correctly |
| DTT (NS) | ✅ 1.5% confirmed (Town of Mahone Bay) |
| Insurance re-quote flagged | ✅ Required for STR rider |
| No heritage overlay | ✅ Confirmed: not on heritage register |

---

*Synthetic example prepared to illustrate the analysis tool's output. All
figures in CAD. Mortgage uses Canadian semi-annual compounding. Not
financial advice — consult licensed professionals.*
