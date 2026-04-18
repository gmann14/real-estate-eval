import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const tsconfig = JSON.parse(readFileSync(new URL("../tsconfig.json", import.meta.url), "utf8"));

test("tsconfig.json enables explicit strict compiler options", () => {
  assert.equal(tsconfig.compilerOptions?.allowJs, true);
  assert.equal(tsconfig.compilerOptions?.checkJs, true);
  assert.equal(tsconfig.compilerOptions?.target, "ES2022");
  assert.deepEqual(tsconfig.compilerOptions?.lib, ["ES2022"]);
  assert.equal(tsconfig.compilerOptions?.module, "NodeNext");
  assert.equal(tsconfig.compilerOptions?.moduleResolution, "NodeNext");
  assert.equal(tsconfig.compilerOptions?.strict, true);
  assert.equal(tsconfig.compilerOptions?.noEmit, true);
  assert.equal(tsconfig.compilerOptions?.exactOptionalPropertyTypes, true);
  assert.equal(tsconfig.compilerOptions?.noFallthroughCasesInSwitch, true);
  assert.equal(tsconfig.compilerOptions?.noUncheckedIndexedAccess, true);
  assert.deepEqual(tsconfig.compilerOptions?.types, ["node"]);
  assert.equal(tsconfig.compilerOptions?.esModuleInterop, true);
  assert.equal(tsconfig.compilerOptions?.forceConsistentCasingInFileNames, true);
  assert.equal(tsconfig.compilerOptions?.skipLibCheck, true);
});

test("tsconfig.json includes scripts and test files for checking", () => {
  assert.ok(tsconfig.include?.includes("src/**/*.ts"));
  assert.ok(tsconfig.include?.includes("vitest.config.ts"));
  assert.ok(tsconfig.include?.includes("scripts/**/*.mjs"));
  assert.ok(tsconfig.include?.includes("tests/**/*.test.mjs"));
});
