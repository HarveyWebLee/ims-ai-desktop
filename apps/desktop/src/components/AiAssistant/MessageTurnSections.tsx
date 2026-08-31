/**
 * 单轮助手消息内的 Trace / Plan / 查询结果区块
 * 与全局底部面板解耦，按消息实例展示
 */
import { Alert, Button, Collapse, Typography } from "antd";
import { BugOutlined, TableOutlined } from "@ant-design/icons";
import { useIntl } from "react-intl";
import dayjs from "dayjs";
import type { PlanStep, TraceEvent, HitlPayload, TraceGraph, PlanGraph } from "@ims/shared-types";
import type { FlowDocumentJSON } from "@/components/BpmnFlowgram";
import type { WorkspaceContent, AiMessageBlock } from "./types";
import DeviceCommandResultPanel from "./DeviceCommandResultPanel";
import ExportResultPanel from "./ExportResultPanel";
import PlanFlowChart from "./PlanFlowChart";
import { useAiAssistantStore } from "./store";
import { getTraceKindClassName, getTraceKindLabelKey } from "./utils/traceTagUtils";
import { buildTraceGraphFromEvents } from "./utils/traceGraphUtils";
import { inferPlanStepStatusFromToolBlocks } from "./utils/planGraphUtils";
import styles from "./index.module.less";

const { Text } = Typography;

/** Phase D3：Trace 执行图（节点链，只读） */
function TraceGraphView({ graph, events }: { graph: TraceGraph; events: TraceEvent[] }) {
  const intl = useIntl();
  if (!graph.nodes.length) return null;
  const eventMap = new Map(events.map((event) => [event.id, event]));

  return (
    <div className={styles.traceGraph}>
      <Text type="secondary" className={styles.traceGraphTitle}>
        {intl.formatMessage({ id: "aiAssistant.trace.graphTitle" })}
      </Text>
      <div className={styles.traceGraphChain} role="list">
        {graph.nodes.map((node, idx) => (
          <div key={node.id} className={styles.traceGraphStep} role="listitem">
            <div className={styles.traceGraphRail} aria-hidden>
              <span
                className={`${styles.traceGraphMarker} ${
                  node.style ? styles[node.style] : styles.traceDefault
                }`}
              >
                {idx + 1}
              </span>
              {idx < graph.nodes.length - 1 ? (
                <span className={styles.traceGraphConnector} />
              ) : null}
            </div>
            <div
              className={`${styles.traceGraphNode} ${
                node.style ? styles[node.style] : styles.traceDefault
              }`}
              title={node.label}
              data-kind={node.kind}
            >
              <div className={styles.traceGraphNodeHeader}>
                <Text type="secondary" className={styles.traceGraphNodeTime}>
                  {dayjs(node.ts).isValid()
                    ? dayjs(node.ts).format("HH:mm:ss.SSS")
                    : "--:--:--.---"}
                </Text>
                <span
                  className={`${styles.traceKindTag} ${
                    styles[getTraceKindClassName(eventMap.get(node.id)?.kind ?? node.kind)]
                  } ${styles.traceGraphNodeKind}`}
                >
                  {intl.formatMessage({
                    id: getTraceKindLabelKey(eventMap.get(node.id)?.kind ?? node.kind),
                  })}
                </span>
              </div>
              <Text className={styles.traceGraphNodeLabel} title={node.label}>
                {node.label}
              </Text>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/** 执行 Trace：默认折叠，置于执行过程/结果之前 */
export function MessageTraceSection({
  events,
  runId,
  streaming,
  graph: graphProp,
}: {
  events: TraceEvent[];
  runId?: string | null;
  streaming?: boolean;
  /** API 返回的 graph；流式时由 events 本地构建 */
  graph?: TraceGraph | null;
}) {
  const intl = useIntl();
  if (!events.length) return null;

  const graph = graphProp ?? buildTraceGraphFromEvents(events);

  return (
    <div className={styles.messageTurnTrace}>
      <Collapse
        ghost
        size="small"
        defaultActiveKey={streaming ? ["trace"] : []}
        items={[
          {
            key: "trace",
            label: (
              <span className={styles.messageTurnTraceLabel}>
                <BugOutlined />
                {intl.formatMessage(
                  { id: "aiAssistant.trace.eventCount" },
                  { count: events.length },
                )}
                {runId ? (
                  <Text type="secondary" className={styles.traceRunId}>
                    {runId.slice(0, 8)}
                  </Text>
                ) : null}
              </span>
            ),
            children: (
              <>
                <TraceGraphView graph={graph} events={events} />
              </>
            ),
          },
        ]}
      />
    </div>
  );
}

/** 结合 HITL 中断与工具块终态推导计划步骤展示状态 */
function resolvePlanStepDisplayStatus(
  step: PlanStep,
  hitlPayload?: HitlPayload | null,
  blocks?: AiMessageBlock[],
  options?: { streaming?: boolean },
): PlanStep["status"] {
  if (
    hitlPayload?.type === "plan_confirm" &&
    (step.status === "pending" || step.status === "awaiting_confirm")
  ) {
    return "awaiting_confirm";
  }
  // 计划已批准执行后，历史 awaiting_confirm 不应继续展示为「等待计划确认」
  if (step.status === "awaiting_confirm" && hitlPayload?.type !== "plan_confirm") {
    return "pending";
  }
  if (
    hitlPayload &&
    step.tool === hitlPayload.tool &&
    (step.status === "running" || step.status === "error")
  ) {
    return "awaiting_hitl";
  }
  // 用户已提交 HITL（interrupt 已清）且本轮仍在流式续跑：显示执行中
  if (options?.streaming && !hitlPayload && step.status === "awaiting_hitl") {
    return "running";
  }
  // 导航 HITL 时，误触发的 export 步骤不再展示为 running
  if (
    hitlPayload?.tool &&
    hitlPayload.tool !== step.tool &&
    step.tool === "download_file" &&
    step.status === "running"
  ) {
    return "skipped";
  }
  // 后续工具 HITL 时，前序 running 步在顺序 ReAct 中应视为已完成（plan_update 未同步兜底）
  if (
    hitlPayload?.tool &&
    step.tool &&
    step.tool !== hitlPayload.tool &&
    step.status === "running" &&
    step.tool !== "download_file"
  ) {
    return "done";
  }
  // 工具块已结束但 plan 步仍为 running/awaiting_hitl：以工具块终态为准
  // 流式续跑中勿用旧终态覆盖（用户刚确认、尚在等待 tool_start/tool_end）
  if (
    blocks?.length &&
    !(options?.streaming && (step.status === "awaiting_hitl" || step.status === "running"))
  ) {
    const inferred = inferPlanStepStatusFromToolBlocks(step, blocks);
    if (inferred) return inferred;
  }
  return step.status;
}

/** 多步任务进度（嵌入消息内） */
export function MessagePlanSection({
  planSteps,
  planGraph,
  planFlowDocument: _planFlowDocument,
  planReplanReason,
  hitlPayload,
  blocks,
  streaming,
}: {
  planSteps: PlanStep[];
  planGraph?: PlanGraph | null;
  /** M1 无 BPMN 画布，仅接收以免调用方类型失败 */
  planFlowDocument?: FlowDocumentJSON | null;
  planReplanReason?: string | null;
  hitlPayload?: HitlPayload | null;
  blocks?: AiMessageBlock[];
  /** 本轮助手消息是否仍在流式续跑（HITL 提交后等待 tool_end） */
  streaming?: boolean;
}) {
  void _planFlowDocument;
  const intl = useIntl();
  if (planSteps.length < 1) return null;

  const displaySteps = planSteps.map((s) => ({
    ...s,
    status: resolvePlanStepDisplayStatus(s, hitlPayload, blocks, {
      streaming,
    }),
  }));

  return (
    <div className={styles.messageTurnPlan}>
      <Text className={styles.taskProgressTitle}>
        {intl.formatMessage({ id: "aiAssistant.plan.title" })}
      </Text>
      {planReplanReason ? (
        <Alert
          type="warning"
          showIcon
          className={styles.planReplanAlert}
          title={intl.formatMessage({ id: "aiAssistant.plan.replanTitle" })}
          description={planReplanReason}
        />
      ) : null}
      <PlanFlowChart
        steps={displaySteps}
        graph={planGraph ?? hitlPayload?.graph}
        layout="timeline"
        showStatus
        showToolTag={false}
      />
    </div>
  );
}

/** 查询结果：消息内入口按钮；表格固定在右侧 Workspace 侧栏（与消息卡并存） */
export function MessageWorkspaceSection({
  content,
}: {
  content: WorkspaceContent;
  /** 保留签名以兼容消息卡调用链；表格追问在侧栏内处理 */
  onSend?: (text: string) => void;
}) {
  const intl = useIntl();
  const openWorkspacePanel = useAiAssistantStore((s) => s.openWorkspacePanel);

  if (content.kind === "device_command") {
    return <DeviceCommandResultPanel data={content} />;
  }
  if (content.kind === "export_download") {
    return <ExportResultPanel data={content} />;
  }

  const isAlarm = content.kind === "alarm_query";
  const isDeviceList = content.kind === "device_list";
  const isDevice = content.kind === "device_detail";
  const isVarRealtime = content.kind === "device_variable_realtime";
  const isVarHistory = content.kind === "device_variable_history";

  const timeLabel =
    isAlarm && content.timeRange?.start && content.timeRange?.end
      ? `${content.timeRange.start} ~ ${content.timeRange.end}`
      : isVarHistory && content.timeRange?.start && content.timeRange?.end
        ? `${content.timeRange.start} ~ ${content.timeRange.end}`
        : null;

  const totalLabel =
    (isAlarm || isDeviceList) && content.ok && content.total > 0
      ? intl.formatMessage({ id: "aiAssistant.workspace.total" }, { count: content.total })
      : null;

  const viewButtonLabel = isDevice
    ? intl.formatMessage({ id: "aiAssistant.workspace.viewDeviceDetail" })
    : isDeviceList
      ? intl.formatMessage({ id: "aiAssistant.workspace.viewDeviceList" })
      : isVarRealtime
        ? intl.formatMessage({ id: "aiAssistant.workspace.viewVarRealtime" })
        : isVarHistory
          ? intl.formatMessage({ id: "aiAssistant.workspace.viewVarHistory" })
          : intl.formatMessage({ id: "aiAssistant.workspace.viewResults" });

  const deviceNameSuffix =
    isDevice && content.ok && content.device.deviceName
      ? ` · ${content.device.deviceName}`
      : isVarRealtime && content.ok && content.deviceName
        ? ` · ${content.deviceName}`
        : isVarHistory && content.ok && content.deviceName
          ? ` · ${content.deviceName}`
          : "";

  return (
    <Button
      type="default"
      size="small"
      icon={<TableOutlined />}
      className={styles.messageTurnWorkspaceBtn}
      onClick={() => openWorkspacePanel(content)}
    >
      {viewButtonLabel}
      {deviceNameSuffix}
      {timeLabel ? ` · ${timeLabel}` : ""}
      {totalLabel ? ` · ${totalLabel}` : ""}
    </Button>
  );
}
