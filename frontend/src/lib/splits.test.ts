import { describe, expect, it } from "vitest";
import { parseSplits } from "./splits";

describe("parseSplits", () => {
  it("parses name=fraction pairs", () => {
    expect(parseSplits("train=0.8,test=0.2")).toEqual({ train: 0.8, test: 0.2 });
  });
  it("trims whitespace", () => {
    expect(parseSplits(" train = 0.5 , val = 0.5 ")).toEqual({ train: 0.5, val: 0.5 });
  });
  it("throws on malformed input", () => {
    expect(() => parseSplits("train")).toThrow();
    expect(() => parseSplits("train=abc")).toThrow();
  });
});
