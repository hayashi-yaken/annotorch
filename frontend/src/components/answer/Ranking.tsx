import { useState } from "react";
import { Badge, Button, Card, HStack, SimpleGrid, Stack, Text } from "@chakra-ui/react";
import { toggleInOrder } from "../../lib/groupstate";
import ItemView from "../ItemView";
import type { EditorProps } from "./types";

export default function Ranking({ projectId, unit, onSave }: EditorProps) {
  const [order, setOrder] = useState<string[]>(
    (unit.answer?.order as string[] | undefined) ?? [],
  );
  return (
    <Stack gap={4}>
      <Text color="fg.muted">良い順にクリックして順位をつける（もう一度クリックで解除）</Text>
      <SimpleGrid columns={{ base: 2, md: 3 }} gap={3}>
        {unit.items.map((item) => {
          const rank = order.indexOf(item.id);
          return (
            <Card.Root key={item.id}
                       cursor="pointer"
                       colorPalette="blue"
                       borderWidth={rank >= 0 ? "2px" : "1px"}
                       borderColor={rank >= 0 ? "colorPalette.solid" : undefined}
                       onClick={() => setOrder(toggleInOrder(order, item.id))}>
              <Card.Body gap={2} p={3}>
                <ItemView projectId={projectId} item={item} />
                <Badge alignSelf="flex-start"
                       colorPalette={rank >= 0 ? "blue" : "gray"}
                       variant={rank >= 0 ? "solid" : "outline"}>
                  {rank >= 0 ? `${rank + 1} 位` : "未選択"}
                </Badge>
              </Card.Body>
            </Card.Root>
          );
        })}
      </SimpleGrid>
      <HStack gap={2}>
        <Button size="lg" colorPalette="blue"
                disabled={order.length !== unit.items.length}
                onClick={() => onSave({ order })}>
          保存して次へ
        </Button>
        <Button variant="outline" onClick={() => setOrder([])}>リセット</Button>
      </HStack>
    </Stack>
  );
}
