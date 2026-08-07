/**
 * Trace 事件 kind → 样式类名 / i18n key
 */

const TRACE_KIND_CLASS: Record<string, string> = {
  plan: "traceKindPlan",
  replan: "traceKindReplan",
  tool_start: "traceKindToolStart",
  tool_end: "traceKindToolEnd",
  interrupt: "traceKindInterrupt",
  error: "traceKindError",
  done: "traceKindDone",
  user_message: "traceKindUserMessage",
  client_action: "traceKindClientAction",
  context: "traceKindPlan",
  rag_passive: "traceKindToolStart",
  llm_input: "traceKindUserMessage",
  assistant_message: "traceKindDone",
};

const TRACE_KIND_I18N: Record<string, string> = {
  plan: "aiAssistant.trace.kind.plan",
  replan: "aiAssistant.trace.kind.replan",
  tool_start: "aiAssistant.trace.kind.toolStart",
  tool_end: "aiAssistant.trace.kind.toolEnd",
  interrupt: "aiAssistant.trace.kind.interrupt",
  error: "aiAssistant.trace.kind.error",
  done: "aiAssistant.trace.kind.done",
  user_message: "aiAssistant.trace.kind.userMessage",
  client_action: "aiAssistant.trace.kind.clientAction",
  context: "aiAssistant.trace.kind.context",
  rag_passive: "aiAssistant.trace.kind.ragPassive",
  llm_input: "aiAssistant.trace.kind.llmInput",
  assistant_message: "aiAssistant.trace.kind.assistantMessage",
};

export function getTraceKindClassName(kind: string): string {
  return TRACE_KIND_CLASS[kind] ?? "traceKindDefault";
}

export function getTraceKindLabelKey(kind: string): string {
  return TRACE_KIND_I18N[kind] ?? "aiAssistant.trace.kind.default";
}
