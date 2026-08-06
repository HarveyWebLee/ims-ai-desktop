/**
 * 知识库运营面板：文档级分页列表；展开行用 Markdown 预览器懒加载全文
 */
import { useCallback, useEffect, useMemo, useRef, useState, type Key } from "react";
import {
  Alert,
  Button,
  Card,
  Descriptions,
  Empty,
  Input,
  Popconfirm,
  Progress,
  Space,
  Spin,
  Table,
  Tag,
  Tooltip,
  Typography,
  Upload,
} from "antd";
import type { TableColumnsType, TablePaginationConfig } from "antd";
import {
  CloudUploadOutlined,
  DeleteOutlined,
  DownloadOutlined,
  ClearOutlined,
  ReloadOutlined,
  SearchOutlined,
  UploadOutlined,
} from "@ant-design/icons";
import { useIntl } from "react-intl";
import { message } from "@/antd/feedback";
import MarkdownContent from "@/components/MarkdownContent";
import * as AgentController from "@/services/AgentController";
import type {
  KnowledgeAudit,
  KnowledgeDocumentItem,
  KnowledgeIngestJob,
  KnowledgePointItem,
  KnowledgeStats,
} from "@/services/AgentController";

const { Text, Paragraph } = Typography;

const DEFAULT_PAGE_SIZE = 20;
const INGEST_POLL_MS = 1200;

type KnowledgeDocRow = {
  key: string;
  source: string;
  filename: string;
  score: number;
  chunkHits: number;
};

type PreviewState = {
  loading: boolean;
  content?: string;
  from?: string;
  error?: string;
};

function triggerBrowserDownload(filename: string, content: string): void {
  const blob = new Blob([content], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename || "knowledge.md";
  anchor.click();
  URL.revokeObjectURL(url);
}

function docsToRows(items: KnowledgeDocumentItem[]): KnowledgeDocRow[] {
  return items
    .filter((item) => (item.source || "").trim())
    .map((item) => ({
      key: item.source,
      source: item.source,
      filename: item.filename || item.source.split(/[/\\]/).pop() || item.source,
      score: 0,
      chunkHits: item.chunk_count ?? 0,
    }));
}

/** 检索命中按 source 去重为文档行（保留最高分） */
function searchHitsToRows(items: KnowledgePointItem[]): KnowledgeDocRow[] {
  const map = new Map<string, KnowledgeDocRow>();
  for (const item of items) {
    const source = (item.source || "").trim();
    if (!source) continue;
    const filename = item.filename || source.split(/[/\\]/).pop() || source;
    const existing = map.get(source);
    if (!existing) {
      map.set(source, {
        key: source,
        source,
        filename,
        score: item.score ?? 0,
        chunkHits: 1,
      });
      continue;
    }
    existing.chunkHits += 1;
    if ((item.score ?? 0) > existing.score) {
      existing.score = item.score ?? 0;
    }
  }
  return Array.from(map.values());
}

function KnowledgeMdPreview({
  source,
  state,
}: {
  source: string;
  state: PreviewState | undefined;
}) {
  const intl = useIntl();
  if (!state || state.loading) {
    return (
      <div style={{ padding: "12px 8px", textAlign: "center" }}>
        <Spin tip={intl.formatMessage({ id: "aiAssistant.knowledge.previewLoading" })} />
      </div>
    );
  }
  if (state.error) {
    return (
      <Alert
        type="error"
        showIcon
        title={intl.formatMessage(
          { id: "aiAssistant.knowledge.previewFailed" },
          { reason: state.error },
        )}
      />
    );
  }
  if (!state.content?.trim()) {
    return (
      <Empty
        image={Empty.PRESENTED_IMAGE_SIMPLE}
        description={intl.formatMessage({ id: "aiAssistant.knowledge.previewEmpty" })}
      />
    );
  }
  return (
    <div
      style={{
        maxHeight: 420,
        overflow: "auto",
        padding: "8px 12px",
        borderRadius: 8,
        background: "var(--ant-color-fill-quaternary, rgba(0,0,0,0.02))",
      }}
    >
      <Text type="secondary" style={{ fontSize: 12, display: "block", marginBottom: 8 }}>
        {intl.formatMessage(
          { id: "aiAssistant.knowledge.previewMeta" },
          { source, from: state.from || "—" },
        )}
      </Text>
      <MarkdownContent content={state.content} />
    </div>
  );
}

export default function KnowledgeOpsPanel() {
  const intl = useIntl();
  const [stats, setStats] = useState<KnowledgeStats | null>(null);
  const [audit, setAudit] = useState<KnowledgeAudit | null>(null);
  const [docs, setDocs] = useState<KnowledgeDocRow[]>([]);
  const [docTotal, setDocTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE);
  const [listTruncated, setListTruncated] = useState(false);
  const [loading, setLoading] = useState(false);
  const [searching, setSearching] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [dropping, setDropping] = useState(false);
  const [ingestJob, setIngestJob] = useState<KnowledgeIngestJob | null>(null);
  const [busySource, setBusySource] = useState<string | null>(null);
  const [sourceFilter, setSourceFilter] = useState("");
  const [appliedFilter, setAppliedFilter] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [searchHits, setSearchHits] = useState<KnowledgePointItem[] | null>(null);
  const [searchPage, setSearchPage] = useState(1);
  const [searchPageSize, setSearchPageSize] = useState(DEFAULT_PAGE_SIZE);
  const [expandedKeys, setExpandedKeys] = useState<readonly Key[]>([]);
  const [previews, setPreviews] = useState<Record<string, PreviewState>>({});
  const ingestCompletionNotifiedRef = useRef<string | null>(null);

  const loadStats = useCallback(async () => {
    try {
      const [s, a] = await Promise.all([
        AgentController.getKnowledgeStats(),
        AgentController.getKnowledgeAudit().catch(() => null),
      ]);
      setStats(s);
      setAudit(a);
    } catch (err) {
      message.error(
        intl.formatMessage(
          { id: "aiAssistant.knowledge.loadFailed" },
          { reason: err instanceof Error ? err.message : String(err) },
        ),
      );
    }
  }, [intl]);

  const loadDocuments = useCallback(
    async (nextPage: number, nextPageSize: number, filter: string) => {
      setLoading(true);
      try {
        const list = await AgentController.listKnowledgeDocuments({
          page: nextPage,
          pageSize: nextPageSize,
          sourceContains: filter.trim() || undefined,
        });
        setDocs(docsToRows(list.items));
        setDocTotal(list.total);
        setPage(list.page);
        setPageSize(list.page_size);
        setListTruncated(Boolean(list.truncated));
        setPreviews({});
        setExpandedKeys([]);
      } catch (err) {
        message.error(
          intl.formatMessage(
            { id: "aiAssistant.knowledge.loadFailed" },
            { reason: err instanceof Error ? err.message : String(err) },
          ),
        );
      } finally {
        setLoading(false);
      }
    },
    [intl],
  );

  useEffect(() => {
    void loadStats();
  }, [loadStats]);

  useEffect(() => {
    if (searchHits != null) return;
    void loadDocuments(page, pageSize, appliedFilter);
    // 仅在页码/页大小/筛选变更时拉列表；searchHits 退出检索时由 clear 触发
    // eslint-disable-next-line react-hooks/exhaustive-deps -- 避免 searchHits 抖动重复请求
  }, [page, pageSize, appliedFilter, loadDocuments]);

  const ensurePreview = useCallback(async (source: string) => {
    let skip = false;
    setPreviews((prev) => {
      if (prev[source]?.content || prev[source]?.loading) {
        skip = true;
        return prev;
      }
      return { ...prev, [source]: { loading: true } };
    });
    if (skip) return;
    try {
      const data = await AgentController.exportKnowledgeBySource(source);
      setPreviews((prev) => ({
        ...prev,
        [source]: { loading: false, content: data.content, from: data.from },
      }));
    } catch (err) {
      setPreviews((prev) => ({
        ...prev,
        [source]: {
          loading: false,
          error: err instanceof Error ? err.message : String(err),
        },
      }));
    }
  }, []);

  const handleRefresh = async () => {
    await loadStats();
    if (searchHits != null) return;
    await loadDocuments(page, pageSize, appliedFilter);
  };

  const handleApplyFilter = () => {
    setSearchHits(null);
    setAppliedFilter(sourceFilter.trim());
    setPage(1);
  };

  const handleSearch = async () => {
    const q = searchQuery.trim();
    if (!q) {
      message.warning(intl.formatMessage({ id: "aiAssistant.knowledge.searchEmpty" }));
      return;
    }
    setSearching(true);
    try {
      const data = await AgentController.searchKnowledge({ query: q, limit: 20 });
      setSearchHits(data.items);
      setSearchPage(1);
      setPreviews({});
      setExpandedKeys([]);
      if (data.items.length === 0) {
        message.info(intl.formatMessage({ id: "aiAssistant.knowledge.searchNoHits" }));
      }
    } catch (err) {
      message.error(
        intl.formatMessage(
          { id: "aiAssistant.knowledge.searchFailed" },
          { reason: err instanceof Error ? err.message : String(err) },
        ),
      );
    } finally {
      setSearching(false);
    }
  };

  const opsLocked = uploading || dropping || ingestJob?.status === "running";

  const refreshIngestJob = useCallback(async (): Promise<KnowledgeIngestJob | null> => {
    try {
      const data = await AgentController.getKnowledgeIngestJobActive();
      setIngestJob(data.job);
      return data.job;
    } catch {
      return null;
    }
  }, []);

  useEffect(() => {
    void refreshIngestJob();
  }, [refreshIngestJob]);

  useEffect(() => {
    if (!ingestJob?.in_progress) return;
    const timer = window.setInterval(() => {
      void (async () => {
        const job = await refreshIngestJob();
        if (job && !job.in_progress) {
          if (ingestCompletionNotifiedRef.current === job.job_id) return;
          ingestCompletionNotifiedRef.current = job.job_id;
          setSearchHits(null);
          await loadStats();
          await loadDocuments(1, pageSize, appliedFilter);
          const errorSummary = (job.items || [])
            .filter((item) => item.status === "error" || item.status === "skipped")
            .map((item) => `${item.filename}: ${item.error || "?"}`)
            .slice(0, 5)
            .join("；");
          if (job.failed === 0) {
            message.success(
              intl.formatMessage(
                { id: "aiAssistant.knowledge.uploadBatchOk" },
                {
                  succeeded: job.succeeded,
                  chunks: job.chunks_total,
                  deleted: job.deleted_total,
                },
              ),
            );
          } else if (job.succeeded === 0) {
            message.error(
              intl.formatMessage(
                { id: "aiAssistant.knowledge.uploadBatchAllFailed" },
                { failed: job.failed, errors: errorSummary || "—" },
              ),
            );
          } else {
            message.warning(
              intl.formatMessage(
                { id: "aiAssistant.knowledge.uploadBatchPartial" },
                {
                  succeeded: job.succeeded,
                  failed: job.failed,
                  chunks: job.chunks_total,
                  errors: errorSummary || "—",
                },
              ),
            );
          }
        }
      })();
    }, INGEST_POLL_MS);
    return () => window.clearInterval(timer);
  }, [
    ingestJob?.in_progress,
    ingestJob?.job_id,
    refreshIngestJob,
    loadStats,
    loadDocuments,
    pageSize,
    appliedFilter,
    intl,
  ]);

  const handleUploadBatch = async (files: File[]) => {
    if (files.length === 0 || opsLocked) return;
    setUploading(true);
    const hide = message.loading(
      intl.formatMessage({ id: "aiAssistant.knowledge.uploadEnqueueing" }, { count: files.length }),
      0,
    );
    try {
      const job = await AgentController.enqueueKnowledgeIngestFiles(files);
      hide();
      ingestCompletionNotifiedRef.current = null;
      setIngestJob(job);
      message.info(
        intl.formatMessage({ id: "aiAssistant.knowledge.uploadJobStarted" }, { total: job.total }),
      );
    } catch (err) {
      hide();
      message.error(
        intl.formatMessage(
          { id: "aiAssistant.knowledge.uploadFailed" },
          { reason: err instanceof Error ? err.message : String(err) },
        ),
      );
      await refreshIngestJob();
    } finally {
      setUploading(false);
    }
  };

  const handleDownload = async (row: KnowledgeDocRow) => {
    if (!row.source || busySource) return;
    setBusySource(row.source);
    const hide = message.loading(
      intl.formatMessage({ id: "aiAssistant.knowledge.downloading" }),
      0,
    );
    try {
      const data = await AgentController.exportKnowledgeBySource(row.source);
      hide();
      triggerBrowserDownload(data.filename, data.content);
      setPreviews((prev) => ({
        ...prev,
        [row.source]: { loading: false, content: data.content, from: data.from },
      }));
      message.success(
        intl.formatMessage({ id: "aiAssistant.knowledge.downloadOk" }, { name: data.filename }),
      );
    } catch (err) {
      hide();
      message.error(
        intl.formatMessage(
          { id: "aiAssistant.knowledge.downloadFailed" },
          { reason: err instanceof Error ? err.message : String(err) },
        ),
      );
    } finally {
      setBusySource(null);
    }
  };

  const handleReplace = async (source: string, file: File) => {
    if (!source || busySource || opsLocked) return false;
    setBusySource(source);
    const hide = message.loading(intl.formatMessage({ id: "aiAssistant.knowledge.updating" }), 0);
    try {
      const result = await AgentController.replaceKnowledgeFile(source, file);
      hide();
      message.success(
        intl.formatMessage(
          { id: "aiAssistant.knowledge.updateOk" },
          { chunks: result.chunks, deleted: result.deleted_before },
        ),
      );
      setSearchHits(null);
      setPreviews((prev) => {
        const next = { ...prev };
        delete next[source];
        return next;
      });
      await loadStats();
      await loadDocuments(page, pageSize, appliedFilter);
    } catch (err) {
      hide();
      message.error(
        intl.formatMessage(
          { id: "aiAssistant.knowledge.updateFailed" },
          { reason: err instanceof Error ? err.message : String(err) },
        ),
      );
    } finally {
      setBusySource(null);
    }
    return false;
  };

  const handleDelete = async (source: string) => {
    if (opsLocked) return;
    try {
      const result = await AgentController.deleteKnowledgeBySource(source);
      message.success(
        intl.formatMessage({ id: "aiAssistant.knowledge.deleteOk" }, { count: result.deleted }),
      );
      setSearchHits(null);
      setPreviews((prev) => {
        const next = { ...prev };
        delete next[source];
        return next;
      });
      setExpandedKeys((keys) => keys.filter((k) => k !== source));
      await loadStats();
      const nextTotal = Math.max(0, docTotal - 1);
      const maxPage = Math.max(1, Math.ceil(nextTotal / pageSize) || 1);
      const nextPage = Math.min(page, maxPage);
      await loadDocuments(nextPage, pageSize, appliedFilter);
    } catch (err) {
      message.error(
        intl.formatMessage(
          { id: "aiAssistant.knowledge.deleteFailed" },
          { reason: err instanceof Error ? err.message : String(err) },
        ),
      );
    }
  };

  const handleDropCollection = async () => {
    if (opsLocked) return;
    setDropping(true);
    const hide = message.loading(
      intl.formatMessage({ id: "aiAssistant.knowledge.dropCollectionRunning" }),
      0,
    );
    try {
      const result = await AgentController.dropKnowledgeCollection();
      hide();
      if (result.dropped) {
        message.success(
          intl.formatMessage(
            { id: "aiAssistant.knowledge.dropCollectionOk" },
            { collection: result.collection },
          ),
        );
      } else {
        message.info(
          intl.formatMessage(
            { id: "aiAssistant.knowledge.dropCollectionSkipped" },
            { collection: result.collection },
          ),
        );
      }
      setSearchHits(null);
      setDocs([]);
      setDocTotal(0);
      setPreviews({});
      setExpandedKeys([]);
      setPage(1);
      await loadStats();
      await loadDocuments(1, pageSize, appliedFilter);
    } catch (err) {
      hide();
      message.error(
        intl.formatMessage(
          { id: "aiAssistant.knowledge.dropCollectionFailed" },
          { reason: err instanceof Error ? err.message : String(err) },
        ),
      );
    } finally {
      setDropping(false);
    }
  };

  const isSearchMode = searchHits != null;
  const searchRows = useMemo(() => (searchHits ? searchHitsToRows(searchHits) : []), [searchHits]);
  const tableData = isSearchMode
    ? searchRows.slice((searchPage - 1) * searchPageSize, searchPage * searchPageSize)
    : docs;

  const pagination: TablePaginationConfig = isSearchMode
    ? {
        current: searchPage,
        pageSize: searchPageSize,
        total: searchRows.length,
        showSizeChanger: true,
        pageSizeOptions: ["10", "20", "50"],
        showTotal: (total, range) =>
          intl.formatMessage(
            { id: "aiAssistant.knowledge.paginationTotal" },
            { start: range[0], end: range[1], total },
          ),
        onChange: (p, ps) => {
          setSearchPage(p);
          setSearchPageSize(ps);
          setExpandedKeys([]);
        },
      }
    : {
        current: page,
        pageSize,
        total: docTotal,
        showSizeChanger: true,
        pageSizeOptions: ["10", "20", "50"],
        showTotal: (total, range) =>
          intl.formatMessage(
            { id: "aiAssistant.knowledge.paginationTotal" },
            { start: range[0], end: range[1], total },
          ),
        onChange: (p, ps) => {
          setPage(p);
          setPageSize(ps);
          setExpandedKeys([]);
        },
      };

  const columns: TableColumnsType<KnowledgeDocRow> = [
    {
      title: intl.formatMessage({ id: "aiAssistant.knowledge.colFilename" }),
      dataIndex: "filename",
      width: 180,
      ellipsis: true,
    },
    {
      title: intl.formatMessage({ id: "aiAssistant.knowledge.colSource" }),
      dataIndex: "source",
      ellipsis: true,
      render: (v: string) => (
        <Text code style={{ fontSize: 11 }}>
          {v || "—"}
        </Text>
      ),
    },
    {
      title: intl.formatMessage({ id: "aiAssistant.knowledge.colChunks" }),
      dataIndex: "chunkHits",
      width: 88,
      render: (v: number) => (v > 0 ? v : "—"),
    },
    ...(isSearchMode
      ? [
          {
            title: intl.formatMessage({ id: "aiAssistant.knowledge.colScore" }),
            dataIndex: "score",
            width: 88,
            render: (v: number) => (v > 0 ? v.toFixed(3) : "—"),
          } satisfies TableColumnsType<KnowledgeDocRow>[number],
        ]
      : []),
    {
      title: intl.formatMessage({ id: "aiAssistant.knowledge.colActions" }),
      key: "actions",
      width: 148,
      fixed: "right",
      render: (_, row) =>
        row.source ? (
          <Space size={0}>
            <Tooltip title={intl.formatMessage({ id: "aiAssistant.knowledge.download" })}>
              <Button
                type="link"
                size="small"
                icon={<DownloadOutlined />}
                loading={busySource === row.source}
                disabled={!!busySource && busySource !== row.source}
                onClick={() => void handleDownload(row)}
              />
            </Tooltip>
            <Tooltip title={intl.formatMessage({ id: "aiAssistant.knowledge.update" })}>
              <Upload
                accept=".md,.txt,.docx,.pdf,.xlsx,.csv,.png,.jpg,.jpeg"
                showUploadList={false}
                disabled={!!busySource || opsLocked}
                beforeUpload={(file) => {
                  void handleReplace(row.source, file);
                  return false;
                }}
              >
                <Button
                  type="link"
                  size="small"
                  icon={<UploadOutlined />}
                  loading={busySource === row.source}
                  disabled={opsLocked || (!!busySource && busySource !== row.source)}
                />
              </Upload>
            </Tooltip>
            <Popconfirm
              title={intl.formatMessage({ id: "aiAssistant.knowledge.deleteConfirm" })}
              description={row.source}
              onConfirm={() => void handleDelete(row.source)}
              okText={intl.formatMessage({ id: "aiAssistant.knowledge.deleteOkBtn" })}
              cancelText={intl.formatMessage({ id: "aiAssistant.knowledge.deleteCancel" })}
              disabled={!!busySource || opsLocked}
            >
              <Tooltip title={intl.formatMessage({ id: "aiAssistant.knowledge.delete" })}>
                <Button
                  type="link"
                  danger
                  size="small"
                  icon={<DeleteOutlined />}
                  disabled={!!busySource || opsLocked}
                />
              </Tooltip>
            </Popconfirm>
          </Space>
        ) : null,
    },
  ];

  return (
    <Space direction="vertical" size={16} style={{ width: "100%" }}>
      <Card size="small">
        <Paragraph type="secondary" style={{ marginBottom: 12 }}>
          {intl.formatMessage({ id: "aiAssistant.knowledge.intro" })}
        </Paragraph>
        <Space wrap>
          <Button
            icon={<ReloadOutlined />}
            loading={loading}
            disabled={opsLocked}
            onClick={() => void handleRefresh()}
          >
            {intl.formatMessage({ id: "aiAssistant.knowledge.refresh" })}
          </Button>
          <Upload
            multiple
            accept=".md,.txt,.docx,.pdf,.xlsx,.csv,.png,.jpg,.jpeg"
            showUploadList={false}
            beforeUpload={(file, fileList) => {
              const last = fileList[fileList.length - 1];
              if (last && file.uid === last.uid) {
                void handleUploadBatch(fileList.map((item) => item as File));
              }
              return false;
            }}
            disabled={opsLocked || stats?.enabled === false}
          >
            <Button
              type="primary"
              icon={<CloudUploadOutlined />}
              loading={uploading || Boolean(ingestJob?.in_progress)}
              disabled={opsLocked || stats?.enabled === false}
            >
              {intl.formatMessage({ id: "aiAssistant.knowledge.upload" })}
            </Button>
          </Upload>
          <Popconfirm
            title={intl.formatMessage({ id: "aiAssistant.knowledge.dropCollectionConfirm" })}
            okText={intl.formatMessage({ id: "aiAssistant.knowledge.dropCollectionOkBtn" })}
            cancelText={intl.formatMessage({ id: "aiAssistant.knowledge.dropCollectionCancel" })}
            okButtonProps={{ danger: true }}
            disabled={opsLocked || stats?.enabled === false}
            onConfirm={() => void handleDropCollection()}
          >
            <Button
              danger
              icon={<ClearOutlined />}
              loading={dropping}
              disabled={opsLocked || stats?.enabled === false}
            >
              {intl.formatMessage({ id: "aiAssistant.knowledge.dropCollection" })}
            </Button>
          </Popconfirm>
        </Space>
        {ingestJob ? (
          <div style={{ marginTop: 16 }}>
            {ingestJob.status === "running" ? (
              <Alert
                type="info"
                showIcon
                style={{ marginBottom: 12 }}
                title={intl.formatMessage({ id: "aiAssistant.knowledge.jobLockedHint" })}
              />
            ) : null}
            <Text strong style={{ display: "block", marginBottom: 8 }}>
              {intl.formatMessage({ id: "aiAssistant.knowledge.jobProgressTitle" })}
            </Text>
            <Progress
              percent={ingestJob.percent}
              status={
                ingestJob.in_progress
                  ? "active"
                  : ingestJob.status === "interrupted" ||
                      (ingestJob.failed > 0 && ingestJob.succeeded === 0)
                    ? "exception"
                    : ingestJob.failed > 0
                      ? "normal"
                      : "success"
              }
              format={() => `${ingestJob.done}/${ingestJob.total}`}
            />
            <Paragraph type="secondary" style={{ marginTop: 8, marginBottom: 0 }}>
              {ingestJob.message ||
                (ingestJob.current_filename
                  ? intl.formatMessage(
                      { id: "aiAssistant.knowledge.jobCurrentFile" },
                      { name: ingestJob.current_filename },
                    )
                  : null)}
            </Paragraph>
            <Space size="middle" wrap style={{ marginTop: 8 }}>
              <Text type="secondary">
                {intl.formatMessage(
                  { id: "aiAssistant.knowledge.jobCounts" },
                  {
                    succeeded: ingestJob.succeeded,
                    failed: ingestJob.failed,
                    chunks: ingestJob.chunks_total,
                    deleted: ingestJob.deleted_total,
                  },
                )}
              </Text>
              <Tag>
                {intl.formatMessage({
                  id: `aiAssistant.knowledge.jobStatus.${ingestJob.status}`,
                })}
              </Tag>
            </Space>
          </div>
        ) : null}
      </Card>

      {stats ? (
        <Card size="small" title={intl.formatMessage({ id: "aiAssistant.knowledge.statsTitle" })}>
          <Descriptions size="small" column={1}>
            <Descriptions.Item
              label={intl.formatMessage({ id: "aiAssistant.knowledge.collection" })}
            >
              <Text code>{stats.collection}</Text>
            </Descriptions.Item>
            <Descriptions.Item label={intl.formatMessage({ id: "aiAssistant.knowledge.points" })}>
              {stats.points}
            </Descriptions.Item>
            <Descriptions.Item label={intl.formatMessage({ id: "aiAssistant.knowledge.status" })}>
              {stats.enabled === false ? (
                <Tag>{intl.formatMessage({ id: "aiAssistant.knowledge.statusDisabled" })}</Tag>
              ) : stats.ok ? (
                <Tag color="success">
                  {intl.formatMessage({ id: "aiAssistant.knowledge.statusOk" })}
                </Tag>
              ) : (
                <Tag color="error">
                  {intl.formatMessage({ id: "aiAssistant.knowledge.statusBad" })}
                </Tag>
              )}
            </Descriptions.Item>
          </Descriptions>
          {stats.message ? (
            <Alert style={{ marginTop: 8 }} type="info" showIcon title={stats.message} />
          ) : null}
          {audit && audit.orphan_count > 0 ? (
            <Alert
              style={{ marginTop: 8 }}
              type="warning"
              showIcon
              title={intl.formatMessage(
                { id: "aiAssistant.knowledge.orphanWarning" },
                { count: audit.orphan_count },
              )}
              description={
                <div>
                  {(audit.orphans || []).slice(0, 5).map((item) => (
                    <div key={item.source}>
                      <Text code style={{ fontSize: 12 }}>
                        {item.filename || item.source}
                      </Text>
                      <Text type="secondary" style={{ marginLeft: 8, fontSize: 12 }}>
                        {intl.formatMessage(
                          { id: "aiAssistant.knowledge.orphanChunks" },
                          { count: item.chunk_count },
                        )}
                      </Text>
                    </div>
                  ))}
                  {audit.orphan_count > 5 ? (
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {intl.formatMessage(
                        { id: "aiAssistant.knowledge.orphanMore" },
                        { count: audit.orphan_count - 5 },
                      )}
                    </Text>
                  ) : null}
                  <Paragraph
                    type="secondary"
                    style={{ marginTop: 8, marginBottom: 0, fontSize: 12 }}
                  >
                    {intl.formatMessage({ id: "aiAssistant.knowledge.orphanHint" })}
                  </Paragraph>
                </div>
              }
            />
          ) : null}
        </Card>
      ) : null}

      <Card size="small" title={intl.formatMessage({ id: "aiAssistant.knowledge.searchTitle" })}>
        <Space.Compact style={{ width: "100%" }}>
          <Input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={intl.formatMessage({ id: "aiAssistant.knowledge.searchPlaceholder" })}
            onPressEnter={() => void handleSearch()}
            allowClear
          />
          <Button
            type="primary"
            icon={<SearchOutlined />}
            loading={searching}
            onClick={() => void handleSearch()}
          >
            {intl.formatMessage({ id: "aiAssistant.knowledge.search" })}
          </Button>
        </Space.Compact>
        {searchHits ? (
          <Button
            type="link"
            size="small"
            style={{ marginTop: 8, paddingInline: 0 }}
            onClick={() => {
              setSearchHits(null);
              setPreviews({});
              setExpandedKeys([]);
              setPage(1);
              void loadDocuments(1, pageSize, appliedFilter);
            }}
          >
            {intl.formatMessage({ id: "aiAssistant.knowledge.clearSearch" })}
          </Button>
        ) : null}
      </Card>

      <Card
        size="small"
        title={
          isSearchMode
            ? intl.formatMessage({ id: "aiAssistant.knowledge.searchResults" })
            : intl.formatMessage({ id: "aiAssistant.knowledge.browseTitle" })
        }
        extra={
          !isSearchMode ? (
            <Space.Compact>
              <Input
                size="small"
                style={{ width: 180 }}
                value={sourceFilter}
                onChange={(e) => setSourceFilter(e.target.value)}
                placeholder={intl.formatMessage({
                  id: "aiAssistant.knowledge.filterSourcePlaceholder",
                })}
                allowClear
                onPressEnter={handleApplyFilter}
              />
              <Button size="small" onClick={handleApplyFilter} loading={loading}>
                {intl.formatMessage({ id: "aiAssistant.knowledge.filter" })}
              </Button>
            </Space.Compact>
          ) : null
        }
      >
        <Paragraph type="secondary" style={{ marginBottom: 12 }}>
          {intl.formatMessage({ id: "aiAssistant.knowledge.expandHint" })}
        </Paragraph>
        {!isSearchMode && listTruncated ? (
          <Alert
            style={{ marginBottom: 12 }}
            type="warning"
            showIcon
            title={intl.formatMessage({ id: "aiAssistant.knowledge.listTruncated" })}
          />
        ) : null}
        {tableData.length === 0 && !loading && !searching ? (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={intl.formatMessage({ id: "aiAssistant.knowledge.empty" })}
          />
        ) : (
          <Table
            size="small"
            rowKey="key"
            loading={loading || searching}
            pagination={pagination}
            dataSource={tableData}
            columns={columns}
            scroll={{ x: 720 }}
            expandable={{
              expandedRowKeys: expandedKeys,
              onExpandedRowsChange: (keys) => setExpandedKeys(keys),
              onExpand: (expanded, record) => {
                if (expanded) void ensurePreview(record.source);
              },
              expandedRowRender: (record) => (
                <KnowledgeMdPreview source={record.source} state={previews[record.source]} />
              ),
              rowExpandable: (record) => !!record.source,
            }}
          />
        )}
      </Card>
    </Space>
  );
}
