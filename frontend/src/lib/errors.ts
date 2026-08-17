/** 例外を通知に載せられる1行のメッセージにする。 */
export function message(e: unknown): string {
  return e instanceof Error ? e.message : String(e);
}
