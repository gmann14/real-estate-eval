import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";

test("pnpm test succeeds when the package has no test files", () => {
  const tempDir = mkdtempSync(join(tmpdir(), "real-estate-eval-empty-tests-"));

  writeFileSync(
    join(tempDir, "package.json"),
    JSON.stringify(
      {
        name: "empty-test-suite",
        private: true,
        packageManager: "pnpm@10.28.2",
        scripts: {
          test: "node --test",
        },
      },
      null,
      2,
    ),
  );

  const result = spawnSync("pnpm", ["test"], {
    cwd: tempDir,
    encoding: "utf8",
  });

  assert.ifError(result.error);
  assert.equal(result.status, 0, result.stderr || result.stdout);
});
