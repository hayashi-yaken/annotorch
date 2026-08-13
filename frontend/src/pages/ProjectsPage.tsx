import { useEffect, useState } from "react";
import { api, Project } from "../api";

export default function ProjectsPage({ onOpen }: { onOpen: (p: Project) => void }) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [name, setName] = useState("");
  const [error, setError] = useState("");

  const refresh = () =>
    api.listProjects().then(setProjects).catch((e) => setError(String(e)));
  useEffect(() => { refresh(); }, []);

  const create = async () => {
    if (!name.trim()) return;
    try {
      await api.createProject(name.trim());
      setName("");
      refresh();
    } catch (e) { setError(String(e)); }
  };

  const remove = async (p: Project) => {
    if (!confirm(`プロジェクト「${p.name}」を削除する？`)) return;
    try {
      await api.deleteProject(p.id);
      refresh();
    } catch (e) { setError(String(e)); }
  };

  return (
    <div className="container">
      <h1>annotorch</h1>
      {error && <p className="error">{error}</p>}
      <div className="row">
        <input value={name} onChange={(e) => setName(e.target.value)}
               placeholder="新しいプロジェクト名"
               onKeyDown={(e) => e.key === "Enter" && create()} />
        <button onClick={create}>作成</button>
      </div>
      {projects.map((p) => (
        <div key={p.id} className="card row">
          <strong>{p.name}</strong>
          <span>{p.description}</span>
          <button onClick={() => onOpen(p)}>開く</button>
          <button onClick={() => remove(p)}>削除</button>
        </div>
      ))}
      {projects.length === 0 && <p>プロジェクトはまだありません</p>}
    </div>
  );
}
