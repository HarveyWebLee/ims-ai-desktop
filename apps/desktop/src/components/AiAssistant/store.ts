/**
 * AI 助手 Zustand Store
 * 独立状态，与 ai_chat 完全隔离
 */
import { create } from "zustand";
import { persist } from "zustand/middleware";
import { DEFAULT_AGENT_MODEL_ID, getCatalogItem } from "@ims/agent-core/model-catalog";
import type { AgentModelId, PlanStep, TraceEvent } from "@ims/shared-types";
import type { AiMessage, AiSession, HitlPayload } from "./types";
import { reconcilePlanStepsWithToolBlocks } from "./utils/planGraphUtils";
import { v4 as uuidv4 } from "uuid";

/** 持久化模型 ID 若已下线则回退默认，避免下拉空白 / 请求非法 model_id */
function resolvePersistedModelId(id: unknown): AgentModelId {
  if (typeof id === "string" && getCatalogItem(id)) {
    return id as AgentModelId;
  }
  return DEFAULT_AGENT_MODEL_ID;
}

/** 助手消息上可局部更新的元数据字段 */
type AssistantMessageMeta = Pick<
  AiMessage,
  | "streaming"
  | "traceEvents"
  | "traceGraph"
  | "runId"
  | "workspaceContent"
  | "planSteps"
  | "planGraph"
  | "planFlowDocument"
  | "planReplanReason"
>;

export interface AiAssistantState {
  sidebarOpen: boolean;
  sidebarWidth: number;
  currentThreadId: string;
  sessions: AiSession[];
  messages: AiMessage[];
  isStreaming: boolean;
  selectedModelId: AgentModelId;
  /** 当前选中的声纹用户 ID（语音输入必选） */
  selectedVoiceprintId: string | null;
  pendingInterrupt: HitlPayload | null;
  alarmDetailRecord: Record<string, unknown> | null;

  setSidebarOpen: (open: boolean) => void;
  setSidebarWidth: (width: number) => void;
  toggleSidebar: () => void;
  setSelectedModelId: (id: AgentModelId) => void;
  setSelectedVoiceprintId: (id: string | null) => void;
  createNewSession: () => string;
  switchSession: (threadId: string) => void;
  setSessions: (sessions: AiSession[]) => void;
  setMessages: (messages: AiMessage[]) => void;
  addUserMessage: (content: string) => string;
  appendAssistantBlock: (messageId: string, block: AiMessage["blocks"][0]) => void;
  /** 替换消息中已有 interrupt 块（HITL 从 ask_params 切到 confirm 时避免堆叠） */
  setAssistantInterruptBlock: (
    messageId: string,
    payload: Extract<AiMessage["blocks"][0], { type: "interrupt" }>["payload"],
  ) => void;
  /** 用户批准/拒绝或 HITL 已结束后移除 interrupt 块 */
  clearAssistantInterruptBlock: (messageId: string) => void;
  completeAssistantToolCall: (
    messageId: string,
    tool: string,
    result?: string,
    finalStatus?: "done" | "error" | "awaiting_hitl" | "cancelled",
  ) => void;
  /** HITL 中断：仅标记 running 工具为 awaiting_hitl，不覆盖已 error/done 的历史块 */
  markAssistantToolAwaitingHitl: (messageId: string, tool: string) => void;
  /** HITL 已批准/已提交：将 awaiting_hitl 工具块恢复为 running（续跑等待 SSE 前） */
  markAssistantToolRunning: (messageId: string, tool: string) => void;
  completeClientAction: (messageId: string, status: "done" | "error") => void;
  updateAssistantText: (
    messageId: string,
    delta: string,
    options?: { markStreaming?: boolean },
  ) => void;
  finalizeAssistantMessage: (messageId: string) => void;
  /** 更新单条助手消息的 Trace / Plan / Workspace 等元数据 */
  patchAssistantMessage: (messageId: string, patch: Partial<AssistantMessageMeta>) => void;
  appendAssistantTraceEvent: (messageId: string, event: TraceEvent) => void;
  updateAssistantPlanStep: (
    messageId: string,
    stepId: string,
    status: string,
    patch?: Partial<
      Pick<
        PlanStep,
        | "args"
        | "resultSummary"
        | "errorMessage"
        | "startedAt"
        | "endedAt"
        | "side"
        | "riskLevel"
        | "hitl"
        | "retry"
        | "attempt"
        | "autoRetryFrom"
        | "autoRetryTo"
        | "modelId"
        | "nodeId"
        | "nodeType"
        | "skipReason"
        | "matchedBranchKey"
        | "label"
      >
    >,
  ) => void;
  /** tool_end 后同步 Plan 步骤终态（plan_update 丢失或 step_id 不一致时的兜底） */
  syncAssistantPlanStepFromToolEnd: (
    messageId: string,
    tool: string,
    status: "done" | "error" | "skipped",
    patch?: Partial<
      Pick<
        PlanStep,
        | "args"
        | "resultSummary"
        | "errorMessage"
        | "startedAt"
        | "endedAt"
        | "side"
        | "riskLevel"
        | "hitl"
        | "retry"
        | "attempt"
        | "autoRetryFrom"
        | "autoRetryTo"
        | "modelId"
        | "nodeId"
        | "nodeType"
        | "skipReason"
        | "matchedBranchKey"
        | "label"
      >
    >,
  ) => void;
  /** 将仍为 running 的 Plan 步骤与 tool_call 块终态对齐（plan_update 丢失兜底） */
  reconcileAssistantPlanStepsFromBlocks: (messageId: string) => void;
  setStreaming: (streaming: boolean) => void;
  setPendingInterrupt: (payload: HitlPayload | null) => void;
  setAlarmDetailRecord: (record: Record<string, unknown> | null) => void;
}

export const useAiAssistantStore = create<AiAssistantState>()(
  persist(
    (set) => ({
      sidebarOpen: false,
      sidebarWidth: 360,
      currentThreadId: uuidv4(),
      sessions: [],
      messages: [],
      isStreaming: false,
      selectedModelId: DEFAULT_AGENT_MODEL_ID as AgentModelId,
      selectedVoiceprintId: null,
      pendingInterrupt: null,
      alarmDetailRecord: null,

      setSidebarOpen: (open) => set({ sidebarOpen: open }),
      setSidebarWidth: (width) => set({ sidebarWidth: Math.max(280, Math.round(width)) }),
      toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),

      setSelectedModelId: (id) => set({ selectedModelId: id }),
      setSelectedVoiceprintId: (id) => set({ selectedVoiceprintId: id }),

      createNewSession: () => {
        const threadId = uuidv4();
        set({
          currentThreadId: threadId,
          messages: [],
          pendingInterrupt: null,
        });
        return threadId;
      },

      switchSession: (threadId) =>
        set({
          currentThreadId: threadId,
          messages: [],
          pendingInterrupt: null,
        }),

      setSessions: (sessions) => set({ sessions }),

      setMessages: (messages) => set({ messages }),

      addUserMessage: (content) => {
        const id = uuidv4();
        const msg: AiMessage = {
          id,
          role: "user",
          blocks: [{ type: "text", content }],
          createdAt: Date.now(),
        };
        set((s) => ({ messages: [...s.messages, msg] }));
        return id;
      },

      appendAssistantBlock: (messageId, block) =>
        set((s) => ({
          messages: s.messages.map((m) => {
            if (m.id !== messageId) return m;
            // HITL 续跑会再次 tool_start：复用同工具的 awaiting_hitl/running 块，避免执行过程双行
            if (block.type === "tool_call") {
              const blocks = [...m.blocks];
              for (let i = blocks.length - 1; i >= 0; i -= 1) {
                const existing = blocks[i];
                if (
                  existing.type === "tool_call" &&
                  existing.tool === block.tool &&
                  (existing.status === "awaiting_hitl" || existing.status === "running")
                ) {
                  blocks[i] = {
                    ...existing,
                    ...block,
                    status: block.status,
                    args: block.args ?? existing.args,
                    retry: Boolean(existing.retry || block.retry),
                    attempt: block.attempt ?? existing.attempt,
                    result: block.result ?? existing.result,
                  };
                  return { ...m, blocks };
                }
              }
            }
            return { ...m, blocks: [...m.blocks, block] };
          }),
        })),

      setAssistantInterruptBlock: (messageId, payload) =>
        set((s) => ({
          messages: s.messages.map((m) => {
            if (m.id !== messageId) return m;
            const withoutInterrupt = m.blocks.filter((b) => b.type !== "interrupt");
            return {
              ...m,
              blocks: [...withoutInterrupt, { type: "interrupt", payload }],
            };
          }),
        })),

      clearAssistantInterruptBlock: (messageId) =>
        set((s) => ({
          messages: s.messages.map((m) =>
            m.id === messageId
              ? { ...m, blocks: m.blocks.filter((b) => b.type !== "interrupt") }
              : m,
          ),
        })),

      completeAssistantToolCall: (messageId, tool, result, finalStatus = "done") =>
        set((s) => ({
          messages: s.messages.map((m) => {
            if (m.id !== messageId) return m;
            const blocks = [...m.blocks];
            for (let i = blocks.length - 1; i >= 0; i -= 1) {
              const b = blocks[i];
              if (
                b.type === "tool_call" &&
                b.tool === tool &&
                (b.status === "running" || b.status === "error" || b.status === "awaiting_hitl")
              ) {
                blocks[i] = { ...b, status: finalStatus, result };
                break;
              }
            }
            return { ...m, blocks };
          }),
        })),

      markAssistantToolAwaitingHitl: (messageId, tool) =>
        set((s) => ({
          messages: s.messages.map((m) => {
            if (m.id !== messageId) return m;
            const blocks = [...m.blocks];
            let marked = false;
            for (let i = blocks.length - 1; i >= 0; i -= 1) {
              const b = blocks[i];
              if (b.type === "tool_call" && b.tool === tool && b.status === "running") {
                blocks[i] = { ...b, status: "awaiting_hitl" };
                marked = true;
                break;
              }
            }
            if (!marked) {
              blocks.push({
                type: "tool_call",
                tool,
                status: "awaiting_hitl",
                args: {},
              });
            }
            return { ...m, blocks };
          }),
        })),

      markAssistantToolRunning: (messageId, tool) =>
        set((s) => ({
          messages: s.messages.map((m) => {
            if (m.id !== messageId) return m;
            const blocks = [...m.blocks];
            let marked = false;
            for (let i = blocks.length - 1; i >= 0; i -= 1) {
              const b = blocks[i];
              if (
                b.type === "tool_call" &&
                b.tool === tool &&
                (b.status === "awaiting_hitl" || b.status === "running")
              ) {
                blocks[i] = { ...b, status: "running", result: undefined };
                marked = true;
                break;
              }
            }
            if (!marked) {
              blocks.push({
                type: "tool_call",
                tool,
                status: "running",
                args: {},
              });
            }
            return { ...m, blocks };
          }),
        })),

      completeClientAction: (messageId, status) =>
        set((s) => ({
          messages: s.messages.map((m) => {
            if (m.id !== messageId) return m;
            const blocks = [...m.blocks];
            // 仅完成最近一条 pending 的 client_action，避免并发时误标全部
            for (let i = blocks.length - 1; i >= 0; i -= 1) {
              const b = blocks[i];
              if (b.type === "client_action" && b.status === "pending") {
                blocks[i] = { ...b, status };
                break;
              }
            }
            return { ...m, blocks };
          }),
        })),

      updateAssistantText: (messageId, delta, options) =>
        set((s) => ({
          messages: s.messages.map((m) => {
            if (m.id !== messageId) return m;
            const blocks = [...m.blocks];
            const last = blocks[blocks.length - 1];
            if (last?.type === "text") {
              blocks[blocks.length - 1] = {
                type: "text",
                content: last.content + delta,
              };
            } else {
              blocks.push({ type: "text", content: delta });
            }
            const markStreaming = options?.markStreaming !== false;
            return {
              ...m,
              blocks,
              streaming: markStreaming ? true : m.streaming,
            };
          }),
        })),

      finalizeAssistantMessage: (messageId) =>
        set((s) => ({
          messages: s.messages.map((m) => (m.id === messageId ? { ...m, streaming: false } : m)),
        })),

      patchAssistantMessage: (messageId, patch) =>
        set((s) => ({
          messages: s.messages.map((m) => (m.id === messageId ? { ...m, ...patch } : m)),
        })),

      appendAssistantTraceEvent: (messageId, event) =>
        set((s) => ({
          messages: s.messages.map((m) =>
            m.id === messageId ? { ...m, traceEvents: [...(m.traceEvents ?? []), event] } : m,
          ),
        })),

      updateAssistantPlanStep: (messageId, stepId, status, patch) =>
        set((s) => ({
          messages: s.messages.map((m) => {
            if (m.id !== messageId || !m.planSteps?.length) return m;
            const normalizedStepId = String(stepId);
            return {
              ...m,
              planSteps: m.planSteps.map((step) =>
                String(step.id) === normalizedStepId ||
                String(step.nodeId ?? "") === normalizedStepId
                  ? {
                      ...step,
                      status: status as PlanStep["status"],
                      ...(patch ?? {}),
                    }
                  : step,
              ),
            };
          }),
        })),

      syncAssistantPlanStepFromToolEnd: (messageId, tool, status, patch) =>
        set((s) => ({
          messages: s.messages.map((m) => {
            if (m.id !== messageId || !m.planSteps?.length) return m;
            // 优先未终态步骤；若 plan_update 已先标 done，仍回写同工具步骤以补 resultSummary
            let targetIndex = m.planSteps.findIndex(
              (step) => step.tool === tool && step.status !== "done" && step.status !== "skipped",
            );
            if (targetIndex < 0) {
              for (let i = m.planSteps.length - 1; i >= 0; i -= 1) {
                if (m.planSteps[i].tool === tool) {
                  targetIndex = i;
                  break;
                }
              }
            }
            if (targetIndex < 0) return m;
            const nextSteps = [...m.planSteps];
            nextSteps[targetIndex] = {
              ...nextSteps[targetIndex],
              status,
              ...(patch ?? {}),
            };
            return { ...m, planSteps: nextSteps };
          }),
        })),

      reconcileAssistantPlanStepsFromBlocks: (messageId) =>
        set((s) => ({
          messages: s.messages.map((m) => {
            if (m.id !== messageId || !m.planSteps?.length) return m;
            const nextSteps = reconcilePlanStepsWithToolBlocks(m.planSteps, m.blocks);
            if (nextSteps === m.planSteps) return m;
            return { ...m, planSteps: nextSteps };
          }),
        })),

      setStreaming: (streaming) => set({ isStreaming: streaming }),
      setPendingInterrupt: (payload) => set({ pendingInterrupt: payload }),
      setAlarmDetailRecord: (record) => set({ alarmDetailRecord: record }),
    }),
    {
      name: "ai-assistant-store",
      partialize: (s) => ({
        selectedModelId: s.selectedModelId,
        selectedVoiceprintId: s.selectedVoiceprintId,
        sidebarOpen: s.sidebarOpen,
        sidebarWidth: s.sidebarWidth,
      }),
      merge: (persisted, current) => {
        const p = (persisted ?? {}) as Partial<AiAssistantState>;
        return {
          ...current,
          ...p,
          selectedModelId: resolvePersistedModelId(p.selectedModelId),
          selectedVoiceprintId:
            typeof p.selectedVoiceprintId === "string" ? p.selectedVoiceprintId : null,
        };
      },
    },
  ),
);
