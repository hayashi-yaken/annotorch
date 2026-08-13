import { useEffect } from "react";
import ItemView from "../ItemView";
import type { EditorProps } from "./types";

export default function Preference({ projectId, unit, onSave }: EditorProps) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "ArrowLeft") onSave({ winner: 1 });
      else if (e.key === "ArrowRight") onSave({ winner: -1 });
      else if (e.key === "=") onSave({ winner: 0 });
      else if (e.key === " ") { e.preventDefault(); onSave({ winner: null }); }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onSave]);

  const [a, b] = unit.items;
  return (
    <div>
      <div className="row">
        <div style={{ flex: 1 }}><ItemView projectId={projectId} item={a} size="large" /></div>
        <div style={{ flex: 1 }}><ItemView projectId={projectId} item={b} size="large" /></div>
      </div>
      <div className="row">
        <button className="big" onClick={() => onSave({ winner: 1 })}>← 左が良い</button>
        <button className="big" onClick={() => onSave({ winner: 0 })}>= 引き分け</button>
        <button className="big" onClick={() => onSave({ winner: -1 })}>右が良い →</button>
        <button onClick={() => onSave({ winner: null })}>スキップ（スペース）</button>
      </div>
    </div>
  );
}
