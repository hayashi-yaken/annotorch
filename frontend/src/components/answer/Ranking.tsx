import { useState } from "react";
import { toggleInOrder } from "../../lib/groupstate";
import ItemView from "../ItemView";
import type { EditorProps } from "./types";

export default function Ranking({ projectId, unit, onSave }: EditorProps) {
  const [order, setOrder] = useState<string[]>(
    (unit.answer?.order as string[] | undefined) ?? [],
  );
  return (
    <div>
      <p>良い順にクリックして順位をつける（もう一度クリックで解除）</p>
      <div className="grid">
        {unit.items.map((item) => {
          const rank = order.indexOf(item.id);
          return (
            <div key={item.id} className={`clickable ${rank >= 0 ? "selected" : ""}`}
                 onClick={() => setOrder(toggleInOrder(order, item.id))}>
              <ItemView projectId={projectId} item={item} />
              <div>{rank >= 0 ? `${rank + 1} 位` : "未選択"}</div>
            </div>
          );
        })}
      </div>
      <div className="row">
        <button className="big" disabled={order.length !== unit.items.length}
                onClick={() => onSave({ order })}>
          保存して次へ
        </button>
        <button onClick={() => setOrder([])}>リセット</button>
      </div>
    </div>
  );
}
