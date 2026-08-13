export function normalizeDist(
  weights: Record<string, number>,
): Record<string, number> | null {
  const entries = Object.entries(weights).filter(([, v]) => v > 0);
  const total = entries.reduce((sum, [, v]) => sum + v, 0);
  if (total <= 0) return null;
  return Object.fromEntries(entries.map(([k, v]) => [k, v / total]));
}
