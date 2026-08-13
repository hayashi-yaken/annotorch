import { useState } from "react";
import { api } from "../api";
import type { ExportResult, Task } from "../api";
import { parseSplits } from "../lib/splits";

export default function ExportPanel({ projectId, task, onClose }: {
  projectId: string; task: Task; onClose: () => void;
}) {
  const [outputDir, setOutputDir] = useState("");
  const [splits, setSplits] = useState("");
  const [seed, setSeed] = useState(0);
  const [result, setResult] = useState<ExportResult | null>(null);
  const [error, setError] = useState("");

  const run = async () => {
    setError("");
    try {
      const parsed = splits.trim() ? parseSplits(splits) : null;
      setResult(await api.exportTask(projectId, task.id,
        { output_dir: outputDir.trim(), splits: parsed, seed }));
    } catch (e) { setError(String(e)); }
  };

  return (
    <div className="card">
      <h3>エクスポート: {task.name}</h3>
      <div className="row">
        <input value={outputDir} onChange={(e) => setOutputDir(e.target.value)} size={40}
               placeholder="出力先ディレクトリ（Docker では /data/exports/... 推奨）" />
        <input value={splits} onChange={(e) => setSplits(e.target.value)} size={24}
               placeholder="train=0.8,test=0.2（空なら全てtrain）" />
        <label>seed{" "}
          <input type="number" value={seed}
                 onChange={(e) => setSeed(+e.target.value)} style={{ width: 60 }} />
        </label>
        <button onClick={run} disabled={!outputDir.trim()}>データセット作成</button>
        <button onClick={onClose}>閉じる</button>
      </div>
      {error && <p className="error">{error}</p>}
      {result && (
        <div>
          <p>
            {result.num_rows} 件を {result.output_dir} に出力した
            {result.num_unanswered_units > 0 &&
              `（未回答 ${result.num_unanswered_units} Unit は除外）`}
            {result.num_skipped > 0 && `（スキップ ${result.num_skipped} 件は除外）`}
          </p>
          <pre>{
`from annotorch.datasets import load
ds = load(${JSON.stringify(result.output_dir)}, split="train")`
          }</pre>
        </div>
      )}
    </div>
  );
}
