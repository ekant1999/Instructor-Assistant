import { createRoot } from "react-dom/client";
import App from "./App";
import "./index.css";

const root =
  document.getElementById("root") ??
  (() => {
    const el = document.createElement("div");
    el.id = "root";
    (document.body || document.documentElement).appendChild(el);
    return el;
  })();

createRoot(root).render(<App />);
