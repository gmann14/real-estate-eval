# Real Estate Eval — Tasks

## Completed
- [x] 9 Prince Street Lunenburg — full analysis (6 scenarios, stress tests, rent-vs-buy) — 2026-03-20
- [x] Tier-B (login-gated) extractor for Viewpoint.ca via Playwright + macOS Keychain — 2026-04-19
- [x] Tier-B pass across 56 Montague / 94 King / 69 Fox with material analysis updates — 2026-04-19

## To Do — Tier-B extractor TDD fix pass (2026-04-19)
See [docs/tdd-fix-plan.md](../docs/tdd-fix-plan.md) for the full plan.

- [ ] Refactor: extract pure `parseViewpointBody` from `viewpoint-tier-b.ts` for unit-testability
- [ ] Fix #1: listing agent false positive on non-VP brokerages (69 Fox / Sotheby's returns ViewPoint's house agent)
- [ ] Fix #2: extract heritage designation from description text (currently `null` for 69 Fox despite "Provincial Heritage Property" in description)
- [ ] Fix #3: dedupe listing events (69 Fox returns 41 events with duplicates, ~30 unique)
- [ ] Fix #4: strengthen event-label extraction (currently falls back to "Expired — listed" on price-change rows)
- [ ] Fix #5: finish 94 King Scenario B/C/D with oil OPEX delta (only Scenario A updated)
- [ ] Fix #6: finish 69 Fox D-Inn scenario with heating + roof deltas
- [ ] Fix #7: recompute 56 Montague scenarios with electric-heat savings
- [ ] Fix #11: bump `details` key length from 60 to 80 chars

## To Do — general
- [ ] Build reusable evaluation template from Prince Street analysis
- [ ] Create NS defaults config (CMHC tables, deed transfer tax, current rates)
- [ ] Add support for other provinces (ON, BC)
- [ ] Build universal Google Sheet export matching Graham's design (see templates/sheet-design-reference.md)
- [ ] Incorporate audit findings into revised analysis.md for Prince Street
- [ ] MODL zoning adapter (or municipal GIS scrape) — currently `null` for all MODL properties
- [ ] URL → analysis.md end-to-end automation (Phase 2 deterministic engine)

## Backlog — Deal Finder (Auto-Listing Scanner)
- [ ] **Daily listing scraper** — pull new listings from realtor.ca / viewpoint.ca matching criteria
  - Location: Lunenburg, South Shore NS, Halifax (configurable)
  - Type: multi-unit (duplex, triplex, fourplex), single-family with ADU potential
  - Price range: configurable ($300K-$600K default)
  - Minimum lot size for ADU potential (e.g., >0.1 acres)
- [ ] **Auto-scoring system** — each listing gets scored on:
  - Multi-unit potential (existing units, zoning for more)
  - ADU/expansion potential (lot size, zoning, setbacks)
  - Rental income offset potential (est. rent vs mortgage)
  - Obvious renovation ROI (outdated kitchens/baths, unfinished basement, no heat pump)
  - STR potential (walkability, tourist area, character/charm)
  - Value-add signals (estate sale, long DOM, price drops, motivated seller language)
- [ ] **Quick analysis** — top-scoring listings get a mini-evaluation (cash to close, estimated monthly cost, cap rate)
- [ ] **Daily digest** — Telegram summary of interesting new listings with scores and one-liner reasoning
- [ ] **Full evaluation trigger** — Graham says "analyze this one" and it runs the full pipeline
- [ ] **Data sources to investigate:**
  - realtor.ca API or scraping (they have an undocumented API)
  - viewpoint.ca (NS-specific, great data)
  - PVSC assessment data (Nova Scotia property assessments)
  - Zoning maps / municipal GIS for ADU feasibility
