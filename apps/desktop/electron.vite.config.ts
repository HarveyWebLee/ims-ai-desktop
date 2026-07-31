import { resolve } from "node:path";
import { defineConfig, externalizeDepsPlugin } from "electron-vite";
import react from "@vitejs/plugin-react";

const platformApiBase = process.env.PLATFORM_API_BASE || "http://192.168.99.240:18001/api/app";
const agentUrl = process.env.AGENT_SERVICE_URL || "http://127.0.0.1:8008";

export default defineConfig({
  main: {
    plugins: [externalizeDepsPlugin()],
    build: {
      outDir: "dist-electron",
      lib: {
        entry: "electron/main.ts",
      },
    },
  },
  preload: {
    plugins: [externalizeDepsPlugin()],
    build: {
      outDir: "dist-electron",
      emptyOutDir: false,
      lib: {
        entry: "electron/preload.ts",
      },
    },
  },
  renderer: {
    root: ".",
    build: {
      outDir: "dist",
      rollupOptions: {
        input: {
          index: resolve(__dirname, "index.html"),
        },
      },
    },
    resolve: {
      alias: {
        "@": resolve("src"),
        "@umijs/max": resolve("src/shims/umijs-max.tsx"),
      },
    },
    css: {
      preprocessorOptions: {
        less: {
          javascriptEnabled: true,
        },
      },
    },
    server: {
      host: "127.0.0.1",
      port: 6587,
      proxy: {
        "/api/agent": {
          target: agentUrl,
          changeOrigin: true,
          timeout: 0,
          proxyTimeout: 0,
          ws: true,
        },
        "/api/app": {
          target: platformApiBase.replace(/\/api\/app\/?$/, ""),
          changeOrigin: true,
          rewrite: (path) => path,
        },
      },
    },
    plugins: [react()],
  },
});
