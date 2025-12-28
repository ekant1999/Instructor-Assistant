import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  define: {
    "process.env.NODE_ENV": JSON.stringify("production"),
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
    lib: {
      entry: "src/main.tsx",
      formats: ["iife"],
      name: "ResearchNotesWidget",
      fileName: () => "widget",
    },
    rollupOptions: {
      input: "src/main.tsx",
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
