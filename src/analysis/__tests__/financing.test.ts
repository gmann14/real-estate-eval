import { describe, it, expect } from "vitest";
import {
  canadianEffectiveMonthlyRate,
  canadianMortgagePayment,
  cmhcPremiumRate,
  cmhcPremium,
  financingBreakdown,
} from "../financing.js";

describe("canadianEffectiveMonthlyRate", () => {
  it("converts 4.2% nominal → 0.34697% effective monthly", () => {
    expect(canadianEffectiveMonthlyRate(0.042)).toBeCloseTo(0.00346976, 8);
  });

  it("returns 0 for a 0% rate", () => {
    expect(canadianEffectiveMonthlyRate(0)).toBe(0);
  });

  it("differs from US-style r/12 by roughly 0.4% at 4.2%", () => {
    const canadian = canadianEffectiveMonthlyRate(0.042);
    const american = 0.042 / 12;
    expect(american).toBeGreaterThan(canadian);
    expect(american / canadian - 1).toBeCloseTo(0.00874, 3);
  });

  it("rejects negative rates", () => {
    expect(() => canadianEffectiveMonthlyRate(-0.01)).toThrow(RangeError);
  });
});

describe("canadianMortgagePayment", () => {
  it("matches the 9 Prince Street 5%-down known-answer case", () => {
    const payment = canadianMortgagePayment({
      principal: 479_180,
      annualRate: 0.042,
      amortizationYears: 25,
    });
    expect(payment).toBeCloseTo(2572.8, 1);
  });

  it("matches the 9 Prince Street 20%-down known-answer case", () => {
    const payment = canadianMortgagePayment({
      principal: 388_000,
      annualRate: 0.042,
      amortizationYears: 25,
    });
    expect(payment).toBeCloseTo(2083.24, 1);
  });

  it("produces meaningfully lower payments than US monthly compounding", () => {
    const principal = 479_180;
    const rate = 0.042;
    const years = 25;
    const canadian = canadianMortgagePayment({
      principal,
      annualRate: rate,
      amortizationYears: years,
    });
    const n = years * 12;
    const i = rate / 12;
    const american = (principal * i) / (1 - Math.pow(1 + i, -n));
    expect(american - canadian).toBeCloseTo(9.7, 1);
  });

  it("handles 0% rate as principal / n", () => {
    expect(
      canadianMortgagePayment({ principal: 300_000, annualRate: 0, amortizationYears: 25 }),
    ).toBe(1000);
  });

  it("returns 0 for zero principal", () => {
    expect(
      canadianMortgagePayment({ principal: 0, annualRate: 0.05, amortizationYears: 25 }),
    ).toBe(0);
  });

  it("rejects negative principal", () => {
    expect(() =>
      canadianMortgagePayment({ principal: -1, annualRate: 0.04, amortizationYears: 25 }),
    ).toThrow(RangeError);
  });

  it("rejects non-positive amortization", () => {
    expect(() =>
      canadianMortgagePayment({ principal: 300_000, annualRate: 0.04, amortizationYears: 0 }),
    ).toThrow(RangeError);
  });
});

describe("cmhcPremiumRate", () => {
  it("returns 4.0% at 95% LTV", () => {
    expect(cmhcPremiumRate(0.95)).toBe(0.04);
  });

  it("returns 3.1% at 90% LTV", () => {
    expect(cmhcPremiumRate(0.9)).toBe(0.031);
  });

  it("returns 2.4% at 80% LTV", () => {
    expect(cmhcPremiumRate(0.8)).toBe(0.024);
  });

  it("adds surcharges", () => {
    expect(cmhcPremiumRate(0.95, 0.002)).toBe(0.042);
  });

  it("rejects LTVs above 95%", () => {
    expect(() => cmhcPremiumRate(0.96)).toThrow(RangeError);
  });

  it("tolerates floating-point LTVs that are 0.95 by intent (e.g. 0.9500000000000001)", () => {
    expect(cmhcPremiumRate(0.95 + 1e-12)).toBe(0.04);
  });
});

describe("financingBreakdown — floating-point edge cases", () => {
  it("handles 5% down on $749,999 without tripping the LTV guard", () => {
    const result = financingBreakdown(749_999, 0.05, 0.042, 25);
    expect(result.premiumRate).toBe(0.04);
    expect(result.totalMortgage).toBeCloseTo(740_999.01, 2);
    expect(result.monthlyPayment).toBeCloseTo(3978.56, 1);
  });
});

describe("cmhcPremium", () => {
  it("computes the 9 Prince Street 5% down case exactly", () => {
    const result = cmhcPremium({ purchasePrice: 485_000, downPayment: 24_250 });
    expect(result.baseMortgage).toBe(460_750);
    expect(result.ltv).toBeCloseTo(0.95, 10);
    expect(result.rate).toBe(0.04);
    expect(result.premium).toBe(18_430);
  });

  it("waives the premium at 20%+ down", () => {
    const result = cmhcPremium({ purchasePrice: 485_000, downPayment: 97_000 });
    expect(result.premium).toBe(0);
    expect(result.rate).toBe(0);
  });

  it("waives the premium when fully paid", () => {
    const result = cmhcPremium({ purchasePrice: 485_000, downPayment: 485_000 });
    expect(result.premium).toBe(0);
  });
});

describe("financingBreakdown — end-to-end", () => {
  it("reproduces 9 Prince Street at 5% down", () => {
    const b = financingBreakdown(485_000, 0.05, 0.042, 25);
    expect(b.downPayment).toBe(24_250);
    expect(b.baseMortgage).toBe(460_750);
    expect(b.cmhcPremium).toBe(18_430);
    expect(b.totalMortgage).toBe(479_180);
    expect(b.monthlyPayment).toBeCloseTo(2572.8, 1);
  });

  it("reproduces 9 Prince Street at 20% down", () => {
    const b = financingBreakdown(485_000, 0.2, 0.042, 25);
    expect(b.downPayment).toBe(97_000);
    expect(b.cmhcPremium).toBe(0);
    expect(b.totalMortgage).toBe(388_000);
    expect(b.monthlyPayment).toBeCloseTo(2083.24, 1);
  });

  it("produces internally consistent numbers (down + baseMortgage == price)", () => {
    const b = financingBreakdown(425_000, 0.05, 0.042, 25);
    expect(b.downPayment + b.baseMortgage).toBe(b.purchasePrice);
    expect(b.cmhcPremium + b.baseMortgage).toBe(b.totalMortgage);
  });

  it("reproduces the correct 142 Maple Lane 5%-down numbers (replacing the known-bad published values)", () => {
    const b = financingBreakdown(425_000, 0.05, 0.042, 25);
    expect(b.downPayment).toBe(21_250);
    expect(b.cmhcPremium).toBe(16_150);
    expect(b.totalMortgage).toBe(419_900);
    expect(b.monthlyPayment).toBeCloseTo(2254.52, 1);
  });
});
