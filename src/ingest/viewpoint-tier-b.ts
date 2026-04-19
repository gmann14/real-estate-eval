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
 */
import { writeFileSync } from "node:fs";
import type { Page } from "playwright";
import { closeSession, openSession } from "./viewpoint-auth.js";

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

export interface ListingEvent {
  date: string;
  event: string;
  price: string;
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

async function extractFromPage(page: Page, url: string): Promise<TierBData> {
  await page.goto(url, { waitUntil: "domcontentloaded", timeout: 60_000 });

  // Wait for the JS bundle to populate fields. We watch for the
  // disappearance of unresolved handlebars markers, then settle.
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
            (el as HTMLElement).offsetParent !== null
          ) {
            (el as HTMLElement).click();
            return true;
          }
        }
        return false;
      }, tabLabel)
      .catch(() => false);
    await page.waitForTimeout(800);
  }

  // Final settle for any async content fetched by the tab clicks.
  await page.waitForLoadState("networkidle", { timeout: 15_000 }).catch(() => {});
  await page.waitForTimeout(1_500);

  // NB: this function runs in the browser. tsx's transpile inserts a
  // `__name` helper for named function expressions which breaks inside
  // page.evaluate (the browser context has no `__name`). To avoid this,
  // we pass the function source as a string.
  const evalSource = `(() => {
    var text = document.body && document.body.innerText ? document.body.innerText : "";
    var lines = text.split(/\\r?\\n/).map(function(s){ return s.trim(); });

    // DETAILS panel renders one "LABEL:VALUE" per line.
    var details = {};
    for (var i = 0; i < lines.length; i++) {
      var l = lines[i];
      var ci = l.indexOf(":");
      if (ci > 0 && ci < 60) {
        var key = l.slice(0, ci).trim().toUpperCase();
        var val = l.slice(ci + 1).trim();
        if (val && val !== "N/A" && val !== "—" && !/^\\{\\{/.test(val) && !/^https?:/.test(val)) {
          if (!details[key]) details[key] = val;
        }
      }
    }
    var pick = function() {
      for (var k = 0; k < arguments.length; k++) {
        var v = details[arguments[k].toUpperCase()];
        if (v) return v;
      }
      return null;
    };

    // Summary panel — labels are on their own line, values follow on next line.
    var labeledLine = function(label) {
      for (var i = 0; i < lines.length; i++) {
        if (lines[i].toUpperCase() === label.toUpperCase()) {
          var n = lines[i + 1] || "";
          if (n && n !== "N/A" && n !== "—" && !/^\\{\\{/.test(n)) return n;
        }
      }
      return null;
    };

    // Listing-history table: rows look like
    //   <STATUS>           e.g. "For Sale", "Sold", "Expired", "Withdrawn"
    //   <START DATE>       "May 23, 2025"
    //   <END DATE?>        optional, same date format (omitted for active)
    //   <LIST PRICE>       "$1,175,000"
    //   <SOLD PRICE?>      optional "$380,000"
    //   <DURATION>         "331 days"
    //   then a series of "<DATE>" + "Status change..." or "Price change..." sub-rows.
    // We capture each (DATE, EVENT, PRICE) row by walking the LISTING HISTORY block.
    var events = [];
    var hStart = -1;
    for (var k = 0; k < lines.length; k++) {
      if (lines[k] === "LISTING HISTORY" && lines[k + 1] && /^STATUS$/.test(lines[k + 1])) {
        hStart = k + 1;
        break;
      }
    }
    if (hStart < 0) {
      // Fallback: first LISTING HISTORY occurrence followed by date-like row.
      for (var k2 = 0; k2 < lines.length; k2++) {
        if (lines[k2] === "LISTING HISTORY") { hStart = k2; break; }
      }
    }
    if (hStart >= 0) {
      var datePat = /^(\\d{4}-\\d{2}-\\d{2}|[A-Za-z]+ \\d{1,2}, \\d{4})$/;
      var pricePat = /^\\$[\\d,]+$/;
      var statusPat = /^(For Sale|Sold|Expired|Withdrawn|Pending|Conditional|Leased|Cancelled)$/i;
      var hStop = Math.min(lines.length, hStart + 400);
      var lastStatus = null;
      for (var m = hStart; m < hStop; m++) {
        var ln = lines[m];
        if (!ln) continue;
        if (statusPat.test(ln)) {
          lastStatus = ln;
          continue;
        }
        if (datePat.test(ln)) {
          // Look ahead a few lines for an event description or price.
          var ev = "";
          var pr = "";
          for (var look = 1; look <= 3; look++) {
            var lk = lines[m + look] || "";
            if (!ev && /change|status|price/i.test(lk)) { ev = lk; }
            if (!pr && pricePat.test(lk)) { pr = lk; }
          }
          if (!ev && lastStatus) ev = lastStatus + " — listed";
          events.push({ date: ln, event: ev, price: pr });
        }
      }
    }

    return {
      rawSummaryText: text.slice(0, 25000),
      listPrice: labeledLine("FOR SALE") || pick("LIST PRICE", "PRICE"),
      address: null,
      yearBuilt: pick("AGE", "YEAR BUILT"),
      lotSize: labeledLine("LOT SIZE") || pick("LISTING PARCEL SIZE", "PARCEL SIZE"),
      daysOnMarket: null,
      assessment: pick("ASSESSED AT"),
      annualTaxes: null,
      zoning: pick("ZONING", "MLS ZONING"),
      heating: pick("HEATING/COOLING", "HEATING", "HEAT TYPE"),
      foundation: pick("FOUNDATION"),
      basement: pick("BASEMENT"),
      roof: pick("ROOF"),
      water: pick("DRINKING WATER", "WATER", "WATER SOURCE"),
      sewer: pick("SEWER"),
      buildingStyle: pick("BUILDING STYLE", "STYLE"),
      propertySubType: pick("PROPERTY SUB TYPE", "TYPE"),
      exteriorFinish: pick("EXTERIOR", "EXTERIOR FINISH"),
      flooring: pick("FLOORING"),
      parking: pick("PARKING") || pick("HAS GARAGE"),
      occupancy: pick("OCCUPANCY"),
      possession: pick("POSSESSION"),
      heritageDesignated: pick("HERITAGE", "HERITAGE PROPERTY", "HERITAGE DESIGNATED"),
      listingAgentName: (function(){
        for (var i = 0; i < lines.length; i++) {
          if (/REALTOR®/.test(lines[i])) {
            var prev = lines[i - 1] || "";
            if (prev && prev.length < 60 && !/[a-z]/.test(prev[0] || "")) return prev;
          }
        }
        return null;
      })(),
      listingAgentPhone: (function(){
        for (var i = 0; i < lines.length; i++) {
          if (/REALTOR®/.test(lines[i])) {
            for (var j = 1; j <= 3; j++) {
              var nx = lines[i + j] || "";
              if (/^\\d{3}-\\d{3}-\\d{4}$/.test(nx)) return nx;
            }
          }
        }
        return null;
      })(),
      brokerage: pick("LISTED BY"),
      listingEvents: events,
      details: details,
    };
  })()`;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const data = (await page.evaluate(evalSource as unknown as () => any)) as Record<string, any>;

  const warnings: string[] = [];
  const tierBKeys = [
    "zoning",
    "heating",
    "foundation",
    "water",
    "sewer",
  ] as const;
  for (const k of tierBKeys) {
    if (!data[k]) warnings.push(`Tier-B field "${k}" not populated`);
  }

  return {
    url,
    pid: pidFromUrl(url),
    fetchedAt: new Date().toISOString(),
    listPrice: data.listPrice,
    address: data.address,
    yearBuilt: data.yearBuilt,
    lotSize: data.lotSize,
    daysOnMarket: data.daysOnMarket,
    assessment: data.assessment,
    annualTaxes: data.annualTaxes,
    zoning: data.zoning,
    heating: data.heating,
    foundation: data.foundation,
    basement: data.basement,
    roof: data.roof,
    water: data.water,
    sewer: data.sewer,
    buildingStyle: data.buildingStyle,
    propertySubType: data.propertySubType,
    exteriorFinish: data.exteriorFinish,
    flooring: data.flooring,
    parking: data.parking,
    occupancy: data.occupancy,
    possession: data.possession,
    heritageDesignated: data.heritageDesignated,
    listingAgentName: data.listingAgentName,
    listingAgentPhone: data.listingAgentPhone,
    brokerage: data.brokerage,
    listingEvents: data.listingEvents ?? [],
    saleHistory: [],
    rawSummaryText: data.rawSummaryText ?? null,
    details: (data.details as Record<string, string>) ?? {},
    warnings,
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
        results.push({
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
          warnings: [`fetch failed: ${(e as Error).message}`],
        });
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
