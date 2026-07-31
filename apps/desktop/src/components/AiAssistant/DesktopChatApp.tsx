/**
 * 桌面端 AI 聊天主界面（全屏）
 */
import { useState } from "react";
import { Button, Layout, Tooltip, message } from "antd";
import {
  RobotOutlined,
  PlusOutlined,
  HistoryOutlined,
  AuditOutlined,
  CloudSyncOutlined,
  LogoutOutlined,
} from "@ant-design/icons";
import { useIntl } from "@umijs/max";
import { logout as clearAuth } from "@ims/desktop-api";
import * as AgentController from "@/services/AgentController";
import SessionHistoryDrawer from "./SessionHistoryDrawer";
import AuditLogDrawer from "./AuditLogDrawer";
import ChatPanel from "./ChatPanel";
import { useAiAssistantStore } from "./store";
import styles from "./index.module.less";

const { Header, Content } = Layout;

export default function DesktopChatApp() {
  const intl = useIntl();
  const [historyOpen, setHistoryOpen] = useState(false);
  const [auditOpen, setAuditOpen] = useState(false);
  const [entitySyncing, setEntitySyncing] = useState(false);
  const { createNewSession } = useAiAssistantStore();

  const handleEntitySync = async () => {
    if (entitySyncing) return;
    setEntitySyncing(true);
    const hide = message.loading(intl.formatMessage({ id: "aiAssistant.entitySync.running" }), 0);
    try {
      const result = await AgentController.triggerEntitySync();
      hide();
      if (result.skipped && result.reason === "empty_config") {
        message.info(intl.formatMessage({ id: "aiAssistant.entitySync.skippedEmpty" }));
        return;
      }
      const missing = result.missing_tables?.filter(Boolean) ?? [];
      if (missing.length > 0) {
        message.warning(
          intl.formatMessage(
            { id: "aiAssistant.entitySync.missingTables" },
            { tables: missing.join(", ") },
          ),
        );
      }
      message.success(
        result.message || intl.formatMessage({ id: "aiAssistant.entitySync.success" }),
      );
    } catch (err) {
      hide();
      message.error(
        intl.formatMessage(
          { id: "aiAssistant.entitySync.failed" },
          { reason: err instanceof Error ? err.message : String(err) },
        ),
      );
    } finally {
      setEntitySyncing(false);
    }
  };

  return (
    <Layout className={styles.desktopRoot}>
      <Header className={styles.desktopHeader}>
        <div className={styles.desktopTitle}>
          <span className={styles.desktopTitleIcon} aria-hidden>
            <RobotOutlined />
          </span>
          {intl.formatMessage({ id: "aiAssistant.title" })}
        </div>
        <div className={styles.desktopHeaderActions}>
          <Tooltip title={intl.formatMessage({ id: "aiAssistant.entitySync.tooltip" })}>
            <Button
              type="text"
              className={styles.desktopHeaderIconBtn}
              icon={<CloudSyncOutlined />}
              loading={entitySyncing}
              onClick={() => void handleEntitySync()}
            />
          </Tooltip>
          <Tooltip
            title={intl.formatMessage({
              id: "aiAssistant.session.historyTitle",
            })}
          >
            <Button
              type="text"
              className={styles.desktopHeaderIconBtn}
              icon={<HistoryOutlined />}
              onClick={() => setHistoryOpen(true)}
            />
          </Tooltip>
          <Tooltip title={intl.formatMessage({ id: "aiAssistant.audit.title" })}>
            <Button
              type="text"
              className={styles.desktopHeaderIconBtn}
              icon={<AuditOutlined />}
              onClick={() => setAuditOpen(true)}
            />
          </Tooltip>
          <Button
            type="primary"
            className={styles.desktopNewChatBtn}
            icon={<PlusOutlined />}
            onClick={() => createNewSession()}
          >
            {intl.formatMessage({ id: "aiAssistant.newChat" })}
          </Button>
          <Button
            type="text"
            className={styles.desktopLogoutBtn}
            icon={<LogoutOutlined />}
            onClick={() => {
              clearAuth();
              window.location.reload();
            }}
          >
            {intl.formatMessage({ id: "aiAssistant.logout" })}
          </Button>
        </div>
      </Header>
      <Content className={styles.desktopContent}>
        <ChatPanel />
      </Content>
      <SessionHistoryDrawer open={historyOpen} onClose={() => setHistoryOpen(false)} />
      <AuditLogDrawer open={auditOpen} onClose={() => setAuditOpen(false)} />
    </Layout>
  );
}
