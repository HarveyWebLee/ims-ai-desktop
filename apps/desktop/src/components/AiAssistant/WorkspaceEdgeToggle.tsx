/**
 * IDEA 风格右侧工具窗切换条：固定在窗口最右，控制结果工作区显隐。
 */
import { TableOutlined } from "@ant-design/icons";
import { Tooltip } from "antd";
import { useIntl } from "react-intl";
import { useAiAssistantStore } from "./store";
import styles from "./index.module.less";

export default function WorkspaceEdgeToggle() {
  const intl = useIntl();
  const sidebarOpen = useAiAssistantStore((s) => s.sidebarOpen);
  const activeWorkspace = useAiAssistantStore((s) => s.activeWorkspace);
  const setSidebarOpen = useAiAssistantStore((s) => s.setSidebarOpen);
  const openWorkspacePanel = useAiAssistantStore((s) => s.openWorkspacePanel);

  const canOpen = Boolean(activeWorkspace) || sidebarOpen;
  const tipId = sidebarOpen ? "aiAssistant.workspace.hidePanel" : "aiAssistant.workspace.openPanel";

  return (
    <aside
      className={styles.workspaceEdgeRail}
      aria-label={intl.formatMessage({ id: "aiAssistant.workspace.panelTitle" })}
    >
      <Tooltip title={intl.formatMessage({ id: tipId })} placement="left">
        <span className={styles.workspaceEdgeToggleWrap}>
          <button
            type="button"
            className={`${styles.workspaceEdgeToggle}${sidebarOpen ? ` ${styles.workspaceEdgeToggleActive}` : ""}`}
            disabled={!canOpen}
            aria-pressed={sidebarOpen}
            aria-label={intl.formatMessage({ id: tipId })}
            onClick={() => {
              if (sidebarOpen) {
                setSidebarOpen(false);
                return;
              }
              if (activeWorkspace) {
                openWorkspacePanel(activeWorkspace);
              }
            }}
          >
            <TableOutlined className={styles.workspaceEdgeToggleIcon} aria-hidden />
            <span className={styles.workspaceEdgeToggleLabel}>
              {intl.formatMessage({ id: "aiAssistant.workspace.panelTitle" })}
            </span>
          </button>
        </span>
      </Tooltip>
    </aside>
  );
}
