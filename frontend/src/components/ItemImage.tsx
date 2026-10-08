import { useState } from "react";
import { Center, Image, Text } from "@chakra-ui/react";
import { api } from "../api";

/** アイテムの画像。読み込みに失敗したら同じ大きさの枠にその旨を出す。 */
export default function ItemImage({ projectId, itemId, h }: {
  projectId: string; itemId: string; h: string;
}) {
  const src = api.itemFileUrl(projectId, itemId);
  const [failedSrc, setFailedSrc] = useState<string | null>(null);

  if (failedSrc === src) {
    return (
      <Center w="full" h={h} bg="gray.100" px={2}>
        <Text fontSize="xs" color="fg.muted" textAlign="center">
          画像を読み込めませんでした
        </Text>
      </Center>
    );
  }
  return (
    <Image
      src={src}
      alt={itemId}
      w="full"
      h={h}
      objectFit="contain"
      bg="gray.100"
      onError={() => setFailedSrc(src)}
    />
  );
}
