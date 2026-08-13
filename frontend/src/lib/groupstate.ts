export function toggleInOrder(order: string[], id: string): string[] {
  return order.includes(id) ? order.filter((x) => x !== id) : [...order, id];
}

export function assignToGroup(
  groups: Record<string, number>, id: string, group: number,
): Record<string, number> {
  return { ...groups, [id]: group };
}

export function groupsToAnswer(
  itemIds: string[], groups: Record<string, number>,
): string[][] | null {
  if (!itemIds.every((id) => groups[id] !== undefined)) return null;
  const buckets = new Map<number, string[]>();
  for (const id of itemIds) {
    const g = groups[id];
    if (!buckets.has(g)) buckets.set(g, []);
    buckets.get(g)!.push(id);
  }
  return [...buckets.entries()].sort(([a], [b]) => a - b).map(([, ids]) => ids);
}
