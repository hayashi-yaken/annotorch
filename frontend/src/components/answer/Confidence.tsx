import { useState } from "react";
import { Button, HStack, NumberInput, Slider, Stack } from "@chakra-ui/react";
import ItemView from "../ItemView";
import type { EditorProps } from "./types";

export default function Confidence({ projectId, unit, onSave }: EditorProps) {
  const initial = (unit.answer?.score as number | null | undefined) ?? 0.5;
  const [score, setScore] = useState<number>(initial);
  // 入力中の文字列は整形せずそのまま保持する。毎キーストロークで score から
  // 作り直すと "0." が "0.00" に書き換わって小数が打てない。
  const [text, setText] = useState<string>(initial.toFixed(2));

  const commit = (value: number) => {
    setScore(value);
    setText(value.toFixed(2));
  };

  return (
    <Stack gap={4}>
      <ItemView projectId={projectId} item={unit.items[0]} size="large" />
      <HStack gap={3}>
        <Slider.Root
          min={0} max={100}
          value={[score * 100]}
          onValueChange={(e) => commit(e.value[0] / 100)}
          flex="1"
          display="flex" flexDirection="row" alignItems="center" gap={3}
        >
          <Slider.Label flexShrink={0}>低い</Slider.Label>
          <Slider.Control flex="1">
            <Slider.Track>
              <Slider.Range />
            </Slider.Track>
            <Slider.Thumb index={0}>
              <Slider.HiddenInput />
            </Slider.Thumb>
          </Slider.Control>
          <Slider.Label flexShrink={0}>高い</Slider.Label>
        </Slider.Root>
        <NumberInput.Root
          width="6rem"
          min={0} max={1} step={0.01}
          value={text}
          onValueChange={(d) => {
            setText(d.value);
            if (d.valueAsNumber >= 0 && d.valueAsNumber <= 1) setScore(d.valueAsNumber);
          }}
        >
          <NumberInput.Control />
          <NumberInput.Input aria-label="スコア" onBlur={() => commit(score)} />
        </NumberInput.Root>
      </HStack>
      <HStack gap={2}>
        <Button size="lg" colorPalette="blue" onClick={() => onSave({ score })}>
          保存して次へ
        </Button>
        <Button variant="ghost" onClick={() => onSave({ score: null })}>
          スキップ（判断できない）
        </Button>
      </HStack>
    </Stack>
  );
}
