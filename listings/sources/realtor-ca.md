# Realtor.ca Adapter

> Canada-wide coverage. Aggressive anti-bot (Cloudflare + challenge
> pages). Expect the fetch to fail more often than succeed. **Plan for
> fallback.**

## Fetch strategy

1. Try `WebFetch` with a realistic browser User-Agent
2. If the response is a Cloudflare interstitial, CAPTCHA page, or
   returns `403`/`429`: **do not retry**. Fall through immediately.
3. On fall-through, tell the user:

   > Realtor.ca blocked the fetch. Please paste the page content
   > (from "Property Details" through the description). I'll extract
   > from the paste.

4. Route the pasted content through `listings/sources/paste.md`.

## Anti-bot detection markers

Treat as a block if the fetched HTML contains any of:
- `<title>.*Just a moment.*</title>` (Cloudflare)
- `cf-challenge` class
- "Please verify you are a human"
- "Access denied"
- HTTP status 403 or 429
- Response body is suspiciously short (<2 KB) or all JavaScript

## Happy-path extraction (when fetch succeeds)

Realtor.ca pages have structured `<script type="application/ld+json">`
RealEstateListing payloads. If present, parse that first — it has
clean price, address, type, and description fields.

Fall back to HTML scraping for fields not in the JSON-LD:
- MLS® number in the details section
- Year built, lot size, square footage in the attribute list
- Photos from the `<ul>` gallery

## URL shapes

Realtor.ca URLs usually look like:
- `https://www.realtor.ca/real-estate/<mls-id>/<slug>` (current)
- Older formats exist; the MLS ID is always a number in the path

Extract the MLS ID from the URL and set it as `listing_id`.
Set `source: "realtor-ca"`.

## Realtor.ca quirks

- Listings for Québec properties on Realtor.ca often have sparser data
  than on Centris.ca directly. Flag this.
- Rental amounts are almost never on Realtor.ca — owners list on
  Kijiji/Facebook. Leave blank.
- "For Sale by Owner" listings on Realtor.ca route through a
  third-party aggregator; structure varies. Treat as paste-target.
- Property tax shown is usually the latest municipal year; capture as
  `property_tax_annual` but note the year if available.

## Do not

- Do not retry on anti-bot rejections.
- Do not rotate User-Agents or attempt evasion — we're a research tool,
  not a scraper. If they block us, we fall back to paste.
- Do not store cookies or session state between fetches.
