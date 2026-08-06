/**
 * Workspace 结构化内容渲染（消息弹窗 / 右侧固定侧栏复用）
 */
import { Typography } from "antd";
import { useIntl } from "react-intl";
import type { WorkspaceContent } from "./types";
import { AlarmQueryTable } from "./AlarmQueryTable";
import { DeviceDetailPanel } from "./DeviceDetailPanel";
import DeviceCommandResultPanel from "./DeviceCommandResultPanel";
import { DeviceListTable } from "./DeviceListTable";
import ExportResultPanel from "./ExportResultPanel";
import { DeviceVariableHistoryPanel, DeviceVariableRealtimePanel } from "./DeviceVariablePanels";
import styles from "./index.module.less";

const { Text } = Typography;

/** 适合固定侧栏展示的结果类型（小结果卡仍可留在消息内） */
export function isPinnedWorkspaceKind(content: WorkspaceContent): boolean {
  return (
    content.kind === "alarm_query" ||
    content.kind === "device_list" ||
    content.kind === "device_detail" ||
    content.kind === "device_variable_realtime" ||
    content.kind === "device_variable_history"
  );
}

export function workspacePanelTitleId(content: WorkspaceContent): string {
  switch (content.kind) {
    case "device_detail":
      return "aiAssistant.workspace.deviceTitle";
    case "device_list":
      return "aiAssistant.workspace.deviceListTitle";
    case "device_variable_realtime":
      return "aiAssistant.workspace.varRealtimeTitle";
    case "device_variable_history":
      return "aiAssistant.workspace.varHistoryTitle";
    case "device_command":
      return "aiAssistant.workspace.deviceCmdSuccess";
    case "export_download":
      return "aiAssistant.workspace.exportSuccess";
    default:
      return "aiAssistant.workspace.title";
  }
}

export function WorkspaceContentView({
  content,
  onSend,
  compact = false,
}: {
  content: WorkspaceContent;
  onSend?: (text: string) => void;
  /** 侧栏内略增高表格可视区域 */
  compact?: boolean;
}) {
  const intl = useIntl();

  if (content.kind === "device_command") {
    return <DeviceCommandResultPanel data={content} />;
  }
  if (content.kind === "export_download") {
    return <ExportResultPanel data={content} />;
  }

  const timeLabel =
    content.kind === "alarm_query" && content.timeRange?.start && content.timeRange?.end
      ? `${content.timeRange.start} ~ ${content.timeRange.end}`
      : content.kind === "device_variable_history" &&
          content.timeRange?.start &&
          content.timeRange?.end
        ? `${content.timeRange.start} ~ ${content.timeRange.end}`
        : null;

  return (
    <div className={styles.workspaceContentView}>
      {timeLabel ? (
        <Text type="secondary" className={styles.workspaceMeta}>
          {intl.formatMessage({ id: "aiAssistant.workspace.timeRange" })}：{timeLabel}
        </Text>
      ) : null}
      {content.kind === "alarm_query" && (
        <AlarmQueryTable data={content} modalMode={compact} onSend={onSend} />
      )}
      {content.kind === "device_list" && (
        <DeviceListTable data={content} modalMode={compact} onSend={onSend} />
      )}
      {content.kind === "device_detail" && <DeviceDetailPanel data={content} />}
      {content.kind === "device_variable_realtime" && (
        <DeviceVariableRealtimePanel data={content} />
      )}
      {content.kind === "device_variable_history" && <DeviceVariableHistoryPanel data={content} />}
      {content.kind === "alarm_query" ? (
        <Text type="secondary" className={styles.workspaceHint}>
          {intl.formatMessage({ id: "aiAssistant.workspace.rowHint" })}
        </Text>
      ) : null}
      {content.kind === "device_list" ? (
        <Text type="secondary" className={styles.workspaceHint}>
          {intl.formatMessage({ id: "aiAssistant.workspace.deviceListRowHint" })}
        </Text>
      ) : null}
    </div>
  );
}
