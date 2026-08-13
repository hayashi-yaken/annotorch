export function parseSplits(text: string): Record<string, number> {
  const out: Record<string, number> = {};
  for (const part of text.split(",")) {
    const [name, value] = part.split("=").map((s) => s.trim());
    const v = Number(value);
    if (!name || value === undefined || value === "" || !Number.isFinite(v)) {
      throw new Error(`invalid splits: ${part}`);
    }
    out[name] = v;
  }
  return out;
}
