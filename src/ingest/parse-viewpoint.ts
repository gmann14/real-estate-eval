/**
 * Pure parser for ViewPoint.ca page text.
 *
 * Takes the rendered `document.body.innerText` from a logged-in
 * ViewPoint cutsheet/property page and the parsed DETAILS dict, and
 * returns the structured TierBData fields. No DOM, no browser — fully
 * unit-testable.
 *
 * The browser-bound step (in viewpoint-tier-b.ts) only walks the DOM
 * to read text + build the LABEL:VALUE dict; everything else lives
 * here.
 */

export interface ListingEvent {
  date: string;
  event: string;
  price: string;
}

export interface ParsedViewpoint {
  listPrice: string | null;
  yearBuilt: string | null;
  lotSize: string | null;
  assessment: string | null;
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
}

const VIEWPOINT_HOUSE_AGENTS = new Set(["STEPHANIE DEVRIES"]);

const HERITAGE_PATTERNS: Array<{ pattern: RegExp; label: string }> = [
  { pattern: /Provincial Heritage Property/i, label: "Provincial Heritage Property" },
  { pattern: /Municipally? Designated Heritage|Municipal Heritage Property/i, label: "Municipal Heritage Property" },
  { pattern: /Federally? Designated Heritage|National Historic Site/i, label: "Federal/National Historic Site" },
];

const HERITAGE_NEGATIVE_GUARDS = [
  /\b(near|surrounded by|adjacent to|next to|close to)\s+[\w\s]{0,40}(heritage|historic)/i,
];

function pick(details: Record<string, string>, ...labels: string[]): string | null {
  for (const label of labels) {
    const v = details[label.toUpperCase()];
    if (v) return v;
  }
  return null;
}

function labeledLine(lines: string[], label: string): string | null {
  const target = label.toUpperCase();
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (!line) continue;
    if (line.toUpperCase() === target) {
      const next = lines[i + 1] ?? "";
      if (next && next !== "N/A" && next !== "—" && !/^\{\{/.test(next)) {
        return next;
      }
    }
  }
  return null;
}

export function buildDetails(text: string): Record<string, string> {
  const details: Record<string, string> = {};
  for (const raw of text.split(/\r?\n/)) {
    const line = raw.trim();
    const ci = line.indexOf(":");
    if (ci > 0 && ci < 80) {
      const key = line.slice(0, ci).trim().toUpperCase();
      const val = line.slice(ci + 1).trim();
      if (val && val !== "N/A" && val !== "—" && !/^\{\{/.test(val) && !/^https?:/.test(val)) {
        if (!details[key]) details[key] = val;
      }
    }
  }
  return details;
}

export function extractListingAgent(
  lines: string[],
  brokerage: string | null,
): { name: string | null; phone: string | null } {
  const isViewpointBrokerage = (brokerage ?? "").toLowerCase().includes("viewpoint");
  for (let i = 0; i < lines.length; i++) {
    if (!/REALTOR®/.test(lines[i] ?? "")) continue;
    const prev = (lines[i - 1] ?? "").trim();
    if (!prev || prev.length >= 60) continue;
    // Reject ViewPoint's house agent widget when the listing belongs to another brokerage.
    if (!isViewpointBrokerage && VIEWPOINT_HOUSE_AGENTS.has(prev.toUpperCase())) {
      return { name: null, phone: null };
    }
    // Looks like a name (mostly uppercase letters/spaces)
    if (!/^[A-Z][A-Z\s.'-]+$/.test(prev)) continue;
    let phone: string | null = null;
    for (let j = 1; j <= 3; j++) {
      const candidate = (lines[i + j] ?? "").trim();
      if (/^\d{3}-\d{3}-\d{4}$/.test(candidate)) {
        phone = candidate;
        break;
      }
    }
    return { name: prev, phone };
  }
  return { name: null, phone: null };
}

export function extractHeritage(text: string): string | null {
  for (const { pattern, label } of HERITAGE_PATTERNS) {
    const match = pattern.exec(text);
    if (!match) continue;
    // Look at the surrounding context to filter out "near a heritage property" cases.
    const start = Math.max(0, match.index - 60);
    const end = Math.min(text.length, match.index + match[0].length + 20);
    const context = text.slice(start, end);
    if (HERITAGE_NEGATIVE_GUARDS.some((guard) => guard.test(context))) continue;
    return label;
  }
  return null;
}

const DATE_PAT = /^(\d{4}-\d{2}-\d{2}|[A-Za-z]+ \d{1,2}, \d{4})$/;
const PRICE_PAT = /^\$[\d,]+$/;
const STATUS_PAT = /^(For Sale|Sold|Expired|Withdrawn|Pending|Conditional|Leased|Cancelled)$/i;
const EVENT_DESCRIPTION_PAT = /^(Price change|Status change|Sold|Withdrawn|Listed|Expired|Cancelled)/i;

export function extractListingEvents(lines: string[]): ListingEvent[] {
  let hStart = -1;
  for (let k = 0; k < lines.length - 1; k++) {
    if (lines[k] === "LISTING HISTORY" && /^STATUS$/.test(lines[k + 1] ?? "")) {
      hStart = k + 1;
      break;
    }
  }
  if (hStart < 0) {
    for (let k = 0; k < lines.length; k++) {
      if (lines[k] === "LISTING HISTORY") {
        hStart = k;
        break;
      }
    }
  }
  if (hStart < 0) return [];

  const hStop = Math.min(lines.length, hStart + 400);
  const events: ListingEvent[] = [];
  let lastStatus: string | null = null;

  for (let m = hStart; m < hStop; m++) {
    const ln = lines[m];
    if (!ln) continue;
    if (STATUS_PAT.test(ln)) {
      lastStatus = ln;
      continue;
    }
    if (!DATE_PAT.test(ln)) continue;

    let event = "";
    let price = "";
    for (let look = 1; look <= 3; look++) {
      const lk = (lines[m + look] ?? "").trim();
      if (!event && EVENT_DESCRIPTION_PAT.test(lk)) event = lk;
      if (!price && PRICE_PAT.test(lk)) price = lk;
    }
    if (!event && lastStatus) event = `${lastStatus} — listed`;
    events.push({ date: ln, event, price });
  }

  // Dedupe by full {date,event,price} triple. ViewPoint sometimes
  // renders the same listing-history block twice (collapsed-row repeat).
  const seen = new Set<string>();
  const deduped: ListingEvent[] = [];
  for (const ev of events) {
    const key = `${ev.date}|${ev.event}|${ev.price}`;
    if (seen.has(key)) continue;
    seen.add(key);
    deduped.push(ev);
  }
  return deduped;
}

export function parseViewpointBody(
  text: string,
  details: Record<string, string>,
): ParsedViewpoint {
  const lines = text.split(/\r?\n/).map((s) => s.trim());
  const brokerage = pick(details, "LISTED BY");
  const agent = extractListingAgent(lines, brokerage);
  const heritage =
    pick(details, "HERITAGE", "HERITAGE PROPERTY", "HERITAGE DESIGNATED") ??
    extractHeritage(text);

  return {
    listPrice: labeledLine(lines, "FOR SALE") ?? pick(details, "LIST PRICE", "PRICE"),
    yearBuilt: pick(details, "AGE", "YEAR BUILT"),
    lotSize:
      labeledLine(lines, "LOT SIZE") ??
      pick(details, "LISTING PARCEL SIZE", "PARCEL SIZE"),
    assessment: pick(details, "ASSESSED AT"),
    zoning: pick(details, "ZONING", "MLS ZONING"),
    heating: pick(details, "HEATING/COOLING", "HEATING", "HEAT TYPE"),
    foundation: pick(details, "FOUNDATION"),
    basement: pick(details, "BASEMENT"),
    roof: pick(details, "ROOF"),
    water: pick(details, "DRINKING WATER", "WATER", "WATER SOURCE"),
    sewer: pick(details, "SEWER"),
    buildingStyle: pick(details, "BUILDING STYLE", "STYLE"),
    propertySubType: pick(details, "PROPERTY SUB TYPE", "TYPE"),
    exteriorFinish: pick(details, "EXTERIOR", "EXTERIOR FINISH"),
    flooring: pick(details, "FLOORING"),
    parking: pick(details, "PARKING") ?? pick(details, "HAS GARAGE"),
    occupancy: pick(details, "OCCUPANCY"),
    possession: pick(details, "POSSESSION"),
    heritageDesignated: heritage,
    listingAgentName: agent.name,
    listingAgentPhone: agent.phone,
    brokerage,
    listingEvents: extractListingEvents(lines),
  };
}
