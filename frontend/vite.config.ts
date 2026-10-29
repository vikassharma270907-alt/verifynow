import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Inside Docker the backend is reachable as http://backend:8000 (set VITE_API_PROXY there).
const apiTarget = process.env.VITE_API_PROXY || "http://localhost:8000";

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
