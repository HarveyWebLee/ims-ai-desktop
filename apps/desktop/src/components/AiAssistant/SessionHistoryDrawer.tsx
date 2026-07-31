/**
 * 历史会话抽屉 — 从侧栏顶部入口打开，不占聊天主区域
 */
import { useEffect } from "react";
import { DeleteOutlined } from "@ant-design/icons";
import { Button, Drawer, Empty, Popconfirm, Typography, message } from "antd";
import { useIntl } from "@umijs/max";
import dayjs from "dayjs";
import * as AgentController from "@/services/AgentController";
import { useAiAssistantStore } from "./store";
import { useAgentStream } from "./hooks/useAgentStream";
import styles from "./index.module.less";

const { Text } = Typography;

function formatSessionTime(iso?: string): string {
  if (!iso) return "";
  const d = dayjs(iso);
  if (!d.isValid()) return "";
  const now = dayjs();
  if (now.diff(d, "day") < 1) {
    return d.format("HH:mm");
  }
  if (now.diff(d, "day") < 7) {
    return d.format("ddd HH:mm");
  }
  return d.format("MM-DD HH:mm");
}

export default function SessionHistoryDrawer({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const intl = useIntl();
  const { sessions, currentThreadId, switchSession, createNewSession, setMessages, setSessions } =
    useAiAssistantStore();
  const { loadSessions, loadThreadHistory } = useAgentStream();

  useEffect(() => {
    if (open) {
      void loadSessions();
    }
  }, [open, loadSessions]);

  const handleSwitch = (threadId: string) => {
    switchSession(threadId);
    void loadThreadHistory(threadId);
    onClose();
  };

  const handleDelete = async (threadId: string) => {
    try {
      await AgentController.deleteSession(threadId);
      const nextSessions = sessions.filter((s) => s.thread_id !== threadId);
      setSessions(nextSessions);

      if (threadId === currentThreadId) {
        if (nextSessions.length > 0) {
          const nextId = nextSessions[0].thread_id;
          switchSession(nextId);
          await loadThreadHistory(nextId);
        } else {
          createNewSession();
          setMessages([]);
        }
      }
      message.success(intl.formatMessage({ id: "aiAssistant.session.deleted" }));
    } catch (err) {
      message.error(
        err instanceof Error
          ? err.message
          : intl.formatMessage({ id: "aiAssistant.session.deleteFailed" }),
      );
    }
  };

  return (
    <Drawer
      title={intl.formatMessage({ id: "aiAssistant.session.historyTitle" })}
      placement="left"
      width={Math.min(320, window.innerWidth * 0.85)}
      open={open}
      onClose={onClose}
      className={styles.sessionDrawer}
      destroyOnClose={false}
    >
      {sessions.length === 0 ? (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={intl.formatMessage({ id: "aiAssistant.noSessions" })}
        />
      ) : (
        <ul className={styles.sessionDrawerList}>
          {sessions.map((item) => {
            const active = item.thread_id === currentThreadId;
            return (
              <li
                key={item.thread_id}
                className={active ? styles.sessionDrawerItemActive : styles.sessionDrawerItem}
              >
                <button
                  type="button"
                  className={styles.sessionDrawerItemMain}
                  onClick={() => handleSwitch(item.thread_id)}
                >
                  <Text ellipsis className={styles.sessionDrawerTitle}>
                    {item.title}
                  </Text>
                  <Text type="secondary" className={styles.sessionDrawerTime}>
                    {formatSessionTime(item.updated_at)}
                  </Text>
                </button>
                <Popconfirm
                  title={intl.formatMessage({
                    id: "aiAssistant.session.deleteConfirm",
                  })}
                  okText={intl.formatMessage({ id: "aiAssistant.session.deleteOk" })}
                  cancelText={intl.formatMessage({
                    id: "aiAssistant.session.deleteCancel",
                  })}
                  onConfirm={() => handleDelete(item.thread_id)}
                >
                  <Button
                    type="text"
                    size="small"
                    danger
                    icon={<DeleteOutlined />}
                    className={styles.sessionDrawerDelete}
                    onClick={(e) => e.stopPropagation()}
                    aria-label={intl.formatMessage({
                      id: "aiAssistant.session.deleteAria",
                    })}
                  />
                </Popconfirm>
              </li>
            );
          })}
        </ul>
      )}
    </Drawer>
  );
}
