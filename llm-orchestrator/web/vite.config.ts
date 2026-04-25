import { defineConfig } from "vite";

export default defineConfig({
  root: ".",
  appType: "spa",
  build: {
    outDir: "dist",
    /** Prod image serves minified assets only; no public source maps. */
    sourcemap: false,
  },
  server: {
    port: 5173,
    strictPort: true,
  },
});
