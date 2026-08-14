import { useEffect } from "react";
import { Button, SimpleGrid, Stack, Wrap } from "@chakra-ui/react";
import ItemView from "../ItemView";
import type { EditorProps } from "./types";

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
    <Stack gap={4}>
      <SimpleGrid columns={2} gap={4}>
        <ItemView projectId={projectId} item={a} size="large" />
        <ItemView projectId={projectId} item={b} size="large" />
      </SimpleGrid>
      <Wrap gap={2}>
        <Button size="lg" colorPalette="blue" onClick={() => onSave({ winner: 1 })}>← 左が良い</Button>
        <Button size="lg" colorPalette="blue" variant="outline" onClick={() => onSave({ winner: 0 })}>= 引き分け</Button>
        <Button size="lg" colorPalette="blue" onClick={() => onSave({ winner: -1 })}>右が良い →</Button>
        <Button variant="ghost" onClick={() => onSave({ winner: null })}>スキップ（スペース）</Button>
      </Wrap>
    </Stack>
  );
}
