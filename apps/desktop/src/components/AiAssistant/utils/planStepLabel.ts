/**
 * Plan 步骤展示标题：业务中文优先，工具 key 走 i18n
 */
import type { PlanStep } from "@ims/shared-types";
import { TOOL_LABEL_KEYS, getToolLabelKey } from "../chatCardUtils";

type FormatMessage = (descriptor: { id: string }) => string;

export function resolvePlanStepDisplayLabel(
  step: Pick<PlanStep, "label" | "tool"> | undefined,
  nodeLabel: string | undefined,
  formatMessage: FormatMessage,
): string {
  const tool = step?.tool?.trim();
  const stepLabel = step?.label?.trim();
  const graphLabel = nodeLabel?.trim();

  const looksLikeToolKey = (value?: string): boolean =>
    !!value && (!!TOOL_LABEL_KEYS[value] || (!!tool && value === tool));

  if (stepLabel && !looksLikeToolKey(stepLabel)) {
    return stepLabel;
  }
  if (graphLabel && !looksLikeToolKey(graphLabel)) {
    return graphLabel;
  }
  if (tool) {
    return formatMessage({ id: getToolLabelKey(tool) });
  }
  if (graphLabel && TOOL_LABEL_KEYS[graphLabel]) {
    return formatMessage({ id: getToolLabelKey(graphLabel) });
  }
  return stepLabel || graphLabel || "";
}

/** 将 steps 上的中文标题写回 BPMN 节点 data.title */
export function localizePlanFlowDocumentTitles<
  T extends {
    nodes: Array<{ id: string; data?: Record<string, unknown> }>;
  },
>(doc: T, steps: PlanStep[], formatMessage: FormatMessage): T {
  const byKey = new Map<string, PlanStep>();
  steps.forEach((s) => {
    byKey.set(s.id, s);
    if (s.nodeId) byKey.set(s.nodeId, s);
  });
  return {
    ...doc,
    nodes: doc.nodes.map((node) => {
      const step = byKey.get(node.id);
      if (!step) return node;
      const title = resolvePlanStepDisplayLabel(
        step,
        typeof node.data?.title === "string" ? node.data.title : undefined,
        formatMessage,
      );
      return {
        ...node,
        data: {
          ...(node.data ?? {}),
          title,
          tool: step.tool ?? node.data?.tool,
          planStatus: step.status,
          side: step.side ?? node.data?.side,
          riskLevel: step.riskLevel ?? node.data?.riskLevel,
        },
      };
    }),
  };
}
