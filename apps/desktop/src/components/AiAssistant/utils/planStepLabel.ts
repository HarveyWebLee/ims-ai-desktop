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
