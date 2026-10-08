import { Box, Text } from "@chakra-ui/react";
import type { Item } from "../api";
import ItemImage from "./ItemImage";

export default function ItemView({ projectId, item, size }: {
  projectId: string; item: Item; size?: "large";
}) {
  if (item.modality === "image") {
    return (
      <ItemImage projectId={projectId} itemId={item.id}
                 h={size === "large" ? "260px" : "100px"} />
    );
  }
  return (
    <Box borderWidth="1px" borderRadius="md" p={3}>
      <Text fontSize={size === "large" ? "1.15rem" : "md"}>{item.text}</Text>
    </Box>
  );
}
