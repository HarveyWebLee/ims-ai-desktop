import { contextBridge } from "electron";

contextBridge.exposeInMainWorld("imsDesktop", {
  platform: process.platform,
});
