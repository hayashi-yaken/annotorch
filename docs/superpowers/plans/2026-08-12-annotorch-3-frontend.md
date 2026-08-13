# annotorch 計画3: 最小限の React UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 計画2のAPIを叩く最小限のReact UIを作り、「プロジェクト作成 → インポート → 全方式のアノテーション → データセット作成」がブラウザで一通り回るようにする。仕上げに Dockerfile へフロントビルドを組み込む。

**Architecture:** Vite + React + TypeScript。ルーターやUIライブラリは使わず、`useState` によるページ切り替えと素朴なCSSのみ。API呼び出しは `src/api.ts` の薄い fetch ラッパーに集約。ロジック（ソフトラベル正規化、順位付け・グルーピングの状態遷移、splits文字列パース）は純関数として `src/lib/` に置き、Vitest でテストする。ビルド成果物は `../src/annotorch/server/static` に出力して FastAPI が配信する。

**Tech Stack:** Node 20+, Vite, React 18+, TypeScript, Vitest。追加ライブラリなし（react-router / dnd / コンポーネントライブラリ不使用）。

**前提:** 計画1・2が完了していること。
**参照スペック:** `docs/superpowers/specs/2026-08-12-annotorch-design.md`

## Global Constraints

- 計画1・2の Global Constraints を引き継ぐ（preference winner = `1/-1/0/null` など）
- 依存は React + Vite + TypeScript + Vitest のみ。UIの作り込みは最小限（スペックの方針どおり、全方式が操作できることを優先）
- ranking / grouping はドラッグ&ドロップではなく**クリック操作**で実装する（最小実装。スペックに明記済み）
- API のベースパスは `/api` 固定。開発時は vite の proxy で `http://localhost:8000` へ、本番はFastAPIと同一オリジン
- フロントのコマンドはすべて `frontend/` で実行: `npm run dev` / `npm run build` / `npm run test`
- `npm run build` は `src/annotorch/server/static` へ出力（gitignore する）
- 動作確認: バックエンドは `uv run annotorch serve --root /tmp/annotorch-dev --no-browser` を別プロセスで起動しておく。ブラウザ操作の確認には Playwright MCP を使ってよい

---

### Task 1: Vite scaffold + APIクライアント + splitsパーサ

**Files:**
- Create: `frontend/`（`npm create vite` による scaffold 一式）
- Modify: `frontend/vite.config.ts`
- Modify: `frontend/package.json`（vitest 追加、test スクリプト）
- Create: `frontend/src/api.ts`
- Create: `frontend/src/lib/splits.ts`
- Modify: `.gitignore`
- Test: `frontend/src/lib/splits.test.ts`

**Interfaces:**
- Consumes: 計画2の全エンドポイント
- Produces:
  - 型: `Project`, `Item`, `Task`, `TaskWithProgress`, `UnitView`, `Answer`, `ImportReport`, `ExportResult`, `Presentation`, `QuestionType`
  - `api.*` メソッド群（下記コード参照）と `api.itemFileUrl(pid, itemId)`
  - `parseSplits(text: string): Record<string, number>`（不正入力は throw）

- [ ] **Step 1: scaffold と依存**

```bash
cd /Users/hayashinaofumi/workspace/hayashi-yaken/annotorch
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
npm install -D vitest
```

`.gitignore`（リポジトリルート）に追記:

```
frontend/node_modules/
src/annotorch/server/static/
```

`frontend/package.json` の scripts に追加: `"test": "vitest run"`

`frontend/vite.config.ts`（全置換）:

```ts
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  server: { proxy: { "/api": "http://localhost:8000" } },
  build: { outDir: "../src/annotorch/server/static", emptyOutDir: true },
});
```

- [ ] **Step 2: 失敗するテストを書く**

`frontend/src/lib/splits.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { parseSplits } from "./splits";

describe("parseSplits", () => {
  it("parses name=fraction pairs", () => {
    expect(parseSplits("train=0.8,test=0.2")).toEqual({ train: 0.8, test: 0.2 });
  });
  it("trims whitespace", () => {
    expect(parseSplits(" train = 0.5 , val = 0.5 ")).toEqual({ train: 0.5, val: 0.5 });
  });
  it("throws on malformed input", () => {
    expect(() => parseSplits("train")).toThrow();
    expect(() => parseSplits("train=abc")).toThrow();
  });
});
```

- [ ] **Step 3: テストを実行して失敗を確認**

Run: `npm run test`
Expected: FAIL（`splits.ts` が無い）

- [ ] **Step 4: 実装**

`frontend/src/lib/splits.ts`:

```ts
export function parseSplits(text: string): Record<string, number> {
  const out: Record<string, number> = {};
  for (const part of text.split(",")) {
    const [name, value] = part.split("=").map((s) => s.trim());
    const v = Number(value);
    if (!name || value === undefined || value === "" || !Number.isFinite(v)) {
      throw new Error(`invalid splits: ${part}`);
    }
    out[name] = v;
  }
  return out;
}
```

`frontend/src/api.ts`:

```ts
export type Modality = "image" | "text";
export type Presentation = "single" | "pair" | "group";
export type QuestionType =
  | "hard_label" | "soft_label" | "preference"
  | "similarity" | "ranking" | "grouping";

export interface Project {
  id: string; name: string; description: string; created_at: string;
}
export interface Item {
  id: string; project_id: string; modality: Modality;
  path: string | null; text: string | null; metadata: Record<string, unknown>;
}
export interface TaskConfig {
  labels?: string[] | null;
  similarity_mode?: "binary" | "continuous";
  group_size?: number | null;
  num_units?: number | null;
  seed?: number;
}
export interface Task {
  id: string; project_id: string; name: string;
  presentation: Presentation; question: QuestionType; config: TaskConfig;
}
export interface TaskWithProgress extends Task {
  total_units: number; answered_units: number;
}
export type Answer = Record<string, unknown>;
export interface UnitView {
  id: string; position: number; items: Item[]; answer: Answer | null;
}
export interface ImportReport {
  imported: number; skipped: { source: string; reason: string }[];
}
export interface ExportResult {
  output_dir: string; num_rows: number; num_unanswered_units: number;
  num_skipped: number; split_counts: Record<string, number>;
}

const BASE = "/api";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(BASE + path, init);
  if (!res.ok) {
    const detail = (await res.json().catch(() => null))?.detail;
    throw new Error(typeof detail === "string" ? detail : res.statusText);
  }
  return res.json();
}

const json = (method: string, body: unknown): RequestInit => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export const api = {
  listProjects: () => req<Project[]>("/projects"),
  createProject: (name: string, description = "") =>
    req<Project>("/projects", json("POST", { name, description })),
  deleteProject: (pid: string) =>
    req<{ ok: boolean }>(`/projects/${pid}`, { method: "DELETE" }),

  listItems: (pid: string) => req<Item[]>(`/projects/${pid}/items`),
  uploadImages: (pid: string, files: File[]) => {
    const fd = new FormData();
    files.forEach((f) => fd.append("files", f));
    return req<ImportReport>(`/projects/${pid}/items/upload`,
      { method: "POST", body: fd });
  },
  uploadTexts: (pid: string, file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return req<ImportReport>(`/projects/${pid}/items/upload-texts`,
      { method: "POST", body: fd });
  },
  importFolder: (pid: string, path: string) =>
    req<ImportReport>(`/projects/${pid}/items/import-folder`,
      json("POST", { path })),
  itemFileUrl: (pid: string, itemId: string) =>
    `${BASE}/projects/${pid}/items/${itemId}/file`,

  listTasks: (pid: string) => req<TaskWithProgress[]>(`/projects/${pid}/tasks`),
  createTask: (pid: string, body: {
    name: string; presentation: Presentation;
    question: QuestionType; config: TaskConfig;
  }) => req<{ task: Task; num_units: number }>(`/projects/${pid}/tasks`,
    json("POST", body)),

  listUnits: (pid: string, tid: string) =>
    req<UnitView[]>(`/projects/${pid}/tasks/${tid}/units`),
  saveAnnotation: (pid: string, tid: string, uid: string, answer: Answer) =>
    req<{ unit_id: string; answer: Answer }>(
      `/projects/${pid}/tasks/${tid}/units/${uid}/annotation`,
      json("PUT", { answer })),

  exportTask: (pid: string, tid: string, body: {
    output_dir: string; splits: Record<string, number> | null; seed: number;
  }) => req<ExportResult>(`/projects/${pid}/tasks/${tid}/export`,
    json("POST", body)),
};
```

- [ ] **Step 5: テストと型チェック**

Run: `npm run test`
Expected: 3 PASSED

Run: `npm run build`
Expected: 型チェック込みで成功（react-ts テンプレートの build は `tsc -b && vite build`）

- [ ] **Step 6: コミット**

```bash
cd /Users/hayashinaofumi/workspace/hayashi-yaken/annotorch
git add .gitignore frontend
git commit -m "feat: frontend scaffold, API client, splits parser"
```

---

### Task 2: アノテーションUIの純ロジック（softlabel / groupstate）

**Files:**
- Create: `frontend/src/lib/softlabel.ts`
- Create: `frontend/src/lib/groupstate.ts`
- Test: `frontend/src/lib/softlabel.test.ts`, `frontend/src/lib/groupstate.test.ts`

**Interfaces:**
- Consumes: なし（純関数）
- Produces:
  - `normalizeDist(weights: Record<string, number>): Record<string, number> | null` — 正の重みを合計1に正規化。全て0以下なら null
  - `toggleInOrder(order: string[], id: string): string[]` — 順位リストへの追加/解除
  - `assignToGroup(groups: Record<string, number>, id: string, group: number): Record<string, number>`
  - `groupsToAnswer(itemIds: string[], groups: Record<string, number>): string[][] | null` — 全アイテム割当済みならグループ番号順の分割を返す。未割当があれば null

- [ ] **Step 1: 失敗するテストを書く**

`frontend/src/lib/softlabel.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { normalizeDist } from "./softlabel";

describe("normalizeDist", () => {
  it("normalizes positive weights to sum 1", () => {
    const dist = normalizeDist({ cat: 60, dog: 40 })!;
    expect(dist.cat).toBeCloseTo(0.6);
    expect(dist.dog).toBeCloseTo(0.4);
    expect(Object.values(dist).reduce((s, v) => s + v, 0)).toBeCloseTo(1);
  });
  it("drops zero-weight classes", () => {
    expect(normalizeDist({ cat: 50, dog: 0 })).toEqual({ cat: 1 });
  });
  it("returns null when everything is zero", () => {
    expect(normalizeDist({ cat: 0, dog: 0 })).toBeNull();
  });
});
```

`frontend/src/lib/groupstate.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { assignToGroup, groupsToAnswer, toggleInOrder } from "./groupstate";

describe("toggleInOrder", () => {
  it("appends unknown id and removes known id", () => {
    expect(toggleInOrder([], "a")).toEqual(["a"]);
    expect(toggleInOrder(["a", "b"], "c")).toEqual(["a", "b", "c"]);
    expect(toggleInOrder(["a", "b", "c"], "b")).toEqual(["a", "c"]);
  });
});

describe("grouping", () => {
  it("assigns and reassigns items", () => {
    let g = assignToGroup({}, "a", 0);
    g = assignToGroup(g, "a", 1);
    expect(g).toEqual({ a: 1 });
  });
  it("returns null until every item is assigned", () => {
    expect(groupsToAnswer(["a", "b"], { a: 0 })).toBeNull();
  });
  it("builds partition ordered by group number", () => {
    const groups = { a: 1, b: 0, c: 1 };
    expect(groupsToAnswer(["a", "b", "c"], groups)).toEqual([["b"], ["a", "c"]]);
  });
});
```

- [ ] **Step 2: テストを実行して失敗を確認**

Run: `npm run test`
Expected: 新規テストが FAIL

- [ ] **Step 3: 実装**

`frontend/src/lib/softlabel.ts`:

```ts
export function normalizeDist(
  weights: Record<string, number>,
): Record<string, number> | null {
  const entries = Object.entries(weights).filter(([, v]) => v > 0);
  const total = entries.reduce((sum, [, v]) => sum + v, 0);
  if (total <= 0) return null;
  return Object.fromEntries(entries.map(([k, v]) => [k, v / total]));
}
```

`frontend/src/lib/groupstate.ts`:

```ts
export function toggleInOrder(order: string[], id: string): string[] {
  return order.includes(id) ? order.filter((x) => x !== id) : [...order, id];
}

export function assignToGroup(
  groups: Record<string, number>, id: string, group: number,
): Record<string, number> {
  return { ...groups, [id]: group };
}

export function groupsToAnswer(
  itemIds: string[], groups: Record<string, number>,
): string[][] | null {
  if (!itemIds.every((id) => groups[id] !== undefined)) return null;
  const buckets = new Map<number, string[]>();
  for (const id of itemIds) {
    const g = groups[id];
    if (!buckets.has(g)) buckets.set(g, []);
    buckets.get(g)!.push(id);
  }
  return [...buckets.entries()].sort(([a], [b]) => a - b).map(([, ids]) => ids);
}
```

- [ ] **Step 4: テストを実行してパスを確認**

Run: `npm run test`
Expected: 全て PASSED

- [ ] **Step 5: コミット**

```bash
git add frontend/src/lib
git commit -m "feat: annotation UI pure logic (soft label normalize, ranking/grouping state)"
```

---

### Task 3: 共通UI（CSS / ItemView / ProjectsPage）

**Files:**
- Modify: `frontend/src/index.css`（全置換）
- Create: `frontend/src/components/ItemView.tsx`
- Create: `frontend/src/pages/ProjectsPage.tsx`

**Interfaces:**
- Consumes: `api`, `Project`, `Item`
- Produces:
  - `<ItemView projectId item size?>` — image は `<img>`（`size="large"` で拡大）、text は本文表示
  - `<ProjectsPage onOpen={(p: Project) => void}>` — 一覧・作成・削除

- [ ] **Step 1: 実装**

`frontend/src/index.css`（全置換）:

```css
* { box-sizing: border-box; }
body { margin: 0; font-family: system-ui, sans-serif; color: #222; background: #fff; }
.container { max-width: 960px; margin: 0 auto; padding: 16px; }
h1 { font-size: 1.4rem; }
h2 { font-size: 1.1rem; margin-top: 24px; }
button { cursor: pointer; padding: 6px 12px; }
input, select { padding: 6px; }
.row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin: 8px 0; }
.card { border: 1px solid #ddd; border-radius: 8px; padding: 12px; margin: 8px 0; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 8px; }
.item-thumb { width: 100%; height: 100px; object-fit: contain; background: #f5f5f5; }
.progress { height: 8px; background: #eee; border-radius: 4px; overflow: hidden; }
.progress > div { height: 100%; background: #4a7; }
.selected { outline: 3px solid #4a7; }
.clickable { cursor: pointer; }
.error { color: #c33; }
.big { font-size: 1.05rem; padding: 12px 20px; }
pre { background: #f5f5f5; padding: 8px; overflow-x: auto; }
```

`frontend/src/components/ItemView.tsx`:

```tsx
import { api, Item } from "../api";

export default function ItemView({ projectId, item, size }: {
  projectId: string; item: Item; size?: "large";
}) {
  if (item.modality === "image") {
    return (
      <img
        className="item-thumb"
        style={size === "large" ? { height: 260 } : undefined}
        src={api.itemFileUrl(projectId, item.id)}
        alt={item.id}
      />
    );
  }
  return (
    <div className="card" style={size === "large" ? { fontSize: "1.15rem" } : undefined}>
      {item.text}
    </div>
  );
}
```

`frontend/src/pages/ProjectsPage.tsx`:

```tsx
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
```

- [ ] **Step 2: 型チェック**

Run: `npm run build`
Expected: 型チェック込みで成功（App.tsx はまだ scaffold のままで良い）

- [ ] **Step 3: コミット**

```bash
git add frontend/src
git commit -m "feat: base styles, ItemView, projects page"
```

---

### Task 4: インポート / タスク作成 / エクスポートのパネル

**Files:**
- Create: `frontend/src/components/ImportPanel.tsx`
- Create: `frontend/src/components/TaskForm.tsx`
- Create: `frontend/src/components/ExportPanel.tsx`

**Interfaces:**
- Consumes: `api`, `parseSplits`
- Produces:
  - `<ImportPanel projectId onImported>` — 画像複数アップロード（ファイル選択 + ドラッグ&ドロップ）、JSONL/CSVアップロード、フォルダパス取り込み。結果レポート表示
  - `<TaskForm projectId numItems onCreated>` — presentation × question 選択と質問別設定フォーム
  - `<ExportPanel projectId task onClose>` — 出力先・splits・seed を指定して実行、結果と読み込みサンプルコード表示

- [ ] **Step 1: 実装**

`frontend/src/components/ImportPanel.tsx`:

```tsx
import { useRef, useState } from "react";
import { api, ImportReport } from "../api";

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
```

`frontend/src/components/TaskForm.tsx`:

```tsx
import { useState } from "react";
import { api, Presentation, QuestionType, TaskConfig } from "../api";

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
```

`frontend/src/components/ExportPanel.tsx`:

```tsx
import { useState } from "react";
import { api, ExportResult, Task } from "../api";
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
```

- [ ] **Step 2: 型チェック**

Run: `npm run build`
Expected: 型チェック込みで成功（react-ts テンプレートの build は `tsc -b && vite build`）

- [ ] **Step 3: コミット**

```bash
git add frontend/src/components
git commit -m "feat: import/task-form/export panels"
```

---

### Task 5: 回答エディタ6種

**Files:**
- Create: `frontend/src/components/answer/types.ts`
- Create: `frontend/src/components/answer/HardLabel.tsx`
- Create: `frontend/src/components/answer/SoftLabel.tsx`
- Create: `frontend/src/components/answer/Preference.tsx`
- Create: `frontend/src/components/answer/Similarity.tsx`
- Create: `frontend/src/components/answer/Ranking.tsx`
- Create: `frontend/src/components/answer/Grouping.tsx`

**Interfaces:**
- Consumes: `ItemView`、`normalizeDist` / `toggleInOrder` / `assignToGroup` / `groupsToAnswer`（Task 2）
- Produces: 各エディタは共通 props `EditorProps { projectId, task, unit, onSave(answer) }` を受け、質問タイプに応じた回答 JSON（計画1のスキーマと同形）を `onSave` に渡す:
  - hard_label: `{label}`（数字キー1〜9対応）
  - soft_label: `{dist}`（スライダー + 正規化）
  - preference: `{winner: 1 | -1 | 0 | null}`（← → = スペース）
  - similarity: `{score}` または `{same}`（Task設定に従う）
  - ranking: `{order}`（クリックで順位付け）
  - grouping: `{groups}`（グループ選択 → アイテムクリックで振り分け）

- [ ] **Step 1: 実装**

`frontend/src/components/answer/types.ts`:

```ts
import { Answer, Task, UnitView } from "../../api";

export interface EditorProps {
  projectId: string;
  task: Task;
  unit: UnitView;
  onSave: (answer: Answer) => void;
}
```

`frontend/src/components/answer/HardLabel.tsx`:

```tsx
import { useEffect } from "react";
import ItemView from "../ItemView";
import { EditorProps } from "./types";

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
```

`frontend/src/components/answer/SoftLabel.tsx`:

```tsx
import { useState } from "react";
import { normalizeDist } from "../../lib/softlabel";
import ItemView from "../ItemView";
import { EditorProps } from "./types";

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
```

`frontend/src/components/answer/Preference.tsx`:

```tsx
import { useEffect } from "react";
import ItemView from "../ItemView";
import { EditorProps } from "./types";

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
```

（winner の値は保存層と同じ規約: 1 = 1番目のアイテム = 左、-1 = 2番目 = 右、0 = tie、null = skip）

`frontend/src/components/answer/Similarity.tsx`:

```tsx
import { useState } from "react";
import ItemView from "../ItemView";
import { EditorProps } from "./types";

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
```

`frontend/src/components/answer/Ranking.tsx`:

```tsx
import { useState } from "react";
import { toggleInOrder } from "../../lib/groupstate";
import ItemView from "../ItemView";
import { EditorProps } from "./types";

export default function Ranking({ projectId, unit, onSave }: EditorProps) {
  const [order, setOrder] = useState<string[]>(
    (unit.answer?.order as string[] | undefined) ?? [],
  );
  return (
    <div>
      <p>良い順にクリックして順位をつける（もう一度クリックで解除）</p>
      <div className="grid">
        {unit.items.map((item) => {
          const rank = order.indexOf(item.id);
          return (
            <div key={item.id} className={`clickable ${rank >= 0 ? "selected" : ""}`}
                 onClick={() => setOrder(toggleInOrder(order, item.id))}>
              <ItemView projectId={projectId} item={item} />
              <div>{rank >= 0 ? `${rank + 1} 位` : "未選択"}</div>
            </div>
          );
        })}
      </div>
      <div className="row">
        <button className="big" disabled={order.length !== unit.items.length}
                onClick={() => onSave({ order })}>
          保存して次へ
        </button>
        <button onClick={() => setOrder([])}>リセット</button>
      </div>
    </div>
  );
}
```

`frontend/src/components/answer/Grouping.tsx`:

```tsx
import { useState } from "react";
import { assignToGroup, groupsToAnswer } from "../../lib/groupstate";
import ItemView from "../ItemView";
import { EditorProps } from "./types";

const COLORS = ["#4a7", "#47a", "#a47", "#a74", "#7a4", "#74a"];

export default function Grouping({ projectId, unit, onSave }: EditorProps) {
  const [numGroups, setNumGroups] = useState(2);
  const [active, setActive] = useState(0);
  const [assignment, setAssignment] = useState<Record<string, number>>({});
  const answer = groupsToAnswer(unit.items.map((i) => i.id), assignment);

  return (
    <div>
      <p>グループを選んでからアイテムをクリックして振り分ける</p>
      <div className="row">
        {Array.from({ length: numGroups }, (_, g) => (
          <button key={g}
                  style={{
                    border: `${active === g ? 3 : 1}px solid ${COLORS[g % COLORS.length]}`,
                  }}
                  onClick={() => setActive(g)}>
            グループ {g + 1}
          </button>
        ))}
        <button onClick={() => setNumGroups(numGroups + 1)}>＋ グループ追加</button>
      </div>
      <div className="grid">
        {unit.items.map((item) => {
          const g = assignment[item.id];
          return (
            <div key={item.id} className="clickable"
                 style={g !== undefined
                   ? { outline: `3px solid ${COLORS[g % COLORS.length]}` }
                   : undefined}
                 onClick={() => setAssignment(assignToGroup(assignment, item.id, active))}>
              <ItemView projectId={projectId} item={item} />
              <div>{g !== undefined ? `グループ ${g + 1}` : "未割当"}</div>
            </div>
          );
        })}
      </div>
      <div className="row">
        <button className="big" disabled={!answer}
                onClick={() => answer && onSave({ groups: answer })}>
          保存して次へ
        </button>
        <button onClick={() => setAssignment({})}>リセット</button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: 型チェック**

Run: `npm run build`
Expected: 型チェック込みで成功（react-ts テンプレートの build は `tsc -b && vite build`）

- [ ] **Step 3: コミット**

```bash
git add frontend/src/components/answer
git commit -m "feat: answer editors for all six question types"
```

---

### Task 6: ページ組み立て（ProjectPage / AnnotatePage / App）

**Files:**
- Create: `frontend/src/pages/ProjectPage.tsx`
- Create: `frontend/src/pages/AnnotatePage.tsx`
- Modify: `frontend/src/App.tsx`（全置換）
- Modify: `frontend/src/main.tsx`（全置換）
- Delete: `frontend/src/App.css`, `frontend/src/assets/`（scaffold の残骸）

**Interfaces:**
- Consumes: これまでの全コンポーネント
- Produces: `App` — `projects → project → annotate` の3画面遷移。アノテーション画面は最初の未回答Unitから開始し、保存で自動的に次へ進む

- [ ] **Step 1: 実装**

`frontend/src/pages/ProjectPage.tsx`:

```tsx
import { useCallback, useEffect, useState } from "react";
import { api, Item, Project, Task, TaskWithProgress } from "../api";
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

  const refresh = useCallback(() => {
    api.listItems(project.id).then(setItems);
    api.listTasks(project.id).then(setTasks);
  }, [project.id]);
  useEffect(() => { refresh(); }, [refresh]);

  return (
    <div className="container">
      <div className="row">
        <button onClick={onBack}>← プロジェクト一覧</button>
        <h1>{project.name}</h1>
      </div>

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
```

`frontend/src/pages/AnnotatePage.tsx`:

```tsx
import { useCallback, useEffect, useState } from "react";
import { Answer, api, Project, Task, UnitView } from "../api";
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
```

（`key={unit.id}` が重要: Unit が切り替わるたびにエディタ内部の state をリセットする）

`frontend/src/App.tsx`（全置換）:

```tsx
import { useState } from "react";
import { Project, Task } from "./api";
import AnnotatePage from "./pages/AnnotatePage";
import ProjectPage from "./pages/ProjectPage";
import ProjectsPage from "./pages/ProjectsPage";

type View =
  | { page: "projects" }
  | { page: "project"; project: Project }
  | { page: "annotate"; project: Project; task: Task };

export default function App() {
  const [view, setView] = useState<View>({ page: "projects" });

  if (view.page === "projects") {
    return <ProjectsPage onOpen={(project) => setView({ page: "project", project })} />;
  }
  if (view.page === "project") {
    return (
      <ProjectPage
        project={view.project}
        onBack={() => setView({ page: "projects" })}
        onAnnotate={(task) =>
          setView({ page: "annotate", project: view.project, task })}
      />
    );
  }
  return (
    <AnnotatePage
      project={view.project}
      task={view.task}
      onBack={() => setView({ page: "project", project: view.project })}
    />
  );
}
```

`frontend/src/main.tsx`（全置換）:

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
```

scaffold の残骸を削除:

```bash
rm -f frontend/src/App.css
rm -rf frontend/src/assets
```

- [ ] **Step 2: ビルドで型チェック込みの検証**

Run: `npm run build`
Expected: 成功し、`src/annotorch/server/static/index.html` が生成される

- [ ] **Step 3: 手動E2E確認（開発モード）**

ターミナル1: `uv run annotorch serve --root /tmp/annotorch-dev --no-browser`
ターミナル2: `cd frontend && npm run dev`

ブラウザ（または Playwright MCP）で `http://localhost:5173` を開き、以下を一巡:

1. プロジェクト作成 → 開く
2. 画像を数枚アップロード（`/tmp` に PIL で適当な PNG を作っておく）
3. hard_label タスク作成 → アノテーション（数字キーで回答が進むこと）
4. pair/preference タスク作成 → ←/→/=/スペースで回答
5. group/ranking と group/grouping をクリック操作で回答
6. soft_label のスライダー → 保存
7. エクスポート実行 → 出力パスとサンプルコードが表示される

Expected: 全操作がエラー表示なしで完了し、進捗バーが更新される

- [ ] **Step 4: コミット**

```bash
git add frontend
git commit -m "feat: assemble pages and app shell"
```

---

### Task 7: ビルド統合（静的配信・Docker・README）

**Files:**
- Modify: `Dockerfile`（node ビルドステージ追加）
- Modify: `README.md`（クイックスタート記載。現状は空ファイル)

**Interfaces:**
- Consumes: `npm run build` の成果物、計画2の compose 設定
- Produces: `docker compose up --build` だけで UI 込みのサーバーが立つ。README に利用手順

- [ ] **Step 1: FastAPI からの静的配信を確認**

```bash
cd frontend && npm run build && cd ..
uv run annotorch serve --root /tmp/annotorch-dev --no-browser &
sleep 2
curl -s http://127.0.0.1:8000/ | head -c 200
kill %1
```

Expected: ビルドされた `index.html` の中身が返る（`<!doctype html>` で始まる）

- [ ] **Step 2: Dockerfile をマルチステージに更新**

`Dockerfile`（全置換）:

```dockerfile
FROM node:22-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build
# 成果物は /app/src/annotorch/server/static に出る（vite の outDir 設定）

FROM python:3.13-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
COPY --from=frontend /app/src/annotorch/server/static ./src/annotorch/server/static
RUN pip install --no-cache-dir ".[server]"
EXPOSE 8000
CMD ["annotorch", "serve", "--root", "/data", "--host", "0.0.0.0", "--port", "8000", "--no-browser"]
```

- [ ] **Step 3: Docker で UI 込みの動作確認**

```bash
docker compose up --build -d
sleep 3
curl -s http://localhost:8000/ | head -c 200
curl -s http://localhost:8000/api/health
docker compose down
```

Expected: `/` が HTML を返し、`/api/health` が ok を返す。ブラウザで `http://localhost:8000` を開いて一巡確認

- [ ] **Step 4: README を書く**

`README.md`（全置換）:

```markdown
# annotorch

画像・テキストにブラウザ上でアノテーション（ハードラベル / ソフトラベル /
ペアワイズ選好・類似性 / グループ順位付け・グルーピング）を行い、
PyTorch の `DataLoader` でそのまま読めるデータセットを作るローカルツール。

## 起動（Docker）

```bash
docker compose up --build
# → http://localhost:8000 をブラウザで開く
```

作業データは volume `annotorch-data` に永続化される。
フォルダ取り込みを使う場合はホストの `./import` に画像を置き、
UI で `/import` を指定する。

## 起動（Docker なし・開発用）

```bash
uv sync --extra server
cd frontend && npm install && npm run build && cd ..
uv run annotorch serve
```

## 作ったデータセットを使う

```bash
pip install -e .   # 学習環境に（server extra は不要）
```

```python
from torch.utils.data import DataLoader
from annotorch.datasets import load

ds = load("path/to/exported-dataset", split="train", transform=my_transform)
loader = DataLoader(ds, batch_size=32, shuffle=True)
```

質問タイプごとの `ds[i]` の形式や preference の符号規約
（1 = 1番目の勝ち, -1 = 2番目, 0 = tie）は
`docs/superpowers/specs/2026-08-12-annotorch-design.md` を参照。

## 開発

```bash
uv run pytest tests/ -v          # バックエンド
cd frontend && npm run test      # フロントのロジックテスト
```
```

- [ ] **Step 5: コミット**

```bash
git add Dockerfile README.md
git commit -m "feat: multi-stage Docker build with frontend, README quickstart"
```

---

## 計画3の完了条件

- `npm run test` / `npx tsc --noEmit` / `npm run build` が全て成功
- `docker compose up --build` で UI 込みのサーバーが立ち、ブラウザから
  「プロジェクト作成 → インポート → 6方式すべてのアノテーション → エクスポート」が一巡できる
- エクスポートしたデータセットが `annotorch.datasets.load()` で読める（計画1・2のテストで担保済み）
