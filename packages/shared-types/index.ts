/**
 * @ims/shared-types — 前后端共享类型定义
 * AgentModelId 须与 @ims/agent-core/model-catalog.ts 严格对齐
 */

/** Agent 可选大模型 ID（与 model-catalog 同步） */
export type AgentModelId =
  | "qwen3.5-35b-a3b"
  | "qwen3-8b"
  | "qwen3-32b"
  | "qwen3-coder-plus"
  | "qwen3-coder-480b-a35b-instruct"
  | "deepseek-v4-flash"
  | "deepseek-r1-distill-qwen-7b"
  | "deepseek-r1-distill-qwen-32b"
  | "qwen3-vl-flash-2025-10-15"
  | "qwen3-vl-8b-thinking"
  | "qwen3-vl-30b-a3b-thinking"
  | "qwen3-vl-32b-thinking"
  | "qwen3-vl-235b-a22b-thinking"
  | "qwen-vl-plus"
  | "qwen-vl-ocr-latest"
  | "qwen3.7-flash-2026-07-15"
  | "qwen-plus-0112"
  | "qwen-plus"
  | "qwen-turbo"
  | "qwen3-next-80b-a3b-thinking"
  | "qwen3.5-27b"
  | "tongyi-xiaomi-analysis-flash"
  | "qwen3-vl-flash"
  | "qwen3-14b"
  | "qwen3-max-2025-09-23"
  | "qwen-plus-2025-12-01"
  | "qwen-plus-character"
  | "qwen-flash-character"
  | "qwen3-30b-a3b-instruct-2507"
  | "qwen-flash"
  | "qwen-flash-2025-07-28"
  | "qwen3-235b-a22b-instruct-2507"
  | "qwen3.5-plus-2026-04-20"
  | "qwen-plus-1220"
  | "qwen3.5-122b-a10b"
  | "qwen3-max"
  | "qwen3.5-plus-2026-02-15"
  | "qwen3-235b-a22b-thinking-2507"
  | "qwen3.7-max-2026-06-08"
  | "qwen3.7-max-preview"
  | "qwen3.6-max-preview";

/** 模型提供方 */
export type AgentModelProvider = "deepseek" | "dashscope";

/** 平台工具执行侧 */
export type PlatformToolSide = "server" | "client";

/** 工具风险等级 */
export type PlatformToolRiskLevel = "low" | "medium" | "high";

/**
 * 会话运行模式（对齐 Cursor Mode：权限即产品）
 * - readonly：仅查询类工具
 * - confirm：写操作须 HITL 确认（默认）
 * - autonomous：跳过 confirm HITL，缺参仍 ask_params
 */
export type AgentRunMode = "readonly" | "confirm" | "autonomous";

/** 工具领域标签（子集注入） */
export type PlatformToolDomain = "alarm" | "device" | "export" | "nav" | "duty" | "acs";

/** 工具 preflight 声明式规则（catalog 驱动，Python 领域 handler 仍负责时间语义解析） */
export interface ToolPreflightConfig {
  /** 缺时间时触发 HITL datetime_range（query_alarms / download_file / batch_*） */
  alarm_time?: boolean;
  /**
   * download_file：仅当 resource 命中时走 alarm_time。
   * 支持单值或数组（多 resource 共用时间补参）。
   */
  when_resource?: string | string[];
  /** 条件必填：任一组字段有值即满足（如 alarm_ids 与 time 二选一） */
  one_of?: string[][];
}

/** 平台工具 manifest 定义（tool-catalog 条目） */
export interface PlatformToolDefinition {
  /** snake_case 全局唯一工具名 */
  name: string;
  /** 给 LLM 的中文说明 */
  description: string;
  /** OpenAI function calling 兼容 JSON Schema */
  parameters: Record<string, unknown>;
  /** server：Agent 调平台 API；client：SSE → ClientToolExecutor */
  side: PlatformToolSide;
  risk_level: PlatformToolRiskLevel;
  /** 领域标签：create_agent 绑定时按意图裁剪子集 */
  domains?: PlatformToolDomain[];
  /** 平台权限码（可选） */
  required_permissions?: string[];
  /** Server Tool 绑定的平台 API 路径 */
  platform_api?: string;
  /** Client Tool 动作类型 */
  client_action?: string;
  /** 是否在 Agent 中启用 */
  enabled?: boolean;
  /** HITL 补参表单字段（datetime_range / async_select 等复杂类型） */
  hitl_fields?: HitlField[];
  /** invoke 前 preflight 规则（与 Python tool_preflight 对齐） */
  preflight?: ToolPreflightConfig;
}

/** Agent 后端标准 JSON 响应 envelope */
export interface AgentApiResponse<T = unknown> {
  /** 0 成功，非 0 失败 */
  code: number;
  data: T;
  message: string;
}

/** SSE 事件类型 */
export type AgentSseEventType =
  | "message"
  | "tool_start"
  | "tool_end"
  | "interrupt"
  | "client_action"
  | "plan"
  | "plan_update"
  | "replan"
  | "trace"
  | "done"
  | "error";

/** 多步任务计划步骤 */
export type PlanStepStatus =
  | "pending"
  | "running"
  | "done"
  | "error"
  | "skipped"
  /** HITL 中断：工具暂停，等待使用者补参或确认 */
  | "awaiting_hitl"
  /** plan_confirm：多步计划已生成，等待使用者批准后开始执行 */
  | "awaiting_confirm";

export interface PlanStep {
  id: string;
  label: string;
  tool?: string;
  status: PlanStepStatus;
  /** 计划或实际入参（脱敏后，供 BPMN 节点详情） */
  args?: Record<string, unknown>;
  /** 一行结果摘要（成功/进行中预览） */
  resultSummary?: string;
  /** 失败原因 */
  errorMessage?: string;
  /** 开始时间 epoch ms */
  startedAt?: number;
  /** 结束时间 epoch ms */
  endedAt?: number;
  /** 工具执行侧（来自 tool-catalog） */
  side?: PlatformToolSide;
  /** 工具风险等级（来自 tool-catalog） */
  riskLevel?: PlatformToolRiskLevel;
  /** HITL 卡点信息（类型 + 用户决议） */
  hitl?: PlanStepHitlInfo;
  /** 工具重试标记（SSE tool_start/end meta.retry） */
  retry?: boolean;
  /** 当前尝试轮次（从 1 起） */
  attempt?: number;
  /** 自动换变量重试：原变量名 */
  autoRetryFrom?: string;
  /** 自动换变量重试：新变量名 */
  autoRetryTo?: string;
  /** BPMN 画布节点 id（与 step.id 可能相同） */
  nodeId?: string;
  /** BPMN 节点类型（CONDITION / AUTO 等） */
  nodeType?: string;
  /** 条件未匹配等跳过原因 */
  skipReason?: string;
  /** 条件节点命中分支 key（如 if_online / else） */
  matchedBranchKey?: string;
  /**
   * LLM 编排节点绑定的模型 ID（画布元数据；执行仍以会话 selectedModelId 为准）
   */
  modelId?: AgentModelId | string;
}

/** Plan 步骤上的 HITL 快照 */
export interface PlanStepHitlInfo {
  type?: "ask_params" | "confirm" | "plan_confirm";
  /** 用户决议 */
  resolution?: "approved" | "rejected" | "submitted" | "cancelled";
  message?: string;
}

/** 执行 Trace 事件（研发只读观测） */
export type TraceEventKind =
  | "user_message"
  | "plan"
  | "replan"
  | "tool_start"
  | "tool_end"
  | "interrupt"
  | "client_action"
  | "error"
  | "done";

export interface TraceEvent {
  id: string;
  ts: number;
  kind: TraceEventKind | string;
  label: string;
  detail?: Record<string, unknown>;
}

/** Phase D3：Trace 执行图（只读可视化） */
export interface TraceGraphNode {
  id: string;
  label: string;
  kind: string;
  style?: string;
  ts?: number;
}

export interface TraceGraphEdge {
  from: string;
  to: string;
}

export interface TraceGraph {
  nodes: TraceGraphNode[];
  edges: TraceGraphEdge[];
  mermaid: string;
}

/** Phase D4：Plan 流程图（与 TraceGraph 结构一致） */
export type PlanGraph = TraceGraph;

export interface AgentTraceRun {
  thread_id: string;
  run_id: string;
  started_at: number;
  ended_at: number;
  events: TraceEvent[];
  /** 由 trace API 附加的执行图 */
  graph?: TraceGraph;
}

/** send_device_cmd confirm 前设备摘要（Phase B） */
export interface HitlDevicePreview {
  deviceCode?: string;
  deviceName?: string;
  onlineStatusLabel?: string;
  regionName?: string;
  subSystemName?: string;
  variableName?: string;
  variableValue?: string;
  operateName?: string;
}

/** HITL interrupt payload（一律由父图 / 工具包装器 interrupt 产生；resume → Command） */
export interface HitlPayload {
  type: "ask_params" | "confirm" | "plan_confirm";
  tool: string;
  fields?: HitlField[];
  message?: string;
  /** 用户本轮需求 ID；resume 须回传，与 SSE/气泡归属一致 */
  mid?: string;
  /** ask_params：表单预填值（如 device_code / start_time） */
  current?: Record<string, unknown>;
  /** confirm：指令下发前设备摘要（来自 get_device_detail 等价只读） */
  device_preview?: HitlDevicePreview;
  /** plan_confirm：待用户批准的多步计划预览 */
  steps?: PlanStep[];
  /** plan_confirm：步骤流程图（D4 图形化编排） */
  graph?: PlanGraph;
  /** plan_confirm：BPMN 画布 JSON（服务端下发初始画布） */
  flow_document?: Record<string, unknown>;
}

export interface HitlField {
  name: string;
  label: string;
  type:
    | "string"
    | "text"
    | "number"
    | "date"
    | "datetime"
    | "datetime_range"
    | "select"
    | "async_select"
    /** 设备单选表格（筛选分组/类型/区域/名称/编码/在线状态） */
    | "device_picker"
    /** 设备变量下拉（依赖同行 device_picker 或固定 deviceCode） */
    | "variable_picker";
  required?: boolean;
  options?: { label: string; value: string }[];
  description?: string;
  /** async_select：平台字典数据源 */
  asyncSource?: "alarm_category" | "alarm_rank";
  /** select / async_select：多选 */
  mode?: "multiple";
  /**
   * variable_picker：固定设备编码。
   * 未设时读取同表单 dependsOn 字段（默认 device_code）。
   */
  deviceCode?: string;
  /** variable_picker：仅展示可写变量；默认 false（展示全部变量） */
  writableOnly?: boolean;
  /**
   * variable_picker：依赖的设备编码字段名，默认 device_code
   */
  dependsOn?: string;
  /**
   * device_picker：预填筛选（如上一轮 query_devices 的在线状态）
   * onlineStatus: 0 离线 / 1 在线 / 2 异常
   */
  defaultFilters?: {
    deviceGroupId?: string | number;
    deviceCategoryId?: string | number;
    regionId?: string | number;
    deviceName?: string;
    deviceCode?: string;
    onlineStatus?: number;
  };
}

/** Client Tool 动作协议 */
export type ClientAction =
  | { action: "navigate"; path: string; query?: Record<string, string> }
  | {
      action: "openModal";
      modal: "alarmDetail";
      params: { alarmId: string; record?: Record<string, unknown> };
    }
  | { action: "download"; url: string; filename: string }
  | {
      action: "toast";
      level: "success" | "error" | "info";
      message: string;
    }
  | { action: "refresh"; target?: string }
  | { action: "pause"; seconds: number };

/**
 * 桌面/宿主执行 client_action 后的回执（P2-2）。
 * 经 POST /api/agent/threads/{thread_id}/client-action-result 写入审计；不阻塞图、不替代 HITL。
 */
export interface ClientActionResult {
  /** 动作类型，与 ClientAction.action 对齐 */
  action: ClientAction["action"];
  ok: boolean;
  /** true=无宿主或宿主拒绝执行时的产品降级跳过 */
  skipped?: boolean;
  summary?: string;
  error?: string;
  /** navigate 时的目标路径 */
  path?: string;
  /** openModal 时的弹窗名 */
  modal?: string;
}

/**
 * 平台工具统一返回（MCP Tool JSON / SSE tool_end.result）。
 * 与 `platform_mcp.runtime.result.tool_result` 对齐。
 *
 * `client_action` 与 `client_actions` 二选一；同时存在时序列化侧优先 `client_actions`
 *（如分批导出多文件）。Agent 流层会展开为多条 SSE `client_action` 事件。
 */
export interface ToolResult {
  ok: boolean;
  summary: string;
  /** 结构化载荷（列表、计数、平台响应等）；形状随工具而定 */
  data?: unknown;
  client_action?: ClientAction | null;
  /** 多条前端动作（分批下载等）；优先于 client_action */
  client_actions?: ClientAction[];
  /** 用户 HITL 拒绝 / 取消；编排层应跳过自动重试 */
  user_cancelled?: boolean;
}
