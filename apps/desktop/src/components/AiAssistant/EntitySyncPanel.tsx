/**
 * 向量库同步面板：触发同步并展示最近一次结果
 */
import { useMemo, useState } from "react";
import { Alert, Button, Card, Descriptions, Empty, Space, Table, Tag, Typography } from "antd";
import { CloudSyncOutlined, ReloadOutlined } from "@ant-design/icons";
import { useIntl } from "react-intl";
import { message } from "@/antd/feedback";
import * as AgentController from "@/services/AgentController";
import type { EntitySyncResult } from "@/services/AgentController";
import dayjs from "dayjs";

const { Text, Paragraph } = Typography;

const LAST_SYNC_KEY = "ims_ai_last_entity_sync";

type StoredSync = {
  at: string;
  result: EntitySyncResult;
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

export default function EntitySyncPanel() {
  const intl = useIntl();
  const [syncing, setSyncing] = useState(false);
  const [lastSync, setLastSync] = useState<StoredSync | null>(() => readStoredSync());

  const statusTag = useMemo(() => {
    if (!lastSync) return null;
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
  }, [intl, lastSync]);

  const handleSync = async () => {
    if (syncing) return;
    setSyncing(true);
    const hide = message.loading(intl.formatMessage({ id: "aiAssistant.entitySync.running" }), 0);
    try {
      const result = await AgentController.triggerEntitySync();
      hide();
      const entry: StoredSync = { at: new Date().toISOString(), result };
      writeStoredSync(entry);
      setLastSync(entry);

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
        <Space direction="vertical" size={12} style={{ width: "100%" }}>
          <Paragraph type="secondary" style={{ marginBottom: 0 }}>
            {intl.formatMessage({ id: "aiAssistant.entitySync.tooltip" })}
          </Paragraph>
          <Space wrap>
            <Button
              type="primary"
              icon={<CloudSyncOutlined />}
              loading={syncing}
              onClick={() => void handleSync()}
            >
              {intl.formatMessage({ id: "aiAssistant.entitySync.button" })}
            </Button>
            {lastSync ? (
              <Button
                icon={<ReloadOutlined />}
                onClick={() => setLastSync(readStoredSync())}
                disabled={syncing}
              >
                {intl.formatMessage({ id: "aiAssistant.entitySync.reloadStatus" })}
              </Button>
            ) : null}
          </Space>
        </Space>
      </Card>

      {!lastSync ? (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={intl.formatMessage({ id: "aiAssistant.entitySync.noStatus" })}
        />
      ) : (
        <>
          <Card
            size="small"
            title={intl.formatMessage({ id: "aiAssistant.entitySync.lastResult" })}
            extra={statusTag}
          >
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
          </Card>

          {tables.length > 0 ? (
            <Card
              size="small"
              title={intl.formatMessage({ id: "aiAssistant.entitySync.tableDetail" })}
            >
              <Table
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
            </Card>
          ) : null}
        </>
      )}
    </Space>
  );
}
