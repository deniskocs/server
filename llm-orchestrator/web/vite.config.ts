import { defineConfig } from "vite";

export default defineConfig({
  root: ".",
  appType: "spa",
  build: {
    outDir: "dist",
    sourcemap: true,
  },
  server: {
    port: 5173,
    strictPort: true,
  },
});
