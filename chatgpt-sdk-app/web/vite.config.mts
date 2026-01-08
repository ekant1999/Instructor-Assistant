import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "path";

const repoRoot = path.resolve(import.meta.dirname, "../..");
const widgetEntry = path.resolve(import.meta.dirname, "src", "widget-entry.tsx");

export default defineConfig({
  plugins: [react(), tailwindcss()],
  define: {
    "process.env.NODE_ENV": JSON.stringify("production"),
  },
  resolve: {
    alias: {
      "@": path.resolve(repoRoot, "client", "src"),
      "@assets": path.resolve(repoRoot, "attached_assets"),
      "react-dom/server": path.resolve(repoRoot, "node_modules", "react-dom", "server.browser.js"),
      react: path.resolve(repoRoot, "node_modules", "react"),
      "react-dom": path.resolve(repoRoot, "node_modules", "react-dom"),
    },
    dedupe: ["react", "react-dom"],
  },
  server: {
    fs: {
      allow: [repoRoot],
    },
  },
  css: {
    postcss: {
      plugins: [],
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
    lib: {
      entry: widgetEntry,
      formats: ["iife"],
      name: "ResearchNotesWidget",
      fileName: () => "widget",
    },
    rollupOptions: {
      input: widgetEntry,
      output: {
        format: "iife",
        inlineDynamicImports: true,
        manualChunks: undefined,
        entryFileNames: "widget.js",
        assetFileNames: "assets/[name][extname]",
        intro:
          "var process = globalThis.process && typeof globalThis.process === 'object'\n" +
          "  ? globalThis.process\n" +
          "  : { env: { NODE_ENV: 'production' } };\n" +
          "var global = globalThis;",
      },
    },
    cssCodeSplit: false,
  },
});
