import { financingBreakdown } from "./financing.js";

function usage(): never {
  process.stderr.write(
    `Usage: npx tsx src/analysis/cli.ts <price> <down-fraction> <annual-rate> <amort-years>

Prints the Canadian-semi-annual-compounded financing breakdown as JSON.

Arguments:
  price         Purchase price in CAD (e.g. 485000)
  down-fraction Down payment as a decimal (e.g. 0.05 for 5%)
  annual-rate   Nominal annual mortgage rate (e.g. 0.042 for 4.2%)
  amort-years   Amortization in years (e.g. 25)

Example:
  npx tsx src/analysis/cli.ts 485000 0.05 0.042 25
`,
  );
  process.exit(2);
}

const args = process.argv.slice(2);
if (args.length !== 4) usage();

const [priceArg, downArg, rateArg, amortArg] = args as [string, string, string, string];
const price = Number(priceArg);
const down = Number(downArg);
const rate = Number(rateArg);
const amort = Number(amortArg);

if ([price, down, rate, amort].some((n) => !Number.isFinite(n))) {
  process.stderr.write(`All arguments must be numbers. Got: ${args.join(" ")}\n`);
  process.exit(2);
}

const result = financingBreakdown(price, down, rate, amort);
process.stdout.write(
  JSON.stringify(
    {
      purchasePrice: round2(result.purchasePrice),
      downPayment: round2(result.downPayment),
      baseMortgage: round2(result.baseMortgage),
      cmhcPremiumRate: Number(result.premiumRate.toFixed(5)),
      cmhcPremium: round2(result.cmhcPremium),
      totalMortgage: round2(result.totalMortgage),
      ltv: Number(result.ltv.toFixed(5)),
      monthlyPayment: round2(result.monthlyPayment),
    },
    null,
    2,
  ) + "\n",
);

function round2(n: number): number {
  return Math.round(n * 100) / 100;
}
