/**
 * Phase D4：Plan 步骤 → 流程图结构
 */
import type { PlanGraph, PlanStep, PlanStepStatus } from "@ims/shared-types";
import { getPlanToolShortLabel } from "@/components/BpmnFlowgram/utils/plan-tool-catalog";
import type { AiMessageBlock } from "../types";

const STATUS_STYLE: Record<string, string> = {
  pending: "planPending",
  running: "planRunning",
  done: "planDone",
  error: "planError",
  skipped: "planSkipped",
  awaiting_confirm: "planAwaiting",
  awaiting_hitl: "planHitl",
};

/** Plan 步骤状态 → 流程图样式 class 名（与 index.module.less 对齐） */
export function planStepStyleKey(status?: PlanStepStatus | string): string {
  return STATUS_STYLE[status || "pending"] || "planPending";
}

/** @deprecated 请使用 getPlanToolShortLabel（与 aiAssistant i18n 对齐） */
export function planToolLabel(tool?: string): string {
  return getPlanToolShortLabel(tool ?? "");
}

export function buildPlanGraphFromSteps(steps: PlanStep[]): PlanGraph {
  if (!steps.length) {
    return { nodes: [], edges: [], mermaid: "flowchart LR\n  empty[无步骤]" };
  }

  const nodes: PlanGraph["nodes"] = [
    {
      id: "__start__",
      label: "开始",
      kind: "start",
      style: "planStart",
    },
  ];
  const edges: PlanGraph["edges"] = [];
  let prevId = "__start__";
  const mermaidLines = ["flowchart LR", "  __start__([开始])"];

  steps.forEach((step, i) => {
    const id = step.id || String(i + 1);
    const label = (step.label || step.tool || id).slice(0, 40);
    const safeLabel = label.replace(/"/g, "'");
    const status = step.status || "pending";
    nodes.push({
      id,
      label,
      kind: "plan_step",
      style: STATUS_STYLE[status] || "planPending",
    });
    edges.push({ from: prevId, to: id });
    mermaidLines.push(`  ${id}["${safeLabel}"]`);
    mermaidLines.push(`  ${prevId} --> ${id}`);
    prevId = id;
  });

  return { nodes, edges, mermaid: mermaidLines.join("\n") };
}

/** 切换步骤 skipped 状态（plan_confirm 轻量编排） */
export function togglePlanStepSkip(steps: PlanStep[], stepId: string): PlanStep[] {
  return steps.map((s) => {
    if (s.id !== stepId) return s;
    const next: PlanStepStatus = s.status === "skipped" ? "awaiting_confirm" : "skipped";
    return { ...s, status: next };
  });
}

/** 至少保留一个非 skipped 步骤 */
export function countActivePlanSteps(steps: PlanStep[]): number {
  return steps.filter((s) => s.status !== "skipped").length;
}

/** Plan 流程图节点是否仅为装饰（开始/结束），不应出现在任务时间轴 */
export function isDecorativePlanGraphNode(node: {
  id: string;
  kind?: string;
  label?: string;
}): boolean {
  if (node.id === "__start__" || node.kind === "start" || node.kind === "end") {
    return true;
  }
  const label = (node.label ?? "").trim();
  return label === "开始" || label === "开始事件";
}

/** 按图节点 id / nodeId / tool 解析对应 Plan 步骤（BPMN node_id 与 step.id 不一致时） */
export function findPlanStepForGraphNode(
  steps: PlanStep[],
  node: { id: string; tool?: string },
): PlanStep | undefined {
  const direct = steps.find((s) => s.id === node.id || (s.nodeId != null && s.nodeId === node.id));
  if (direct) return direct;
  const nodeTool = node.tool?.trim();
  if (!nodeTool) return undefined;
  return steps.find((s) => s.tool === nodeTool);
}

const TOOL_BLOCK_TERMINAL_STATUS: Record<string, PlanStepStatus> = {
  done: "done",
  error: "error",
  cancelled: "skipped",
};

/** 根据工具块终态推导 Plan 步骤应展示/持久化的状态（plan_update 丢失时的兜底） */
export function inferPlanStepStatusFromToolBlocks(
  step: PlanStep,
  blocks: AiMessageBlock[],
): PlanStepStatus | null {
  if (!step.tool) return null;
  if (step.status !== "running" && step.status !== "awaiting_hitl" && step.status !== "error") {
    return null;
  }
  for (let i = blocks.length - 1; i >= 0; i -= 1) {
    const block = blocks[i];
    if (block.type !== "tool_call" || block.tool !== step.tool) continue;
    return TOOL_BLOCK_TERMINAL_STATUS[block.status] ?? null;
  }
  return null;
}

/** 将仍为 running 的 Plan 步骤与已完成的 tool_call 块对齐（返回新数组，无变化时返回原引用） */
export function reconcilePlanStepsWithToolBlocks(
  planSteps: PlanStep[],
  blocks: AiMessageBlock[],
): PlanStep[] {
  let changed = false;
  const next = planSteps.map((step) => {
    const inferred = inferPlanStepStatusFromToolBlocks(step, blocks);
    if (!inferred || inferred === step.status) return step;
    changed = true;
    return {
      ...step,
      status: inferred,
      endedAt: step.endedAt ?? Date.now(),
    };
  });
  return changed ? next : planSteps;
}
