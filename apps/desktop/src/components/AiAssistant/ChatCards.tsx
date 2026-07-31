/**
 * AI 助手聊天卡片组件
 */
import { UserOutlined } from "@ant-design/icons";
import { Avatar, Spin } from "antd";
import { useIntl } from "react-intl";
import MarkdownContent from "@/components/MarkdownContent";
import type { AiMessage } from "./types";
import { filterPlanStepsForMessage, partitionAssistantBlocks } from "./chatCardUtils";
import {
  shouldHideMessagePlanForInteractiveHitl,
  shouldShowHitlQuickActions,
} from "./utils/hitlInterruptUtils";
import {
  MessagePlanSection,
  MessageTraceSection,
  MessageWorkspaceSection,
} from "./MessageTurnSections";
import HitlInteractionCard from "./HitlInteractionCard";
import HitlQuickActions from "./HitlQuickActions";
import type { HitlPayload } from "@ims/shared-types";
import type { FlowDocumentJSON } from "@/components/BpmnFlowgram";
import { resolveWorkspaceFromMessage } from "./utils/workspaceFromTool";
import { AiAvatar } from "./AiAvatar";
import styles from "./index.module.less";

/** 用户消息气泡 */
export function UserMessageCard({ content }: { content: string }) {
  return (
    <div className={styles.userRow}>
      <div className={styles.userBubble}>
        <div className={styles.messageText}>{content}</div>
      </div>
      <Avatar size={28} className={styles.userAvatar} icon={<UserOutlined />} />
    </div>
  );
}

export interface AssistantMessageCardProps {
  message: AiMessage;
  /** 当前消息是否承载可交互 HITL */
  hitlInteractive?: boolean;
  hitlLoading?: boolean;
  onHitlSubmit?: (values: Record<string, unknown>) => void | Promise<void>;
  onHitlConfirm?: (
    approved: boolean,
    options?: {
      steps?: import("@ims/shared-types").PlanStep[];
      graph?: import("@ims/shared-types").PlanGraph;
      flow_document?: FlowDocumentJSON;
    },
  ) => void | Promise<void>;
  onSend?: (text: string) => void;
}

/** 助手回复卡片（含文本、任务计划、HITL 交互；不再单独展示「执行过程」） */
export function AssistantMessageCard({
  message,
  hitlInteractive,
  hitlLoading,
  onHitlSubmit,
  onHitlConfirm,
  onSend,
}: AssistantMessageCardProps) {
  const intl = useIntl();
  const { textBlocks, executionBlocks, interruptBlock } = partitionAssistantBlocks(message.blocks);

  const hitlRejected =
    !hitlInteractive &&
    !!interruptBlock &&
    executionBlocks.some(
      (b) =>
        b.type === "tool_call" &&
        b.status === "cancelled" &&
        b.tool === interruptBlock.payload.tool,
    );

  const hitlPayload = interruptBlock ? (interruptBlock.payload as HitlPayload) : null;
  const hideMessagePlan = shouldHideMessagePlanForInteractiveHitl(hitlPayload, !!hitlInteractive);

  const visiblePlanSteps = filterPlanStepsForMessage(message.planSteps ?? [], message.blocks);

  const workspaceContent = message.workspaceContent ?? resolveWorkspaceFromMessage(message);

  // 气泡内实际渲染的内容（工具块仅驱动 Plan/HITL，不再单独成卡）
  const hasRenderedContent =
    textBlocks.some((b) => b.type === "text" && b.content.trim().length > 0) ||
    (!hideMessagePlan && visiblePlanSteps.length > 0) ||
    !!workspaceContent ||
    !!interruptBlock ||
    (message.traceEvents?.length ?? 0) > 0 ||
    !!message.traceGraph;

  /* 纯思考态：头像与提示同一中线，不套气泡边框 */
  if (message.streaming && !hasRenderedContent) {
    return (
      <div className={`${styles.assistantRow} ${styles.assistantRowThinking}`}>
        <AiAvatar size={32} />
        <div className={styles.streamingHint}>
          <Spin size="small" />
          <span>{intl.formatMessage({ id: "aiAssistant.thinkingHint" })}</span>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.assistantRow}>
      <AiAvatar size={32} />
      <div className={styles.assistantBubble}>
        {/* 1. Trace（执行观测，默认折叠） */}
        <MessageTraceSection
          events={message.traceEvents ?? []}
          runId={message.runId}
          streaming={message.streaming}
          graph={message.traceGraph}
        />

        {interruptBlock && hitlInteractive && shouldShowHitlQuickActions(hitlPayload, true) ? (
          <HitlQuickActions payload={interruptBlock.payload as HitlPayload} />
        ) : null}

        {/* 2. 多步任务计划（plan_confirm 待确认时由 HITL 卡片统一承载） */}
        {!hideMessagePlan ? (
          <MessagePlanSection
            planSteps={visiblePlanSteps}
            planGraph={
              visiblePlanSteps.length === (message.planSteps ?? []).length
                ? message.planGraph
                : null
            }
            planReplanReason={message.planReplanReason}
            hitlPayload={hitlPayload}
            blocks={message.blocks}
            streaming={!!message.streaming}
          />
        ) : null}

        {/* 3. 自然语言总结 */}
        {textBlocks.map((block, i) =>
          block.type === "text" ? (
            <MarkdownContent
              key={i}
              content={block.content}
              className={styles.messageText}
              compact
              streaming={!!message.streaming && i === textBlocks.length - 1}
            />
          ) : null,
        )}

        {/* 4. 结构化查询结果（按钮 + 弹窗） */}
        {workspaceContent ? (
          <MessageWorkspaceSection content={workspaceContent} onSend={onSend} />
        ) : null}

        {interruptBlock && (
          <HitlInteractionCard
            payload={interruptBlock.payload as HitlPayload}
            interactive={!!hitlInteractive}
            rejected={hitlRejected}
            loading={hitlLoading}
            onSubmit={onHitlSubmit}
            onConfirm={onHitlConfirm}
          />
        )}

        {message.streaming && hasRenderedContent ? (
          <div className={styles.streamingHint}>
            <Spin size="small" />
            <span>…</span>
          </div>
        ) : null}
      </div>
    </div>
  );
}
