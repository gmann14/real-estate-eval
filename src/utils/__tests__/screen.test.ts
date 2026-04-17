import { describe, it, expect } from "vitest";
import type { Criteria } from "../criteria.js";
import { screenListing } from "../screen.js";

const exampleCriteria: Criteria = {
  hardFilters: [
    { field: "units", operator: ">=", value: 2, raw: "" },
    { field: "price", operator: "<=", value: 600000, raw: "" },
    { field: "location", operator: "in", value: ["MODL", "HRM"], raw: "" },
    { field: "lot_size_acres", operator: ">=", value: 0.08, raw: "" },
    {
      field: "excluded_zones",
      operator: "not_in",
      value: ["flood", "industrial", "arterial"],
      raw: "",
    },
  ],
  softSignals: [],
};

describe("screenListing", () => {
  it("returns 'full' for a duplex at $425K in MODL with ADU potential", () => {
    const result = screenListing(
      {
        units: 2,
        price: 425000,
        jurisdiction: "MODL",
        lot_size_acres: 0.22,
        zones: ["residential"],
      },
      exampleCriteria,
    );
    expect(result).toBe("full");
  });

  it("returns 'full' for a duplex at $425K in MODL without ADU potential (hard pass)", () => {
    const result = screenListing(
      {
        units: 2,
        price: 425000,
        jurisdiction: "MODL",
        lot_size_acres: 0.1,
        zones: ["residential"],
      },
      exampleCriteria,
    );
    expect(result).toBe("full");
  });

  it("rejects a single-family home (units < 2)", () => {
    const result = screenListing(
      {
        units: 1,
        price: 425000,
        jurisdiction: "MODL",
        lot_size_acres: 0.22,
        zones: ["residential"],
      },
      exampleCriteria,
    );
    expect(result).toBe("reject");
  });

  it("rejects a duplex above the price cap", () => {
    const result = screenListing(
      {
        units: 2,
        price: 850000,
        jurisdiction: "MODL",
        lot_size_acres: 0.22,
        zones: ["residential"],
      },
      exampleCriteria,
    );
    expect(result).toBe("reject");
  });

  it("rejects a duplex outside allowed jurisdictions", () => {
    const result = screenListing(
      {
        units: 2,
        price: 425000,
        jurisdiction: "Kings",
        lot_size_acres: 0.22,
        zones: ["residential"],
      },
      exampleCriteria,
    );
    expect(result).toBe("reject");
  });

  it("rejects a property whose zones overlap excluded_zones", () => {
    const result = screenListing(
      {
        units: 2,
        price: 425000,
        jurisdiction: "MODL",
        lot_size_acres: 0.22,
        zones: ["residential", "flood"],
      },
      exampleCriteria,
    );
    expect(result).toBe("reject");
  });

  it("passes when a hard filter's field is missing from the facts", () => {
    const result = screenListing(
      {
        units: 2,
        price: 425000,
        jurisdiction: "MODL",
      },
      exampleCriteria,
    );
    expect(result).toBe("full");
  });

  it("returns 'full' when criteria has no hard filters", () => {
    const result = screenListing(
      { units: 1, price: 850000, jurisdiction: "Kings" },
      { hardFilters: [], softFilters: [], softSignals: [] } as unknown as Criteria,
    );
    expect(result).toBe("full");
  });

  it("is case-insensitive for location matching", () => {
    const result = screenListing(
      {
        units: 2,
        price: 425000,
        jurisdiction: "modl",
        lot_size_acres: 0.22,
      },
      exampleCriteria,
    );
    expect(result).toBe("full");
  });

  it("handles equality operator", () => {
    const criteria: Criteria = {
      hardFilters: [{ field: "units", operator: "==", value: 2, raw: "" }],
      softSignals: [],
    };
    expect(screenListing({ units: 2 }, criteria)).toBe("full");
    expect(screenListing({ units: 3 }, criteria)).toBe("reject");
  });
});
