import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { checkCollision } from "../collision.js";

let workDir: string;

beforeEach(() => {
  workDir = mkdtempSync(path.join(tmpdir(), "collision-test-"));
});

afterEach(() => {
  rmSync(workDir, { recursive: true, force: true });
});

function writeEval(slug: string, inputMd: string): string {
  const dir = path.join(workDir, slug);
  mkdirSync(dir, { recursive: true });
  writeFileSync(path.join(dir, "input.md"), inputMd, "utf-8");
  return dir;
}

const validInput = (price: number) => `# Property — Evaluation Input

## Listing Details

- **Address:** 142 Maple Lane, Mahone Bay, NS
- **Asking Price:** $${price.toLocaleString("en-US")}
- **Type:** duplex

## Units

| # | Name |
|---|------|
| 1 | A |

## Municipal

- **Municipality:** Mahone Bay
- **Province:** NS
`;

describe("checkCollision", () => {
  it("reports exists:false when the directory does not exist", () => {
    const missing = path.join(workDir, "nothing-here");
    const result = checkCollision(missing, { price: 400000 });
    expect(result.exists).toBe(false);
  });

  it("reports priceChanged:false when the existing input has the same price", () => {
    const dir = writeEval("same-price", validInput(400000));
    const result = checkCollision(dir, { price: 400000 });
    expect(result.exists).toBe(true);
    if (result.exists && !("unparseable" in result)) {
      expect(result.priceChanged).toBe(false);
      expect(result.oldPrice).toBe(400000);
      expect(result.newPrice).toBe(400000);
    }
  });

  it("reports priceChanged:true with old/new when prices differ", () => {
    const dir = writeEval("different-price", validInput(400000));
    const result = checkCollision(dir, { price: 380000 });
    expect(result.exists).toBe(true);
    if (result.exists && !("unparseable" in result)) {
      expect(result.priceChanged).toBe(true);
      expect(result.oldPrice).toBe(400000);
      expect(result.newPrice).toBe(380000);
    }
  });

  it("flags unparseable:true when input.md is malformed", () => {
    const dir = writeEval("malformed", "this is not a valid input.md\n");
    const result = checkCollision(dir, { price: 400000 });
    expect(result.exists).toBe(true);
    expect("unparseable" in result && result.unparseable).toBe(true);
  });

  it("flags unparseable when input.md is missing (dir exists, file absent)", () => {
    const dir = path.join(workDir, "no-input-md");
    mkdirSync(dir, { recursive: true });
    const result = checkCollision(dir, { price: 400000 });
    expect(result.exists).toBe(true);
    expect("unparseable" in result && result.unparseable).toBe(true);
  });

  it("does not mutate the target directory", () => {
    const dir = writeEval("readonly-check", validInput(400000));
    checkCollision(dir, { price: 380000 });
    const result = checkCollision(dir, { price: 400000 });
    expect(result.exists).toBe(true);
    if (result.exists && !("unparseable" in result)) {
      expect(result.priceChanged).toBe(false);
    }
  });
});
