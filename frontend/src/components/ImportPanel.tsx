import { useState } from "react";
import { Button, Card, FileUpload, HStack, Input, Stack, Text, useFileUpload } from "@chakra-ui/react";
import type { FileUpload as FileUploadNS } from "@chakra-ui/react";
import { api } from "../api";
import type { ImportReport } from "../api";

export default function ImportPanel({ projectId, onImported }: {
  projectId: string; onImported: () => void;
}) {
  const [folder, setFolder] = useState("");
  const [report, setReport] = useState<ImportReport | null>(null);
  const [error, setError] = useState("");

  const run = async (fn: () => Promise<ImportReport>) => {
    setError("");
    try {
      setReport(await fn());
      onImported();
    } catch (e) { setError(String(e)); }
  };

  // FileUpload validates against `accept` client-side and splits the drop into
  // acceptedFiles/rejectedFiles; we forward both to the server so it keeps
  // deciding what's importable and reports skips with a reason (unchanged
  // behavior from the previous plain <input>-based version).
  const filesFrom = (details: FileUploadNS.FileChangeDetails) => [
    ...details.acceptedFiles,
    ...details.rejectedFiles.map((r) => r.file),
  ];

  // Uses the external-store form (useFileUpload + RootProvider) instead of
  // FileUpload.Root so we can clear the picker's internal file list right
  // after each auto-upload. With maxFiles > 1 the picker otherwise keeps
  // accumulating every previously accepted file, which would resend
  // already-imported files on every new selection/drop.
  const imageUpload = useFileUpload({
    maxFiles: Infinity,
    accept: "image/*",
    onFileChange: (details) => {
      const files = filesFrom(details);
      imageUpload.clearFiles();
      imageUpload.clearRejectedFiles();
      if (files.length) run(() => api.uploadImages(projectId, files));
    },
  });
  const textUpload = useFileUpload({
    accept: ".jsonl,.csv",
    onFileChange: (details) => {
      const file = filesFrom(details)[0];
      textUpload.clearFiles();
      textUpload.clearRejectedFiles();
      if (file) run(() => api.uploadTexts(projectId, file));
    },
  });

  return (
    <Card.Root>
      <Card.Body>
        <Stack gap={5}>
          <Stack gap={2}>
            <Text fontWeight="bold">画像を取り込む</Text>
            <FileUpload.RootProvider value={imageUpload}>
              <FileUpload.HiddenInput />
              <FileUpload.Dropzone>
                <FileUpload.DropzoneContent>
                  画像をドロップ、またはクリックで選択
                </FileUpload.DropzoneContent>
              </FileUpload.Dropzone>
            </FileUpload.RootProvider>
          </Stack>

          <Stack gap={2}>
            <Text fontWeight="bold">テキスト（JSONL / CSV）を取り込む</Text>
            <FileUpload.RootProvider value={textUpload}>
              <FileUpload.HiddenInput />
              <FileUpload.Dropzone>
                <FileUpload.DropzoneContent>
                  JSONL / CSV をドロップ、またはクリックで選択
                </FileUpload.DropzoneContent>
              </FileUpload.Dropzone>
            </FileUpload.RootProvider>
          </Stack>

          <Stack gap={2}>
            <Text fontWeight="bold">サーバー上のフォルダから取り込む</Text>
            <HStack>
              <Input
                value={folder}
                onChange={(e) => setFolder(e.target.value)}
                placeholder="Docker では /import 配下のパス"
              />
              <Button onClick={() => folder && run(() => api.importFolder(projectId, folder))}>
                取り込み
              </Button>
            </HStack>
          </Stack>

          {report && (
            <Text>
              取り込み {report.imported} 件 / スキップ {report.skipped.length} 件
              {report.skipped.slice(0, 3).map((s) => ` （${s.reason}）`).join("")}
            </Text>
          )}
          {error && <Text color="red.500">{error}</Text>}
        </Stack>
      </Card.Body>
    </Card.Root>
  );
}
