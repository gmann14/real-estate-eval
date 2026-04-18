import test from "node:test";
import assert from "node:assert/strict";
import { copyFileSync, existsSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";

test("pnpm install succeeds with the repository package configuration", () => {
  const tempDir = mkdtempSync(join(tmpdir(), "real-estate-eval-pnpm-"));

  copyFileSync(new URL("../package.json", import.meta.url), join(tempDir, "package.json"));
  copyFileSync(new URL("../.npmrc", import.meta.url), join(tempDir, ".npmrc"));

  const result = spawnSync("pnpm", ["install"], {
    cwd: tempDir,
    encoding: "utf8",
  });

  assert.ifError(result.error);
  assert.equal(result.status, 0, result.stderr || result.stdout);
  assert.equal(existsSync(join(tempDir, "pnpm-lock.yaml")), true);
});
