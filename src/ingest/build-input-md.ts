/**
 * Render a TierBData JSON record into the standard `input.md`
 * template used by `/evaluate-property`.
 *
 * Usage (CLI):
 *   npx tsx src/ingest/build-input-md.ts <path-to-tier-b.json> [--index=<n>]
 *   cat tier-b.json | npx tsx src/ingest/build-input-md.ts -
 *
 * Output: markdown to stdout. Tier-B fields are populated; everything
 * else is marked `[PROMPT USER]` so the operator (or downstream skill)
 * can fill them in. The intent is that the `/ingest-listing` skill
 * runs the Tier-B extractor, then runs this builder to land a draft
 * input.md, then prompts the user for the residual fields before
 * handing off to `/evaluate-property`.
 */
import { readFileSync } from "node:fs";
import type { TierBData } from "./viewpoint-tier-b.js";

const PLACEHOLDER = "[PROMPT USER]";

function ageToYearBuilt(age: string | null, fetchedAt: string): string {
  if (!age) return PLACEHOLDER;
  const n = Number.parseInt(age, 10);
  if (!Number.isFinite(n)) return PLACEHOLDER;
  // ViewPoint stores AGE in years; convert to year-built.
  if (n < 500) {
    const refYear = new Date(fetchedAt).getUTCFullYear();
    return String(refYear - n);
  }
  return age;
}

function splitAddress(address: string | null): {
  full: string;
  municipality: string;
  province: string;
} {
  if (!address) {
    return { full: PLACEHOLDER, municipality: PLACEHOLDER, province: PLACEHOLDER };
  }
  // Format: "<civic> <street>, <city>"  (ViewPoint omits province)
  const parts = address.split(",").map((s) => s.trim());
  const municipality = parts.length >= 2 ? (parts[1] ?? PLACEHOLDER) : PLACEHOLDER;
  // ViewPoint is NS-only today; flag if we expand.
  const province = "NS";
  return { full: address, municipality, province };
}

function previousSale(sales: TierBData["saleHistory"]): string {
  if (!sales || sales.length === 0) return PLACEHOLDER;
  const latest = sales[0]; // already sorted newest-first by ViewPoint
  if (!latest) return PLACEHOLDER;
  return `${latest.price} (${latest.date})`;
}

function listingAgentLine(d: TierBData): string {
  if (!d.listingAgentName && !d.brokerage) return PLACEHOLDER;
  const parts = [d.listingAgentName, d.brokerage, d.listingAgentPhone].filter(Boolean);
  return parts.join(", ");
}

function waterSewer(water: string | null, sewer: string | null): string {
  if (!water && !sewer) return PLACEHOLDER;
  if (water && sewer && water === sewer) return water.toLowerCase();
  return `${water ?? "?"} water / ${sewer ?? "?"} sewer`;
}

function maybe(value: string | null): string {
  return value && value.trim() ? value : PLACEHOLDER;
}

export function buildInputMd(data: TierBData): string {
  const { full: address, municipality, province } = splitAddress(data.address);
  const yearBuilt = ageToYearBuilt(data.yearBuilt, data.fetchedAt);

  const taxOverride = data.annualTaxes ?? PLACEHOLDER;
  const heritageFlag = data.heritageDesignated ? "yes" : "no";

  return `# ${address} — Evaluation Input

> Auto-generated from ViewPoint Tier-B extract on ${data.fetchedAt}.
> Fields marked \`${PLACEHOLDER}\` need human input before
> \`/evaluate-property\` will run.

---

## Listing Details

- **Address\\*:** ${address}
- **Asking Price\\*:** ${maybe(data.listPrice)}
- **Listing URL:** ${data.url}
- **Type\\*:** ${PLACEHOLDER}  *(infer from beds/baths + photos; not in Tier-B)*
- **Year Built:** ${yearBuilt}
- **Land:** ${maybe(data.lotSize)}
- **Previous Sale Price:** ${previousSale(data.saleHistory)}
- **Days on Market:** ${maybe(data.daysOnMarket)}
- **Listing Agent:** ${listingAgentLine(data)}

## Units

> Unit breakdown is not in Tier-B. Fill from listing photos /
> seller-Q round.

| # | Name | Beds | Baths | Sq Ft | Level | Kitchen | Laundry | Separate Entry | Current Use | Current Rent | Airbnb URL |
|---|------|------|-------|-------|-------|---------|---------|----------------|-------------|--------------|------------|
| 1 | ${PLACEHOLDER} |   |   |   |   |   |   |   | ${PLACEHOLDER} |   |   |
| 2 | ${PLACEHOLDER} |   |   |   |   |   |   |   |                |   |   |

## Building Features

- **Heating:** ${maybe(data.heating)}
- **Roof:** ${maybe(data.roof)}
- **Foundation:** ${maybe(data.foundation)}
- **Parking:** ${maybe(data.parking)}
- **Heritage Designated:** ${heritageFlag}${data.heritageDesignated ? ` — ${data.heritageDesignated}` : ""}
- **Basement:** ${maybe(data.basement)}
- **Exterior:** ${maybe(data.exteriorFinish)}
- **Flooring:** ${maybe(data.flooring)}
- **Building Style:** ${maybe(data.buildingStyle)}
- **Known Issues:** ${PLACEHOLDER}

## Recent Renovations (since previous sale)

- ${PLACEHOLDER}

## Municipal

- **Municipality\\*:** ${municipality}
- **Province\\*:** ${province}
- **Water/Sewer:** ${waterSewer(data.water, data.sewer)}
- **Zoning:** ${maybe(data.zoning)}${data.zoning ? "" : `  *(known gap: ViewPoint doesn't populate this for MODL listings)*`}
- **STR Permitted:** ${PLACEHOLDER}  *(municipal lookup)*

## Actual Operating Data (if seller-provided)

| Year | Gross Revenue | Operating Expenses | Net Profit (pre-depreciation) |
|------|---------------|--------------------|-------------------------------|
|      | $             | $                  | $                             |

## Optional Overrides

- **Property Tax Override:** ${taxOverride}/yr
- **Insurance Override:** ${PLACEHOLDER}
- **Heating Override:** ${PLACEHOLDER}
- **Electricity Override:** ${PLACEHOLDER}
- **Water/Sewer Override:** ${PLACEHOLDER}

## Tier-B Diagnostics (for audit)

- **PID:** ${data.pid ?? PLACEHOLDER}
- **2026 Assessment:** ${maybe(data.assessment)}
- **Listing-history events captured:** ${data.listingEvents.length}
- **Historical sales captured:** ${data.saleHistory.length}
- **Tier-B warnings:** ${data.warnings.length === 0 ? "none" : data.warnings.join("; ")}

## Notes / Open Questions for the Agent

- ${PLACEHOLDER}
`;
}

function readJson(path: string): TierBData | TierBData[] {
  const raw = path === "-" ? readFileSync(0, "utf8") : readFileSync(path, "utf8");
  return JSON.parse(raw) as TierBData | TierBData[];
}

function main(): void {
  const args = process.argv.slice(2);
  if (args.length === 0) {
    console.error(
      "Usage: npx tsx src/ingest/build-input-md.ts <path|-> [--index=<n>]",
    );
    process.exit(2);
  }
  const path = args[0]!;
  let index = 0;
  for (const a of args.slice(1)) {
    if (a.startsWith("--index=")) index = Number.parseInt(a.slice("--index=".length), 10);
  }

  const json = readJson(path);
  const records = Array.isArray(json) ? json : [json];
  const record = records[index];
  if (!record) {
    console.error(`No record at index ${index} (got ${records.length} records).`);
    process.exit(2);
  }
  process.stdout.write(buildInputMd(record));
}

if (import.meta.url === `file://${process.argv[1]}`) {
  main();
}
