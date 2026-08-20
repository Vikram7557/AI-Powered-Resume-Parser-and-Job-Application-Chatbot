import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      "/session": "http://localhost:8000",
      "/chat": "http://localhost:8000",
      "/upload-resume": "http://localhost:8000",
      "/roles": "http://localhost:8000",
      "/health": "http://localhost:8000",
    },
  },
});
