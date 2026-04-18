import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import * as analysis from "../src/analysis/index.ts";
import { calculateClosingCosts, cmhcPremium, generateFinancingScenarios, monthlyPayment } from "../src/analysis/financing.ts";
import { generateFinancingScenarios as generateFromScenarioModule } from "../src/analysis/scenarios.ts";

test("monthlyPayment matches the validated Prince Street fixture", () => {
  const principal = 479180;
  const annualRate = 0.042;
  const totalMonths = 25 * 12;
  const monthlyRate = Math.pow(1 + annualRate / 2, 1 / 6) - 1;
  const growthFactor = Math.pow(1 + monthlyRate, totalMonths);
  const expectedPayment = Math.round((principal * monthlyRate * growthFactor) / (growthFactor - 1));

  assert.equal(expectedPayment, 2573);
  assert.equal(monthlyPayment(479180, 0.042, 5, 25), 2573);
});

test("monthlyPayment returns a zero-interest payment when the rate is zero", () => {
  assert.equal(monthlyPayment(120000, 0, 5, 25), 400);
});

test("cmhcPremium calculates the premium for a 5% down insured mortgage", () => {
  assert.equal(cmhcPremium(500000, 5), 19000);
});

test("cmhcPremium applies the 3.1% premium band for a 10% down insured mortgage", () => {
  assert.equal(cmhcPremium(500000, 10), 13950);
});

test("cmhcPremium applies the 2.8% premium band for a 15% down insured mortgage", () => {
  assert.equal(cmhcPremium(500000, 15), 11900);
});

test("cmhcPremium uses the statutory split minimum down payment above $500K", () => {
  assert.equal(cmhcPremium(750000, 5), 28000);
});

test("cmhcPremium does not apply CMHC at 20% down", () => {
  assert.equal(cmhcPremium(485000, 20), 0);
});

test("calculateClosingCosts loads the Nova Scotia config and includes the appraisal for insured purchases", () => {
  assert.deepEqual(calculateClosingCosts(485000, "ns"), {
    province: "NS",
    deedTransferTax: 7275,
    legalFees: 2500,
    homeInspection: 500,
    appraisal: 350,
    titleInsurance: 350,
    pstOnCmhc: 0,
    total: 10975,
  });
});

test("calculateClosingCosts omits the appraisal for uninsured purchases", () => {
  assert.equal(calculateClosingCosts(485000, "NS", { insured: false }).appraisal, 0);
});

test("generateFinancingScenarios returns the four required scenarios for the modeled offer price", () => {
  const scenarios = generateFinancingScenarios(485000);

  assert.deepEqual(
    scenarios.map((scenario) => ({
      name: scenario.name,
      downPaymentPercent: scenario.downPaymentPercent,
      downPaymentAmount: scenario.downPaymentAmount,
      cmhcPremium: scenario.cmhcPremium,
      totalMortgage: scenario.totalMortgage,
      monthlyPayment: scenario.monthlyPayment,
      cashToClose: scenario.cashToClose,
      closingCosts: scenario.closingCosts,
    })),
    [
      {
        name: "Low leverage",
        downPaymentPercent: 5,
        downPaymentAmount: 24250,
        cmhcPremium: 18430,
        totalMortgage: 479180,
        monthlyPayment: 2573,
        cashToClose: 35225,
        closingCosts: {
          province: "NS",
          deedTransferTax: 7275,
          legalFees: 2500,
          homeInspection: 500,
          appraisal: 350,
          titleInsurance: 350,
          pstOnCmhc: 0,
          total: 10975,
        },
      },
      {
        name: "Medium leverage",
        downPaymentPercent: 10,
        downPaymentAmount: 48500,
        cmhcPremium: 13531.5,
        totalMortgage: 450031.5,
        monthlyPayment: 2416,
        cashToClose: 59475,
        closingCosts: {
          province: "NS",
          deedTransferTax: 7275,
          legalFees: 2500,
          homeInspection: 500,
          appraisal: 350,
          titleInsurance: 350,
          pstOnCmhc: 0,
          total: 10975,
        },
      },
      {
        name: "Conventional",
        downPaymentPercent: 20,
        downPaymentAmount: 97000,
        cmhcPremium: 0,
        totalMortgage: 388000,
        monthlyPayment: 2083,
        cashToClose: 107625,
        closingCosts: {
          province: "NS",
          deedTransferTax: 7275,
          legalFees: 2500,
          homeInspection: 500,
          appraisal: 0,
          titleInsurance: 350,
          pstOnCmhc: 0,
          total: 10625,
        },
      },
      {
        name: "Investment",
        downPaymentPercent: 20,
        downPaymentAmount: 97000,
        cmhcPremium: 0,
        totalMortgage: 388000,
        monthlyPayment: 2083,
        cashToClose: 107625,
        closingCosts: {
          province: "NS",
          deedTransferTax: 7275,
          legalFees: 2500,
          homeInspection: 500,
          appraisal: 0,
          titleInsurance: 350,
          pstOnCmhc: 0,
          total: 10625,
        },
      },
    ],
  );
});

test("generateFinancingScenarios excludes insured scenarios above the CMHC price cap", () => {
  assert.deepEqual(
    generateFinancingScenarios(1500000).map((scenario) => scenario.name),
    ["Conventional", "Investment"],
  );
});

test("analysis index re-exports the financing API", () => {
  assert.deepEqual(Object.keys(analysis).sort(), [
    "calculateClosingCosts",
    "cmhcPremium",
    "generateFinancingScenarios",
    "monthlyPayment",
  ]);
  assert.equal(analysis.monthlyPayment(479180, 0.042, 5, 25), 2573);
});

test("scenario exports are available from the scenario module", () => {
  assert.deepEqual(generateFromScenarioModule(485000), generateFinancingScenarios(485000));
});

test("tsconfig allows explicit TypeScript import specifiers for NodeNext modules", () => {
  const tsconfig = JSON.parse(
    readFileSync(new URL("../tsconfig.json", import.meta.url), "utf8"),
  ) as {
    compilerOptions?: {
      allowImportingTsExtensions?: boolean;
    };
  };

  assert.equal(tsconfig.compilerOptions?.allowImportingTsExtensions, true);
});
