/**
 * HITL interrupt 生命周期工具（SSE done / 活跃消息 / 历史恢复）
 *
 * 原则：凡已写入消息块的 interrupt，在流结束时不应仅凭「无 running tool_call」就清除；
 * plan_confirm / ask_params / confirm 由父图 checkpoint interrupt 产生，可能无对应 running 工具块。
 */
import type { HitlPayload } from "@ims/shared-types";
import type { AiMessage, AiMessageBlock } from "../types";

/** 父图级 HITL：不依赖 tool_call 块即可挂起 */
export function isGraphLevelHitlType(type: HitlPayload["type"] | string | undefined): boolean {
  return type === "plan_confirm" || type === "ask_params" || type === "confirm";
}

/** 从消息块中取 interrupt payload */
export function findInterruptPayload(blocks: AiMessageBlock[]): HitlPayload | null {
  const block = blocks.find((b) => b.type === "interrupt");
  if (block?.type !== "interrupt") return null;
  return block.payload;
}

/**
 * SSE onDone：是否应保留 interrupt 块并同步 pendingInterrupt。
 */
export function shouldPreserveHitlOnStreamDone(
  payload: HitlPayload,
  blocks: AiMessageBlock[],
): boolean {
  if (isGraphLevelHitlType(payload.type)) {
    return true;
  }
  const hitlTool = payload.tool;
  if (!hitlTool) return true;
  return blocks.some(
    (b) =>
      b.type === "tool_call" &&
      b.tool === hitlTool &&
      (b.status === "running" || b.status === "awaiting_hitl"),
  );
}

/**
 * 解析当前可交互 HITL 所在助手消息 id。
 * 优先 interrupt 块；兜底 pendingInterrupt + 计划/工具 awaiting 状态（防 onDone 误清后的恢复）。
 */
export function resolveActiveHitlMessageId(
  messages: AiMessage[],
  pendingInterrupt: HitlPayload | null,
): string | null {
  for (let i = messages.length - 1; i >= 0; i -= 1) {
    const m = messages[i];
    if (m.role === "assistant" && m.blocks.some((b) => b.type === "interrupt")) {
      return m.id;
    }
  }

  if (!pendingInterrupt) return null;

  for (let i = messages.length - 1; i >= 0; i -= 1) {
    const m = messages[i];
    if (m.role !== "assistant") continue;
    const payload = findInterruptPayload(m.blocks);
    if (payload && payload.type === pendingInterrupt.type) {
      return m.id;
    }
    const awaitingPlan = m.planSteps?.some(
      (s) => s.status === "awaiting_confirm" || s.status === "awaiting_hitl",
    );
    const awaitingTool = m.blocks.some(
      (b) =>
        b.type === "tool_call" &&
        b.tool === pendingInterrupt.tool &&
        (b.status === "running" || b.status === "awaiting_hitl"),
    );
    if (awaitingPlan || awaitingTool) {
      return m.id;
    }
  }
  return null;
}

/** 从历史消息恢复 pendingInterrupt（切换会话后仍可继续 HITL） */
export function findPendingInterruptFromMessages(messages: AiMessage[]): HitlPayload | null {
  for (let i = messages.length - 1; i >= 0; i -= 1) {
    const m = messages[i];
    if (m.role !== "assistant") continue;
    const payload = findInterruptPayload(m.blocks);
    if (payload) return payload;
  }
  return null;
}

/** 是否应在计划区顶部展示快捷确认按钮（plan_confirm） */
export function shouldShowPlanConfirmActions(
  hitlPayload: HitlPayload | null | undefined,
  interactive: boolean,
): boolean {
  return interactive && hitlPayload?.type === "plan_confirm";
}

/** 是否应在计划区上方展示高风险 confirm 快捷按钮（单工具 confirm） */
export function shouldShowToolConfirmActions(
  hitlPayload: HitlPayload | null | undefined,
  interactive: boolean,
): boolean {
  return interactive && hitlPayload?.type === "confirm";
}

/**
 * 是否渲染气泡顶部的 HitlQuickActions。
 * confirm / plan_confirm 均由 HitlInteractionCard 承载，避免重复面板。
 * ask_params 仅保留顶栏「请向下填写表单」提示。
 */
export function shouldShowHitlQuickActions(
  hitlPayload: HitlPayload | null | undefined,
  interactive: boolean,
): boolean {
  if (!interactive || !hitlPayload) return false;
  return hitlPayload.type === "ask_params";
}

/**
 * plan_confirm 待确认时隐藏 MessagePlanSection，计划预览与按钮统一在 HITL 卡片内。
 */
export function shouldHideMessagePlanForInteractiveHitl(
  hitlPayload: HitlPayload | null | undefined,
  interactive: boolean,
): boolean {
  return interactive && hitlPayload?.type === "plan_confirm";
}
