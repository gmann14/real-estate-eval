export interface MortgagePaymentInput {
  principal: number;
  annualRate: number;
  amortizationYears: number;
}

export interface CMHCPremiumInput {
  purchasePrice: number;
  downPayment: number;
  surcharges?: number;
}

export interface FinancingBreakdown {
  purchasePrice: number;
  downPayment: number;
  baseMortgage: number;
  cmhcPremium: number;
  totalMortgage: number;
  ltv: number;
  premiumRate: number;
  monthlyPayment: number;
}

export function canadianEffectiveMonthlyRate(annualRate: number): number {
  if (annualRate < 0) throw new RangeError("annualRate must be non-negative");
  return Math.pow(1 + annualRate / 2, 1 / 6) - 1;
}

export function canadianMortgagePayment(input: MortgagePaymentInput): number {
  const { principal, annualRate, amortizationYears } = input;
  if (principal < 0) throw new RangeError("principal must be non-negative");
  if (amortizationYears <= 0) throw new RangeError("amortizationYears must be positive");
  if (principal === 0) return 0;

  const n = amortizationYears * 12;
  const i = canadianEffectiveMonthlyRate(annualRate);

  if (i === 0) return principal / n;

  return (principal * i) / (1 - Math.pow(1 + i, -n));
}

export function cmhcPremiumRate(ltv: number, surcharges = 0): number {
  if (ltv <= 0.65) return 0.006 + surcharges;
  if (ltv <= 0.75) return 0.017 + surcharges;
  if (ltv <= 0.8) return 0.024 + surcharges;
  if (ltv <= 0.85) return 0.028 + surcharges;
  if (ltv <= 0.9) return 0.031 + surcharges;
  if (ltv <= 0.95) return 0.04 + surcharges;
  throw new RangeError(`LTV ${ltv} exceeds 95% — CMHC-insured financing not available`);
}

export function cmhcPremium(input: CMHCPremiumInput): { premium: number; baseMortgage: number; ltv: number; rate: number } {
  const { purchasePrice, downPayment, surcharges = 0 } = input;
  if (purchasePrice <= 0) throw new RangeError("purchasePrice must be positive");
  if (downPayment < 0) throw new RangeError("downPayment must be non-negative");
  if (downPayment >= purchasePrice) {
    return { premium: 0, baseMortgage: 0, ltv: 0, rate: 0 };
  }

  const baseMortgage = purchasePrice - downPayment;
  const ltv = baseMortgage / purchasePrice;

  if (ltv <= 0.8) {
    return { premium: 0, baseMortgage, ltv, rate: 0 };
  }

  const rate = cmhcPremiumRate(ltv, surcharges);
  return { premium: baseMortgage * rate, baseMortgage, ltv, rate };
}

export function financingBreakdown(
  purchasePrice: number,
  downPaymentFraction: number,
  annualRate: number,
  amortizationYears: number,
  surcharges = 0,
): FinancingBreakdown {
  if (downPaymentFraction < 0 || downPaymentFraction > 1) {
    throw new RangeError("downPaymentFraction must be between 0 and 1");
  }
  const downPayment = purchasePrice * downPaymentFraction;
  const { premium, baseMortgage, ltv, rate } = cmhcPremium({
    purchasePrice,
    downPayment,
    surcharges,
  });
  const totalMortgage = baseMortgage + premium;
  const monthlyPayment = canadianMortgagePayment({
    principal: totalMortgage,
    annualRate,
    amortizationYears,
  });

  return {
    purchasePrice,
    downPayment,
    baseMortgage,
    cmhcPremium: premium,
    totalMortgage,
    ltv,
    premiumRate: rate,
    monthlyPayment,
  };
}
