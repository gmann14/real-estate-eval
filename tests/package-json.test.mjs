import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const packageJson = JSON.parse(readFileSync(new URL("../package.json", import.meta.url), "utf8"));
const npmrc = readFileSync(new URL("../.npmrc", import.meta.url), "utf8");

test("package.json stays installable without registry dependencies", () => {
  assert.equal(packageJson.packageManager, "pnpm@10.28.2");
  assert.equal(packageJson.dependencies, undefined);
  assert.equal(packageJson.devDependencies, undefined);
});

test("package.json exposes validation scripts", () => {
  assert.equal(packageJson.scripts?.lint, "node scripts/lint-package.mjs");
  assert.equal(packageJson.scripts?.test, "node --test");
  assert.deepEqual(Object.keys(packageJson.scripts ?? {}).sort(), ["lint", "test"]);
});

test(".npmrc disables pnpm update checks", () => {
  assert.equal(npmrc.trim(), "update-notifier=false");
});
