/**
 * 告警查询结果表格（供消息内弹窗复用）
 * 支持服务端分页：有 queryContext 时翻页调用平台 getAlarmList
 */
import { Empty, Space, Table, Tag, Typography, Button, message } from "antd";
import type { ColumnsType, TablePaginationConfig } from "antd/es/table";
import { useIntl } from "@umijs/max";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { AlarmQueryWorkspace } from "./types";
import { useAiAssistantStore } from "./store";
import { fetchAlarmQueryPage } from "./utils/alarmListPage";
import styles from "./index.module.less";

const { Text } = Typography;

const DEFAULT_PAGE_SIZE = 20;
const PAGE_SIZE_OPTIONS = [10, 20, 50];

function statusTagColor(statusName?: string): string {
  if (!statusName) return "default";
  if (statusName.includes("待确认") || statusName.includes("未处理")) return "orange";
  if (statusName.includes("已确认")) return "blue";
  if (statusName.includes("已处理")) return "green";
  return "default";
}

/** 生成表格行唯一键（antd 5.x 起 rowKey 回调的 index 参数已弃用） */
function rowKeyOf(row: AlarmQueryWorkspace["items"][0]): string {
  if (row.id != null && row.id !== "") {
    return String(row.id);
  }
  return [row.startTime, row.deviceName, row.variableName, row.statusName, row.alarmRankName]
    .map((v) => String(v ?? ""))
    .join("|");
}

export function AlarmQueryTable({
  data,
  modalMode = false,
  onSend,
}: {
  data: AlarmQueryWorkspace;
  modalMode?: boolean;
  /** 对本查询结果发起批量确认/处理（走 Agent + HITL，禁止直调写接口） */
  onSend?: (text: string) => void;
}) {
  const intl = useIntl();
  const setAlarmDetailRecord = useAiAssistantStore((s) => s.setAlarmDetailRecord);

  const initialPage = data.page ?? 1;
  const initialPageSize = data.pageSize ?? DEFAULT_PAGE_SIZE;

  const [page, setPage] = useState(initialPage);
  const [pageSize, setPageSize] = useState(initialPageSize);
  const [items, setItems] = useState(data.items);
  const [total, setTotal] = useState(data.total);
  const [loading, setLoading] = useState(false);

  /** 数据源变更（新一次 query_alarms）时重置分页 */
  useEffect(() => {
    setPage(data.page ?? 1);
    setPageSize(data.pageSize ?? DEFAULT_PAGE_SIZE);
    setItems(data.items);
    setTotal(data.total);
  }, [data]);

  const columns: ColumnsType<AlarmQueryWorkspace["items"][0]> = useMemo(
    () => [
      {
        title: intl.formatMessage({ id: "aiAssistant.workspace.col.device" }),
        dataIndex: "deviceName",
        ellipsis: true,
        width: 140,
        render: (v: string) => v || "-",
      },
      {
        title: intl.formatMessage({ id: "aiAssistant.workspace.col.level" }),
        dataIndex: "alarmRankName",
        width: 72,
        render: (v: string) => v || "-",
      },
      {
        title: intl.formatMessage({ id: "aiAssistant.workspace.col.status" }),
        dataIndex: "statusName",
        width: 88,
        render: (v: string) => (v ? <Tag color={statusTagColor(v)}>{v}</Tag> : "-"),
      },
      {
        title: intl.formatMessage({ id: "aiAssistant.workspace.col.time" }),
        dataIndex: "startTime",
        width: 120,
        ellipsis: true,
        render: (v: string) => (v ? v.slice(0, 16) : "-"),
      },
    ],
    [intl],
  );

  const loadPage = useCallback(
    async (nextPage: number, nextPageSize: number) => {
      if (!data.queryContext) {
        // 无 queryContext（历史消息）：仅客户端对已有 items 分页
        setPage(nextPage);
        setPageSize(nextPageSize);
        return;
      }

      setLoading(true);
      try {
        const result = await fetchAlarmQueryPage(data.queryContext, nextPage, nextPageSize);
        setItems(result.items);
        setTotal(result.total);
        setPage(nextPage);
        setPageSize(nextPageSize);
      } catch (err) {
        message.error(
          err instanceof Error
            ? err.message
            : intl.formatMessage({
                id: "aiAssistant.workspace.pageLoadFailed",
              }),
        );
      } finally {
        setLoading(false);
      }
    },
    [data.queryContext, intl],
  );

  const handleTableChange = (pagination: TablePaginationConfig) => {
    const nextPage = pagination.current ?? 1;
    const nextSize = pagination.pageSize ?? pageSize;
    if (!data.queryContext) {
      setPage(nextPage);
      setPageSize(nextSize);
      return;
    }
    if (nextPage === page && nextSize === pageSize) return;
    void loadPage(nextPage, nextSize);
  };

  if (!data.ok) {
    return (
      <Text type="danger" className={styles.workspaceError}>
        {data.summary || intl.formatMessage({ id: "aiAssistant.workspace.queryFailed" })}
      </Text>
    );
  }

  if (total === 0) {
    return (
      <Empty
        image={Empty.PRESENTED_IMAGE_SIMPLE}
        description={intl.formatMessage({
          id: "aiAssistant.workspace.noAlarms",
        })}
      />
    );
  }

  /** 无 queryContext 时在本地 items 上切片分页 */
  const displayItems = data.queryContext
    ? items
    : items.slice((page - 1) * pageSize, page * pageSize);

  const buildBatchPrompt = (action: "confirm" | "process"): string => {
    const ctx = data.queryContext;
    const start = ctx?.startTime || data.timeRange?.start || "";
    const end = ctx?.endTime || data.timeRange?.end || "";
    const codes = ctx?.deviceCodes?.filter(Boolean) ?? [];
    const verb = action === "confirm" ? "批量确认" : "批量处理";
    const parts = [
      `请对刚才告警查询结果执行${verb}（须 HITL 确认后再写库）。`,
      start && end ? `时间范围：${start} ~ ${end}。` : "",
      codes.length === 1
        ? `设备编码：${codes[0]}。`
        : codes.length > 1
          ? `设备编码：${codes.join(",")}。`
          : "",
      action === "confirm"
        ? "请调用 batch_confirm_alarms，按上述时间与设备筛选待确认告警。"
        : "请调用 batch_process_alarms，按上述时间与设备筛选可处理告警。",
    ];
    return parts.filter(Boolean).join("");
  };

  return (
    <Space direction="vertical" size="small" style={{ width: "100%" }}>
      {onSend && data.ok && total > 0 && data.queryContext ? (
        <Space wrap>
          <Button size="small" onClick={() => onSend(buildBatchPrompt("confirm"))}>
            {intl.formatMessage({
              id: "aiAssistant.workspace.batchConfirm",
            })}
          </Button>
          <Button size="small" onClick={() => onSend(buildBatchPrompt("process"))}>
            {intl.formatMessage({
              id: "aiAssistant.workspace.batchProcess",
            })}
          </Button>
        </Space>
      ) : null}
      <Table
        size="small"
        rowKey={rowKeyOf}
        columns={columns}
        dataSource={displayItems}
        loading={loading}
        pagination={{
          current: page,
          pageSize,
          total,
          showSizeChanger: true,
          pageSizeOptions: PAGE_SIZE_OPTIONS,
          showTotal: (t, range) =>
            intl.formatMessage(
              { id: "aiAssistant.workspace.paginationTotal" },
              { start: range[0], end: range[1], total: t },
            ),
          size: "small",
        }}
        onChange={handleTableChange}
        scroll={{ y: modalMode ? 360 : 160, x: 480 }}
        className={styles.workspaceTable}
        onRow={(record) => ({
          onClick: () => {
            if (record.id) {
              setAlarmDetailRecord(record as Record<string, unknown>);
            }
          },
          className: record.id ? styles.workspaceRowClickable : undefined,
        })}
      />
    </Space>
  );
}
