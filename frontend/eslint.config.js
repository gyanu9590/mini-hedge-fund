import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // Proxy all /api calls to FastAPI during development
      // so you don't hit CORS issues locally
      "/health":    "http://localhost:8000",
      "/metrics":   "http://localhost:8000",
      "/signals":   "http://localhost:8000",
      "/orders":    "http://localhost:8000",
      "/risk":      "http://localhost:8000",
      "/market":    "http://localhost:8000",
      "/performance":"http://localhost:8000",
      "/pipeline":  "http://localhost:8000",
      "/settings":  "http://localhost:8000",
      "/live-prices":"http://localhost:8000",
      "/ws":        { target: "ws://localhost:8000", ws: true },
    },
  },
});