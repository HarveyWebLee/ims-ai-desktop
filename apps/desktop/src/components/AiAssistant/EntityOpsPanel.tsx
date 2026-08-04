/**
 * 实体术语运营：统计 / 试检索 / 达梦只读同步到 platform_entities
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Alert,
  Button,
  Card,
  Descriptions,
  Empty,
  Input,
  Select,
  Space,
  Table,
  Tag,
  Typography,
} from "antd";
import { CloudSyncOutlined, ReloadOutlined, SearchOutlined } from "@ant-design/icons";
import { useIntl } from "react-intl";
import { message } from "@/antd/feedback";
import * as AgentController from "@/services/AgentController";
import type { EntitySearchHit, EntityStats, EntitySyncResult } from "@/services/AgentController";
import dayjs from "dayjs";

const { Text, Paragraph } = Typography;

const LAST_SYNC_KEY = "ims_ai_last_entity_sync";

type StoredSync = {
  at: string;
  result: EntitySyncResult;
  inProgress?: boolean;
};

function readStoredSync(): StoredSync | null {
  try {
    const raw = sessionStorage.getItem(LAST_SYNC_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as StoredSync;
    if (!parsed?.at || !parsed?.result) return null;
    return parsed;
  } catch {
    return null;
  }
}

function writeStoredSync(entry: StoredSync): void {
  try {
    sessionStorage.setItem(LAST_SYNC_KEY, JSON.stringify(entry));
  } catch {
    /* ignore quota */
  }
}

export default function EntityOpsPanel() {
  const intl = useIntl();
  const [stats, setStats] = useState<EntityStats | null>(null);
  const [statsLoading, setStatsLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [lastSync, setLastSync] = useState<StoredSync | null>(() => readStoredSync());
  const [statusLoading, setStatusLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [entityTypeFilter, setEntityTypeFilter] = useState<string | undefined>(undefined);
  const [searching, setSearching] = useState(false);
  const [searchHits, setSearchHits] = useState<EntitySearchHit[] | null>(null);

  const loadStats = useCallback(async () => {
    setStatsLoading(true);
    try {
      const s = await AgentController.getEntityStats();
      setStats(s);
    } catch (err) {
      message.error(
        intl.formatMessage(
          { id: "aiAssistant.entityOps.loadFailed" },
          { reason: err instanceof Error ? err.message : String(err) },
        ),
      );
    } finally {
      setStatsLoading(false);
    }
  }, [intl]);

  const applyServerStatus = useCallback(async () => {
    setStatusLoading(true);
    try {
      const status = await AgentController.getEntitySyncStatus();
      if (status.result && status.at) {
        const entry: StoredSync = {
          at: status.at,
          result: status.result,
          inProgress: status.in_progress,
        };
        writeStoredSync(entry);
        setLastSync(entry);
      } else if (status.in_progress) {
        setLastSync((prev) => (prev ? { ...prev, inProgress: true } : prev));
      }
    } catch {
      /* 服务端不可达时保留本地缓存 */
    } finally {
      setStatusLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadStats();
    void applyServerStatus();
  }, [applyServerStatus, loadStats]);

  const statusTag = useMemo(() => {
    if (!lastSync) return null;
    if (lastSync.inProgress || syncing) {
      return (
        <Tag color="processing">
          {intl.formatMessage({ id: "aiAssistant.entitySync.statusRunning" })}
        </Tag>
      );
    }
    const r = lastSync.result;
    if (r.skipped) {
      return (
        <Tag color="default">
          {intl.formatMessage({ id: "aiAssistant.entitySync.statusSkipped" })}
        </Tag>
      );
    }
    if (r.ok === false) {
      return (
        <Tag color="error">{intl.formatMessage({ id: "aiAssistant.entitySync.statusFailed" })}</Tag>
      );
    }
    return (
      <Tag color="success">{intl.formatMessage({ id: "aiAssistant.entitySync.statusOk" })}</Tag>
    );
  }, [intl, lastSync, syncing]);

  const handleSearch = async () => {
    const q = searchQuery.trim();
    if (!q) {
      message.warning(intl.formatMessage({ id: "aiAssistant.entityOps.searchEmpty" }));
      return;
    }
    setSearching(true);
    try {
      const data = await AgentController.searchEntities({
        query: q,
        limit: 10,
        entityTypes: entityTypeFilter ? [entityTypeFilter] : undefined,
      });
      setSearchHits(data.items);
      if (data.items.length === 0) {
        message.info(intl.formatMessage({ id: "aiAssistant.entityOps.searchNoHits" }));
      }
    } catch (err) {
      message.error(
        intl.formatMessage(
          { id: "aiAssistant.entityOps.searchFailed" },
          { reason: err instanceof Error ? err.message : String(err) },
        ),
      );
    } finally {
      setSearching(false);
    }
  };

  const handleSync = async () => {
    if (syncing) return;
    setSyncing(true);
    const hide = message.loading(intl.formatMessage({ id: "aiAssistant.entitySync.running" }), 0);
    try {
      const result = await AgentController.triggerEntitySync();
      hide();
      const entry: StoredSync = { at: new Date().toISOString(), result, inProgress: false };
      writeStoredSync(entry);
      setLastSync(entry);
      await Promise.all([applyServerStatus(), loadStats()]);

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
      if (result.ok === false) {
        message.error(
          result.message ||
            intl.formatMessage(
              { id: "aiAssistant.entitySync.failed" },
              { reason: result.message || "unknown" },
            ),
        );
        return;
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
      setSyncing(false);
    }
  };

  const tables = lastSync?.result.tables ?? [];

  return (
    <Space direction="vertical" size={16} style={{ width: "100%" }}>
      <Card size="small">
        <Paragraph type="secondary" style={{ marginBottom: 12 }}>
          {intl.formatMessage({ id: "aiAssistant.entityOps.intro" })}
        </Paragraph>
        <Space wrap>
          <Button
            icon={<ReloadOutlined />}
            loading={statsLoading || statusLoading}
            onClick={() => {
              void loadStats();
              void applyServerStatus();
            }}
          >
            {intl.formatMessage({ id: "aiAssistant.entityOps.refresh" })}
          </Button>
          <Button
            type="primary"
            icon={<CloudSyncOutlined />}
            loading={syncing}
            onClick={() => void handleSync()}
          >
            {intl.formatMessage({ id: "aiAssistant.entitySync.button" })}
          </Button>
        </Space>
      </Card>

      {stats ? (
        <Card size="small" title={intl.formatMessage({ id: "aiAssistant.entityOps.statsTitle" })}>
          <Descriptions size="small" column={1}>
            <Descriptions.Item
              label={intl.formatMessage({ id: "aiAssistant.entityOps.collection" })}
            >
              <Text code>{stats.collection}</Text>
            </Descriptions.Item>
            <Descriptions.Item label={intl.formatMessage({ id: "aiAssistant.entityOps.points" })}>
              {stats.points}
            </Descriptions.Item>
            <Descriptions.Item
              label={intl.formatMessage({ id: "aiAssistant.entityOps.syncTables" })}
            >
              <Text code>{stats.sync_tables?.trim() || "—"}</Text>
            </Descriptions.Item>
            <Descriptions.Item label={intl.formatMessage({ id: "aiAssistant.entityOps.status" })}>
              {stats.enabled === false ? (
                <Tag>{intl.formatMessage({ id: "aiAssistant.entityOps.statusDisabled" })}</Tag>
              ) : stats.ok ? (
                <Tag color="success">
                  {intl.formatMessage({ id: "aiAssistant.entityOps.statusOk" })}
                </Tag>
              ) : (
                <Tag color="error">
                  {intl.formatMessage({ id: "aiAssistant.entityOps.statusBad" })}
                </Tag>
              )}
              {stats.in_progress || syncing ? (
                <Tag color="processing" style={{ marginInlineStart: 4 }}>
                  {intl.formatMessage({ id: "aiAssistant.entitySync.statusRunning" })}
                </Tag>
              ) : null}
            </Descriptions.Item>
          </Descriptions>
          {stats.message ? (
            <Alert style={{ marginTop: 8 }} type="info" showIcon title={stats.message} />
          ) : null}
        </Card>
      ) : null}

      <Card size="small" title={intl.formatMessage({ id: "aiAssistant.entityOps.searchTitle" })}>
        <Space.Compact style={{ width: "100%" }}>
          <Select
            allowClear
            placeholder={intl.formatMessage({ id: "aiAssistant.entityOps.typeAll" })}
            style={{ width: 120 }}
            value={entityTypeFilter}
            onChange={(v) => setEntityTypeFilter(v)}
            options={[
              {
                value: "device",
                label: intl.formatMessage({ id: "aiAssistant.entityOps.typeDevice" }),
              },
              {
                value: "variable",
                label: intl.formatMessage({ id: "aiAssistant.entityOps.typeVariable" }),
              },
            ]}
          />
          <Input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={intl.formatMessage({ id: "aiAssistant.entityOps.searchPlaceholder" })}
            onPressEnter={() => void handleSearch()}
            allowClear
          />
          <Button
            type="primary"
            icon={<SearchOutlined />}
            loading={searching}
            onClick={() => void handleSearch()}
          >
            {intl.formatMessage({ id: "aiAssistant.entityOps.search" })}
          </Button>
        </Space.Compact>
        {searchHits ? (
          <div style={{ marginTop: 12 }}>
            {searchHits.length === 0 ? (
              <Empty
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description={intl.formatMessage({ id: "aiAssistant.entityOps.searchNoHits" })}
              />
            ) : (
              <Table
                size="small"
                rowKey={(row) => `${row.source}-${row.entity_key}-${row.score}`}
                pagination={false}
                dataSource={searchHits}
                scroll={{ x: 720 }}
                columns={[
                  {
                    title: intl.formatMessage({ id: "aiAssistant.entityOps.colType" }),
                    dataIndex: "entity_type",
                    width: 88,
                    render: (v: string) =>
                      v === "device"
                        ? intl.formatMessage({ id: "aiAssistant.entityOps.typeDevice" })
                        : v === "variable"
                          ? intl.formatMessage({ id: "aiAssistant.entityOps.typeVariable" })
                          : v || "—",
                  },
                  {
                    title: intl.formatMessage({ id: "aiAssistant.entityOps.colKey" }),
                    dataIndex: "entity_key",
                    width: 140,
                    ellipsis: true,
                  },
                  {
                    title: intl.formatMessage({ id: "aiAssistant.entityOps.colText" }),
                    dataIndex: "text_preview",
                    ellipsis: true,
                  },
                  {
                    title: intl.formatMessage({ id: "aiAssistant.entityOps.colScore" }),
                    dataIndex: "score",
                    width: 80,
                    render: (v: number) => (v > 0 ? v.toFixed(3) : "—"),
                  },
                ]}
              />
            )}
          </div>
        ) : null}
      </Card>

      <Card size="small" title={intl.formatMessage({ id: "aiAssistant.entitySync.lastResult" })}>
        <Paragraph type="secondary" style={{ marginBottom: 12 }}>
          {intl.formatMessage({ id: "aiAssistant.entitySync.tooltip" })}
        </Paragraph>
        {!lastSync ? (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={intl.formatMessage({ id: "aiAssistant.entitySync.noStatus" })}
          />
        ) : (
          <>
            <div style={{ marginBottom: 8 }}>{statusTag}</div>
            <Descriptions size="small" column={1}>
              <Descriptions.Item
                label={intl.formatMessage({ id: "aiAssistant.entitySync.syncedAt" })}
              >
                {dayjs(lastSync.at).format("YYYY-MM-DD HH:mm:ss")}
              </Descriptions.Item>
              {lastSync.result.collection ? (
                <Descriptions.Item
                  label={intl.formatMessage({ id: "aiAssistant.entitySync.collection" })}
                >
                  <Text code>{lastSync.result.collection}</Text>
                </Descriptions.Item>
              ) : null}
              {lastSync.result.config ? (
                <Descriptions.Item
                  label={intl.formatMessage({ id: "aiAssistant.entitySync.config" })}
                >
                  <Text code>{lastSync.result.config}</Text>
                </Descriptions.Item>
              ) : null}
              {typeof lastSync.result.upserted === "number" ? (
                <Descriptions.Item
                  label={intl.formatMessage({ id: "aiAssistant.entitySync.upserted" })}
                >
                  {lastSync.result.upserted}
                </Descriptions.Item>
              ) : null}
              {lastSync.result.message ? (
                <Descriptions.Item
                  label={intl.formatMessage({ id: "aiAssistant.entitySync.message" })}
                >
                  {lastSync.result.message}
                </Descriptions.Item>
              ) : null}
            </Descriptions>

            {lastSync.result.skipped ? (
              <Alert
                style={{ marginTop: 12 }}
                type="info"
                showIcon
                title={intl.formatMessage({ id: "aiAssistant.entitySync.skippedEmpty" })}
              />
            ) : null}

            {(lastSync.result.missing_tables?.length ?? 0) > 0 ? (
              <Alert
                style={{ marginTop: 12 }}
                type="warning"
                showIcon
                title={intl.formatMessage(
                  { id: "aiAssistant.entitySync.missingTables" },
                  { tables: (lastSync.result.missing_tables ?? []).join(", ") },
                )}
              />
            ) : null}

            {tables.length > 0 ? (
              <Table
                style={{ marginTop: 12 }}
                size="small"
                rowKey="table"
                pagination={false}
                dataSource={tables}
                columns={[
                  {
                    title: intl.formatMessage({ id: "aiAssistant.entitySync.colTable" }),
                    dataIndex: "table",
                  },
                  {
                    title: intl.formatMessage({ id: "aiAssistant.entitySync.colRows" }),
                    dataIndex: "rows_read",
                    width: 100,
                  },
                  {
                    title: intl.formatMessage({ id: "aiAssistant.entitySync.colUpserted" }),
                    dataIndex: "upserted",
                    width: 100,
                  },
                  {
                    title: intl.formatMessage({ id: "aiAssistant.entitySync.colStatus" }),
                    width: 100,
                    render: (_, row) =>
                      row.ok ? (
                        <Tag color="success">
                          {intl.formatMessage({ id: "aiAssistant.entitySync.statusOk" })}
                        </Tag>
                      ) : (
                        <Tag color="error">
                          {intl.formatMessage({ id: "aiAssistant.entitySync.statusFailed" })}
                        </Tag>
                      ),
                  },
                  {
                    title: intl.formatMessage({ id: "aiAssistant.entitySync.colError" }),
                    dataIndex: "error",
                    ellipsis: true,
                    render: (v: string | null | undefined) => v || "—",
                  },
                ]}
              />
            ) : null}
          </>
        )}
      </Card>
    </Space>
  );
}
