import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Inside Docker the backend is reachable as http://backend:8000 (compose sets VITE_API_URL).
const apiTarget =
  process.env.VITE_API_URL || process.env.VITE_API_PROXY || "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      "/api": apiTarget,
      "/health": apiTarget,
    },
  },
});