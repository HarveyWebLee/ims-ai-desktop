import { app, BrowserWindow, Menu, shell } from "electron";
import { join } from "node:path";

/** 去掉原生 File / Edit / View 等菜单栏（Windows 必须对窗口再 setMenu(null)） */
function stripNativeMenu(win: BrowserWindow): void {
  Menu.setApplicationMenu(null);
  win.setMenu(null);
  win.setMenuBarVisibility(false);
}

/** 创建主窗口（全屏聊天） */
function createWindow(): void {
  const win = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 960,
    minHeight: 640,
    title: "IMS AI 助手",
    autoHideMenuBar: true,
    webPreferences: {
      preload: join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  });

  stripNativeMenu(win);

  win.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: "deny" };
  });

  if (process.env.ELECTRON_RENDERER_URL) {
    win.loadURL(process.env.ELECTRON_RENDERER_URL);
  } else {
    win.loadFile(join(__dirname, "../dist/index.html"));
  }
}

app.whenReady().then(() => {
  Menu.setApplicationMenu(null);
  createWindow();
  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});
