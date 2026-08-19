import { useState } from "react";
import { Box, Button, Checkbox, HStack, SimpleGrid, Stack, Text } from "@chakra-ui/react";
import { api } from "../api";
import type { Item } from "../api";
import { message } from "../lib/errors";
import { toaster } from "../lib/toaster";
import { useAsync } from "../lib/useAsync";
import ConfirmDialog from "./ConfirmDialog";
import ItemView from "./ItemView";

const VISIBLE_LIMIT = 50;

/** アイテムのサムネイル一覧と、選択したアイテムの削除。 */
export default function ItemGrid({ projectId, items, onChanged }: {
  projectId: string; items: Item[]; onChanged: () => void;
}) {
  const [selected, setSelected] = useState<string[]>([]);
  const [confirming, setConfirming] = useState(false);

  const visible = items.slice(0, VISIBLE_LIMIT);
  const targets = selected.filter((id) => visible.some((i) => i.id === id));

  const toggle = (id: string) =>
    setSelected((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]);

  const remove = useAsync(async () => {
    try {
      const { deleted } = await api.deleteItems(projectId, targets);
      setSelected([]);
      onChanged();
      toaster.success({ title: `アイテムを ${deleted} 件削除しました` });
    } catch (e) {
      toaster.error({ title: "アイテムを削除できませんでした", description: message(e) });
    } finally {
      setConfirming(false);
    }
  });

  return (
    <Stack gap={3}>
      {targets.length > 0 && (
        <HStack>
          <Text>{targets.length} 件選択中</Text>
          <Button size="sm" variant="outline" onClick={() => setSelected([])}>
            選択を解除
          </Button>
          <Button size="sm" colorPalette="red" onClick={() => setConfirming(true)}>
            削除
          </Button>
        </HStack>
      )}

      <SimpleGrid columns={{ base: 2, sm: 3, md: 5 }} gap={3}>
        {visible.map((item) => (
          <Box key={item.id} position="relative">
            <Checkbox.Root
              checked={selected.includes(item.id)}
              onCheckedChange={() => toggle(item.id)}
              position="absolute"
              top="1"
              left="1"
              zIndex="1"
              bg="bg"
              borderRadius="sm"
            >
              <Checkbox.HiddenInput aria-label={`${item.id} を選択`} />
              <Checkbox.Control />
            </Checkbox.Root>
            <ItemView projectId={projectId} item={item} />
          </Box>
        ))}
      </SimpleGrid>

      {items.length > VISIBLE_LIMIT && (
        <Text color="gray.500">…他 {items.length - VISIBLE_LIMIT} 件</Text>
      )}

      <ConfirmDialog
        open={confirming}
        title="アイテムを削除"
        message={`選択した ${targets.length} 件のアイテムを削除します。\n`
          + "元に戻せません。タスクで使用中のアイテムが含まれる場合は削除できません。"}
        loading={remove.pending}
        onConfirm={() => remove.run()}
        onCancel={() => setConfirming(false)}
      />
    </Stack>
  );
}
