/**
 * 从 Server Tool 返回 JSON 构建 Workspace 结构化展示数据
 */
import type {
  AiMessage,
  AlarmQueryWorkspace,
  DeviceCommandWorkspace,
  DeviceDetailRecord,
  DeviceDetailWorkspace,
  DeviceVariableHistoryWorkspace,
  DeviceVariableRealtimeWorkspace,
  WorkspaceContent,
} from "../types";
export interface AlarmBriefItem {
  id?: string;
  deviceName?: string;
  variableName?: string | null;
  startTime?: string;
  status?: number | string;
  statusName?: string;
  alarmRankName?: string;
}

/** 解析 query_alarms tool_end 的 result 字符串 */
export function buildAlarmQueryWorkspace(
  resultJson: string,
  toolArgs?: Record<string, unknown>,
): AlarmQueryWorkspace | null {
  let parsed: Record<string, unknown>;
  try {
    parsed = JSON.parse(resultJson) as Record<string, unknown>;
  } catch {
    return null;
  }

  if (!parsed.ok) {
    return {
      kind: "alarm_query",
      ok: false,
      total: 0,
      items: [],
      summary: String(parsed.summary ?? "查询失败"),
      timeRange: buildTimeRangeFromArgs(toolArgs),
    };
  }

  const data = (parsed.data ?? {}) as Record<string, unknown>;
  const items = (Array.isArray(data.items) ? data.items : []) as AlarmBriefItem[];
  const total = Number(data.total ?? items.length ?? 0);
  const page = Number(data.page ?? 1);
  const pageSize = Number(data.pageSize ?? (items.length || 20));
  const queryContext = data.queryContext as AlarmQueryWorkspace["queryContext"];

  const timeRange =
    buildTimeRangeFromQueryContext(queryContext) ?? buildTimeRangeFromArgs(toolArgs);

  return {
    kind: "alarm_query",
    ok: true,
    total,
    items,
    summary: String(parsed.summary ?? ""),
    timeRange,
    page,
    pageSize,
    queryContext,
  };
}

/** 从 tool_start args 提取查询时间范围（ISO → 日期展示） */
function buildTimeRangeFromArgs(
  toolArgs?: Record<string, unknown>,
): AlarmQueryWorkspace["timeRange"] {
  if (!toolArgs) return undefined;
  const start = String(toolArgs.start_time ?? "");
  const end = String(toolArgs.end_time ?? "");
  if (!start && !end) return undefined;
  return {
    start: formatDisplayTime(start),
    end: formatDisplayTime(end),
  };
}

/** 优先使用服务端 queryContext 中已解析的平台时间（比 args 中的「昨天」更准确） */
function buildTimeRangeFromQueryContext(
  queryContext?: AlarmQueryWorkspace["queryContext"],
): AlarmQueryWorkspace["timeRange"] | undefined {
  if (!queryContext?.startTime || !queryContext?.endTime) return undefined;
  return {
    start: formatDisplayTime(String(queryContext.startTime)),
    end: formatDisplayTime(String(queryContext.endTime)),
  };
}

function formatDisplayTime(value: string): string {
  if (!value) return "";
  const normalized = value.replace("T", " ").replace(/([+-]\d{2}:\d{2}|Z)$/i, "");
  if (/\d{1,2}:\d{2}/.test(normalized)) {
    return normalized.trim().slice(0, 16);
  }
  return normalized.trim().slice(0, 10);
}

function normalizeDeviceDetailRecord(raw: unknown): DeviceDetailRecord | null {
  if (!raw || typeof raw !== "object") return null;
  const record = raw as Record<string, unknown>;
  const deviceCode = String(record.deviceCode ?? "").trim();
  const deviceName = String(record.deviceName ?? "").trim();
  if (!deviceCode && !deviceName) return null;
  return record as DeviceDetailRecord;
}

/** 解析 get_device_detail tool_end 的 result 字符串 */
export function buildDeviceDetailWorkspace(resultJson: string): DeviceDetailWorkspace | null {
  let parsed: Record<string, unknown>;
  try {
    parsed = JSON.parse(resultJson) as Record<string, unknown>;
  } catch {
    return null;
  }

  if (!parsed.ok) {
    return {
      kind: "device_detail",
      ok: false,
      device: {},
      summary: String(parsed.summary ?? "查询失败"),
    };
  }

  const data = (parsed.data ?? {}) as Record<string, unknown>;
  const device = normalizeDeviceDetailRecord(data.device);
  if (!device) return null;

  return {
    kind: "device_detail",
    ok: true,
    device,
    summary: String(parsed.summary ?? ""),
  };
}

/** 解析 send_device_cmd tool_end 的 result 字符串 */
export function buildDeviceCommandWorkspace(resultJson: string): DeviceCommandWorkspace | null {
  let parsed: Record<string, unknown>;
  try {
    parsed = JSON.parse(resultJson) as Record<string, unknown>;
  } catch {
    return null;
  }

  const summary = String(parsed.summary ?? "").trim();
  const userCancelled = parsed.user_cancelled === true;
  const ok = userCancelled ? false : Boolean(parsed.ok);
  const data =
    parsed.data && typeof parsed.data === "object" && !Array.isArray(parsed.data)
      ? (parsed.data as Record<string, unknown>)
      : {};

  const autoRetryRaw = data.auto_retry as { from?: string; to?: string } | undefined;
  const autoRetry =
    autoRetryRaw?.from && autoRetryRaw?.to
      ? { from: String(autoRetryRaw.from), to: String(autoRetryRaw.to) }
      : undefined;

  return {
    kind: "device_command",
    ok,
    summary:
      summary ||
      (userCancelled ? "已取消设备指令下发" : ok ? "设备指令下发成功" : "设备指令下发失败"),
    deviceCode: data.deviceCode != null ? String(data.deviceCode) : undefined,
    deviceName: data.deviceName != null ? String(data.deviceName) : undefined,
    variableName: data.variableName != null ? String(data.variableName) : undefined,
    variableValue: data.variableValue != null ? String(data.variableValue) : undefined,
    taskNo: data.taskNo != null ? String(data.taskNo) : undefined,
    autoRetry,
    userCancelled,
  };
}

function asRecord(value: unknown): Record<string, unknown> | null {
  if (value && typeof value === "object" && !Array.isArray(value)) {
    return value as Record<string, unknown>;
  }
  return null;
}

/** 解析 query_device_variable_realtime */
export function buildDeviceVariableRealtimeWorkspace(
  resultJson: string,
): DeviceVariableRealtimeWorkspace | null {
  let parsed: Record<string, unknown>;
  try {
    parsed = JSON.parse(resultJson) as Record<string, unknown>;
  } catch {
    return null;
  }
  const data = asRecord(parsed.data) ?? {};
  const device = asRecord(data.device) ?? {};
  const variable = asRecord(data.variable) ?? {};
  const itemsRaw = Array.isArray(data.items) ? data.items : [];
  const items = itemsRaw
    .filter((it): it is Record<string, unknown> => !!it && typeof it === "object")
    .map((it) => ({
      varName: it.varName != null ? String(it.varName) : undefined,
      showName: it.showName != null ? String(it.showName) : undefined,
      value: (it.value as string | number | null | undefined) ?? null,
      unit: it.unit != null ? String(it.unit) : undefined,
      quality: it.quality as string | number | undefined,
      updatedAt: it.updated_at as string | number | undefined,
      hasValue:
        typeof it.has_value === "boolean"
          ? it.has_value
          : it.value != null && String(it.value).trim() !== "",
    }));

  const scopeRaw = String(data.scope || "");
  const scope: "all" | "single" | undefined =
    scopeRaw === "all" || scopeRaw === "single"
      ? scopeRaw
      : items.length > 1
        ? "all"
        : items.length === 1
          ? "single"
          : undefined;

  return {
    kind: "device_variable_realtime",
    ok: Boolean(parsed.ok),
    summary: String(parsed.summary ?? ""),
    deviceCode: device.deviceCode != null ? String(device.deviceCode) : undefined,
    deviceName: device.deviceName != null ? String(device.deviceName) : undefined,
    varName: variable.varName != null ? String(variable.varName) : undefined,
    showName: variable.showName != null ? String(variable.showName) : undefined,
    value: (data.value as string | number | null | undefined) ?? null,
    unit: data.unit != null ? String(data.unit) : undefined,
    quality: data.quality as string | number | undefined,
    updatedAt: data.updated_at as string | number | undefined,
    items: items.length ? items : undefined,
    total: data.total != null ? Number(data.total) : items.length || undefined,
    scope,
  };
}

/** 解析 query_device_variable_history */
export function buildDeviceVariableHistoryWorkspace(
  resultJson: string,
): DeviceVariableHistoryWorkspace | null {
  let parsed: Record<string, unknown>;
  try {
    parsed = JSON.parse(resultJson) as Record<string, unknown>;
  } catch {
    return null;
  }
  const data = asRecord(parsed.data) ?? {};
  const device = asRecord(data.device) ?? {};
  const variable = asRecord(data.variable) ?? {};
  const timeRange = asRecord(data.timeRange);
  const navigateRaw = asRecord(data.navigate);
  const pointsRaw = Array.isArray(data.points) ? data.points : [];
  const points = pointsRaw
    .filter((p): p is Record<string, unknown> => !!p && typeof p === "object")
    .map((p) => ({
      t: p.t as string | number | undefined,
      v: p.v as string | number | null | undefined,
    }));
  const navigate =
    navigateRaw && typeof navigateRaw.path === "string"
      ? {
          path: String(navigateRaw.path),
          query:
            navigateRaw.query && typeof navigateRaw.query === "object"
              ? Object.fromEntries(
                  Object.entries(navigateRaw.query as Record<string, unknown>).map(([k, v]) => [
                    k,
                    String(v ?? ""),
                  ]),
                )
              : undefined,
        }
      : undefined;

  return {
    kind: "device_variable_history",
    ok: Boolean(parsed.ok),
    summary: String(parsed.summary ?? data.summary ?? ""),
    deviceCode: device.deviceCode != null ? String(device.deviceCode) : undefined,
    deviceName: device.deviceName != null ? String(device.deviceName) : undefined,
    varName: variable.varName != null ? String(variable.varName) : undefined,
    showName: variable.showName != null ? String(variable.showName) : undefined,
    points,
    pointCount: data.point_count != null ? Number(data.point_count) : points.length,
    timeRange: timeRange
      ? {
          start: timeRange.start != null ? String(timeRange.start) : undefined,
          end: timeRange.end != null ? String(timeRange.end) : undefined,
        }
      : undefined,
    navigate,
  };
}

/** 根据工具名与 result 更新 Workspace */
export function workspaceFromToolEnd(
  tool: string,
  result: string,
  toolArgs?: Record<string, unknown>,
): WorkspaceContent | null {
  if (tool === "query_alarms") {
    return buildAlarmQueryWorkspace(result, toolArgs);
  }
  if (tool === "get_device_detail") {
    return buildDeviceDetailWorkspace(result);
  }
  if (tool === "send_device_cmd") {
    return buildDeviceCommandWorkspace(result);
  }
  if (tool === "query_device_variable_realtime") {
    return buildDeviceVariableRealtimeWorkspace(result);
  }
  if (tool === "query_device_variable_history") {
    return buildDeviceVariableHistoryWorkspace(result);
  }
  return null;
}

/**
 * 从助手消息 blocks 中解析最后一次成功的结构化 Workspace。
 * 用于 onDone / 历史恢复时补全 workspaceContent（避免「查看结果」按钮丢失）。
 */
export function resolveWorkspaceFromMessage(
  message: Pick<AiMessage, "blocks" | "workspaceContent">,
): WorkspaceContent | null {
  const existing = message.workspaceContent;
  if (existing?.kind === "device_command") {
    return existing;
  }
  if (existing?.ok) {
    return existing;
  }

  let lastOk: WorkspaceContent | null = null;
  let lastDeviceCommand: WorkspaceContent | null = null;
  for (const block of message.blocks) {
    if (block.type !== "tool_call") continue;
    if (block.status !== "done" || !block.result) continue;
    const workspace = workspaceFromToolEnd(block.tool, block.result, block.args);
    if (!workspace) continue;
    if (workspace.kind === "device_command") {
      lastDeviceCommand = workspace;
      continue;
    }
    if (workspace.ok) {
      lastOk = workspace;
    }
  }
  return lastDeviceCommand ?? lastOk;
}
