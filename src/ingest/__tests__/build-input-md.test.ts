import { describe, expect, it } from "vitest";
import { buildInputMd } from "../build-input-md.js";
import type { TierBData } from "../viewpoint-tier-b.js";

function baseRecord(overrides: Partial<TierBData> = {}): TierBData {
  return {
    url: "https://www.viewpoint.ca/property/60063062",
    pid: "60063062",
    fetchedAt: "2026-04-19T12:00:00.000Z",
    listPrice: "$1,175,000",
    address: "56 Montague Street, Lunenburg",
    yearBuilt: "152",
    lotSize: "2,153 sqft",
    daysOnMarket: "331",
    assessment: "$683,900",
    annualTaxes: "$9,410",
    zoning: null,
    heating: "Baseboard, Radiator, Hot Water",
    foundation: "Stone",
    basement: "Full, Fully Developed, Walkout",
    roof: "Asphalt Shingle",
    water: "Municipal",
    sewer: "Municipal",
    buildingStyle: "1.5 Storey",
    propertySubType: "Single Family",
    exteriorFinish: "Wood Siding",
    flooring: "Softwood, Hardwood",
    parking: "Driveway",
    occupancy: null,
    possession: null,
    heritageDesignated: null,
    listingAgentName: "STEPHANIE DEVRIES",
    listingAgentPhone: "902-521-1575",
    brokerage: "Viewpoint Realty Services Inc.(lunenburg)",
    listingEvents: [{ date: "May 23, 2025", event: "Listed", price: "$1,225,000" }],
    saleHistory: [
      { date: "Sep 22, 2016", price: "$380,000" },
      { date: "Sep 30, 2008", price: "$380,000" },
    ],
    rawSummaryText: null,
    details: {},
    warnings: [],
    ...overrides,
  };
}

describe("buildInputMd", () => {
  it("converts AGE to year-built using fetchedAt year", () => {
    const md = buildInputMd(baseRecord({ yearBuilt: "152", fetchedAt: "2026-04-19T00:00:00Z" }));
    expect(md).toContain("Year Built:** 1874");
  });

  it("treats numeric values >= 500 as already-formatted year-built", () => {
    const md = buildInputMd(baseRecord({ yearBuilt: "1885" }));
    expect(md).toContain("Year Built:** 1885");
  });

  it("renders [PROMPT USER] for missing year built", () => {
    const md = buildInputMd(baseRecord({ yearBuilt: null }));
    expect(md).toContain("Year Built:** [PROMPT USER]");
  });

  it("populates address, municipality, and pins province=NS", () => {
    const md = buildInputMd(baseRecord());
    expect(md).toContain("Address\\*:** 56 Montague Street, Lunenburg");
    expect(md).toContain("Municipality\\*:** Lunenburg");
    expect(md).toContain("Province\\*:** NS");
  });

  it("flags zoning as a known MODL gap when null", () => {
    const md = buildInputMd(baseRecord({ zoning: null }));
    expect(md).toContain("**Zoning:** [PROMPT USER]");
    expect(md).toContain("known gap: ViewPoint doesn't populate this");
  });

  it("uses the populated zoning value when present", () => {
    const md = buildInputMd(baseRecord({ zoning: "R-2" }));
    expect(md).toContain("**Zoning:** R-2");
    expect(md).not.toContain("known gap");
  });

  it("renders previous sale from the most recent saleHistory entry", () => {
    const md = buildInputMd(baseRecord());
    expect(md).toContain("Previous Sale Price:** $380,000 (Sep 22, 2016)");
  });

  it("falls back to [PROMPT USER] when saleHistory is empty", () => {
    const md = buildInputMd(baseRecord({ saleHistory: [] }));
    expect(md).toContain("Previous Sale Price:** [PROMPT USER]");
  });

  it("collapses water+sewer when both are 'Municipal'", () => {
    const md = buildInputMd(baseRecord());
    expect(md).toContain("Water/Sewer:** municipal");
  });

  it("composes the listing agent line with name + brokerage + phone", () => {
    const md = buildInputMd(baseRecord());
    expect(md).toContain(
      "Listing Agent:** STEPHANIE DEVRIES, Viewpoint Realty Services Inc.(lunenburg), 902-521-1575",
    );
  });

  it("marks heritage as 'no' when not designated", () => {
    const md = buildInputMd(baseRecord({ heritageDesignated: null }));
    expect(md).toMatch(/Heritage Designated:\*\* no\b/);
  });

  it("includes the heritage designation label when present", () => {
    const md = buildInputMd(baseRecord({ heritageDesignated: "Provincial Heritage Property" }));
    expect(md).toContain("Heritage Designated:** yes — Provincial Heritage Property");
  });

  it("flows assessment + tax + warnings into the diagnostics section", () => {
    const md = buildInputMd(
      baseRecord({ warnings: ['Tier-B field "zoning" not populated'] }),
    );
    expect(md).toContain("PID:** 60063062");
    expect(md).toContain("2026 Assessment:** $683,900");
    expect(md).toContain('Tier-B warnings:** Tier-B field "zoning" not populated');
  });

  it("includes the listing URL in the listing details", () => {
    const md = buildInputMd(baseRecord());
    expect(md).toContain("https://www.viewpoint.ca/property/60063062");
  });
});
