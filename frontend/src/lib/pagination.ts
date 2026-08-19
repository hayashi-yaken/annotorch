export interface Page {
  page: number;
  pageCount: number;
  start: number;
  end: number;
}

/** 範囲外のページ番号を丸めたうえで、表示する要素の範囲を返す。 */
export function pageSlice(total: number, page: number, size: number): Page {
  const pageCount = Math.max(1, Math.ceil(total / size));
  const clamped = Math.min(Math.max(page, 0), pageCount - 1);
  const start = clamped * size;
  return { page: clamped, pageCount, start, end: Math.min(start + size, total) };
}
