from pathlib import Path

path = Path(
    "e:/WORK/CODE/ims-ai-desktop/apps/desktop/src/components/AiAssistant/hooks/useAgentStream.ts"
)
text = path.read_text(encoding="utf-8")

old_resume_abort = """      setPendingInterrupt(null);
      abortRef.current?.abort();
      abortRef.current = new AbortController();

      const resumeArgs: Record<string, unknown> = { ...values };
"""
new_resume_abort = """      setPendingInterrupt(null);
      const boundThreadId = storeState.currentThreadId;
      const abortController = beginThreadController(boundThreadId);

      const resumeArgs: Record<string, unknown> = { ...values };
"""
if old_resume_abort not in text:
    raise SystemExit("resume abort block missing")
text = text.replace(old_resume_abort, new_resume_abort, 1)

text = text.replace(
    """      agentDebugLog("hitl.resume_submit", {
        threadId: currentThreadId.slice(0, 12),""",
    """      agentDebugLog("hitl.resume_submit", {
        threadId: boundThreadId.slice(0, 12),""",
    1,
)

text = text.replace(
    "              const base = createStreamHandlers(sourceMessageId!);",
    "              const base = createStreamHandlers(sourceMessageId!, boundThreadId);",
    1,
)
text = text.replace(
    "          : createStreamHandlers(fallbackAssistantId!);",
    "          : createStreamHandlers(fallbackAssistantId!, boundThreadId);",
    1,
)

old_resume_await = """        await AgentController.resumeStream(
          {
            thread_id: currentThreadId,
            mid: sourceMid,
            model_id: selectedModelId,
            run_mode: runMode,
            plan_first: planFirst,
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
"""
new_resume_await = """        await AgentController.resumeStream(
          {
            thread_id: boundThreadId,
            mid: sourceMid,
            model_id: selectedModelId,
            run_mode: runMode,
            plan_first: planFirst,
            decisions: [{ type: "respond", args: resumeArgs }],
          },
          resumeHandlers,
          abortController.signal,
        );
      } catch (err) {
        if ((err as Error).name !== "AbortError") {
          message.error((err as Error).message || "提交失败");
        }
      } finally {
        releaseThreadController(boundThreadId, abortController);
        runWithMessageThread(boundThreadId, () => {
          finalizeSource();
          if (fallbackAssistantId) {
            finalizeAssistantMessage(fallbackAssistantId);
          }
          setStreaming(false);
        });
      }
    },
    [
      appendAssistantPlaceholder,
      beginThreadController,
      clearAssistantInterruptBlock,
      markAssistantToolRunning,
      createStreamHandlers,
      finalizeAssistantMessage,
      releaseThreadController,
"""
if old_resume_await not in text:
    raise SystemExit("resume await missing")
text = text.replace(old_resume_await, new_resume_await, 1)

old_confirm_abort = """      abortRef.current?.abort();
      abortRef.current = new AbortController();

      // 用户拒绝：不新建助手气泡，静默通知后端清理状态，取消文案写回原消息
"""
new_confirm_abort = """      const boundThreadId = storeState.currentThreadId;
      const abortController = beginThreadController(boundThreadId);

      // 用户拒绝：不新建助手气泡，静默通知后端清理状态，取消文案写回原消息
"""
if old_confirm_abort not in text:
    raise SystemExit("confirm abort missing")
text = text.replace(old_confirm_abort, new_confirm_abort, 1)

text = text.replace(
    """        agentDebugLog("hitl.confirm_reject", {
          threadId: currentThreadId.slice(0, 12),""",
    """        agentDebugLog("hitl.confirm_reject", {
          threadId: boundThreadId.slice(0, 12),""",
    1,
)

print("signal count", text.count("abortRef.current.signal"))
text = text.replace("abortRef.current.signal", "abortController.signal")

text = text.replace(
    "createStreamHandlers(streamMessageId)",
    "createStreamHandlers(streamMessageId, boundThreadId)",
    1,
)

print("thread_id current count", text.count("thread_id: currentThreadId"))
text = text.replace("thread_id: currentThreadId", "thread_id: boundThreadId")

old_rej_finally = """        } catch {
          // 静默
        } finally {
          finalizeSource();
          setStreaming(false);
        }
        return;
      }
"""
new_rej_finally = """        } catch {
          // 静默
        } finally {
          releaseThreadController(boundThreadId, abortController);
          runWithMessageThread(boundThreadId, () => {
            finalizeSource();
            setStreaming(false);
          });
        }
        return;
      }
"""
if old_rej_finally not in text:
    raise SystemExit("rej finally missing")
text = text.replace(old_rej_finally, new_rej_finally, 1)

old_ok_finally = """      } catch (err) {
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
"""
new_ok_finally = """      } catch (err) {
        if ((err as Error).name !== "AbortError") {
          message.error((err as Error).message || "操作失败");
        }
      } finally {
        releaseThreadController(boundThreadId, abortController);
        runWithMessageThread(boundThreadId, () => {
          setStreaming(false);
          finalizeAssistantMessage(streamMessageId);
        });
      }
    },
    [
      appendAssistantPlaceholder,
      beginThreadController,
      clearAssistantInterruptBlock,
"""
if old_ok_finally not in text:
    raise SystemExit("ok finally missing")
text = text.replace(old_ok_finally, new_ok_finally, 1)

# Remove currentThreadId from confirm deps if still present near abortStream
confirm_block = text[text.find("const submitHitlConfirm") : text.find("const abortStream")]
if "currentThreadId," in confirm_block and "releaseThreadController," not in confirm_block:
    text = text.replace(
        """      createStreamHandlers,
      currentThreadId,
      finalizeAssistantMessage,
      intl,
      loadSessions,""",
        """      createStreamHandlers,
      finalizeAssistantMessage,
      intl,
      loadSessions,
      releaseThreadController,""",
        1,
    )
elif "currentThreadId," in confirm_block:
    text = text.replace(
        """      createStreamHandlers,
      currentThreadId,
      finalizeAssistantMessage,
      intl,
      loadSessions,
      patchAssistantMessage,""",
        """      createStreamHandlers,
      finalizeAssistantMessage,
      intl,
      loadSessions,
      patchAssistantMessage,
      releaseThreadController,""",
        1,
    )

old_abort = """  const abortStream = useCallback(() => {
    abortRef.current?.abort();
    const state = useAiAssistantStore.getState();
    const streamingMsg = [...state.messages]
      .reverse()
      .find(
        (m) =>
          m.role === "assistant" &&
          (m.streaming || m.blocks.some((b) => isActiveInterruptBlock(b))),
      );
    if (streamingMsg) {
      finalizeTurnResidue(streamingMsg.id, "aborted", {
        resultSummary: intl.formatMessage({ id: "aiAssistant.card.hitl.aborted" }),
      });
    } else {
      state.setPendingInterrupt(null);
      setStreaming(false);
    }
  }, [intl, setStreaming]);

  return {
    sendMessage,
    submitHitlResume,
    submitHitlConfirm,
    loadSessions,
    loadThreadHistory,
    abortStream,
  };
}
"""
new_abort = """  const abortStream = useCallback(() => {
    const state = useAiAssistantStore.getState();
    const boundThreadId = state.currentThreadId;
    abortThreadController(boundThreadId);
    const streamingMsg = [...state.messages]
      .reverse()
      .find(
        (m) =>
          m.role === "assistant" &&
          (m.streaming || m.blocks.some((b) => isActiveInterruptBlock(b))),
      );
    runWithMessageThread(boundThreadId, () => {
      if (streamingMsg) {
        finalizeTurnResidue(streamingMsg.id, "aborted", {
          resultSummary: intl.formatMessage({ id: "aiAssistant.card.hitl.aborted" }),
        });
      } else {
        state.setPendingInterrupt(null);
        setStreaming(false);
      }
    });
  }, [abortThreadController, intl, setStreaming]);

  /** 删除会话时中止该 thread 后台流并清理快照 */
  const disposeThreadRuntime = useCallback(
    (threadId: string) => {
      abortThreadController(threadId);
      useAiAssistantStore.getState().clearThreadSnapshot(threadId);
    },
    [abortThreadController],
  );

  return {
    sendMessage,
    submitHitlResume,
    submitHitlConfirm,
    loadSessions,
    loadThreadHistory,
    abortStream,
    disposeThreadRuntime,
  };
}
"""
if old_abort not in text:
    raise SystemExit("abortStream block missing")
text = text.replace(old_abort, new_abort, 1)

print("abortRef remaining", text.count("abortRef"))
bad = [
    line
    for line in text.splitlines()
    if "createStreamHandlers(" in line
    and "boundThreadId" not in line
    and "assistantId: string" not in line
]
print("bad createStreamHandlers lines:", bad)
path.write_text(text, encoding="utf-8")
print("ok")
