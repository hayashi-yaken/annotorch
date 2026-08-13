import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
import type { Item, Project, Task, TaskWithProgress } from "../api";
import ExportPanel from "../components/ExportPanel";
import ImportPanel from "../components/ImportPanel";
import ItemView from "../components/ItemView";
import TaskForm from "../components/TaskForm";

export default function ProjectPage({ project, onBack, onAnnotate }: {
  project: Project;
  onBack: () => void;
  onAnnotate: (task: Task) => void;
}) {
  const [items, setItems] = useState<Item[]>([]);
  const [tasks, setTasks] = useState<TaskWithProgress[]>([]);
  const [exportTask, setExportTask] = useState<Task | null>(null);
  const [error, setError] = useState("");

  const refresh = useCallback(() => {
    api.listItems(project.id).then(setItems).catch((e) => setError(String(e)));
    api.listTasks(project.id).then(setTasks).catch((e) => setError(String(e)));
  }, [project.id]);
  useEffect(() => { refresh(); }, [refresh]);

  return (
    <div className="container">
      <div className="row">
        <button onClick={onBack}>← プロジェクト一覧</button>
        <h1>{project.name}</h1>
      </div>
      {error && <p className="error">{error}</p>}

      <h2>アイテム（{items.length}件）</h2>
      <ImportPanel projectId={project.id} onImported={refresh} />
      <div className="grid">
        {items.slice(0, 50).map((item) => (
          <ItemView key={item.id} projectId={project.id} item={item} />
        ))}
      </div>
      {items.length > 50 && <p>…他 {items.length - 50} 件</p>}

      <h2>タスク</h2>
      <TaskForm projectId={project.id} numItems={items.length} onCreated={refresh} />
      {tasks.map((t) => (
        <div key={t.id} className="card">
          <div className="row">
            <strong>{t.name}</strong>
            <span>{t.presentation}/{t.question}</span>
            <span>{t.answered_units}/{t.total_units} 回答済み</span>
            <button onClick={() => onAnnotate(t)}>アノテーション</button>
            <button onClick={() => setExportTask(t)}>エクスポート</button>
          </div>
          <div className="progress">
            <div style={{
              width: `${t.total_units ? (100 * t.answered_units) / t.total_units : 0}%`,
            }} />
          </div>
        </div>
      ))}
      {exportTask && (
        <ExportPanel projectId={project.id} task={exportTask}
                     onClose={() => setExportTask(null)} />
      )}
    </div>
  );
}
