import type { Answer, Task, UnitView } from "../../api";

export interface EditorProps {
  projectId: string;
  task: Task;
  unit: UnitView;
  onSave: (answer: Answer) => void;
}
