---
name: ingest-listing
description: Take a listing URL or pasted listing text, extract the property details, check against the user's criteria if configured, and produce a full evaluation. Use when the user says "ingest this listing", "/ingest-listing", pastes a real-estate URL (viewpoint.ca / realtor.ca / centris.ca), or pastes raw listing text and asks for analysis.
---

# Ingest Listing Skill

You're the front end of the evaluation pipeline. The user pastes a
URL or raw listing text; you produce a fully analyzed
`evaluations/<slug>/` folder at the end. Do not invent data. Ask
before overwriting. Show a summary before running the full analysis.

## Inputs you might receive

1. **URL** — `https://www.viewpoint.ca/...`, `realtor.ca/...`,
   `centris.ca/...`, or another MLS source
2. **Pasted listing text** — a block of text copied from a listing
   page (description, property details, unit breakdown)
3. **Both** — user provides a URL and also pastes the page in case
   the fetch is blocked
4. **Nothing obvious** — user says "ingest this listing" but gives no
   URL and no paste. Ask for one.

## Step 1 — Pick the adapter

| Input contains…                        | Use adapter                                |
|----------------------------------------|--------------------------------------------|
| `viewpoint.ca`                         | `listings/sources/viewpoint.md`            |
| `realtor.ca`                           | `listings/sources/realtor-ca.md`           |
| `centris.ca`                           | `listings/sources/centris-ca.md` (placeholder — route to paste for now) |
| Any other URL                          | Try `WebFetch`; on failure fall through to paste |
| Raw text (no URL)                      | `listings/sources/paste.md`                |

Read the adapter file before extracting. Follow its rules for fall-through.

## Step 2 — Extract

Produce a JSON block of the shape defined in `listings/sources/paste.md`.
Do not invent missing fields — use `[PROMPT USER]` for missing required
fields (address, asking_price, type, municipality, province).

If any `[PROMPT USER]` markers remain after extraction, stop and ask
the user for the missing values before continuing.

### 2a — ViewPoint URLs: use the Tier-B extractor pipeline

For ViewPoint cutsheet/property URLs, prefer the deterministic
extraction pipeline over WebFetch + manual parsing:

```sh
# Pulls Tier-B fields (login-gated) into a JSON file
npx tsx src/ingest/viewpoint-tier-b.ts <url> --out=/tmp/tier-b-<slug>.json

# Renders that JSON into a draft input.md (Tier-B fields populated;
# unknowns marked [PROMPT USER])
npx tsx src/ingest/build-input-md.ts /tmp/tier-b-<slug>.json \
  > evaluations/<slug>/input.md
```

The first run prompts for the ViewPoint password (read from macOS
Keychain — see `listings/sources/viewpoint.md` for one-time setup).
Subsequent runs reuse the saved session in `.session/viewpoint.json`.

After running the pipeline, **read the resulting input.md**, find
every `[PROMPT USER]` marker, and either fill from listing photos or
ask the user for the residual fields (typically: type, unit
breakdown, STR-permitted lookup, known issues, recent renovations).
Then continue from Step 3.

## Step 3 — Compute slug and check for collision

Slug format: `<street-num>-<street-slug>-<city-slug>` (ASCII, kebab-case,
diacritic-free, ≤60 chars). For example:
- `142 Maple Lane, Mahone Bay, NS` → `142-maple-lane-mahone-bay`
- `1234 Rue St-Denis, Montréal, QC` → `1234-rue-st-denis-montreal`

If the address won't parse, fall back to `<listing-id>-<source>`.

Check `evaluations/<slug>/`:
- **Doesn't exist:** proceed to Step 4.
- **Exists, same price:** tell the user a prior analysis exists;
  ask overwrite / v2 / skip.
- **Exists, different price:** show the price delta; ask
  overwrite / v2 / skip / diff.
- **Exists, `input.md` missing or malformed:** treat as
  recoverable; ask user whether to overwrite.

Only create the folder once the user has chosen.

## Step 4 — Write `input.md`

Fill `templates/evaluation-template.md` using the extracted JSON.
Leave unknown optional fields as `?`. Do not leave required fields
blank or as placeholders — Step 5 will fail if you do.

## Step 5 — Validate input.md

Required shape:
- Sections `## Listing Details`, `## Units`, `## Municipal` present
- Non-placeholder values for `Address`, `Asking Price`, `Type`,
  `Municipality`, `Province`
- `## Units` contains a markdown table with consistent column counts

If anything fails, fix the specific field and ask the user for help
if you cannot.

## Step 6 — Check criteria (optional)

If `config/criteria.md` exists, parse its hard filters and evaluate
each against the extracted facts:

- **Hard filter fails** (e.g. `Price: <= $600,000` and
  asking_price = $850,000) → set verdict = `reject`. Write a short
  `evaluations/<slug>/skipped.md` explaining which filter failed.
  Skip the full analysis. Still append the row to `INDEX.md`.
- **All hard filters pass or no `criteria.md` exists** → verdict =
  `full`. Proceed to Step 7.

`[PROMPT USER]`-flagged fields are treated as "unknown, pass" —
don't reject on missing data.

## Step 7 — Load municipal context

If the property's `(city, province)` has a file under
`config/municipalities/`, note it. The analysis skill will pick it
up automatically, but flag it in the summary so the user can see
which rules are being applied.

NS cities currently routed:
- Mahone Bay, Lunenburg, Chester, Bridgewater → `modl.md`
- Halifax, Dartmouth, Bedford, Sackville → `hrm.md`
- Others → fall back to `config/provinces/ns.md`

## Step 8 — Show the summary, ask to proceed

Before burning tokens on full analysis, show:

```
# Ingest summary — 142-maple-lane-mahone-bay

- Address: 142 Maple Lane, Mahone Bay, NS
- Asking: $425,000
- Type: duplex · 2 units · 1910
- Lot: 0.22 acres
- Municipal config: modl.md
- Criteria verdict: full
- Missing data: current rents (both units), property tax year

Proceed with full analysis? (yes / edit inputs / cancel)
```

Wait for the user's "yes" before Step 9.

## Step 9 — Invoke /evaluate-property

Run the `evaluate-property` skill against
`evaluations/<slug>/input.md`. That skill owns the entire analysis
pass (analysis.md, enhancements.md, audit, optional email-to-realtor).

## Step 10 — Append INDEX.md

After the analysis lands, update `evaluations/INDEX.md` with a row:

```
| 2026-04-18 | 142 Maple Lane, Mahone Bay, NS | $425,000 | duplex | full | [→](./142-maple-lane-mahone-bay/analysis.md) |
```

Rules:
- If `INDEX.md` doesn't exist, create it with a header and the
  standard column set: `Date | Address | Price | Type | Verdict | Link`
- Sort rows by date descending
- If a row with the same slug already exists (rerun of an existing
  listing), update it in place rather than duplicating
- For `reject` verdicts, append the failing criterion inline:
  `reject — price cap`
- Don't corrupt an existing malformed file — ask the user if the
  current `INDEX.md` doesn't parse

## Principles

- **Never invent data.** `[PROMPT USER]` is always better than a
  plausible-looking guess.
- **Confirm before writing.** Ask before overwriting an existing eval
  folder, before running the full analysis, before amending
  `INDEX.md`.
- **Fallback is always paste.** If anything upstream breaks, ask the
  user to paste the page. The paste adapter is the backstop.
- **Mode A only.** This skill handles the manual "I pasted something"
  flow. Scheduled scanning is Phase 3.1; don't build anything
  persistent or cron-like here.

## Developer note

The project also ships TypeScript utilities under `src/utils/` that
mirror the deterministic pieces of this flow (slug, validate-input,
criteria, screen, index-md, collision, municipal). They're there for
automated Mode B use and for unit-testing the rules. You're welcome
to invoke them via `npx tsx -e "…"` for any check, but natural-
language reasoning over the markdown files is fine for Mode A — the
rules in this skill file are the source of truth.
