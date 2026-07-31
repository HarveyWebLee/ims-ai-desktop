/**
 * 桌面端 AI 聊天主界面（侧栏历史会话 + 聊天区）
 */
import { useState } from "react";
import { Button, Layout, Space, Tooltip, Typography, theme } from "antd";
import { SettingOutlined, LogoutOutlined, MenuUnfoldOutlined } from "@ant-design/icons";
import { useIntl } from "react-intl";
import { logout as clearAuth } from "@ims/desktop-api";
import SessionSidebar from "./SessionSidebar";
import ChatPanel from "./ChatPanel";
import { AiMark } from "./AiAvatar";
import styles from "./index.module.less";

const { Header, Content } = Layout;
const { Text } = Typography;

export default function DesktopChatApp({ onOpenSettings }: { onOpenSettings: () => void }) {
  const intl = useIntl();
  const { token } = theme.useToken();
  const [siderCollapsed, setSiderCollapsed] = useState(false);

  return (
    <Layout className={styles.desktopRoot} hasSider>
      <SessionSidebar collapsed={siderCollapsed} onCollapse={setSiderCollapsed} />
      <Layout className={styles.desktopMain}>
        <Header className={styles.desktopHeader}>
          <div className={styles.desktopTitle}>
            {siderCollapsed ? (
              <Tooltip title={intl.formatMessage({ id: "aiAssistant.session.expandSidebar" })}>
                <Button
                  type="text"
                  className={styles.desktopHeaderIconBtn}
                  icon={<MenuUnfoldOutlined />}
                  onClick={() => setSiderCollapsed(false)}
                  aria-label={intl.formatMessage({ id: "aiAssistant.session.expandSidebar" })}
                />
              </Tooltip>
            ) : null}
            <span
              className={styles.desktopTitleIcon}
              style={{
                background: token.colorPrimary,
                boxShadow: `0 4px 12px ${token.colorPrimary}33`,
              }}
              aria-hidden
            >
              <AiMark size={18} />
            </span>
            <div className={styles.desktopTitleText}>
              <span className={styles.desktopTitleMain}>
                {intl.formatMessage({ id: "aiAssistant.title" })}
              </span>
              <Text type="secondary" className={styles.desktopTitleSub}>
                {intl.formatMessage({ id: "aiAssistant.subtitle" })}
              </Text>
            </div>
          </div>
          <Space size={4} className={styles.desktopHeaderActions} wrap={false}>
            <Tooltip title={intl.formatMessage({ id: "aiAssistant.settings.openTip" })}>
              <Button type="text" icon={<SettingOutlined />} onClick={onOpenSettings}>
                {intl.formatMessage({ id: "aiAssistant.settings.shortTitle" })}
              </Button>
            </Tooltip>
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
          </Space>
        </Header>
        <Content className={styles.desktopContent}>
          <ChatPanel />
        </Content>
      </Layout>
    </Layout>
  );
}
