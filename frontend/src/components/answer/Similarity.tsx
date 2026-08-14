import { useState } from "react";
import { Button, HStack, SimpleGrid, Slider, Stack, Text } from "@chakra-ui/react";
import ItemView from "../ItemView";
import type { EditorProps } from "./types";

export default function Similarity({ projectId, task, unit, onSave }: EditorProps) {
  const [score, setScore] = useState<number>(
    (unit.answer?.score as number | undefined) ?? 0.5,
  );
  const [a, b] = unit.items;
  return (
    <Stack gap={4}>
      <SimpleGrid columns={2} gap={4}>
        <ItemView projectId={projectId} item={a} size="large" />
        <ItemView projectId={projectId} item={b} size="large" />
      </SimpleGrid>
      {task.config.similarity_mode === "binary" ? (
        <HStack gap={2}>
          <Button size="lg" colorPalette="blue" onClick={() => onSave({ same: true })}>同じ</Button>
          <Button size="lg" colorPalette="blue" onClick={() => onSave({ same: false })}>違う</Button>
        </HStack>
      ) : (
        <HStack gap={3}>
          <Slider.Root min={0} max={100}
                       value={[score * 100]}
                       onValueChange={(e) => setScore(e.value[0] / 100)}
                       flex="1"
                       display="flex" flexDirection="row" alignItems="center" gap={3}>
            <Slider.Label flexShrink={0}>似ていない</Slider.Label>
            <Slider.Control flex="1">
              <Slider.Track>
                <Slider.Range />
              </Slider.Track>
              <Slider.Thumb index={0}>
                <Slider.HiddenInput />
              </Slider.Thumb>
            </Slider.Control>
            <Text flexShrink={0} fontVariantNumeric="tabular-nums">
              似ている（{score.toFixed(2)}）
            </Text>
          </Slider.Root>
          <Button size="lg" colorPalette="blue" onClick={() => onSave({ score })}>保存して次へ</Button>
        </HStack>
      )}
    </Stack>
  );
}
