import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Two entry points, both emitted unhashed into dist/ (served by FastAPI at /js):
//   - main.js   the site's vanilla-TS bundle (carousel + tides widget)
//   - tides.js  the React dashboard mounted on the /tides page
// In dev, /api is proxied to the FastAPI backend.
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: process.env.PORT ? Number(process.env.PORT) : 5173,
    proxy: {
      "/api": process.env.VITE_API_PROXY ?? "http://127.0.0.1:8000",
    },
  },
  build: {
    rollupOptions: {
      input: {
        main: "src/main.ts",
        tides: "src/tides/main.tsx",
      },
      output: {
        entryFileNames: "[name].js",
        chunkFileNames: "[name]-[hash].js",
        assetFileNames: "[name][extname]",
      },
    },
  },
});
