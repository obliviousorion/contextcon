import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The app calls relative /api/...; the dev server proxies it to the local AsOf API (no CORS, no env var).
// Set VITE_API_URL only to call a different API origin directly.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": { target: "http://127.0.0.1:8787", changeOrigin: false },
    },
  },
  preview: {
    proxy: {
      "/api": { target: "http://127.0.0.1:8787", changeOrigin: false },
    },
  },
});
