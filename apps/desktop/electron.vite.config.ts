import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { defineConfig, externalizeDepsPlugin } from "electron-vite";
import react from "@vitejs/plugin-react";

/** 简易 .env 加载：不引入 dotenv 依赖；override=true 时覆盖已有键。 */
function applyEnvFile(filePath: string, options: { override: boolean }): void {
  const { override } = options;
  if (!existsSync(filePath)) {
    return;
  }
  for (const rawLine of readFileSync(filePath, "utf8").split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#")) {
      continue;
    }
    const eq = line.indexOf("=");
    if (eq <= 0) {
      continue;
    }
    const key = line.slice(0, eq).trim();
    let value = line.slice(eq + 1).trim();
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }
    if (!override && process.env[key] !== undefined) {
      continue;
    }
    process.env[key] = value;
  }
}

const repoRoot = resolve(__dirname, "../..");
// 仓根共享 → 本应用 .env 覆盖（与 Agent/MCP 约定一致）
applyEnvFile(resolve(repoRoot, ".env.shared"), { override: false });
applyEnvFile(resolve(__dirname, ".env"), { override: true });

const platformApiBase = process.env.PLATFORM_API_BASE || "http://127.0.0.1:18001/api/app";
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
