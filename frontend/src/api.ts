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
  pairing?: "random" | "anchor";
  anchor_item_ids?: string[];
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
  deleteItems: (pid: string, itemIds: string[]) =>
    req<{ deleted: number }>(`/projects/${pid}/items`,
      json("DELETE", { item_ids: itemIds })),
  itemFileUrl: (pid: string, itemId: string) =>
    `${BASE}/projects/${pid}/items/${itemId}/file`,

  listTasks: (pid: string) => req<TaskWithProgress[]>(`/projects/${pid}/tasks`),
  createTask: (pid: string, body: {
    name: string; presentation: Presentation;
    question: QuestionType; config: TaskConfig;
  }) => req<{ task: Task; num_units: number }>(`/projects/${pid}/tasks`,
    json("POST", body)),
  deleteTask: (pid: string, tid: string) =>
    req<{ ok: boolean }>(`/projects/${pid}/tasks/${tid}`, { method: "DELETE" }),

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
