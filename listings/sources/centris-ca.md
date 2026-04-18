# Centris.ca Adapter

> **Placeholder.** Phase 3.1 target. Centris is the Québec MLS
> aggregator. Pages are French-language and often behind soft
> anti-bot. Real implementation requires French parsing in the
> extraction prompt.

## Phase 3 behaviour

For now, route all `centris.ca` URLs to the paste adapter with a
note asking the user to paste the rendered page. The paste adapter
prompt already handles French text reasonably — set
`source: "centris-ca"` when producing the extraction JSON, and rely
on the analysis agent to translate inline.

## To populate in Phase 3.1

- Centris URL patterns (`centris.ca/fr/...` and `.ca/en/...`)
- JSON-LD or structured block locations
- French → English field label map ("Année de construction" → year
  built, "Évaluation municipale" → municipal assessment, etc.)
- Anti-bot detection markers
- Welcome tax (taxe de bienvenue) calculation notes — these differ
  from NS DTT and need the `config/provinces/qc.md` file to exist
  before we can model full Montréal deals.
