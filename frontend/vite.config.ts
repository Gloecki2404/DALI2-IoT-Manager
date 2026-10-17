import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import { fileURLToPath } from "node:url";

// Built files go straight into the add-on, relative base for HA ingress.
export default defineConfig({
  base: "./",
  plugins: [vue()],
  build: {
    outDir: fileURLToPath(new URL("../dali2_iot_manager/www", import.meta.url)),
    emptyOutDir: true,
    chunkSizeWarningLimit: 1500,
  },
  server: {
    port: 5173,
    proxy: {
      "/api": { target: "http://localhost:8099", ws: true },
    },
  },
});
