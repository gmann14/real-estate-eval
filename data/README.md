# `data/` — local working data (mostly gitignored)

This directory holds the tax-sale toolkit's working data. Almost everything in
here is **gitignored** because it's either bulky (public PDFs re-downloadable
from MODL), contains real bidder names (the §13.8 privacy concern), or is
personally curated (your PVSC enrichment).

## Expected layout

```
data/
├── README.md                                  # this file (tracked)
├── probe/modl/{year}/                         # IGNORED
│   ├── _page.html                             #   archived MODL page (~150 KB)
│   ├── tender-package.pdf                     #   text PDF, all lots' details
│   ├── bid-form.pdf                           #   blank tender form
│   ├── faqs.pdf
│   ├── property-{NNN}.pdf                     #   per-lot legal counsel report
│   ├── property-{NNN}.json                    #   hand-OCR'd JSON fixture
│   ├── award-{NNN}.pdf                        #   per-lot bid record (post-tender)
│   └── award-{NNN}.json                       #   hand-OCR'd JSON fixture
└── enrichment/                                # IGNORED
    └── pvsc-{year}.csv                        #   your manual PVSC lookups
```

## How to populate this directory

### Historical data (2021–2026)

Already populated locally during the v0 build of the toolkit. ~189 PDFs,
~92 award JSON fixtures, ~71 property-info JSON fixtures. Not pushed
because:
- 392 MB of MODL public PDFs would bloat the repo (re-scrapeable anyway)
- JSON fixtures contain real bidder names transcribed from MODL's
  publicly-posted award PDFs; bulk-republishing them in a searchable
  public repo is a different privacy posture than MODL's per-property
  PDF disclosure

If you want to regenerate from scratch on a fresh clone:

1. Clone the repo and `cd data/`
2. `mkdir -p probe/modl`
3. Copy `tax_sale/data-probe-modl-_download.sh` here (or recreate it —
   the URL-by-year mapping is documented in `tax_sale/RUNBOOK-2027.md`)
4. `bash _download.sh` — pulls all the public PDFs
5. OCR the scanned PDFs per `tax_sale/RUNBOOK-2027.md` step 4

### New live data (2027+)

Follow [`../tax_sale/RUNBOOK-2027.md`](../tax_sale/RUNBOOK-2027.md)
step-by-step when MODL drops the next tender package.

### PVSC enrichment

Follow [`../tax_sale/PVSC-LOOKUP-GUIDE.md`](../tax_sale/PVSC-LOOKUP-GUIDE.md).
Writes to `data/enrichment/pvsc-{year}.csv`. Personal/local only.

## Why nothing's tracked

The toolkit code (`tax_sale/`) operates on this directory but doesn't
depend on the specific contents being committed. Tests `pytest.skip` when
fixtures are absent. `python -m tax_sale stats --strict` will fail loudly
on first run after a clean clone — by design — so you know to populate
the directory before relying on results.

If you want a personal backup, mirror this directory to your own private
storage (Google Drive, Dropbox, S3 bucket with restricted access). Don't
push to a public repo.
