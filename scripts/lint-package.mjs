import { readFileSync } from "node:fs";

const packageJson = JSON.parse(readFileSync(new URL("../package.json", import.meta.url), "utf8"));
const tsconfig = JSON.parse(readFileSync(new URL("../tsconfig.json", import.meta.url), "utf8"));
const npmrc = readFileSync(new URL("../.npmrc", import.meta.url), "utf8");

const requiredScripts = {
  lint: "node scripts/lint-package.mjs",
  test: "node --test",
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
const requiredIncludes = ["src/**/*.ts", "vitest.config.ts", "scripts/**/*.mjs", "tests/**/*.test.mjs"];

if (packageJson.packageManager !== "pnpm@10.28.2") {
  throw new Error(`Unexpected package manager: ${packageJson.packageManager ?? "missing"}`);
}

if (packageJson.dependencies) {
  throw new Error("package.json must not declare runtime dependencies");
}

if (packageJson.devDependencies) {
  throw new Error("package.json must not declare devDependencies");
}

for (const [scriptName, command] of Object.entries(requiredScripts)) {
  if (packageJson.scripts?.[scriptName] !== command) {
    throw new Error(`Unexpected ${scriptName} script: ${packageJson.scripts?.[scriptName] ?? "missing"}`);
  }
}

if (Object.keys(packageJson.scripts ?? {}).length !== Object.keys(requiredScripts).length) {
  throw new Error("package.json must only expose the supported scripts");
}

if (npmrc.trim() !== "update-notifier=false") {
  throw new Error("The repository .npmrc must disable the pnpm update notifier");
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
