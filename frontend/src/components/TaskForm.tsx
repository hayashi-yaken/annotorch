import { useState } from "react";
import {
  Button, Card, Field, HStack, Input, NativeSelect, NumberInput, Stack, Text,
} from "@chakra-ui/react";
import { api } from "../api";
import type { Presentation, QuestionType, TaskConfig } from "../api";

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
    <Card.Root>
      <Card.Body>
        <Stack gap={5}>
          <HStack wrap="wrap" gap={3}>
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="タスク名"
              maxW="14rem"
            />
            <NativeSelect.Root width="12rem">
              <NativeSelect.Field
                value={presentation}
                onChange={(e) => {
                  const p = e.target.value as Presentation;
                  setPresentation(p);
                  setQuestion(QUESTIONS[p][0]);
                }}
              >
                <option value="single">single（1枚ずつ）</option>
                <option value="pair">pair（2枚比較）</option>
                <option value="group">group（複数まとめて）</option>
              </NativeSelect.Field>
              <NativeSelect.Indicator />
            </NativeSelect.Root>
            <NativeSelect.Root width="10rem">
              <NativeSelect.Field
                value={question}
                onChange={(e) => setQuestion(e.target.value as QuestionType)}
              >
                {QUESTIONS[presentation].map((q) => (
                  <option key={q} value={q}>{q}</option>
                ))}
              </NativeSelect.Field>
              <NativeSelect.Indicator />
            </NativeSelect.Root>
          </HStack>

          <HStack wrap="wrap" gap={4} align="flex-end">
            {needsLabels && (
              <Field.Root width="16rem">
                <Field.Label>ラベル（カンマ区切り）</Field.Label>
                <Input value={labels} onChange={(e) => setLabels(e.target.value)} />
              </Field.Root>
            )}
            {question === "similarity" && (
              <Field.Root width="12rem">
                <Field.Label>類似度モード</Field.Label>
                <NativeSelect.Root>
                  <NativeSelect.Field
                    value={similarityMode}
                    onChange={(e) =>
                      setSimilarityMode(e.target.value as "binary" | "continuous")}
                  >
                    <option value="continuous">連続値（0〜1）</option>
                    <option value="binary">二値（同じ/違う）</option>
                  </NativeSelect.Field>
                  <NativeSelect.Indicator />
                </NativeSelect.Root>
              </Field.Root>
            )}
            {presentation !== "single" && (
              <Field.Root width="6rem">
                <Field.Label>Unit数</Field.Label>
                <NumberInput.Root
                  min={1}
                  value={String(numUnits)}
                  onValueChange={(d) =>
                    setNumUnits(Number.isNaN(d.valueAsNumber) ? 0 : d.valueAsNumber)}
                >
                  <NumberInput.Control />
                  <NumberInput.Input />
                </NumberInput.Root>
              </Field.Root>
            )}
            {presentation === "group" && (
              <Field.Root width="6rem">
                <Field.Label>グループサイズ</Field.Label>
                <NumberInput.Root
                  min={2}
                  value={String(groupSize)}
                  onValueChange={(d) =>
                    setGroupSize(Number.isNaN(d.valueAsNumber) ? 0 : d.valueAsNumber)}
                >
                  <NumberInput.Control />
                  <NumberInput.Input />
                </NumberInput.Root>
              </Field.Root>
            )}
            <Field.Root width="6rem">
              <Field.Label>seed</Field.Label>
              <NumberInput.Root
                value={String(seed)}
                onValueChange={(d) =>
                  setSeed(Number.isNaN(d.valueAsNumber) ? 0 : d.valueAsNumber)}
              >
                <NumberInput.Control />
                <NumberInput.Input />
              </NumberInput.Root>
            </Field.Root>
            <Button onClick={create} disabled={numItems === 0}>タスク作成</Button>
            {numItems === 0 && (
              <Text fontSize="sm" color="gray.500">（先にアイテムを取り込んでね）</Text>
            )}
          </HStack>

          {error && <Text color="red.500">{error}</Text>}
        </Stack>
      </Card.Body>
    </Card.Root>
  );
}
