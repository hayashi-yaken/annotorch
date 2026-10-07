import { useLayoutEffect, useRef, useState } from "react";
import { Portal, Text, Tooltip } from "@chakra-ui/react";
import type { TextProps } from "@chakra-ui/react";

/** 1行に収まらない分を「…」で省略し、省略されているときだけホバーで全文を出すテキスト。 */
export default function TruncatedText({ children, ...props }: TextProps & {
  children: string;
}) {
  const ref = useRef<HTMLParagraphElement>(null);
  const [truncated, setTruncated] = useState(false);

  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    const check = () => setTruncated(el.scrollWidth > el.clientWidth);
    check();
    const observer = new ResizeObserver(check);
    observer.observe(el);
    return () => observer.disconnect();
  }, [children]);

  return (
    <Tooltip.Root disabled={!truncated} openDelay={300} positioning={{ placement: "top-start" }}>
      <Tooltip.Trigger asChild>
        <Text ref={ref} truncate minW={0} {...props}>{children}</Text>
      </Tooltip.Trigger>
      <Portal>
        <Tooltip.Positioner>
          <Tooltip.Content maxW="32rem" wordBreak="break-all">{children}</Tooltip.Content>
        </Tooltip.Positioner>
      </Portal>
    </Tooltip.Root>
  );
}
