import React from "react";
import ReactDOM from "react-dom/client";
import { CompanionGate } from "./CompanionGate";
import App from "./App";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>{"__TAURI_INTERNALS__" in window ? <App /> : <CompanionGate><App /></CompanionGate>}</React.StrictMode>,
);
