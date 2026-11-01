const pad = (n: number) => String(n).padStart(2, "0");

/** エクスポート名の初期値。サーバーが受け付ける1階層のフォルダ名にする。 */
export function defaultDatasetName(taskName: string, at: Date): string {
  const stamp = `${at.getFullYear()}${pad(at.getMonth() + 1)}${pad(at.getDate())}`
    + `-${pad(at.getHours())}${pad(at.getMinutes())}${pad(at.getSeconds())}`;
  const base = taskName.trim().replace(/[/\\]/g, "_").replace(/^\.+/, "").trim();
  return `${base || "dataset"}-${stamp}`;
}
