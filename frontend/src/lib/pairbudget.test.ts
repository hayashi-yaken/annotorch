import { describe, expect, it } from "vitest";
import { pairBudgetRange } from "./pairbudget";

describe("pairBudgetRange", () => {
  it("allows floor(n / 2) pairs for random pairing", () => {
    expect(pairBudgetRange(10, "random", 0)).toEqual({ min: 1, max: 5 });
    expect(pairBudgetRange(11, "random", 0)).toEqual({ min: 1, max: 5 });
  });

  it("bounds anchor pairing by anchors and remaining items", () => {
    expect(pairBudgetRange(10, "anchor", 3)).toEqual({ min: 3, max: 7 });
  });

  it("reports an empty range when there are too few items", () => {
    expect(pairBudgetRange(1, "random", 0)).toEqual({ min: 1, max: 0 });
    expect(pairBudgetRange(4, "anchor", 3)).toEqual({ min: 3, max: 1 });
  });
});
