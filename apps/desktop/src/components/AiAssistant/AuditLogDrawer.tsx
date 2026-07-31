/**
 * 审计日志抽屉 — 只读展示当前会话的工具调用、HITL 确认等审计事件
 * 支持按 run_id / event_type 筛选；每条可展开查看完整 payload
 */
import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { Button, Collapse, Drawer, Empty, Select, Spin, Tag, Typography, message } from "antd";
import { ReloadOutlined } from "@ant-design/icons";
import { useIntl } from "@umijs/max";
import type { IntlShape } from "@umijs/max";
import dayjs from "dayjs";
import * as AgentController from "@/services/AgentController";
import type { AgentAuditLogEntry } from "@/services/AgentController";
import { formatAgentErrorMessage } from "./utils/formatAgentError";
import { useAiAssistantStore } from "./store";
import styles from "./index.module.less";

const { Text } = Typography;

/** 审计 event_type → i18n key 后缀 */
const EVENT_TYPE_I18N: Record<string, string> = {
  tool_start: "toolStart",
  tool_end: "toolEnd",
  replan: "replan",
  interrupt: "interrupt",
  error: "error",
  confirm_approve: "confirmApprove",
  confirm_reject: "confirmReject",
  confirm_respond: "confirmRespond",
};

/** 可选 event_type 筛选列表 */
const FILTERABLE_EVENT_TYPES = [
  "tool_start",
  "tool_end",
  "interrupt",
  "replan",
  "error",
  "confirm_approve",
  "confirm_reject",
  "confirm_respond",
] as const;

function formatAuditTime(iso?: string | null): string {
  if (!iso) return "";
  const d = dayjs(iso);
  return d.isValid() ? d.format("MM-DD HH:mm:ss") : "";
}

/** 列表行摘要（一行） */
function summarizePayload(entry: AgentAuditLogEntry): string {
  const summary = entry.payload_summary;
  if (!summary || typeof summary !== "object") return "";

  if (entry.event_type === "error") {
    const data = summary.data;
    const msg = typeof summary.message === "string" && summary.message ? summary.message : "";
    if (typeof data === "object" && data && "detail" in data) {
      const detail = String((data as { detail?: string }).detail ?? "").trim();
      if (detail && detail !== msg) {
        return msg ? `${msg} — ${detail.slice(0, 80)}` : detail.slice(0, 120);
      }
    }
    return msg;
  }

  const parts: string[] = [];
  if (typeof summary.reason === "string" && summary.reason) {
    parts.push(summary.reason);
  }
  if (typeof summary.decision_type === "string" && summary.decision_type) {
    parts.push(summary.decision_type);
  }
  if (typeof summary.type === "string" && summary.type) {
    parts.push(summary.type);
  }
  if (typeof summary.message === "string" && summary.message) {
    parts.push(summary.message);
  }
  return parts.join(" · ");
}

function renderField(intl: IntlShape, labelId: string, value: ReactNode) {
  if (value === null || value === undefined || value === "") return null;
  return (
    <div className={styles.auditDrawerField}>
      <Text type="secondary" className={styles.auditDrawerFieldLabel}>
        {intl.formatMessage({ id: labelId })}
      </Text>
      <div className={styles.auditDrawerFieldValue}>{value}</div>
    </div>
  );
}

function renderJsonBlock(value: unknown) {
  if (value === null || value === undefined) return null;
  const text = typeof value === "string" ? value : JSON.stringify(value, null, 2);
  if (!text.trim()) return null;
  return <pre className={styles.auditDrawerPre}>{text}</pre>;
}

/** 展开区：按事件类型结构化展示 */
function renderAuditDetail(entry: AgentAuditLogEntry, intl: IntlShape) {
  const summary = entry.payload_summary;
  if (!summary || typeof summary !== "object") {
    return <Text type="secondary">{intl.formatMessage({ id: "aiAssistant.audit.noDetail" })}</Text>;
  }

  const blocks: ReactNode[] = [];

  if (entry.event_type === "error") {
    const main = formatAgentErrorMessage(
      intl,
      typeof summary.message === "string" ? summary.message : "",
      summary.data,
    );
    blocks.push(
      renderField(
        intl,
        "aiAssistant.audit.field.summary",
        <Text>{main.replace(/\n/g, " · ")}</Text>,
      ),
    );
    const data =
      summary.data && typeof summary.data === "object"
        ? (summary.data as Record<string, unknown>)
        : null;
    if (data?.detail) {
      blocks.push(
        renderField(intl, "aiAssistant.audit.field.detail", renderJsonBlock(String(data.detail))),
      );
    }
    if (summary.code !== undefined) {
      blocks.push(renderField(intl, "aiAssistant.audit.field.code", String(summary.code)));
    }
    if (data?.kind) {
      blocks.push(renderField(intl, "aiAssistant.audit.field.kind", String(data.kind)));
    }
  } else if (entry.event_type === "tool_start") {
    blocks.push(renderField(intl, "aiAssistant.audit.field.args", renderJsonBlock(summary.args)));
  } else if (entry.event_type === "tool_end") {
    blocks.push(
      renderField(
        intl,
        "aiAssistant.audit.field.result",
        renderJsonBlock(summary.result_preview ?? summary.result),
      ),
    );
  } else if (entry.event_type === "interrupt") {
    blocks.push(
      renderField(
        intl,
        "aiAssistant.audit.field.type",
        typeof summary.type === "string" ? summary.type : null,
      ),
      renderField(
        intl,
        "aiAssistant.audit.field.summary",
        typeof summary.message === "string" ? summary.message : null,
      ),
      renderField(
        intl,
        "aiAssistant.audit.field.args",
        summary.fields ? renderJsonBlock(summary.fields) : null,
      ),
    );
  } else if (entry.event_type === "replan") {
    blocks.push(
      renderField(
        intl,
        "aiAssistant.audit.field.summary",
        typeof summary.reason === "string" ? summary.reason : null,
      ),
      renderField(
        intl,
        "aiAssistant.audit.field.failedTool",
        typeof summary.failed_tool === "string" ? summary.failed_tool : null,
      ),
    );
  } else if (entry.event_type.startsWith("confirm_")) {
    blocks.push(
      renderField(
        intl,
        "aiAssistant.audit.field.type",
        typeof summary.decision_type === "string" ? summary.decision_type : null,
      ),
      renderField(
        intl,
        "aiAssistant.audit.field.args",
        summary.args ? renderJsonBlock(summary.args) : null,
      ),
    );
  }

  if (entry.run_id) {
    blocks.push(renderField(intl, "aiAssistant.audit.field.runId", entry.run_id));
  }

  const hasStructured = blocks.some(Boolean);
  if (hasStructured) {
    return <div className={styles.auditDrawerDetailBody}>{blocks}</div>;
  }

  return (
    <div className={styles.auditDrawerDetailBody}>
      {renderField(intl, "aiAssistant.audit.field.raw", renderJsonBlock(summary))}
    </div>
  );
}

export default function AuditLogDrawer({ open, onClose }: { open: boolean; onClose: () => void }) {
  const intl = useIntl();
  const { currentThreadId } = useAiAssistantStore();
  const [loading, setLoading] = useState(false);
  const [allLogs, setAllLogs] = useState<AgentAuditLogEntry[]>([]);
  const [filterRunId, setFilterRunId] = useState<string | undefined>();
  const [filterEventType, setFilterEventType] = useState<string | undefined>();

  const loadAudit = useCallback(
    async (options?: { notify?: boolean }) => {
      if (!currentThreadId) return;
      setLoading(true);
      try {
        const { logs: rows } = await AgentController.getThreadAudit(currentThreadId, {
          limit: 200,
        });
        const next = rows ?? [];
        setAllLogs(next);
        if (options?.notify) {
          message.success(
            intl.formatMessage({ id: "aiAssistant.audit.refreshed" }, { count: next.length }),
          );
        }
      } catch (err) {
        message.error(
          err instanceof Error
            ? err.message
            : intl.formatMessage({ id: "aiAssistant.audit.loadFailed" }),
        );
        setAllLogs([]);
      } finally {
        setLoading(false);
      }
    },
    [currentThreadId, intl],
  );

  useEffect(() => {
    if (open) {
      void loadAudit();
    }
  }, [open, currentThreadId, loadAudit]);

  const handleRefresh = useCallback(() => {
    void loadAudit({ notify: true });
  }, [loadAudit]);

  /** 从全量记录提取 run_id 选项 */
  const runIdOptions = useMemo(() => {
    const ids = new Set<string>();
    for (const entry of allLogs) {
      if (entry.run_id) ids.add(entry.run_id);
    }
    return Array.from(ids);
  }, [allLogs]);

  /** 客户端筛选（后端 API 亦支持 run_id / event_type 查询参数） */
  const logs = useMemo(() => {
    let rows = allLogs;
    if (filterRunId) {
      rows = rows.filter((e) => e.run_id === filterRunId);
    }
    if (filterEventType) {
      rows = rows.filter((e) => e.event_type === filterEventType);
    }
    return rows;
  }, [allLogs, filterEventType, filterRunId]);

  const eventLabel = (eventType: string) => {
    const suffix = EVENT_TYPE_I18N[eventType] ?? "default";
    return intl.formatMessage({ id: `aiAssistant.audit.event.${suffix}` });
  };

  const collapseItems = logs.map((entry, index) => {
    const key = String(entry.id ?? `${entry.created_at}-${index}`);
    const preview = summarizePayload(entry);
    const tagColor = entry.event_type === "error" ? "error" : undefined;

    return {
      key,
      label: (
        <div className={styles.auditDrawerCollapseLabel}>
          <Tag color={tagColor}>{eventLabel(entry.event_type)}</Tag>
          {entry.tool_name ? (
            <Text code className={styles.auditDrawerTool}>
              {entry.tool_name}
            </Text>
          ) : null}
          {entry.run_id ? (
            <Text type="secondary" className={styles.auditDrawerRunId} ellipsis>
              {entry.run_id.slice(0, 8)}
            </Text>
          ) : null}
          <Text type="secondary" ellipsis className={styles.auditDrawerPreview}>
            {preview || intl.formatMessage({ id: "aiAssistant.audit.tapToExpand" })}
          </Text>
          <Text type="secondary" className={styles.auditDrawerTime}>
            {formatAuditTime(entry.created_at)}
          </Text>
        </div>
      ),
      children: renderAuditDetail(entry, intl),
    };
  });

  return (
    <Drawer
      title={intl.formatMessage({ id: "aiAssistant.audit.title" })}
      extra={
        <Button
          type="text"
          size="small"
          icon={<ReloadOutlined />}
          loading={loading}
          onClick={handleRefresh}
          aria-label={intl.formatMessage({ id: "aiAssistant.audit.refresh" })}
        >
          {intl.formatMessage({ id: "aiAssistant.audit.refresh" })}
        </Button>
      }
      placement="left"
      width={Math.min(420, window.innerWidth * 0.92)}
      open={open}
      onClose={onClose}
      className={styles.auditDrawer}
      destroyOnClose={false}
    >
      <div className={styles.auditDrawerFilters}>
        <Text type="secondary" className={styles.auditDrawerCount}>
          {intl.formatMessage(
            { id: "aiAssistant.audit.totalCount" },
            { count: logs.length, total: allLogs.length },
          )}
        </Text>
        <Select
          allowClear
          size="small"
          placeholder={intl.formatMessage({ id: "aiAssistant.audit.filterRun" })}
          value={filterRunId}
          onChange={(v) => setFilterRunId(v)}
          options={runIdOptions.map((id) => ({
            label: id.length > 12 ? `${id.slice(0, 8)}…` : id,
            value: id,
          }))}
          className={styles.auditDrawerFilterSelect}
        />
        <Select
          allowClear
          size="small"
          placeholder={intl.formatMessage({ id: "aiAssistant.audit.filterEvent" })}
          value={filterEventType}
          onChange={(v) => setFilterEventType(v)}
          options={FILTERABLE_EVENT_TYPES.map((t) => ({
            label: eventLabel(t),
            value: t,
          }))}
          className={styles.auditDrawerFilterSelect}
        />
      </div>

      {loading && allLogs.length === 0 ? (
        <div className={styles.auditDrawerLoading}>
          <Spin />
        </div>
      ) : logs.length === 0 ? (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={intl.formatMessage({ id: "aiAssistant.audit.empty" })}
        />
      ) : (
        <div className={loading ? styles.auditDrawerListLoading : undefined}>
          <Collapse
            ghost
            size="small"
            className={styles.auditDrawerCollapse}
            items={collapseItems}
          />
        </div>
      )}
    </Drawer>
  );
}
