/**
 * 将 Agent SSE error 事件格式化为使用者可读文案
 */
import type { IntlShape } from "@umijs/max";

export interface AgentErrorData {
  kind?: string;
  hint?: string;
  http_status?: number;
  error_type?: string;
  detail?: string;
}

function normalizeAgentErrorData(data: unknown): AgentErrorData | null {
  if (!data || typeof data !== "object") {
    if (typeof data === "string" && data.trim()) {
      return { detail: data.trim() };
    }
    return null;
  }
  return data as AgentErrorData;
}

/** 按 kind 取 i18n 主文案；否则使用后端 message */
function resolveMainMessage(intl: IntlShape, message: string, kind?: string): string {
  if (kind) {
    const id = `aiAssistant.error.kind.${kind}`;
    const localized = intl.formatMessage({ id, defaultMessage: "" });
    if (localized) return localized;
  }
  if (message?.trim()) return message.trim();
  return intl.formatMessage({ id: "aiAssistant.error.generic" });
}

/** 操作提示：优先后端 hint，其次 i18n hint.{kind}；无翻译时不展示 raw key */
function resolveHint(intl: IntlShape, data: AgentErrorData | null): string {
  if (data?.hint?.trim()) return data.hint.trim();
  const kind = data?.kind;
  if (!kind) return "";
  const id = `aiAssistant.error.hint.${kind}`;
  const localized = intl.formatMessage({ id, defaultMessage: "" });
  // formatMessage 未命中时可能回传 id 本身，需过滤
  if (localized && localized !== id) return localized;
  return "";
}

/**
 * 完整错误说明（可用于气泡内展示，含换行）
 */
export function formatAgentErrorMessage(intl: IntlShape, message: string, data?: unknown): string {
  const parsed = normalizeAgentErrorData(data);
  const main = resolveMainMessage(intl, message, parsed?.kind);
  const hint = resolveHint(intl, parsed);
  return hint ? `${main}\n${hint}` : main;
}

/**
 * Toast 用短文案：主句 + 可选首句 hint（过长则省略）
 */
export function formatAgentErrorToast(intl: IntlShape, message: string, data?: unknown): string {
  const full = formatAgentErrorMessage(intl, message, data);
  const [first, second] = full.split("\n");
  if (!second) return first;
  if (second.length <= 60) return `${first} ${second}`;
  return first;
}
