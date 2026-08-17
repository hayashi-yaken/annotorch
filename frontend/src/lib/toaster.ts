import { createToaster } from "@chakra-ui/react";

/** アプリ共通のスナックバー。表示先は components/Toaster.tsx。 */
export const toaster = createToaster({
  placement: "top",
  pauseOnPageIdle: true,
  max: 3,
});
