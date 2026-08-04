/**
 * 设备列表结果表格（query_devices Workspace）
 * 行点击经 onSend 走 Agent 查详情（可触发 HITL），禁止直连写接口。
 */
import { Empty, Table, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import { useIntl } from "react-intl";
import { useMemo } from "react";
import type { DeviceListItem, DeviceListWorkspace } from "./types";
import styles from "./index.module.less";

const { Text } = Typography;

function rowKeyOf(row: DeviceListItem, index: number): string {
  if (row.deviceCode) return row.deviceCode;
  if (row.deviceName) return `${row.deviceName}-${index}`;
  return `device-${index}`;
}

export function DeviceListTable({
  data,
  modalMode = false,
  onSend,
}: {
  data: DeviceListWorkspace;
  modalMode?: boolean;
  onSend?: (text: string) => void;
}) {
  const intl = useIntl();

  const columns: ColumnsType<DeviceListItem> = useMemo(
    () => [
      {
        title: intl.formatMessage({ id: "aiAssistant.workspace.deviceCol.name" }),
        dataIndex: "deviceName",
        ellipsis: true,
        width: 140,
        render: (v: string) => v || "-",
      },
      {
        title: intl.formatMessage({ id: "aiAssistant.workspace.deviceCol.code" }),
        dataIndex: "deviceCode",
        ellipsis: true,
        width: 120,
        render: (v: string) => v || "-",
      },
      {
        title: intl.formatMessage({ id: "aiAssistant.workspace.deviceCol.online" }),
        dataIndex: "onlineStatusLabel",
        width: 88,
        render: (v: string) => v || "-",
      },
      {
        title: intl.formatMessage({ id: "aiAssistant.workspace.deviceCol.enableStatus" }),
        dataIndex: "enableStatusLabel",
        width: 88,
        render: (_: unknown, row) => row.enableStatusLabel || row.deviceStatusLabel || "-",
      },
      {
        title: intl.formatMessage({ id: "aiAssistant.workspace.deviceCol.region" }),
        dataIndex: "regionName",
        ellipsis: true,
        width: 100,
        render: (v: string | null) => v || "-",
      },
      {
        title: intl.formatMessage({ id: "aiAssistant.workspace.deviceCol.subsystem" }),
        dataIndex: "subSystemName",
        ellipsis: true,
        width: 100,
        render: (v: string | null) => v || "-",
      },
    ],
    [intl],
  );

  if (!data.ok) {
    return (
      <Empty
        description={
          data.summary || intl.formatMessage({ id: "aiAssistant.workspace.deviceListFailed" })
        }
      />
    );
  }

  if (!data.items.length) {
    return <Empty description={intl.formatMessage({ id: "aiAssistant.workspace.noDevices" })} />;
  }

  return (
    <>
      <Table
        size="small"
        rowKey={(row, index) => rowKeyOf(row, index ?? 0)}
        columns={columns}
        dataSource={data.items}
        pagination={false}
        scroll={{ y: modalMode ? 360 : 160, x: 480 }}
        className={styles.workspaceTable}
        onRow={(record) => ({
          onClick: () => {
            if (!onSend) return;
            const code = record.deviceCode?.trim();
            const name = record.deviceName?.trim();
            if (!code && !name) return;
            const prompt = code
              ? intl.formatMessage({ id: "aiAssistant.workspace.deviceListDetailPrompt" }, { code })
              : intl.formatMessage(
                  { id: "aiAssistant.workspace.deviceListDetailPromptByName" },
                  { name: name || "" },
                );
            onSend(prompt);
          },
          className:
            onSend && (record.deviceCode || record.deviceName)
              ? styles.workspaceRowClickable
              : undefined,
        })}
      />
      {onSend ? (
        <Text type="secondary" className={styles.workspaceHint}>
          {intl.formatMessage({ id: "aiAssistant.workspace.deviceListRowHint" })}
        </Text>
      ) : null}
    </>
  );
}
