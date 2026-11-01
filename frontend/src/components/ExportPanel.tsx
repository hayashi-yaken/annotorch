import { useState } from "react";
import {
  Box, Button, Card, Code, Field, HStack, Input, NumberInput, Stack, Text,
} from "@chakra-ui/react";
import { api } from "../api";
import type { ExportResult, Task } from "../api";
import { defaultDatasetName } from "../lib/datasetName";
import { message } from "../lib/errors";
import { parseSplits } from "../lib/splits";
import { toaster } from "../lib/toaster";
import { useAsync } from "../lib/useAsync";

export default function ExportPanel({ projectId, task, onClose }: {
  projectId: string; task: Task; onClose: () => void;
}) {
  const [name, setName] = useState(() => defaultDatasetName(task.name, new Date()));
  const [splits, setSplits] = useState("");
  const [seed, setSeed] = useState(0);
  const [result, setResult] = useState<ExportResult | null>(null);

  const request = () => ({
    name: name.trim(), splits: splits.trim() ? parseSplits(splits) : null, seed,
  });

  const createDataset = useAsync(async () => {
    try {
      const exported = await api.exportTask(projectId, task.id, request());
      setResult(exported);
      setName(defaultDatasetName(task.name, new Date()));
      toaster.success({
        title: `${exported.num_rows} 件をエクスポートしました`,
        description: exported.output_dir,
      });
    } catch (e) {
      toaster.error({ title: "エクスポートに失敗しました", description: message(e) });
    }
  });

  return (
    <Card.Root>
      <Card.Body>
        <Stack gap={5}>
          <Text fontWeight="bold">エクスポート: {task.name}</Text>

          <HStack wrap="wrap" gap={4} align="flex-end">
            <Field.Root width="20rem">
              <Field.Label>データセット名</Field.Label>
              <Input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="フォルダ名（/ を含めない）"
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
                onValueChange={(d) => setSeed(Number.isNaN(d.valueAsNumber) ? 0 : d.valueAsNumber)}
              >
                <NumberInput.Control />
                <NumberInput.Input />
              </NumberInput.Root>
            </Field.Root>
            <Button
              onClick={() => createDataset.run()}
              loading={createDataset.pending}
              loadingText="作成中…"
              disabled={!name.trim()}
            >
              エクスポート先に保存
            </Button>
            <Button variant="outline" disabled={createDataset.pending} onClick={onClose}>閉じる</Button>
          </HStack>

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
