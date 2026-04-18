import { readFileSync } from "node:fs";

const packageJson = JSON.parse(readFileSync(new URL("../package.json", import.meta.url), "utf8"));
const tsconfig = JSON.parse(readFileSync(new URL("../tsconfig.json", import.meta.url), "utf8"));

const requiredDependencies = ["yaml"];
const requiredDevDependencies = ["@types/node", "ts-node", "typescript", "vitest"];
const requiredScripts = {
  lint: "node scripts/lint-package.mjs",
  test: "node --test",
  "test:vitest": "vitest run",
  typecheck: "tsc --noEmit",
};

for (const dependency of requiredDependencies) {
  if (!packageJson.dependencies?.[dependency]) {
    throw new Error(`Missing dependency: ${dependency}`);
  }
}

for (const dependency of requiredDevDependencies) {
  if (!packageJson.devDependencies?.[dependency]) {
    throw new Error(`Missing devDependency: ${dependency}`);
  }
}

for (const [scriptName, command] of Object.entries(requiredScripts)) {
  if (packageJson.scripts?.[scriptName] !== command) {
    throw new Error(`Unexpected ${scriptName} script: ${packageJson.scripts?.[scriptName] ?? "missing"}`);
  }
}

if (!tsconfig.compilerOptions?.strict) {
  throw new Error("TypeScript strict mode must be enabled");
}

if (!Array.isArray(tsconfig.include) || !tsconfig.include.includes("tests/**/*.test.mjs")) {
  throw new Error("tsconfig.json must include the test files");
}
