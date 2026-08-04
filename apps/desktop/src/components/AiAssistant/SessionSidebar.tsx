/**
 * 左侧历史会话侧栏
 */
import { useEffect } from "react";
import { DeleteOutlined, MenuFoldOutlined, PlusOutlined } from "@ant-design/icons";
import { Button, Empty, Layout, Popconfirm, Space, Tooltip, Typography } from "antd";
import { message } from "@/antd/feedback";
import { useIntl } from "react-intl";
import dayjs from "dayjs";
import * as AgentController from "@/services/AgentController";
import { useAiAssistantStore } from "./store";
import { useAgentStream } from "./hooks/useAgentStream";
import styles from "./index.module.less";

const { Sider } = Layout;
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

export default function SessionSidebar({
  collapsed,
  onCollapse,
}: {
  collapsed: boolean;
  onCollapse: (collapsed: boolean) => void;
}) {
  const intl = useIntl();
  const {
    sessions,
    currentThreadId,
    switchSession,
    createNewSession,
    setSessions,
    streamingByThread,
  } = useAiAssistantStore();
  const { loadSessions, loadThreadHistory, disposeThreadRuntime } = useAgentStream();

  useEffect(() => {
    void loadSessions();
  }, [loadSessions]);

  const handleSwitch = (threadId: string) => {
    if (threadId === currentThreadId) return;
    switchSession(threadId);
    // 有快照或后台流时 loadThreadHistory 会自行跳过
    void loadThreadHistory(threadId);
  };

  const handleDelete = async (threadId: string) => {
    try {
      disposeThreadRuntime(threadId);
      await AgentController.deleteSession(threadId);
      setSessions(sessions.filter((s) => s.thread_id !== threadId));

      // 删除当前选中会话时进入空白新会话，不自动切到下一条历史
      if (threadId === currentThreadId) {
        createNewSession();
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
    <Sider
      className={styles.sessionSider}
      width={268}
      collapsedWidth={0}
      collapsible
      collapsed={collapsed}
      onCollapse={onCollapse}
      trigger={null}
      theme="light"
    >
      <div className={styles.sessionSiderInner}>
        <div className={styles.sessionSiderHeader}>
          <Text strong className={styles.sessionSiderTitle}>
            {intl.formatMessage({ id: "aiAssistant.session.historyTitle" })}
          </Text>
          <Space size={4}>
            <Tooltip title={intl.formatMessage({ id: "aiAssistant.session.collapseSidebar" })}>
              <Button
                type="text"
                size="small"
                className={styles.sessionSiderIconBtn}
                icon={<MenuFoldOutlined />}
                onClick={() => onCollapse(true)}
                aria-label={intl.formatMessage({ id: "aiAssistant.session.collapseSidebar" })}
              />
            </Tooltip>
          </Space>
        </div>

        <div className={styles.sessionSiderActions}>
          <Button type="primary" block icon={<PlusOutlined />} onClick={() => createNewSession()}>
            {intl.formatMessage({ id: "aiAssistant.newChat" })}
          </Button>
        </div>

        <div className={styles.sessionSiderList}>
          {sessions.length === 0 ? (
            <div className={styles.sessionSiderEmpty}>
              <Empty
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description={
                  <span className={styles.sessionSiderEmptyDesc}>
                    {intl.formatMessage({ id: "aiAssistant.noSessions" })}
                    <br />
                    <Text type="secondary" className={styles.sessionSiderEmptyHint}>
                      {intl.formatMessage({ id: "aiAssistant.session.emptyHint" })}
                    </Text>
                  </span>
                }
              />
            </div>
          ) : (
            <ul className={styles.sessionDrawerList}>
              {sessions.map((item) => {
                const active = item.thread_id === currentThreadId;
                const running = Boolean(streamingByThread[item.thread_id]);
                return (
                  <li
                    key={item.thread_id}
                    className={[
                      styles.sessionDrawerItem,
                      active ? styles.sessionDrawerItemActive : "",
                    ]
                      .filter(Boolean)
                      .join(" ")}
                  >
                    <button
                      type="button"
                      className={styles.sessionDrawerItemMain}
                      onClick={() => handleSwitch(item.thread_id)}
                    >
                      <Text ellipsis className={styles.sessionDrawerTitle}>
                        {item.title}
                        {running ? <span className={styles.sessionRunningDot} aria-hidden /> : null}
                      </Text>
                      <Text type="secondary" className={styles.sessionDrawerTime}>
                        {running
                          ? intl.formatMessage({ id: "aiAssistant.session.running" })
                          : formatSessionTime(item.updated_at)}
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
                      onConfirm={() => void handleDelete(item.thread_id)}
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
        </div>
      </div>
    </Sider>
  );
}
