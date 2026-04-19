# Viewpoint.ca Adapter

> Primary NS source. Public, relatively scrape-friendly, but has three
> URL shapes with meaningfully different scrapeability.

## URL architecture (verified 2026-04)

Viewpoint serves listings under three URL shapes. **The shape matters
for whether WebFetch will return useful content:**

| URL shape | Example | Server-rendered? | Use for WebFetch? |
|-----------|---------|------------------|-------------------|
| Short code | `viewpoint.ca/VgJkv` | **No** — 307-redirects to `/map#<base64>`, which is a JS-rendered SPA shell. Raw HTML is the map template, not the listing. | **No.** Decode the base64 fragment to get `pid`, then use the `/property/<pid>` shape below. |
| Property ID | `viewpoint.ca/property/60063062` | Redirects (302) to a cutsheet URL. | Yes — follows the redirect automatically. |
| Cutsheet (canonical) | `viewpoint.ca/cutsheet/<listing_id>/1/<slug>` | **Yes** — the fully rendered detail page. | Yes — prefer this form when you have the listing_id. |

**Recovery path if you only have a short URL:**

1. `curl -sI <short-url>` to read the `Location:` header — it points at
   `/map#<base64>`.
2. Base64-decode the fragment. You'll get JSON like
   `{"summary":{"property":{"pid":"<PID>"}},"overview":{"listing":{"listing_id":"<ID>"}}}`.
3. Fetch `viewpoint.ca/property/<pid>` (or the cutsheet URL if you
   have the listing_id) — this is what WebFetch can actually read.

## Fetch strategy

1. **Normalize the URL first** using the recovery path above if you
   were given a short code. Feeding a short URL directly to WebFetch
   will return the SPA shell and fabricated data.
2. **WebFetch the cutsheet or `/property/<pid>` URL.** Most of the
   listing *summary* is rendered server-side in these shapes — see
   the "Reliably present in the cutsheet HTML" list below.
3. **For Tier-A enrichment (age, lot, taxes, assessment, DOM,
   listing history):** use the Playwright MCP (`mcp__playwright__*`).
   - `browser_navigate` to `/property/<pid>` (auto-redirects to the
     cutsheet URL).
   - `browser_wait_for` ~5 seconds for the JS bundle to populate the
     summary panel.
   - `browser_evaluate` against `document.body.innerText` and regex
     out the labelled fields. The summary block is consistent across
     Lunenburg-area listings:
     `BEDROOMS / BATHROOMS / AGE / MLA/TLA / EST. MORTGAGE / PRICE/SQ. FT. / <YEAR> ASSESSMENT & TAX / LOT SIZE / LISTING HISTORY / HISTORICAL ASSESSMENT / BUILDING PERMITS`.
   - `browser_close` when done. One Playwright session can serve
     multiple listings sequentially — reuse it.
4. **For Tier-B fields (zoning, heating, foundation, water/sewer,
   roof, basement, building style, listing-event log, heritage flag):**
   use the dedicated extractor at `src/ingest/viewpoint-tier-b.ts`.
   It uses Playwright with a persistent session (`.session/viewpoint.json`)
   and reads credentials from macOS Keychain (service `viewpoint.ca`,
   account configurable via `--account=<email>`). One-time setup:
   ```sh
   security add-internet-password -s viewpoint.ca \
     -a graham_mann14@hotmail.com -r htps -T '' -U -w
   # (paste password when prompted)
   ```
   Then:
   ```sh
   npx tsx src/ingest/viewpoint-tier-b.ts \
     https://www.viewpoint.ca/property/60063062 \
     --out=evaluations/.tier-b/<slug>.json
   ```
   Subsequent runs reuse the saved session — no re-login. Use
   `--force-login` to refresh, `--headed` to debug.
5. **On 403 / CAPTCHA / rate-limit:** fall through to the paste
   adapter (`listings/sources/paste.md`).
6. **Max 1 retry** on transient failures. No retry storms.

## What is and isn't server-rendered (critical — verified 2026-04)

**Reliably present in the cutsheet HTML** (safe to extract via WebFetch):

- `list_price`, `address`, `civicnum`, `street`, `city`, `pid`,
  `listing_id`
- `nbeds`, `nfullbaths`, `nhalfbaths`, `tla` (total living area
  sq ft), `mla` (main living area sq ft)
- `list_dt`, `update_dt`
- `listing_b1` (brokerage name)
- Full remarks text: parse the `<script type="application/ld+json">`
  block and read the `description` field. Postal code, geo, and the
  full image array also live in this JSON-LD block.
- `pix_count` (photo count) and individual image URLs under
  `viewpoint.ca/media/...`

**Loaded client-side via JS and NOT present in raw HTML** — these
appear as unresolved handlebars templates like
`{{ entry.year_built || 'N/A' }}` and split into two tiers:

*Tier A — public after JS render (extractable via Playwright with no login):*

- `age` (years since built — derive `year_built = current_year − age`)
- `lot_sqft` (rendered as e.g. `2,153 sqft`)
- Current-year `assessment_value` and `annual_taxes` (e.g.
  `2026 ASSESSMENT & TAX  $683,900  $9,410`)
- `days_on_market`
- Listing-history event count (e.g. `12 events over 17 years`) and
  historical-assessment growth (e.g. `51% increase (2022-2026)`)
- Building permit count (often `N/A` in MODL towns)
- `est_mortgage_monthly` (Viewpoint's own estimate — do not use as a
  payment figure; use `src/analysis/cli.ts` for canonical math)
- Price/sqft

*Tier B — login-gated (still handlebars after Playwright render
without a logged-in session — extractable via `src/ingest/viewpoint-tier-b.ts`):*

- `zoning` / `mls_zoning` — **note:** ViewPoint doesn't actually
  populate this field for MODL listings; comes back `null` even with
  full Tier-B access. Treat as a known gap, not a bug.
- `heating` type, `fuel_supply`
- `foundation`, `basement`, `roof`
- `water`, `sewer`
- `building_style`, `property_sub_type`, `exterior`, `flooring`
- `commission`, `occupancy`, `possession`
- `listing_owners` / `provincial_owners`
- Listing-agent name + phone — **caveat:** ViewPoint shows their
  house agent (Stephanie DeVries) in the page chrome on every
  listing. The extractor cross-checks against `LISTED BY` brokerage
  to suppress this on non-VP-brokered listings. Always verify the
  agent name against the brokerage shown.
- Heritage designation — VP rarely populates the structured field
  even for heritage properties. The extractor falls back to
  description-text scanning for "Provincial Heritage Property" /
  "Municipal Heritage Property". UNESCO World Heritage Site
  membership (Old Town Lunenburg) is **context**, not designation.

**HARD RULE — do not fabricate these fields from the description
text.** If the description says "late 1800s home", do NOT populate
`year_built: 1890`. Pull `year_built` from the rendered AGE summary
(Tier A) instead. If even that's unavailable, mark `year_built:
unknown` and add a `[PROMPT USER]` marker. LLMs will happily
synthesize plausible Victorian-era numbers for Lunenburg listings;
this exact pattern produced fabricated extractions during the
2026-04 smoke test.

Same rule applies to all Tier B fields. Extract them only if you see
a concrete value (not a `{{ handlebars }}` template) in the HTML or
the rendered DOM.

## Page landmarks to extract from

For the fields that ARE server-rendered:

- Price, address, beds, baths, living area: scan for the JSON blob
  `"list_price":"<N>",...,"nbeds":"<N>",...` present once per listing
  in the cutsheet HTML. Regex: `"list_price":"([^"]+)".*?"address":"([^"]+)"`.
- Full description: find `<script type="application/ld+json">...</script>`,
  parse JSON, read `.description`.
- Photo URLs: all `<img src="https://www.viewpoint.ca/media/...">` in
  the page.

For the JS-rendered fields, leave them `unknown` and emit a single
`[PROMPT USER] Missing: year_built, annual_taxes, heating, foundation,
zoning, water, sewer` note in the draft input.md. The user can fill
them from the rendered page in their browser or from the seller-Q
round.

## Extract into these fields

Target the same JSON shape as `listings/sources/paste.md`. Set
`source: "viewpoint"` and `listing_id` to the VP number if present.

## Viewpoint-specific quirks

- **Taxes** on Viewpoint are sometimes the PVSC assessment's tax
  estimate, not the actual owner-paid tax. Flag this in the notes —
  and only populate the field if you see a concrete value in the
  HTML (see handlebars-template caveat above).
- **Days on Market** — Viewpoint labels "Active" listings with a
  count; pending/conditionally-sold listings may not show DOM.
- **Previous sale price** — Viewpoint shows historical sales when
  available; capture all entries with date.
- **Unit breakdowns** — Viewpoint rarely publishes per-unit rent for
  duplexes. Leave `current_rent` blank; the user or a seller-Q round
  can fill in later.
- **Heritage** — listings in Lunenburg, Annapolis Royal, etc. often
  note heritage status in the description. Parse carefully; only set
  `heritage: true` for explicit designated status.

## Fall-through behavior

If WebFetch returns HTML that:
- Does not contain a price anywhere, OR
- Does not contain an address anywhere, OR
- Looks like the map SPA shell (keywords: "mapbox-gl", body is
  nearly empty, URL was a short code), OR
- Appears to be a challenge/block page (keywords: "captcha",
  "are you human", "please enable JavaScript")

then:
1. Log the fallback reason to the user
2. Ask them to paste the rendered page text
3. Route the pasted text through `listings/sources/paste.md`

## Photos

Collect unique image URLs from the rendered HTML. For Mode A MVP,
store them as URLs in the input.md notes section; do NOT download
unless the user explicitly asks. Local photo storage is a Phase 3.1
decision.
