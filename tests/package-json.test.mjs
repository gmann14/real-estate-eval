import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const packageJson = JSON.parse(readFileSync(new URL("../package.json", import.meta.url), "utf8"));

test("package.json includes the requested packages", () => {
  assert.equal(packageJson.dependencies?.yaml, "latest");
  assert.equal(packageJson.devDependencies?.["@types/node"], "latest");
  assert.equal(packageJson.devDependencies?.["ts-node"], "latest");
  assert.equal(packageJson.devDependencies?.typescript, "latest");
  assert.equal(packageJson.devDependencies?.vitest, "latest");
});

test("package.json exposes validation scripts", () => {
  assert.equal(packageJson.scripts?.lint, "node scripts/lint-package.mjs");
  assert.equal(packageJson.scripts?.test, "node --test");
  assert.equal(packageJson.scripts?.["test:vitest"], "vitest run");
  assert.equal(packageJson.scripts?.typecheck, "tsc --noEmit");
});
