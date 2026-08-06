/**
 * AI 助手 Zustand Store
 * 独立状态，与 ai_chat 完全隔离
 */
import { create } from "zustand";
import { persist } from "zustand/middleware";
import {
  AUTO_AGENT_MODEL_ID,
  getCatalogItem,
  type AgentModelSelectionId,
} from "@ims/agent-core/model-catalog";
import type { AgentRunMode, PlanStep, TraceEvent } from "@ims/shared-types";
import type { AiMessage, AiSession, HitlPayload, WorkspaceContent } from "./types";
import { getMessageWriteThreadId, type ThreadSnapshot } from "./threadRuntime";
import { reconcilePlanStepsWithToolBlocks } from "./utils/planGraphUtils";
import { v4 as uuidv4 } from "uuid";
import { isPinnedWorkspaceKind } from "./WorkspaceContentView";

const DEFAULT_RUN_MODE: AgentRunMode = "confirm";

/** 从消息列表取最近一条可固定侧栏的 workspace */
function latestPinnedWorkspace(
  messages: AiMessage[],
): { content: WorkspaceContent; messageId: string } | null {
  for (let i = messages.length - 1; i >= 0; i -= 1) {
    const m = messages[i];
    if (m.role === "assistant" && m.workspaceContent && isPinnedWorkspaceKind(m.workspaceContent)) {
      return { content: m.workspaceContent, messageId: m.id };
    }
  }
  return null;
}

function resolvePersistedRunMode(value: unknown): AgentRunMode {
  if (value === "readonly" || value === "confirm" || value === "autonomous") {
    return value;
  }
  return DEFAULT_RUN_MODE;
}

/** 在消息块中定位待更新的 tool_call：优先 toolCallId，否则按工具名取最近匹配状态 */
function findToolCallBlockIndex(
  blocks: AiMessage["blocks"],
  tool: string,
  toolCallId: string | undefined,
  statuses: string[],
): number {
  if (toolCallId) {
    for (let i = blocks.length - 1; i >= 0; i -= 1) {
      const b = blocks[i];
      if (b.type === "tool_call" && b.toolCallId === toolCallId) {
        return i;
      }
    }
  }
  for (let i = blocks.length - 1; i >= 0; i -= 1) {
    const b = blocks[i];
    if (b.type === "tool_call" && b.tool === tool && statuses.includes(b.status)) {
      return i;
    }
  }
  return -1;
}

/** 持久化模型 ID 若已下线 / 非法则回退 Auto，避免下拉空白 / 请求非法 model_id */
function resolvePersistedModelId(id: unknown): AgentModelSelectionId {
  if (typeof id !== "string" || !id.trim()) {
    return AUTO_AGENT_MODEL_ID;
  }
  if (id === AUTO_AGENT_MODEL_ID) {
    return AUTO_AGENT_MODEL_ID;
  }
  if (getCatalogItem(id)) {
    return id as AgentModelSelectionId;
  }
  return AUTO_AGENT_MODEL_ID;
}

/** 读取写入目标 thread 的消息列表（当前会话或后台快照） */
function baseMessagesForWrite(s: {
  currentThreadId: string;
  messages: AiMessage[];
  threadSnapshots: Record<string, ThreadSnapshot>;
}): { threadId: string; messages: AiMessage[]; isCurrent: boolean } {
  const threadId = getMessageWriteThreadId(s.currentThreadId);
  const isCurrent = threadId === s.currentThreadId;
  const messages = isCurrent ? s.messages : (s.threadSnapshots[threadId]?.messages ?? []);
  return { threadId, messages, isCurrent };
}

function commitThreadMessages(
  s: {
    currentThreadId: string;
    messages: AiMessage[];
    pendingInterrupt: HitlPayload | null;
    threadSnapshots: Record<string, ThreadSnapshot>;
  },
  threadId: string,
  messages: AiMessage[],
  extra?: {
    pendingInterrupt?: HitlPayload | null;
    isStreaming?: boolean;
    streamingByThread?: Record<string, boolean>;
    isLoadingHistory?: boolean;
  },
): {
  messages?: AiMessage[];
  pendingInterrupt?: HitlPayload | null;
  threadSnapshots: Record<string, ThreadSnapshot>;
  isStreaming?: boolean;
  streamingByThread?: Record<string, boolean>;
  isLoadingHistory?: boolean;
} {
  const isCurrent = threadId === s.currentThreadId;
  const prev = s.threadSnapshots[threadId];
  let pending = prev?.pendingInterrupt ?? null;
  if (isCurrent) {
    pending =
      extra && "pendingInterrupt" in extra ? (extra.pendingInterrupt ?? null) : s.pendingInterrupt;
  } else if (extra && "pendingInterrupt" in extra) {
    pending = extra.pendingInterrupt ?? null;
  }
  const threadSnapshots = {
    ...s.threadSnapshots,
    [threadId]: { messages, pendingInterrupt: pending },
  };
  if (isCurrent) {
    return { messages, threadSnapshots, ...(extra ?? {}) };
  }
  return { threadSnapshots, ...(extra ?? {}) };
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
  /** P2-4：各 thread 是否仍有进行中的 SSE */
  streamingByThread: Record<string, boolean>;
  /** P2-4：切走会话时缓存消息 / HITL，供后台流继续写入与切回恢复 */
  threadSnapshots: Record<string, ThreadSnapshot>;
  /** 正在拉取历史会话消息（切换会话期间不展示欢迎空态） */
  isLoadingHistory: boolean;
  selectedModelId: AgentModelSelectionId;
  /** 会话运行模式：只读 / 确认执行 / 自主 */
  runMode: AgentRunMode;
  /** 显式「先计划后执行」：多步任务先 plan_confirm 再调写工具 */
  planFirst: boolean;
  /** 当前选中的声纹用户 ID（语音输入必选） */
  selectedVoiceprintId: string | null;
  /**
   * 声纹门禁是否开启（与 Agent VOICEPRINT_ENABLED 同步，运行时拉取，不持久化）
   */
  voiceprintEnabled: boolean;
  /** 是否在输入框用下划线标注纠错段并悬停显示原文 */
  voiceCorrectionHighlightEnabled: boolean;
  pendingInterrupt: HitlPayload | null;
  alarmDetailRecord: Record<string, unknown> | null;
  /** 右侧 Workspace 侧栏当前展示的结构化结果 */
  activeWorkspace: WorkspaceContent | null;
  activeWorkspaceSourceId: string | null;

  setSidebarOpen: (open: boolean) => void;
  setSidebarWidth: (width: number) => void;
  toggleSidebar: () => void;
  /** 打开侧栏并固定展示指定结果（与消息内卡片并存） */
  openWorkspacePanel: (content: WorkspaceContent, sourceMessageId?: string | null) => void;
  clearActiveWorkspace: () => void;
  setSelectedModelId: (id: AgentModelSelectionId) => void;
  setRunMode: (mode: AgentRunMode) => void;
  setPlanFirst: (enabled: boolean) => void;
  setSelectedVoiceprintId: (id: string | null) => void;
  setVoiceprintEnabled: (enabled: boolean) => void;
  setVoiceCorrectionHighlightEnabled: (enabled: boolean) => void;
  createNewSession: () => string;
  switchSession: (threadId: string) => void;
  /** 当前或指定 thread 是否 streaming */
  isThreadStreaming: (threadId?: string) => boolean;
  /** 切会话前是否已有可恢复快照（有消息或仍在流式） */
  hasThreadSnapshot: (threadId: string) => boolean;
  clearThreadSnapshot: (threadId: string) => void;
  setSessions: (sessions: AiSession[]) => void;
  /**
   * 发起对话后立即刷新侧栏会话摘要（与后端 upsert 标题规则对齐：前 20 字）。
   * 置顶当前 thread，避免流结束前切走看不到新会话。
   */
  touchSession: (threadId: string, title: string) => void;
  setMessages: (messages: AiMessage[]) => void;
  setLoadingHistory: (loading: boolean) => void;
  addUserMessage: (content: string) => string;
  appendAssistantBlock: (messageId: string, block: AiMessage["blocks"][0]) => void;
  /** 替换消息中已有 interrupt 块（HITL 从 ask_params 切到 confirm 时避免堆叠） */
  setAssistantInterruptBlock: (
    messageId: string,
    payload: Extract<AiMessage["blocks"][0], { type: "interrupt" }>["payload"],
  ) => void;
  /** 用户批准/拒绝或 HITL 已结束后移除 interrupt 块 */
  clearAssistantInterruptBlock: (messageId: string) => void;
  /** 将 interrupt 块标为终态（保留卡片展示，不可再交互） */
  resolveAssistantInterruptBlock: (
    messageId: string,
    resolution: "rejected" | "aborted" | "superseded",
  ) => void;
  completeAssistantToolCall: (
    messageId: string,
    tool: string,
    result?: string,
    finalStatus?: "done" | "error" | "awaiting_hitl" | "cancelled",
    toolCallId?: string,
  ) => void;
  /** HITL 中断：仅标记 running 工具为 awaiting_hitl，不覆盖已 error/done 的历史块 */
  markAssistantToolAwaitingHitl: (messageId: string, tool: string, toolCallId?: string) => void;
  /** HITL 已批准/已提交：将 awaiting_hitl 工具块恢复为 running（续跑等待 SSE 前） */
  markAssistantToolRunning: (messageId: string, tool: string, toolCallId?: string) => void;
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
    (set, get) => ({
      sidebarOpen: false,
      sidebarWidth: 360,
      currentThreadId: uuidv4(),
      sessions: [],
      messages: [],
      isStreaming: false,
      streamingByThread: {},
      threadSnapshots: {},
      isLoadingHistory: false,
      selectedModelId: AUTO_AGENT_MODEL_ID,
      runMode: DEFAULT_RUN_MODE,
      planFirst: false,
      selectedVoiceprintId: null,
      voiceprintEnabled: false,
      voiceCorrectionHighlightEnabled: false,
      pendingInterrupt: null,
      alarmDetailRecord: null,
      activeWorkspace: null,
      activeWorkspaceSourceId: null,

      setSidebarOpen: (open) => set({ sidebarOpen: open }),
      setSidebarWidth: (width) => set({ sidebarWidth: Math.max(280, Math.round(width)) }),
      toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
      openWorkspacePanel: (content, sourceMessageId) =>
        set({
          activeWorkspace: content,
          activeWorkspaceSourceId: sourceMessageId ?? null,
          sidebarOpen: true,
        }),
      clearActiveWorkspace: () => set({ activeWorkspace: null, activeWorkspaceSourceId: null }),

      setSelectedModelId: (id) => set({ selectedModelId: id }),
      setRunMode: (mode) => set({ runMode: mode }),
      setPlanFirst: (enabled) => set({ planFirst: Boolean(enabled) }),
      setSelectedVoiceprintId: (id) => set({ selectedVoiceprintId: id }),
      setVoiceprintEnabled: (enabled) => set({ voiceprintEnabled: enabled }),
      setVoiceCorrectionHighlightEnabled: (enabled) =>
        set({ voiceCorrectionHighlightEnabled: enabled }),

      createNewSession: () => {
        const threadId = uuidv4();
        set((s) => {
          const snapshots = { ...s.threadSnapshots };
          snapshots[s.currentThreadId] = {
            messages: s.messages,
            pendingInterrupt: s.pendingInterrupt,
          };
          return {
            threadSnapshots: snapshots,
            currentThreadId: threadId,
            messages: [],
            pendingInterrupt: null,
            isStreaming: Boolean(s.streamingByThread[threadId]),
            isLoadingHistory: false,
            activeWorkspace: null,
            activeWorkspaceSourceId: null,
          };
        });
        return threadId;
      },

      switchSession: (threadId) =>
        set((s) => {
          if (threadId === s.currentThreadId) return {};
          const snapshots = { ...s.threadSnapshots };
          snapshots[s.currentThreadId] = {
            messages: s.messages,
            pendingInterrupt: s.pendingInterrupt,
          };
          const target = snapshots[threadId];
          const nextMessages = target?.messages ?? [];
          const pinned = latestPinnedWorkspace(nextMessages);
          const hasCache =
            Boolean(target && target.messages.length > 0) || Boolean(s.streamingByThread[threadId]);
          return {
            threadSnapshots: snapshots,
            currentThreadId: threadId,
            messages: nextMessages,
            pendingInterrupt: target?.pendingInterrupt ?? null,
            isStreaming: Boolean(s.streamingByThread[threadId]),
            // 有快照或后台仍在流：不拉历史，避免冲掉进行中气泡
            isLoadingHistory: !hasCache,
            activeWorkspace: pinned?.content ?? null,
            activeWorkspaceSourceId: pinned?.messageId ?? null,
            // 切会话时若有可展示结果则保持侧栏偏好；无结果则关闭避免空壳
            sidebarOpen: pinned ? s.sidebarOpen : false,
          };
        }),

      isThreadStreaming: (threadId) => {
        const s = get();
        const tid = threadId ?? s.currentThreadId;
        return Boolean(s.streamingByThread[tid]);
      },

      hasThreadSnapshot: (threadId) => {
        const s = get();
        const snap = s.threadSnapshots[threadId];
        return Boolean((snap && snap.messages.length > 0) || s.streamingByThread[threadId]);
      },

      clearThreadSnapshot: (threadId) =>
        set((s) => {
          if (!(threadId in s.threadSnapshots) && !(threadId in s.streamingByThread)) {
            return {};
          }
          const threadSnapshots = { ...s.threadSnapshots };
          delete threadSnapshots[threadId];
          const streamingByThread = { ...s.streamingByThread };
          delete streamingByThread[threadId];
          return {
            threadSnapshots,
            streamingByThread,
            isStreaming:
              threadId === s.currentThreadId
                ? false
                : Boolean(streamingByThread[s.currentThreadId]),
          };
        }),

      setSessions: (sessions) => set({ sessions }),

      touchSession: (threadId, title) =>
        set((s) => {
          const trimmed = title.trim();
          const normalized = trimmed.slice(0, 20) + (trimmed.length > 20 ? "…" : "");
          const now = new Date().toISOString();
          const prev = s.sessions.find((x) => x.thread_id === threadId);
          const rest = s.sessions.filter((x) => x.thread_id !== threadId);
          return {
            sessions: [
              {
                thread_id: threadId,
                title: normalized || prev?.title || "新会话",
                updated_at: now,
                created_at: prev?.created_at ?? now,
              },
              ...rest,
            ],
          };
        }),

      setMessages: (messages) =>
        set((s) => {
          const tid = getMessageWriteThreadId(s.currentThreadId);
          const pinned = latestPinnedWorkspace(messages);
          const committed = commitThreadMessages(s, tid, messages);
          return {
            ...committed,
            activeWorkspace: pinned?.content ?? null,
            activeWorkspaceSourceId: pinned?.messageId ?? null,
            // 历史加载后有结果则保留侧栏偏好；无结果关闭空壳
            sidebarOpen: pinned ? s.sidebarOpen : false,
          };
        }),

      setLoadingHistory: (loading) => set({ isLoadingHistory: loading }),

      addUserMessage: (content) => {
        const id = uuidv4();
        const msg: AiMessage = {
          id,
          role: "user",
          blocks: [{ type: "text", content }],
          createdAt: Date.now(),
        };
        set((s) => {
          const { threadId, messages } = baseMessagesForWrite(s);
          return commitThreadMessages(s, threadId, [...messages, msg]);
        });
        return id;
      },

      appendAssistantBlock: (messageId, block) =>
        set((s) => {
          const { threadId, messages: base } = baseMessagesForWrite(s);
          return commitThreadMessages(
            s,
            threadId,
            base.map((m) => {
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
          );
        }),

      setAssistantInterruptBlock: (messageId, payload) =>
        set((s) => {
          const { threadId, messages: base } = baseMessagesForWrite(s);
          return commitThreadMessages(
            s,
            threadId,
            base.map((m) => {
              if (m.id !== messageId) return m;
              const withoutInterrupt = m.blocks.filter((b) => b.type !== "interrupt");
              return {
                ...m,
                blocks: [...withoutInterrupt, { type: "interrupt", payload }],
              };
            }),
          );
        }),

      clearAssistantInterruptBlock: (messageId) =>
        set((s) => {
          const { threadId, messages: base } = baseMessagesForWrite(s);
          return commitThreadMessages(
            s,
            threadId,
            base.map((m) =>
              m.id === messageId
                ? { ...m, blocks: m.blocks.filter((b) => b.type !== "interrupt") }
                : m,
            ),
          );
        }),

      resolveAssistantInterruptBlock: (messageId, resolution) =>
        set((s) => {
          const { threadId, messages: base } = baseMessagesForWrite(s);
          return commitThreadMessages(
            s,
            threadId,
            base.map((m) => {
              if (m.id !== messageId) return m;
              return {
                ...m,
                blocks: m.blocks.map((b) =>
                  b.type === "interrupt" && !b.resolution ? { ...b, resolution } : b,
                ),
              };
            }),
          );
        }),

      completeAssistantToolCall: (messageId, tool, result, finalStatus = "done", toolCallId) =>
        set((s) => {
          const { threadId, messages: base } = baseMessagesForWrite(s);
          return commitThreadMessages(
            s,
            threadId,
            base.map((m) => {
              if (m.id !== messageId) return m;
              const blocks = [...m.blocks];
              const i = findToolCallBlockIndex(blocks, tool, toolCallId, [
                "running",
                "error",
                "awaiting_hitl",
              ]);
              if (i >= 0) {
                const b = blocks[i];
                if (b.type === "tool_call") {
                  blocks[i] = {
                    ...b,
                    status: finalStatus,
                    result,
                    toolCallId: b.toolCallId ?? toolCallId,
                  };
                }
              }
              return { ...m, blocks };
            }),
          );
        }),

      markAssistantToolAwaitingHitl: (messageId, tool, toolCallId) =>
        set((s) => {
          const { threadId, messages: base } = baseMessagesForWrite(s);
          return commitThreadMessages(
            s,
            threadId,
            base.map((m) => {
              if (m.id !== messageId) return m;
              const blocks = [...m.blocks];
              const i = findToolCallBlockIndex(blocks, tool, toolCallId, ["running"]);
              if (i >= 0) {
                const b = blocks[i];
                if (b.type === "tool_call") {
                  blocks[i] = {
                    ...b,
                    status: "awaiting_hitl",
                    toolCallId: b.toolCallId ?? toolCallId,
                  };
                }
              } else {
                blocks.push({
                  type: "tool_call",
                  tool,
                  status: "awaiting_hitl",
                  args: {},
                  toolCallId,
                });
              }
              return { ...m, blocks };
            }),
          );
        }),

      markAssistantToolRunning: (messageId, tool, toolCallId) =>
        set((s) => {
          const { threadId, messages: base } = baseMessagesForWrite(s);
          return commitThreadMessages(
            s,
            threadId,
            base.map((m) => {
              if (m.id !== messageId) return m;
              const blocks = [...m.blocks];
              const i = findToolCallBlockIndex(blocks, tool, toolCallId, [
                "awaiting_hitl",
                "running",
              ]);
              if (i >= 0) {
                const b = blocks[i];
                if (b.type === "tool_call") {
                  blocks[i] = {
                    ...b,
                    status: "running",
                    result: undefined,
                    toolCallId: b.toolCallId ?? toolCallId,
                  };
                }
              } else {
                blocks.push({
                  type: "tool_call",
                  tool,
                  status: "running",
                  args: {},
                  toolCallId,
                });
              }
              return { ...m, blocks };
            }),
          );
        }),

      completeClientAction: (messageId, status) =>
        set((s) => {
          const { threadId, messages: base } = baseMessagesForWrite(s);
          return commitThreadMessages(
            s,
            threadId,
            base.map((m) => {
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
          );
        }),

      updateAssistantText: (messageId, delta, options) =>
        set((s) => {
          const { threadId, messages: base } = baseMessagesForWrite(s);
          return commitThreadMessages(
            s,
            threadId,
            base.map((m) => {
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
          );
        }),

      finalizeAssistantMessage: (messageId) =>
        set((s) => {
          const { threadId, messages: base } = baseMessagesForWrite(s);
          return commitThreadMessages(
            s,
            threadId,
            base.map((m) => (m.id === messageId ? { ...m, streaming: false } : m)),
          );
        }),

      patchAssistantMessage: (messageId, patch) =>
        set((s) => {
          const { threadId, messages: base, isCurrent } = baseMessagesForWrite(s);
          const nextMessages = base.map((m) => (m.id === messageId ? { ...m, ...patch } : m));
          const committed = commitThreadMessages(s, threadId, nextMessages);
          const ws = patch.workspaceContent;
          if (isCurrent && ws && isPinnedWorkspaceKind(ws)) {
            return {
              ...committed,
              activeWorkspace: ws,
              activeWorkspaceSourceId: messageId,
              sidebarOpen: true,
            };
          }
          return committed;
        }),

      appendAssistantTraceEvent: (messageId, event) =>
        set((s) => {
          const { threadId, messages: base } = baseMessagesForWrite(s);
          return commitThreadMessages(
            s,
            threadId,
            base.map((m) =>
              m.id === messageId ? { ...m, traceEvents: [...(m.traceEvents ?? []), event] } : m,
            ),
          );
        }),

      updateAssistantPlanStep: (messageId, stepId, status, patch) =>
        set((s) => {
          const { threadId, messages: base } = baseMessagesForWrite(s);
          return commitThreadMessages(
            s,
            threadId,
            base.map((m) => {
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
          );
        }),

      syncAssistantPlanStepFromToolEnd: (messageId, tool, status, patch) =>
        set((s) => {
          const { threadId, messages: base } = baseMessagesForWrite(s);
          return commitThreadMessages(
            s,
            threadId,
            base.map((m) => {
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
          );
        }),

      reconcileAssistantPlanStepsFromBlocks: (messageId) =>
        set((s) => {
          const { threadId, messages: base } = baseMessagesForWrite(s);
          return commitThreadMessages(
            s,
            threadId,
            base.map((m) => {
              if (m.id !== messageId || !m.planSteps?.length) return m;
              const nextSteps = reconcilePlanStepsWithToolBlocks(m.planSteps, m.blocks);
              if (nextSteps === m.planSteps) return m;
              return { ...m, planSteps: nextSteps };
            }),
          );
        }),

      setStreaming: (streaming) =>
        set((s) => {
          const tid = getMessageWriteThreadId(s.currentThreadId);
          const streamingByThread = { ...s.streamingByThread };
          if (streaming) {
            streamingByThread[tid] = true;
          } else {
            delete streamingByThread[tid];
          }
          return {
            streamingByThread,
            isStreaming: Boolean(streamingByThread[s.currentThreadId]),
          };
        }),
      setPendingInterrupt: (payload) =>
        set((s) => {
          const tid = getMessageWriteThreadId(s.currentThreadId);
          const isCurrent = tid === s.currentThreadId;
          const prev = s.threadSnapshots[tid];
          const messages = isCurrent ? s.messages : (prev?.messages ?? []);
          const threadSnapshots = {
            ...s.threadSnapshots,
            [tid]: { messages, pendingInterrupt: payload },
          };
          if (isCurrent) {
            return { pendingInterrupt: payload, threadSnapshots };
          }
          return { threadSnapshots };
        }),
      setAlarmDetailRecord: (record) => set({ alarmDetailRecord: record }),
    }),
    {
      name: "ai-assistant-store",
      partialize: (s) => ({
        selectedModelId: s.selectedModelId,
        runMode: s.runMode,
        planFirst: s.planFirst,
        selectedVoiceprintId: s.selectedVoiceprintId,
        voiceCorrectionHighlightEnabled: s.voiceCorrectionHighlightEnabled,
        sidebarOpen: s.sidebarOpen,
        sidebarWidth: s.sidebarWidth,
      }),
      merge: (persisted, current) => {
        const p = (persisted ?? {}) as Partial<AiAssistantState>;
        return {
          ...current,
          ...p,
          selectedModelId: resolvePersistedModelId(p.selectedModelId),
          runMode: resolvePersistedRunMode(p.runMode),
          planFirst: Boolean(p.planFirst),
          selectedVoiceprintId:
            typeof p.selectedVoiceprintId === "string" ? p.selectedVoiceprintId : null,
          voiceCorrectionHighlightEnabled: Boolean(p.voiceCorrectionHighlightEnabled),
        };
      },
    },
  ),
);

/** 读取当前写入目标 thread 的消息（配合 runWithMessageThread） */
export function getWriteTargetMessages(
  state: {
    currentThreadId: string;
    messages: AiMessage[];
    threadSnapshots: Record<string, ThreadSnapshot>;
  } = useAiAssistantStore.getState(),
): AiMessage[] {
  return baseMessagesForWrite(state).messages;
}

/** 读取当前写入目标 thread 的 pendingInterrupt */
export function getWriteTargetPendingInterrupt(
  state: {
    currentThreadId: string;
    pendingInterrupt: HitlPayload | null;
    threadSnapshots: Record<string, ThreadSnapshot>;
  } = useAiAssistantStore.getState(),
): HitlPayload | null {
  const tid = getMessageWriteThreadId(state.currentThreadId);
  if (tid === state.currentThreadId) return state.pendingInterrupt;
  return state.threadSnapshots[tid]?.pendingInterrupt ?? null;
}

/** 更新写入目标 thread 的消息列表（绕过仅改当前 UI 的 setState） */
export function updateWriteTargetMessages(
  updater: (messages: AiMessage[]) => AiMessage[],
  extra?: {
    pendingInterrupt?: HitlPayload | null;
    isStreaming?: boolean;
    streamingByThread?: Record<string, boolean>;
    isLoadingHistory?: boolean;
  },
): void {
  useAiAssistantStore.setState((s) => {
    const { threadId, messages } = baseMessagesForWrite(s);
    return commitThreadMessages(s, threadId, updater(messages), extra);
  });
}
