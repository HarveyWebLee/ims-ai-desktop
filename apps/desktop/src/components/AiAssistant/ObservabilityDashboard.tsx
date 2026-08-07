/**
 * 可观测仪表盘 — 跨会话运行指标；列表按会话分组，展开查看各次 run
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Button,
  Card,
  Col,
  Collapse,
  Drawer,
  Empty,
  Row,
  Select,
  Space,
  Spin,
  Statistic,
  Table,
  Tag,
  Typography,
} from "antd";
import { ReloadOutlined } from "@ant-design/icons";
import { useIntl, type IntlShape } from "react-intl";
import dayjs from "dayjs";
import type { ColumnsType } from "antd/es/table";
import type { TraceEvent } from "@ims/shared-types";
import { message } from "@/antd/feedback";
import * as AgentController from "@/services/AgentController";
import type {
  AgentAuditLogEntry,
  ObservabilityRunSummary,
  ObservabilitySummary,
} from "@/services/AgentController";
import { getTraceKindClassName, getTraceKindLabelKey } from "./utils/traceTagUtils";
import styles from "./index.module.less";

const { Text, Title } = Typography;

const HOUR_OPTIONS = [
  { value: 6, labelKey: "hours6" },
  { value: 24, labelKey: "hours24" },
  { value: 72, labelKey: "hours72" },
  { value: 168, labelKey: "hours168" },
] as const;

type RunStatus = ObservabilityRunSummary["status"];

/** 会话级聚合行（外层表） */
interface SessionGroupRow {
  thread_id: string;
  thread_title: string;
  run_count: number;
  ok_count: number;
  error_count: number;
  interrupted_count: number;
  /** 最差状态：error > interrupted > ok */
  status: RunStatus;
  last_started_at: number;
  total_duration_ms: number | null;
  tool_call_count: number;
  tool_fail_count: number;
  last_message_preview: string;
  runs: ObservabilityRunSummary[];
}

function formatPct(rate: number | null | undefined): string {
  if (rate == null || Number.isNaN(rate)) return "—";
  return `${(rate * 100).toFixed(1)}%`;
}

function formatMs(ms: number | null | undefined): string {
  if (ms == null || Number.isNaN(ms)) return "—";
  if (ms < 1000) return `${ms} ms`;
  return `${(ms / 1000).toFixed(1)} s`;
}

function statusColor(status: RunStatus): string {
  if (status === "error") return "error";
  if (status === "interrupted") return "warning";
  return "success";
}

function worstStatus(statuses: RunStatus[]): RunStatus {
  if (statuses.includes("error")) return "error";
  if (statuses.includes("interrupted")) return "interrupted";
  return "ok";
}

/** 将扁平 run 列表按会话分组，会话按最近活动倒序 */
function groupRunsBySession(runs: ObservabilityRunSummary[]): SessionGroupRow[] {
  const byThread = new Map<string, ObservabilityRunSummary[]>();
  for (const run of runs) {
    const tid = run.thread_id || "";
    if (!tid) continue;
    const list = byThread.get(tid) ?? [];
    list.push(run);
    byThread.set(tid, list);
  }

  const groups: SessionGroupRow[] = [];
  for (const [threadId, threadRuns] of byThread) {
    const sorted = [...threadRuns].sort((a, b) => (b.started_at || 0) - (a.started_at || 0));
    const durations = sorted
      .map((r) => r.duration_ms)
      .filter((d): d is number => typeof d === "number");
    const latest = sorted[0];
    groups.push({
      thread_id: threadId,
      thread_title: latest?.thread_title || threadId.slice(0, 8),
      run_count: sorted.length,
      ok_count: sorted.filter((r) => r.status === "ok").length,
      error_count: sorted.filter((r) => r.status === "error").length,
      interrupted_count: sorted.filter((r) => r.status === "interrupted").length,
      status: worstStatus(sorted.map((r) => r.status)),
      last_started_at: latest?.started_at ?? 0,
      total_duration_ms: durations.length ? durations.reduce((sum, d) => sum + d, 0) : null,
      tool_call_count: sorted.reduce((sum, r) => sum + (r.tool_call_count || 0), 0),
      tool_fail_count: sorted.reduce((sum, r) => sum + (r.tool_fail_count || 0), 0),
      last_message_preview: latest?.user_message_preview || "",
      runs: sorted,
    });
  }

  groups.sort((a, b) => (b.last_started_at || 0) - (a.last_started_at || 0));
  return groups;
}

function channelLabel(intl: IntlShape, channel: unknown): string | null {
  if (channel === "mcp") return intl.formatMessage({ id: "aiAssistant.observability.channelMcp" });
  if (channel === "rag") return intl.formatMessage({ id: "aiAssistant.observability.channelRag" });
  if (channel === "local")
    return intl.formatMessage({ id: "aiAssistant.observability.channelLocal" });
  return null;
}

function summarizeEventDetail(event: TraceEvent): string {
  const d = event.detail ?? {};
  if (event.kind === "user_message") return String(d.message ?? "");
  if (event.kind === "llm_input") {
    const content = String(d.content ?? "");
    return content.length > 160 ? `${content.slice(0, 160)}…` : content;
  }
  if (event.kind === "assistant_message") {
    const content = String(d.content ?? "");
    return content.length > 160 ? `${content.slice(0, 160)}…` : content;
  }
  if (event.kind === "rag_passive") {
    if (d.skipped) return "skipped";
    const hits = Number(d.hit_count ?? 0);
    return `hits=${hits}`;
  }
  if (event.kind === "tool_start") {
    const argsJson = String(d.args_json ?? JSON.stringify(d.args ?? {}));
    return argsJson.length > 120 ? `${argsJson.slice(0, 120)}…` : argsJson;
  }
  if (event.kind === "tool_end") {
    return String(d.summary || d.rag_summary || d.result_preview || "").slice(0, 160);
  }
  if (event.kind === "context") {
    const tools = Array.isArray(d.tool_subset) ? d.tool_subset.length : 0;
    return `model=${d.model_id || "—"} · tools=${tools}`;
  }
  return event.label;
}

function buildFlowSummary(events: TraceEvent[]): string[] {
  const steps: string[] = [];
  for (const e of events) {
    if (e.kind === "user_message") steps.push("用户输入");
    else if (e.kind === "rag_passive") {
      const d = e.detail ?? {};
      if (d.skipped) steps.push("被动RAG(跳过)");
      else if (Number(d.hit_count ?? 0) > 0) steps.push(`被动RAG(${d.hit_count})`);
      else steps.push("被动RAG(无命中)");
    } else if (e.kind === "llm_input") steps.push("LLM入参");
    else if (e.kind === "assistant_message") steps.push("LLM回复");
    else if (e.kind === "tool_start") {
      const ch = String(e.detail?.channel || "tool");
      const tool = String(e.detail?.tool || "");
      steps.push(`${ch.toUpperCase()}→${tool}`);
    } else if (e.kind === "tool_end") {
      const ok = e.detail?.ok !== false;
      steps.push(ok ? "工具结果✓" : "工具结果✗");
    } else if (e.kind === "interrupt") steps.push("HITL");
    else if (e.kind === "done") steps.push("结束");
    else if (e.kind === "error") steps.push("错误");
  }
  return steps;
}

function RunTimeline({ events }: { events: TraceEvent[] }) {
  const intl = useIntl();
  if (!events.length) {
    return (
      <Text type="secondary">
        {intl.formatMessage({ id: "aiAssistant.observability.noTimeline" })}
      </Text>
    );
  }
  const flow = buildFlowSummary(events);
  return (
    <div className={styles.observabilityTimeline}>
      <Text type="secondary" className={styles.observabilityTimelineHint}>
        {intl.formatMessage({ id: "aiAssistant.observability.timelineHint" })}
      </Text>
      {flow.length > 0 ? (
        <div className={styles.observabilityFlowSummary}>
          <Text strong>{intl.formatMessage({ id: "aiAssistant.observability.flowSummary" })}</Text>
          <Text className={styles.observabilityFlowChain}>{flow.join(" → ")}</Text>
        </div>
      ) : null}
      <Collapse
        size="small"
        items={events.map((event, idx) => {
          const channel = channelLabel(intl, event.detail?.channel);
          const preview = summarizeEventDetail(event);
          return {
            key: event.id || String(idx),
            label: (
              <div className={styles.observabilityTimelineLabel}>
                <Text type="secondary" className={styles.observabilityTimelineIdx}>
                  {idx + 1}
                </Text>
                <span
                  className={`${styles.traceKindTag} ${styles[getTraceKindClassName(event.kind)]}`}
                >
                  {intl.formatMessage({ id: getTraceKindLabelKey(event.kind) })}
                </span>
                {channel ? (
                  <Tag className={styles.observabilityTimelineChannel}>{channel}</Tag>
                ) : null}
                <Text ellipsis={{ tooltip: true }} className={styles.observabilityTimelinePreview}>
                  {event.label}
                  {preview ? ` · ${preview}` : ""}
                </Text>
              </div>
            ),
            children: (
              <pre className={styles.observabilityTimelinePre}>
                {JSON.stringify(event.detail ?? {}, null, 2)}
              </pre>
            ),
          };
        })}
      />
    </div>
  );
}

function StatusTag({ status }: { status: RunStatus }) {
  const intl = useIntl();
  return (
    <Tag color={statusColor(status)}>
      {intl.formatMessage({ id: `aiAssistant.observability.status.${status}` })}
    </Tag>
  );
}

export default function ObservabilityDashboard() {
  const intl = useIntl();
  const [hours, setHours] = useState(24);
  const [statusFilter, setStatusFilter] = useState<RunStatus | undefined>();
  const [loading, setLoading] = useState(false);
  const [summary, setSummary] = useState<ObservabilitySummary | null>(null);
  const [runs, setRuns] = useState<ObservabilityRunSummary[]>([]);
  const [totalRuns, setTotalRuns] = useState(0);
  const [detailOpen, setDetailOpen] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailEvents, setDetailEvents] = useState<TraceEvent[]>([]);
  const [detailAudits, setDetailAudits] = useState<AgentAuditLogEntry[]>([]);
  const [detailSummary, setDetailSummary] = useState<ObservabilityRunSummary | null>(null);

  const sessionGroups = useMemo(() => groupRunsBySession(runs), [runs]);

  const load = useCallback(
    async (options?: { notify?: boolean }) => {
      setLoading(true);
      try {
        const [sum, list] = await Promise.all([
          AgentController.getObservabilitySummary({ hours }),
          AgentController.listObservabilityRuns({
            hours,
            status: statusFilter,
            limit: 100,
            offset: 0,
          }),
        ]);
        setSummary(sum);
        setRuns(list.runs ?? []);
        setTotalRuns(list.total ?? 0);
        if (options?.notify) {
          message.success(
            intl.formatMessage(
              { id: "aiAssistant.observability.refreshed" },
              { count: list.total ?? 0 },
            ),
          );
        }
      } catch (err) {
        message.error(
          err instanceof Error
            ? err.message
            : intl.formatMessage({ id: "aiAssistant.observability.loadFailed" }),
        );
      } finally {
        setLoading(false);
      }
    },
    [hours, statusFilter, intl],
  );

  useEffect(() => {
    void load();
  }, [load]);

  const openDetail = async (row: ObservabilityRunSummary) => {
    setDetailOpen(true);
    setDetailLoading(true);
    setDetailSummary(row);
    setDetailEvents([]);
    setDetailAudits([]);
    try {
      const detail = await AgentController.getObservabilityRunDetail(row.thread_id, row.run_id);
      const events = (detail.run?.events ?? []) as TraceEvent[];
      setDetailEvents(events);
      setDetailAudits(detail.audit_logs ?? []);
      if (detail.summary) setDetailSummary(detail.summary);
    } catch (err) {
      message.error(
        err instanceof Error
          ? err.message
          : intl.formatMessage({ id: "aiAssistant.observability.detailFailed" }),
      );
    } finally {
      setDetailLoading(false);
    }
  };

  const sessionColumns: ColumnsType<SessionGroupRow> = [
    {
      title: intl.formatMessage({ id: "aiAssistant.observability.colSession" }),
      dataIndex: "thread_title",
      ellipsis: true,
      render: (title: string, row) => (
        <div className={styles.observabilitySessionCell}>
          <Text strong ellipsis={{ tooltip: title }}>
            {title}
          </Text>
          <Text
            type="secondary"
            className={styles.observabilitySessionId}
            copyable={{ text: row.thread_id }}
          >
            {row.thread_id.slice(0, 8)}…
          </Text>
        </div>
      ),
    },
    {
      title: intl.formatMessage({ id: "aiAssistant.observability.colLastActive" }),
      dataIndex: "last_started_at",
      width: 140,
      render: (v: number) => (v ? dayjs(v).format("MM-DD HH:mm:ss") : "—"),
    },
    {
      title: intl.formatMessage({ id: "aiAssistant.observability.colRunCount" }),
      dataIndex: "run_count",
      width: 110,
      render: (count: number, row) => (
        <Space size={4} wrap>
          <Text>{count}</Text>
          {row.error_count > 0 ? <Tag color="error">{row.error_count}</Tag> : null}
          {row.interrupted_count > 0 ? <Tag color="warning">{row.interrupted_count}</Tag> : null}
        </Space>
      ),
    },
    {
      title: intl.formatMessage({ id: "aiAssistant.observability.colStatus" }),
      dataIndex: "status",
      width: 100,
      render: (status: RunStatus) => <StatusTag status={status} />,
    },
    {
      title: intl.formatMessage({ id: "aiAssistant.observability.colDuration" }),
      dataIndex: "total_duration_ms",
      width: 90,
      render: (v: number | null) => formatMs(v),
    },
    {
      title: intl.formatMessage({ id: "aiAssistant.observability.colTools" }),
      key: "tools",
      width: 90,
      render: (_, row) =>
        `${row.tool_call_count}${row.tool_fail_count ? ` / ✗${row.tool_fail_count}` : ""}`,
    },
    {
      title: intl.formatMessage({ id: "aiAssistant.observability.colLastMessage" }),
      dataIndex: "last_message_preview",
      ellipsis: true,
      render: (v: string) => v || "—",
    },
  ];

  const runColumns: ColumnsType<ObservabilityRunSummary> = [
    {
      title: intl.formatMessage({ id: "aiAssistant.observability.colStarted" }),
      dataIndex: "started_at",
      width: 140,
      render: (v: number) => (v ? dayjs(v).format("MM-DD HH:mm:ss") : "—"),
    },
    {
      title: intl.formatMessage({ id: "aiAssistant.observability.colStatus" }),
      dataIndex: "status",
      width: 100,
      render: (status: RunStatus) => <StatusTag status={status} />,
    },
    {
      title: intl.formatMessage({ id: "aiAssistant.observability.colDuration" }),
      dataIndex: "duration_ms",
      width: 90,
      render: (v: number | null) => formatMs(v),
    },
    {
      title: intl.formatMessage({ id: "aiAssistant.observability.colTools" }),
      key: "tools",
      width: 90,
      render: (_, row) =>
        `${row.tool_call_count}${row.tool_fail_count ? ` / ✗${row.tool_fail_count}` : ""}`,
    },
    {
      title: intl.formatMessage({ id: "aiAssistant.observability.colMessage" }),
      dataIndex: "user_message_preview",
      ellipsis: true,
      render: (v: string) => v || "—",
    },
  ];

  return (
    <div className={styles.observabilityRoot}>
      <div className={styles.observabilityToolbar}>
        <Space wrap>
          <Select
            value={hours}
            style={{ width: 140 }}
            options={HOUR_OPTIONS.map((o) => ({
              value: o.value,
              label: intl.formatMessage({ id: `aiAssistant.observability.${o.labelKey}` }),
            }))}
            onChange={setHours}
          />
          <Select
            allowClear
            placeholder={intl.formatMessage({ id: "aiAssistant.observability.filterStatus" })}
            style={{ width: 140 }}
            value={statusFilter}
            options={[
              {
                value: "ok",
                label: intl.formatMessage({ id: "aiAssistant.observability.status.ok" }),
              },
              {
                value: "error",
                label: intl.formatMessage({ id: "aiAssistant.observability.status.error" }),
              },
              {
                value: "interrupted",
                label: intl.formatMessage({
                  id: "aiAssistant.observability.status.interrupted",
                }),
              },
            ]}
            onChange={(v) => setStatusFilter(v)}
          />
          <Button icon={<ReloadOutlined />} onClick={() => void load({ notify: true })}>
            {intl.formatMessage({ id: "aiAssistant.observability.refresh" })}
          </Button>
        </Space>
        <Text type="secondary">
          {intl.formatMessage({ id: "aiAssistant.observability.intro" })}
        </Text>
      </div>

      <Spin spinning={loading}>
        <Row gutter={[12, 12]} className={styles.observabilityStats}>
          <Col xs={12} sm={8} md={4}>
            <Card size="small">
              <Statistic
                title={intl.formatMessage({ id: "aiAssistant.observability.metric.runs" })}
                value={summary?.run_count ?? 0}
              />
            </Card>
          </Col>
          <Col xs={12} sm={8} md={4}>
            <Card size="small">
              <Statistic
                title={intl.formatMessage({ id: "aiAssistant.observability.metric.successRate" })}
                value={formatPct(summary?.success_rate)}
              />
            </Card>
          </Col>
          <Col xs={12} sm={8} md={4}>
            <Card size="small">
              <Statistic
                title={intl.formatMessage({ id: "aiAssistant.observability.metric.p50" })}
                value={formatMs(summary?.latency_ms?.p50)}
              />
            </Card>
          </Col>
          <Col xs={12} sm={8} md={4}>
            <Card size="small">
              <Statistic
                title={intl.formatMessage({ id: "aiAssistant.observability.metric.p95" })}
                value={formatMs(summary?.latency_ms?.p95)}
              />
            </Card>
          </Col>
          <Col xs={12} sm={8} md={4}>
            <Card size="small">
              <Statistic
                title={intl.formatMessage({ id: "aiAssistant.observability.metric.hitl" })}
                value={
                  summary
                    ? summary.hitl.emit +
                      summary.hitl.approve +
                      summary.hitl.reject +
                      summary.hitl.abort
                    : 0
                }
                suffix={
                  summary
                    ? ` (✓${summary.hitl.approve}/✗${summary.hitl.reject}/⊘${summary.hitl.abort})`
                    : undefined
                }
              />
            </Card>
          </Col>
          <Col xs={12} sm={8} md={4}>
            <Card size="small">
              <Statistic
                title={intl.formatMessage({ id: "aiAssistant.observability.metric.toolFail" })}
                value={formatPct(summary?.tool_fail_rate)}
                suffix={summary ? ` (${summary.tool_fail_count}/${summary.tool_calls})` : undefined}
              />
            </Card>
          </Col>
        </Row>

        <Card
          size="small"
          className={styles.observabilityRunsCard}
          title={intl.formatMessage(
            { id: "aiAssistant.observability.sessionsTitle" },
            { sessions: sessionGroups.length, runs: totalRuns },
          )}
        >
          {sessionGroups.length === 0 && !loading ? (
            <Empty description={intl.formatMessage({ id: "aiAssistant.observability.empty" })} />
          ) : (
            <Table
              size="small"
              rowKey={(r) => r.thread_id}
              columns={sessionColumns}
              dataSource={sessionGroups}
              pagination={false}
              expandable={{
                expandedRowRender: (session) => (
                  <Table
                    size="small"
                    className={styles.observabilityNestedRuns}
                    rowKey={(r) => r.run_id}
                    columns={runColumns}
                    dataSource={session.runs}
                    pagination={false}
                    onRow={(row) => ({
                      onClick: () => void openDetail(row),
                      style: { cursor: "pointer" },
                    })}
                  />
                ),
                rowExpandable: (session) => session.run_count > 0,
              }}
            />
          )}
        </Card>
      </Spin>

      <Drawer
        title={intl.formatMessage({ id: "aiAssistant.observability.detailTitle" })}
        open={detailOpen}
        onClose={() => setDetailOpen(false)}
        width={520}
        destroyOnHidden
      >
        <Spin spinning={detailLoading}>
          {detailSummary ? (
            <Space direction="vertical" size="middle" style={{ width: "100%" }}>
              <div>
                <Title level={5} style={{ margin: 0 }}>
                  {detailSummary.thread_title || detailSummary.thread_id}
                </Title>
                <Text type="secondary" copyable>
                  {detailSummary.run_id}
                </Text>
                <div style={{ marginTop: 8 }}>
                  <StatusTag status={detailSummary.status} />
                  <Text type="secondary">{formatMs(detailSummary.duration_ms)}</Text>
                </div>
                {detailSummary.user_message_preview ? (
                  <Text>{detailSummary.user_message_preview}</Text>
                ) : null}
              </div>
              <div>
                <Title level={5} style={{ marginBottom: 8 }}>
                  {intl.formatMessage({ id: "aiAssistant.observability.timelineTitle" })}
                </Title>
                <RunTimeline events={detailEvents} />
              </div>
              {detailAudits.length > 0 ? (
                <div>
                  <Text type="secondary">
                    {intl.formatMessage(
                      { id: "aiAssistant.observability.auditCount" },
                      { count: detailAudits.length },
                    )}
                  </Text>
                  <ul className={styles.observabilityAuditList}>
                    {detailAudits.slice(0, 30).map((entry, idx) => (
                      <li key={entry.id ?? `${entry.event_type}-${idx}`}>
                        <Tag>{entry.event_type}</Tag>
                        {entry.tool_name ? <Text>{entry.tool_name}</Text> : null}
                        {entry.created_at ? (
                          <Text type="secondary">{dayjs(entry.created_at).format("HH:mm:ss")}</Text>
                        ) : null}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </Space>
          ) : null}
        </Spin>
      </Drawer>
    </div>
  );
}
