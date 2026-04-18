# Paste Adapter

> Always-works fallback. Invoked when the user pastes raw listing text
> or HTML, or when a URL-based adapter (viewpoint, realtor.ca, centris)
> is blocked and falls through to here.

## Inputs

You will receive one of:
1. Plain-text paste of a listing page (Realtor paragraph, "Property
   Details" block, unit breakdown, etc.)
2. Copy-pasted HTML from the rendered page
3. Markdown a user typed out themselves

The input may be partial. Extract whatever is present; do not
invent data.

## Extract into these fields

Produce a JSON block with the following shape (omit keys you genuinely
couldn't find — do NOT fill with "null" or guesses):

```json
{
  "address": "142 Maple Lane, Mahone Bay, NS B0J 2E0",
  "asking_price": 425000,
  "type": "duplex",
  "year_built": 1910,
  "land_acres": 0.22,
  "beds_total": 4,
  "baths_total": 2,
  "sqft_total": 1850,
  "property_tax_annual": 3420,
  "heating": "oil",
  "foundation": "stone",
  "parking": "gravel, 2 spots",
  "heritage": false,
  "water": "municipal",
  "sewer": "septic",
  "zoning": "R2",
  "listing_id": "202511234",
  "source": "paste",
  "listing_agent": "Jane Smith, XYZ Realty, 902-555-1234",
  "days_on_market": 14,
  "description_excerpt": "First 1-2 sentences of the listing description",
  "units": [
    {
      "name": "Main",
      "beds": 2,
      "baths": 1,
      "sqft": 900,
      "level": "main",
      "kitchen": true,
      "laundry": true,
      "separate_entry": true,
      "current_use": "ltr",
      "current_rent": 1200
    },
    { "name": "Upper", "beds": 2, "baths": 1, "sqft": 950, "level": "upper",
      "kitchen": true, "laundry": false, "separate_entry": true,
      "current_use": "vacant" }
  ],
  "known_issues": ["knob-and-tube in attic"],
  "recent_renovations": ["2023 roof", "2022 heat pump"]
}
```

## Field precedence rules

1. **Price:** the asking price, not assessed / previous sale / estimated
   value. Strip `$` and commas → integer.
2. **Address:** the FULL address including city, province, postal code
   if present. If only city is given, include what's there.
3. **Type:** choose the most specific: `single`, `duplex`, `triplex`,
   `fourplex`, `mixed-use`, `condo`. If the listing says "2-unit" treat
   as duplex.
4. **Units:** one object per rental unit. Owner's unit counts.
   `current_use` is one of `owner | ltr | str | vacant`.
5. **Land:** convert sq ft to acres if needed (1 acre = 43,560 sq ft).
6. **Unit rent:** only fill `current_rent` when explicitly stated in
   the text. Never extrapolate from "comparable rents" language — leave
   blank and let the analysis agent estimate from comps.
7. **Heritage:** `true` only if the listing explicitly uses
   "heritage designated" / "heritage property" / "registered heritage"
   language. "Historic charm" is not heritage designation.

## Missing data

If the text is missing a required field (address, price, type,
municipality, province), insert the marker `[PROMPT USER]` in the
returned JSON at that key. The orchestrating skill will surface this
to the user before writing `input.md`.

Never guess a required field to avoid the prompt.

## Writing input.md

After extraction, populate `templates/evaluation-template.md` with the
extracted JSON. Fields the template has but you don't have go as `?`
(let the analysis agent fill them). Fields in the JSON not in the
template (e.g. `description_excerpt`, `listing_id`) go in
`## Notes / Open Questions for the Agent` at the bottom.

Rent override table rows: only fill if you have actual paid rents for
units. Market-rate estimates go in the analysis pass, not here.
