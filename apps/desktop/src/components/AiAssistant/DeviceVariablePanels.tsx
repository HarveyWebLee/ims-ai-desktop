/**
 * 设备变量实时值 / 历史摘要 Workspace 面板
 */
import { Button, Descriptions, Empty, Space, Table, Typography } from "antd";
import { useIntl } from "react-intl";
import { executeClientAction } from "./ClientToolExecutor";
import type { DeviceVariableHistoryWorkspace, DeviceVariableRealtimeWorkspace } from "./types";
import styles from "./index.module.less";

const { Text } = Typography;

function formatVarValue(value: string | number | null | undefined, unit?: string): string {
  if (value == null || String(value).trim() === "") {
    return "—";
  }
  const text = String(value);
  return unit ? `${text} ${unit}` : text;
}

export function DeviceVariableRealtimePanel({ data }: { data: DeviceVariableRealtimeWorkspace }) {
  const intl = useIntl();
  if (!data.ok) {
    return (
      <Text type="danger" className={styles.workspaceError}>
        {data.summary || intl.formatMessage({ id: "aiAssistant.workspace.varRealtimeFailed" })}
      </Text>
    );
  }

  const items =
    data.items && data.items.length > 0
      ? data.items
      : [
          {
            varName: data.varName,
            showName: data.showName,
            value: data.value,
            unit: data.unit,
            updatedAt: data.updatedAt,
            hasValue: data.value != null && String(data.value).trim() !== "",
          },
        ];

  const showTable = items.length > 1 || data.scope === "all";

  return (
    <Space direction="vertical" size="middle" style={{ width: "100%" }}>
      <Text type="secondary">
        {data.summary ||
          intl.formatMessage(
            { id: "aiAssistant.workspace.varRealtimeSummary" },
            { count: data.total ?? items.length },
          )}
      </Text>
      <Text type="secondary">
        {intl.formatMessage({ id: "aiAssistant.workspace.deviceCol.name" })}：
        {data.deviceName || "-"}
        {data.deviceCode ? `（${data.deviceCode}）` : ""}
      </Text>
      {showTable ? (
        <Table
          size="small"
          rowKey={(row, index) => String(row.varName || row.showName || index)}
          pagination={
            items.length > 10 ? { pageSize: 10, size: "small", showSizeChanger: false } : false
          }
          dataSource={items}
          scroll={{ y: 320, x: 480 }}
          columns={[
            {
              title: intl.formatMessage({
                id: "aiAssistant.workspace.varCol.variable",
              }),
              key: "variable",
              ellipsis: true,
              render: (_, row) => {
                const label = row.showName || row.varName || "-";
                if (row.varName && row.showName && row.showName !== row.varName) {
                  return `${label} (${row.varName})`;
                }
                return label;
              },
            },
            {
              title: intl.formatMessage({
                id: "aiAssistant.workspace.varCol.value",
              }),
              key: "value",
              width: 140,
              render: (_, row) => formatVarValue(row.value, row.unit),
            },
            {
              title: intl.formatMessage({
                id: "aiAssistant.workspace.varCol.updatedAt",
              }),
              dataIndex: "updatedAt",
              width: 160,
              ellipsis: true,
              render: (v: string | number | undefined) =>
                v != null && String(v).trim() !== "" ? String(v) : "—",
            },
          ]}
        />
      ) : (
        <Descriptions size="small" column={1} bordered>
          <Descriptions.Item
            label={intl.formatMessage({
              id: "aiAssistant.workspace.varCol.variable",
            })}
          >
            {items[0]?.showName || items[0]?.varName || "-"}
            {items[0]?.varName && items[0]?.showName && items[0].showName !== items[0].varName
              ? ` (${items[0].varName})`
              : ""}
          </Descriptions.Item>
          <Descriptions.Item
            label={intl.formatMessage({
              id: "aiAssistant.workspace.varCol.value",
            })}
          >
            {formatVarValue(items[0]?.value, items[0]?.unit)}
          </Descriptions.Item>
          <Descriptions.Item
            label={intl.formatMessage({
              id: "aiAssistant.workspace.varCol.updatedAt",
            })}
          >
            {items[0]?.updatedAt != null && String(items[0].updatedAt).trim() !== ""
              ? String(items[0].updatedAt)
              : "—"}
          </Descriptions.Item>
        </Descriptions>
      )}
    </Space>
  );
}

export function DeviceVariableHistoryPanel({ data }: { data: DeviceVariableHistoryWorkspace }) {
  const intl = useIntl();

  if (!data.ok) {
    return (
      <Text type="danger" className={styles.workspaceError}>
        {data.summary || intl.formatMessage({ id: "aiAssistant.workspace.varHistoryFailed" })}
      </Text>
    );
  }

  const handleOpenCurve = () => {
    if (!data.navigate?.path) return;
    void executeClientAction({
      action: "navigate",
      path: data.navigate.path,
      query: data.navigate.query,
    });
  };

  return (
    <Space direction="vertical" size="middle" style={{ width: "100%" }}>
      <Text type="secondary">
        {data.summary ||
          intl.formatMessage(
            { id: "aiAssistant.workspace.varHistorySummary" },
            { count: data.pointCount ?? data.points.length },
          )}
      </Text>
      {data.timeRange?.start && data.timeRange?.end ? (
        <Text type="secondary">
          {intl.formatMessage({ id: "aiAssistant.workspace.timeRange" })}：{data.timeRange.start} ~{" "}
          {data.timeRange.end}
        </Text>
      ) : null}
      {data.points.length ? (
        <Table
          size="small"
          rowKey={(_, i) => String(i)}
          pagination={false}
          dataSource={data.points}
          columns={[
            {
              title: intl.formatMessage({
                id: "aiAssistant.workspace.varCol.time",
              }),
              dataIndex: "t",
              render: (v: string | number | undefined) => (v != null ? String(v) : "-"),
            },
            {
              title: intl.formatMessage({
                id: "aiAssistant.workspace.varCol.value",
              }),
              dataIndex: "v",
              render: (v: string | number | null | undefined) =>
                v != null && v !== "" ? String(v) : "-",
            },
          ]}
        />
      ) : (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={intl.formatMessage({
            id: "aiAssistant.workspace.varHistoryEmpty",
          })}
        />
      )}
      {data.navigate?.path ? (
        <Button type="primary" size="small" onClick={handleOpenCurve}>
          {intl.formatMessage({ id: "aiAssistant.workspace.openHistoryCurve" })}
        </Button>
      ) : null}
    </Space>
  );
}
