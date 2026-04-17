import { describe, it, expect } from "vitest";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { loadMunicipalConfig } from "../municipal.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, "../../..");
const CONFIG_ROOT = path.join(REPO_ROOT, "config");
const opts = { configRoot: CONFIG_ROOT };

describe("loadMunicipalConfig", () => {
  it("routes Mahone Bay, NS to modl.md", () => {
    const cfg = loadMunicipalConfig("Mahone Bay", "NS", opts);
    expect(cfg?.slug).toBe("modl");
    expect(cfg?.content).toContain("Lunenburg South Shore");
  });

  it("routes Halifax, NS to hrm.md", () => {
    const cfg = loadMunicipalConfig("Halifax", "NS", opts);
    expect(cfg?.slug).toBe("hrm");
    expect(cfg?.content).toContain("Halifax Regional Municipality");
  });

  it("routes Chester, NS to modl.md (district-level)", () => {
    const cfg = loadMunicipalConfig("Chester", "NS", opts);
    expect(cfg?.slug).toBe("modl");
  });

  it("routes Lunenburg, NS to modl.md", () => {
    const cfg = loadMunicipalConfig("Lunenburg", "NS", opts);
    expect(cfg?.slug).toBe("modl");
  });

  it("returns null for Sydney, NS (not yet mapped)", () => {
    const cfg = loadMunicipalConfig("Sydney", "NS", opts);
    expect(cfg).toBeNull();
  });

  it("routes Montréal, QC to montreal.md (placeholder)", () => {
    const cfg = loadMunicipalConfig("Montréal", "QC", opts);
    expect(cfg?.slug).toBe("montreal");
    expect(cfg?.content).toMatch(/TODO/i);
  });

  it("handles the ASCII spelling 'Montreal'", () => {
    const cfg = loadMunicipalConfig("Montreal", "QC", opts);
    expect(cfg?.slug).toBe("montreal");
  });

  it("is case- and whitespace-insensitive", () => {
    const cfg = loadMunicipalConfig("  halifax  ", "ns", opts);
    expect(cfg?.slug).toBe("hrm");
  });

  it("returns null when the province is unknown", () => {
    const cfg = loadMunicipalConfig("Halifax", "ZZ", opts);
    expect(cfg).toBeNull();
  });
});
