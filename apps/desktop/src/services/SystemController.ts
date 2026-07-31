/**
 * 平台 API 薄封装（HITL 选器等）
 */
import { getAuthHeaders } from "@ims/desktop-api";

async function platformRequest<T = unknown>(
  method: "GET" | "POST",
  path: string,
  data?: unknown,
): Promise<{ code: number; data: T; message?: string }> {
  let url = `/api/app${path}`;
  const headers = getAuthHeaders();
  const init: RequestInit = {
    method,
    headers,
  };

  if (method === "GET") {
    if (data && typeof data === "object") {
      const query = new URLSearchParams();
      for (const [k, v] of Object.entries(data as Record<string, unknown>)) {
        if (v !== undefined && v !== null) query.set(k, String(v));
      }
      const qs = query.toString();
      if (qs) url += `?${qs}`;
    }
  } else {
    init.body = JSON.stringify(data ?? {});
  }

  const res = await fetch(url, init);
  return res.json();
}

export async function getAlarmList(data?: unknown) {
  return platformRequest("POST", "/alarm/getAlarmList", data);
}

export async function getAlarmUnprocessList(data?: unknown) {
  return platformRequest("POST", "/alarm/getAlarmUnprocessList", data);
}

export async function getAlarmCategoryList(data?: unknown) {
  return platformRequest("POST", "/dic/getAlarmCategoryList", data);
}

export async function getAlarmRankList(data?: unknown) {
  return platformRequest("POST", "/dic/getAlarmRankList", data);
}

export async function getVarListByCode(data?: unknown) {
  return platformRequest("POST", "/device/getVarListByCode", data);
}

export async function getDeviceList(data?: unknown) {
  return platformRequest("POST", "/device/getDeviceList", data);
}

export async function getDeviceCategoryTree(data?: unknown) {
  return platformRequest("POST", "/device/getDeviceCategoryTree", data);
}

export async function getDeviceGroupTree(data?: unknown) {
  return platformRequest("POST", "/device/getDeviceGroupTree", data);
}

export async function getRegionTree(data?: unknown) {
  return platformRequest("GET", "/region/getRegionTree", data);
}
