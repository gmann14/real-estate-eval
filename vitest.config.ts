const config = {
  test: {
    environment: "node",
    include: ["tests/**/*.vitest.test.{js,mjs,cjs,ts,mts,cts,jsx,tsx}"],
    passWithNoTests: true,
  },
};

export default config;
