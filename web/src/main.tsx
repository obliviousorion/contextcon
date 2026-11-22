import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import Guided from "./guided/Guided";
import "./index.css";

// "/" and "/guided": the guided flow. "/console": the operator console (fallback).
// The server sends index.html for any page path, so no backend change is needed.
const path = window.location.pathname.replace(/\/+$/, "");
const Root = path.startsWith("/console") ? App : Guided;

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <Root />
  </React.StrictMode>,
);
