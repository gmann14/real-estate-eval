import { existsSync, readFileSync, statSync } from "node:fs";
import path from "node:path";

export interface IncomingFacts {
  price?: number;
}

export type CollisionResult =
  | { exists: false }
  | { exists: true; unparseable: true }
  | {
      exists: true;
      priceChanged: boolean;
      oldPrice?: number;
      newPrice?: number;
    };

export function checkCollision(
  evalDir: string,
  incoming: IncomingFacts,
): CollisionResult {
  if (!existsSync(evalDir) || !statSync(evalDir).isDirectory()) {
    return { exists: false };
  }

  const inputPath = path.join(evalDir, "input.md");
  if (!existsSync(inputPath)) {
    return { exists: true, unparseable: true };
  }

  const md = readFileSync(inputPath, "utf-8");
  const oldPrice = parsePrice(md);

  if (oldPrice === null) {
    return { exists: true, unparseable: true };
  }

  const newPrice = incoming.price;
  const priceChanged =
    typeof newPrice === "number" ? oldPrice !== newPrice : false;

  return { exists: true, priceChanged, oldPrice, newPrice };
}

function parsePrice(md: string): number | null {
  const m = md.match(/\*\*Asking Price:\*\*\s*\$?([\d,]+(?:\.\d+)?)/i);
  if (!m) return null;
  const cleaned = (m[1] ?? "").replace(/,/g, "");
  if (!cleaned || !/^\d+(\.\d+)?$/.test(cleaned)) return null;
  return Number(cleaned);
}
