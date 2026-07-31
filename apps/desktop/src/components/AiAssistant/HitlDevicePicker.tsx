/**
 * HITL 设备单选表格：支持分组/类型/区域/名称/编码/在线状态筛选
 * 注意：不可再包 Form（外层 HitlInteractionCard 已有 Form）
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { Button, Empty, Input, Select, Space, Table, Tag, TreeSelect, Typography } from "antd";
import type { ColumnsType, TablePaginationConfig } from "antd/es/table";
import { ReloadOutlined, SearchOutlined } from "@ant-design/icons";
import { useIntl } from "@umijs/max";
import {
  getDeviceCategoryTree,
  getDeviceGroupTree,
  getDeviceList,
  getRegionTree,
} from "@/services/SystemController";
import styles from "./index.module.less";

const { Text } = Typography;

const DEFAULT_PAGE_SIZE = 10;
const PAGE_SIZE_OPTIONS = ["10", "20", "50"];

/** 与设备管理页一致：排除网关设备 */
const DEFAULT_COMM_MODEL = [1, 2, 4];

interface DeviceRecord {
  id?: number | string;
  deviceCode?: string;
  deviceName?: string;
  deviceGroupName?: string;
  deviceCategoryName?: string;
  regionName?: string;
  onlineStatus?: number;
}

interface TreeNodeOption {
  title: string;
  value: string | number;
  key: string | number;
  children?: TreeNodeOption[];
}

interface DeviceFilters {
  deviceGroupId?: string | number;
  deviceCategoryId?: string | number;
  regionId?: string | number;
  deviceName?: string;
  deviceCode?: string;
  onlineStatus?: number;
}

export interface HitlDevicePickerProps {
  /** 已选设备编码（Form.Item 注入） */
  value?: string;
  onChange?: (deviceCode: string | undefined) => void;
  /** 字段说明文案 */
  description?: string;
}

function normalizeTreePayload(data: unknown): unknown[] {
  if (!data) return [];
  if (Array.isArray(data)) return data;
  if (typeof data === "object") {
    const obj = data as Record<string, unknown>;
    for (const key of ["data", "list", "records", "children"]) {
      if (Array.isArray(obj[key])) return obj[key] as unknown[];
    }
  }
  return [];
}

function toTreeSelectNodes(nodes: unknown[]): TreeNodeOption[] {
  return nodes.map((raw) => {
    const node = (raw ?? {}) as Record<string, unknown>;
    const id = node.id ?? node.value ?? node.key;
    const title = String(
      node.title ?? node.label ?? node.name ?? node.deviceGroupName ?? id ?? "-",
    );
    const value = (id ?? title) as string | number;
    const childrenRaw = node.children;
    return {
      title,
      value,
      key: value,
      children: Array.isArray(childrenRaw)
        ? toTreeSelectNodes(childrenRaw as unknown[])
        : undefined,
    };
  });
}

function onlineTagColor(status?: number): string {
  if (status === 1) return "success";
  if (status === 2) return "warning";
  return "default";
}

function onlineLabel(status: number | undefined, intl: ReturnType<typeof useIntl>): string {
  if (status === 1) {
    return intl.formatMessage({ id: "aiAssistant.hitl.device.online" });
  }
  if (status === 2) {
    return intl.formatMessage({ id: "aiAssistant.hitl.device.abnormal" });
  }
  return intl.formatMessage({ id: "aiAssistant.hitl.device.offline" });
}

const EMPTY_FILTERS: DeviceFilters = {};

export default function HitlDevicePicker({ value, onChange, description }: HitlDevicePickerProps) {
  const intl = useIntl();
  const [filters, setFilters] = useState<DeviceFilters>(EMPTY_FILTERS);
  const [loading, setLoading] = useState(false);
  const [records, setRecords] = useState<DeviceRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE);
  const [selectedMeta, setSelectedMeta] = useState<DeviceRecord | null>(null);

  const [groupTree, setGroupTree] = useState<TreeNodeOption[]>([]);
  const [categoryTree, setCategoryTree] = useState<TreeNodeOption[]>([]);
  const [regionTree, setRegionTree] = useState<TreeNodeOption[]>([]);

  const treeSelectCommonProps = useMemo(
    () => ({
      allowClear: true,
      showSearch: true,
      treeNodeFilterProp: "title" as const,
      popupMatchSelectWidth: false,
      style: { width: "100%" as const },
      size: "small" as const,
    }),
    [],
  );

  const patchFilter = useCallback((patch: Partial<DeviceFilters>) => {
    setFilters((prev) => ({ ...prev, ...patch }));
  }, []);

  const loadTrees = useCallback(async () => {
    const [groupRes, categoryRes, regionRes] = await Promise.all([
      getDeviceGroupTree(),
      getDeviceCategoryTree(),
      getRegionTree(),
    ]);
    if (groupRes?.code === 0) {
      setGroupTree(toTreeSelectNodes(normalizeTreePayload(groupRes.data)));
    }
    if (categoryRes?.code === 0) {
      setCategoryTree(toTreeSelectNodes(normalizeTreePayload(categoryRes.data)));
    }
    if (regionRes?.code === 0) {
      setRegionTree(toTreeSelectNodes(normalizeTreePayload(regionRes.data)));
    }
  }, []);

  const fetchList = useCallback(
    async (nextPage: number, nextSize: number, nextFilters: DeviceFilters) => {
      setLoading(true);
      try {
        const res = await getDeviceList({
          page: nextPage,
          size: nextSize,
          containSubLevel: 1,
          commModel: DEFAULT_COMM_MODEL,
          deviceGroupId: nextFilters.deviceGroupId || undefined,
          deviceCategoryId: nextFilters.deviceCategoryId || undefined,
          regionId: nextFilters.regionId || undefined,
          deviceName: String(nextFilters.deviceName || "").trim() || undefined,
          deviceCode: String(nextFilters.deviceCode || "").trim() || undefined,
          onlineStatus:
            nextFilters.onlineStatus === 0 || nextFilters.onlineStatus === 1
              ? nextFilters.onlineStatus
              : undefined,
        });
        if (res?.code === 0) {
          const data = (res.data ?? {}) as {
            records?: DeviceRecord[];
            list?: DeviceRecord[];
            total?: number;
          };
          const list = (data.records ?? data.list ?? []) as DeviceRecord[];
          setRecords(list);
          setTotal(Number(data.total ?? list.length) || 0);
          setPage(nextPage);
          setPageSize(nextSize);
          if (value) {
            const found = list.find((item) => item.deviceCode === value);
            if (found) setSelectedMeta(found);
          }
        } else {
          setRecords([]);
          setTotal(0);
        }
      } catch {
        setRecords([]);
        setTotal(0);
      } finally {
        setLoading(false);
      }
    },
    [value],
  );

  useEffect(() => {
    void loadTrees();
    void fetchList(1, DEFAULT_PAGE_SIZE, EMPTY_FILTERS);
    // 仅挂载时拉取
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSearch = () => {
    void fetchList(1, pageSize, filters);
  };

  const handleReset = () => {
    setFilters(EMPTY_FILTERS);
    void fetchList(1, pageSize, EMPTY_FILTERS);
  };

  const handleTableChange = (pagination: TablePaginationConfig) => {
    const nextPage = pagination.current ?? 1;
    const nextSize = pagination.pageSize ?? pageSize;
    void fetchList(nextPage, nextSize, filters);
  };

  const columns: ColumnsType<DeviceRecord> = useMemo(
    () => [
      {
        title: intl.formatMessage({ id: "aiAssistant.hitl.device.colName" }),
        dataIndex: "deviceName",
        ellipsis: true,
        width: 120,
        render: (v: string) => v || "-",
      },
      {
        title: intl.formatMessage({ id: "aiAssistant.hitl.device.colCode" }),
        dataIndex: "deviceCode",
        ellipsis: true,
        width: 100,
        render: (v: string) => v || "-",
      },
      {
        title: intl.formatMessage({ id: "aiAssistant.hitl.device.colGroup" }),
        dataIndex: "deviceGroupName",
        ellipsis: true,
        width: 90,
        render: (v: string) => v || "-",
      },
      {
        title: intl.formatMessage({ id: "aiAssistant.hitl.device.colType" }),
        dataIndex: "deviceCategoryName",
        ellipsis: true,
        width: 90,
        render: (v: string) => v || "-",
      },
      {
        title: intl.formatMessage({ id: "aiAssistant.hitl.device.colRegion" }),
        dataIndex: "regionName",
        ellipsis: true,
        width: 90,
        render: (v: string) => v || "-",
      },
      {
        title: intl.formatMessage({ id: "aiAssistant.hitl.device.colOnline" }),
        dataIndex: "onlineStatus",
        width: 72,
        render: (status: number) => (
          <Tag color={onlineTagColor(status)} bordered={false}>
            {onlineLabel(status, intl)}
          </Tag>
        ),
      },
    ],
    [intl],
  );

  const selectedCode = value || undefined;
  const selectPlaceholder = intl.formatMessage({
    id: "aiAssistant.hitl.selectPlaceholder",
  });

  return (
    <div className={styles.hitlDevicePicker}>
      <div className={styles.hitlDevicePickerHint}>
        {selectedCode ? (
          <Text className={styles.hitlDevicePickerSelected}>
            {intl.formatMessage(
              { id: "aiAssistant.hitl.device.selected" },
              {
                name:
                  selectedMeta?.deviceName ||
                  selectedCode ||
                  intl.formatMessage({
                    id: "aiAssistant.hitl.device.unknown",
                  }),
                code: selectedCode,
              },
            )}
          </Text>
        ) : (
          <Text type="secondary">
            {description || intl.formatMessage({ id: "aiAssistant.hitl.device.hint" })}
          </Text>
        )}
      </div>

      <div className={styles.hitlDevicePickerFilters}>
        <div className={styles.hitlDevicePickerFilterGrid}>
          <label className={styles.hitlDevicePickerFilterItem}>
            <span className={styles.hitlDevicePickerFilterLabel}>
              {intl.formatMessage({
                id: "aiAssistant.hitl.device.filterGroup",
              })}
            </span>
            <TreeSelect
              {...treeSelectCommonProps}
              value={filters.deviceGroupId}
              treeData={groupTree}
              placeholder={selectPlaceholder}
              onChange={(v) => patchFilter({ deviceGroupId: v as string | number | undefined })}
            />
          </label>
          <label className={styles.hitlDevicePickerFilterItem}>
            <span className={styles.hitlDevicePickerFilterLabel}>
              {intl.formatMessage({
                id: "aiAssistant.hitl.device.filterType",
              })}
            </span>
            <TreeSelect
              {...treeSelectCommonProps}
              value={filters.deviceCategoryId}
              treeData={categoryTree}
              placeholder={selectPlaceholder}
              onChange={(v) =>
                patchFilter({
                  deviceCategoryId: v as string | number | undefined,
                })
              }
            />
          </label>
          <label className={styles.hitlDevicePickerFilterItem}>
            <span className={styles.hitlDevicePickerFilterLabel}>
              {intl.formatMessage({
                id: "aiAssistant.hitl.device.filterRegion",
              })}
            </span>
            <TreeSelect
              {...treeSelectCommonProps}
              value={filters.regionId}
              treeData={regionTree}
              placeholder={selectPlaceholder}
              onChange={(v) => patchFilter({ regionId: v as string | number | undefined })}
            />
          </label>
          <label className={styles.hitlDevicePickerFilterItem}>
            <span className={styles.hitlDevicePickerFilterLabel}>
              {intl.formatMessage({
                id: "aiAssistant.hitl.device.filterOnline",
              })}
            </span>
            <Select
              allowClear
              size="small"
              style={{ width: "100%" }}
              value={filters.onlineStatus}
              placeholder={selectPlaceholder}
              options={[
                {
                  value: 1,
                  label: intl.formatMessage({
                    id: "aiAssistant.hitl.device.online",
                  }),
                },
                {
                  value: 0,
                  label: intl.formatMessage({
                    id: "aiAssistant.hitl.device.offline",
                  }),
                },
              ]}
              onChange={(v) =>
                patchFilter({
                  onlineStatus: typeof v === "number" ? v : undefined,
                })
              }
            />
          </label>
          <label className={styles.hitlDevicePickerFilterItem}>
            <span className={styles.hitlDevicePickerFilterLabel}>
              {intl.formatMessage({
                id: "aiAssistant.hitl.device.filterName",
              })}
            </span>
            <Input
              allowClear
              size="small"
              value={filters.deviceName ?? ""}
              placeholder={intl.formatMessage({
                id: "aiAssistant.hitl.device.namePlaceholder",
              })}
              onChange={(e) => patchFilter({ deviceName: e.target.value })}
              onPressEnter={handleSearch}
            />
          </label>
          <label className={styles.hitlDevicePickerFilterItem}>
            <span className={styles.hitlDevicePickerFilterLabel}>
              {intl.formatMessage({
                id: "aiAssistant.hitl.device.filterCode",
              })}
            </span>
            <Input
              allowClear
              size="small"
              value={filters.deviceCode ?? ""}
              placeholder={intl.formatMessage({
                id: "aiAssistant.hitl.device.codePlaceholder",
              })}
              onChange={(e) => patchFilter({ deviceCode: e.target.value })}
              onPressEnter={handleSearch}
            />
          </label>
        </div>
        <Space size={8} className={styles.hitlDevicePickerActions}>
          <Button
            type="primary"
            size="small"
            icon={<SearchOutlined />}
            loading={loading}
            onClick={handleSearch}
          >
            {intl.formatMessage({ id: "aiAssistant.hitl.device.search" })}
          </Button>
          <Button size="small" icon={<ReloadOutlined />} onClick={handleReset} disabled={loading}>
            {intl.formatMessage({ id: "aiAssistant.hitl.device.reset" })}
          </Button>
        </Space>
      </div>

      <Table<DeviceRecord>
        className={styles.hitlDevicePickerTable}
        size="small"
        rowKey={(row) => String(row.deviceCode || row.id || "")}
        loading={loading}
        columns={columns}
        dataSource={records}
        scroll={{ x: 560, y: 220 }}
        locale={{
          emptyText: (
            <Empty
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              description={intl.formatMessage({
                id: "aiAssistant.hitl.device.empty",
              })}
            />
          ),
        }}
        rowSelection={{
          type: "radio",
          selectedRowKeys: selectedCode ? [selectedCode] : [],
          onChange: (keys, rows) => {
            const code = String(keys[0] ?? "");
            if (!code) {
              onChange?.(undefined);
              setSelectedMeta(null);
              return;
            }
            onChange?.(code);
            setSelectedMeta(rows[0] ?? null);
          },
          columnWidth: 36,
        }}
        onRow={(record) => ({
          onClick: () => {
            const code = String(record.deviceCode || "");
            if (!code) return;
            onChange?.(code);
            setSelectedMeta(record);
          },
        })}
        pagination={{
          current: page,
          pageSize,
          total,
          size: "small",
          showSizeChanger: true,
          pageSizeOptions: PAGE_SIZE_OPTIONS,
          showTotal: (t) =>
            intl.formatMessage({ id: "aiAssistant.hitl.device.total" }, { total: t }),
        }}
        onChange={handleTableChange}
      />
    </div>
  );
}
