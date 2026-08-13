import { useState } from "react";
import type { Project, Task } from "./api";
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
