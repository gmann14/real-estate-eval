# Viewpoint.ca Adapter

> Primary NS source. Public, relatively scrape-friendly. URLs look like
> `https://www.viewpoint.ca/property/12345/...` or `/property/listing/...`.

## Fetch strategy

1. **First attempt:** `WebFetch` the URL. Viewpoint pages render most
   of the listing detail server-side, so the fetched HTML is usable.
2. **On 403 / CAPTCHA / rate-limit:** fall through to the paste
   adapter (`listings/sources/paste.md`) — ask the user to paste the
   page content.
3. **Max 1 retry** on transient failures. No retry storms.

## Page landmarks to extract from

Viewpoint uses semi-consistent markup. These patterns have been stable
as of 2026-04 but **verify by scanning the fetched HTML** before
trusting:

- Price: `<span class="price">` or similar near the top of the detail
  section, or labeled "Asking:" / "List Price:"
- Address: the `<h1>` usually contains the street address; city and
  province in a subtitle line
- MLS # / Viewpoint ID: look for "VP#" or "MLS®" labels
- Property details table: `<table>` with rows like Year Built, Lot
  Size, Square Feet, Taxes, Zoning
- Description: a long `<div>` or `<p>` block below the details table
- Photos: `<img>` tags with `src` pointing to `viewpoint.ca/media/...`

## Extract into these fields

Target the same JSON shape as `listings/sources/paste.md`. Set
`source: "viewpoint"` and `listing_id` to the VP number if present.

## Viewpoint-specific quirks

- **Taxes** on Viewpoint are sometimes the PVSC assessment's tax
  estimate, not the actual owner-paid tax. Flag this in the notes.
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
