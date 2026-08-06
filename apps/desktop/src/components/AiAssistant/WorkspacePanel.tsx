/**
 * 右侧固定 Workspace 侧栏：展示最近结构化结果，支持点选追问（经 onSend → Agent）
 */
import { Button, Empty, Layout, Space, Tag, Typography } from "antd";
import { CloseOutlined, TableOutlined } from "@ant-design/icons";
import { useIntl } from "react-intl";
import { useAiAssistantStore } from "./store";
import { WorkspaceContentView, workspacePanelTitleId } from "./WorkspaceContentView";
import styles from "./index.module.less";

const { Sider } = Layout;
const { Text } = Typography;

export default function WorkspacePanel({ onSend }: { onSend: (text: string) => void }) {
  const intl = useIntl();
  const sidebarOpen = useAiAssistantStore((s) => s.sidebarOpen);
  const sidebarWidth = useAiAssistantStore((s) => s.sidebarWidth);
  const activeWorkspace = useAiAssistantStore((s) => s.activeWorkspace);
  const setSidebarOpen = useAiAssistantStore((s) => s.setSidebarOpen);
  const clearActiveWorkspace = useAiAssistantStore((s) => s.clearActiveWorkspace);

  if (!sidebarOpen) {
    return null;
  }

  const totalLabel =
    activeWorkspace &&
    (activeWorkspace.kind === "alarm_query" || activeWorkspace.kind === "device_list") &&
    activeWorkspace.ok &&
    activeWorkspace.total > 0
      ? intl.formatMessage({ id: "aiAssistant.workspace.total" }, { count: activeWorkspace.total })
      : null;

  return (
    <Sider
      theme="light"
      width={sidebarWidth}
      className={styles.workspaceSider}
      aria-label={intl.formatMessage({ id: "aiAssistant.workspace.panelTitle" })}
    >
      <div className={styles.workspaceSiderInner}>
        <div className={styles.workspaceSiderHeader}>
          <Space size={8} wrap className={styles.workspaceSiderTitle}>
            <TableOutlined aria-hidden />
            <Text strong>
              {activeWorkspace
                ? intl.formatMessage({ id: workspacePanelTitleId(activeWorkspace) })
                : intl.formatMessage({ id: "aiAssistant.workspace.panelTitle" })}
            </Text>
            {totalLabel ? (
              <Tag color="green" className={styles.workspaceTotalTag}>
                {totalLabel}
              </Tag>
            ) : null}
          </Space>
          <Button
            type="text"
            size="small"
            icon={<CloseOutlined />}
            aria-label={intl.formatMessage({ id: "aiAssistant.workspace.closePanel" })}
            onClick={() => {
              setSidebarOpen(false);
            }}
          />
        </div>
        <div className={styles.workspaceSiderBody}>
          {activeWorkspace ? (
            <WorkspaceContentView content={activeWorkspace} onSend={onSend} compact />
          ) : (
            <Empty
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              description={intl.formatMessage({ id: "aiAssistant.workspace.panelEmpty" })}
            >
              <Button
                type="link"
                size="small"
                onClick={() => {
                  clearActiveWorkspace();
                  setSidebarOpen(false);
                }}
              >
                {intl.formatMessage({ id: "aiAssistant.workspace.closePanel" })}
              </Button>
            </Empty>
          )}
        </div>
      </div>
    </Sider>
  );
}
