import { useState } from "react";
import { Badge, Button, Card, HStack, SimpleGrid, Stack, Text, Wrap } from "@chakra-ui/react";
import { assignToGroup, groupsToAnswer } from "../../lib/groupstate";
import ItemView from "../ItemView";
import type { EditorProps } from "./types";

const COLORS = ["green", "blue", "purple", "orange", "teal", "pink"];

export default function Grouping({ projectId, unit, onSave }: EditorProps) {
  const savedGroups = unit.answer?.groups as string[][] | undefined;
  const [numGroups, setNumGroups] = useState(Math.max(savedGroups?.length ?? 0, 2));
  const [active, setActive] = useState(0);
  const [assignment, setAssignment] = useState<Record<string, number>>(() => {
    const init: Record<string, number> = {};
    savedGroups?.forEach((ids, g) => ids.forEach((id) => { init[id] = g; }));
    return init;
  });
  const answer = groupsToAnswer(unit.items.map((i) => i.id), assignment);

  return (
    <Stack gap={4}>
      <Text color="fg.muted">グループを選んでからアイテムをクリックして振り分ける</Text>
      <Wrap gap={2}>
        {Array.from({ length: numGroups }, (_, g) => (
          <Button key={g}
                  colorPalette={COLORS[g % COLORS.length]}
                  variant={active === g ? "solid" : "outline"}
                  onClick={() => setActive(g)}>
            グループ {g + 1}
          </Button>
        ))}
        <Button variant="ghost" onClick={() => setNumGroups(numGroups + 1)}>＋ グループ追加</Button>
      </Wrap>
      <SimpleGrid columns={{ base: 2, md: 3 }} gap={3}>
        {unit.items.map((item) => {
          const g = assignment[item.id];
          return (
            <Card.Root key={item.id}
                       cursor="pointer"
                       colorPalette={g !== undefined ? COLORS[g % COLORS.length] : "gray"}
                       borderWidth={g !== undefined ? "3px" : "1px"}
                       borderColor={g !== undefined ? "colorPalette.solid" : undefined}
                       onClick={() => setAssignment(assignToGroup(assignment, item.id, active))}>
              <Card.Body gap={2} p={3}>
                <ItemView projectId={projectId} item={item} />
                <Badge alignSelf="flex-start" variant={g !== undefined ? "solid" : "outline"}>
                  {g !== undefined ? `グループ ${g + 1}` : "未割当"}
                </Badge>
              </Card.Body>
            </Card.Root>
          );
        })}
      </SimpleGrid>
      <HStack gap={2}>
        <Button size="lg" colorPalette="blue"
                disabled={!answer}
                onClick={() => answer && onSave({ groups: answer })}>
          保存して次へ
        </Button>
        <Button variant="outline" onClick={() => setAssignment({})}>リセット</Button>
      </HStack>
    </Stack>
  );
}
