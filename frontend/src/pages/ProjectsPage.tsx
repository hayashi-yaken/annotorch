import { useEffect, useState } from "react";
import { Box, Button, Card, HStack, Input, Stack, Text } from "@chakra-ui/react";
import Layout from "../components/Layout";
import { api } from "../api";
import type { Project } from "../api";

export default function ProjectsPage({ onOpen }: { onOpen: (p: Project) => void }) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [name, setName] = useState("");
  const [error, setError] = useState("");

  const refresh = () =>
    api.listProjects().then(setProjects).catch((e) => setError(String(e)));
  useEffect(() => { refresh(); }, []);

  const create = async () => {
    if (!name.trim()) return;
    try {
      await api.createProject(name.trim());
      setName("");
      refresh();
    } catch (e) { setError(String(e)); }
  };

  const remove = async (p: Project) => {
    if (!confirm(`プロジェクト「${p.name}」を削除する？`)) return;
    try {
      await api.deleteProject(p.id);
      refresh();
    } catch (e) { setError(String(e)); }
  };

  return (
    <Layout title="annotorch">
      {error && <Text color="red.500">{error}</Text>}
      <HStack>
        <Input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="新しいプロジェクト名"
          onKeyDown={(e) => e.key === "Enter" && create()}
        />
        <Button onClick={create}>作成</Button>
      </HStack>
      <Stack gap={3}>
        {projects.map((p) => (
          <Card.Root key={p.id}>
            <Card.Body>
              <HStack justify="space-between">
                <Box>
                  <Text fontWeight="bold">{p.name}</Text>
                  <Text color="fg.muted">{p.description}</Text>
                </Box>
                <HStack>
                  <Button onClick={() => onOpen(p)}>開く</Button>
                  <Button colorPalette="red" variant="outline" onClick={() => remove(p)}>削除</Button>
                </HStack>
              </HStack>
            </Card.Body>
          </Card.Root>
        ))}
      </Stack>
      {projects.length === 0 && <Text>プロジェクトはまだありません</Text>}
    </Layout>
  );
}
