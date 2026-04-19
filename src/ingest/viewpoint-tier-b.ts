/// <reference lib="dom" />
/**
 * Viewpoint.ca Tier-B extractor.
 *
 * Usage:
 *   npx tsx src/ingest/viewpoint-tier-b.ts <url> [<url> ...]
 *
 * Output: JSON to stdout, one object per URL with the Tier-B fields
 * (zoning, heating, foundation, water/sewer, roof, basement, building
 * style, listing-event log, listing-agent name/phone, heritage flag).
 *
 * Reads viewpoint.ca credentials from macOS Keychain (service
 * "viewpoint.ca", account configurable via --account=<email>) and
 * persists session state at .session/viewpoint.json so subsequent
 * runs skip the login flow.
 *
 * Architecture: the browser-bound step (page.evaluate) only reads the
 * rendered text; all parsing lives in `parse-viewpoint.ts` so it can
 * be unit-tested without spinning up Playwright.
 */
import { writeFileSync } from "node:fs";
import type { Page } from "playwright";
import { closeSession, openSession } from "./viewpoint-auth.js";
import {
  buildDetails,
  parseViewpointBody,
  type ListingEvent,
} from "./parse-viewpoint.js";

interface CliArgs {
  urls: string[];
  account?: string;
  headless: boolean;
  forceLogin: boolean;
  outFile?: string;
}

function parseArgs(argv: string[]): CliArgs {
  const args: CliArgs = { urls: [], headless: true, forceLogin: false };
  for (const a of argv) {
    if (a.startsWith("--account=")) args.account = a.slice("--account=".length);
    else if (a === "--headed") args.headless = false;
    else if (a === "--force-login") args.forceLogin = true;
    else if (a.startsWith("--out=")) args.outFile = a.slice("--out=".length);
    else if (!a.startsWith("--")) args.urls.push(a);
  }
  return args;
}

export interface TierBData {
  url: string;
  pid: string | null;
  fetchedAt: string;
  listPrice: string | null;
  address: string | null;
  yearBuilt: string | null;
  lotSize: string | null;
  daysOnMarket: string | null;
  assessment: string | null;
  annualTaxes: string | null;
  // Tier-B (login-gated)
  zoning: string | null;
  heating: string | null;
  foundation: string | null;
  basement: string | null;
  roof: string | null;
  water: string | null;
  sewer: string | null;
  buildingStyle: string | null;
  propertySubType: string | null;
  exteriorFinish: string | null;
  flooring: string | null;
  parking: string | null;
  occupancy: string | null;
  possession: string | null;
  heritageDesignated: string | null;
  listingAgentName: string | null;
  listingAgentPhone: string | null;
  brokerage: string | null;
  listingEvents: ListingEvent[];
  saleHistory: Array<{ date: string; price: string }>;
  rawSummaryText: string | null;
  details: Record<string, string>;
  warnings: string[];
}

function pidFromUrl(url: string): string | null {
  const m = url.match(/\/property\/(\d+)/) ?? url.match(/\/cutsheet\/(\d+)/);
  return m && m[1] ? m[1] : null;
}

async function readPageText(page: Page, url: string): Promise<string> {
  await page.goto(url, { waitUntil: "domcontentloaded", timeout: 60_000 });
  await page.waitForLoadState("networkidle", { timeout: 30_000 }).catch(() => {});
  await page
    .waitForFunction(
      () => {
        const t = document.body?.innerText ?? "";
        return /BEDROOMS|ASSESSMENT|LOT SIZE/i.test(t);
      },
      { timeout: 20_000 },
    )
    .catch(() => {});

  // The summary view doesn't include Tier-B fields — they live behind
  // the DETAILS / HISTORY tabs. Click each in turn so its content gets
  // injected into the DOM, then read everything at once.
  for (const tabLabel of ["DETAILS", "HISTORY", "TAXES", "ROOMS"]) {
    await page
      .evaluate((label) => {
        const candidates = Array.from(document.querySelectorAll("a, button, li, span, div"));
        for (const el of candidates as HTMLElement[]) {
          if (
            el.innerText &&
            el.innerText.trim().toUpperCase() === label &&
            el.offsetParent !== null
          ) {
            el.click();
            return true;
          }
        }
        return false;
      }, tabLabel)
      .catch(() => false);
    await page.waitForTimeout(800);
  }

  await page.waitForLoadState("networkidle", { timeout: 15_000 }).catch(() => {});
  await page.waitForTimeout(1_500);

  // Pull the rendered text. Any further parsing happens in Node so it
  // can be unit-tested without Playwright.
  return await page.evaluate(() => document.body?.innerText ?? "");
}

async function extractFromPage(page: Page, url: string): Promise<TierBData> {
  const text = await readPageText(page, url);
  const details = buildDetails(text);
  const parsed = parseViewpointBody(text, details);

  const warnings: string[] = [];
  for (const k of ["zoning", "heating", "foundation", "water", "sewer"] as const) {
    if (!parsed[k]) warnings.push(`Tier-B field "${k}" not populated`);
  }

  return {
    url,
    pid: pidFromUrl(url),
    fetchedAt: new Date().toISOString(),
    listPrice: parsed.listPrice,
    address: null,
    yearBuilt: parsed.yearBuilt,
    lotSize: parsed.lotSize,
    daysOnMarket: null,
    assessment: parsed.assessment,
    annualTaxes: null,
    zoning: parsed.zoning,
    heating: parsed.heating,
    foundation: parsed.foundation,
    basement: parsed.basement,
    roof: parsed.roof,
    water: parsed.water,
    sewer: parsed.sewer,
    buildingStyle: parsed.buildingStyle,
    propertySubType: parsed.propertySubType,
    exteriorFinish: parsed.exteriorFinish,
    flooring: parsed.flooring,
    parking: parsed.parking,
    occupancy: parsed.occupancy,
    possession: parsed.possession,
    heritageDesignated: parsed.heritageDesignated,
    listingAgentName: parsed.listingAgentName,
    listingAgentPhone: parsed.listingAgentPhone,
    brokerage: parsed.brokerage,
    listingEvents: parsed.listingEvents,
    saleHistory: [],
    rawSummaryText: text.slice(0, 25_000),
    details,
    warnings,
  };
}

function emptyResult(url: string, message: string): TierBData {
  return {
    url,
    pid: pidFromUrl(url),
    fetchedAt: new Date().toISOString(),
    listPrice: null,
    address: null,
    yearBuilt: null,
    lotSize: null,
    daysOnMarket: null,
    assessment: null,
    annualTaxes: null,
    zoning: null,
    heating: null,
    foundation: null,
    basement: null,
    roof: null,
    water: null,
    sewer: null,
    buildingStyle: null,
    propertySubType: null,
    exteriorFinish: null,
    flooring: null,
    parking: null,
    occupancy: null,
    possession: null,
    heritageDesignated: null,
    listingAgentName: null,
    listingAgentPhone: null,
    brokerage: null,
    listingEvents: [],
    saleHistory: [],
    rawSummaryText: null,
    details: {},
    warnings: [message],
  };
}

async function main(): Promise<void> {
  const args = parseArgs(process.argv.slice(2));
  if (args.urls.length === 0) {
    console.error("Usage: npx tsx src/ingest/viewpoint-tier-b.ts <url> [<url>...]");
    console.error("Options: --account=<email> --headed --force-login --out=<path>");
    process.exit(2);
  }

  const session = await openSession({
    account: args.account,
    headless: args.headless,
    forceLogin: args.forceLogin,
  });

  const results: TierBData[] = [];
  try {
    for (const url of args.urls) {
      try {
        process.stderr.write(`[viewpoint-tier-b] fetching ${url}\n`);
        const data = await extractFromPage(session.page, url);
        results.push(data);
      } catch (e) {
        process.stderr.write(
          `[viewpoint-tier-b] FAILED ${url}: ${(e as Error).message}\n`,
        );
        results.push(emptyResult(url, `fetch failed: ${(e as Error).message}`));
      }
    }
  } finally {
    await closeSession(session);
  }

  const json = JSON.stringify(results, null, 2);
  if (args.outFile) {
    writeFileSync(args.outFile, json);
    process.stderr.write(`[viewpoint-tier-b] wrote ${args.outFile}\n`);
  } else {
    process.stdout.write(`${json}\n`);
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
