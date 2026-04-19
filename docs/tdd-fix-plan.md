# TDD Fix Plan — Tier-B Extractor + Analysis Gaps

> **Context:** The Tier-B extractor at [src/ingest/viewpoint-tier-b.ts](../src/ingest/viewpoint-tier-b.ts)
> shipped on 2026-04-19 and pulled real data for 56 Montague, 94 King,
> and 69 Fox. The resulting analyses changed materially. This document
> catalogs the remaining bugs, plans red/green fixes, and stress-tests
> the plan before implementation.

## Known bugs (from real 3-property run)

Classified by impact + TDD-ability:

### Code bugs (testable)

| # | Bug | Evidence | Root cause |
|---|-----|----------|------------|
| 1 | Listing-agent extractor returns ViewPoint house agent for non-VP brokerages | 69 Fox (brokerage: Sotheby's) returns `"STEPHANIE DEVRIES"` with ViewPoint REALTOR® tag | The `/REALTOR®/` scan matches ViewPoint's page-chrome widget (which shows their house agent on every listing). Need to cross-check against `LISTED BY` brokerage before assigning. |
| 2 | Heritage designation returns `null` when description clearly states it | 69 Fox description: *"Recognized as a Provincial Heritage Property"* — `heritageDesignated: null` | ViewPoint has no structured heritage field. Need a description-text fallback scan. |
| 3 | Listing events contain duplicates | 69 Fox events: `"Mar 31, 2025"` + `"Expired — listed"` + `$849,000` appears twice; same for `"Oct 1, 2025"` | The `LISTING HISTORY` walker matches both a primary block and a repeat section that ViewPoint renders for collapsed entries. No dedupe step. |
| 4 | Event label defaults to `"<Status> — listed"` fallback | Many 69 Fox events labeled `"Expired — listed"` when the real event is a price change or status transition | Fallback logic picks up the `lastStatus` when no `/change\|status\|price/i` text is found within 3 lookahead lines. Too eager. |

### Documentation-only bugs (not TDD-testable, just missing edits)

| # | Bug | Scope |
|---|-----|-------|
| 5 | 94 King OIL OPEX delta flowed through Scenario A only; B/C/D tables still show Pass 2 numbers | [evaluations/94-king-street-lunenburg/analysis.md](../evaluations/94-king-street-lunenburg/analysis.md) |
| 6 | 69 Fox D-Inn scenario math doesn't reflect no-central-heat + cedar-shake roof revisions | [evaluations/69-fox-street-lunenburg/analysis.md](../evaluations/69-fox-street-lunenburg/analysis.md) |
| 7 | 56 Montague scenario table references electric-heat savings in prose but scenarios untouched | [evaluations/56-montague-street-lunenburg/analysis.md](../evaluations/56-montague-street-lunenburg/analysis.md) |

### Known gaps (document, don't fix today)

| # | Gap | Why defer |
|---|-----|-----------|
| 8 | Zoning returns `null` for all NS MODL properties | ViewPoint doesn't surface zoning. Real fix requires a MODL planning adapter or description-scan heuristic. Document as `[PROMPT USER]` in ingest template. |
| 9 | No URL → analysis.md automation — only URL → input.md | Full analysis generation from structured input is Phase 2 (deterministic TS engine). Today, agent authors analysis.md in multi-pass — acceptable for current v0.1. |
| 10 | Zero test coverage on `src/ingest/*.ts` | Addressed by this plan (refactor + unit tests on parser). |
| 11 | Details-dict key length capped at 60 chars (`ci < 60`) | No real case hits this; bump to 80 and add a unit test guard. Low priority. |

---

## Refactor plan — make parsing testable

The current extractor stuffs a ~140-line JavaScript source string into
`page.evaluate`, making the parsing logic impossible to unit-test
directly. Before writing tests:

**Extract `parseViewpointBody(text: string, details: Record<string,string>): ParsedViewpoint`**
into `src/ingest/parse-viewpoint.ts`.

- The `page.evaluate` step stays minimal — it only reads
  `document.body.innerText` and builds the `details` dict from
  `LABEL:VALUE` lines (simple, DOM-bound, no logic).
- All listing-event parsing, agent extraction, heritage detection, and
  field selection moves to the pure parser.
- `ParsedViewpoint` matches the current TierBData shape minus the
  browser-bound fields (`url`, `pid`, `fetchedAt`, `warnings`).
- Unit tests in `src/ingest/__tests__/parse-viewpoint.test.ts` load
  fixtures from `evaluations/.tier-b/all.json` (already captured real
  page text from the 3-property run).

**Why this architecture:**

- Keeps the Playwright call simple and flake-resistant.
- Parser becomes pure TS — fast vitest, no browser.
- Future source adapters (realtor.ca, centris.ca) can follow the same
  split: DOM-read in Playwright, parse in Node.

---

## Red/green plan per bug

### Bug 1 — Listing agent false positive

**Red:** `it('returns null for non-VP brokerages when only VP house agent is visible')`
with 69 Fox fixture. Expected: `listingAgentName` is `null` (or a
specific non-VP name if we can parse one), NOT `"STEPHANIE DEVRIES"`.

**Green:**

```ts
function extractListingAgent(lines: string[], brokerage: string | null) {
  const isViewpointBrokerage = brokerage?.toLowerCase().includes('viewpoint');
  // Look for REALTOR® marker
  for (let i = 0; i < lines.length; i++) {
    if (!/REALTOR®/.test(lines[i])) continue;
    const prev = lines[i - 1] ?? '';
    // Reject VP's house agent widget unless this IS a VP-brokered listing
    if (!isViewpointBrokerage && prev === 'STEPHANIE DEVRIES') continue;
    if (prev.length < 60 && /^[A-Z\s.'-]+$/.test(prev)) return prev;
  }
  return null;
}
```

**Acceptance:** 56 Montague + 94 King (both VP-brokered) still return
`"STEPHANIE DEVRIES"`. 69 Fox (Sotheby's) returns `null`.

### Bug 2 — Heritage from description

**Red:** `it('extracts heritage designation from description text')`
with 69 Fox fixture. Expected: `heritageDesignated` contains
`"Provincial Heritage Property"` or similar.

**Green:** In the parser, after structured-field lookup fails, scan
`rawSummaryText` for regex patterns:

- `/Provincial Heritage Property/i` → `"Provincial Heritage Property"`
- `/UNESCO World Heritage/i` → add as separate `heritageContext` field
- `/Municipally Designated Heritage|Municipal Heritage Property/i` → municipal designation

**Acceptance:** 69 Fox detects Provincial Heritage. 56 Montague and
94 King return `null` (neither description mentions formal designation,
despite being inside the UNESCO district — those are **context**, not
**designation**).

### Bug 3 — Listing event dedupe

**Red:** `it('deduplicates listing events with identical date+event+price')`
with 69 Fox fixture. Expected: no two events share all three fields.

**Green:** After event collection, dedupe using
`JSON.stringify({date, event, price})` as the key. Preserve first
occurrence (since the primary block is parsed first).

**Acceptance:** 69 Fox events shrink from 41 to ~30 (unique entries).
56 Montague and 94 King unchanged (no duplicates there).

### Bug 4 — Event label fallback

**Red:** `it('does not label price-change rows as "Expired — listed"')`
with 69 Fox fixture. Expected: every event with a `Price change from X to Y`
line in the lookahead should label the event as that change, not as
"Expired — listed".

**Green:** Reorder the lookahead: check for `Price change`, `Status change`,
`Sold`, `Withdrawn` descriptions BEFORE falling back to `lastStatus`.
Only use fallback when no lookahead line matches any pattern.

**Acceptance:** 69 Fox events include `"Price change from $959,000 to $899,000"`
instead of `"Expired — listed"` at the `Jun 20, 2025` row.

### Bug 11 — Details key length

**Red:** `it('extracts labels up to 80 chars')` with a synthetic line
containing a 65-char `LABEL:VALUE`. Expected: label appears in the
`details` dict.

**Green:** Change `ci < 60` → `ci < 80`. No other logic change.

**Acceptance:** The 60-char limit test fails today, passes after
the fix. No regression on the 3 real fixtures.

---

## Doc-only fixes (bugs 5, 6, 7)

No tests — just careful Edit passes on each analysis.md:

- **94 King:** Recompute monthly OPEX in Scenario B/C/D tables adding
  the +$140/mo delta (+$75 heating, +$65 insurance) from oil heat.
- **69 Fox:** Recompute D-Inn scenario with heating delta (-$80/mo
  for no central heat, +reserve for cedar-shake replacement at
  $30-40K over ~10 years = +$250/mo reserve).
- **56 Montague:** Recompute all scenarios with electric-heat savings
  (-$120/mo) and revised insurance (-$50/mo).

These are edits, not code. They land in the same commit series so the
analysis files are coherent.

---

## Stress-test of the plan

Before implementing, poke at the plan:

**Q: Is the parser refactor worth the diff noise?**

Yes. Today the parsing logic is untestable unless you spin up a
browser + authenticated VP session per test. That's impractical.
Moving parsing to pure TS lets us:
- Write 10 tests in ~5 min instead of 10 tests in ~2 hours
- Iterate on edge cases without login flakiness
- Reuse fixtures across future adapters

**Q: What if the VP house-agent heuristic breaks when VP changes the page?**

It's fragile. Mitigation: the check is narrow — only excludes the
exact name `STEPHANIE DEVRIES` when brokerage is non-VP. If VP rotates
agents or changes the widget, the worst case is we go back to
returning their house agent. That's no worse than today.

A more robust fix would parse the `LISTED BY` field and only trust
agent names that appear near that brokerage block. Deferred — real
listings don't render agent name near brokerage in the HTML body;
it's in a cutsheet PDF we'd need to fetch separately.

**Q: Could heritage description-scan false-positive?**

Yes. If a Lunenburg listing description mentions "surrounded by
provincial heritage properties" without the subject property being
one, we'd misclassify. Mitigation: require the phrase to be a
standalone declarative (e.g., not preceded by "near", "surrounded by").
Add a negative-match guard in the regex.

Still, heritage detection from prose is inherently probabilistic. The
output should say `"heritageDesignated: Provincial Heritage Property
(extracted from description — verify with municipality)"`, not claim
authoritative knowledge.

**Q: Does dedupe risk dropping legitimate repeat events?**

No. A genuine re-listing event would have a different date. Only
identical `{date, event, price}` triples are dropped, which by
definition are duplicates.

**Q: What about the non-code analysis.md edits?**

Those depend on judgement calls (what's the right reserve for a
cedar shake roof in Lunenburg? What does electric heat actually cost
there?). The numbers from the Tier-B pass need to be committed to
memory first — memory/feedback_tier-b-opex-deltas.md captures the
deltas used.

The risk here: if I edit these files rapid-fire, I may introduce
math errors. Mitigation: update each scenario one row at a time,
running the new total by hand and spot-checking against
`src/analysis/cli.ts` for anything mortgage-related.

**Q: Should the URL → analysis.md gap be in scope?**

No. That's Phase 2 (deterministic engine). Today's `/ingest-listing`
skill does URL → input.md → agent-authored analysis.md. Known
limitation, documented in SPEC.md. A scaffolded `build-input.ts` that
calls the Tier-B extractor and merges into the input template would
be valuable, but it's a new feature, not a bug fix.

**Q: Should zoning get a fix?**

Not this round. Real zoning data lives in MODL's planning system —
that's a separate adapter. Today mark as `[PROMPT USER]` gap in the
input template and document in SPEC known-gaps.

---

## Commit strategy

1. `refactor(ingest): extract pure parseViewpointBody from Tier-B evaluator`
2. `test(ingest): snapshot 3 real Tier-B fixtures for parser tests`
3. `fix(ingest): reject VP house agent on non-VP brokerages (#1)`
4. `fix(ingest): scan description for heritage designation (#2)`
5. `fix(ingest): dedupe listing events + strengthen event labels (#3, #4)`
6. `fix(ingest): bump details key length to 80 (#11)`
7. `fix(analysis): flow Tier-B OPEX deltas through 94 King scenarios (#5)`
8. `fix(analysis): flow heating/roof deltas through 69 Fox D-Inn (#6)`
9. `fix(analysis): recompute 56 Montague scenarios with electric-heat delta (#7)`
10. `docs: update SPEC, tasks, viewpoint adapter for Tier-B + known gaps`

Each commit runs typecheck + vitest clean before landing.

---

## Out of scope (deferred items)

- MODL zoning adapter (new data source)
- URL → full analysis.md automation (Phase 2)
- Agent-extraction fixtures for realtor.ca / centris.ca (Phase 3.1)
- Tier-B extractor for realtor.ca (requires different login + page structure)
- Price-drop watcher (Phase 3.1 Mode B)

---

*This plan stress-tested. Proceeding with implementation in order above.*
