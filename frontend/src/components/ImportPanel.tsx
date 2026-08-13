import { useRef, useState } from "react";
import { api } from "../api";
import type { ImportReport } from "../api";

export default function ImportPanel({ projectId, onImported }: {
  projectId: string; onImported: () => void;
}) {
  const imageInput = useRef<HTMLInputElement>(null);
  const textInput = useRef<HTMLInputElement>(null);
  const [folder, setFolder] = useState("");
  const [report, setReport] = useState<ImportReport | null>(null);
  const [error, setError] = useState("");

  const run = async (fn: () => Promise<ImportReport>) => {
    setError("");
    try {
      setReport(await fn());
      onImported();
    } catch (e) { setError(String(e)); }
  };

  return (
    <div
      className="card"
      onDragOver={(e) => e.preventDefault()}
      onDrop={(e) => {
        e.preventDefault();
        const files = Array.from(e.dataTransfer.files);
        if (files.length) run(() => api.uploadImages(projectId, files));
      }}
    >
      <div className="row">
        <input ref={imageInput} type="file" multiple accept="image/*" />
        <button onClick={() => {
          const files = Array.from(imageInput.current?.files ?? []);
          if (files.length) run(() => api.uploadImages(projectId, files));
        }}>画像をアップロード</button>
        <span>（この枠に画像をドロップしてもOK）</span>
      </div>
      <div className="row">
        <input ref={textInput} type="file" accept=".jsonl,.csv" />
        <button onClick={() => {
          const f = textInput.current?.files?.[0];
          if (f) run(() => api.uploadTexts(projectId, f));
        }}>テキスト（JSONL/CSV）をアップロード</button>
      </div>
      <div className="row">
        <input value={folder} onChange={(e) => setFolder(e.target.value)} size={44}
               placeholder="サーバーから見えるフォルダパス（Docker では /import 配下）" />
        <button onClick={() => folder && run(() => api.importFolder(projectId, folder))}>
          フォルダから取り込み
        </button>
      </div>
      {report && (
        <p>
          取り込み {report.imported} 件 / スキップ {report.skipped.length} 件
          {report.skipped.slice(0, 3).map((s) => ` （${s.reason}）`).join("")}
        </p>
      )}
      {error && <p className="error">{error}</p>}
    </div>
  );
}
