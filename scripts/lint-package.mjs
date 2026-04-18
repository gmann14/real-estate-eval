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
const requiredCompilerOptions = {
  allowJs: true,
  checkJs: true,
  target: "ES2022",
  module: "NodeNext",
  moduleResolution: "NodeNext",
  strict: true,
  noEmit: true,
  exactOptionalPropertyTypes: true,
  noFallthroughCasesInSwitch: true,
  noUncheckedIndexedAccess: true,
  esModuleInterop: true,
  forceConsistentCasingInFileNames: true,
  skipLibCheck: true,
};
const requiredIncludes = ["vitest.config.ts", "scripts/**/*.mjs", "tests/**/*.test.mjs"];

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

for (const [optionName, expectedValue] of Object.entries(requiredCompilerOptions)) {
  if (tsconfig.compilerOptions?.[optionName] !== expectedValue) {
    throw new Error(
      `Unexpected compiler option ${optionName}: ${tsconfig.compilerOptions?.[optionName] ?? "missing"}`,
    );
  }
}

if (tsconfig.compilerOptions?.lib?.[0] !== "ES2022") {
  throw new Error(`Unexpected compiler option lib: ${tsconfig.compilerOptions?.lib ?? "missing"}`);
}

if (tsconfig.compilerOptions?.types?.[0] !== "node") {
  throw new Error(`Unexpected compiler option types: ${tsconfig.compilerOptions?.types ?? "missing"}`);
}

if (!Array.isArray(tsconfig.include) || requiredIncludes.some((pattern) => !tsconfig.include.includes(pattern))) {
  throw new Error("tsconfig.json must include the script and test files");
}
