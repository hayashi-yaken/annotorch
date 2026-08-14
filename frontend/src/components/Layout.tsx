import { Container, Heading, Stack } from "@chakra-ui/react";
import type { ReactNode } from "react";

export default function Layout({
  title,
  children,
}: {
  title?: string;
  children: ReactNode;
}) {
  return (
    <Container maxW="4xl" py={6}>
      <Stack gap={4}>
        {title && <Heading as="h1" size="lg">{title}</Heading>}
        {children}
      </Stack>
    </Container>
  );
}
