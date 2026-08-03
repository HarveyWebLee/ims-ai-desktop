/**
 * Agent API Client
 */
import { getAuthHeaders } from "@ims/desktop-api";
import type { AgentApiResponse, AgentModelId, HitlPayload } from "@ims/shared-types";
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
    model_id: AgentModelId;
    metadata?: { current_path?: string };
    /** 近期用户消息（不含本条），用于多轮时间上下文 */
    recent_user_messages?: string[];
  },
  handlers: AgentSseHandler,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`${AGENT_BASE}/chat`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify(params),
    signal,
  });
  await consumeSseResponse(res, handlers);
}

/** HITL resume（SSE 继续输出） */
export async function resumeStream(
  params: {
    thread_id: string;
    /** 与产生 interrupt 的 chat mid 一致 */
    mid?: string;
    model_id: AgentModelId;
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

/** 声纹用户（ERes2Net；换 model_id 后 needs_reenroll=true） */
export interface VoiceprintProfile {
  id: string;
  display_name: string;
  description?: string;
  sample_count: number;
  enrolled: boolean;
  model_id?: string;
  needs_reenroll?: boolean;
  created_at?: string;
  updated_at?: string;
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
  body: { display_name?: string; description?: string },
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

export async function enrollVoiceprint(
  id: string,
  pcm: Blob,
  options?: { sampleRate?: number; filename?: string },
): Promise<VoiceprintProfile> {
  const form = new FormData();
  form.append("file", pcm, options?.filename ?? "enroll.pcm");
  form.append("sample_rate", String(options?.sampleRate ?? 16000));
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
  options?: { sampleRate?: number; filename?: string },
): Promise<{
  matched: boolean;
  score: number;
  threshold: number;
  display_name?: string;
  skipped?: boolean;
}> {
  const form = new FormData();
  form.append("profile_id", profileId);
  form.append("file", pcm, options?.filename ?? "verify.pcm");
  form.append("sample_rate", String(options?.sampleRate ?? 16000));
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
