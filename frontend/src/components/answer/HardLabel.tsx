import { useEffect } from "react";
import ItemView from "../ItemView";
import type { EditorProps } from "./types";

export default function HardLabel({ projectId, task, unit, onSave }: EditorProps) {
  const labels = task.config.labels ?? [];

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const n = Number(e.key);
      if (n >= 1 && n <= Math.min(9, labels.length)) onSave({ label: labels[n - 1] });
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [labels, onSave]);

  const current = unit.answer?.label as string | undefined;
  return (
    <div>
      <ItemView projectId={projectId} item={unit.items[0]} size="large" />
      <div className="row">
        {labels.map((label, n) => (
          <button key={label}
                  className={`big ${current === label ? "selected" : ""}`}
                  onClick={() => onSave({ label })}>
            {n + 1}. {label}
          </button>
        ))}
      </div>
    </div>
  );
}
