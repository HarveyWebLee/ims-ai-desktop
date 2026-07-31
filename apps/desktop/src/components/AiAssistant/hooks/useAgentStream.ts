/**
 * Agent SSE 流式对话 Hook
 */
import { useCallback, useRef } from "react";
import { useIntl } from "react-intl";
import { message } from "@/antd/feedback";
import { v4 as uuidv4 } from "uuid";
import * as AgentController from "@/services/AgentController";
import { executeClientAction } from "../ClientToolExecutor";
import { useAiAssistantStore } from "../store";
import type { AgentSseHandler } from "../types";
import { workspaceFromToolEnd, resolveWorkspaceFromMessage } from "../utils/workspaceFromTool";
import {
  parseToolResultOk,
  parseToolResultUserCancelled,
  parseToolResultShortSummary,
  parseToolResultAutoRetry,
} from "../utils/parseToolResult";
import type { FlowDocumentJSON } from "@/components/BpmnFlowgram";
import { mapHistoryToMessages } from "../utils/mapHistoryMessages";
import {
  applyBpmnSnapshotToMessages,
  enrichMessagesWithTraceRuns,
} from "../utils/enrichHistoryWithTrace";
import { formatAgentErrorMessage, formatAgentErrorToast } from "../utils/formatAgentError";
import { agentDebugLog, summarizeAssistantMessage } from "../utils/agentDebugLog";
import { assistantMessageHasVisibleContent } from "../chatCardUtils";
import {
  findPendingInterruptFromMessages,
  shouldPreserveHitlOnStreamDone,
} from "../utils/hitlInterruptUtils";
import { enrichPlanStepCatalogMeta } from "@/components/BpmnFlowgram/utils/plan-tool-catalog";

export function useAgentStream() {
  const intl = useIntl();
  const abortRef = useRef<AbortController | null>(null);
  const pendingToolArgsRef = useRef<Record<string, Record<string, unknown>>>({});
  /** 本轮 download_file 已触发的浏览器下载次数（多文件导出进度提示） */
  const exportDownloadCountRef = useRef(0);

  const {
    currentThreadId,
    selectedModelId,
    setStreaming,
    setMessages,
    appendAssistantBlock,
    setAssistantInterruptBlock,
    clearAssistantInterruptBlock,
    completeAssistantToolCall,
    markAssistantToolAwaitingHitl,
    markAssistantToolRunning,
    completeClientAction,
    updateAssistantText,
    finalizeAssistantMessage,
    setPendingInterrupt,
    setSessions,
    patchAssistantMessage,
    appendAssistantTraceEvent,
    updateAssistantPlanStep,
    syncAssistantPlanStepFromToolEnd,
    reconcileAssistantPlanStepsFromBlocks,
  } = useAiAssistantStore();

  const loadSessions = useCallback(async () => {
    try {
      const { sessions } = await AgentController.getSessions();
      setSessions(sessions);
    } catch {
      // 后端未启动时静默
    }
  }, [setSessions]);

  /** 创建 SSE 事件处理器（绑定到指定 assistant 消息） */
  const createStreamHandlers = useCallback(
    (assistantId: string): AgentSseHandler => ({
      onTextDelta: (delta) => updateAssistantText(assistantId, delta),
      onToolStart: (tool, args, meta) => {
        agentDebugLog("sse.tool_start", {
          assistantId: assistantId.slice(0, 8),
          tool,
        });
        if (tool === "download_file") {
          exportDownloadCountRef.current = 0;
        }
        pendingToolArgsRef.current[tool] = args;
        appendAssistantBlock(assistantId, {
          type: "tool_call",
          tool,
          args,
          status: "running",
          retry: meta?.retry,
          attempt: meta?.attempt,
        });
        // 同步 Plan 步骤：running + 入参 + 开始时间
        const planMsg = useAiAssistantStore.getState().messages.find((m) => m.id === assistantId);
        const runningStep = planMsg?.planSteps?.find(
          (s) =>
            s.tool === tool &&
            (s.status === "pending" ||
              s.status === "awaiting_confirm" ||
              s.status === "awaiting_hitl" ||
              s.status === "running"),
        );
        if (runningStep) {
          const enriched = enrichPlanStepCatalogMeta({
            ...runningStep,
            tool,
          });
          updateAssistantPlanStep(assistantId, runningStep.id, "running", {
            args: args && typeof args === "object" ? (args as Record<string, unknown>) : undefined,
            startedAt: runningStep.startedAt ?? Date.now(),
            errorMessage: undefined,
            resultSummary: undefined,
            side: enriched.side,
            riskLevel: enriched.riskLevel,
            retry: Boolean(meta?.retry),
            attempt: typeof meta?.attempt === "number" ? meta.attempt : undefined,
          });
        }
      },
      onToolEnd: (tool, result, meta) => {
        agentDebugLog("sse.tool_end", {
          assistantId: assistantId.slice(0, 8),
          tool,
          userCancelled: parseToolResultUserCancelled(result),
        });
        if (tool === "download_file" && exportDownloadCountRef.current > 0) {
          message.destroy();
          message.success(
            intl.formatMessage(
              { id: "aiAssistant.card.action.downloadBatchDone" },
              { count: exportDownloadCountRef.current },
            ),
          );
          exportDownloadCountRef.current = 0;
        }
        const args = pendingToolArgsRef.current[tool];
        delete pendingToolArgsRef.current[tool];
        const userCancelled = parseToolResultUserCancelled(result);
        const ok = userCancelled ? false : parseToolResultOk(result);
        const shortSummary = parseToolResultShortSummary(result);
        const autoRetry = parseToolResultAutoRetry(result);
        completeAssistantToolCall(
          assistantId,
          tool,
          result,
          userCancelled ? "cancelled" : ok ? "done" : "error",
        );
        syncAssistantPlanStepFromToolEnd(
          assistantId,
          tool,
          userCancelled ? "skipped" : ok ? "done" : "error",
          {
            args: args && typeof args === "object" ? (args as Record<string, unknown>) : undefined,
            endedAt: Date.now(),
            resultSummary: ok && shortSummary ? shortSummary : undefined,
            errorMessage: !ok && !userCancelled ? shortSummary || "工具执行失败" : undefined,
            ...(() => {
              const metaEnriched = enrichPlanStepCatalogMeta({ tool });
              return {
                side: metaEnriched.side,
                riskLevel: metaEnriched.riskLevel,
              };
            })(),
            retry: Boolean(meta?.retry) || Boolean(autoRetry),
            attempt: typeof meta?.attempt === "number" ? meta.attempt : undefined,
            autoRetryFrom: autoRetry?.from,
            autoRetryTo: autoRetry?.to,
            hitl: userCancelled ? { resolution: "cancelled" as const } : undefined,
          },
        );
        reconcileAssistantPlanStepsFromBlocks(assistantId);
        const workspace = workspaceFromToolEnd(tool, result, args);
        // device_command 成败都展示结构化卡；其余 Workspace 仍仅成功写入
        if (workspace && (workspace.kind === "device_command" || ok)) {
          patchAssistantMessage(assistantId, { workspaceContent: workspace });
        }
        void meta;
      },
      onInterrupt: (payload) => {
        agentDebugLog("sse.interrupt", {
          assistantId: assistantId.slice(0, 8),
          type: payload.type,
          tool: payload.tool,
        });
        setPendingInterrupt(payload);
        setAssistantInterruptBlock(assistantId, payload);
        // plan_confirm：整份计划待批准，步骤标记 awaiting_confirm
        if (payload.type === "plan_confirm") {
          const msg = useAiAssistantStore.getState().messages.find((m) => m.id === assistantId);
          const steps = msg?.planSteps?.length ? msg.planSteps : (payload.steps ?? []);
          steps.forEach((step) => {
            const enriched = enrichPlanStepCatalogMeta(step);
            updateAssistantPlanStep(assistantId, step.id, "awaiting_confirm", {
              side: enriched.side,
              riskLevel: enriched.riskLevel,
              hitl: {
                type: "plan_confirm",
                message:
                  typeof payload.message === "string"
                    ? payload.message.trim().slice(0, 200)
                    : undefined,
              },
            });
          });
          if (!msg?.planSteps?.length && payload.steps?.length) {
            patchAssistantMessage(assistantId, {
              planSteps: payload.steps.map((s) => {
                const enriched = enrichPlanStepCatalogMeta(s);
                return {
                  ...enriched,
                  status: "awaiting_confirm" as const,
                  hitl: {
                    type: "plan_confirm" as const,
                    message:
                      typeof payload.message === "string"
                        ? payload.message.trim().slice(0, 200)
                        : undefined,
                  },
                };
              }),
              planGraph: payload.graph ?? null,
            });
          } else if (payload.graph) {
            patchAssistantMessage(assistantId, {
              planGraph: payload.graph,
            });
          }
          return;
        }
        // HITL 中断并非工具失败：将关联工具与计划步骤标记为等待人工介入
        const msgBefore = useAiAssistantStore.getState().messages.find((m) => m.id === assistantId);
        // 导航等 HITL 到来时，将同轮误触发的 export running 块标为 skipped
        if (msgBefore) {
          for (const block of msgBefore.blocks) {
            if (
              block.type === "tool_call" &&
              block.tool !== payload.tool &&
              block.status === "running" &&
              block.tool === "download_file"
            ) {
              completeAssistantToolCall(assistantId, block.tool, undefined, "cancelled");
              const staleStep = msgBefore.planSteps?.find(
                (s) => s.tool === block.tool && (s.status === "running" || s.status === "pending"),
              );
              if (staleStep) {
                updateAssistantPlanStep(assistantId, staleStep.id, "skipped");
              }
            }
          }
        }
        // 顺序 ReAct：后续工具 HITL 说明前序 running 步已完成
        if (msgBefore?.planSteps?.length && payload.tool) {
          for (const step of msgBefore.planSteps) {
            if (
              step.tool &&
              step.tool !== payload.tool &&
              step.status === "running" &&
              step.tool !== "download_file"
            ) {
              updateAssistantPlanStep(assistantId, step.id, "done");
            }
          }
          for (const block of msgBefore.blocks) {
            if (
              block.type === "tool_call" &&
              block.tool !== payload.tool &&
              block.status === "running" &&
              block.tool !== "download_file"
            ) {
              completeAssistantToolCall(assistantId, block.tool, undefined, "done");
            }
          }
        }
        markAssistantToolAwaitingHitl(assistantId, payload.tool);
        const msg = useAiAssistantStore.getState().messages.find((m) => m.id === assistantId);
        const hitlStep = msg?.planSteps?.find(
          (s) => s.tool === payload.tool && (s.status === "running" || s.status === "error"),
        );
        if (hitlStep) {
          updateAssistantPlanStep(assistantId, hitlStep.id, "awaiting_hitl", {
            resultSummary:
              typeof payload.message === "string" && payload.message.trim()
                ? payload.message.trim().slice(0, 200)
                : intl.formatMessage({
                    id: "aiAssistant.card.tool.awaitingHitl",
                  }),
            hitl: {
              type: payload.type,
              message:
                typeof payload.message === "string"
                  ? payload.message.trim().slice(0, 200)
                  : undefined,
            },
            ...(() => {
              const meta = enrichPlanStepCatalogMeta({
                tool: payload.tool,
              });
              return { side: meta.side, riskLevel: meta.riskLevel };
            })(),
          });
        }
      },
      onClientAction: async (action) => {
        appendAssistantBlock(assistantId, {
          type: "client_action",
          action,
          status: "pending",
        });
        if (action.action === "download") {
          exportDownloadCountRef.current += 1;
          const n = exportDownloadCountRef.current;
          message.loading(
            intl.formatMessage({ id: "aiAssistant.card.action.downloadProgress" }, { current: n }),
            0,
          );
        }
        const result = await executeClientAction(action);
        if (action.action === "download") {
          message.destroy();
        }
        completeClientAction(assistantId, result.ok ? "done" : "error");
        if (!result.ok) {
          message.error(result.error);
        }
      },
      onPlan: (payload) => {
        const normalized = Array.isArray(payload) ? { steps: payload } : payload;
        agentDebugLog("sse.plan", {
          assistantId: assistantId.slice(0, 8),
          stepTools: normalized.steps?.map((s) => s.tool),
          stepStatuses: normalized.steps?.map((s) => s.status),
        });
        patchAssistantMessage(assistantId, {
          planSteps: (normalized.steps ?? []).map((s) => enrichPlanStepCatalogMeta(s)),
          planGraph: normalized.graph ?? null,
          planFlowDocument: (normalized.flow_document as FlowDocumentJSON | undefined) ?? null,
        });
      },
      onPlanUpdate: (update) => {
        const stepId = String(update.step_id || update.node_id || "");
        updateAssistantPlanStep(assistantId, stepId, update.status, {
          ...(update.tool ? { tool: update.tool } : {}),
          ...(update.skipReason ? { skipReason: update.skipReason } : {}),
          ...(update.matchedBranchKey ? { matchedBranchKey: update.matchedBranchKey } : {}),
          ...(update.node_id ? { nodeId: String(update.node_id) } : {}),
          ...(update.node_type ? { nodeType: update.node_type } : {}),
          ...(update.label ? { label: update.label } : {}),
        });
      },
      onReplan: ({ reason, steps }) => {
        patchAssistantMessage(assistantId, {
          planSteps: steps,
          planReplanReason: reason,
          planGraph: null,
          planFlowDocument: null,
        });
      },
      onTrace: (event) => {
        appendAssistantTraceEvent(assistantId, event);
      },
      onDone: () => {
        // 兜底：interrupt 块已写入但 pendingInterrupt 未同步时，从消息块恢复
        const latest = useAiAssistantStore.getState().messages.find((m) => m.id === assistantId);
        const hitlBlock = latest?.blocks.find((b) => b.type === "interrupt");
        if (hitlBlock?.type === "interrupt" && latest) {
          const payload = hitlBlock.payload;
          const stillAwaitingHitl = shouldPreserveHitlOnStreamDone(payload, latest.blocks);
          if (stillAwaitingHitl && !useAiAssistantStore.getState().pendingInterrupt) {
            setPendingInterrupt(payload);
          } else if (!stillAwaitingHitl) {
            // 工具已结束（含用户取消/失败）时清除残留 interrupt，避免确认卡常驻
            useAiAssistantStore.getState().clearAssistantInterruptBlock(assistantId);
          }
        } else if (!useAiAssistantStore.getState().pendingInterrupt) {
          void hitlBlock;
        }
        // 兜底：tool_end 已写入 blocks 但 workspaceContent 未同步时补全「查看结果」
        const forWorkspace = useAiAssistantStore
          .getState()
          .messages.find((m) => m.id === assistantId);
        if (forWorkspace && !forWorkspace.workspaceContent) {
          const workspace = resolveWorkspaceFromMessage(forWorkspace);
          if (workspace?.ok) {
            patchAssistantMessage(assistantId, { workspaceContent: workspace });
          }
        }
        // 工具仍 running 且无 interrupt 块：标记为 awaiting_hitl（避免永久转圈）
        if (latest) {
          for (const block of latest.blocks) {
            if (block.type === "tool_call" && block.status === "running") {
              completeAssistantToolCall(assistantId, block.tool, undefined, "awaiting_hitl");
            }
          }
        }
        reconcileAssistantPlanStepsFromBlocks(assistantId);
        finalizeAssistantMessage(assistantId);
        loadSessions();
      },
      onError: (code, msg, data) => {
        agentDebugLog("sse.error", {
          assistantId: assistantId.slice(0, 8),
          code,
          msg,
        });
        // 流异常中断时，将仍 running 的工具块标为失败，避免侧栏永久转圈
        const msgState = useAiAssistantStore.getState().messages.find((m) => m.id === assistantId);
        if (msgState) {
          for (const block of msgState.blocks) {
            if (block.type === "tool_call" && block.status === "running") {
              completeAssistantToolCall(assistantId, block.tool, undefined, "error");
            }
          }
        }
        const toast = formatAgentErrorToast(intl, msg, data);
        const detail = formatAgentErrorMessage(intl, msg, data);
        message.error(toast, 6);
        updateAssistantText(assistantId, `\n\n⚠️ ${detail.replace(/\n/g, "\n\n")}`);
        finalizeAssistantMessage(assistantId);
        void code;
      },
    }),
    [
      appendAssistantBlock,
      setAssistantInterruptBlock,
      appendAssistantTraceEvent,
      completeAssistantToolCall,
      markAssistantToolAwaitingHitl,
      completeClientAction,
      finalizeAssistantMessage,
      loadSessions,
      patchAssistantMessage,
      setPendingInterrupt,
      updateAssistantPlanStep,
      syncAssistantPlanStepFromToolEnd,
      reconcileAssistantPlanStepsFromBlocks,
      updateAssistantText,
      intl,
    ],
  );

  const loadThreadHistory = useCallback(
    async (threadId: string) => {
      const { setLoadingHistory } = useAiAssistantStore.getState();
      setLoadingHistory(true);
      try {
        const { messages: history, bpmn_snapshot: bpmnSnapshot } =
          await AgentController.getThreadState(threadId);
        // 快速连续切换时，丢弃过期请求结果
        if (useAiAssistantStore.getState().currentThreadId !== threadId) return;

        let mapped = mapHistoryToMessages(history);
        const restoredPending = findPendingInterruptFromMessages(mapped);
        setPendingInterrupt(restoredPending);

        try {
          const { runs } = await AgentController.getThreadTrace(threadId);
          if (runs?.length) {
            mapped = enrichMessagesWithTraceRuns(mapped, runs);
          }
        } catch {
          // trace 接口可选
        }

        // BPMN 快照挂到含 plan 的助手消息（AC-26 多轮增强）
        if (bpmnSnapshot) {
          mapped = applyBpmnSnapshotToMessages(mapped, bpmnSnapshot);
        }

        if (useAiAssistantStore.getState().currentThreadId !== threadId) return;
        setMessages(mapped);
      } catch {
        if (useAiAssistantStore.getState().currentThreadId !== threadId) return;
        setMessages([]);
      } finally {
        if (useAiAssistantStore.getState().currentThreadId === threadId) {
          setLoadingHistory(false);
        }
      }
    },
    [setMessages, setPendingInterrupt],
  );

  const appendAssistantPlaceholder = useCallback(() => {
    const assistantId = uuidv4();
    useAiAssistantStore.setState((s) => ({
      messages: [
        ...s.messages,
        {
          id: assistantId,
          role: "assistant" as const,
          blocks: [],
          createdAt: Date.now(),
          streaming: true,
          traceEvents: [],
          planSteps: [],
        },
      ],
    }));
    return assistantId;
  }, []);

  const sendMessage = useCallback(
    async (content: string) => {
      if (!content.trim()) return;

      const priorUserMessages = useAiAssistantStore
        .getState()
        .messages.filter((m) => m.role === "user")
        .slice(-3)
        .map((m) =>
          m.blocks
            .filter((b) => b.type === "text")
            .map((b) => (b as { type: "text"; content: string }).content)
            .join(""),
        )
        .filter(Boolean);

      const assistantId = uuidv4();
      const userMsgId = uuidv4();
      useAiAssistantStore.setState((s) => ({
        pendingInterrupt: null,
        isStreaming: true,
        messages: [
          ...s.messages,
          {
            id: userMsgId,
            role: "user" as const,
            blocks: [{ type: "text" as const, content: content.trim() }],
            createdAt: Date.now(),
          },
          {
            id: assistantId,
            role: "assistant" as const,
            blocks: [],
            createdAt: Date.now(),
            streaming: true,
            traceEvents: [],
            planSteps: [],
          },
        ],
      }));
      agentDebugLog("chat.send", {
        threadId: currentThreadId.slice(0, 12),
        assistantId: assistantId.slice(0, 8),
        messagePreview: content.trim().slice(0, 80),
        priorMessages: useAiAssistantStore
          .getState()
          .messages.filter((m) => m.role === "assistant")
          .map(summarizeAssistantMessage),
      });

      abortRef.current?.abort();
      const abortController = new AbortController();
      abortRef.current = abortController;
      let abortedByUser = false;
      abortController.signal.addEventListener(
        "abort",
        () => {
          abortedByUser = true;
        },
        { once: true },
      );

      try {
        await AgentController.chatStream(
          {
            thread_id: currentThreadId,
            message: content.trim(),
            model_id: selectedModelId,
            // 桌面端无宿主路由，固定根路径供后端 client_action 等上下文使用
            metadata: { current_path: "/" },
            recent_user_messages: priorUserMessages,
          },
          createStreamHandlers(assistantId),
          abortController.signal,
        );
      } catch (err) {
        if ((err as Error).name !== "AbortError") {
          message.error((err as Error).message || "发送失败");
        }
      } finally {
        setStreaming(false);
        const latest = useAiAssistantStore.getState().messages.find((m) => m.id === assistantId);
        // 被新消息 abort 且无内容：移除空白助手占位，避免多条兜底文案
        if (abortedByUser && latest && !assistantMessageHasVisibleContent(latest)) {
          useAiAssistantStore.setState((s) => ({
            messages: s.messages.filter((m) => m.id !== assistantId),
          }));
        } else if (!abortedByUser && latest && !assistantMessageHasVisibleContent(latest)) {
          updateAssistantText(
            assistantId,
            intl.formatMessage({ id: "aiAssistant.emptyResponse" }),
            { markStreaming: false },
          );
          agentDebugLog("chat.empty_response_fallback", {
            assistantId: assistantId.slice(0, 8),
          });
        }
        finalizeAssistantMessage(assistantId);
      }
    },
    [
      createStreamHandlers,
      currentThreadId,
      finalizeAssistantMessage,
      selectedModelId,
      setStreaming,
      intl,
      updateAssistantText,
    ],
  );

  const submitHitlResume = useCallback(
    async (values: Record<string, unknown>) => {
      setStreaming(true);

      let sourceMessageId: string | null = null;
      let hitlTool: string | undefined;
      const msgs = useAiAssistantStore.getState().messages;
      for (let i = msgs.length - 1; i >= 0; i -= 1) {
        const m = msgs[i];
        const interruptBlock = m.blocks.find((b) => b.type === "interrupt");
        if (m.role === "assistant" && interruptBlock?.type === "interrupt") {
          sourceMessageId = m.id;
          hitlTool = interruptBlock.payload.tool;
          const hitlStep = m.planSteps?.find(
            (s) => s.tool === hitlTool && (s.status === "awaiting_hitl" || s.status === "running"),
          );
          // 补参已提交：立即切到执行中，避免等待 SSE 期间仍显示「等待确认」
          if (hitlTool) {
            markAssistantToolRunning(m.id, hitlTool);
          }
          if (hitlStep) {
            updateAssistantPlanStep(m.id, hitlStep.id, "running", {
              hitl: {
                ...(hitlStep.hitl ?? {}),
                type: interruptBlock.payload.type,
                resolution: "submitted",
              },
              resultSummary: undefined,
              errorMessage: undefined,
              startedAt: hitlStep.startedAt ?? Date.now(),
            });
          }
          clearAssistantInterruptBlock(m.id);
          patchAssistantMessage(m.id, { streaming: true });
          break;
        }
      }

      setPendingInterrupt(null);
      abortRef.current?.abort();
      abortRef.current = new AbortController();

      const resumeArgs: Record<string, unknown> = { ...values };
      if (hitlTool) {
        resumeArgs._hitl_tool = hitlTool;
      }

      agentDebugLog("hitl.resume_submit", {
        threadId: currentThreadId.slice(0, 12),
        sourceMessageId: sourceMessageId?.slice(0, 8) ?? null,
        hitlTool,
        argKeys: Object.keys(resumeArgs),
        messagesSnapshot: msgs.filter((m) => m.role === "assistant").map(summarizeAssistantMessage),
      });

      const finalizeSource = () => {
        if (sourceMessageId) {
          finalizeAssistantMessage(sourceMessageId);
        }
      };

      const fallbackAssistantId = sourceMessageId ? null : appendAssistantPlaceholder();

      try {
        const resumeHandlers: AgentSseHandler = sourceMessageId
          ? (() => {
              const base = createStreamHandlers(sourceMessageId!);
              return {
                ...base,
                onTextDelta: (delta) => {
                  updateAssistantText(sourceMessageId!, delta, {
                    markStreaming: false,
                  });
                },
                onToolStart: (tool, args, meta) => {
                  if (tool === "download_file" && hitlTool && hitlTool !== "download_file") {
                    agentDebugLog("sse.skip_stale_tool_on_resume", {
                      tool,
                      hitlTool,
                    });
                    return;
                  }
                  base.onToolStart?.(tool, args, meta);
                },
                onToolEnd: (tool, result, meta) => {
                  if (
                    tool === "download_file" &&
                    hitlTool &&
                    hitlTool !== "download_file" &&
                    parseToolResultUserCancelled(result)
                  ) {
                    agentDebugLog("sse.skip_stale_tool_end_on_resume", {
                      tool,
                      hitlTool,
                    });
                    return;
                  }
                  base.onToolEnd?.(tool, result, meta);
                },
                onDone: (threadId) => {
                  base.onDone?.(threadId);
                },
                onError: (code, msg, data) => {
                  const toast = formatAgentErrorToast(intl, msg, data);
                  const detail = formatAgentErrorMessage(intl, msg, data);
                  message.error(toast, 6);
                  updateAssistantText(sourceMessageId!, `\n\n⚠️ ${detail.replace(/\n/g, "\n\n")}`, {
                    markStreaming: false,
                  });
                  finalizeSource();
                  void code;
                },
              };
            })()
          : createStreamHandlers(fallbackAssistantId!);

        await AgentController.resumeStream(
          {
            thread_id: currentThreadId,
            model_id: selectedModelId,
            decisions: [{ type: "respond", args: resumeArgs }],
          },
          resumeHandlers,
          abortRef.current.signal,
        );
      } catch (err) {
        if ((err as Error).name !== "AbortError") {
          message.error((err as Error).message || "提交失败");
        }
      } finally {
        finalizeSource();
        if (fallbackAssistantId) {
          finalizeAssistantMessage(fallbackAssistantId);
        }
        setStreaming(false);
      }
    },
    [
      appendAssistantPlaceholder,
      clearAssistantInterruptBlock,
      markAssistantToolRunning,
      createStreamHandlers,
      currentThreadId,
      finalizeAssistantMessage,
      intl,
      patchAssistantMessage,
      selectedModelId,
      setPendingInterrupt,
      setStreaming,
      updateAssistantPlanStep,
      updateAssistantText,
    ],
  );

  const submitHitlConfirm = useCallback(
    async (
      approved: boolean,
      options?: {
        steps?: import("@ims/shared-types").PlanStep[];
        graph?: import("@ims/shared-types").PlanGraph;
        flow_document?: FlowDocumentJSON;
      },
    ) => {
      setStreaming(true);
      setPendingInterrupt(null);

      let sourceMessageId: string | null = null;
      const msgs = useAiAssistantStore.getState().messages;
      for (let i = msgs.length - 1; i >= 0; i -= 1) {
        const m = msgs[i];
        const interruptBlock = m.blocks.find((b) => b.type === "interrupt");
        if (m.role === "assistant" && interruptBlock?.type === "interrupt") {
          sourceMessageId = m.id;
          if (!approved) {
            // 清除该条消息可能残留的流式 loading（如 plan 执行中断后未复位）
            finalizeAssistantMessage(m.id);
            clearAssistantInterruptBlock(m.id);
            const hitlTool = interruptBlock.payload.tool;
            if (hitlTool) {
              completeAssistantToolCall(m.id, hitlTool, undefined, "cancelled");
            }
            if (interruptBlock.payload.type === "plan_confirm") {
              m.planSteps?.forEach((step) => {
                if (step.status === "awaiting_confirm") {
                  updateAssistantPlanStep(m.id, step.id, "skipped", {
                    hitl: {
                      ...(step.hitl ?? {}),
                      type: "plan_confirm",
                      resolution: "rejected",
                    },
                    resultSummary: intl.formatMessage({
                      id: "aiAssistant.card.hitl.rejected",
                    }),
                  });
                }
              });
            } else {
              const hitlStep = m.planSteps?.find(
                (s) =>
                  s.tool === hitlTool && (s.status === "awaiting_hitl" || s.status === "running"),
              );
              if (hitlStep) {
                updateAssistantPlanStep(m.id, hitlStep.id, "skipped", {
                  hitl: {
                    ...(hitlStep.hitl ?? {}),
                    type: interruptBlock.payload.type,
                    resolution: "rejected",
                  },
                  resultSummary: intl.formatMessage({
                    id: "aiAssistant.card.tool.cancelled",
                  }),
                });
              }
            }
          }
          break;
        }
      }

      abortRef.current?.abort();
      abortRef.current = new AbortController();

      // 用户拒绝：不新建助手气泡，静默通知后端清理状态，取消文案写回原消息
      if (!approved) {
        agentDebugLog("hitl.confirm_reject", {
          threadId: currentThreadId.slice(0, 12),
          sourceMessageId: sourceMessageId?.slice(0, 8) ?? null,
          interruptType: (() => {
            if (!sourceMessageId) return null;
            const m = msgs.find((x) => x.id === sourceMessageId);
            const b = m?.blocks.find((x) => x.type === "interrupt");
            return b?.type === "interrupt" ? b.payload.type : null;
          })(),
          hitlTool: (() => {
            if (!sourceMessageId) return null;
            const m = msgs.find((x) => x.id === sourceMessageId);
            const b = m?.blocks.find((x) => x.type === "interrupt");
            return b?.type === "interrupt" ? b.payload.tool : null;
          })(),
        });
        const finalizeSource = () => {
          if (sourceMessageId) {
            finalizeAssistantMessage(sourceMessageId);
          }
        };
        try {
          await AgentController.resumeStream(
            {
              thread_id: currentThreadId,
              model_id: selectedModelId,
              decisions: [{ type: "reject" }],
            },
            {
              onTextDelta: (delta) => {
                if (sourceMessageId) {
                  // 取消说明为静态追加，不进入流式 loading 态
                  updateAssistantText(sourceMessageId, delta, {
                    markStreaming: false,
                  });
                }
              },
              onDone: () => {
                finalizeSource();
                loadSessions();
              },
              // 编排层取消失败时不打扰用户（前端已标记为已取消）
              onError: () => {
                finalizeSource();
              },
            },
            abortRef.current.signal,
          );
        } catch {
          // 静默
        } finally {
          finalizeSource();
          setStreaming(false);
        }
        return;
      }

      const streamMessageId = sourceMessageId ?? appendAssistantPlaceholder();

      // 批准续跑：始终写回触发 HITL 的助手消息（含 plan_confirm 带编排 steps），避免 Plan 与执行拆成两条气泡
      if (sourceMessageId && approved) {
        const sourceMsg = useAiAssistantStore
          .getState()
          .messages.find((m) => m.id === sourceMessageId);
        const interruptBlock = sourceMsg?.blocks.find((b) => b.type === "interrupt");
        const hitlTool =
          interruptBlock?.type === "interrupt" ? interruptBlock.payload.tool : undefined;
        const interruptType =
          interruptBlock?.type === "interrupt" ? interruptBlock.payload.type : undefined;

        clearAssistantInterruptBlock(sourceMessageId);
        const patch: Parameters<typeof patchAssistantMessage>[1] = {
          streaming: true,
        };
        if (options?.steps?.length) {
          patch.planSteps = options.steps.map((s) => {
            const enriched = enrichPlanStepCatalogMeta(s);
            return {
              ...enriched,
              status:
                s.status === "skipped"
                  ? ("skipped" as const)
                  : s.status === "awaiting_confirm"
                    ? ("pending" as const)
                    : s.status,
              hitl: {
                ...(enriched.hitl ?? {}),
                type: "plan_confirm",
                resolution: "approved" as const,
              },
            };
          });
          // 计划确认后：首个未跳过步骤立即显示执行中
          const firstActive = patch.planSteps.find((s) => s.status !== "skipped");
          if (firstActive) {
            patch.planSteps = patch.planSteps.map((s) =>
              s.id === firstActive.id
                ? {
                    ...s,
                    status: "running" as const,
                    startedAt: Date.now(),
                    resultSummary: undefined,
                    errorMessage: undefined,
                  }
                : s,
            );
          }
          patch.planGraph = options.graph ?? null;
          patch.planFlowDocument = options.flow_document ?? null;
        } else if (hitlTool) {
          // confirm / 工具级批准：立即切到执行中，覆盖「等待确认→已完成」中间空白
          markAssistantToolRunning(sourceMessageId, hitlTool);
          const hitlStep = sourceMsg?.planSteps?.find(
            (s) =>
              s.tool === hitlTool &&
              (s.status === "awaiting_hitl" || s.status === "running" || s.status === "pending"),
          );
          if (hitlStep) {
            updateAssistantPlanStep(sourceMessageId, hitlStep.id, "running", {
              hitl: {
                ...(hitlStep.hitl ?? {}),
                type: interruptType,
                resolution: "approved",
              },
              resultSummary: undefined,
              errorMessage: undefined,
              startedAt: hitlStep.startedAt ?? Date.now(),
            });
          }
        }
        patchAssistantMessage(sourceMessageId, patch);
      } else if (streamMessageId === sourceMessageId && sourceMessageId) {
        clearAssistantInterruptBlock(sourceMessageId);
        patchAssistantMessage(sourceMessageId, { streaming: true });
      }

      try {
        const resumeArgs: Record<string, unknown> = {};
        if (options?.steps) resumeArgs.steps = options.steps;
        if (options?.graph) resumeArgs.graph = options.graph;
        if (options?.flow_document) {
          resumeArgs.flow_document = options.flow_document;
        }

        await AgentController.resumeStream(
          {
            thread_id: currentThreadId,
            model_id: selectedModelId,
            decisions: [
              {
                type: approved ? "approve" : "reject",
                args: Object.keys(resumeArgs).length ? resumeArgs : undefined,
              },
            ],
          },
          createStreamHandlers(streamMessageId),
          abortRef.current.signal,
        );
      } catch (err) {
        if ((err as Error).name !== "AbortError") {
          message.error((err as Error).message || "操作失败");
        }
      } finally {
        setStreaming(false);
        finalizeAssistantMessage(streamMessageId);
      }
    },
    [
      appendAssistantPlaceholder,
      clearAssistantInterruptBlock,
      completeAssistantToolCall,
      markAssistantToolRunning,
      createStreamHandlers,
      currentThreadId,
      finalizeAssistantMessage,
      intl,
      loadSessions,
      patchAssistantMessage,
      selectedModelId,
      setPendingInterrupt,
      setStreaming,
      updateAssistantPlanStep,
      updateAssistantText,
    ],
  );

  const abortStream = useCallback(() => {
    abortRef.current?.abort();
    setStreaming(false);
  }, [setStreaming]);

  return {
    sendMessage,
    submitHitlResume,
    submitHitlConfirm,
    loadSessions,
    loadThreadHistory,
    abortStream,
  };
}
