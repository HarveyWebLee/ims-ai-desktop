/**
 * 聊天卡片展示用工具函数
 */
import type { PlanStep } from "@ims/shared-types";
import type { AiMessageBlock, AiMessage } from "./types";
import type { HitlPayload } from "@ims/shared-types";
import { agentDebugLog } from "./utils/agentDebugLog";

/** 工具名 → i18n key */
export const TOOL_LABEL_KEYS: Record<string, string> = {
  navigate_to: "aiAssistant.card.tool.navigate",
  pause: "aiAssistant.card.tool.pause",
  open_alarm_detail: "aiAssistant.card.tool.openAlarm",
  query_alarms: "aiAssistant.card.tool.queryAlarms",
  get_alarm_detail: "aiAssistant.card.tool.getAlarmDetail",
  download_file: "aiAssistant.card.tool.downloadFile",
  batch_confirm_alarms: "aiAssistant.card.tool.batchConfirmAlarms",
  batch_process_alarms: "aiAssistant.card.tool.batchProcessAlarms",
  query_devices: "aiAssistant.card.tool.queryDevices",
  get_device_detail: "aiAssistant.card.tool.getDeviceDetail",
  query_device_variables: "aiAssistant.card.tool.queryDeviceVariables",
  query_device_variable_realtime: "aiAssistant.card.tool.queryDeviceVariableRealtime",
  query_device_variable_history: "aiAssistant.card.tool.queryDeviceVariableHistory",
  send_device_cmd: "aiAssistant.card.tool.sendDeviceCmd",
  open_device_detail: "aiAssistant.card.tool.openDeviceDetail",
};

export function getToolLabelKey(tool: string): string {
  return TOOL_LABEL_KEYS[tool] ?? "aiAssistant.card.tool.default";
}

/** Client Action 展示文案（完成态） */
export function getClientActionLabel(action: { action: string }): string {
  switch (action.action) {
    case "navigate":
      return "aiAssistant.card.action.navigate";
    case "openModal":
      return "aiAssistant.card.action.openModal";
    case "download":
      return "aiAssistant.card.action.download";
    case "toast":
      return "aiAssistant.card.action.toast";
    case "refresh":
      return "aiAssistant.card.action.refresh";
    case "pause":
      return "aiAssistant.card.action.pause";
    default:
      return "aiAssistant.card.action.default";
  }
}

/** Client Action 进行中状态文案（按动作类型，禁止一律显示「下载中」） */
export function getClientActionPendingStatusKey(action: { action: string }): string {
  switch (action.action) {
    case "download":
      return "aiAssistant.card.action.downloading";
    case "pause":
      return "aiAssistant.card.action.pausing";
    case "navigate":
      return "aiAssistant.card.action.navigating";
    case "openModal":
      return "aiAssistant.card.action.openingModal";
    case "refresh":
      return "aiAssistant.card.action.refreshing";
    case "toast":
      return "aiAssistant.card.action.running";
    default:
      return "aiAssistant.card.action.running";
  }
}

export function isExecutionBlock(block: AiMessageBlock): boolean {
  return block.type === "tool_call" || block.type === "client_action";
}

/** 助手消息是否已有可展示内容（文本 / 工具 / HITL / Plan / Trace / Workspace） */
export function assistantMessageHasVisibleContent(message: AiMessage): boolean {
  if (message.workspaceContent) return true;
  if ((message.planSteps?.length ?? 0) > 0) return true;
  if ((message.traceEvents?.length ?? 0) > 0) return true;
  for (const block of message.blocks) {
    if (block.type === "text" && block.content.trim()) return true;
    if (block.type === "tool_call" || block.type === "client_action") return true;
    if (block.type === "interrupt") return true;
  }
  return false;
}

type ToolCallBlock = Extract<AiMessageBlock, { type: "tool_call" }>;

/** 结合 HITL 中断块推导工具展示状态（仅 running 可映射为 awaiting_hitl，保留 error 反馈） */
export function resolveToolCallDisplayStatus(
  block: ToolCallBlock,
  hitlPayload?: HitlPayload | null,
): ToolCallBlock["status"] {
  if (hitlPayload && hitlPayload.tool === block.tool && block.status === "running") {
    return "awaiting_hitl";
  }
  return block.status;
}

/** 仅展示与本条消息内工具/HITL 相关的计划步骤，避免跨轮次 Plan 残留 */
export function filterPlanStepsForMessage(
  planSteps: PlanStep[],
  blocks: AiMessageBlock[],
): PlanStep[] {
  if (!planSteps.length) return planSteps;

  const interruptBlock = blocks.find((b) => b.type === "interrupt");
  const interruptTool =
    interruptBlock?.type === "interrupt" ? interruptBlock.payload.tool : undefined;

  // 有 HITL 时：plan_confirm / 多步 Plan 内 confirm 保留完整步骤，避免只显示当前中断工具
  if (interruptTool && interruptBlock?.type === "interrupt") {
    const interruptType = interruptBlock.payload.type;
    if (interruptType === "plan_confirm" || (interruptType === "confirm" && planSteps.length > 1)) {
      return planSteps;
    }
    const filtered = planSteps.filter((step) => step.tool === interruptTool);
    if (filtered.length) {
      if (filtered.length !== planSteps.length) {
        agentDebugLog("ui.plan_filter", {
          mode: "interrupt_primary",
          interruptTool,
          allPlanTools: planSteps.map((s) => s.tool),
          filteredTools: filtered.map((s) => s.tool),
        });
      }
      return filtered;
    }
  }

  const toolsInTurn = new Set<string>();
  for (const block of blocks) {
    if (block.type === "tool_call" && block.tool) {
      if (interruptTool && block.tool === "download_file" && interruptTool !== "download_file") {
        continue;
      }
      toolsInTurn.add(block.tool);
    }
    if (block.type === "interrupt" && block.payload.tool) {
      toolsInTurn.add(block.payload.tool);
    }
  }
  if (!toolsInTurn.size) return planSteps;

  // 多步 Plan 已有完成步骤时保留全量展示（如 export confirm 续跑气泡）
  if (planSteps.length > 1 && planSteps.some((s) => s.status === "done")) {
    return planSteps;
  }

  const filtered = planSteps.filter((step) => step.tool && toolsInTurn.has(step.tool));
  if (filtered.length !== planSteps.length) {
    agentDebugLog("ui.plan_filter", {
      toolsInTurn: [...toolsInTurn],
      allPlanTools: planSteps.map((s) => s.tool),
      filteredTools: filtered.map((s) => s.tool),
      hiddenAll: filtered.length === 0,
    });
  }
  // 不匹配本轮工具时不回退展示全量 Plan（避免跨轮次污染）
  return filtered;
}

/** 隐藏同轮误触发且与 HITL 无关的 running 工具行（如导航轮次的 export） */
export function filterExecutionBlocksForMessage(
  blocks: AiMessageBlock[],
  interruptBlock: Extract<AiMessageBlock, { type: "interrupt" }> | null,
): AiMessageBlock[] {
  if (!interruptBlock?.payload.tool) return blocks;
  const hitlTool = interruptBlock.payload.tool;
  return blocks.filter((block) => {
    if (block.type !== "tool_call") return true;
    if (block.tool === hitlTool) return true;
    if (
      block.status === "running" &&
      block.tool === "download_file" &&
      hitlTool !== "download_file"
    ) {
      return false;
    }
    return true;
  });
}

/**
 * 同一工具在 HITL 续跑前后会各留一条 tool_call（awaiting_hitl + done），
 * 执行过程区合并为一条，避免「已确认 / 完成」重复展示。
 */
const TOOL_STATUS_RANK: Record<ToolCallBlock["status"], number> = {
  pending: 0,
  running: 1,
  awaiting_hitl: 2,
  cancelled: 3,
  error: 4,
  done: 5,
};

function coalesceToolCallBlocks(earlier: ToolCallBlock, later: ToolCallBlock): ToolCallBlock {
  const preferLater =
    (TOOL_STATUS_RANK[later.status] ?? 0) >= (TOOL_STATUS_RANK[earlier.status] ?? 0);
  const winner = preferLater ? later : earlier;
  const loser = preferLater ? earlier : later;
  return {
    ...winner,
    retry: Boolean(earlier.retry || later.retry),
    attempt: later.attempt ?? earlier.attempt,
    result: winner.result ?? loser.result,
    args: winner.args && Object.keys(winner.args).length > 0 ? winner.args : loser.args,
  };
}

/** 按工具名合并重复的 tool_call；client_action 保持原序 */
export function coalesceExecutionBlocks(blocks: AiMessageBlock[]): AiMessageBlock[] {
  const result: AiMessageBlock[] = [];
  const indexByTool = new Map<string, number>();

  for (const block of blocks) {
    if (block.type !== "tool_call") {
      result.push(block);
      continue;
    }
    const existingIndex = indexByTool.get(block.tool);
    if (existingIndex === undefined) {
      indexByTool.set(block.tool, result.length);
      result.push(block);
      continue;
    }
    const existing = result[existingIndex];
    if (existing?.type !== "tool_call") {
      result.push(block);
      continue;
    }
    result[existingIndex] = coalesceToolCallBlocks(existing, block);
  }

  return result;
}

export function partitionAssistantBlocks(blocks: AiMessageBlock[]) {
  const textBlocks: AiMessageBlock[] = [];
  const executionBlocks: AiMessageBlock[] = [];
  let interruptBlock: Extract<AiMessageBlock, { type: "interrupt" }> | null = null;

  for (const block of blocks) {
    if (block.type === "text") {
      textBlocks.push(block);
    } else if (block.type === "interrupt") {
      interruptBlock = block;
    } else if (isExecutionBlock(block)) {
      executionBlocks.push(block);
    }
  }

  return { textBlocks, executionBlocks, interruptBlock };
}
