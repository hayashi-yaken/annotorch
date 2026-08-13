import { useState } from "react";
import { api } from "../api";
import type { Presentation, QuestionType, TaskConfig } from "../api";

const QUESTIONS: Record<Presentation, QuestionType[]> = {
  single: ["hard_label", "soft_label"],
  pair: ["preference", "similarity"],
  group: ["ranking", "grouping"],
};

export default function TaskForm({ projectId, numItems, onCreated }: {
  projectId: string; numItems: number; onCreated: () => void;
}) {
  const [name, setName] = useState("");
  const [presentation, setPresentation] = useState<Presentation>("single");
  const [question, setQuestion] = useState<QuestionType>("hard_label");
  const [labels, setLabels] = useState("cat, dog");
  const [similarityMode, setSimilarityMode] =
    useState<"binary" | "continuous">("continuous");
  const [numUnits, setNumUnits] = useState(50);
  const [groupSize, setGroupSize] = useState(4);
  const [seed, setSeed] = useState(0);
  const [error, setError] = useState("");

  const needsLabels = question === "hard_label" || question === "soft_label";

  const create = async () => {
    setError("");
    const config: TaskConfig = { seed };
    if (needsLabels) {
      config.labels = labels.split(",").map((s) => s.trim()).filter(Boolean);
    }
    if (question === "similarity") config.similarity_mode = similarityMode;
    if (presentation !== "single") config.num_units = numUnits;
    if (presentation === "group") config.group_size = groupSize;
    try {
      await api.createTask(projectId, {
        name: name.trim() || `${presentation}-${question}`,
        presentation, question, config,
      });
      onCreated();
    } catch (e) { setError(String(e)); }
  };

  return (
    <div className="card">
      <div className="row">
        <input value={name} onChange={(e) => setName(e.target.value)}
               placeholder="タスク名" />
        <select value={presentation} onChange={(e) => {
          const p = e.target.value as Presentation;
          setPresentation(p);
          setQuestion(QUESTIONS[p][0]);
        }}>
          <option value="single">single（1枚ずつ）</option>
          <option value="pair">pair（2枚比較）</option>
          <option value="group">group（複数まとめて）</option>
        </select>
        <select value={question}
                onChange={(e) => setQuestion(e.target.value as QuestionType)}>
          {QUESTIONS[presentation].map((q) => (
            <option key={q} value={q}>{q}</option>
          ))}
        </select>
      </div>
      <div className="row">
        {needsLabels && (
          <label>ラベル（カンマ区切り）{" "}
            <input value={labels} onChange={(e) => setLabels(e.target.value)} size={30} />
          </label>
        )}
        {question === "similarity" && (
          <select value={similarityMode}
                  onChange={(e) => setSimilarityMode(e.target.value as "binary" | "continuous")}>
            <option value="continuous">連続値（0〜1）</option>
            <option value="binary">二値（同じ/違う）</option>
          </select>
        )}
        {presentation !== "single" && (
          <label>Unit数{" "}
            <input type="number" min={1} value={numUnits}
                   onChange={(e) => setNumUnits(+e.target.value)} style={{ width: 80 }} />
          </label>
        )}
        {presentation === "group" && (
          <label>グループサイズ{" "}
            <input type="number" min={2} value={groupSize}
                   onChange={(e) => setGroupSize(+e.target.value)} style={{ width: 60 }} />
          </label>
        )}
        <label>seed{" "}
          <input type="number" value={seed}
                 onChange={(e) => setSeed(+e.target.value)} style={{ width: 60 }} />
        </label>
        <button onClick={create} disabled={numItems === 0}>タスク作成</button>
        {numItems === 0 && <span>（先にアイテムを取り込んでね）</span>}
      </div>
      {error && <p className="error">{error}</p>}
    </div>
  );
}
