import { Spinner, Stack, Text } from "@chakra-ui/react";

/** 読み込み中の領域を埋める中央寄せのスピナー。 */
export default function Loader({ label = "読み込み中…" }: { label?: string }) {
  return (
    <Stack align="center" justify="center" py={10} gap={3}>
      <Spinner size="lg" color="blue.solid" />
      <Text color="fg.muted">{label}</Text>
    </Stack>
  );
}
