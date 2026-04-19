import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import {
  buildDetails,
  extractHeritage,
  extractListingAgent,
  extractListingEvents,
  parseViewpointBody,
} from "../parse-viewpoint.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const FIXTURE_PATH = join(__dirname, "fixtures", "tier-b-snapshots.json");

interface RawSnapshot {
  url: string;
  pid: string;
  rawSummaryText: string;
  details: Record<string, string>;
  // captured-at-time results, kept for reference only — current parser
  // output is what we assert against in the tests below.
  brokerage: string | null;
  listingAgentName: string | null;
}

const snapshots: RawSnapshot[] = JSON.parse(readFileSync(FIXTURE_PATH, "utf8"));

function findByPid(pid: string): RawSnapshot {
  const snap = snapshots.find((s) => s.pid === pid);
  if (!snap) throw new Error(`fixture missing pid=${pid}`);
  return snap;
}

const MONTAGUE = findByPid("60063062"); // 56 Montague — VP brokerage
const KING = findByPid("60058500"); // 94 King — VP brokerage
const FOX = findByPid("60602463"); // 69 Fox — Sotheby's brokerage

describe("buildDetails", () => {
  it("parses LABEL:VALUE rows from page text", () => {
    const details = buildDetails(MONTAGUE.rawSummaryText);
    expect(details["FOUNDATION"]).toBe("Stone");
    expect(details["HEATING/COOLING"]).toBe("Baseboard, Radiator, Hot Water");
    expect(details["LISTED BY"]).toBe("Viewpoint Realty Services Inc.(lunenburg)");
  });

  it("supports labels longer than 60 chars (up to 80)", () => {
    const text = "A REALLY LONG LABEL THAT IS MORE THAN SIXTY CHARS WIDE BLAH:hello\n";
    const details = buildDetails(text);
    expect(details["A REALLY LONG LABEL THAT IS MORE THAN SIXTY CHARS WIDE BLAH"]).toBe("hello");
  });

  it("ignores handlebars placeholder values", () => {
    const text = "ZONING:{{ entry.zoning || 'N/A' }}\n";
    const details = buildDetails(text);
    expect(details["ZONING"]).toBeUndefined();
  });
});

describe("extractListingAgent", () => {
  it("returns the visible agent for ViewPoint-brokered listings", () => {
    const lines = MONTAGUE.rawSummaryText.split(/\r?\n/).map((s) => s.trim());
    const result = extractListingAgent(lines, "Viewpoint Realty Services Inc.(lunenburg)");
    expect(result.name).toBe("STEPHANIE DEVRIES");
    expect(result.phone).toBe("902-521-1575");
  });

  it("rejects ViewPoint house agent on a Sotheby's-brokered listing", () => {
    const lines = FOX.rawSummaryText.split(/\r?\n/).map((s) => s.trim());
    const result = extractListingAgent(lines, "Sotheby's International Realty Canada");
    expect(result.name).toBeNull();
    expect(result.phone).toBeNull();
  });

  it("returns null when no REALTOR® marker is present", () => {
    const result = extractListingAgent(["just some text", "no marker here"], "Some Brokerage");
    expect(result.name).toBeNull();
  });
});

describe("extractHeritage", () => {
  it("detects 'Provincial Heritage Property' phrasing in description", () => {
    expect(extractHeritage(FOX.rawSummaryText)).toBe("Provincial Heritage Property");
  });

  it("returns null when no heritage designation phrasing is present", () => {
    expect(extractHeritage(MONTAGUE.rawSummaryText)).toBeNull();
    expect(extractHeritage(KING.rawSummaryText)).toBeNull();
  });

  it("does not false-positive on 'near a heritage property' phrasing", () => {
    const text = "This home sits near a Provincial Heritage Property in Old Town.";
    expect(extractHeritage(text)).toBeNull();
  });

  it("does not treat UNESCO World Heritage Site context as a designation", () => {
    const text = "Located in the UNESCO World Heritage Site of Old Town Lunenburg.";
    expect(extractHeritage(text)).toBeNull();
  });
});

describe("extractListingEvents", () => {
  it("deduplicates identical {date,event,price} triples", () => {
    const lines = FOX.rawSummaryText.split(/\r?\n/).map((s) => s.trim());
    const events = extractListingEvents(lines);
    const seen = new Set<string>();
    for (const ev of events) {
      const key = `${ev.date}|${ev.event}|${ev.price}`;
      expect(seen.has(key)).toBe(false);
      seen.add(key);
    }
  });

  it("labels price-change rows with the actual price-change description", () => {
    const lines = FOX.rawSummaryText.split(/\r?\n/).map((s) => s.trim());
    const events = extractListingEvents(lines);
    const priceChange = events.find((ev) => ev.date === "Jun 20, 2025");
    expect(priceChange).toBeDefined();
    expect(priceChange?.event).toMatch(/Price change/i);
  });

  it("returns one event for the single-listing 94 King case", () => {
    const lines = KING.rawSummaryText.split(/\r?\n/).map((s) => s.trim());
    const events = extractListingEvents(lines);
    expect(events.length).toBeGreaterThanOrEqual(1);
    const initial = events[0];
    expect(initial?.date).toBe("Feb 5, 2026");
    expect(initial?.price).toBe("$825,000");
  });

  it("returns [] when no LISTING HISTORY section is present", () => {
    expect(extractListingEvents(["random", "text", "with", "no", "section"])).toEqual([]);
  });
});

describe("parseViewpointBody — full integration", () => {
  it("extracts Tier-B fields for 56 Montague (VP brokerage)", () => {
    const details = buildDetails(MONTAGUE.rawSummaryText);
    const parsed = parseViewpointBody(MONTAGUE.rawSummaryText, details);
    expect(parsed.heating).toBe("Baseboard, Radiator, Hot Water");
    expect(parsed.foundation).toBe("Stone");
    expect(parsed.basement).toBe("Full, Fully Developed, Walkout");
    expect(parsed.water).toBe("Municipal");
    expect(parsed.sewer).toBe("Municipal");
    expect(parsed.brokerage).toBe("Viewpoint Realty Services Inc.(lunenburg)");
    expect(parsed.listingAgentName).toBe("STEPHANIE DEVRIES");
    expect(parsed.heritageDesignated).toBeNull();
  });

  it("extracts Tier-B fields for 69 Fox (Sotheby's brokerage)", () => {
    const details = buildDetails(FOX.rawSummaryText);
    const parsed = parseViewpointBody(FOX.rawSummaryText, details);
    expect(parsed.heating).toBe("Baseboard, Stove, Fireplace");
    expect(parsed.roof).toBe("Shakes");
    expect(parsed.brokerage).toBe("Sotheby's International Realty Canada");
    expect(parsed.listingAgentName).toBeNull();
    expect(parsed.heritageDesignated).toBe("Provincial Heritage Property");
  });

  it("returns null zoning for MODL listings (known gap)", () => {
    const details = buildDetails(KING.rawSummaryText);
    const parsed = parseViewpointBody(KING.rawSummaryText, details);
    expect(parsed.zoning).toBeNull();
  });
});
