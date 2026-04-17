# Montréal — Municipal Rules

> **TODO: populate.** Placeholder so the `/ingest-listing` pipeline has
> somewhere to route Montréal addresses. Someone with local knowledge
> should fill this in — probably in tandem with adding a Centris.ca
> source adapter.

## Jurisdictions covered

- Ville de Montréal (all 19 boroughs)

## Deed Transfer Tax / Welcome Tax

Québec uses a municipal **taxe de bienvenue** (welcome tax / transfer
duty). Calculated in tiers against the greater of purchase price or
municipal assessment. Montréal has its own higher tiers on top of the
provincial minimum.

See [config/provinces/qc.md](../provinces/qc.md) once that file exists.

## Property tax

Set by Ville de Montréal each year; varies by borough. Typical combined
residential rate is in the range of 0.7–0.9% of assessed value but
changes annually. **Always verify.**

## Short-term rentals (STR)

Montréal restricts STR to specific zones. The rules changed after the
2023 fire and are stricter than most Canadian cities. This needs to be
captured in detail before any STR-scenario modeling.

## Zoning / multi-unit

- Montréal boroughs each have their own land-use bylaw.
- "Plex" (duplex / triplex / quadruplex) stock is common and widely
  permitted in many boroughs.
- Needs local research to capture borough-by-borough nuances.

## Known gotchas

- French-language listings — the Centris adapter must translate
  inline.
- Older plex stock may have pre-1980 knob-and-tube or aluminum wiring.
- Montréal's rental board (TAL, formerly Régie du logement) sets tight
  constraints on rent increases for existing tenants.
