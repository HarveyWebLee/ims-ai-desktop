/**
 * Phase D3：从 Trace 事件构建执行图（与后端 trace_graph.py 对齐）
 */
import type { TraceEvent, TraceGraph } from "@ims/shared-types";

const KIND_STYLE: Record<string, string> = {
  user_message: "traceUser",
  plan: "tracePlan",
  replan: "traceReplan",
  tool_start: "traceTool",
  tool_end: "traceTool",
  interrupt: "traceHitl",
  client_action: "traceClient",
  error: "traceError",
  done: "traceDone",
};

export function buildTraceGraphFromEvents(events: TraceEvent[]): TraceGraph {
  if (!events.length) {
    return { nodes: [], edges: [], mermaid: "flowchart LR\n  empty[无事件]" };
  }

  const nodes = [
    {
      id: "__start__",
      label: "开始",
      kind: "start",
      style: "traceStart",
      ts: events[0]?.ts,
    },
  ];
  const edges: TraceGraph["edges"] = [];
  let prevId = "__start__";
  const mermaidLines = ["flowchart TD", "  __start__([开始])"];

  events.forEach((evt, i) => {
    const id = evt.id || `evt-${i}`;
    const kind = evt.kind || "unknown";
    const label = (evt.label || kind).slice(0, 40);
    const safeLabel = label.replace(/"/g, "'");
    nodes.push({
      id,
      label,
      kind,
      style: KIND_STYLE[kind] || "traceDefault",
      ts: evt.ts,
    });
    edges.push({ from: prevId, to: id });
    mermaidLines.push(`  ${id}["${safeLabel}"]`);
    mermaidLines.push(`  ${prevId} --> ${id}`);
    prevId = id;
  });

  return { nodes, edges, mermaid: mermaidLines.join("\n") };
}
