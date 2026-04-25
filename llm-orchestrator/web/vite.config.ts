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
    proxy: {
      // Backend: cd backend && uvicorn app.main:app --port 8765
      "/api": {
        target: "http://127.0.0.1:8765",
        changeOrigin: true,
      },
    },
  },
});
