/** 按 SSE mid 定位助手气泡；无 mid 时回退绑定 id */
const resolveAssistantIdByMid = useCallback((fallbackId: string, mid?: string) => {
  if (!mid) return fallbackId;
  const matched = [...getWriteTargetMessages()]
    .reverse()
    .find((m) => m.role === "assistant" && m.mid === mid);
  return matched?.id ?? fallbackId;
}, []);

/** 创建 SSE 事件处理器（绑定到指定 assistant 消息与 thread） */
const createStreamHandlers = useCallback(
  (assistantId: string, boundThreadId: string): AgentSseHandler => {
    const raw: AgentSseHandler = {
      onTextDelta: (delta, meta) =>
        updateAssistantText(resolveAssistantIdByMid(assistantId, meta?.mid), delta),
      onToolStart: (tool, args, meta) => {
        const id = resolveAssistantIdByMid(assistantId, meta?.mid);
        agentDebugLog("sse.tool_start", {
          assistantId: id.slice(0, 8),
          mid: meta?.mid,
          tool,
          toolCallId: meta?.toolCallId,
        });
        if (tool === "download_file") {
          exportDownloadCountRef.current = 0;
        }
        const argsKey = meta?.toolCallId || tool;
        pendingToolArgsRef.current[argsKey] = args;
        appendAssistantBlock(id, {
          type: "tool_call",
          tool,
          args,
          status: "running",
          toolCallId: meta?.toolCallId,
          retry: meta?.retry,
          attempt: meta?.attempt,
        });
        const planMsg = getWriteTargetMessages().find((m) => m.id === id);
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
          updateAssistantPlanStep(id, runningStep.id, "running", {
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
        const id = resolveAssistantIdByMid(assistantId, meta?.mid);
        agentDebugLog("sse.tool_end", {
          assistantId: id.slice(0, 8),
          mid: meta?.mid,
          tool,
          toolCallId: meta?.toolCallId,
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
        const argsKey = meta?.toolCallId || tool;
        const args = pendingToolArgsRef.current[argsKey] ?? pendingToolArgsRef.current[tool];
        delete pendingToolArgsRef.current[argsKey];
        if (meta?.toolCallId) delete pendingToolArgsRef.current[tool];
        const userCancelled = parseToolResultUserCancelled(result);
        const ok = userCancelled ? false : parseToolResultOk(result);
        const shortSummary = parseToolResultShortSummary(result);
        const autoRetry = parseToolResultAutoRetry(result);
        completeAssistantToolCall(
          id,
          tool,
          result,
          userCancelled ? "cancelled" : ok ? "done" : "error",
          meta?.toolCallId,
        );
        syncAssistantPlanStepFromToolEnd(
          id,
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
        reconcileAssistantPlanStepsFromBlocks(id);
        const workspace = workspaceFromToolEnd(tool, result, args);
        if (workspace && (workspace.kind === "device_command" || ok)) {
          patchAssistantMessage(id, { workspaceContent: workspace });
        }
        void meta;
      },
      onInterrupt: (payload) => {
        const id = resolveAssistantIdByMid(assistantId, payload.mid);
        const boundMid = getWriteTargetMessages().find((m) => m.id === id)?.mid;
        const interruptPayload = payload.mid || !boundMid ? payload : { ...payload, mid: boundMid };
        agentDebugLog("sse.interrupt", {
          assistantId: id.slice(0, 8),
          mid: interruptPayload.mid,
          type: interruptPayload.type,
          tool: interruptPayload.tool,
        });
        setPendingInterrupt(interruptPayload);
        setAssistantInterruptBlock(id, interruptPayload);
        if (interruptPayload.type === "plan_confirm") {
          const msg = getWriteTargetMessages().find((m) => m.id === id);
          const steps = msg?.planSteps?.length ? msg.planSteps : (interruptPayload.steps ?? []);
          steps.forEach((step) => {
            const enriched = enrichPlanStepCatalogMeta(step);
            updateAssistantPlanStep(id, step.id, "awaiting_confirm", {
              side: enriched.side,
              riskLevel: enriched.riskLevel,
              hitl: {
                type: "plan_confirm",
                message:
                  typeof interruptPayload.message === "string"
                    ? interruptPayload.message.trim().slice(0, 200)
                    : undefined,
              },
            });
          });
          if (!msg?.planSteps?.length && interruptPayload.steps?.length) {
            patchAssistantMessage(id, {
              planSteps: interruptPayload.steps.map((s) => {
                const enriched = enrichPlanStepCatalogMeta(s);
                return {
                  ...enriched,
                  status: "awaiting_confirm" as const,
                  hitl: {
                    type: "plan_confirm" as const,
                    message:
                      typeof interruptPayload.message === "string"
                        ? interruptPayload.message.trim().slice(0, 200)
                        : undefined,
                  },
                };
              }),
              planGraph: interruptPayload.graph ?? null,
            });
          } else if (interruptPayload.graph) {
            patchAssistantMessage(id, {
              planGraph: interruptPayload.graph,
            });
          }
          notifyBackgroundThread(boundThreadId, "hitl");
          return;
        }
        const msgBefore = getWriteTargetMessages().find((m) => m.id === id);
        if (msgBefore) {
          for (const block of msgBefore.blocks) {
            if (
              block.type === "tool_call" &&
              block.tool !== interruptPayload.tool &&
              block.status === "running" &&
              block.tool === "download_file"
            ) {
              completeAssistantToolCall(id, block.tool, undefined, "cancelled");
              const staleStep = msgBefore.planSteps?.find(
                (s) => s.tool === block.tool && (s.status === "running" || s.status === "pending"),
              );
              if (staleStep) {
                updateAssistantPlanStep(id, staleStep.id, "skipped");
              }
            }
          }
        }
        if (msgBefore?.planSteps?.length && interruptPayload.tool) {
          for (const step of msgBefore.planSteps) {
            if (
              step.tool &&
              step.tool !== interruptPayload.tool &&
              step.status === "running" &&
              step.tool !== "download_file"
            ) {
              updateAssistantPlanStep(id, step.id, "done");
            }
          }
          for (const block of msgBefore.blocks) {
            if (
              block.type === "tool_call" &&
              block.tool !== interruptPayload.tool &&
              block.status === "running" &&
              block.tool !== "download_file"
            ) {
              completeAssistantToolCall(id, block.tool, undefined, "done");
            }
          }
        }
        markAssistantToolAwaitingHitl(id, interruptPayload.tool);
        const msg = getWriteTargetMessages().find((m) => m.id === id);
        const hitlStep = msg?.planSteps?.find(
          (s) =>
            s.tool === interruptPayload.tool && (s.status === "running" || s.status === "error"),
        );
        if (hitlStep) {
          updateAssistantPlanStep(id, hitlStep.id, "awaiting_hitl", {
            resultSummary:
              typeof interruptPayload.message === "string" && interruptPayload.message.trim()
                ? interruptPayload.message.trim().slice(0, 200)
                : intl.formatMessage({
                    id: "aiAssistant.card.tool.awaitingHitl",
                  }),
            hitl: {
              type: interruptPayload.type,
              message:
                typeof interruptPayload.message === "string"
                  ? interruptPayload.message.trim().slice(0, 200)
                  : undefined,
            },
            ...(() => {
              const meta = enrichPlanStepCatalogMeta({
                tool: interruptPayload.tool,
              });
              return { side: meta.side, riskLevel: meta.riskLevel };
            })(),
          });
        }
        notifyBackgroundThread(boundThreadId, "hitl");
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
        if (boundThreadId) {
          void AgentController.reportClientActionResult(boundThreadId, result).catch((err) => {
            agentDebugLog("client_action.ack_failed", {
              action: result.action,
              error: err instanceof Error ? err.message : String(err),
            });
          });
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
        const latest = getWriteTargetMessages().find((m) => m.id === assistantId);
        const hitlBlock = latest?.blocks.find((b) => b.type === "interrupt");
        if (hitlBlock?.type === "interrupt" && latest) {
          const payload = hitlBlock.payload;
          const stillAwaitingHitl = shouldPreserveHitlOnStreamDone(payload, latest.blocks);
          if (stillAwaitingHitl && !getWriteTargetPendingInterrupt()) {
            setPendingInterrupt(payload);
          } else if (!stillAwaitingHitl) {
            useAiAssistantStore.getState().clearAssistantInterruptBlock(assistantId);
          }
        } else if (!getWriteTargetPendingInterrupt()) {
          void hitlBlock;
        }
        const forWorkspace = getWriteTargetMessages().find((m) => m.id === assistantId);
        if (forWorkspace && !forWorkspace.workspaceContent) {
          const workspace = resolveWorkspaceFromMessage(forWorkspace);
          if (workspace?.ok) {
            patchAssistantMessage(assistantId, { workspaceContent: workspace });
          }
        }
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
        if (!getWriteTargetPendingInterrupt()) {
          notifyBackgroundThread(boundThreadId, "done");
        }
      },
      onError: (code, msg, data) => {
        agentDebugLog("sse.error", {
          assistantId: assistantId.slice(0, 8),
          code,
          msg,
        });
        const msgState = getWriteTargetMessages().find((m) => m.id === assistantId);
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
        notifyBackgroundThread(boundThreadId, "error");
        void code;
      },
    };
    return bindAgentSseHandlersToThread(boundThreadId, raw);
  },
  [
    appendAssistantBlock,
    setAssistantInterruptBlock,
    appendAssistantTraceEvent,
    completeAssistantToolCall,
    markAssistantToolAwaitingHitl,
    completeClientAction,
    finalizeAssistantMessage,
    loadSessions,
    notifyBackgroundThread,
    patchAssistantMessage,
    setPendingInterrupt,
    updateAssistantPlanStep,
    syncAssistantPlanStepFromToolEnd,
    reconcileAssistantPlanStepsFromBlocks,
    updateAssistantText,
    intl,
    resolveAssistantIdByMid,
  ],
);
