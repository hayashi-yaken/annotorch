import { describe, expect, it } from "vitest";
import { normalizeDist } from "./softlabel";

describe("normalizeDist", () => {
  it("normalizes positive weights to sum 1", () => {
    const dist = normalizeDist({ cat: 60, dog: 40 })!;
    expect(dist.cat).toBeCloseTo(0.6);
    expect(dist.dog).toBeCloseTo(0.4);
    expect(Object.values(dist).reduce((s, v) => s + v, 0)).toBeCloseTo(1);
  });
  it("drops zero-weight classes", () => {
    expect(normalizeDist({ cat: 50, dog: 0 })).toEqual({ cat: 1 });
  });
  it("returns null when everything is zero", () => {
    expect(normalizeDist({ cat: 0, dog: 0 })).toBeNull();
  });
});
