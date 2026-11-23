import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In development, Vite forwards /api/* to the FastAPI backend.
// This keeps browser and API on the same origin, so the backend needs no CORS setup.
// In Docker, nginx does the same job (see nginx.conf).
const backend = process.env.API_URL ?? "http://localhost:7555";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: backend,
        changeOrigin: true,
        rewrite: (caminho) => caminho.replace(/^\/api/, ""),
      },
    },
  },
});
