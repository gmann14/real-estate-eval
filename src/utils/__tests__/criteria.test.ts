import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { parseCriteria, CriteriaParseError } from "../criteria.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "../../..");

const read = (rel: string) =>
  readFileSync(path.join(ROOT, rel), "utf-8");

describe("parseCriteria", () => {
  it("parses the example criteria file into structured rules", () => {
    const md = read("config/criteria.example.md");
    const c = parseCriteria(md);

    expect(c.hardFilters.length).toBeGreaterThanOrEqual(5);
    expect(c.softSignals.length).toBeGreaterThanOrEqual(6);

    const units = c.hardFilters.find((f) => f.field === "units");
    expect(units).toBeDefined();
    expect(units?.operator).toBe(">=");
    expect(units?.value).toBe(2);

    const price = c.hardFilters.find((f) => f.field === "price");
    expect(price?.operator).toBe("<=");
    expect(price?.value).toBe(600000);

    const location = c.hardFilters.find((f) => f.field === "location");
    expect(location?.operator).toBe("in");
    expect(location?.value).toEqual(["MODL", "HRM"]);

    const lot = c.hardFilters.find((f) => f.field === "lot_size_acres");
    expect(lot?.operator).toBe(">=");
    expect(lot?.value).toBe(0.08);

    const excluded = c.hardFilters.find((f) => f.field === "excluded_zones");
    expect(excluded?.operator).toBe("not_in");
    expect(excluded?.value).toEqual(["flood", "industrial", "arterial"]);
  });

  it("captures soft-signal groups from the example file", () => {
    const md = read("config/criteria.example.md");
    const c = parseCriteria(md);

    const groups = new Set(c.softSignals.map((s) => s.group));
    expect(groups.has("ADU potential")).toBe(true);
    expect(groups.has("Upgrade potential")).toBe(true);
    expect(groups.has("Condition signals")).toBe(true);

    const adu = c.softSignals.filter((s) => s.group === "ADU potential");
    expect(adu.length).toBeGreaterThanOrEqual(3);
    expect(adu.some((s) => s.label.toLowerCase().includes("basement"))).toBe(true);
  });

  it("parses a minimal file with only hard filters", () => {
    const md = read("tests/fixtures/criteria/minimal.md");
    const c = parseCriteria(md);
    expect(c.hardFilters).toHaveLength(2);
    expect(c.softSignals).toHaveLength(0);
  });

  it("throws CriteriaParseError on a malformed file", () => {
    const md = read("tests/fixtures/criteria/malformed.md");
    expect(() => parseCriteria(md)).toThrowError(CriteriaParseError);
  });

  it("throws CriteriaParseError on empty input", () => {
    expect(() => parseCriteria("")).toThrowError(CriteriaParseError);
  });

  it("parses '$600,000' style money values", () => {
    const md = `## Hard filters\n\n- **Price:** <= $600,000\n`;
    const c = parseCriteria(md);
    expect(c.hardFilters[0]?.value).toBe(600000);
  });

  it("preserves the raw source line on each hard filter", () => {
    const md = read("tests/fixtures/criteria/minimal.md");
    const c = parseCriteria(md);
    expect(c.hardFilters[0]?.raw).toContain("Units");
  });
});
