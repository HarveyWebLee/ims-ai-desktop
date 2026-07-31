/**
 * AI 助手跨轮次 / HITL 排查日志（仅开发环境或手动开启）。
 *
 * 浏览器控制台过滤：[AgentTrace]
 * 持久开启：localStorage.setItem('aiAssistant.debugTrace', '1')
 */

function isAgentDebugEnabled(): boolean {
  if (process.env.NODE_ENV === "development") {
    return true;
  }
  try {
    return localStorage.getItem("aiAssistant.debugTrace") === "1";
  } catch {
    return false;
  }
}

/** 输出结构化排查日志 */
export function agentDebugLog(event: string, data?: Record<string, unknown>): void {
  if (!isAgentDebugEnabled()) return;
  // eslint-disable-next-line no-console
  console.debug(`[AgentTrace] ${event}`, data ?? {});
}

/** 助手消息摘要（避免打印整段 blocks） */
export function summarizeAssistantMessage(msg: {
  id: string;
  streaming?: boolean;
  planSteps?: { id: string; tool?: string; status?: string }[];
  blocks: { type: string; tool?: string; payload?: { tool?: string; type?: string } }[];
}): Record<string, unknown> {
  const toolsInBlocks = msg.blocks
    .filter((b) => b.type === "tool_call" || b.type === "interrupt")
    .map((b) => {
      if (b.type === "tool_call") return b.tool;
      return b.payload?.tool;
    })
    .filter(Boolean);
  return {
    messageId: msg.id.slice(0, 8),
    streaming: msg.streaming ?? false,
    blockTypes: msg.blocks.map((b) => b.type),
    toolsInBlocks,
    planTools: (msg.planSteps ?? []).map((s) => ({
      tool: s.tool,
      status: s.status,
    })),
  };
}
