/**
 * Phase D4：多步 Plan 流程图（只读 / 执行态时间轴）
 */
import {
  CheckCircleFilled,
  CloseCircleFilled,
  ClockCircleOutlined,
  LoadingOutlined,
  MinusCircleOutlined,
  PauseCircleFilled,
} from "@ant-design/icons";
import { Tag, Tooltip, Typography } from "antd";
import { useIntl } from "react-intl";
import type { PlanGraph, PlanStep, PlanStepStatus } from "@ims/shared-types";
import { getToolLabelKey } from "./chatCardUtils";
import {
  buildPlanGraphFromSteps,
  findPlanStepForGraphNode,
  isDecorativePlanGraphNode,
  planStepStyleKey,
} from "./utils/planGraphUtils";
import { resolvePlanStepDisplayLabel } from "./utils/planStepLabel";
import styles from "./index.module.less";

const { Text } = Typography;

/** 工具副标签：始终展示 i18n 工具名 */
function resolvePlanToolDisplayLabel(
  tool: string | undefined,
  intl: ReturnType<typeof useIntl>,
): string {
  if (!tool) return "";
  return intl.formatMessage({ id: getToolLabelKey(tool) });
}

export interface PlanFlowChartProps {
  steps: PlanStep[];
  /** API 下发的 graph；缺省时由 steps 本地构建 */
  graph?: PlanGraph | null;
  /**
   * chain：横向链式（plan_confirm 预览）
   * timeline：纵向时间轴（消息内任务计划，展示执行状态）
   */
  layout?: "chain" | "timeline";
  /** 是否展示步骤状态文案（timeline 默认开启） */
  showStatus?: boolean;
  /** 是否在节点上展示工具短标签（与 label 重复时可关闭） */
  showToolTag?: boolean;
}

function planStepStatusLabel(
  status: PlanStepStatus | string,
  intl: ReturnType<typeof useIntl>,
): string {
  switch (status) {
    case "done":
      return intl.formatMessage({ id: "aiAssistant.plan.statusDone" });
    case "error":
      return intl.formatMessage({ id: "aiAssistant.plan.statusError" });
    case "running":
      return intl.formatMessage({ id: "aiAssistant.plan.statusRunning" });
    case "skipped":
      return intl.formatMessage({ id: "aiAssistant.plan.skipped" });
    case "awaiting_confirm":
      return intl.formatMessage({ id: "aiAssistant.plan.awaitingConfirm" });
    case "awaiting_hitl":
      return intl.formatMessage({ id: "aiAssistant.plan.awaitingHitl" });
    default:
      return intl.formatMessage({ id: "aiAssistant.plan.statusPending" });
  }
}

function PlanStepStatusIcon({ status }: { status: PlanStepStatus | string }) {
  switch (status) {
    case "done":
      return <CheckCircleFilled className={styles.planFlowStatusIconDone} />;
    case "error":
      return <CloseCircleFilled className={styles.planFlowStatusIconError} />;
    case "running":
      return <LoadingOutlined spin className={styles.planFlowStatusIconRunning} />;
    case "skipped":
      return <MinusCircleOutlined className={styles.planFlowStatusIconSkipped} />;
    case "awaiting_confirm":
    case "awaiting_hitl":
      return <PauseCircleFilled className={styles.planFlowStatusIconAwaiting} />;
    default:
      return <ClockCircleOutlined className={styles.planFlowStatusIconPending} />;
  }
}

export default function PlanFlowChart({
  steps,
  graph: graphProp,
  layout = "chain",
  showStatus,
  showToolTag = true,
}: PlanFlowChartProps) {
  const intl = useIntl();
  if (!steps.length) return null;

  const graph = graphProp ?? buildPlanGraphFromSteps(steps);
  const planNodes = graph.nodes.filter((n) => !isDecorativePlanGraphNode(n));
  const showStatusText = showStatus ?? layout === "timeline";

  const renderStepNode = (
    node: (typeof planNodes)[number],
    options?: { index?: number; isLast?: boolean },
  ) => {
    const step = findPlanStepForGraphNode(steps, {
      id: node.id,
      tool: (node as { tool?: string }).tool,
    });
    const status = step?.status ?? "pending";
    const styleKey = planStepStyleKey(status);
    const styleClass = styles[styleKey];
    const skipped = status === "skipped";
    const statusLabel = planStepStatusLabel(status, intl);
    const displayLabel = resolvePlanStepDisplayLabel(step, node.label, (d) =>
      intl.formatMessage(d),
    );
    const toolDisplayLabel = resolvePlanToolDisplayLabel(step?.tool, intl);

    if (layout === "timeline") {
      return (
        <div key={node.id} className={styles.planFlowTimelineItem} role="listitem">
          <div className={styles.planFlowTimelineRail} aria-hidden>
            <span className={`${styles.planFlowTimelineMarker} ${styleClass}`}>
              <PlanStepStatusIcon status={status} />
            </span>
            {!options?.isLast ? <span className={styles.planFlowTimelineConnector} /> : null}
          </div>
          <div
            className={`${styles.planFlowTimelineBody} ${styleClass} ${
              skipped ? styles.planFlowNodeSkipped : ""
            }`}
          >
            <div className={styles.planFlowTimelineHeader}>
              <Text className={styles.planFlowTimelineLabel} title={displayLabel}>
                {displayLabel}
              </Text>
              {showStatusText ? (
                <Tag
                  variant="filled"
                  className={`${styles.planFlowTimelineStatusTag} ${styles[`planFlowStatusTag_${status}`]}`}
                >
                  {statusLabel}
                </Tag>
              ) : null}
            </div>
            {showToolTag && step?.tool ? (
              <Text type="secondary" className={styles.planFlowTimelineTool}>
                {toolDisplayLabel}
              </Text>
            ) : null}
            {status === "done" && step?.resultSummary ? (
              <Text type="secondary" className={styles.planFlowTimelineResult}>
                {step.resultSummary}
              </Text>
            ) : null}
            {status === "error" && step?.errorMessage ? (
              <Text type="danger" className={styles.planFlowTimelineError}>
                {step.errorMessage}
              </Text>
            ) : null}
            {skipped && step?.skipReason ? (
              <Text type="secondary" className={styles.planFlowTimelineTool}>
                {intl.formatMessage(
                  { id: "aiAssistant.plan.skipReason" },
                  { reason: step.skipReason },
                )}
              </Text>
            ) : null}
            {skipped && !step?.skipReason && step?.resultSummary ? (
              <Text type="secondary" className={styles.planFlowTimelineResult}>
                {step.resultSummary}
              </Text>
            ) : null}
          </div>
        </div>
      );
    }

    return (
      <div key={node.id} className={styles.planFlowStep}>
        <span className={styles.planFlowArrow} aria-hidden>
          →
        </span>
        <Tooltip title={step?.tool ? toolDisplayLabel : undefined}>
          <span
            className={`${styles.planFlowNode} ${styleClass} ${
              skipped ? styles.planFlowNodeSkipped : ""
            }`}
          >
            <span className={styles.planFlowNodeHeader}>
              <PlanStepStatusIcon status={status} />
              <span className={styles.planFlowNodeLabel}>{displayLabel}</span>
            </span>
            {showStatusText ? (
              <span className={styles.planFlowNodeStatus}>{statusLabel}</span>
            ) : null}
            {showToolTag && step?.tool ? (
              <Tag className={styles.planFlowToolTag} variant="filled">
                {toolDisplayLabel}
              </Tag>
            ) : null}
          </span>
        </Tooltip>
      </div>
    );
  };

  return (
    <div
      className={`${styles.planFlowChart} ${
        layout === "timeline" ? styles.planFlowChartTimeline : ""
      }`}
    >
      {layout === "timeline" ? (
        <div className={styles.planFlowTimeline} role="list">
          <div className={styles.planFlowTimelineItem} role="listitem">
            <div className={styles.planFlowTimelineRail} aria-hidden>
              <span className={`${styles.planFlowTimelineMarker} ${styles.planStart}`}>
                <CheckCircleFilled className={styles.planFlowStatusIconDone} />
              </span>
              {planNodes.length > 0 ? <span className={styles.planFlowTimelineConnector} /> : null}
            </div>
            <div className={`${styles.planFlowTimelineBody} ${styles.planStart}`}>
              <Text className={styles.planFlowTimelineLabel}>
                {intl.formatMessage({ id: "aiAssistant.plan.graphStart" })}
              </Text>
            </div>
          </div>
          {planNodes.map((node, index) =>
            renderStepNode(node, {
              index,
              isLast: index === planNodes.length - 1,
            }),
          )}
        </div>
      ) : (
        <div className={styles.planFlowChain}>
          <span className={`${styles.planFlowNode} ${styles.planStart}`}>
            {intl.formatMessage({ id: "aiAssistant.plan.graphStart" })}
          </span>
          {planNodes.map((node) => renderStepNode(node))}
        </div>
      )}
    </div>
  );
}
