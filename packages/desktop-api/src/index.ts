/**
 * 桌面端鉴权与 Agent API
 */
const TOKEN_KEY = "ims_ai_desktop_token";

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

/** 平台要求 Authorization: Bearer <access_token>（登录返回 token_type=bearer） */
function toBearerAuthorization(token: string): string {
  const trimmed = token.trim();
  if (!trimmed) return trimmed;
  return /^Bearer\s+/i.test(trimmed) ? trimmed : `Bearer ${trimmed}`;
}

export function getAuthHeaders(): Record<string, string> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  const token = getToken();
  if (token) {
    headers.Authorization = toBearerAuthorization(token);
  }
  return headers;
}

/** 平台统一响应 */
export interface PlatformEnvelope<T = unknown> {
  code: number;
  data: T;
  message?: string;
}

export interface LoginResult {
  token?: string;
  access_token?: string;
  accessToken?: string;
  [key: string]: unknown;
}

/** 简易登录：POST /api/app/auth/login */
export async function login(username: string, password: string): Promise<string> {
  const res = await fetch("/api/app/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  const raw = await res.text();
  let json: PlatformEnvelope<LoginResult>;
  try {
    json = JSON.parse(raw) as PlatformEnvelope<LoginResult>;
  } catch {
    throw new Error(raw.slice(0, 120) || `登录失败（HTTP ${res.status}）`);
  }
  if (json.code !== 0) {
    throw new Error(
      (typeof json.data === "string" ? json.data : null) || json.message || "登录失败",
    );
  }
  const data = json.data || {};
  const token =
    (typeof data === "string" ? data : null) || data.token || data.access_token || data.accessToken;
  if (!token || typeof token !== "string") {
    throw new Error("登录成功但未返回 token");
  }
  setToken(token);
  return token;
}

export function logout(): void {
  clearToken();
}
