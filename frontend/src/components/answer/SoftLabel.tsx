import { useState } from "react";
import { Button, Slider, Stack, Text } from "@chakra-ui/react";
import { normalizeDist } from "../../lib/softlabel";
import ItemView from "../ItemView";
import type { EditorProps } from "./types";

export default function SoftLabel({ projectId, task, unit, onSave }: EditorProps) {
  const labels = task.config.labels ?? [];
  const initial = (unit.answer?.dist as Record<string, number> | undefined) ?? {};
  const [weights, setWeights] = useState<Record<string, number>>(
    Object.fromEntries(labels.map((l) => [l, (initial[l] ?? 0) * 100])),
  );
  const dist = normalizeDist(weights);

  return (
    <Stack gap={4}>
      <ItemView projectId={projectId} item={unit.items[0]} size="large" />
      <Stack gap={3}>
        {labels.map((label) => (
          <Slider.Root key={label}
                       min={0} max={100}
                       value={[weights[label] ?? 0]}
                       onValueChange={(e) => setWeights({ ...weights, [label]: e.value[0] })}
                       display="flex" flexDirection="row" alignItems="center" gap={3}>
            <Slider.Label minW="7rem" flexShrink={0}>{label}</Slider.Label>
            <Slider.Control flex="1">
              <Slider.Track>
                <Slider.Range />
              </Slider.Track>
              <Slider.Thumb index={0}>
                <Slider.HiddenInput />
              </Slider.Thumb>
            </Slider.Control>
            <Text minW="3rem" textAlign="right" fontVariantNumeric="tabular-nums">
              {dist?.[label] !== undefined ? dist[label].toFixed(2) : "0.00"}
            </Text>
          </Slider.Root>
        ))}
      </Stack>
      <Button size="lg" colorPalette="blue" alignSelf="flex-start"
              disabled={!dist}
              onClick={() => dist && onSave({ dist })}>
        保存して次へ
      </Button>
    </Stack>
  );
}
