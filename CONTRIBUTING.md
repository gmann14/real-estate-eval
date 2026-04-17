# Contributing

Thanks for your interest. This tool started as a personal framework for
evaluating real estate in Nova Scotia and is being opened up so others can
use it for other provinces and markets.

## Ways to contribute

### 1. Add a province

The highest-leverage contribution: add a new file at
`config/provinces/<code>.md` (e.g., `on.md`, `bc.md`, `ab.md`, `qc.md`) following
the shape of `config/provinces/ns.md`. It should cover, at minimum:

- Land/property transfer tax (rates + bands + rebates)
- Property tax conventions (who assesses, how it's charged, municipal
  variations)
- Non-resident surtaxes, if any
- STR regulation (provincial + major municipalities)
- Rent control / tenant law highlights
- First-time buyer programs
- HST/GST/PST treatment of STR income
- CMHC-specific considerations for the province
- Insurance notes for common risks in the province
- Public data sources (assessment portal, MLS, etc.)

All information should be public and cited. If you can't cite a source for a
rate, leave it out — wrong defaults are worse than missing defaults.

### 2. Add a municipality

If you know a specific municipality well, add a file at
`config/municipalities/<province>/<city>.md` covering:

- DTT rate (confirmed, with year)
- Property tax rate (confirmed, with year)
- STR bylaws (with links)
- Zoning quirks relevant to investors
- Heritage or conservation districts, if applicable

### 3. Improve the templates

If you evaluate a property and find that a section is missing or misleading,
open an issue or PR proposing the change to the relevant template in
`templates/`. Keep templates opinionated but generic.

### 4. Contribute a synthetic worked example

A publishable synthetic example (fictional address, plausible numbers) is
valuable both as documentation and as a regression fixture. Put it under
`evaluations/examples/<slug>/` and include all four files: input, analysis,
enhancements, and (optional) email-to-realtor template.

### 5. Wire up the deterministic financial engine

The roadmap in `SPEC.md` describes a TypeScript engine that would replace the
AI for financial math. Current-state: agent does everything. Ideal-state: the
math (mortgage, CMHC, projections, rent-vs-buy) is deterministic code with
unit tests; the agent only handles data gathering and narrative. If you want
to work on that, start with `src/analysis/financing.ts` + tests against the
synthetic example fixtures.

## Principles

1. **Public data only.** Every rate, rule, and default must be citable from a
   public source. No paywalled MLS data in configs. No real realtor
   contact information in example evaluations.
2. **Conservative defaults.** When in doubt, bias toward the cautious number.
   Users can override.
3. **Every assumption documented.** Rates need a source and a year. Add
   `Last updated: YYYY-MM-DD` at the bottom of every config file you touch.
4. **Not financial advice.** All user-facing outputs must carry the "consult
   a licensed professional" disclaimer. This tool is a first-draft decision
   aid, not a substitute for a mortgage broker or accountant.
5. **Personal evaluations stay private.** The `evaluations/` folder is
   gitignored by default. If you want to contribute an example, use
   `evaluations/examples/` and use synthetic data only.

## Submitting a change

1. Fork the repo
2. Create a branch (`add-ontario-config`, `fix-cmhc-rule-2026`, etc.)
3. Make the change in an atomic commit
4. Include a sentence in the commit message explaining *why* the data is
   correct and where it came from
5. Open a PR

For config changes specifically, include the source URL in the PR description
so reviewers can verify.

## Code of conduct

Be kind. Assume good faith. Don't publish anyone's personal real estate
transactions.
