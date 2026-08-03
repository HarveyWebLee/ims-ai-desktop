/**
 * HITL 人工确认 / 补参交互卡片（嵌入助手消息流）
 */
import { useEffect, useState } from "react";
import { Button, Descriptions, Form, Space, Typography } from "antd";
import { InteractionOutlined } from "@ant-design/icons";
import { useIntl } from "react-intl";
import type { HitlPayload, PlanGraph, PlanStep } from "@ims/shared-types";
import HitlFormField, { buildHitlFieldRules } from "./HitlFormField";
import PlanFlowChart from "./PlanFlowChart";
import { normalizeHitlFormValues } from "./utils/hitlFormUtils";
import { buildPlanGraphFromSteps } from "./utils/planGraphUtils";
import type { FlowDocumentJSON } from "@/components/BpmnFlowgram";
import styles from "./index.module.less";

const { Text } = Typography;

export interface HitlInteractionCardProps {
  payload: HitlPayload;
  /** 是否为当前待处理项（展示可编辑表单） */
  interactive: boolean;
  /** 非交互态下是否因用户拒绝而结束 */
  rejected?: boolean;
  /** 流式中止导致的终态 */
  aborted?: boolean;
  /** 历史恢复后的可续跑提示（interactive 时展示） */
  resumable?: boolean;
  loading?: boolean;
  onSubmit?: (values: Record<string, unknown>) => void | Promise<void>;
  /** plan_confirm 可附带编排后的 steps */
  onConfirm?: (
    approved: boolean,
    options?: {
      steps?: PlanStep[];
      graph?: PlanGraph;
      flow_document?: FlowDocumentJSON;
    },
  ) => void | Promise<void>;
  /** 编排画布就地改 plan 时回写消息（M1 无画布编辑，可选预留） */
  onPlanOrchestrationApplied?: (payload: {
    steps: PlanStep[];
    graph?: PlanGraph | null;
    flow_document?: FlowDocumentJSON;
  }) => void;
}

export default function HitlInteractionCard({
  payload,
  interactive,
  rejected,
  aborted,
  resumable,
  loading,
  onSubmit,
  onConfirm,
  onPlanOrchestrationApplied: _onPlanOrchestrationApplied,
}: HitlInteractionCardProps) {
  void _onPlanOrchestrationApplied;
  const intl = useIntl();
  const [form] = Form.useForm();
  const isPlanConfirm = payload.type === "plan_confirm";
  const [editableSteps, setEditableSteps] = useState<PlanStep[]>(() => payload.steps ?? []);
  const [editableGraph, setEditableGraph] = useState<PlanGraph | null>(() => payload.graph ?? null);
  useEffect(() => {
    if (isPlanConfirm && payload.steps?.length) {
      setEditableSteps(payload.steps);
      setEditableGraph(payload.graph ?? buildPlanGraphFromSteps(payload.steps));
    }
  }, [isPlanConfirm, payload.steps, payload.graph]);

  const normalizePlanConfirmSteps = (steps: PlanStep[]): PlanStep[] =>
    steps.map((s) => ({
      ...s,
      status: s.status === "skipped" ? ("skipped" as const) : ("awaiting_confirm" as const),
    }));

  const title = payload.message || intl.formatMessage({ id: "aiAssistant.hitl.needParams" });

  const handleFinish = async (values: Record<string, unknown>) => {
    const normalized = normalizeHitlFormValues(values, payload.fields);
    await onSubmit?.(normalized);
    if (interactive) {
      form.resetFields();
    }
  };

  const isConfirm = payload.type === "confirm" || isPlanConfirm;

  if (rejected || aborted) {
    return (
      <div className={styles.hitlCardCompleted}>
        <div className={styles.hitlCompletedHint}>
          {intl.formatMessage({
            id: aborted ? "aiAssistant.card.hitl.aborted" : "aiAssistant.card.hitl.rejected",
          })}
        </div>
      </div>
    );
  }

  if (!interactive && !rejected) {
    return (
      <div className={styles.hitlCardCompleted}>
        <div className={styles.hitlCompletedHint}>
          {intl.formatMessage({ id: "aiAssistant.card.hitl.completed" })}
        </div>
      </div>
    );
  }

  return (
    <div className={interactive ? styles.hitlCard : styles.hitlCardCompleted}>
      <div className={styles.hitlCardHeader}>
        <span className={styles.hitlCardIcon}>
          <InteractionOutlined />
        </span>
        <div className={styles.hitlCardHeaderText}>
          <span className={styles.hitlCardTitle}>
            {intl.formatMessage({
              id: isPlanConfirm
                ? "aiAssistant.card.hitl.planConfirmTitle"
                : isConfirm
                  ? "aiAssistant.card.hitl.confirmTitle"
                  : "aiAssistant.card.hitl.title",
            })}
          </span>
          <span className={styles.hitlCardDesc}>{title}</span>
          {resumable ? (
            <span className={styles.hitlCardDesc}>
              {intl.formatMessage({ id: "aiAssistant.card.hitl.resumable" })}
            </span>
          ) : null}
        </div>
      </div>

      {isPlanConfirm && editableSteps.length ? (
        <div className={styles.hitlPlanPreview}>
          <Text type="secondary" className={styles.hitlPlanPreviewLabel}>
            {intl.formatMessage({ id: "aiAssistant.hitl.planPreview" })}
          </Text>
          <PlanFlowChart
            steps={normalizePlanConfirmSteps(editableSteps)}
            graph={editableGraph ?? payload.graph}
            layout="timeline"
            showStatus
            showToolTag={false}
            hint="none"
          />
        </div>
      ) : null}

      {interactive ? (
        payload.type === "confirm" ? (
          <Space direction="vertical" size="middle" className={styles.hitlConfirmActions}>
            {payload.device_preview ? (
              <div className={styles.hitlDevicePreview}>
                <Text type="secondary" className={styles.hitlPlanPreviewLabel}>
                  {intl.formatMessage({
                    id: "aiAssistant.hitl.devicePreviewTitle",
                  })}
                </Text>
                <Descriptions size="small" column={1} bordered>
                  <Descriptions.Item
                    label={intl.formatMessage({
                      id: "aiAssistant.workspace.deviceCol.name",
                    })}
                  >
                    {payload.device_preview.deviceName || "-"}
                  </Descriptions.Item>
                  <Descriptions.Item
                    label={intl.formatMessage({
                      id: "aiAssistant.workspace.deviceCol.code",
                    })}
                  >
                    {payload.device_preview.deviceCode || "-"}
                  </Descriptions.Item>
                  <Descriptions.Item
                    label={intl.formatMessage({
                      id: "aiAssistant.workspace.deviceCol.online",
                    })}
                  >
                    {payload.device_preview.onlineStatusLabel || "-"}
                  </Descriptions.Item>
                  {payload.device_preview.regionName ? (
                    <Descriptions.Item
                      label={intl.formatMessage({
                        id: "aiAssistant.workspace.deviceCol.region",
                      })}
                    >
                      {payload.device_preview.regionName}
                    </Descriptions.Item>
                  ) : null}
                  <Descriptions.Item
                    label={intl.formatMessage({
                      id: "aiAssistant.workspace.deviceCmdCol.variable",
                    })}
                  >
                    {payload.device_preview.variableName || "-"}
                  </Descriptions.Item>
                  <Descriptions.Item
                    label={intl.formatMessage({
                      id: "aiAssistant.workspace.deviceCmdCol.value",
                    })}
                  >
                    {payload.device_preview.variableValue || "-"}
                  </Descriptions.Item>
                </Descriptions>
              </div>
            ) : null}
            <Space>
              <Button onClick={() => onConfirm?.(false)} disabled={loading}>
                {intl.formatMessage({ id: "aiAssistant.hitl.reject" })}
              </Button>
              <Button type="primary" loading={loading} onClick={() => onConfirm?.(true)}>
                {intl.formatMessage({ id: "aiAssistant.hitl.approve" })}
              </Button>
            </Space>
          </Space>
        ) : payload.type === "plan_confirm" ? (
          <Space className={styles.planConfirmActions}>
            <Button onClick={() => onConfirm?.(false)} disabled={loading}>
              {intl.formatMessage({ id: "aiAssistant.hitl.planReject" })}
            </Button>
            <Button
              type="primary"
              loading={loading}
              onClick={() =>
                onConfirm?.(true, {
                  steps: editableSteps,
                  graph: editableGraph ?? buildPlanGraphFromSteps(editableSteps),
                  flow_document:
                    (payload.flow_document as FlowDocumentJSON | undefined) ?? undefined,
                })
              }
            >
              {intl.formatMessage({ id: "aiAssistant.hitl.planApprove" })}
            </Button>
          </Space>
        ) : payload.type === "ask_params" ? (
          <Form
            form={form}
            layout="vertical"
            className={styles.hitlCardForm}
            onFinish={handleFinish}
          >
            {payload.fields?.map((field) => (
              <Form.Item
                key={field.name}
                name={field.name}
                label={field.type === "device_picker" ? undefined : field.label}
                extra={
                  field.type === "device_picker" ||
                  field.type === "datetime_range" ||
                  field.type === "variable_picker"
                    ? undefined
                    : field.description
                }
                className={
                  field.type === "device_picker"
                    ? `${styles.hitlFormItem} ${styles.hitlFormItemDevicePicker}`
                    : styles.hitlFormItem
                }
                rules={buildHitlFieldRules(field, intl)}
              >
                <HitlFormField field={field} />
              </Form.Item>
            ))}
            {/* 与 confirm / plan_confirm 对称：取消走 reject 续跑，清理 interrupt */}
            <Space className={styles.hitlParamsActions}>
              <Button
                type="default"
                htmlType="button"
                disabled={loading}
                onClick={() => onConfirm?.(false)}
              >
                {intl.formatMessage({ id: "aiAssistant.hitl.reject" })}
              </Button>
              <Button
                type="primary"
                htmlType="submit"
                loading={loading}
                className={styles.hitlSubmitBtn}
              >
                {intl.formatMessage({ id: "aiAssistant.hitl.submitParams" })}
              </Button>
            </Space>
          </Form>
        ) : null
      ) : (
        <div className={styles.hitlCompletedHint}>
          {intl.formatMessage({
            id: rejected ? "aiAssistant.card.hitl.rejected" : "aiAssistant.card.hitl.completed",
          })}
        </div>
      )}
    </div>
  );
}
