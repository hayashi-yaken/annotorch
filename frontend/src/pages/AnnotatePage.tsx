import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
import type { Answer, Project, Task, UnitView } from "../api";
import Grouping from "../components/answer/Grouping";
import HardLabel from "../components/answer/HardLabel";
import Preference from "../components/answer/Preference";
import Ranking from "../components/answer/Ranking";
import Similarity from "../components/answer/Similarity";
import SoftLabel from "../components/answer/SoftLabel";

export default function AnnotatePage({ project, task, onBack }: {
  project: Project; task: Task; onBack: () => void;
}) {
  const [units, setUnits] = useState<UnitView[] | null>(null);
  const [index, setIndex] = useState(0);
  const [error, setError] = useState("");

  useEffect(() => {
    api.listUnits(project.id, task.id).then((us) => {
      setUnits(us);
      const firstUnanswered = us.findIndex((u) => u.answer === null);
      setIndex(firstUnanswered === -1 ? 0 : firstUnanswered);
    });
  }, [project.id, task.id]);

  const save = useCallback(async (answer: Answer) => {
    if (!units) return;
    const unit = units[index];
    setError("");
    try {
      await api.saveAnnotation(project.id, task.id, unit.id, answer);
      setUnits(units.map((u, n) => (n === index ? { ...u, answer } : u)));
      if (index < units.length - 1) setIndex(index + 1);
    } catch (e) { setError(String(e)); }
  }, [units, index, project.id, task.id]);

  if (!units) return <div className="container">読み込み中…</div>;
  if (units.length === 0) {
    return (
      <div className="container">
        <button onClick={onBack}>← 戻る</button>
        <p>Unit がありません</p>
      </div>
    );
  }

  const unit = units[index];
  const answered = units.filter((u) => u.answer !== null).length;
  const editorProps = { projectId: project.id, task, unit, onSave: save };

  return (
    <div className="container">
      <div className="row">
        <button onClick={onBack}>← 戻る</button>
        <strong>{task.name}</strong>
        <span>{index + 1} / {units.length}（回答済み {answered}）</span>
        <button onClick={() => setIndex(Math.max(0, index - 1))}>前へ</button>
        <button onClick={() => setIndex(Math.min(units.length - 1, index + 1))}>
          次へ
        </button>
      </div>
      <div className="progress">
        <div style={{ width: `${(100 * answered) / units.length}%` }} />
      </div>
      {error && <p className="error">{error}</p>}
      {task.question === "hard_label" && <HardLabel key={unit.id} {...editorProps} />}
      {task.question === "soft_label" && <SoftLabel key={unit.id} {...editorProps} />}
      {task.question === "preference" && <Preference key={unit.id} {...editorProps} />}
      {task.question === "similarity" && <Similarity key={unit.id} {...editorProps} />}
      {task.question === "ranking" && <Ranking key={unit.id} {...editorProps} />}
      {task.question === "grouping" && <Grouping key={unit.id} {...editorProps} />}
    </div>
  );
}
