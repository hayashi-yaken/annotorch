import { ChakraProvider, defaultSystem } from "@chakra-ui/react";
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import Toaster from "./components/Toaster";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ChakraProvider value={defaultSystem}>
      <App />
      <Toaster />
    </ChakraProvider>
  </React.StrictMode>,
);
