import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const vitestConfigSource = readFileSync(new URL("../vitest.config.ts", import.meta.url), "utf8");

function loadVitestConfig() {
  return Function(
    `"use strict";\n${vitestConfigSource.replace("export default config;", "return config;")}`,
  )();
}

test("vitest.config.ts targets node-based Vitest test files", () => {
  const config = loadVitestConfig();

  assert.equal(config.test?.environment, "node");
  assert.deepEqual(config.test?.include, ["tests/**/*.vitest.test.{js,mjs,cjs,ts,mts,cts,jsx,tsx}"]);
  assert.equal(config.test?.passWithNoTests, true);
});
