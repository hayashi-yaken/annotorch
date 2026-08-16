import { useEffect, useState } from "react";
import { Box, Button, Card, HStack, Input, Stack, Text } from "@chakra-ui/react";
import ConfirmDialog from "../components/ConfirmDialog";
import Layout from "../components/Layout";
import { toaster } from "../lib/toaster";
import { api } from "../api";
import { message } from "../lib/errors";
import type { Project } from "../api";

export default function ProjectsPage({ onOpen }: { onOpen: (p: Project) => void }) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [name, setName] = useState("");
  const [pendingDelete, setPendingDelete] = useState<Project | null>(null);

  const refresh = () =>
    api.listProjects().then(setProjects).catch((e) =>
      toaster.error({ title: "プロジェクト一覧を取得できませんでした", description: message(e) }));
  useEffect(() => { refresh(); }, []);

  const create = async () => {
    if (!name.trim()) return;
    try {
      const p = await api.createProject(name.trim());
      setName("");
      refresh();
      toaster.success({ title: `プロジェクト「${p.name}」を作成しました` });
    } catch (e) {
      toaster.error({ title: "プロジェクトを作成できませんでした", description: message(e) });
    }
  };

  const remove = async (p: Project) => {
    setPendingDelete(null);
    try {
      await api.deleteProject(p.id);
      refresh();
      toaster.success({ title: `プロジェクト「${p.name}」を削除しました` });
    } catch (e) {
      toaster.error({ title: "プロジェクトを削除できませんでした", description: message(e) });
    }
  };

  return (
    <Layout title="annotorch">
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
              <HStack justify="space-between" wrap="wrap">
                <Box>
                  <Text fontWeight="bold">{p.name}</Text>
                  <Text color="fg.muted">{p.description}</Text>
                </Box>
                <HStack>
                  <Button onClick={() => onOpen(p)}>開く</Button>
                  <Button colorPalette="red" variant="outline"
                          onClick={() => setPendingDelete(p)}>削除</Button>
                </HStack>
              </HStack>
            </Card.Body>
          </Card.Root>
        ))}
      </Stack>
      {projects.length === 0 && <Text>プロジェクトはまだありません</Text>}

      <ConfirmDialog
        open={pendingDelete !== null}
        title="プロジェクトを削除"
        message={pendingDelete
          ? `プロジェクト「${pendingDelete.name}」を削除します。\n`
            + "アイテム・タスク・回答もすべて削除され、元に戻せません。"
          : ""}
        onConfirm={() => pendingDelete && remove(pendingDelete)}
        onCancel={() => setPendingDelete(null)}
      />
    </Layout>
  );
}
