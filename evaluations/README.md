# evaluations/

Each property you evaluate gets its own subfolder here:

```
evaluations/
  9-prince-street-lunenburg/
    input.md              # Filled-out evaluation template
    analysis.md           # Full analysis report
    enhancements.md       # ROI enhancement recommendations
    email-to-realtor.md   # Questions to send
    realtor-answers.md    # Responses as they come in
    (optional) notes.md   # Your running notes
```

## Privacy

By default, this folder is **gitignored** (see `.gitignore`). Your individual
property evaluations contain:

- Personal financial assumptions
- Realtor names, contact info, and correspondence
- Pricing thoughts and negotiation strategy
- Seller-provided financials marked confidential

None of this should end up in a public repo. The gitignore keeps
`evaluations/*` out while still tracking `evaluations/README.md` and the
`evaluations/examples/` directory for synthetic/published examples.

## Publishable examples

If you want to share a worked example (for documentation, contribution, or
teaching), put it under `evaluations/examples/<slug>/` using **synthetic
data only**:

- Fictional address
- Plausible but invented numbers
- No real realtor names, phone numbers, or contact info
- No seller-provided confidential financials

See `CONTRIBUTING.md` for guidelines.

## Naming convention

`<street-number>-<street-name>-<city>/` — e.g., `9-prince-street-lunenburg/`.
Keep it lowercase, hyphenated, and human-readable.

## Creating a new evaluation

1. Copy `templates/evaluation-template.md` to
   `evaluations/<slug>/input.md`
2. Fill in what you know
3. Ask Claude to run the analysis (see the skill in
   `.claude/skills/evaluate-property/`)
4. Review the generated `analysis.md` and `enhancements.md`
5. Iterate — update assumptions, re-run, audit
