/**
 * 历史会话恢复：将 trace runs 中的 plan / trace 数据回填到助手消息
 */
import type { PlanGraph, PlanStep, TraceEvent } from "@ims/shared-types";
import type { FlowDocumentJSON } from "@/components/BpmnFlowgram";
import type { AiMessage, AiMessageBlock } from "../types";

/** 线程级 BPMN 快照（与 GET /threads/{id}/state 对齐） */
export interface BpmnSnapshotLike {
  steps?: PlanStep[];
  graph?: PlanGraph | null;
  flow_document?: FlowDocumentJSON | Record<string, unknown> | null;
}

/** trace API 返回的单轮 run（含 plan_snapshot） */
export interface TraceRunSnapshot {
  run_id?: string;
  events?: TraceEvent[];
  graph?: PlanGraph | null;
  plan_snapshot?: {
    steps?: PlanStep[];
    graph?: PlanGraph;
    flow_document?: FlowDocumentJSON;
  } | null;
}

function extractPlanFromRun(run: TraceRunSnapshot): {
  planSteps?: PlanStep[];
  planGraph?: PlanGraph | null;
  planFlowDocument?: FlowDocumentJSON | null;
} {
  const snapshot = run.plan_snapshot;
  if (snapshot?.steps?.length) {
    return {
      planSteps: snapshot.steps,
      planGraph: snapshot.graph ?? null,
      planFlowDocument: snapshot.flow_document ?? null,
    };
  }

  const planEvent = [...(run.events ?? [])].reverse().find((e) => e.kind === "plan");
  const detail = planEvent?.detail as { steps?: PlanStep[]; graph?: PlanGraph } | undefined;
  if (detail?.steps?.length) {
    return {
      planSteps: detail.steps,
      planGraph: detail.graph ?? null,
      planFlowDocument: null,
    };
  }

  return {};
}

function messageHasPlanConfirmInterrupt(msg: AiMessage): boolean {
  return msg.blocks.some((b) => b.type === "interrupt" && b.payload.type === "plan_confirm");
}

function messageHasPlanBlock(msg: AiMessage): boolean {
  return msg.blocks.some((b) => b.type === "plan");
}

function messageHasVisibleText(msg: AiMessage): boolean {
  return msg.blocks.some((b) => b.type === "text" && b.content.trim().length > 0);
}

/**
 * 从 trace error 事件还原助手气泡文案（兼容未写入 checkpoint 的旧会话）。
 * 与后端 ``format_error_assistant_content`` / 实时 onError 对齐。
 */
export function extractErrorAssistantTextFromRun(run: TraceRunSnapshot): string | null {
  const errorEvent = [...(run.events ?? [])].reverse().find((e) => e.kind === "error");
  if (!errorEvent) return null;

  const detail = errorEvent.detail as { message?: unknown; data?: { hint?: unknown } } | undefined;
  const message = String(detail?.message ?? errorEvent.label ?? "").trim();
  if (!message) return null;

  const hint = String(detail?.data?.hint ?? "").trim();
  const body = hint ? `${message}\n\n${hint}` : message;
  return body.startsWith("⚠️") ? body : `⚠️ ${body}`;
}

/** 比较消息 plan 与 BPMN 快照步骤的重合度（id 权重高于 tool） */
function planOverlapScore(messageSteps: PlanStep[], snapshotSteps: PlanStep[]): number {
  if (!messageSteps.length || !snapshotSteps.length) return 0;

  const snapshotIds = new Set(snapshotSteps.map((s) => s.id));
  const snapshotTools = new Set(snapshotSteps.map((s) => s.tool).filter(Boolean) as string[]);

  let score = 0;
  for (const step of messageSteps) {
    if (snapshotIds.has(step.id)) score += 3;
    if (step.tool && snapshotTools.has(step.tool)) score += 1;
  }
  if (messageSteps.length === snapshotSteps.length) score += 2;
  return score;
}

/**
 * 定位应挂载 BPMN 快照的助手消息索引（多轮对话不误挂到最后一条）。
 *
 * 优先级：plan_confirm 中断 → plan 块 → 与快照步骤重合度最高 → 多步 plan → 任意 plan
 */
export function findPlanOwnerMessageIndex(
  messages: AiMessage[],
  bpmnSnapshot: BpmnSnapshotLike,
): number {
  const snapshotSteps = bpmnSnapshot.steps ?? [];
  const assistantIndices = messages
    .map((m, i) => (m.role === "assistant" ? i : -1))
    .filter((i) => i >= 0);

  if (!assistantIndices.length) return -1;

  for (let i = assistantIndices.length - 1; i >= 0; i -= 1) {
    const idx = assistantIndices[i];
    if (messageHasPlanConfirmInterrupt(messages[idx])) return idx;
  }

  for (let i = assistantIndices.length - 1; i >= 0; i -= 1) {
    const idx = assistantIndices[i];
    if (messageHasPlanBlock(messages[idx])) return idx;
  }

  if (snapshotSteps.length) {
    let bestIdx = -1;
    let bestScore = 0;
    for (const idx of assistantIndices) {
      const msgSteps = messages[idx].planSteps ?? [];
      if (!msgSteps.length) continue;
      const score = planOverlapScore(msgSteps, snapshotSteps);
      if (score > bestScore) {
        bestScore = score;
        bestIdx = idx;
      }
    }
    if (bestIdx >= 0 && bestScore > 0) return bestIdx;
  }

  for (let i = assistantIndices.length - 1; i >= 0; i -= 1) {
    const idx = assistantIndices[i];
    if ((messages[idx].planSteps?.length ?? 0) >= 2) return idx;
  }

  for (let i = assistantIndices.length - 1; i >= 0; i -= 1) {
    const idx = assistantIndices[i];
    if (messages[idx].planSteps?.length) return idx;
  }

  return -1;
}

/** 将线程 BPMN 快照挂到含 plan 的助手消息（AC-26 多轮增强） */
export function applyBpmnSnapshotToMessages(
  messages: AiMessage[],
  bpmnSnapshot: BpmnSnapshotLike,
): AiMessage[] {
  if (!bpmnSnapshot.flow_document && !bpmnSnapshot.steps?.length) {
    return messages;
  }

  const ownerIdx = findPlanOwnerMessageIndex(messages, bpmnSnapshot);
  if (ownerIdx < 0) return messages;

  const next = messages.map((m) => ({ ...m }));
  const msg = next[ownerIdx];
  next[ownerIdx] = {
    ...msg,
    planSteps: bpmnSnapshot.steps ?? msg.planSteps,
    planGraph: bpmnSnapshot.graph ?? msg.planGraph,
    planFlowDocument:
      (bpmnSnapshot.flow_document as AiMessage["planFlowDocument"]) ?? msg.planFlowDocument,
  };
  return next;
}

function ensureErrorTextOnAssistant(msg: AiMessage, run: TraceRunSnapshot): AiMessage {
  const errText = extractErrorAssistantTextFromRun(run);
  if (!errText || messageHasVisibleText(msg)) return msg;
  const textBlock: AiMessageBlock = { type: "text", content: errText };
  return { ...msg, blocks: [...msg.blocks, textBlock] };
}

function buildAssistantFromErrorRun(
  run: TraceRunSnapshot,
  options: { mid: string | undefined; seed: string },
): AiMessage | null {
  const errText = extractErrorAssistantTextFromRun(run);
  if (!errText) return null;

  const plan = extractPlanFromRun(run);
  return {
    id: `trace-error-${run.run_id || options.seed}`,
    role: "assistant",
    mid: options.mid,
    blocks: [{ type: "text", content: errText }],
    createdAt: Date.now(),
    streaming: false,
    traceEvents: run.events ?? [],
    runId: run.run_id ?? null,
    traceGraph: run.graph ?? null,
    planSteps: plan.planSteps,
    planGraph: plan.planGraph ?? null,
    planFlowDocument: plan.planFlowDocument ?? null,
  };
}

/**
 * 按用户轮次将 trace runs 与助手消息对齐（每轮用户后的**第一张**助手卡对应一个 run）。
 * 与实时单卡一致：同 turn 不应因 ReAct 多 AIMessage 消耗多个 run。
 * 无前置 user 的孤立助手卡仍按剩余 run 顺序回填（兼容单测与残缺历史）。
 * 若本轮仅有用户消息、checkpoint 无助手（旧版 LLM error 未落盘），则用 trace error 合成气泡。
 */
export function enrichMessagesWithTraceRuns(
  messages: AiMessage[],
  runs: TraceRunSnapshot[],
): AiMessage[] {
  if (!runs.length) return messages;

  const chronologicalRuns = [...runs].reverse();
  const next: AiMessage[] = messages.map((m) => ({ ...m, blocks: [...m.blocks] }));
  let runIdx = 0;
  const boundAssistants = new Set<number>();

  const applyRun = (msgIdx: number, run: TraceRunSnapshot) => {
    const plan = extractPlanFromRun(run);
    const patch: Partial<AiMessage> = {};

    if (run.events?.length) {
      patch.traceEvents = run.events;
      patch.runId = run.run_id ?? null;
      patch.traceGraph = run.graph ?? null;
    }
    if (plan.planSteps?.length) {
      patch.planSteps = plan.planSteps;
      patch.planGraph = plan.planGraph ?? null;
      // trace 快照未必含 flow_document；勿覆盖消息上已有 BPMN 画布（AC-26）
      if (plan.planFlowDocument) {
        patch.planFlowDocument = plan.planFlowDocument;
      }
    }

    if (Object.keys(patch).length) {
      next[msgIdx] = { ...next[msgIdx], ...patch };
    }
    next[msgIdx] = ensureErrorTextOnAssistant(next[msgIdx], run);
  };

  for (let i = 0; i < next.length; i += 1) {
    if (next[i].role !== "user") continue;

    const run = chronologicalRuns[runIdx];
    if (!run) break;
    runIdx += 1;

    let assistantIdx = -1;
    for (let j = i + 1; j < next.length; j += 1) {
      if (next[j].role === "user") break;
      if (next[j].role === "assistant") {
        assistantIdx = j;
        break;
      }
    }

    if (assistantIdx >= 0) {
      boundAssistants.add(assistantIdx);
      applyRun(assistantIdx, run);
      continue;
    }

    // checkpoint 无助手卡：用 trace error 合成（额度耗尽等旧数据）
    const synthesized = buildAssistantFromErrorRun(run, {
      mid: next[i].mid,
      seed: String(i),
    });
    if (synthesized) {
      next.splice(i + 1, 0, synthesized);
      boundAssistants.add(i + 1);
    }
  }

  for (let i = 0; i < next.length; i += 1) {
    if (next[i].role !== "assistant" || boundAssistants.has(i)) continue;
    const run = chronologicalRuns[runIdx];
    if (!run) break;
    runIdx += 1;
    applyRun(i, run);
  }

  return next;
}
