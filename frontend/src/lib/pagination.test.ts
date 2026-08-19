import { describe, expect, it } from "vitest";
import { pageSlice } from "./pagination";

describe("pageSlice", () => {
  it("returns the requested window of a full page", () => {
    expect(pageSlice(120, 1, 50)).toEqual({ page: 1, pageCount: 3, start: 50, end: 100 });
  });

  it("stops the last page at the total", () => {
    expect(pageSlice(120, 2, 50)).toEqual({ page: 2, pageCount: 3, start: 100, end: 120 });
  });

  it("clamps a page past the end onto the last page", () => {
    expect(pageSlice(120, 9, 50)).toEqual({ page: 2, pageCount: 3, start: 100, end: 120 });
  });

  it("clamps a negative page onto the first one", () => {
    expect(pageSlice(120, -1, 50)).toEqual({ page: 0, pageCount: 3, start: 0, end: 50 });
  });

  it("reports a single page when everything fits", () => {
    expect(pageSlice(50, 0, 50)).toEqual({ page: 0, pageCount: 1, start: 0, end: 50 });
  });

  it("reports one empty page when there is nothing to show", () => {
    expect(pageSlice(0, 0, 50)).toEqual({ page: 0, pageCount: 1, start: 0, end: 0 });
  });
});
