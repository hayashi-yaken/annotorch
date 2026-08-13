import { describe, expect, it } from "vitest";
import { assignToGroup, groupsToAnswer, toggleInOrder } from "./groupstate";

describe("toggleInOrder", () => {
  it("appends unknown id and removes known id", () => {
    expect(toggleInOrder([], "a")).toEqual(["a"]);
    expect(toggleInOrder(["a", "b"], "c")).toEqual(["a", "b", "c"]);
    expect(toggleInOrder(["a", "b", "c"], "b")).toEqual(["a", "c"]);
  });
});

describe("grouping", () => {
  it("assigns and reassigns items", () => {
    let g = assignToGroup({}, "a", 0);
    g = assignToGroup(g, "a", 1);
    expect(g).toEqual({ a: 1 });
  });
  it("returns null until every item is assigned", () => {
    expect(groupsToAnswer(["a", "b"], { a: 0 })).toBeNull();
  });
  it("builds partition ordered by group number", () => {
    const groups = { a: 1, b: 0, c: 1 };
    expect(groupsToAnswer(["a", "b", "c"], groups)).toEqual([["b"], ["a", "c"]]);
  });
});
