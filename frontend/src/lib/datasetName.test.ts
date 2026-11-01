import { describe, expect, it } from "vitest";
import { defaultDatasetName } from "./datasetName";

describe("defaultDatasetName", () => {
  const at = new Date(2026, 10, 1, 9, 5, 7);

  it("joins the task name and a local timestamp", () => {
    expect(defaultDatasetName("swan-duck", at)).toBe("swan-duck-20261101-090507");
  });
  it("replaces slashes and backslashes", () => {
    expect(defaultDatasetName("a/b\\c", at)).toBe("a_b_c-20261101-090507");
  });
  it("drops leading dots so the name is not hidden", () => {
    expect(defaultDatasetName("..x", at)).toBe("x-20261101-090507");
  });
  it("falls back to the timestamp when nothing is left", () => {
    expect(defaultDatasetName(" . ", at)).toBe("dataset-20261101-090507");
  });
});
