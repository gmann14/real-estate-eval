import { describe, it, expect } from "vitest";
import {
  slugify,
  slugFromListingId,
  InvalidAddressError,
} from "../slug.js";

describe("slugify", () => {
  it.each([
    ["142 Maple Lane, Mahone Bay, NS", "142-maple-lane-mahone-bay"],
    ["9 Prince St, Lunenburg, NS", "9-prince-st-lunenburg"],
    ["1234 Rue St-Denis, Montréal, QC", "1234-rue-st-denis-montreal"],
    ["Lot 5, Back Road, Chester, NS", "lot-5-back-road-chester"],
    ["  15 O'Brien Ave, Halifax, NS  ", "15-obrien-ave-halifax"],
    ["742 Evergreen Terrace, Halifax, NS, Canada", "742-evergreen-terrace-halifax"],
    ["1 rue Saint-Jacques, Montréal, QC", "1-rue-saint-jacques-montreal"],
  ])("slugifies %j → %j", (input, expected) => {
    expect(slugify(input)).toBe(expected);
  });

  it("throws InvalidAddressError on empty string", () => {
    expect(() => slugify("")).toThrow(InvalidAddressError);
  });

  it("throws InvalidAddressError on whitespace-only", () => {
    expect(() => slugify("   ")).toThrow(InvalidAddressError);
  });

  it("throws InvalidAddressError when only a province code is given", () => {
    expect(() => slugify("NS")).toThrow(InvalidAddressError);
  });

  it("caps slug at 60 characters", () => {
    const long =
      "12345 Some Extraordinarily Long Street Name Blvd, Someplacewithalongname, NS";
    const result = slugify(long);
    expect(result.length).toBeLessThanOrEqual(60);
    expect(result).not.toMatch(/-$/);
  });

  it("collapses multiple dashes and trims edges", () => {
    expect(slugify("100 -- Main Street, Halifax, NS")).toBe(
      "100-main-street-halifax",
    );
  });
});

describe("slugFromListingId", () => {
  it("builds a slug from listing ID and source", () => {
    expect(slugFromListingId("MLS-12345", "RLTR")).toBe("mls-12345-rltr");
  });

  it("handles lowercase input", () => {
    expect(slugFromListingId("viewpoint-987", "vwpt")).toBe("viewpoint-987-vwpt");
  });

  it("strips unsafe characters from listing ID", () => {
    expect(slugFromListingId("MLS/12#345", "RLTR")).toBe("mls-12-345-rltr");
  });

  it("throws InvalidAddressError when both inputs are empty", () => {
    expect(() => slugFromListingId("", "")).toThrow(InvalidAddressError);
  });
});
