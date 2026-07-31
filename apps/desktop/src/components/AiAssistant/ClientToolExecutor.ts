/**
 * Client Tool 执行器（桌面端）
 * navigate / 告警详情等平台动作 skip，后续由 Agent WS 推送 App
 */
import { message } from "antd";
import type { ClientAction } from "@ims/shared-types";
import qs from "qs";
import { requestTo } from "@/utils";
import { download } from "@/utils/tools";
import { dispatchAlarmDataChanged } from "./utils/alarmDataSync";

/** 带鉴权下载平台导出文件 */
async function downloadWithAuth(
  url: string,
  filename: string,
): Promise<{ ok: boolean; error?: string }> {
  const apiPath = url.startsWith("/api/app") ? url.slice("/api/app".length) : url;
  const [pathOnly, queryString] = apiPath.split("?");
  const params = queryString ? qs.parse(queryString) : undefined;

  const res = await requestTo<Record<string, unknown>, Blob>("get", {
    url: pathOnly,
    data: params,
    responseType: "blob",
  });

  if (res.code !== 0) {
    return { ok: false, error: "导出失败" };
  }

  const payload = res.data as Blob | { data?: Blob; filename?: string };
  const blob = payload instanceof Blob ? payload : payload?.data;
  if (!blob) {
    return { ok: false, error: "导出文件为空" };
  }

  const name =
    filename || (payload instanceof Blob ? undefined : payload?.filename) || "export.xlsx";
  download(blob, name);
  return { ok: true };
}

/** 执行 Client Tool；平台导航类动作桌面端跳过 */
export async function executeClientAction(
  action: ClientAction,
): Promise<{ ok: boolean; summary?: string; error?: string }> {
  try {
    switch (action.action) {
      case "navigate": {
        console.warn("[desktop] skip navigate:", action.path, action.query);
        return {
          ok: true,
          summary: "桌面端已跳过页面跳转（将由平台 WS 处理）",
        };
      }

      case "openModal": {
        console.warn("[desktop] skip openModal:", action.modal, action.params);
        return {
          ok: true,
          summary: "桌面端已跳过打开详情（将由平台 WS 处理）",
        };
      }

      case "download": {
        if (action.url.startsWith("/api/app")) {
          const result = await downloadWithAuth(action.url, action.filename);
          if (!result.ok) {
            return { ok: false, error: result.error };
          }
          return { ok: true, summary: `已开始下载 ${action.filename}` };
        }
        const link = document.createElement("a");
        link.href = action.url;
        link.download = action.filename;
        link.click();
        return { ok: true, summary: `已开始下载 ${action.filename}` };
      }

      case "toast": {
        message[action.level](action.message);
        return { ok: true };
      }

      case "refresh": {
        dispatchAlarmDataChanged();
        return { ok: true, summary: "Workspace 数据已同步刷新" };
      }

      case "pause": {
        const sec = Math.min(Math.max(Math.floor(action.seconds), 0), 120);
        await new Promise<void>((resolve) => {
          window.setTimeout(resolve, sec * 1000);
        });
        return { ok: true, summary: `已等待 ${sec} 秒` };
      }

      default: {
        const unknown = action as { action?: string };
        return {
          ok: false,
          error: `未知的 client_action: ${unknown.action ?? "undefined"}`,
        };
      }
    }
  } catch (err) {
    return {
      ok: false,
      error: err instanceof Error ? err.message : String(err),
    };
  }
}
