import { useEffect } from "react";
import { Button, Stack, Wrap } from "@chakra-ui/react";
import ItemView from "../ItemView";
import type { EditorProps } from "./types";

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
    <Stack gap={4}>
      <ItemView projectId={projectId} item={unit.items[0]} size="large" />
      <Wrap gap={2}>
        {labels.map((label, n) => (
          <Button key={label}
                  size="lg"
                  colorPalette="blue"
                  variant={current === label ? "solid" : "outline"}
                  onClick={() => onSave({ label })}>
            {n + 1}. {label}
          </Button>
        ))}
      </Wrap>
    </Stack>
  );
}
