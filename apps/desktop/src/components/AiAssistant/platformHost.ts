/**
 * 平台宿主桥：有宿主时执行 navigate / openModal；无宿主则返回 null 由 Executor 降级。
 *
 * 宿主注入（嵌入综合信息平台时由父页设置）：
 *   window.imsPlatformHost = { navigate, openModal }
 *
 * 本地验收：localStorage.setItem('ims_ai_mock_platform_host','1') 后刷新，
 * 启用模拟宿主（toast 可见执行效果）。
 */
import type { ClientAction } from "@ims/shared-types";
import { message } from "@/antd/feedback";

export type HostActionOutcome = {
  ok: boolean;
  summary?: string;
  error?: string;
};

export type PlatformHost = {
  navigate?: (payload: {
    path: string;
    query?: Record<string, string>;
  }) => HostActionOutcome | Promise<HostActionOutcome>;
  openModal?: (payload: {
    modal: string;
    params: Record<string, unknown>;
  }) => HostActionOutcome | Promise<HostActionOutcome>;
};

declare global {
  interface Window {
    imsPlatformHost?: PlatformHost;
  }
}

const MOCK_KEY = "ims_ai_mock_platform_host";

function createMockHost(): PlatformHost {
  return {
    navigate: ({ path, query }) => {
      const q =
        query && Object.keys(query).length > 0 ? `?${new URLSearchParams(query).toString()}` : "";
      message.success(`[模拟宿主] 已导航 ${path}${q}`);
      return { ok: true, summary: `模拟宿主已导航 ${path}${q}` };
    },
    openModal: ({ modal, params }) => {
      const id =
        typeof params.alarmId === "string" ? params.alarmId : JSON.stringify(params).slice(0, 40);
      message.success(`[模拟宿主] 已打开 ${modal}（${id}）`);
      return { ok: true, summary: `模拟宿主已打开 ${modal}` };
    },
  };
}

/** 解析当前宿主：真宿主优先；否则按 mock 开关。 */
export function resolvePlatformHost(): PlatformHost | null {
  if (typeof window === "undefined") return null;
  const real = window.imsPlatformHost;
  if (real && (typeof real.navigate === "function" || typeof real.openModal === "function")) {
    return real;
  }
  try {
    if (window.localStorage?.getItem(MOCK_KEY) === "1") {
      return createMockHost();
    }
  } catch {
    /* private mode */
  }
  return null;
}

export function isPlatformHostAvailable(): boolean {
  return resolvePlatformHost() != null;
}

export async function hostNavigate(
  path: string,
  query?: Record<string, string>,
): Promise<HostActionOutcome | null> {
  const host = resolvePlatformHost();
  if (!host?.navigate) return null;
  return host.navigate({ path, query });
}

export async function hostOpenModal(
  action: Extract<ClientAction, { action: "openModal" }>,
): Promise<HostActionOutcome | null> {
  const host = resolvePlatformHost();
  if (!host?.openModal) return null;
  return host.openModal({
    modal: action.modal,
    params: action.params as unknown as Record<string, unknown>,
  });
}
