/**
 * 审计日志面板 — 配置页内嵌；按会话分组，会话内再按运行（run）折叠展示
 */
import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { Button, Collapse, Empty, Select, Spin, Tag, Typography } from "antd";
import { message } from "@/antd/feedback";
import { ReloadOutlined } from "@ant-design/icons";
import { useIntl, type IntlShape } from "react-intl";
import dayjs from "dayjs";
import * as AgentController from "@/services/AgentController";
import type { AgentAuditLogEntry } from "@/services/AgentController";
import type { AiSession } from "./types";
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
  tool_hook_deny: "toolHookDeny",
  tool_hook_after: "toolHookAfter",
  client_action_result: "clientActionResult",
  hitl_lifecycle: "hitlLifecycle",
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
  "tool_hook_deny",
  "tool_hook_after",
  "client_action_result",
] as const;

/** 单次运行下的审计事件组 */
interface RunAuditGroup {
  runId: string | null;
  logs: AgentAuditLogEntry[];
  latestAt: string;
}

/** 会话级审计分组 */
interface SessionAuditGroup {
  threadId: string;
  title: string;
  updatedAt: string;
  logs: AgentAuditLogEntry[];
  latestAt: string;
  runs: RunAuditGroup[];
}

function formatAuditTime(iso?: string | null): string {
  if (!iso) return "";
  const d = dayjs(iso);
  return d.isValid() ? d.format("MM-DD HH:mm:ss") : "";
}

function eventTimeMs(iso?: string | null): number {
  if (!iso) return 0;
  const d = dayjs(iso);
  return d.isValid() ? d.valueOf() : 0;
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

function groupLogsByRun(logs: AgentAuditLogEntry[]): RunAuditGroup[] {
  const order: string[] = [];
  const map = new Map<string, AgentAuditLogEntry[]>();
  for (const entry of logs) {
    const key = entry.run_id?.trim() || "__none__";
    if (!map.has(key)) {
      order.push(key);
      map.set(key, []);
    }
    map.get(key)!.push(entry);
  }

  return order.map((key) => {
    const groupLogs = map.get(key) ?? [];
    const latestAt = groupLogs.reduce(
      (best, e) => (eventTimeMs(e.created_at) > eventTimeMs(best) ? (e.created_at ?? "") : best),
      groupLogs[0]?.created_at ?? "",
    );
    return {
      runId: key === "__none__" ? null : key,
      logs: groupLogs,
      latestAt,
    };
  });
}

function buildSessionGroups(
  sessions: AiSession[],
  logsByThread: Record<string, AgentAuditLogEntry[]>,
  filterEventType?: string,
): SessionAuditGroup[] {
  const groups: SessionAuditGroup[] = [];
  for (const session of sessions) {
    let logs = logsByThread[session.thread_id] ?? [];
    if (filterEventType) {
      logs = logs.filter((e) => e.event_type === filterEventType);
    }
    if (logs.length === 0) continue;
    const latestAt = logs.reduce(
      (best, e) => (eventTimeMs(e.created_at) > eventTimeMs(best) ? (e.created_at ?? "") : best),
      logs[0]?.created_at ?? session.updated_at ?? "",
    );
    groups.push({
      threadId: session.thread_id,
      title: session.title || session.thread_id.slice(0, 8),
      updatedAt: session.updated_at,
      logs,
      latestAt,
      runs: groupLogsByRun(logs),
    });
  }
  groups.sort((a, b) => eventTimeMs(b.latestAt) - eventTimeMs(a.latestAt));
  return groups;
}

function EventCollapse({
  logs,
  eventLabel,
  intl,
}: {
  logs: AgentAuditLogEntry[];
  eventLabel: (eventType: string) => string;
  intl: IntlShape;
}) {
  const items = logs.map((entry, index) => {
    const key = String(entry.id ?? `${entry.created_at}-${entry.event_type}-${index}`);
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

  return <Collapse ghost size="small" className={styles.auditDrawerCollapse} items={items} />;
}

/** 审计日志面板（配置页内嵌；不再以 Drawer 打开） */
export default function AuditLogPanel() {
  const intl = useIntl();
  const { currentThreadId } = useAiAssistantStore();
  const [loading, setLoading] = useState(false);
  const [sessions, setSessions] = useState<AiSession[]>([]);
  const [logsByThread, setLogsByThread] = useState<Record<string, AgentAuditLogEntry[]>>({});
  const [filterEventType, setFilterEventType] = useState<string | undefined>();
  const [activeSessionKeys, setActiveSessionKeys] = useState<string[]>([]);

  const loadAudit = useCallback(
    async (options?: { notify?: boolean }) => {
      setLoading(true);
      try {
        const { sessions: sessionRows } = await AgentController.getSessions();
        const nextSessions = sessionRows ?? [];
        setSessions(nextSessions);

        const results = await Promise.allSettled(
          nextSessions.map(async (session) => {
            const { logs } = await AgentController.getThreadAudit(session.thread_id, {
              limit: 200,
            });
            return { threadId: session.thread_id, logs: logs ?? [] };
          }),
        );

        const nextLogs: Record<string, AgentAuditLogEntry[]> = {};
        let total = 0;
        for (const result of results) {
          if (result.status !== "fulfilled") continue;
          nextLogs[result.value.threadId] = result.value.logs;
          total += result.value.logs.length;
        }
        setLogsByThread(nextLogs);

        const withLogs = nextSessions
          .filter((s) => (nextLogs[s.thread_id] ?? []).length > 0)
          .map((s) => s.thread_id);
        // 优先展开当前会话；否则展开最近有记录的会话
        const activeThreadId = useAiAssistantStore.getState().currentThreadId;
        const preferred =
          activeThreadId && withLogs.includes(activeThreadId)
            ? activeThreadId
            : (withLogs[0] ?? null);
        setActiveSessionKeys(preferred ? [preferred] : []);

        if (options?.notify) {
          message.success(
            intl.formatMessage(
              { id: "aiAssistant.audit.refreshedSessions" },
              { sessions: withLogs.length, count: total },
            ),
          );
        }
      } catch (err) {
        message.error(
          err instanceof Error
            ? err.message
            : intl.formatMessage({ id: "aiAssistant.audit.loadFailed" }),
        );
        setSessions([]);
        setLogsByThread({});
        setActiveSessionKeys([]);
      } finally {
        setLoading(false);
      }
    },
    [intl],
  );

  useEffect(() => {
    void loadAudit();
  }, [loadAudit]);

  // 切到有审计记录的会话时，自动展开对应分组（不重拉数据）
  useEffect(() => {
    if (!currentThreadId) return;
    const hasLogs = (logsByThread[currentThreadId] ?? []).length > 0;
    if (!hasLogs) return;
    setActiveSessionKeys((prev) =>
      prev.includes(currentThreadId) ? prev : [currentThreadId, ...prev],
    );
  }, [currentThreadId, logsByThread]);

  const handleRefresh = useCallback(() => {
    void loadAudit({ notify: true });
  }, [loadAudit]);

  const sessionGroups = useMemo(
    () => buildSessionGroups(sessions, logsByThread, filterEventType),
    [sessions, logsByThread, filterEventType],
  );

  const totalEvents = useMemo(
    () => sessionGroups.reduce((sum, g) => sum + g.logs.length, 0),
    [sessionGroups],
  );

  const eventLabel = (eventType: string) => {
    const suffix = EVENT_TYPE_I18N[eventType] ?? "default";
    return intl.formatMessage({ id: `aiAssistant.audit.event.${suffix}` });
  };

  const sessionCollapseItems = sessionGroups.map((group) => {
    const isCurrent = group.threadId === currentThreadId;
    const runItems = group.runs.map((run, runIndex) => {
      const runKey = run.runId ?? `none-${runIndex}`;
      const runTitle = run.runId
        ? intl.formatMessage(
            { id: "aiAssistant.audit.runLabel" },
            { id: run.runId.length > 12 ? `${run.runId.slice(0, 8)}…` : run.runId },
          )
        : intl.formatMessage({ id: "aiAssistant.audit.runUnknown" });

      return {
        key: runKey,
        label: (
          <div className={styles.auditRunCollapseLabel}>
            <Text strong className={styles.auditRunTitle}>
              {runTitle}
            </Text>
            <Text type="secondary" className={styles.auditRunMeta}>
              {intl.formatMessage(
                { id: "aiAssistant.audit.runEventCount" },
                { count: run.logs.length },
              )}
            </Text>
            <Text type="secondary" className={styles.auditDrawerTime}>
              {formatAuditTime(run.latestAt)}
            </Text>
          </div>
        ),
        children: <EventCollapse logs={run.logs} eventLabel={eventLabel} intl={intl} />,
      };
    });

    return {
      key: group.threadId,
      label: (
        <div className={styles.auditSessionCollapseLabel}>
          <div className={styles.auditSessionTitleRow}>
            <Text strong ellipsis className={styles.auditSessionTitle}>
              {group.title}
            </Text>
            {isCurrent ? (
              <Tag color="processing">
                {intl.formatMessage({ id: "aiAssistant.audit.currentSession" })}
              </Tag>
            ) : null}
          </div>
          <div className={styles.auditSessionMetaRow}>
            <Text type="secondary">
              {intl.formatMessage(
                { id: "aiAssistant.audit.sessionMeta" },
                {
                  events: group.logs.length,
                  runs: group.runs.length,
                },
              )}
            </Text>
            <Text type="secondary" className={styles.auditDrawerTime}>
              {formatAuditTime(group.latestAt)}
            </Text>
          </div>
        </div>
      ),
      children: (
        <Collapse
          ghost
          size="small"
          className={styles.auditRunCollapse}
          defaultActiveKey={group.runs.slice(0, 2).map((r, i) => r.runId ?? `none-${i}`)}
          items={runItems}
        />
      ),
    };
  });

  return (
    <div className={styles.auditPanel}>
      <Text type="secondary" className={styles.auditPanelIntro}>
        {intl.formatMessage({ id: "aiAssistant.audit.intro" })}
      </Text>

      <div className={styles.auditDrawerFilters}>
        <Text type="secondary" className={styles.auditDrawerCount}>
          {intl.formatMessage(
            { id: "aiAssistant.audit.sessionTotalCount" },
            { sessions: sessionGroups.length, count: totalEvents },
          )}
        </Text>
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
        <Button
          type="default"
          size="small"
          icon={<ReloadOutlined />}
          loading={loading}
          onClick={handleRefresh}
        >
          {intl.formatMessage({ id: "aiAssistant.audit.refresh" })}
        </Button>
      </div>

      {loading && sessionGroups.length === 0 && sessions.length === 0 ? (
        <div className={styles.auditDrawerLoading}>
          <Spin />
        </div>
      ) : sessionGroups.length === 0 ? (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={intl.formatMessage({ id: "aiAssistant.audit.empty" })}
        />
      ) : (
        <div className={loading ? styles.auditDrawerListLoading : undefined}>
          <Collapse
            ghost
            size="small"
            className={styles.auditSessionCollapse}
            activeKey={activeSessionKeys}
            onChange={(keys) =>
              setActiveSessionKeys(Array.isArray(keys) ? keys.map(String) : [String(keys)])
            }
            items={sessionCollapseItems}
          />
        </div>
      )}
    </div>
  );
}
