/**
 * Client Tool 执行器（桌面端）
 * 有平台宿主时执行 navigate / openModal；无宿主跳过并降级提示；执行结果可回执 Agent。
 */
import type { ClientAction, ClientActionResult } from "@ims/shared-types";
import qs from "qs";
import { message } from "@/antd/feedback";
import { requestTo } from "@/utils";
import { download } from "@/utils/tools";
import { hostNavigate, hostOpenModal } from "./platformHost";

export type ClientActionExecResult = ClientActionResult;

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

function toResult(
  action: ClientAction["action"],
  partial: Omit<ClientActionExecResult, "action">,
): ClientActionExecResult {
  return { action, ...partial };
}

/** 执行 Client Tool；返回结构化结果供 Store 与 Agent 回执 */
export async function executeClientAction(action: ClientAction): Promise<ClientActionExecResult> {
  try {
    switch (action.action) {
      case "navigate": {
        const hosted = await hostNavigate(action.path, action.query);
        if (hosted) {
          if (!hosted.ok) {
            return toResult("navigate", {
              ok: false,
              path: action.path,
              error: hosted.error || "宿主导航失败",
              summary: hosted.summary,
            });
          }
          return toResult("navigate", {
            ok: true,
            skipped: false,
            path: action.path,
            summary: hosted.summary || `宿主已导航 ${action.path}`,
          });
        }
        console.warn("[desktop] skip navigate (no host):", action.path, action.query);
        message.info("桌面端已跳过页面跳转（无平台宿主；可开启模拟宿主验收）");
        return toResult("navigate", {
          ok: true,
          skipped: true,
          path: action.path,
          summary: "桌面端已跳过页面跳转（无平台宿主）",
        });
      }

      case "openModal": {
        const hosted = await hostOpenModal(action);
        if (hosted) {
          if (!hosted.ok) {
            return toResult("openModal", {
              ok: false,
              modal: action.modal,
              error: hosted.error || "宿主打开弹窗失败",
              summary: hosted.summary,
            });
          }
          return toResult("openModal", {
            ok: true,
            skipped: false,
            modal: action.modal,
            summary: hosted.summary || `宿主已打开 ${action.modal}`,
          });
        }
        console.warn("[desktop] skip openModal (no host):", action.modal, action.params);
        message.info("桌面端已跳过打开详情（无平台宿主；可开启模拟宿主验收）");
        return toResult("openModal", {
          ok: true,
          skipped: true,
          modal: action.modal,
          summary: "桌面端已跳过打开详情（无平台宿主）",
        });
      }

      case "download": {
        if (action.url.startsWith("/api/app")) {
          const result = await downloadWithAuth(action.url, action.filename);
          if (!result.ok) {
            return toResult("download", { ok: false, error: result.error });
          }
          return toResult("download", {
            ok: true,
            summary: `已开始下载 ${action.filename}`,
          });
        }
        const link = document.createElement("a");
        link.href = action.url;
        link.download = action.filename;
        link.click();
        return toResult("download", {
          ok: true,
          summary: `已开始下载 ${action.filename}`,
        });
      }

      case "toast": {
        message[action.level](action.message);
        return toResult("toast", { ok: true, summary: action.message });
      }

      case "refresh": {
        return toResult("refresh", { ok: true, summary: "Workspace 数据已同步刷新" });
      }

      case "pause": {
        const sec = Math.min(Math.max(Math.floor(action.seconds), 0), 120);
        await new Promise<void>((resolve) => {
          window.setTimeout(resolve, sec * 1000);
        });
        return toResult("pause", { ok: true, summary: `已等待 ${sec} 秒` });
      }

      default: {
        const unknown = action as { action?: string };
        return {
          action: (unknown.action as ClientAction["action"]) || "navigate",
          ok: false,
          error: `未知的 client_action: ${unknown.action ?? "undefined"}`,
        };
      }
    }
  } catch (err) {
    return {
      action: action.action,
      ok: false,
      error: err instanceof Error ? err.message : String(err),
    };
  }
}
