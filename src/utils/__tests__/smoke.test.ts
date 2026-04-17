import { describe, it, expect } from "vitest";

describe("test harness", () => {
  it("runs vitest", () => {
    expect(true).toBe(true);
  });

  it("supports async tests", async () => {
    const value = await Promise.resolve(42);
    expect(value).toBe(42);
  });
});
