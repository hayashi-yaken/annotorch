import { Box, Image, Text } from "@chakra-ui/react";
import { api } from "../api";
import type { Item } from "../api";

export default function ItemView({ projectId, item, size }: {
  projectId: string; item: Item; size?: "large";
}) {
  if (item.modality === "image") {
    return (
      <Image
        src={api.itemFileUrl(projectId, item.id)}
        alt={item.id}
        w="full"
        h={size === "large" ? "260px" : "100px"}
        objectFit="contain"
        bg="gray.100"
      />
    );
  }
  return (
    <Box borderWidth="1px" borderRadius="md" p={3}>
      <Text fontSize={size === "large" ? "1.15rem" : "md"}>{item.text}</Text>
    </Box>
  );
}
