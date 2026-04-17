import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { validateInput } from "../validate-input.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const FIXTURES = path.resolve(__dirname, "../../../tests/fixtures/input");

const fx = (name: string) =>
  readFileSync(path.join(FIXTURES, name), "utf-8");

describe("validateInput", () => {
  it("accepts a full valid duplex", () => {
    const result = validateInput(fx("valid-duplex.md"));
    expect(result.valid).toBe(true);
    expect(result.errors).toHaveLength(0);
  });

  it("accepts a minimal valid input (just required fields)", () => {
    const result = validateInput(fx("valid-minimal.md"));
    expect(result.valid).toBe(true);
    expect(result.errors).toHaveLength(0);
  });

  it("rejects an input with missing price", () => {
    const result = validateInput(fx("missing-price.md"));
    expect(result.valid).toBe(false);
    expect(result.errors.map((e) => e.code)).toContain("PRICE_MISSING");
  });

  it("rejects an input with a placeholder address", () => {
    const result = validateInput(fx("missing-address.md"));
    expect(result.valid).toBe(false);
    expect(result.errors.map((e) => e.code)).toContain("ADDRESS_MISSING");
  });

  it("rejects a units table with inconsistent columns", () => {
    const result = validateInput(fx("bad-units-table.md"));
    expect(result.valid).toBe(false);
    expect(result.errors.map((e) => e.code)).toContain("UNITS_TABLE_MALFORMED");
  });

  it("rejects an unrelated document as missing sections and fields", () => {
    const result = validateInput(fx("unparseable.md"));
    expect(result.valid).toBe(false);
    const codes = result.errors.map((e) => e.code);
    expect(codes).toContain("SECTION_MISSING");
    expect(codes).toContain("ADDRESS_MISSING");
  });

  it("rejects inline placeholder values like [street, city, province]", () => {
    const md = `## Listing Details

- **Address:** [street, city]
- **Asking Price:** $400,000
- **Type:** duplex

## Units

| # | Name |
|---|------|
| 1 | A |

## Municipal

- **Municipality:** Halifax
- **Province:** NS
`;
    const result = validateInput(md);
    expect(result.valid).toBe(false);
    expect(result.errors.map((e) => e.code)).toContain("ADDRESS_MISSING");
  });

  it("rejects empty markdown", () => {
    const result = validateInput("");
    expect(result.valid).toBe(false);
    expect(result.errors.length).toBeGreaterThan(0);
  });

  it("returns an error with a field name when a field is missing", () => {
    const result = validateInput(fx("missing-price.md"));
    const priceError = result.errors.find((e) => e.code === "PRICE_MISSING");
    expect(priceError?.field).toBe("Asking Price");
  });
});
