import { useState } from "react";
import { normalizeDist } from "../../lib/softlabel";
import ItemView from "../ItemView";
import type { EditorProps } from "./types";

export default function SoftLabel({ projectId, task, unit, onSave }: EditorProps) {
  const labels = task.config.labels ?? [];
  const initial = (unit.answer?.dist as Record<string, number> | undefined) ?? {};
  const [weights, setWeights] = useState<Record<string, number>>(
    Object.fromEntries(labels.map((l) => [l, (initial[l] ?? 0) * 100])),
  );
  const dist = normalizeDist(weights);

  return (
    <div>
      <ItemView projectId={projectId} item={unit.items[0]} size="large" />
      {labels.map((label) => (
        <div className="row" key={label}>
          <span style={{ width: 120 }}>{label}</span>
          <input type="range" min={0} max={100} value={weights[label] ?? 0}
                 onChange={(e) => setWeights({ ...weights, [label]: +e.target.value })} />
          <span>{dist?.[label] !== undefined ? dist[label].toFixed(2) : "0.00"}</span>
        </div>
      ))}
      <button className="big" disabled={!dist}
              onClick={() => dist && onSave({ dist })}>
        保存して次へ
      </button>
    </div>
  );
}
