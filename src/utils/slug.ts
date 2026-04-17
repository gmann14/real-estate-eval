const PROVINCE_CODES = new Set([
  "NS", "QC", "NB", "PE", "NL", "ON", "MB", "SK", "AB", "BC", "YT", "NT", "NU",
]);

const COUNTRY_TOKENS = new Set(["Canada", "CA", "USA", "US"]);

const MAX_SLUG_LENGTH = 60;

export class InvalidAddressError extends Error {
  constructor(message = "Address is empty or unparseable") {
    super(message);
    this.name = "InvalidAddressError";
  }
}

export function slugify(address: string): string {
  if (!address || !address.trim()) {
    throw new InvalidAddressError();
  }

  const parts = address
    .split(",")
    .map((p) => p.trim())
    .filter(Boolean);

  const kept = parts.filter((p) => {
    if (PROVINCE_CODES.has(p.toUpperCase())) return false;
    if (COUNTRY_TOKENS.has(p)) return false;
    return true;
  });

  if (kept.length === 0) {
    throw new InvalidAddressError();
  }

  const slug = kebab(kept.join(" "));

  if (!slug) {
    throw new InvalidAddressError();
  }

  return capAtMaxLength(slug);
}

export function slugFromListingId(id: string, source: string): string {
  if (!id.trim() && !source.trim()) {
    throw new InvalidAddressError("Both id and source are empty");
  }

  const normalized = [kebab(id), kebab(source)].filter(Boolean);
  return capAtMaxLength(normalized.join("-"));
}

function kebab(input: string): string {
  return input
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[''`]/g, "")
    .replace(/[^a-zA-Z0-9]+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "")
    .toLowerCase();
}

function capAtMaxLength(slug: string): string {
  if (slug.length <= MAX_SLUG_LENGTH) return slug;
  const sliced = slug.slice(0, MAX_SLUG_LENGTH);
  const lastDash = sliced.lastIndexOf("-");
  return lastDash > 0 ? sliced.slice(0, lastDash) : sliced;
}
