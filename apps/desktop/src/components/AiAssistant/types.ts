/**
 * AI 智能化交互 — 类型定义
 * 与 @ims/shared-types 对齐，前端消息块扩展
 */
import type {
  AgentModelId,
  ClientAction,
  HitlPayload,
  PlanGraph,
  PlanStep,
  ToolResult,
  TraceEvent,
  TraceGraph,
} from "@ims/shared-types";
import type { FlowDocumentJSON } from "@/components/BpmnFlowgram";

export type {
  AgentModelId,
  ClientAction,
  HitlPayload,
  PlanStep,
  ToolResult,
  TraceEvent,
  TraceGraph,
};

/** 会话摘要 */
export interface AiSession {
  thread_id: string;
  title: string;
  updated_at: string;
  created_at?: string;
}

/** 消息角色 */
export type AiMessageRole = "user" | "assistant" | "system";

/** AI 消息块类型 */
export type AiMessageBlock =
  | { type: "text"; content: string }
  | { type: "thinking"; content: string }
  | {
      type: "tool_call";
      tool: string;
      args: Record<string, unknown>;
      status: "pending" | "running" | "done" | "error" | "awaiting_hitl" | "cancelled";
      result?: string;
      /** 与 SSE / LangChain tool_calls[].id 对齐，同 mid 内禁止仅按工具名猜 */
      toolCallId?: string;
      /** Re-plan 后的重试轮次（来自 SSE tool_start.retry） */
      retry?: boolean;
      attempt?: number;
    }
  | {
      type: "interrupt";
      payload: HitlPayload;
      /** 终态：拒绝 / 中止 / 被新消息顶替；有值则不可再交互 */
      resolution?: "rejected" | "aborted" | "superseded";
    }
  | {
      type: "client_action";
      action: ClientAction;
      status: "pending" | "done" | "error";
    }
  | { type: "artifact"; kind: "file" | "table" | "link"; data: unknown }
  | {
      type: "plan";
      steps: { id: string; label: string; status: string }[];
    };
export interface AlarmQueryQueryContext {
  startTime: string;
  endTime: string;
  deviceCodes?: string[];
  variableNames?: string[];
  alarmCategoryId?: string[];
  alarmRankId?: string[];
  status?: string[];
  /** 翻页 API：未处理列表用 getAlarmUnprocessList，否则 getAlarmList */
  listApi?: "getAlarmList" | "getAlarmUnprocessList";
}

export interface AlarmQueryWorkspace {
  kind: "alarm_query";
  ok: boolean;
  total: number;
  items: Array<{
    id?: string;
    deviceName?: string;
    deviceCode?: string;
    /** 平台 deviceVarName；与 variableName 同义 */
    deviceVarName?: string | null;
    variableName?: string | null;
    alarmValue?: string | null;
    startTime?: string;
    endTime?: string | null;
    status?: number | string;
    statusName?: string;
    alarmRankId?: number | string;
    alarmRankName?: string;
    alarmCategoryId?: number | string;
    alarmCategoryName?: string;
    eventName?: string;
    regionName?: string | null;
    subSystemName?: string | null;
    confirmPerson?: string | null;
    confirmTime?: string | null;
    processPerson?: string | null;
    processTime?: string | null;
    handleMethod?: string | null;
  }>;
  summary?: string;
  timeRange?: { start?: string; end?: string; label?: string };
  /** 当前页（从 1 开始） */
  page?: number;
  pageSize?: number;
  /** 翻页时复用平台 getAlarmList 请求体 */
  queryContext?: AlarmQueryQueryContext;
}

/** get_device_detail 返回的脱敏设备详情 */
export interface DeviceDetailRecord {
  id?: string | number;
  deviceCode?: string;
  deviceName?: string;
  onlineStatus?: number;
  onlineStatusLabel?: string;
  /** 平台启用状态码：0 停用 / 1 启用（字段名历史遗留） */
  deviceStatus?: string | number;
  /** 启用状态中文标签（后端映射） */
  deviceStatusLabel?: string;
  enableStatus?: string | number;
  enableStatusLabel?: string;
  regionName?: string;
  subSystemName?: string;
  deviceGroupName?: string;
  ipAddress?: string;
  port?: string | number;
  manufacturer?: string;
  model?: string;
  location?: string;
  collectServerName?: string;
  commDeviceName?: string;
  firstUseTime?: string;
}

export interface DeviceDetailWorkspace {
  kind: "device_detail";
  ok: boolean;
  device: DeviceDetailRecord;
  summary?: string;
}

/** send_device_cmd 结构化结果（与模型无关，由 tool_end 驱动） */
export interface DeviceCommandWorkspace {
  kind: "device_command";
  ok: boolean;
  summary: string;
  deviceCode?: string;
  deviceName?: string;
  variableName?: string;
  variableValue?: string;
  taskNo?: string;
  autoRetry?: { from: string; to: string };
  userCancelled?: boolean;
}

/** query_devices 列表项（与 MCP DeviceBrief 对齐） */
export interface DeviceListItem {
  deviceCode?: string;
  deviceName?: string;
  onlineStatus?: number | string;
  onlineStatusLabel?: string;
  deviceStatus?: number | string;
  deviceStatusLabel?: string;
  enableStatus?: number | string;
  enableStatusLabel?: string;
  regionName?: string | null;
  subSystemName?: string | null;
}

export interface DeviceListWorkspace {
  kind: "device_list";
  ok: boolean;
  total: number;
  items: DeviceListItem[];
  summary?: string;
  page?: number;
  pageSize?: number;
}

/** download_file 导出结果卡 */
export interface ExportDownloadFileRef {
  url?: string;
  filename?: string;
}

export interface ExportDownloadWorkspace {
  kind: "export_download";
  ok: boolean;
  summary: string;
  total?: number;
  batchCount?: number;
  resource?: string;
  files?: ExportDownloadFileRef[];
  userCancelled?: boolean;
}

/** Workspace 当前展示内容（结构化查询结果：告警 / 设备等） */
export type WorkspaceContent =
  | AlarmQueryWorkspace
  | DeviceDetailWorkspace
  | DeviceCommandWorkspace
  | DeviceListWorkspace
  | ExportDownloadWorkspace
  | DeviceVariableRealtimeWorkspace
  | DeviceVariableHistoryWorkspace;

export interface DeviceVariableRealtimeItem {
  varName?: string;
  showName?: string;
  value?: string | number | null;
  unit?: string;
  quality?: string | number;
  updatedAt?: string | number;
  hasValue?: boolean;
}

export interface DeviceVariableRealtimeWorkspace {
  kind: "device_variable_realtime";
  ok: boolean;
  summary?: string;
  deviceCode?: string;
  deviceName?: string;
  /** 单变量兼容字段（多变量时取 items[0]） */
  varName?: string;
  showName?: string;
  value?: string | number | null;
  unit?: string;
  quality?: string | number;
  updatedAt?: string | number;
  /** 全量/多变量实时列表 */
  items?: DeviceVariableRealtimeItem[];
  total?: number;
  scope?: "all" | "single";
}

export interface DeviceVariableHistoryWorkspace {
  kind: "device_variable_history";
  ok: boolean;
  summary?: string;
  deviceCode?: string;
  deviceName?: string;
  varName?: string;
  showName?: string;
  points: Array<{ t?: string | number; v?: string | number | null }>;
  pointCount?: number;
  timeRange?: { start?: string; end?: string };
  navigate?: { path: string; query?: Record<string, string> };
}

/** 聊天消息 */
export interface AiMessage {
  id: string;
  role: AiMessageRole;
  blocks: AiMessageBlock[];
  createdAt: number;
  /** 用户本轮需求 ID：同 mid 的 user/assistant 气泡归属同一需求（方案 B 可多助手子卡） */
  mid?: string;
  streaming?: boolean;
  /** 本轮 SSE Trace（展示在该条助手消息内） */
  traceEvents?: TraceEvent[];
  /** Phase D3：Trace 执行图（历史恢复时由 API 提供） */
  traceGraph?: TraceGraph | null;
  runId?: string | null;
  /** 本轮结构化查询结果（如 query_alarms 表格） */
  workspaceContent?: WorkspaceContent | null;
  /** 本轮多步任务计划 */
  planSteps?: PlanStep[];
  /** Phase D4：计划线性流程图 */
  planGraph?: PlanGraph | null;
  /** BPMN 编排画布 JSON（plan_confirm 批准后持久化于消息） */
  planFlowDocument?: FlowDocumentJSON | null;
  planReplanReason?: string | null;
}

/** Plan SSE 载荷（含 graph / flow_document） */
export interface PlanSsePayload {
  steps: PlanStep[];
  graph?: PlanGraph;
  flow_document?: Record<string, unknown>;
}

/** SSE 事件处理器 */
export type AgentSseHandler = {
  onTextDelta?: (delta: string, meta?: { mid?: string }) => void;
  onToolStart?: (
    tool: string,
    args: Record<string, unknown>,
    meta?: { retry?: boolean; attempt?: number; mid?: string; toolCallId?: string },
  ) => void;
  onToolEnd?: (
    tool: string,
    result: string,
    meta?: { retry?: boolean; attempt?: number; mid?: string; toolCallId?: string },
  ) => void;
  onInterrupt?: (payload: HitlPayload) => void;
  onClientAction?: (action: ClientAction) => void | Promise<void>;
  onPlan?: (payload: PlanSsePayload | PlanStep[]) => void;
  onPlanUpdate?: (update: {
    step_id: string;
    status: string;
    tool?: string;
    node_id?: string;
    node_type?: string;
    skipReason?: string;
    matchedBranchKey?: string;
    label?: string;
    mid?: string;
  }) => void;
  onReplan?: (payload: {
    reason: string;
    steps: PlanStep[];
    attempt?: number;
    failed_tool?: string;
    mid?: string;
  }) => void;
  onTrace?: (event: TraceEvent) => void;
  onDone?: (threadId: string, meta?: { mid?: string }) => void;
  onError?: (code: number, message: string, data?: unknown) => void;
};
