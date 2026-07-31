/**
 * SSE 事件解析工具
 * 解析 Agent 服务 text/event-stream 格式
 */
import type { ClientAction, HitlPayload, PlanStep, TraceEvent } from "@ims/shared-types";
import type { AgentSseHandler, PlanSsePayload } from "../types";

/** 解析 SSE 原始文本块（client_action 须 await，保证 Plan 内跳转/停留顺序执行） */
export async function parseSseChunk(buffer: string, handlers: AgentSseHandler): Promise<string> {
  const parts = buffer.split("\n\n");
  const remaining = parts.pop() ?? "";

  for (const part of parts) {
    if (!part.trim()) continue;

    let event = "message";
    let dataStr = "";

    for (const line of part.split("\n")) {
      if (line.startsWith("event:")) {
        event = line.slice(6).trim();
      } else if (line.startsWith("data:")) {
        dataStr = line.slice(5).trim();
      }
    }

    if (!dataStr) continue;

    try {
      const data = JSON.parse(dataStr);
      await dispatchSseEvent(event, data, handlers);
    } catch {
      // 忽略非法 JSON
    }
  }

  return remaining;
}

/** 分发 SSE 事件到处理器 */
async function dispatchSseEvent(
  event: string,
  data: Record<string, unknown>,
  handlers: AgentSseHandler,
): Promise<void> {
  switch (event) {
    case "message":
      if (data.type === "text" && typeof data.delta === "string") {
        handlers.onTextDelta?.(data.delta);
      }
      break;

    case "tool_start":
      handlers.onToolStart?.(
        String(data.tool ?? ""),
        (data.args as Record<string, unknown>) ?? {},
        {
          retry: Boolean(data.retry),
          attempt: typeof data.attempt === "number" ? data.attempt : undefined,
        },
      );
      break;

    case "tool_end":
      handlers.onToolEnd?.(String(data.tool ?? ""), String(data.result ?? ""), {
        retry: Boolean(data.retry),
        attempt: typeof data.attempt === "number" ? data.attempt : undefined,
      });
      break;

    case "interrupt":
      handlers.onInterrupt?.(data as unknown as HitlPayload);
      break;

    case "client_action":
      await handlers.onClientAction?.(data as unknown as ClientAction);
      break;

    case "plan": {
      const steps = (data.steps as PlanStep[]) ?? [];
      handlers.onPlan?.({
        steps,
        graph: data.graph as PlanSsePayload["graph"],
        flow_document: data.flow_document as PlanSsePayload["flow_document"],
      });
      break;
    }

    case "plan_update":
      handlers.onPlanUpdate?.(
        data as {
          step_id: string;
          status: string;
          tool?: string;
          node_id?: string;
          node_type?: string;
          skipReason?: string;
          matchedBranchKey?: string;
          label?: string;
        },
      );
      break;

    case "replan":
      handlers.onReplan?.(
        data as {
          reason: string;
          steps: PlanStep[];
          attempt?: number;
          failed_tool?: string;
        },
      );
      break;

    case "trace":
      handlers.onTrace?.(data as unknown as TraceEvent);
      break;

    case "done":
      handlers.onDone?.(String(data.thread_id ?? ""));
      break;

    case "error":
      handlers.onError?.(Number(data.code ?? 500), String(data.message ?? "未知错误"), data.data);
      break;

    default:
      break;
  }
}
