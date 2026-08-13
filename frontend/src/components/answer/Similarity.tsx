import { useState } from "react";
import ItemView from "../ItemView";
import type { EditorProps } from "./types";

export default function Similarity({ projectId, task, unit, onSave }: EditorProps) {
  const [score, setScore] = useState<number>(
    (unit.answer?.score as number | undefined) ?? 0.5,
  );
  const [a, b] = unit.items;
  return (
    <div>
      <div className="row">
        <div style={{ flex: 1 }}><ItemView projectId={projectId} item={a} size="large" /></div>
        <div style={{ flex: 1 }}><ItemView projectId={projectId} item={b} size="large" /></div>
      </div>
      {task.config.similarity_mode === "binary" ? (
        <div className="row">
          <button className="big" onClick={() => onSave({ same: true })}>同じ</button>
          <button className="big" onClick={() => onSave({ same: false })}>違う</button>
        </div>
      ) : (
        <div className="row">
          <span>似ていない</span>
          <input type="range" min={0} max={100} value={score * 100}
                 onChange={(e) => setScore(+e.target.value / 100)} />
          <span>似ている（{score.toFixed(2)}）</span>
          <button className="big" onClick={() => onSave({ score })}>保存して次へ</button>
        </div>
      )}
    </div>
  );
}
