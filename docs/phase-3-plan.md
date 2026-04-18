# Phase 3 Plan — Listing Ingestion & Auto-Analysis

> **Status:** Steps 0–7 shipped (deterministic TS utilities under
> `src/utils/` with 67 vitest cases, plus example criteria + MODL/HRM
> municipal configs). Steps 8–11 (source adapters + `/ingest-listing`
> skill) still to build — see "Post-MVP notes" and success criteria
> below. Mode B (scheduled discovery) comes after Mode A lands.

## Goal

Turn the "evaluate a property" workflow from a manual data-entry
exercise into a one-line command. Two modes:

- **Mode A (MVP):** paste a URL or raw listing text → full analysis
- **Mode B (later):** scheduled scan of configured sources → filter →
  auto-analyze matches → notify

Phase 3 ships Mode A. Mode B is architected-for but deferred until
Mode A proves useful.

---

## Design principles

1. **Source-agnostic.** NS-centric today, but anyone should be able
   to add their own jurisdiction (Montreal, Ontario, US) by dropping
   in a source adapter and a municipal config.
2. **Graceful degradation.** When scraping fails (anti-bot, layout
   changes), fall back to a paste-the-page flow that always works.
3. **No new infra.** Phase 3 runs entirely in Claude Code — no
   servers, no background daemons, no databases.

---

## Mode A — Paste / URL → Analysis

### Workflow

```
User: /ingest-listing https://viewpoint.ca/property/12345
         ├─ or ─
User: /ingest-listing
User: [pastes raw listing text/HTML]
```

1. Agent detects input shape (URL vs pasted content)
2. If URL: route to source adapter → fetch via WebFetch or browser MCP
3. If paste: route to the paste adapter (LLM extraction from raw text)
4. Extract fields into the `templates/evaluation-template.md` shape
5. Show user a parsed summary and ask for confirmation / corrections
6. If `config/criteria.md` exists, run hard-filter pre-screen
   (reject now, or flag for light vs full analysis)
7. Invoke the existing `/evaluate-property` skill with the populated
   input
8. Write outputs to `evaluations/<slug>/` as today
9. Append a one-line row to `evaluations/INDEX.md`

### Slug generation

`<street-num>-<street-slug>-<city-slug>`, e.g. `142-maple-lane-mahone-bay`.
Falls back to `<listing-id>-<source>` if address can't be parsed.

### Collision handling

If `evaluations/<slug>/` already exists, ask user: overwrite, create
`<slug>-v2/`, or skip.

---

## New files & folders

```
.claude/skills/
  ingest-listing/
    SKILL.md                       # new skill entry point

config/
  criteria.example.md              # template (committed)
  criteria.md                      # personal copy (gitignored)
  municipalities/
    modl.md                        # Lunenburg-district rules
    hrm.md                         # Halifax rules
    montreal.md                    # placeholder for QC
  provinces/
    qc.md                          # placeholder for QC

listings/
  sources/
    viewpoint.md                   # Viewpoint.ca adapter
    realtor-ca.md                  # Realtor.ca adapter (with anti-bot notes)
    centris-ca.md                  # Centris.ca adapter (QC, placeholder)
    paste.md                       # always-works fallback

evaluations/
  INDEX.md                         # auto-appended watchlist

docs/
  phase-3-plan.md                  # this file
```

---

## Source adapters

A source adapter is a markdown prompt that tells the agent:
- What fields live where on this source's pages
- What selectors / patterns to look for
- What the source's quirks are (anti-bot, French-language, etc.)
- How to extract photos and listing IDs

### Coverage for Phase 3 MVP

| Source        | Jurisdiction | Strategy                   | Notes                                    |
|---------------|--------------|----------------------------|------------------------------------------|
| Viewpoint.ca  | NS           | WebFetch + structured parse | Primary NS source, relatively open       |
| Realtor.ca    | Canada-wide  | Try → fall back to paste   | Aggressive anti-bot; expect blocking     |
| Paste         | Any          | LLM extraction             | Always works; used as fallback           |
| Centris.ca    | QC           | Placeholder for Phase 3.1  | French parsing needed                    |

---

## Criteria file

`config/criteria.example.md` shape (gitignored personal copy lives at
`config/criteria.md`):

```md
# My Evaluation Criteria

## Hard filters (reject if any fail)
- Units: >= 2
- Price: <= $600,000
- Location: MODL OR HRM
- Lot size: >= 0.08 acres
- Excluded zones: flood zone, industrial, arterial frontage

## Soft signals (flag in analysis)
- ADU potential:
  - Basement height >= 7 ft
  - Separate entrance exists or feasible
  - Lot >= 0.2 acres (garden-suite candidate)
- Upgrade potential:
  - Kitchen/bath described as "original"
  - Year built 1900-1950 (character + reno headroom)
  - Electrical panel not yet upgraded (easy win)
- Condition signals:
  - Roof < 10 years old
  - Heat pump already installed
  - Poured concrete foundation
```

The criteria file is **not** hard-coded into the scanner. It's parsed
on each run so the user can edit it freely. The pre-screen step
returns one of: `reject` (don't analyze), `light` (short-form eval),
`full` (full analysis).

For Mode A the criteria file is optional — paste anything and you get
an analysis regardless. The criteria hook is for Mode B, but adding
it now is cheap.

---

## Municipal configs

`config/municipalities/modl.md` and `hrm.md` should each capture:
- Property tax rate (if different from provincial average)
- STR bylaw status (currently allowed? pending changes?)
- ADU / secondary-suite rules
- Zoning categories that matter for multi-unit
- Deed transfer tax rate if municipal

These pull stuff out of `config/provinces/ns.md` that varies by
municipality. Reduces guesswork on the agent's part.

---

## Mode B — Scheduled discovery (sketch only)

Not in Phase 3 scope. Sketching so Mode A doesn't paint us into a
corner:

- `.claude/scheduled/scan-listings.md` — scheduled task definition
- Runs daily, hits each configured source
- Applies hard-filter to listing-list pages first (cheap)
- Full analysis only for passes
- Writes daily digest to `digests/YYYY-MM-DD.md`
- Notification (Phase 3.2):
  - Email via SMTP or GitHub Action
  - Telegram via bot token in `.env`

For Phase 3 MVP, don't build the scheduler — just make sure the
Mode A skill is callable from one eventually.

---

## Open questions

1. **Re-running an existing listing** — when you paste a URL you've
   already analyzed, do we auto-update (price drop) or refuse?
   Default: show diff, ask.
2. **Photos** — store locally (`evaluations/<slug>/photos/`) or just
   reference URLs? URLs die; local costs disk. **Default: save
   locally.**
3. **Rent info missing from listing** — most owner-sale listings
   don't show rent. Prompt user to enter, or assume market?
   **Default: prompt, with market-rate suggestion.**
4. **Non-English listings (Montreal)** — auto-translate via agent,
   or require user to paste English-translated version?
   **Default: agent translates inline during extraction.**

---

## Out of scope for Phase 3

- Watchlist UI (a plain `INDEX.md` is enough)
- Comparisons between properties (Phase 4 candidate)
- Post-close actuals tracker (defer until first purchase)
- The TypeScript deterministic engine (still Phase 2, separate)

---

## Success criteria for Phase 3

- [ ] `/ingest-listing <viewpoint-url>` produces a full
      `evaluations/<slug>/` folder end-to-end
- [ ] `/ingest-listing` with pasted text works even when the URL
      fetch is blocked
- [x] `criteria.md` is parsed and hard-filters actually reject
      *(parser `src/utils/criteria.ts` + screener `src/utils/screen.ts`
      shipped with vitest; still need skill wiring to call them)*
- [x] `INDEX.md` appender shipped as `src/utils/index-md.ts` with
      vitest *(skill wiring pending)*
- [ ] At least one MODL and one HRM listing run successfully
- [ ] Someone in Montreal could add `centris-ca.md` +
      `config/provinces/qc.md` without touching any existing code
      *(municipal config slot shipped; adapter slot still to build)*

---

## Implementation plan (red/green TDD)

### Test strategy

This project is primarily agent-driven markdown, so "tests" come in
two flavors:

1. **Unit tests (deterministic pieces).** Pure functions — slug
   generation, criteria parsing, INDEX.md row formatting, collision
   detection — live in TypeScript with `vitest`. Fast, cheap, run on
   every change. Seeds Phase 2's deterministic engine without
   committing to it yet.
2. **Agent tests (LLM-bound pieces).** Field extraction from listing
   text, Viewpoint page parsing, end-to-end skill orchestration. Use
   fixture inputs + schema-validation + golden-file snapshots. Slower,
   cost API calls, run on demand.

Each step below is sized to a single PR. Land them in order; merge
when tests pass and docs updated.

---

### Step 0 — Test harness scaffolding

**Red (failing state):** no `npm test` command. No `tests/` layout.

**Green (what ships):**

- `package.json` with `vitest`, `tsx`, and a `test` script
- `tsconfig.json` — minimal, ES modules, strict
- `src/utils/` directory (empty stub)
- `src/utils/__tests__/smoke.test.ts` — one trivial test (`expect(true).toBe(true)`)
- `tests/agent/` directory (empty; for later LLM-bound fixtures)
- `tests/agent/run.sh` — stub shell harness that echoes "no agent
  tests yet" and exits 0
- `.gitignore` updated with `node_modules/`, `dist/`, `coverage/`
- README Quickstart updated to mention `npm install && npm test`

**Acceptance:**

- `npm install` succeeds
- `npm test` runs vitest, one test passes
- `./tests/agent/run.sh` runs and exits 0
- CI-ready (even if no CI yet)

---

### Step 1 — Slug generator

**Red:** `src/utils/__tests__/slug.test.ts` with table-driven cases:

| Input                                       | Expected                          |
|---------------------------------------------|-----------------------------------|
| `"142 Maple Lane, Mahone Bay, NS"`          | `"142-maple-lane-mahone-bay"`     |
| `"9 Prince St, Lunenburg, NS"`              | `"9-prince-st-lunenburg"`         |
| `"1234 Rue St-Denis, Montréal, QC"`         | `"1234-rue-st-denis-montreal"`    |
| `"Lot 5, Back Road, Chester, NS"`           | `"lot-5-back-road-chester"`       |
| `""` (empty address)                        | throws `InvalidAddressError`      |
| `{listingId: "MLS-12345", source: "RLTR"}`  | `"mls-12345-rltr"` (ID fallback)  |

All tests RED.

**Green:** `src/utils/slug.ts` exports `slugify(address: string): string`
and `slugFromListingId(id: string, source: string): string`. Handle:
accent normalization (é → e), remove commas + province codes,
lowercase, kebab-case, strip empty tokens.

**Acceptance:** all table rows green. No slug exceeds 60 chars. No
external deps.

---

### Step 2 — Input.md schema validator

**Red:** `src/utils/__tests__/validate-input.test.ts` with fixtures:

- `tests/fixtures/input/valid-duplex.md` — should pass validation
- `tests/fixtures/input/missing-price.md` — should fail with
  `PRICE_MISSING`
- `tests/fixtures/input/bad-units-table.md` — should fail with
  `UNITS_TABLE_MALFORMED`
- `tests/fixtures/input/valid-minimal.md` — all required fields,
  no optionals

**Green:** `src/utils/validate-input.ts` parses a markdown file
against the `templates/evaluation-template.md` schema. Returns
`{valid: true}` or `{valid: false, errors: [...]}`. Covers required
fields (address, price, units, year built) and basic shape (units
table has N rows).

**Acceptance:** fixture-driven; the validator is reusable by all
downstream ingestion steps.

---

### Step 3 — Criteria parser

**Red:** `src/utils/__tests__/criteria.test.ts` using fixtures from
`config/criteria.example.md` and variants:

- Parse the example file → expected structured rules (hard filters,
  soft signals)
- Parse a minimal criteria with only hard filters
- Parse an invalid criteria file (malformed) → errors

**Green:** `src/utils/criteria.ts` exports `parseCriteria(markdown: string): Criteria`.
`Criteria` type distinguishes hard filters (`units >= 2`, `price <= 600000`)
from soft signals (`basement_height >= 7ft`, `kitchen_original`). Uses
regex on the well-structured markdown form, not LLM.

**Acceptance:** deterministic; parses the example; rejects obviously
broken files.

---

### Step 4 — Criteria screener

**Red:** `src/utils/__tests__/screen.test.ts` pairing parsed
criteria × parsed property facts → expected verdict:

- Duplex at $425K in MODL with ADU potential → `full`
- Duplex at $425K in MODL without ADU potential → `full` (hard pass,
  soft fail just absent)
- Single-family at $425K in MODL → `reject` (hard filter fails)
- Duplex at $850K in MODL → `reject` (price cap)
- Duplex at $425K outside jurisdiction → `reject`

**Green:** `src/utils/screen.ts` exports
`screenListing(property: PropertyFacts, criteria: Criteria): 'reject' | 'light' | 'full'`.
Pure function.

**Acceptance:** covers all `reject` paths; `light` is unused in MVP
but reserved for future short-form analysis.

---

### Step 5 — INDEX.md appender

**Red:** `src/utils/__tests__/index-md.test.ts`:

- Given empty `INDEX.md` template + one eval record → expected output
  with header + one row
- Given existing `INDEX.md` with 2 rows + new eval → 3 rows, sorted by
  date descending
- Given a row that already exists (same slug) → update in place
- Malformed existing `INDEX.md` → clear error, don't corrupt

**Green:** `src/utils/index-md.ts` exports
`appendOrUpdate(existing: string, record: EvalRecord): string`.
Pure string-in/string-out.

**Acceptance:** idempotent; row format stable; markdown still lints.

---

### Step 6 — Collision detector

**Red:** `src/utils/__tests__/collision.test.ts`:

- `evaluations/foo/` does not exist → `{exists: false}`
- `evaluations/foo/` exists with same price → `{exists: true, priceChanged: false}`
- `evaluations/foo/` exists with different price → `{exists: true, priceChanged: true, oldPrice, newPrice}`
- `evaluations/foo/` exists but `input.md` malformed → `{exists: true, unparseable: true}`

**Green:** `src/utils/collision.ts` exports
`checkCollision(evalDir: string, incoming: PropertyFacts): CollisionResult`.
Reads existing `input.md`, compares key fields.

**Acceptance:** doesn't mutate anything; purely diagnostic.

---

### Step 7 — Municipal config loader

**Red:** `src/utils/__tests__/municipal.test.ts`:

- `"Mahone Bay, NS"` → loads `config/municipalities/modl.md`
- `"Halifax, NS"` → loads `config/municipalities/hrm.md`
- `"Chester, NS"` → loads `config/municipalities/modl.md` (district-level)
- `"Sydney, NS"` → returns province-level only (`ns.md`), logs
  "no municipal config"
- `"Montréal, QC"` → loads `config/municipalities/montreal.md`
  (placeholder in Phase 3, real later)

**Green:** `src/utils/municipal.ts` exports
`loadMunicipalConfig(city: string, province: string): MunicipalConfig | null`.
Map of city → municipality file. Also write the two NS configs
(`modl.md`, `hrm.md`) with minimally useful content; `montreal.md` is
a "TODO: populate" placeholder.

**Acceptance:** known cities route correctly; unknowns degrade
gracefully; placeholder configs are valid markdown.

---

### Step 8 — Paste adapter (agent-test)

Moves from unit-tests to **agent-tests** — LLM is involved.

**Red:** `tests/agent/fixtures/paste-listings/`:

- `duplex-mahone-bay/input.txt` — synthetic pasted listing text
- `duplex-mahone-bay/expected-facts.json` — expected extracted fields
  (address, price, beds, baths, units, year-built, lot-size,
  property-tax, description-excerpt)
- `duplex-mahone-bay/expected-input.md` — full expected `input.md`
  (golden snapshot)
- Similar fixtures for `sfh-halifax/` and `triplex-bridgewater/`

`tests/agent/run.sh` invokes the paste adapter via `claude -p`
(non-interactive) and compares outputs. Expected state at red: no
adapter exists, tests fail with "adapter not found."

**Green:**

- `listings/sources/paste.md` — adapter prompt defining extraction
  rules, output format, field precedence, error handling
- The `/ingest-listing` skill (stub at this point) routes pasted text
  to this adapter
- Golden snapshots captured from first passing run

**Acceptance:**

- Hard fields (price, beds, units) match expected exactly
- Soft fields (description) present but not byte-compared
- `validate-input.ts` passes on the produced `input.md`
- Known edge case: listings missing rent info → adapter inserts a
  `[PROMPT USER]` marker rather than guessing

**Note on flakiness:** LLM extraction is non-deterministic. Tests
allow 2 retries; if flaky, tighten the adapter prompt before
increasing retry count.

---

### Step 9 — Viewpoint adapter (agent-test + fetch)

**Red:** `tests/agent/fixtures/viewpoint/`:

- `property-12345/snapshot.html` — saved Viewpoint HTML page
  (committed, no live fetch in tests)
- `property-12345/expected-facts.json` and `expected-input.md`
- 2–3 additional property snapshots covering SFH/duplex/multi-unit

**Green:**

- `listings/sources/viewpoint.md` — adapter prompt with Viewpoint
  selectors/patterns
- Live fetch path: `WebFetch` with configured UA, retry-once
- Test path: load local HTML file instead of fetching
- Route in the skill: Viewpoint URL → viewpoint adapter

**Acceptance:**

- All three snapshot fixtures produce passing `input.md`
- Live fetch of an arbitrary Viewpoint URL works in manual test
  (document the command in the PR)
- If live fetch fails (403/blocked), skill falls through to paste
  fallback with a clear message

---

### Step 10 — realtor.ca adapter + fallback

**Red:** `tests/agent/fixtures/realtor/`:

- `blocked-response.html` — a fixture that simulates anti-bot response
- Expected behavior: skill detects block, prompts user to paste
- Additionally: `happy-path-snapshot.html` — if we ever get through,
  expected extraction

**Green:**

- `listings/sources/realtor-ca.md` — adapter with extraction rules
  AND fallback protocol
- Skill: try WebFetch with realistic UA; detect 403/CAPTCHA markers;
  prompt user to paste raw page text; reroute to paste adapter

**Acceptance:**

- Simulated block → fallback path engages, user-facing message is
  clear
- Happy-path snapshot → correct extraction
- No retry storms (max 1 retry on live fetch)

---

### Step 11 — `/ingest-listing` skill orchestration

Everything composed.

**Red:** `tests/agent/fixtures/end-to-end/`:

- `paste-duplex/input.txt` + expected final `evaluations/<slug>/`
  structure (not byte-exact, just structural: all expected files
  present, input.md validates, analysis.md has TL;DR section, etc.)
- `url-viewpoint/url.txt` (containing a URL that points to a local
  fixture server) + expected final structure
- `collision-rerun/` — pre-existing eval folder + re-ingest →
  expected prompt and user-chooses-overwrite behavior

**Green:** `.claude/skills/ingest-listing/SKILL.md` orchestrating:

1. Detect URL vs pasted text
2. Route to correct adapter
3. Extract → produce `input.md` draft
4. Show user the summary, wait for confirmation/corrections
5. Run `checkCollision`
6. If `criteria.md` exists, run `screenListing`; handle `reject` by
   writing a short `<slug>/skipped.md` rationale
7. Invoke `/evaluate-property` on the approved input
8. Append `INDEX.md` row via `index-md.ts`

**Acceptance:**

- All three end-to-end fixtures produce correctly-shaped outputs
- Manual smoke test: real Viewpoint URL + real paste both work
- Updated README documents `/ingest-listing` usage

---

### Step 12 — Documentation + cleanup

**Red:** README still implies Mode A is a roadmap item. Phase 2/3
status table in SPEC still marks `/ingest-listing` as not-built.

**Green:**

- README: move `/ingest-listing` into "Quickstart" with examples
- SPEC: update status table
- Add a short `evaluations/INDEX.md` starter file (or leave for the
  first ingest to create it)
- Update `docs/phase-3-plan.md` to mark MVP complete; sketch Phase
  3.1 (Mode B) as "next"

**Acceptance:**

- Docs match reality
- A new user can follow the README to ingest their first listing

---

## Commit/PR strategy

- One PR per step, in order
- Each PR: its own tests passing, all previous tests still passing
- Small PRs are easier to revert if an adapter gets flaky
- Commit message format: `feat(ingest): Step N — <step-name>`

## Rough effort estimate

| Step | Complexity | Notes                                |
|------|-----------|--------------------------------------|
| 0    | S         | One-time scaffolding                 |
| 1    | S         | Pure function                        |
| 2    | S         | Parser + schema                      |
| 3    | S         | Parser                               |
| 4    | S         | Pure logic                           |
| 5    | S         | String manipulation                  |
| 6    | S         | File I/O + compare                   |
| 7    | M         | Plus writing MODL + HRM configs      |
| 8    | M         | First LLM-bound test; prompt tuning  |
| 9    | M         | Fetch + parse; snapshot management   |
| 10   | M         | Fallback logic                       |
| 11   | L         | Orchestration, end-to-end fixtures   |
| 12   | S         | Docs                                 |

Total: ~2–4 focused sessions for a solo developer. Parallelizable
after Step 2 (Steps 3–7 are independent pure-function islands).

---

## Shipping log

Steps 0–7 shipped as originally planned — deterministic TS utilities
landed under `src/utils/` with 67 vitest cases, plus the example
criteria file and MODL/HRM/Montreal municipal configs.

Steps 8–11 are **next up** and will simplify from the plan above:
skip the agent-test harness, ship the three source adapters as
prompt files (`listings/sources/*.md`) plus an orchestrating
`.claude/skills/ingest-listing/SKILL.md`, and validate by eye on
real listings rather than with golden-file snapshots. Rationale:
LLM extraction prompts churn as they hit real listings, so snapshots
written before real-world validation would lock in extractions that
haven't been vetted yet. Revisit test harness once the adapter
prompts stabilize.

The viewpoint adapter needs two real-world findings baked in:

- **URL architecture:** short URLs like `viewpoint.ca/<code>` redirect
  to `/map#<base64-json>` which is a JS-rendered SPA (no useful
  server-side HTML). The canonical pattern
  `viewpoint.ca/property/<pid>` redirects to
  `/cutsheet/<listing_id>/1/<slug>` which IS server-rendered.
  Prefer the cutsheet URL for WebFetch.
- **Hallucination risk:** fields like `year_built`, `annual_taxes`,
  `heating`, `foundation` are present in cutsheet HTML only as
  unresolved handlebars templates (`{{ entry.year_built || 'N/A' }}`)
  — they load client-side via JS. The adapter MUST mark these
  `unknown` and `[PROMPT USER]` rather than letting the LLM infer
  them from description text. The price, address, beds/baths, living
  area, listing_id, and full remarks (via `application/ld+json`) are
  reliably extractable.

---

## Phase 3.1 — after Mode A lands (Mode B + Centris)

The natural next targets once Mode A has real-world miles on it:

### Scheduled discovery

- `.claude/scheduled/scan-listings.md` — scheduled task definition
- Configure source URLs per municipality (Viewpoint search result
  pages, realtor.ca saved-search feeds)
- Apply hard-filter to listing-list pages first (cheap) before
  per-listing fetch
- Full analysis only for passes
- Writes daily digest to `digests/YYYY-MM-DD.md`
- Notification:
  - Email via SMTP or a GitHub Action
  - Telegram via bot token in `.env`

### Centris.ca + Québec

- Flesh out `listings/sources/centris-ca.md` with French label map,
  JSON-LD parsing, anti-bot detection
- Create `config/provinces/qc.md` covering welcome tax (taxe de
  bienvenue) tiers, TAL rental rules, Québec-specific CMHC nuances
- Populate `config/municipalities/montreal.md` with borough-level
  STR bylaws and zoning categories that matter for plex purchases

### Nice-to-have

- Photo download (`evaluations/<slug>/photos/`) option per open
  question #2
- Rerun-existing-listing diff view (open question #1)
- Filter/sort views on `INDEX.md` (still just one file; tooling on top)
