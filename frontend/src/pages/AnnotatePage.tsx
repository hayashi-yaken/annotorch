import { useCallback, useEffect, useState } from "react";
import { Button, HStack, Progress, Text } from "@chakra-ui/react";
import { api } from "../api";
import type { Answer, Project, Task, UnitView } from "../api";
import Layout from "../components/Layout";
import { toaster } from "../lib/toaster";
import { message } from "../lib/errors";
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
    }).catch((e) => setError(String(e)));
  }, [project.id, task.id]);

  const save = useCallback(async (answer: Answer) => {
    if (!units) return;
    const unit = units[index];
    try {
      await api.saveAnnotation(project.id, task.id, unit.id, answer);
      setUnits(units.map((u, n) => (n === index ? { ...u, answer } : u)));
      if (index < units.length - 1) setIndex(index + 1);
    } catch (e) {
      toaster.error({ title: "回答を保存できませんでした", description: message(e) });
    }
  }, [units, index, project.id, task.id]);

  if (!units) {
    return (
      <Layout title={task.name}>
        {error ? (
          <>
            <Button alignSelf="flex-start" variant="outline" onClick={onBack}>← 戻る</Button>
            <Text color="red.500">{error}</Text>
          </>
        ) : (
          <Text>読み込み中…</Text>
        )}
      </Layout>
    );
  }
  if (units.length === 0) {
    return (
      <Layout title={task.name}>
        <Button alignSelf="flex-start" variant="outline" onClick={onBack}>← 戻る</Button>
        <Text>Unit がありません</Text>
      </Layout>
    );
  }

  const unit = units[index];
  const answered = units.filter((u) => u.answer !== null).length;
  const editorProps = { projectId: project.id, task, unit, onSave: save };

  return (
    <Layout title={task.name}>
      <HStack justify="space-between" wrap="wrap" gap={3}>
        <Button variant="outline" onClick={onBack}>← 戻る</Button>
        <HStack gap={3}>
          <Text color="fg.muted">{index + 1} / {units.length}（回答済み {answered}）</Text>
          <Button size="sm" onClick={() => setIndex(Math.max(0, index - 1))}>前へ</Button>
          <Button size="sm" onClick={() => setIndex(Math.min(units.length - 1, index + 1))}>
            次へ
          </Button>
        </HStack>
      </HStack>
      <Progress.Root value={(100 * answered) / units.length}>
        <Progress.Track>
          <Progress.Range />
        </Progress.Track>
      </Progress.Root>
      {error && <Text color="red.500">{error}</Text>}
      {task.question === "hard_label" && <HardLabel key={unit.id} {...editorProps} />}
      {task.question === "soft_label" && <SoftLabel key={unit.id} {...editorProps} />}
      {task.question === "preference" && <Preference key={unit.id} {...editorProps} />}
      {task.question === "similarity" && <Similarity key={unit.id} {...editorProps} />}
      {task.question === "ranking" && <Ranking key={unit.id} {...editorProps} />}
      {task.question === "grouping" && <Grouping key={unit.id} {...editorProps} />}
    </Layout>
  );
}
