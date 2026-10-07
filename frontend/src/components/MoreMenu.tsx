import { IconButton, Menu, Portal } from "@chakra-ui/react";

export interface MoreMenuItem {
  value: string;
  label: string;
  onSelect: () => void;
  danger?: boolean;
}

/** 頻度の低い操作を「⋯」ボタンの奥にまとめるメニュー。 */
export default function MoreMenu({ items, size = "md" }: {
  items: MoreMenuItem[];
  size?: "sm" | "md";
}) {
  return (
    <Menu.Root positioning={{ placement: "bottom-end" }}>
      <Menu.Trigger asChild>
        <IconButton aria-label="その他の操作" variant="ghost" size={size}>
          ⋯
        </IconButton>
      </Menu.Trigger>
      <Portal>
        <Menu.Positioner>
          <Menu.Content>
            {items.map((item) => (
              <Menu.Item
                key={item.value}
                value={item.value}
                onSelect={item.onSelect}
                {...(item.danger && {
                  color: "fg.error",
                  _hover: { bg: "bg.error", color: "fg.error" },
                })}
              >
                {item.label}
              </Menu.Item>
            ))}
          </Menu.Content>
        </Menu.Positioner>
      </Portal>
    </Menu.Root>
  );
}
