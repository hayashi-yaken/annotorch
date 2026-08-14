import { useState } from "react";
import {
  Box, Button, Card, Code, Field, HStack, Input, NumberInput, Stack, Text,
} from "@chakra-ui/react";
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
    <Card.Root>
      <Card.Body>
        <Stack gap={5}>
          <Text fontWeight="bold">エクスポート: {task.name}</Text>

          <HStack wrap="wrap" gap={4} align="flex-end">
            <Field.Root width="20rem">
              <Field.Label>出力先ディレクトリ</Field.Label>
              <Input
                value={outputDir}
                onChange={(e) => setOutputDir(e.target.value)}
                placeholder="出力先ディレクトリ（Docker では /data/exports/... 推奨）"
              />
            </Field.Root>
            <Field.Root width="16rem">
              <Field.Label>splits</Field.Label>
              <Input
                value={splits}
                onChange={(e) => setSplits(e.target.value)}
                placeholder="train=0.8,test=0.2（空なら全train）"
              />
            </Field.Root>
            <Field.Root width="6rem">
              <Field.Label>seed</Field.Label>
              <NumberInput.Root
                value={String(seed)}
                onValueChange={(d) => setSeed(d.valueAsNumber)}
              >
                <NumberInput.Input />
              </NumberInput.Root>
            </Field.Root>
            <Button onClick={run} disabled={!outputDir.trim()}>データセット作成</Button>
            <Button variant="outline" onClick={onClose}>閉じる</Button>
          </HStack>

          {error && <Text color="red.500">{error}</Text>}

          {result && (
            <Box>
              <Text>
                {result.num_rows} 件を {result.output_dir} に出力した
                {result.num_unanswered_units > 0 &&
                  `（未回答 ${result.num_unanswered_units} Unit は除外）`}
                {result.num_skipped > 0 && `（スキップ ${result.num_skipped} 件は除外）`}
              </Text>
              <Code display="block" whiteSpace="pre" p={3} mt={2} borderRadius="md">
                {`from annotorch.datasets import load
ds = load(${JSON.stringify(result.output_dir)}, split="train")`}
              </Code>
            </Box>
          )}
        </Stack>
      </Card.Body>
    </Card.Root>
  );
}
