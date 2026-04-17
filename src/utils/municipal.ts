import { existsSync, readFileSync } from "node:fs";
import path from "node:path";

export interface MunicipalConfig {
  slug: string;
  filepath: string;
  content: string;
}

export interface LoadOptions {
  configRoot?: string;
}

const CITY_TO_SLUG: Record<string, Record<string, string>> = {
  NS: {
    "mahone bay": "modl",
    lunenburg: "modl",
    chester: "modl",
    bridgewater: "modl",
    halifax: "hrm",
    dartmouth: "hrm",
    bedford: "hrm",
    sackville: "hrm",
  },
  QC: {
    montreal: "montreal",
  },
};

export function loadMunicipalConfig(
  city: string,
  province: string,
  opts: LoadOptions = {},
): MunicipalConfig | null {
  const configRoot = opts.configRoot ?? path.join(process.cwd(), "config");
  const provKey = province.trim().toUpperCase();
  const cityKey = normalize(city);

  const provinceMap = CITY_TO_SLUG[provKey];
  if (!provinceMap) return null;

  const slug = provinceMap[cityKey];
  if (!slug) return null;

  const filepath = path.join(configRoot, "municipalities", `${slug}.md`);
  if (!existsSync(filepath)) return null;

  const content = readFileSync(filepath, "utf-8");
  return { slug, filepath, content };
}

function normalize(s: string): string {
  return s
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}
