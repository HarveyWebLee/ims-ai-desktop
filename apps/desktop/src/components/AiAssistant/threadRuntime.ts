/**
 * P2-4：消息写入目标 thread（流式 handler 可在后台会话写入快照）。
 */
import type { AgentSseHandler, AiMessage, HitlPayload } from "./types";

export type ThreadSnapshot = {
  messages: AiMessage[];
  pendingInterrupt: HitlPayload | null;
};

let writeThreadId: string | null = null;

/** 在指定 thread 上下文中执行 store 写入（嵌套可恢复） */
export function runWithMessageThread<T>(threadId: string, fn: () => T): T {
  const prev = writeThreadId;
  writeThreadId = threadId;
  try {
    return fn();
  } finally {
    writeThreadId = prev;
  }
}

export function getMessageWriteThreadId(fallback: string): string {
  return writeThreadId ?? fallback;
}

export function isWritingBackgroundThread(currentThreadId: string): boolean {
  return Boolean(writeThreadId && writeThreadId !== currentThreadId);
}

/** 将 SSE handler 全部包进指定 thread 的写入上下文 */
export function bindAgentSseHandlersToThread(
  threadId: string,
  handlers: AgentSseHandler,
): AgentSseHandler {
  const wrap = <A extends unknown[], R>(
    fn: ((...args: A) => R) | undefined,
  ): ((...args: A) => R) | undefined => {
    if (!fn) return undefined;
    return (...args: A): R => runWithMessageThread(threadId, () => fn(...args));
  };

  return {
    onTextDelta: wrap(handlers.onTextDelta),
    onToolStart: wrap(handlers.onToolStart),
    onToolEnd: wrap(handlers.onToolEnd),
    onInterrupt: wrap(handlers.onInterrupt),
    onClientAction: wrap(handlers.onClientAction),
    onPlan: wrap(handlers.onPlan),
    onPlanUpdate: wrap(handlers.onPlanUpdate),
    onReplan: wrap(handlers.onReplan),
    onTrace: wrap(handlers.onTrace),
    onDone: wrap(handlers.onDone),
    onError: wrap(handlers.onError),
  };
}
