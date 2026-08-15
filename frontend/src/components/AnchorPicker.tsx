import { Box, Image, SimpleGrid, Stack, Text } from "@chakra-ui/react";
import { api } from "../api";
import type { Item } from "../api";

export default function AnchorPicker({ projectId, items, selected, onChange }: {
  projectId: string;
  items: Item[];
  selected: string[];
  onChange: (ids: string[]) => void;
}) {
  const toggle = (id: string) => {
    onChange(selected.includes(id)
      ? selected.filter((s) => s !== id)
      : [...selected, id]);
  };

  return (
    <Stack gap={2}>
      <Text fontSize="sm" color="gray.600">
        アンカー（基準アイテム）を選択（{selected.length}件）
      </Text>
      <Box maxH="16rem" overflowY="auto" borderWidth="1px" borderRadius="md" p={2}>
        <SimpleGrid columns={{ base: 3, md: 6 }} gap={2}>
          {items.map((item) => (
            <Box
              key={item.id}
              onClick={() => toggle(item.id)}
              cursor="pointer"
              borderWidth="2px"
              borderRadius="md"
              borderColor={selected.includes(item.id) ? "blue.500" : "transparent"}
              overflow="hidden"
            >
              {item.modality === "image" ? (
                <Image
                  src={api.itemFileUrl(projectId, item.id)}
                  alt={item.id}
                  w="full"
                  h="72px"
                  objectFit="contain"
                  bg="gray.100"
                />
              ) : (
                <Text fontSize="xs" p={2} lineClamp={3}>{item.text}</Text>
              )}
            </Box>
          ))}
        </SimpleGrid>
      </Box>
    </Stack>
  );
}
