import test from "node:test";
import assert from "node:assert/strict";
import { accessSync } from "node:fs";

const requiredPaths = [
  "src/input/parser.ts",
  "src/input/manual-input.ts",
  "src/input/schema.ts",
  "src/analysis/financing.ts",
  "src/analysis/scenarios.ts",
  "src/analysis/projections.ts",
  "src/analysis/rent-vs-buy.ts",
  "src/analysis/risk.ts",
  "src/analysis/tax.ts",
  "src/regulation/municipality.ts",
  "src/regulation/provincial.ts",
  "src/regulation/registry.ts",
  "src/enhancement/quick-wins.ts",
  "src/enhancement/medium-investments.ts",
  "src/enhancement/major-value-adds.ts",
  "src/enhancement/revenue-strategy.ts",
  "src/enhancement/feasibility.ts",
  "src/output/markdown.ts",
  "src/output/google-sheets.ts",
  "src/output/telegram.ts",
  "src/agent/orchestrator.ts",
  "src/agent/data-gatherer.ts",
  "src/agent/narrative.ts",
];

test("repository includes the planned src directory structure", () => {
  for (const path of requiredPaths) {
    assert.doesNotThrow(() => accessSync(new URL(`../${path}`, import.meta.url)));
  }
});
