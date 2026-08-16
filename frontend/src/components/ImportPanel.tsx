import { useEffect, useState } from "react";
import {
  Button, Card, FileUpload, Flex, HStack, Input, Spinner, Stack, Text, useFileUpload,
} from "@chakra-ui/react";
import type { UseFileUploadReturn } from "@chakra-ui/react";
import { api } from "../api";
import { message } from "../lib/errors";
import { toaster } from "../lib/toaster";
import type { ImportReport } from "../api";

function Dropzone({ label, hint, upload, busy }: {
  label: string; hint: string; upload: UseFileUploadReturn; busy: boolean;
}) {
  return (
    <Stack gap={2} flex="1" minW="0">
      <Text fontWeight="bold">{label}</Text>
      <FileUpload.RootProvider value={upload}>
        <FileUpload.HiddenInput />
        <FileUpload.Dropzone w="full" minH="9rem">
          <FileUpload.DropzoneContent>
            {busy
              ? <HStack gap={2}><Spinner size="sm" /><Text>取り込み中…</Text></HStack>
              : hint}
          </FileUpload.DropzoneContent>
        </FileUpload.Dropzone>
      </FileUpload.RootProvider>
    </Stack>
  );
}

export default function ImportPanel({ projectId, onImported }: {
  projectId: string; onImported: () => void;
}) {
  const [folder, setFolder] = useState("");
  const [importing, setImporting] = useState<string | null>(null);

  const run = async (label: string, fn: () => Promise<ImportReport>) => {
    setImporting(label);
    try {
      const report = await fn();
      const skipped = report.skipped
        .slice(0, 3)
        .map((s) => `\n・${s.reason}`)
        .join("");
      toaster.create({
        type: report.imported > 0 ? "success" : "warning",
        title: report.imported > 0
          ? `${label}を ${report.imported} 件取り込みました`
          : `${label}を取り込めませんでした`,
        description: `スキップ ${report.skipped.length} 件${skipped}`,
      });
      onImported();
    } catch (e) {
      toaster.error({ title: `${label}の取り込みに失敗しました`, description: message(e) });
    } finally {
      setImporting(null);
    }
  };

  // Uses the external-store form (useFileUpload + RootProvider) instead of
  // FileUpload.Root so we can read acceptedFiles/rejectedFiles as plain state
  // (see the effects below) and clear the picker after each auto-upload.
  // With maxFiles > 1 the picker otherwise keeps accumulating every
  // previously accepted file, which would resend already-imported files on
  // every new selection/drop.
  const imageUpload = useFileUpload({ maxFiles: Infinity, accept: "image/*" });
  const textUpload = useFileUpload({ accept: ".jsonl,.csv" });

  // Deliberately not using onFileChange: zag's file-upload machine keeps
  // acceptedFiles/rejectedFiles as two independent bindable stores, each
  // invoking onFileChange separately with a *stale* read of the other field
  // (via ctx.get) whenever a single drop/select touches both -- e.g. a valid
  // image plus a rejected .txt in the same selection fires onFileChange
  // twice, each carrying only half the files, splitting one upload into two
  // and racing two `run()` calls whose reports silently overwrite one
  // another. React batches both underlying context.set() calls from one
  // browser event into a single commit, so acceptedFiles/rejectedFiles are
  // reliably in sync with each other once this effect runs -- unlike
  // onFileChange, which fires per-field before that commit lands.
  useEffect(() => {
    const files = [...imageUpload.acceptedFiles, ...imageUpload.rejectedFiles.map((r) => r.file)];
    if (!files.length) return;
    imageUpload.clearFiles();
    run("画像", () => api.uploadImages(projectId, files));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [imageUpload.acceptedFiles, imageUpload.rejectedFiles]);

  useEffect(() => {
    const file = [...textUpload.acceptedFiles, ...textUpload.rejectedFiles.map((r) => r.file)][0];
    if (!file) return;
    textUpload.clearFiles();
    run("テキスト", () => api.uploadTexts(projectId, file));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [textUpload.acceptedFiles, textUpload.rejectedFiles]);

  return (
    <Card.Root>
      <Card.Body>
        <Stack gap={5}>
          <Flex direction={{ base: "column", md: "row" }} gap={4} align="stretch">
            <Dropzone
              label="画像を取り込む"
              hint="画像をドロップ、またはクリックで選択"
              upload={imageUpload}
              busy={importing === "画像"}
            />
            <Dropzone
              label="テキスト（JSONL / CSV）を取り込む"
              hint="JSONL / CSV をドロップ、またはクリックで選択"
              upload={textUpload}
              busy={importing === "テキスト"}
            />
          </Flex>

          <Stack gap={2}>
            <Text fontWeight="bold">サーバー上のフォルダから取り込む</Text>
            <HStack>
              <Input
                value={folder}
                onChange={(e) => setFolder(e.target.value)}
                placeholder="Docker では /import 配下のパス"
              />
              <Button
                loading={importing === "フォルダ"}
                loadingText="取り込み中…"
                onClick={() =>
                  folder && run("フォルダ", () => api.importFolder(projectId, folder))}
              >
                取り込み
              </Button>
            </HStack>
          </Stack>
        </Stack>
      </Card.Body>
    </Card.Root>
  );
}
