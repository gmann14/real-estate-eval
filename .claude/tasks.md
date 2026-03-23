# Real Estate Eval — Tasks

## Completed
- [x] 9 Prince Street Lunenburg — full analysis (6 scenarios, stress tests, rent-vs-buy) — 2026-03-20

## To Do
- [ ] Build reusable evaluation template from Prince Street analysis
- [ ] Create NS defaults config (CMHC tables, deed transfer tax, current rates)
- [ ] Add support for other provinces (ON, BC)
- [ ] Build universal Google Sheet export matching Graham's design (see templates/sheet-design-reference.md)
- [ ] Incorporate audit findings into revised analysis.md for Prince Street

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
