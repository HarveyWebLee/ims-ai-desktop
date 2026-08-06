/**
 * HITL interrupt 生命周期工具（SSE done / 活跃消息 / 历史恢复）
 *
 * 原则：凡已写入消息块的 interrupt，在流结束时不应仅凭「无 running tool_call」就清除；
 * plan_confirm / ask_params / confirm 由父图 checkpoint interrupt 产生，可能无对应 running 工具块。
 */
import type { HitlPayload } from "@ims/shared-types";
import type { AiMessage, AiMessageBlock } from "../types";
import { useAiAssistantStore, getWriteTargetMessages } from "../store";

/** 父图级 HITL：不依赖 tool_call 块即可挂起 */
export function isGraphLevelHitlType(type: HitlPayload["type"] | string | undefined): boolean {
  return type === "plan_confirm" || type === "ask_params" || type === "confirm";
}

/** 从消息块中取 interrupt payload（跳过已终态块） */
export function findInterruptPayload(blocks: AiMessageBlock[]): HitlPayload | null {
  const block = blocks.find((b) => b.type === "interrupt" && !b.resolution);
  if (block?.type !== "interrupt") return null;
  return block.payload;
}

/** interrupt 块是否仍可交互（无 resolution） */
export function isActiveInterruptBlock(
  block: AiMessageBlock | undefined | null,
): block is Extract<AiMessageBlock, { type: "interrupt" }> {
  return !!block && block.type === "interrupt" && !block.resolution;
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
 * 优先：pending.mid → 同 mid 含 interrupt 的助手；再：任意 interrupt 块；再：awaiting 兜底。
 */
export function resolveActiveHitlMessageId(
  messages: AiMessage[],
  pendingInterrupt: HitlPayload | null,
): string | null {
  const mid = pendingInterrupt?.mid?.trim();
  if (mid) {
    for (let i = messages.length - 1; i >= 0; i -= 1) {
      const m = messages[i];
      if (
        m.role === "assistant" &&
        m.mid === mid &&
        m.blocks.some((b) => isActiveInterruptBlock(b))
      ) {
        return m.id;
      }
    }
    for (let i = messages.length - 1; i >= 0; i -= 1) {
      const m = messages[i];
      if (m.role === "assistant" && m.mid === mid) {
        return m.id;
      }
    }
  }

  for (let i = messages.length - 1; i >= 0; i -= 1) {
    const m = messages[i];
    if (m.role === "assistant" && m.blocks.some((b) => isActiveInterruptBlock(b))) {
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
    if (payload) {
      // 气泡 mid 回填到 payload，保证 resume 回传
      if (!payload.mid && m.mid) {
        return { ...payload, mid: m.mid };
      }
      return payload;
    }
  }
  return null;
}

/**
 * 将 /state 返回的 pending_interrupt 挂到对应助手气泡。
 * 有 mid：挂同 mid 助手；找不到则新建（禁止回退上一轮）。
 * 无 mid：兼容旧数据挂最后一条助手。
 * 后端已挂块时幂等；仅有顶层字段时补块。
 */
export function applyPendingInterruptToMessages(
  messages: AiMessage[],
  pending: HitlPayload | null | undefined,
): AiMessage[] {
  if (!pending) return messages;
  const mid = pending.mid?.trim();
  const existing = findPendingInterruptFromMessages(messages);
  if (existing && (!mid || existing.mid === mid || !existing.mid)) {
    // 已有 interrupt 块：补 mid
    if (existing.mid || !mid) return messages;
    return messages.map((m) => {
      if (m.role !== "assistant") return m;
      const idx = m.blocks.findIndex((b) => b.type === "interrupt");
      if (idx < 0) return m;
      const block = m.blocks[idx];
      if (block.type !== "interrupt") return m;
      const nextBlocks = [...m.blocks];
      nextBlocks[idx] = {
        type: "interrupt",
        payload: { ...block.payload, mid: block.payload.mid ?? mid },
      };
      return { ...m, mid: m.mid ?? mid, blocks: nextBlocks };
    });
  }

  let targetIndex = -1;
  if (mid) {
    for (let i = messages.length - 1; i >= 0; i -= 1) {
      if (messages[i].role === "assistant" && messages[i].mid === mid) {
        targetIndex = i;
        break;
      }
    }
  } else {
    for (let i = messages.length - 1; i >= 0; i -= 1) {
      if (messages[i].role === "assistant") {
        targetIndex = i;
        break;
      }
    }
  }

  if (targetIndex < 0) {
    return [
      ...messages,
      {
        id: `hitl-${mid ?? "pending"}`,
        role: "assistant",
        mid,
        blocks: [{ type: "interrupt", payload: pending }],
        createdAt: Date.now(),
      },
    ];
  }

  return messages.map((m, i) => {
    if (i !== targetIndex) return m;
    const without = m.blocks.filter((b) => b.type !== "interrupt");
    return {
      ...m,
      mid: m.mid ?? mid,
      blocks: [...without, { type: "interrupt", payload: pending }],
    };
  });
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

export type TurnResidueReason = "aborted" | "rejected" | "superseded";

/**
 * 将助手消息上的 HITL / 运行中工具 / 未完成 Plan 收束为终态（对称路径共用）。
 * 通过 zustand getState 直接改 store，供 abort / reject / 新消息复用。
 */
export function finalizeTurnResidue(
  messageId: string,
  reason: TurnResidueReason,
  options?: { resultSummary?: string },
): void {
  const store = useAiAssistantStore.getState();

  const msg = getWriteTargetMessages(store).find((m) => m.id === messageId);
  if (!msg || msg.role !== "assistant") {
    store.setPendingInterrupt(null);
    store.setStreaming(false);
    return;
  }

  store.setPendingInterrupt(null);

  const interruptBlock = msg.blocks.find((b) => b.type === "interrupt");
  if (interruptBlock?.type === "interrupt" && !interruptBlock.resolution) {
    store.resolveAssistantInterruptBlock(messageId, reason);
    const hitlTool = interruptBlock.payload.tool;
    if (hitlTool) {
      store.completeAssistantToolCall(messageId, hitlTool, undefined, "cancelled");
    }
  }

  // 重新取消息，避免上面已改 tool 后用旧快照漏标
  const latest = getWriteTargetMessages().find((m) => m.id === messageId);
  for (const block of latest?.blocks ?? []) {
    if (
      block.type === "tool_call" &&
      (block.status === "running" || block.status === "awaiting_hitl" || block.status === "pending")
    ) {
      store.completeAssistantToolCall(
        messageId,
        block.tool,
        undefined,
        "cancelled",
        block.toolCallId,
      );
    }
  }

  const summary = options?.resultSummary;
  const planMsg = getWriteTargetMessages().find((m) => m.id === messageId);
  for (const step of planMsg?.planSteps ?? []) {
    if (
      step.status === "pending" ||
      step.status === "running" ||
      step.status === "awaiting_hitl" ||
      step.status === "awaiting_confirm"
    ) {
      store.updateAssistantPlanStep(messageId, step.id, "skipped", {
        hitl: {
          ...(step.hitl ?? {}),
          resolution: reason === "rejected" ? "rejected" : "cancelled",
        },
        ...(summary ? { resultSummary: summary } : {}),
      });
    }
  }

  store.finalizeAssistantMessage(messageId);
  store.setStreaming(false);
}
