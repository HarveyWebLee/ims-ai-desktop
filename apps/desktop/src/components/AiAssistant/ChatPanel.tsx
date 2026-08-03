/**
 * 聊天面板：消息区 + 输入（HITL 交互嵌入消息卡片）
 */
import { useEffect, useRef } from "react";
import MessageList from "./MessageList";
import MessageInput from "./MessageInput";
import { useAiAssistantStore } from "./store";
import { useAgentStream } from "./hooks/useAgentStream";
import { isActiveInterruptBlock } from "./utils/hitlInterruptUtils";
import styles from "./index.module.less";

export default function ChatPanel() {
  const { messages, isStreaming, isLoadingHistory, pendingInterrupt } = useAiAssistantStore();
  const { sendMessage, loadSessions, submitHitlResume, submitHitlConfirm, abortStream } =
    useAgentStream();

  const messageAreaRef = useRef<HTMLDivElement>(null);

  /** 是否存在待处理 HITL（store 或未终态 interrupt 块） */
  const hasPendingHitl =
    !!pendingInterrupt ||
    messages.some((m) => m.role === "assistant" && m.blocks.some((b) => isActiveInterruptBlock(b)));

  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  useEffect(() => {
    const el = messageAreaRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [messages, pendingInterrupt, isStreaming, isLoadingHistory]);

  return (
    <div className={styles.chatPanel}>
      <div className={styles.messageArea} ref={messageAreaRef}>
        <MessageList
          messages={messages}
          loading={isStreaming}
          loadingHistory={isLoadingHistory}
          onHitlSubmit={submitHitlResume}
          onHitlConfirm={submitHitlConfirm}
          onSend={sendMessage}
        />
      </div>

      <MessageInput
        onSend={sendMessage}
        onAbort={abortStream}
        disabled={isLoadingHistory || hasPendingHitl}
      />
    </div>
  );
}
