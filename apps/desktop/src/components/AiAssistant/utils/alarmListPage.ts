/**
 * 告警列表分页：调用平台 getAlarmList，供 Workspace 表格翻页
 */
import { SystemController } from "@/services";
import type { AlarmQueryQueryContext, AlarmQueryWorkspace } from "../types";

const STATUS_LABELS: Record<number, string> = {
  1: "待确认",
  2: "已确认",
  3: "已处理",
};

function formatAlarmStatus(item: Record<string, unknown>): string {
  if (item.statusName) return String(item.statusName);
  const raw = item.status;
  if (raw === undefined || raw === null || raw === "") return "未知状态";
  const code = Number(raw);
  if (!Number.isNaN(code)) {
    return STATUS_LABELS[code] ?? String(raw);
  }
  return String(raw);
}

function pickVarName(item: Record<string, unknown>): string | null | undefined {
  const deviceVar = item.deviceVarName;
  if (deviceVar != null && String(deviceVar).trim() !== "") {
    return String(deviceVar);
  }
  const legacy = item.variableName;
  if (legacy != null && String(legacy).trim() !== "") {
    return String(legacy);
  }
  return legacy as string | null | undefined;
}

/** 与 MCP `_map_alarm_brief_item` 对齐的精简字段 */
export function mapAlarmRecordsToBrief(
  records: Record<string, unknown>[],
): AlarmQueryWorkspace["items"] {
  return records.map((item) => {
    const variableName = pickVarName(item);
    return {
      id: item.id as string | undefined,
      deviceName: item.deviceName as string | undefined,
      deviceCode: item.deviceCode as string | undefined,
      deviceVarName: variableName,
      variableName,
      alarmValue: item.alarmValue != null ? String(item.alarmValue) : null,
      startTime: item.startTime as string | undefined,
      endTime: (item.endTime as string | null | undefined) ?? null,
      status: item.status as number | string | undefined,
      statusName: formatAlarmStatus(item),
      alarmRankId: item.alarmRankId as number | string | undefined,
      alarmRankName: item.alarmRankName as string | undefined,
      alarmCategoryId: item.alarmCategoryId as number | string | undefined,
      alarmCategoryName: item.alarmCategoryName as string | undefined,
      eventName: item.eventName as string | undefined,
      regionName: (item.regionName as string | null | undefined) ?? null,
      subSystemName: (item.subSystemName as string | null | undefined) ?? null,
      confirmPerson: (item.confirmPerson as string | null | undefined) ?? null,
      confirmTime: (item.confirmTime as string | null | undefined) ?? null,
      processPerson: (item.processPerson as string | null | undefined) ?? null,
      processTime: (item.processTime as string | null | undefined) ?? null,
      handleMethod: (item.handleMethod as string | null | undefined) ?? null,
    };
  });
}

/** 按页拉取告警列表（与 Agent query_alarms 使用的平台接口一致） */
export async function fetchAlarmQueryPage(
  queryContext: AlarmQueryQueryContext,
  page: number,
  pageSize: number,
): Promise<{ total: number; items: AlarmQueryWorkspace["items"] }> {
  const listParams = {
    startTime: queryContext.startTime,
    endTime: queryContext.endTime,
    deviceCodes: queryContext.deviceCodes ?? [],
    variableNames: queryContext.variableNames ?? [],
    alarmCategoryId: queryContext.alarmCategoryId ?? [],
    alarmRankId: queryContext.alarmRankId ?? [],
    status: queryContext.status ?? [],
    page,
    size: pageSize,
  };

  const res =
    queryContext.listApi === "getAlarmUnprocessList"
      ? await SystemController.getAlarmUnprocessList(listParams)
      : await SystemController.getAlarmList(listParams);

  if (res?.code !== 0 || !res?.data) {
    throw new Error(res?.message || "告警列表加载失败");
  }

  const data = res.data as Record<string, unknown>;
  const records = (data.records ?? data.list ?? data.rows ?? []) as Record<string, unknown>[];
  const total = Number(data.total ?? data.totalCount ?? records.length ?? 0);

  return {
    total,
    items: mapAlarmRecordsToBrief(records),
  };
}
