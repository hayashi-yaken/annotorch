import { useState } from "react";

/** 非同期ハンドラに実行中フラグを持たせ、完了までの二重実行を防ぐ。 */
export function useAsync<A extends unknown[]>(fn: (...args: A) => Promise<unknown>) {
  const [pending, setPending] = useState(false);

  const run = async (...args: A) => {
    if (pending) return;
    setPending(true);
    try {
      await fn(...args);
    } finally {
      setPending(false);
    }
  };

  return { pending, run };
}
