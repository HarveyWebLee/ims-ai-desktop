/**
 * 消息列表 — 聊天卡片布局
 */
import { useMemo } from "react";
import { RobotOutlined } from "@ant-design/icons";
import { Avatar, Button, Spin } from "antd";
import { useIntl } from "@umijs/max";
import { useAiAssistantStore } from "./store";
import { AssistantMessageCard, UserMessageCard } from "./ChatCards";
import type { AiMessage } from "./types";
import type { FlowDocumentJSON } from "@/components/BpmnFlowgram";
import { extractUserDisplayText } from "./utils/extractUserDisplayText";
import { resolveActiveHitlMessageId } from "./utils/hitlInterruptUtils";
import styles from "./index.module.less";

function getUserText(message: AiMessage): string {
  return message.blocks
    .filter((b) => b.type === "text")
    .map((b) => extractUserDisplayText((b as { type: "text"; content: string }).content))
    .join("");
}

export default function MessageList({
  messages,
  loading,
  onHitlSubmit,
  onHitlConfirm,
  onSend,
}: {
  messages: AiMessage[];
  loading?: boolean;
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
}) {
  const intl = useIntl();
  const { pendingInterrupt, isStreaming } = useAiAssistantStore();

  /** 当前待处理 HITL 所在助手消息 id（interrupt 块 + pendingInterrupt 兜底） */
  const activeHitlMessageId = useMemo(
    () => resolveActiveHitlMessageId(messages, pendingInterrupt),
    [messages, pendingInterrupt],
  );

  /** 流式响应中是否已有助手占位气泡 */
  const hasStreamingAssistant = useMemo(
    () => messages.some((m) => m.role === "assistant" && m.streaming),
    [messages],
  );

  if (!messages.length && !loading) {
    const suggestions = [
      intl.formatMessage({ id: "aiAssistant.emptySuggest.alarms" }),
      intl.formatMessage({ id: "aiAssistant.emptySuggest.yesterday" }),
      intl.formatMessage({ id: "aiAssistant.emptySuggest.navigate" }),
    ];
    return (
      <div className={styles.emptyState}>
        <div className={styles.emptyStateBadge} aria-hidden>
          <RobotOutlined />
        </div>
        <h2 className={styles.emptyStateTitle}>
          {intl.formatMessage({ id: "aiAssistant.emptyWelcome" })}
        </h2>
        <p className={styles.emptyStateDesc}>
          {intl.formatMessage({ id: "aiAssistant.emptyHint" })}
        </p>
        <div className={styles.emptyStateSuggestions}>
          {suggestions.map((text) => (
            <Button key={text} className={styles.emptyStateChip} onClick={() => onSend?.(text)}>
              {text}
            </Button>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className={styles.messageList}>
      {messages.map((msg) => {
        if (msg.role === "user") {
          return <UserMessageCard key={msg.id} content={getUserText(msg)} />;
        }

        return (
          <AssistantMessageCard
            key={msg.id}
            message={msg}
            hitlInteractive={msg.id === activeHitlMessageId}
            hitlLoading={isStreaming && msg.id === activeHitlMessageId}
            onHitlSubmit={onHitlSubmit}
            onHitlConfirm={onHitlConfirm}
            onSend={onSend}
          />
        );
      })}
      {loading && !hasStreamingAssistant ? (
        <div className={styles.assistantRow}>
          <Avatar size={28} className={styles.assistantAvatar} icon={<RobotOutlined />} />
          <div className={styles.assistantBubble}>
            <div className={styles.streamingHint}>
              <Spin size="small" />
              <span>{intl.formatMessage({ id: "aiAssistant.thinkingHint" })}</span>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
