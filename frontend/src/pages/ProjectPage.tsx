import { useCallback, useEffect, useState } from "react";
import { Button, Card, Heading, HStack, Progress, SimpleGrid, Stack, Text } from "@chakra-ui/react";
import { api } from "../api";
import type { Item, Project, Task, TaskWithProgress } from "../api";
import ConfirmDialog from "../components/ConfirmDialog";
import ExportPanel from "../components/ExportPanel";
import ImportPanel from "../components/ImportPanel";
import ItemView from "../components/ItemView";
import Layout from "../components/Layout";
import TaskForm from "../components/TaskForm";

export default function ProjectPage({ project, onBack, onAnnotate }: {
  project: Project;
  onBack: () => void;
  onAnnotate: (task: Task) => void;
}) {
  const [items, setItems] = useState<Item[]>([]);
  const [tasks, setTasks] = useState<TaskWithProgress[]>([]);
  const [exportTask, setExportTask] = useState<Task | null>(null);
  const [deleteTask, setDeleteTask] = useState<TaskWithProgress | null>(null);
  const [error, setError] = useState("");

  const refresh = useCallback(() => {
    api.listItems(project.id).then(setItems).catch((e) => setError(String(e)));
    api.listTasks(project.id).then(setTasks).catch((e) => setError(String(e)));
  }, [project.id]);
  useEffect(() => { refresh(); }, [refresh]);

  const removeTask = async (t: TaskWithProgress) => {
    setDeleteTask(null);
    try {
      await api.deleteTask(project.id, t.id);
      if (exportTask?.id === t.id) setExportTask(null);
      refresh();
    } catch (e) { setError(String(e)); }
  };

  return (
    <Layout title={project.name}>
      <Button alignSelf="flex-start" variant="outline" onClick={onBack}>
        ← プロジェクト一覧
      </Button>
      {error && <Text color="red.500">{error}</Text>}

      <Stack gap={3}>
        <Heading size="md">アイテム（{items.length}件）</Heading>
        <ImportPanel projectId={project.id} onImported={refresh} />
        <SimpleGrid columns={{ base: 2, sm: 3, md: 5 }} gap={3}>
          {items.slice(0, 50).map((item) => (
            <ItemView key={item.id} projectId={project.id} item={item} />
          ))}
        </SimpleGrid>
        {items.length > 50 && <Text color="gray.500">…他 {items.length - 50} 件</Text>}
      </Stack>

      <Stack gap={3}>
        <Heading size="md">タスク</Heading>
        <TaskForm projectId={project.id} items={items} onCreated={refresh} />
        {tasks.map((t) => (
          <Card.Root key={t.id}>
            <Card.Body>
              <Stack gap={2}>
                <HStack wrap="wrap" gap={3}>
                  <Text fontWeight="bold">{t.name}</Text>
                  <Text color="gray.500">{t.presentation}/{t.question}</Text>
                  <Text color="gray.500">{t.answered_units}/{t.total_units} 回答済み</Text>
                  <Button size="sm" onClick={() => onAnnotate(t)}>アノテーション</Button>
                  <Button size="sm" variant="outline" onClick={() => setExportTask(t)}>
                    エクスポート
                  </Button>
                  <Button size="sm" variant="outline" colorPalette="red"
                          onClick={() => setDeleteTask(t)}>
                    削除
                  </Button>
                </HStack>
                <Progress.Root
                  value={t.total_units ? (100 * t.answered_units) / t.total_units : 0}
                >
                  <Progress.Track>
                    <Progress.Range />
                  </Progress.Track>
                </Progress.Root>
              </Stack>
            </Card.Body>
          </Card.Root>
        ))}
      </Stack>

      {exportTask && (
        <ExportPanel projectId={project.id} task={exportTask}
                     onClose={() => setExportTask(null)} />
      )}

      <ConfirmDialog
        open={deleteTask !== null}
        title="タスクを削除"
        message={deleteTask
          ? `タスク「${deleteTask.name}」を削除します。\n`
            + `回答 ${deleteTask.answered_units} 件も一緒に削除され、元に戻せません。`
          : ""}
        onConfirm={() => deleteTask && removeTask(deleteTask)}
        onCancel={() => setDeleteTask(null)}
      />
    </Layout>
  );
}
