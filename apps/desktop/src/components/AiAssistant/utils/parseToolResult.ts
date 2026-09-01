import type { ClientAction, ToolResult } from "@ims/shared-types";

function parseToolResultJson(result: string): ToolResult | null {
  try {
    const data = JSON.parse(result) as unknown;
    if (typeof data === "object" && data !== null && !Array.isArray(data)) {
      return data as ToolResult;
    }
  } catch {
    // 非 JSON
  }
  return null;
}

/**
 * 解析 Server Tool 返回 JSON 的 ok 字段（与后端 parse_tool_result_ok 对齐）
 */
export function parseToolResultOk(result: string): boolean {
  if (!result) return true;
  const data = parseToolResultJson(result);
  if (data && "ok" in data) {
    return Boolean(data.ok);
  }
  // 非 ToolResult JSON 视为成功（纯文本摘要）
  return true;
}

/** 解析工具结果是否为用户主动取消（与后端 user_cancelled 对齐；兼容旧版嵌套在 data） */
export function parseToolResultUserCancelled(result: string): boolean {
  if (!result) return false;
  const data = parseToolResultJson(result);
  if (!data) return false;
  if (data.user_cancelled === true) return true;
  const nested = data.data;
  if (nested && typeof nested === "object" && !Array.isArray(nested)) {
    return (nested as { user_cancelled?: boolean }).user_cancelled === true;
  }
  return false;
}

/**
 * 从 ToolResult 提取需前端执行的动作（支持 client_actions 与单条 client_action）。
 * 与 Agent `_client_actions_from_tool_result` / 历史回放语义对齐。
 */
export function parseToolResultClientActions(result: string | undefined): ClientAction[] {
  if (!result) return [];
  const data = parseToolResultJson(result);
  if (!data) return [];
  if (Array.isArray(data.client_actions) && data.client_actions.length > 0) {
    return data.client_actions;
  }
  if (data.client_action && typeof data.client_action === "object") {
    return [data.client_action];
  }
  return [];
}

export interface ToolStreamMeta {
  retry?: boolean;
  attempt?: number;
}

/** 解析工具结果摘要（失败时用于 UI 展示） */
export function parseToolResultSummary(result: string | undefined): string | null {
  return formatToolResultDetail(result);
}

/** 格式化工具结果：summary + 平台 API 原样 data（供聊天框/执行步骤展示） */
function formatToolResultDetail(result: string | undefined): string | null {
  if (!result) return null;
  const parsed = parseToolResultJson(result);
  if (!parsed) {
    const trimmed = result.trim();
    return trimmed.length > 0 ? trimmed.slice(0, 500) : null;
  }
  const lines: string[] = [];
  const summary = parsed.summary;
  if (typeof summary === "string" && summary.trim()) {
    lines.push(summary.trim());
  }
  const data = parsed.data;
  if (data && typeof data === "object" && !Array.isArray(data)) {
    const plat = data as Record<string, unknown>;
    const autoRetry = plat.auto_retry as { from?: string; to?: string } | undefined;
    if (autoRetry?.from && autoRetry?.to) {
      lines.push(`自动换变量重试：${autoRetry.from} → ${autoRetry.to}`);
    }
    const platformData = plat.platform_data;
    if (platformData !== undefined && platformData !== null) {
      const detail =
        typeof platformData === "string"
          ? platformData.trim()
          : JSON.stringify(platformData, null, 2);
      if (detail) {
        lines.push(`平台响应 data：\n${detail}`);
      }
    }
    const retryErr = plat.retry_error as Record<string, unknown> | undefined;
    if (retryErr?.platform_data !== undefined) {
      const rd =
        typeof retryErr.platform_data === "string"
          ? retryErr.platform_data
          : JSON.stringify(retryErr.platform_data, null, 2);
      lines.push(`重试失败 data：\n${rd}`);
    }
  }
  return lines.length > 0 ? lines.join("\n\n") : null;
}

/** Plan / BPMN 节点用短摘要（优先 summary / error） */
export function parseToolResultShortSummary(result: string | undefined): string | null {
  if (!result) return null;
  const parsed = parseToolResultJson(result);
  if (parsed) {
    if (typeof parsed.summary === "string" && parsed.summary.trim()) {
      return parsed.summary.trim().slice(0, 200);
    }
    const legacy = parsed as ToolResult & { error?: unknown; message?: unknown };
    if (typeof legacy.error === "string" && legacy.error.trim()) {
      return legacy.error.trim().slice(0, 200);
    }
    if (typeof legacy.message === "string" && legacy.message.trim()) {
      return legacy.message.trim().slice(0, 200);
    }
  } else {
    const trimmed = result.trim();
    if (trimmed) return trimmed.slice(0, 200);
  }
  return null;
}

/** 解析工具结果中的自动换变量重试信息 */
export function parseToolResultAutoRetry(
  result: string | undefined,
): { from: string; to: string } | null {
  if (!result) return null;
  const parsed = parseToolResultJson(result);
  if (!parsed) return null;
  const data = parsed.data;
  if (!data || typeof data !== "object" || Array.isArray(data)) return null;
  const autoRetry = (data as Record<string, unknown>).auto_retry as
    { from?: string; to?: string } | undefined;
  if (autoRetry?.from && autoRetry?.to) {
    return { from: String(autoRetry.from), to: String(autoRetry.to) };
  }
  return null;
}
