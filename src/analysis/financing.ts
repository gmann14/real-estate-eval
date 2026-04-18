import { readFileSync } from "node:fs";
import { createRequire } from "node:module";

interface CmhcPremiumBand {
  ltv_min: number;
  ltv_max: number;
  rate: number;
}

interface CmhcMinDownRule {
  up_to?: number;
  from?: number;
  to?: number;
  rate: number;
}

interface CmhcConfig {
  rules: {
    max_price: number;
    min_down_payment: CmhcMinDownRule[];
    premiums: CmhcPremiumBand[];
    owner_occupy_required: boolean;
    max_amortization_insured: number;
  };
}

interface ProvinceConfig {
  province: string;
  code: string;
  closing_costs: {
    deed_transfer_tax: {
      type: "flat_rate";
      rate: number;
    };
    legal_fees: {
      default: number;
    };
    home_inspection: {
      default: number;
    };
    appraisal: {
      required_for: "insured";
      cost: number;
    };
    title_insurance: {
      cost: number;
    };
    pst_on_cmhc?: {
      applicable: boolean;
      rate?: number;
    };
  };
}

export interface ClosingCostsResult {
  province: string;
  deedTransferTax: number;
  legalFees: number;
  homeInspection: number;
  appraisal: number;
  titleInsurance: number;
  pstOnCmhc: number;
  total: number;
}

export interface FinancingScenario {
  name: string;
  downPaymentPercent: number;
  downPaymentAmount: number;
  cmhcPremium: number;
  totalMortgage: number;
  monthlyPayment: number;
  cashToClose: number;
  closingCosts: ClosingCostsResult;
}

interface ClosingCostOptions {
  insured?: boolean;
  cmhcPremium?: number;
}

const DEFAULT_TERM_YEARS = 5;
const DEFAULT_AMORTIZATION_YEARS = 25;
const DEFAULT_ANNUAL_RATE = 0.042;
const DEFAULT_PROVINCE = "ns";
const require = createRequire(import.meta.url);

let yamlParse: ((source: string) => unknown) | undefined;

try {
  const yamlModule = require("yaml") as { parse?: (source: string) => unknown };
  yamlParse = yamlModule.parse;
} catch {
  yamlParse = undefined;
}

let cachedCmhcConfig: CmhcConfig | undefined;
const provinceConfigCache = new Map<string, ProvinceConfig>();

function readYamlFile<T>(relativePath: string): T {
  const source = readFileSync(new URL(relativePath, import.meta.url), "utf8");
  if (yamlParse) {
    return yamlParse(source) as T;
  }

  return JSON.parse(source) as T;
}

function loadCmhcConfig(): CmhcConfig {
  cachedCmhcConfig ??= readYamlFile<CmhcConfig>("../../config/cmhc-premiums.yaml");
  return cachedCmhcConfig;
}

function loadProvinceConfig(province: string): ProvinceConfig {
  const normalizedProvince = province.trim().toLowerCase();
  const cachedConfig = provinceConfigCache.get(normalizedProvince);
  if (cachedConfig) {
    return cachedConfig;
  }

  const provinceConfig = readYamlFile<ProvinceConfig>(`../../config/provinces/${normalizedProvince}.yaml`);
  provinceConfigCache.set(normalizedProvince, provinceConfig);
  return provinceConfig;
}

function roundCurrency(value: number): number {
  return Math.round((value + Number.EPSILON) * 100) / 100;
}

function minimumDownPayment(purchasePrice: number): number {
  const rules = loadCmhcConfig().rules.min_down_payment;
  const firstBracket = rules.find((rule) => rule.up_to !== undefined);
  const secondBracket = rules.find((rule) => rule.from !== undefined);

  if (!firstBracket || firstBracket.up_to === undefined) {
    throw new Error("CMHC config is missing the first minimum down payment bracket");
  }

  if (purchasePrice <= firstBracket.up_to) {
    return roundCurrency(purchasePrice * firstBracket.rate);
  }

  if (!secondBracket) {
    throw new Error("CMHC config is missing the second minimum down payment bracket");
  }

  return roundCurrency(firstBracket.up_to * firstBracket.rate + (purchasePrice - firstBracket.up_to) * secondBracket.rate);
}

function downPaymentAmountForPercent(purchasePrice: number, downPaymentPercent: number): number {
  const requestedAmount = purchasePrice * (downPaymentPercent / 100);
  if (downPaymentPercent >= 20) {
    return roundCurrency(requestedAmount);
  }

  return roundCurrency(Math.max(requestedAmount, minimumDownPayment(purchasePrice)));
}

function cmhcRateForLtv(ltv: number): number {
  const premiumBand = loadCmhcConfig().rules.premiums.find((band) => ltv >= band.ltv_min && ltv <= band.ltv_max);
  return premiumBand?.rate ?? 0;
}

export function monthlyPayment(
  principal: number,
  annualRate: number,
  years: number,
  amortizationYears: number,
): number {
  void years;

  if (principal <= 0) {
    return 0;
  }

  const totalMonths = amortizationYears * 12;
  if (annualRate === 0) {
    return Math.round(principal / totalMonths);
  }

  const monthlyRate = Math.pow(1 + annualRate / 2, 1 / 6) - 1;
  const growthFactor = Math.pow(1 + monthlyRate, totalMonths);
  const payment = (principal * monthlyRate * growthFactor) / (growthFactor - 1);

  return Math.round(payment);
}

export function cmhcPremium(purchasePrice: number, downPaymentPercent: number): number {
  const config = loadCmhcConfig();
  const downPaymentAmount = downPaymentAmountForPercent(purchasePrice, downPaymentPercent);

  if (purchasePrice > config.rules.max_price || downPaymentAmount >= purchasePrice * 0.2) {
    return 0;
  }

  const ltv = 1 - downPaymentAmount / purchasePrice;
  const premiumRate = cmhcRateForLtv(ltv);
  const mortgageAmount = purchasePrice - downPaymentAmount;

  return roundCurrency(mortgageAmount * premiumRate);
}

export function calculateClosingCosts(
  price: number,
  province: string,
  options: ClosingCostOptions = {},
): ClosingCostsResult {
  const provinceConfig = loadProvinceConfig(province);
  const insured = options.insured ?? true;
  const pstRate = provinceConfig.closing_costs.pst_on_cmhc?.rate ?? 0;
  const pstOnCmhc =
    provinceConfig.closing_costs.pst_on_cmhc?.applicable && options.cmhcPremium
      ? roundCurrency(options.cmhcPremium * pstRate)
      : 0;

  const result: ClosingCostsResult = {
    province: provinceConfig.code,
    deedTransferTax: roundCurrency(price * provinceConfig.closing_costs.deed_transfer_tax.rate),
    legalFees: provinceConfig.closing_costs.legal_fees.default,
    homeInspection: provinceConfig.closing_costs.home_inspection.default,
    appraisal: insured ? provinceConfig.closing_costs.appraisal.cost : 0,
    titleInsurance: provinceConfig.closing_costs.title_insurance.cost,
    pstOnCmhc,
    total: 0,
  };

  result.total = roundCurrency(
    result.deedTransferTax +
      result.legalFees +
      result.homeInspection +
      result.appraisal +
      result.titleInsurance +
      result.pstOnCmhc,
  );

  return result;
}

export function generateFinancingScenarios(price: number): FinancingScenario[] {
  const cmhcConfig = loadCmhcConfig();
  const scenarioDefinitions = [
    { name: "Low leverage", downPaymentPercent: 5, insured: true },
    { name: "Medium leverage", downPaymentPercent: 10, insured: true },
    { name: "Conventional", downPaymentPercent: 20, insured: false },
    { name: "Investment", downPaymentPercent: 20, insured: false },
  ].filter((scenarioDefinition) =>
    !scenarioDefinition.insured || price <= cmhcConfig.rules.max_price
  );

  return scenarioDefinitions.map((scenarioDefinition) => {
    const downPaymentAmount = downPaymentAmountForPercent(price, scenarioDefinition.downPaymentPercent);
    const insurancePremium = scenarioDefinition.insured ? cmhcPremium(price, scenarioDefinition.downPaymentPercent) : 0;
    const totalMortgage = roundCurrency(price - downPaymentAmount + insurancePremium);
    const closingCosts = calculateClosingCosts(price, DEFAULT_PROVINCE, {
      insured: insurancePremium > 0,
      cmhcPremium: insurancePremium,
    });

    return {
      name: scenarioDefinition.name,
      downPaymentPercent: scenarioDefinition.downPaymentPercent,
      downPaymentAmount,
      cmhcPremium: insurancePremium,
      totalMortgage,
      monthlyPayment: monthlyPayment(
        totalMortgage,
        DEFAULT_ANNUAL_RATE,
        DEFAULT_TERM_YEARS,
        DEFAULT_AMORTIZATION_YEARS,
      ),
      cashToClose: roundCurrency(downPaymentAmount + closingCosts.total),
      closingCosts,
    };
  });
}
