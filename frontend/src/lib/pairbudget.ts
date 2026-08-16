export function pairBudgetRange(
  numItems: number,
  pairing: "random" | "anchor",
  numAnchors: number,
): { min: number; max: number } {
  if (pairing === "anchor") {
    return { min: numAnchors, max: numItems - numAnchors };
  }
  return { min: 1, max: Math.floor(numItems / 2) };
}
