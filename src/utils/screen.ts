import type { Criteria, HardFilter } from "./criteria.js";

export interface PropertyFacts {
  units?: number;
  price?: number;
  jurisdiction?: string;
  lot_size_acres?: number;
  zones?: string[];
  [key: string]: unknown;
}

export type ScreenVerdict = "reject" | "light" | "full";

export function screenListing(
  facts: PropertyFacts,
  criteria: Criteria,
): ScreenVerdict {
  for (const filter of criteria.hardFilters) {
    if (!passesFilter(filter, facts)) return "reject";
  }
  return "full";
}

function passesFilter(filter: HardFilter, facts: PropertyFacts): boolean {
  const actual = readField(facts, filter.field);

  if (filter.field === "excluded_zones") {
    const zones = toStringArray(facts.zones);
    if (zones.length === 0) return true;
    const excluded = toStringArray(filter.value);
    return !zones.some((z) =>
      excluded.some((e) => e.toLowerCase() === z.toLowerCase()),
    );
  }

  if (actual === undefined || actual === null) return true;

  switch (filter.operator) {
    case ">=":
      return typeof actual === "number" && actual >= (filter.value as number);
    case "<=":
      return typeof actual === "number" && actual <= (filter.value as number);
    case "==":
      return actual === filter.value;
    case "in": {
      const allowed = toStringArray(filter.value);
      if (typeof actual !== "string") return true;
      return allowed.some((a) => a.toLowerCase() === actual.toLowerCase());
    }
    case "not_in": {
      const banned = toStringArray(filter.value);
      if (typeof actual !== "string") return true;
      return !banned.some((b) => b.toLowerCase() === actual.toLowerCase());
    }
  }
}

function readField(facts: PropertyFacts, field: string): unknown {
  if (field === "location") return facts.jurisdiction;
  return facts[field];
}

function toStringArray(v: unknown): string[] {
  if (Array.isArray(v)) return v.filter((x): x is string => typeof x === "string");
  return [];
}
