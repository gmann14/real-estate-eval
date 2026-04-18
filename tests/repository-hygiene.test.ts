import assert from "node:assert/strict";
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";

const ROOT = new URL("..", import.meta.url);
const SOURCE_DIRECTORIES = ["src", "tests"];
const DISALLOWED_PATTERNS = [
  { pattern: new RegExp(String.raw`\bTO` + "DO\\b", "i"), label: "work-item marker" },
  { pattern: new RegExp(String.raw`\bFIX` + "ME\\b", "i"), label: "fix marker" },
  { pattern: new RegExp(String.raw`\bplace` + "holder\\b", "i"), label: "scaffold marker" },
];

function collectTypeScriptFiles(directory: string): string[] {
  const absoluteDirectory = new URL(`${directory}/`, ROOT);
  const entries = readdirSync(absoluteDirectory, { withFileTypes: true });

  return entries.flatMap((entry) => {
    const relativePath = join(directory, entry.name);

    if (entry.isDirectory()) {
      return collectTypeScriptFiles(relativePath);
    }

    return entry.isFile() && entry.name.endsWith(".ts") ? [relativePath] : [];
  });
}

test("repository does not contain empty scaffold TypeScript modules", () => {
  const emptyScaffoldModules = SOURCE_DIRECTORIES.flatMap(collectTypeScriptFiles).filter((filePath) => {
    const source = readFileSync(new URL(filePath, ROOT), "utf8").trim();
    return source === "export {};";
  });

  assert.deepEqual(emptyScaffoldModules, []);
});

test("repository does not contain unfinished markers in TypeScript code", () => {
  const violations = SOURCE_DIRECTORIES.flatMap(collectTypeScriptFiles).flatMap((filePath) => {
    const source = readFileSync(new URL(filePath, ROOT), "utf8");

    return DISALLOWED_PATTERNS.flatMap(({ pattern, label }) =>
      pattern.test(source) ? [`${filePath}: ${label}`] : []
    );
  });

  assert.deepEqual(violations, []);
});
