import assert from "node:assert/strict";
import test from "node:test";

import {
  calculateClosingCosts,
  cmhcPremium,
  generateFinancingScenarios,
  monthlyPayment,
} from "../src/analysis/financing.ts";
import { monthlyPayment as monthlyPaymentFromIndex } from "../src/analysis/index.ts";
import { generateFinancingScenarios as generateFromScenarioModule } from "../src/analysis/scenarios.ts";

test("monthlyPayment uses the Canadian semi-annual compounding formula for the Prince Street fixture", () => {
  assert.equal(monthlyPayment(479180, 0.042, 5, 25), 2573);
});

test("monthlyPayment returns a zero-interest payment when the rate is zero", () => {
  assert.equal(monthlyPayment(120000, 0, 5, 25), 400);
});

test("cmhcPremium calculates the premium for a 5% down insured mortgage", () => {
  assert.equal(cmhcPremium(500000, 5), 19000);
});

test("cmhcPremium calculates the premium using the split minimum down payment above $500K", () => {
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

  assert.equal(scenarios.length, 4);
  assert.deepEqual(
    scenarios.map((scenario) => scenario.name),
    ["Low leverage", "Medium leverage", "Conventional", "Investment"],
  );

  assert.deepEqual(
    {
      downPaymentPercent: scenarios[0]?.downPaymentPercent,
      downPaymentAmount: scenarios[0]?.downPaymentAmount,
      cmhcPremium: scenarios[0]?.cmhcPremium,
      totalMortgage: scenarios[0]?.totalMortgage,
      monthlyPayment: scenarios[0]?.monthlyPayment,
      cashToClose: scenarios[0]?.cashToClose,
    },
    {
      downPaymentPercent: 5,
      downPaymentAmount: 24250,
      cmhcPremium: 18430,
      totalMortgage: 479180,
      monthlyPayment: 2573,
      cashToClose: 35225,
    },
  );

  assert.deepEqual(
    {
      downPaymentPercent: scenarios[2]?.downPaymentPercent,
      downPaymentAmount: scenarios[2]?.downPaymentAmount,
      cmhcPremium: scenarios[2]?.cmhcPremium,
      totalMortgage: scenarios[2]?.totalMortgage,
      cashToClose: scenarios[2]?.cashToClose,
    },
    {
      downPaymentPercent: 20,
      downPaymentAmount: 97000,
      cmhcPremium: 0,
      totalMortgage: 388000,
      cashToClose: 107625,
    },
  );
});

test("scenario exports are available from the scenario module and analysis index", () => {
  assert.deepEqual(generateFromScenarioModule(485000), generateFinancingScenarios(485000));
  assert.equal(monthlyPaymentFromIndex(479180, 0.042, 5, 25), 2573);
});
