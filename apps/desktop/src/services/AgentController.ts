/**
 * Agent API Client
 */
import { getAuthHeaders } from "@ims/desktop-api";
import type { AgentModelSelectionId } from "@ims/agent-core/model-catalog";
import type { AgentApiResponse, AgentModelId, AgentRunMode, HitlPayload } from "@ims/shared-types";
import type { AgentSseHandler, AiSession } from "@/components/AiAssistant/types";
import type { ThreadHistoryMessage } from "@/components/AiAssistant/utils/mapHistoryMessages";
import { parseSseChunk } from "@/components/AiAssistant/utils/sseParser";

const AGENT_BASE = "/api/agent";

/** BPMN 线程快照（与后端 agent_thread_bpmn 对齐） */
export interface BpmnThreadSnapshot {
  steps?: import("@ims/shared-types").PlanStep[];
  graph?: import("@ims/shared-types").PlanGraph;
  flow_document?: Record<string, unknown>;
  updated_at?: string | null;
}

/** BPMN 画布校验结果 */
export interface BpmnValidateResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
}

async function parseJsonResponse<T>(res: Response): Promise<T> {
  const raw = await res.text();
  let json: AgentApiResponse<T>;
  try {
    json = JSON.parse(raw) as AgentApiResponse<T>;
  } catch {
    // 常见于 Agent 未启动时 webpack 代理返回纯文本：
    // "Error occurred while trying to proxy: ..."
    const snippet = raw.replace(/\s+/g, " ").trim().slice(0, 160);
    if (
      /Error occurred while trying to proxy/i.test(snippet) ||
      res.status === 502 ||
      res.status === 503 ||
      res.status === 504
    ) {
      throw new Error("Agent 服务不可用（请确认 platform-agent-service 已在 :8008 启动）");
    }
    throw new Error(
      snippet
        ? `响应非 JSON（HTTP ${res.status}）：${snippet}`
        : `请求失败（HTTP ${res.status || "网络错误"}）`,
    );
  }
  if (json.code !== 0) {
    const detail = typeof json.data === "string" ? json.data : json.message || "请求失败";
    throw new Error(detail);
  }
  return json.data as T;
}

/** 消费 SSE 响应流 */
async function consumeSseResponse(res: Response, handlers: AgentSseHandler): Promise<void> {
  const contentType = res.headers.get("content-type") ?? "";
  if (!contentType.includes("text/event-stream")) {
    let json: AgentApiResponse = { code: res.status, message: res.statusText, data: null };
    try {
      json = (await res.json()) as AgentApiResponse;
    } catch {
      // 非 JSON 错误体
    }
    handlers.onError?.(
      json.code ?? res.status,
      json.message || res.statusText || "请求失败",
      json.data,
    );
    return;
  }

  if (!res.ok) {
    handlers.onError?.(res.status, res.statusText || "Agent 请求失败");
    return;
  }

  const reader = res.body?.getReader();
  if (!reader) {
    handlers.onError?.(500, "无法读取响应流");
    return;
  }

  // 跟踪是否收到有效内容与终端事件，避免 0 事件时误触发 onDone
  let gotContentEvent = false;
  let gotTerminalEvent = false;
  const pendingTools = new Set<string>();
  const wrappedHandlers: AgentSseHandler = {
    ...handlers,
    onTextDelta: (delta) => {
      gotContentEvent = true;
      handlers.onTextDelta?.(delta);
    },
    onToolStart: (tool, args, meta) => {
      gotContentEvent = true;
      if (tool) pendingTools.add(tool);
      handlers.onToolStart?.(tool, args, meta);
    },
    onToolEnd: (tool, result, meta) => {
      gotContentEvent = true;
      if (tool) pendingTools.delete(tool);
      handlers.onToolEnd?.(tool, result, meta);
    },
    onInterrupt: (payload) => {
      gotContentEvent = true;
      handlers.onInterrupt?.(payload);
    },
    onClientAction: async (action) => {
      gotContentEvent = true;
      await handlers.onClientAction?.(action);
    },
    onPlan: (payload) => {
      gotContentEvent = true;
      handlers.onPlan?.(payload);
    },
    onPlanUpdate: (payload) => {
      gotContentEvent = true;
      handlers.onPlanUpdate?.(payload);
    },
    onReplan: (payload) => {
      gotContentEvent = true;
      handlers.onReplan?.(payload);
    },
    onTrace: (event) => {
      gotContentEvent = true;
      handlers.onTrace?.(event);
    },
    onDone: (threadId) => {
      gotTerminalEvent = true;
      handlers.onDone?.(threadId);
    },
    onError: (code, msg, data) => {
      gotTerminalEvent = true;
      handlers.onError?.(code, msg, data);
    },
  };

  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      buffer = await parseSseChunk(buffer, wrappedHandlers);
    }

    if (buffer.trim()) {
      await parseSseChunk(`${buffer}\n\n`, wrappedHandlers);
    }
  } catch (err) {
    // fetch 被 abort 时不当作模型失败
    if ((err as Error).name === "AbortError") {
      return;
    }
    if (!gotTerminalEvent) {
      handlers.onError?.(500, (err as Error).message || "读取 Agent 响应流失败");
    }
    return;
  }

  if (gotTerminalEvent) {
    return;
  }

  if (!gotContentEvent) {
    handlers.onError?.(50002, "连接中断，未收到助手回复。请重试，或切换其他模型。");
    return;
  }

  // 有内容但流异常结束（含 tool_start 未配对 tool_end）：不假装成功
  if (pendingTools.size > 0) {
    handlers.onError?.(50002, "连接中断，工具执行结果可能不完整。请重试。");
    return;
  }

  // 有完整内容但后端未 emit done：补发 done 结束 loading
  handlers.onDone?.("");
}

export async function getModels(): Promise<{
  defaultModelId: AgentModelId;
  models: { modelId: AgentModelId; label: string; provider: string }[];
}> {
  const res = await fetch(`${AGENT_BASE}/models`, {
    headers: getAuthHeaders(),
  });
  return parseJsonResponse(res);
}

export async function getSessions(): Promise<{ sessions: AiSession[] }> {
  const res = await fetch(`${AGENT_BASE}/sessions`, {
    headers: getAuthHeaders(),
  });
  return parseJsonResponse(res);
}

export async function deleteSession(threadId: string): Promise<{ thread_id: string }> {
  const res = await fetch(`${AGENT_BASE}/sessions/${encodeURIComponent(threadId)}`, {
    method: "DELETE",
    headers: getAuthHeaders(),
  });
  return parseJsonResponse(res);
}

export async function getThreadState(threadId: string): Promise<{
  thread_id: string;
  messages: ThreadHistoryMessage[];
  pending_interrupt?: HitlPayload | null;
  bpmn_snapshot?: BpmnThreadSnapshot | null;
}> {
  const res = await fetch(`${AGENT_BASE}/threads/${threadId}/state`, {
    headers: getAuthHeaders(),
  });
  return parseJsonResponse(res);
}

export async function getThreadTrace(
  threadId: string,
  runId?: string,
): Promise<{
  thread_id: string;
  runs?: import("@ims/shared-types").AgentTraceRun[];
  run?: import("@ims/shared-types").AgentTraceRun;
}> {
  const qs = runId ? `?run_id=${encodeURIComponent(runId)}` : "";
  const res = await fetch(`${AGENT_BASE}/threads/${threadId}/trace${qs}`, {
    headers: getAuthHeaders(),
  });
  return parseJsonResponse(res);
}

/** 审计日志条目（只读） */
export interface AgentAuditLogEntry {
  id?: number | null;
  thread_id: string;
  run_id?: string | null;
  user_id: string;
  event_type: string;
  tool_name?: string | null;
  payload_summary?: Record<string, unknown>;
  created_at?: string | null;
}

/** 按 thread_id 查询审计日志（可选 run_id / event_type 筛选） */
export async function getThreadAudit(
  threadId: string,
  options?: {
    limit?: number;
    runId?: string;
    eventType?: string;
  },
): Promise<{ thread_id: string; logs: AgentAuditLogEntry[] }> {
  const qs = new URLSearchParams({
    thread_id: threadId,
    limit: String(options?.limit ?? 100),
  });
  if (options?.runId) {
    qs.set("run_id", options.runId);
  }
  if (options?.eventType) {
    qs.set("event_type", options.eventType);
  }
  const res = await fetch(`${AGENT_BASE}/audit?${qs.toString()}`, {
    headers: getAuthHeaders(),
  });
  return parseJsonResponse(res);
}

/** P2-2：上报 client_action 执行回执（写入 Agent 审计；失败不抛，由调用方吞掉） */
export async function reportClientActionResult(
  threadId: string,
  result: import("@ims/shared-types").ClientActionResult & { run_id?: string },
): Promise<{ thread_id: string; action: string; ok: boolean; skipped?: boolean }> {
  const res = await fetch(
    `${AGENT_BASE}/threads/${encodeURIComponent(threadId)}/client-action-result`,
    {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify(result),
    },
  );
  return parseJsonResponse(res);
}

/** BPMN：画布 JSON ↔ Plan 步骤互转 */
export async function convertBpmn(params: {
  direction: "steps_to_document" | "document_to_steps";
  steps?: import("@ims/shared-types").PlanStep[];
  flow_document?: Record<string, unknown>;
  previous_steps?: import("@ims/shared-types").PlanStep[];
}): Promise<{
  steps?: import("@ims/shared-types").PlanStep[];
  flow_document?: Record<string, unknown>;
  active_step_count?: number;
}> {
  const res = await fetch(`${AGENT_BASE}/bpmn/convert`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify(params),
  });
  return parseJsonResponse(res);
}

/** BPMN：校验画布结构 */
export async function validateBpmn(
  flowDocument: Record<string, unknown>,
): Promise<BpmnValidateResult> {
  const res = await fetch(`${AGENT_BASE}/bpmn/validate`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({ flow_document: flowDocument }),
  });
  return parseJsonResponse(res);
}

/** 读取线程 BPMN 快照 */
export async function getThreadBpmn(threadId: string): Promise<{
  thread_id: string;
  snapshot: BpmnThreadSnapshot | null;
}> {
  const res = await fetch(`${AGENT_BASE}/threads/${threadId}/bpmn`, {
    headers: getAuthHeaders(),
  });
  return parseJsonResponse(res);
}

/** 保存线程 BPMN 编排草稿 */
export async function saveThreadBpmn(
  threadId: string,
  payload: {
    flow_document?: Record<string, unknown>;
    steps?: import("@ims/shared-types").PlanStep[];
    graph?: import("@ims/shared-types").PlanGraph;
  },
): Promise<{ thread_id: string; snapshot: BpmnThreadSnapshot }> {
  const res = await fetch(`${AGENT_BASE}/threads/${threadId}/bpmn`, {
    method: "PUT",
    headers: getAuthHeaders(),
    body: JSON.stringify(payload),
  });
  return parseJsonResponse(res);
}

export async function chatStream(
  params: {
    thread_id: string;
    /** 用户本轮需求 ID；与助手气泡 / SSE mid 对齐 */
    mid: string;
    message: string;
    model_id: AgentModelSelectionId;
    /** 会话运行模式：readonly | confirm | autonomous */
    run_mode?: AgentRunMode;
    /** 显式先计划后执行 */
    plan_first?: boolean;
    metadata?: { current_path?: string };
    /** 近期用户消息（不含本条），用于多轮时间上下文 */
    recent_user_messages?: string[];
  },
  handlers: AgentSseHandler,
  signal?: AbortSignal,
  /** 请求已被接受（headers 返回；此时后端已 upsert 会话） */
  onRequestAccepted?: () => void,
): Promise<void> {
  const res = await fetch(`${AGENT_BASE}/chat`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify(params),
    signal,
  });
  if (res.ok) {
    onRequestAccepted?.();
  }
  await consumeSseResponse(res, handlers);
}

/** HITL resume（SSE 继续输出） */
export async function resumeStream(
  params: {
    thread_id: string;
    /** 与产生 interrupt 的 chat mid 一致 */
    mid?: string;
    model_id: AgentModelSelectionId;
    /** 会话运行模式；须与 chat 一致 */
    run_mode?: AgentRunMode;
    /** 与 chat 对称透传 */
    plan_first?: boolean;
    decisions: { type: string; args?: Record<string, unknown> }[];
  },
  handlers: AgentSseHandler,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`${AGENT_BASE}/resume`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify(params),
    signal,
  });
  await consumeSseResponse(res, handlers);
}

export async function transcribeAudio(
  file: Blob,
  options?: { modelId?: AgentModelId; filename?: string },
): Promise<{
  text: string;
  raw?: string;
  stage?: string;
  changed?: boolean;
  segments?: Array<{
    seq: number;
    raw: string;
    text: string;
    stage?: string;
    changed?: boolean;
    status?: string;
  }>;
}> {
  const form = new FormData();
  form.append("file", file, options?.filename ?? "audio.webm");
  if (options?.modelId) {
    form.append("model_id", options.modelId);
  }
  const headers: Record<string, string> = {};
  const authHeaders = getAuthHeaders();
  if (authHeaders.Authorization) headers.Authorization = authHeaders.Authorization;

  const res = await fetch(`${AGENT_BASE}/transcribe`, {
    method: "POST",
    headers,
    body: form,
  });
  return parseJsonResponse(res);
}

/** 流式转写：创建并行分片会话 */
export async function transcribeStreamStart(options?: {
  modelId?: AgentModelId;
}): Promise<{ session_id: string; workers: number }> {
  const form = new FormData();
  if (options?.modelId) {
    form.append("model_id", options.modelId);
  }
  const headers: Record<string, string> = {};
  const authHeaders = getAuthHeaders();
  if (authHeaders.Authorization) headers.Authorization = authHeaders.Authorization;
  const res = await fetch(`${AGENT_BASE}/transcribe/stream/start`, {
    method: "POST",
    headers,
    body: form,
  });
  return parseJsonResponse(res);
}

/** 流式转写：提交分片（服务端并行处理，立即返回） */
export async function transcribeStreamChunk(
  file: Blob,
  options: {
    sessionId: string;
    seq: number;
    modelId?: AgentModelId;
    filename?: string;
  },
): Promise<{
  accepted: boolean;
  seq: number;
  interim_text?: string;
  interim_seq?: number | null;
  interim_stage?: string | null;
  pending?: number;
}> {
  const form = new FormData();
  form.append("file", file, options.filename ?? `chunk-${options.seq}.webm`);
  form.append("session_id", options.sessionId);
  form.append("seq", String(options.seq));
  if (options.modelId) {
    form.append("model_id", options.modelId);
  }
  const headers: Record<string, string> = {};
  const authHeaders = getAuthHeaders();
  if (authHeaders.Authorization) headers.Authorization = authHeaders.Authorization;
  const res = await fetch(`${AGENT_BASE}/transcribe/stream/chunk`, {
    method: "POST",
    headers,
    body: form,
  });
  return parseJsonResponse(res);
}

/** 流式转写：收敛并返回最终文本（含纠错详情） */
export async function transcribeStreamFinish(sessionId: string): Promise<{
  text: string;
  raw?: string;
  stage?: string;
  changed?: boolean;
  source?: string;
  segments?: Array<{
    seq: number;
    raw: string;
    text: string;
    stage?: string;
    changed?: boolean;
    status?: string;
  }>;
}> {
  const form = new FormData();
  form.append("session_id", sessionId);
  const headers: Record<string, string> = {};
  const authHeaders = getAuthHeaders();
  if (authHeaders.Authorization) headers.Authorization = authHeaders.Authorization;
  const res = await fetch(`${AGENT_BASE}/transcribe/stream/finish`, {
    method: "POST",
    headers,
    body: form,
  });
  return parseJsonResponse(res);
}

/** 实体表 → 向量库同步结果 */
export interface EntitySyncResult {
  ok?: boolean;
  skipped?: boolean;
  reason?: string | null;
  message?: string;
  missing_tables?: string[];
  tables?: Array<{
    table: string;
    rows_read: number;
    upserted: number;
    ok: boolean;
    error?: string | null;
    truncated?: boolean;
  }>;
  upserted?: number;
  config?: string;
  collection?: string;
}

/** 触发达梦业务表只读同步到 Qdrant（配置见 ENTITY_SYNC_TABLES） */
export async function triggerEntitySync(options?: { tables?: string }): Promise<EntitySyncResult> {
  const res = await fetch(`${AGENT_BASE}/entity-sync`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({
      tables: options?.tables ?? null,
    }),
  });
  return parseJsonResponse(res);
}

/** 实体同步服务端可观测状态（进程内最近一次） */
export interface EntitySyncStatus {
  in_progress: boolean;
  at: string | null;
  result: EntitySyncResult | null;
}

export async function getEntitySyncStatus(): Promise<EntitySyncStatus> {
  const res = await fetch(`${AGENT_BASE}/entity-sync/status`, {
    headers: getAuthHeaders(),
  });
  return parseJsonResponse(res);
}

/** 实体术语库（platform_entities：设备/变量） */
export interface EntityStats {
  enabled: boolean;
  ok: boolean;
  collection: string;
  points: number;
  sync_tables?: string;
  in_progress?: boolean;
  message?: string;
  probe?: Record<string, unknown>;
}

export interface EntitySearchHit {
  score: number;
  entity_type: string;
  entity_key: string;
  source: string;
  text: string;
  text_preview: string;
  device_code?: string | null;
  device_name?: string | null;
  var_name?: string | null;
  show_name?: string | null;
  table?: string | null;
}

export async function getEntityStats(): Promise<EntityStats> {
  const res = await fetch(`${AGENT_BASE}/entities/stats`, {
    headers: getAuthHeaders(),
  });
  return parseJsonResponse(res);
}

export async function searchEntities(params: {
  query: string;
  limit?: number;
  entityTypes?: string[];
}): Promise<{ query: string; items: EntitySearchHit[]; collection: string }> {
  const res = await fetch(`${AGENT_BASE}/entities/search`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({
      query: params.query,
      limit: params.limit ?? 8,
      entity_types: params.entityTypes ?? null,
    }),
  });
  return parseJsonResponse(res);
}

/** 文档知识库运营（platform_knowledge） */
export interface KnowledgeStats {
  enabled: boolean;
  ok: boolean;
  collection: string;
  points: number;
  message?: string;
  probe?: Record<string, unknown>;
  upload_dir?: string;
}

export interface KnowledgePointItem {
  id: string;
  score: number;
  text_preview: string;
  source: string;
  filename: string;
  chunk_index?: number | null;
  media_kind?: string | null;
}

export interface KnowledgeDocumentItem {
  source: string;
  filename: string;
  chunk_count: number;
}

export interface KnowledgeDocumentsPage {
  items: KnowledgeDocumentItem[];
  total: number;
  page: number;
  page_size: number;
  scanned_points?: number;
  truncated?: boolean;
  collection: string;
}

export async function getKnowledgeStats(): Promise<KnowledgeStats> {
  const res = await fetch(`${AGENT_BASE}/knowledge/stats`, {
    headers: getAuthHeaders(),
  });
  return parseJsonResponse(res);
}

export async function listKnowledgePoints(options?: {
  limit?: number;
  sourceContains?: string;
}): Promise<{ items: KnowledgePointItem[]; next_offset: string | null; collection: string }> {
  const qs = new URLSearchParams({
    limit: String(options?.limit ?? 20),
  });
  if (options?.sourceContains?.trim()) {
    qs.set("source_contains", options.sourceContains.trim());
  }
  const res = await fetch(`${AGENT_BASE}/knowledge/points?${qs.toString()}`, {
    headers: getAuthHeaders(),
  });
  return parseJsonResponse(res);
}

export async function listKnowledgeDocuments(options?: {
  page?: number;
  pageSize?: number;
  sourceContains?: string;
}): Promise<KnowledgeDocumentsPage> {
  const qs = new URLSearchParams({
    page: String(options?.page ?? 1),
    page_size: String(options?.pageSize ?? 20),
  });
  if (options?.sourceContains?.trim()) {
    qs.set("source_contains", options.sourceContains.trim());
  }
  const res = await fetch(`${AGENT_BASE}/knowledge/documents?${qs.toString()}`, {
    headers: getAuthHeaders(),
  });
  return parseJsonResponse(res);
}

export async function searchKnowledge(params: {
  query: string;
  limit?: number;
}): Promise<{ query: string; items: KnowledgePointItem[] }> {
  const res = await fetch(`${AGENT_BASE}/knowledge/search`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({
      query: params.query,
      limit: params.limit ?? 5,
    }),
  });
  return parseJsonResponse(res);
}

export async function ingestKnowledgeFile(
  file: File,
): Promise<{ source: string; filename: string; chunks: number; deleted_before: number }> {
  const form = new FormData();
  form.append("file", file, file.name);
  const headers: Record<string, string> = {};
  const authHeaders = getAuthHeaders();
  if (authHeaders.Authorization) headers.Authorization = authHeaders.Authorization;
  const res = await fetch(`${AGENT_BASE}/knowledge/ingest`, {
    method: "POST",
    headers,
    body: form,
  });
  return parseJsonResponse(res);
}

export type KnowledgeIngestJobStatus = "receiving" | "running" | "completed" | "interrupted";

export interface KnowledgeIngestJobItem {
  filename: string;
  path?: string;
  status: "pending" | "running" | "ok" | "error" | "skipped";
  source?: string | null;
  chunks?: number;
  deleted_before?: number;
  error?: string | null;
  ok?: boolean;
}

export interface KnowledgeIngestJob {
  job_id: string;
  user_id: string;
  status: KnowledgeIngestJobStatus;
  in_progress: boolean;
  created_at: string;
  updated_at: string;
  total: number;
  done: number;
  succeeded: number;
  failed: number;
  chunks_total: number;
  deleted_total: number;
  percent: number;
  current_filename?: string | null;
  message: string;
  items: KnowledgeIngestJobItem[];
}

export interface KnowledgeIngestJobStatusPayload {
  job: KnowledgeIngestJob | null;
  in_progress: boolean;
}

/** 与后端 APPEND_CHUNK_MAX_FILES 对齐 */
export const KNOWLEDGE_INGEST_UPLOAD_CHUNK = 30;

export async function createKnowledgeIngestJob(): Promise<KnowledgeIngestJob> {
  const res = await fetch(`${AGENT_BASE}/knowledge/ingest-jobs`, {
    method: "POST",
    headers: getAuthHeaders(),
  });
  return parseJsonResponse(res);
}

export async function appendKnowledgeIngestJobFiles(
  jobId: string,
  files: File[],
): Promise<KnowledgeIngestJob> {
  const form = new FormData();
  for (const file of files) {
    form.append("files", file, file.name);
  }
  const headers: Record<string, string> = {};
  const authHeaders = getAuthHeaders();
  if (authHeaders.Authorization) headers.Authorization = authHeaders.Authorization;
  const res = await fetch(
    `${AGENT_BASE}/knowledge/ingest-jobs/${encodeURIComponent(jobId)}/files`,
    {
      method: "POST",
      headers,
      body: form,
    },
  );
  return parseJsonResponse(res);
}

export async function commitKnowledgeIngestJob(jobId: string): Promise<KnowledgeIngestJob> {
  const res = await fetch(
    `${AGENT_BASE}/knowledge/ingest-jobs/${encodeURIComponent(jobId)}/commit`,
    {
      method: "POST",
      headers: getAuthHeaders(),
    },
  );
  return parseJsonResponse(res);
}

export async function getKnowledgeIngestJobActive(): Promise<KnowledgeIngestJobStatusPayload> {
  const res = await fetch(`${AGENT_BASE}/knowledge/ingest-jobs/active`, {
    headers: getAuthHeaders(),
  });
  return parseJsonResponse(res);
}

/**
 * 无数量上限：客户端分片上传入队，服务端后台逐文件入库。
 * 返回 commit 后的任务快照（随后需轮询 active 直到完成）。
 */
export async function enqueueKnowledgeIngestFiles(files: File[]): Promise<KnowledgeIngestJob> {
  if (files.length === 0) {
    throw new Error("未选择任何文件");
  }
  const created = await createKnowledgeIngestJob();
  const chunkSize = KNOWLEDGE_INGEST_UPLOAD_CHUNK;
  for (let i = 0; i < files.length; i += chunkSize) {
    const slice = files.slice(i, i + chunkSize);
    await appendKnowledgeIngestJobFiles(created.job_id, slice);
  }
  return commitKnowledgeIngestJob(created.job_id);
}

export async function replaceKnowledgeFile(
  source: string,
  file: File,
): Promise<{ source: string; filename: string; chunks: number; deleted_before: number }> {
  const form = new FormData();
  form.append("file", file, file.name);
  form.append("source", source);
  const headers: Record<string, string> = {};
  const authHeaders = getAuthHeaders();
  if (authHeaders.Authorization) headers.Authorization = authHeaders.Authorization;
  const res = await fetch(`${AGENT_BASE}/knowledge/replace`, {
    method: "POST",
    headers,
    body: form,
  });
  return parseJsonResponse(res);
}

export async function exportKnowledgeBySource(
  source: string,
): Promise<{ source: string; filename: string; content: string; from: string; chunks?: number }> {
  const res = await fetch(`${AGENT_BASE}/knowledge/export`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({ source }),
  });
  return parseJsonResponse(res);
}

export async function deleteKnowledgeBySource(
  source: string,
): Promise<{ source: string; deleted: number }> {
  const res = await fetch(`${AGENT_BASE}/knowledge/by-source`, {
    method: "DELETE",
    headers: getAuthHeaders(),
    body: JSON.stringify({ source }),
  });
  return parseJsonResponse(res);
}

/** 清空文档知识 collection（须二次确认；换 Embedding 后重建） */
export async function dropKnowledgeCollection(): Promise<{
  dropped: boolean;
  collection: string;
  existed: boolean;
}> {
  const res = await fetch(`${AGENT_BASE}/knowledge/drop-collection`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({ confirm: true }),
  });
  return parseJsonResponse(res);
}

/** 清空实体术语 collection（须二次确认；换 Embedding 后重建） */
export async function dropEntityCollection(): Promise<{
  dropped: boolean;
  collection: string;
  existed: boolean;
}> {
  const res = await fetch(`${AGENT_BASE}/entities/drop-collection`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({ confirm: true }),
  });
  return parseJsonResponse(res);
}

/** 声纹用户（ERes2Net-Large 多模板；≥enroll_min 段后 enrolled） */
export interface VoiceprintProfile {
  id: string;
  display_name: string;
  description?: string;
  sample_count: number;
  status?: "pending" | "enrolled" | "disabled";
  enrolled: boolean;
  model_id?: string;
  enroll_min?: number;
  created_at?: string;
  updated_at?: string;
}

export interface VoiceprintSample {
  id: string;
  profile_id: string;
  model_id: string;
  duration_ms: number;
  device_hint?: string;
  env_hint?: string;
  created_at?: string;
}

export interface VoiceprintMatchResult {
  matched: boolean;
  decision?: "accept" | "unknown" | "reject";
  score: number;
  score_raw?: number;
  threshold: number;
  profile_id?: string | null;
  display_name?: string;
  model_id?: string;
  skipped?: boolean;
  reason?: string;
  latency_ms?: {
    preprocess: number;
    embedding: number;
    search: number;
    total: number;
  };
}

export async function getVoiceprintConfig(): Promise<{
  enabled: boolean;
  enroll_min_samples: number;
  enroll_max_samples: number;
}> {
  const res = await fetch(`${AGENT_BASE}/voiceprints/config`, {
    method: "GET",
    headers: getAuthHeaders(),
  });
  return parseJsonResponse(res);
}

export async function listVoiceprints(): Promise<{
  items: VoiceprintProfile[];
}> {
  const res = await fetch(`${AGENT_BASE}/voiceprints`, {
    method: "GET",
    headers: getAuthHeaders(),
  });
  return parseJsonResponse(res);
}

export async function createVoiceprint(body: {
  display_name: string;
  description?: string;
}): Promise<VoiceprintProfile> {
  const res = await fetch(`${AGENT_BASE}/voiceprints`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify(body),
  });
  return parseJsonResponse(res);
}

export async function updateVoiceprint(
  id: string,
  body: {
    display_name?: string;
    description?: string;
    status?: "pending" | "enrolled" | "disabled";
  },
): Promise<VoiceprintProfile> {
  const res = await fetch(`${AGENT_BASE}/voiceprints/${encodeURIComponent(id)}`, {
    method: "PATCH",
    headers: getAuthHeaders(),
    body: JSON.stringify(body),
  });
  return parseJsonResponse(res);
}

export async function deleteVoiceprint(id: string): Promise<{ deleted: boolean }> {
  const res = await fetch(`${AGENT_BASE}/voiceprints/${encodeURIComponent(id)}`, {
    method: "DELETE",
    headers: getAuthHeaders(),
  });
  return parseJsonResponse(res);
}

export async function listVoiceprintSamples(id: string): Promise<{ items: VoiceprintSample[] }> {
  const res = await fetch(`${AGENT_BASE}/voiceprints/${encodeURIComponent(id)}/samples`, {
    method: "GET",
    headers: getAuthHeaders(),
  });
  return parseJsonResponse(res);
}

export async function deleteVoiceprintSample(
  profileId: string,
  sampleId: string,
): Promise<VoiceprintProfile> {
  const res = await fetch(
    `${AGENT_BASE}/voiceprints/${encodeURIComponent(profileId)}/samples/${encodeURIComponent(sampleId)}`,
    {
      method: "DELETE",
      headers: getAuthHeaders(),
    },
  );
  return parseJsonResponse(res);
}

export async function enrollVoiceprint(
  id: string,
  pcm: Blob,
  options?: {
    sampleRate?: number;
    filename?: string;
    deviceHint?: string;
    envHint?: string;
  },
): Promise<VoiceprintProfile> {
  const form = new FormData();
  form.append("file", pcm, options?.filename ?? "enroll.pcm");
  form.append("sample_rate", String(options?.sampleRate ?? 16000));
  if (options?.deviceHint) form.append("device_hint", options.deviceHint);
  if (options?.envHint) form.append("env_hint", options.envHint);
  const headers: Record<string, string> = {};
  const authHeaders = getAuthHeaders();
  if (authHeaders.Authorization) headers.Authorization = authHeaders.Authorization;
  const res = await fetch(`${AGENT_BASE}/voiceprints/${encodeURIComponent(id)}/enroll`, {
    method: "POST",
    headers,
    body: form,
  });
  return parseJsonResponse(res);
}

export async function verifyVoiceprint(
  profileId: string,
  pcm: Blob,
  options?: { sampleRate?: number; filename?: string; scene?: string },
): Promise<VoiceprintMatchResult> {
  const form = new FormData();
  form.append("profile_id", profileId);
  form.append("file", pcm, options?.filename ?? "verify.pcm");
  form.append("sample_rate", String(options?.sampleRate ?? 16000));
  form.append("scene", options?.scene ?? "assistant_gate");
  const headers: Record<string, string> = {};
  const authHeaders = getAuthHeaders();
  if (authHeaders.Authorization) headers.Authorization = authHeaders.Authorization;
  const res = await fetch(`${AGENT_BASE}/voiceprints/verify`, {
    method: "POST",
    headers,
    body: form,
  });
  return parseJsonResponse(res);
}

export async function identifyVoiceprint(
  pcm: Blob,
  options?: { sampleRate?: number; filename?: string; scene?: string; topK?: number },
): Promise<VoiceprintMatchResult> {
  const form = new FormData();
  form.append("file", pcm, options?.filename ?? "identify.pcm");
  form.append("sample_rate", String(options?.sampleRate ?? 16000));
  form.append("scene", options?.scene ?? "identify_open");
  if (options?.topK != null) form.append("top_k", String(options.topK));
  const headers: Record<string, string> = {};
  const authHeaders = getAuthHeaders();
  if (authHeaders.Authorization) headers.Authorization = authHeaders.Authorization;
  const res = await fetch(`${AGENT_BASE}/voiceprints/identify`, {
    method: "POST",
    headers,
    body: form,
  });
  return parseJsonResponse(res);
}
