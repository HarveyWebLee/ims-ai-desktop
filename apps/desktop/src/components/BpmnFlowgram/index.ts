import type { PlatformToolRiskLevel, PlatformToolSide } from "@ims/shared-types";

/**
 * BPMN / Plan 画布类型桩（桌面端 M1 不提供编排画布 UI）
 */
export type FlowDocumentJSON = Record<string, unknown>;

export type BpmnFlowgramEditorApi = {
  getFlowDocument?: () => FlowDocumentJSON;
};

export function planStepsToFlowDocument(_steps: unknown): FlowDocumentJSON {
  return { nodes: [], edges: [] };
}

export function enrichPlanStepCatalogMeta<T extends { tool?: string }>(
  step: T,
): T & { side?: PlatformToolSide; riskLevel?: PlatformToolRiskLevel } {
  return step as T & { side?: PlatformToolSide; riskLevel?: PlatformToolRiskLevel };
}

export function getPlanToolShortLabel(tool?: string): string {
  return tool || "";
}

/** M1：无画布条件边，恒为 false */
export function flowDocumentHasExecutableConditions(_doc?: FlowDocumentJSON | null): boolean {
  return false;
}

export default function BpmnFlowgramStub() {
  return null;
}
