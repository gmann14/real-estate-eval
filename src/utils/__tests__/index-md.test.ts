import { describe, it, expect } from "vitest";
import { appendOrUpdate, IndexMdParseError, type EvalRecord } from "../index-md.js";

const baseRecord: EvalRecord = {
  slug: "142-maple-lane-mahone-bay",
  date: "2026-04-17",
  address: "142 Maple Lane, Mahone Bay, NS",
  price: 425000,
  type: "duplex",
  verdict: "full",
};

const EMPTY_TEMPLATE = `# Watchlist

| Date | Address | Price | Type | Verdict | Link |
|------|---------|-------|------|---------|------|
`;

describe("appendOrUpdate", () => {
  it("adds a row to the empty template", () => {
    const out = appendOrUpdate(EMPTY_TEMPLATE, baseRecord);
    expect(out).toContain("142 Maple Lane");
    expect(out).toContain("$425,000");
    expect(out).toContain("duplex");
    expect(out).toContain("2026-04-17");
    expect(out).toContain("[→](./142-maple-lane-mahone-bay/analysis.md)");
  });

  it("creates the table from scratch when given empty string", () => {
    const out = appendOrUpdate("", baseRecord);
    expect(out).toContain("# Watchlist");
    expect(out).toContain("| Date");
    expect(out).toContain("142 Maple Lane");
  });

  it("sorts rows by date descending when adding to a populated table", () => {
    const existing = `# Watchlist

| Date | Address | Price | Type | Verdict | Link |
|------|---------|-------|------|---------|------|
| 2026-03-10 | 9 Prince St, Lunenburg | $500,000 | duplex | full | [→](./9-prince-st-lunenburg/analysis.md) |
| 2026-02-01 | 5 Back Rd, Chester | $350,000 | SFH | light | [→](./5-back-rd-chester/analysis.md) |
`;
    const out = appendOrUpdate(existing, baseRecord);
    const maple = out.indexOf("142 Maple Lane");
    const prince = out.indexOf("9 Prince St");
    const chester = out.indexOf("5 Back Rd");
    expect(maple).toBeGreaterThan(-1);
    expect(maple).toBeLessThan(prince);
    expect(prince).toBeLessThan(chester);
  });

  it("updates an existing row with the same slug in place", () => {
    const existing = `# Watchlist

| Date | Address | Price | Type | Verdict | Link |
|------|---------|-------|------|---------|------|
| 2026-04-01 | 142 Maple Lane, Mahone Bay, NS | $450,000 | duplex | full | [→](./142-maple-lane-mahone-bay/analysis.md) |
`;
    const out = appendOrUpdate(existing, baseRecord);
    expect(out).toContain("$425,000");
    expect(out).not.toContain("$450,000");
    const count = (out.match(/142-maple-lane-mahone-bay/g) ?? []).length;
    expect(count).toBe(1);
  });

  it("is idempotent — running with the same record twice gives the same output", () => {
    const once = appendOrUpdate(EMPTY_TEMPLATE, baseRecord);
    const twice = appendOrUpdate(once, baseRecord);
    expect(twice).toBe(once);
  });

  it("throws IndexMdParseError on a file without a recognizable header", () => {
    const broken = `# Something else entirely

Just prose, no table here.`;
    expect(() => appendOrUpdate(broken, baseRecord)).toThrowError(
      IndexMdParseError,
    );
  });

  it("throws IndexMdParseError on a malformed table", () => {
    const broken = `# Watchlist

| Date | Address |
|------|
| 2026-03-10 |
`;
    expect(() => appendOrUpdate(broken, baseRecord)).toThrowError(
      IndexMdParseError,
    );
  });

  it("renders reject verdict with inline notes in the verdict cell", () => {
    const rejected: EvalRecord = {
      ...baseRecord,
      slug: "100-nope-st-halifax",
      address: "100 Nope St, Halifax, NS",
      verdict: "reject",
      notes: "price above cap",
    };
    const out = appendOrUpdate(EMPTY_TEMPLATE, rejected);
    expect(out).toMatch(/reject\s*—\s*price above cap/);
  });
});
