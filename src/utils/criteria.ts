export type Operator = ">=" | "<=" | "==" | "in" | "not_in";

export interface HardFilter {
  field: string;
  operator: Operator;
  value: number | string | string[];
  raw: string;
}

export interface SoftSignal {
  group: string;
  label: string;
}

export interface Criteria {
  hardFilters: HardFilter[];
  softSignals: SoftSignal[];
}

export class CriteriaParseError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "CriteriaParseError";
  }
}

const FIELD_ALIASES: Record<string, string> = {
  "units": "units",
  "price": "price",
  "location": "location",
  "lot size": "lot_size_acres",
  "lot size acres": "lot_size_acres",
  "excluded zones": "excluded_zones",
};

export function parseCriteria(markdown: string): Criteria {
  if (!markdown.trim()) {
    throw new CriteriaParseError("Criteria file is empty");
  }

  const hardSection = extractSection(markdown, "Hard filters");
  const softSection = extractSection(markdown, "Soft signals");

  if (!hardSection && !softSection) {
    throw new CriteriaParseError(
      "No 'Hard filters' or 'Soft signals' section found",
    );
  }

  const hardFilters = hardSection ? parseHardFilters(hardSection) : [];
  const softSignals = softSection ? parseSoftSignals(softSection) : [];

  if (hardFilters.length === 0 && softSignals.length === 0) {
    throw new CriteriaParseError("No parseable rules found");
  }

  return { hardFilters, softSignals };
}

function extractSection(md: string, name: string): string | null {
  const regex = new RegExp(
    `(?:^|\\n)##\\s+${escapeRegex(name)}\\s*\\n([\\s\\S]*?)(?=\\n##\\s|$)`,
    "i",
  );
  const match = md.match(regex);
  return match?.[1] ?? null;
}

function parseHardFilters(section: string): HardFilter[] {
  const filters: HardFilter[] = [];
  const lineRegex = /^-\s+\*\*([^*]+?):\*\*\s+(.+?)\s*$/gm;
  let m: RegExpExecArray | null;
  while ((m = lineRegex.exec(section)) !== null) {
    const rawLabel = m[1]?.trim() ?? "";
    const rawValue = m[2]?.trim() ?? "";
    const field = normalizeField(rawLabel);
    if (!field) continue;
    const parsed = parseRuleValue(rawValue);
    if (!parsed) continue;
    filters.push({
      field,
      operator: parsed.operator,
      value: parsed.value,
      raw: m[0] ?? "",
    });
  }
  return filters;
}

function parseSoftSignals(section: string): SoftSignal[] {
  const signals: SoftSignal[] = [];
  let currentGroup: string | null = null;
  for (const line of section.split("\n")) {
    const groupMatch = line.match(/^###\s+(.+?)\s*$/);
    if (groupMatch) {
      currentGroup = groupMatch[1]?.trim() ?? null;
      continue;
    }
    const bulletMatch = line.match(/^\s*-\s+(.+?)\s*$/);
    if (bulletMatch && currentGroup) {
      const label = bulletMatch[1]?.trim() ?? "";
      if (label) signals.push({ group: currentGroup, label });
    }
  }
  return signals;
}

function normalizeField(label: string): string | null {
  const key = label.trim().toLowerCase();
  return FIELD_ALIASES[key] ?? snakeCase(key);
}

function snakeCase(s: string): string {
  return s.replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "");
}

interface ParsedRule {
  operator: Operator;
  value: number | string | string[];
}

function parseRuleValue(raw: string): ParsedRule | null {
  const compare = raw.match(/^(>=|<=|==)\s+(.+)$/);
  if (compare) {
    const operator = compare[1] as Operator;
    const valueToken = compare[2]?.trim() ?? "";
    const num = parseNumber(valueToken);
    if (num !== null) return { operator, value: num };
    return { operator, value: valueToken };
  }

  const inMatch = raw.match(/^(in|not_in)\s+(.+)$/i);
  if (inMatch) {
    const operator = inMatch[1]?.toLowerCase() as Operator;
    const list = (inMatch[2] ?? "")
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    if (list.length === 0) return null;
    return { operator, value: list };
  }

  return null;
}

function parseNumber(token: string): number | null {
  const cleaned = token.replace(/^\$/, "").replace(/,/g, "").trim();
  if (!/^-?\d+(\.\d+)?$/.test(cleaned)) return null;
  return Number(cleaned);
}

function escapeRegex(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
