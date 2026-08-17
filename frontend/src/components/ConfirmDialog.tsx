import { Button, Dialog, Portal, Text } from "@chakra-ui/react";

export default function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = "削除",
  loading = false,
  onConfirm,
  onCancel,
}: {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  loading?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <Dialog.Root
      role="alertdialog"
      placement="center"
      open={open}
      closeOnInteractOutside={!loading}
      closeOnEscape={!loading}
      onOpenChange={(e) => !e.open && onCancel()}
    >
      <Portal>
        <Dialog.Backdrop />
        <Dialog.Positioner>
          <Dialog.Content>
            <Dialog.Header>
              <Dialog.Title>{title}</Dialog.Title>
            </Dialog.Header>
            <Dialog.Body>
              <Text whiteSpace="pre-line">{message}</Text>
            </Dialog.Body>
            <Dialog.Footer>
              <Button variant="outline" disabled={loading} onClick={onCancel}>
                キャンセル
              </Button>
              <Button colorPalette="red" loading={loading} onClick={onConfirm}>
                {confirmLabel}
              </Button>
            </Dialog.Footer>
          </Dialog.Content>
        </Dialog.Positioner>
      </Portal>
    </Dialog.Root>
  );
}
