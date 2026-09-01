import { getAuthHeaders } from "@ims/desktop-api";

export async function requestTo<P, T>(
  method: "get" | "post",
  options: {
    url: string;
    data?: P;
    responseType?: "blob" | "json";
  },
): Promise<{ code: number; data: T; message?: string }> {
  const { getAuthHeaders } = await import("@ims/desktop-api");
  const headers = getAuthHeaders();
  const isGet = method === "get";
  let url = options.url.startsWith("/api/")
    ? options.url
    : `/api/app${options.url.startsWith("/") ? "" : "/"}${options.url}`;

  if (isGet && options.data && typeof options.data === "object") {
    const qs = new URLSearchParams();
    for (const [k, v] of Object.entries(options.data as Record<string, unknown>)) {
      if (v !== undefined && v !== null) qs.set(k, String(v));
    }
    const q = qs.toString();
    if (q) url += (url.includes("?") ? "&" : "?") + q;
  }

  const res = await fetch(url, {
    method: method.toUpperCase(),
    headers:
      options.responseType === "blob" ? { Authorization: headers.Authorization || "" } : headers,
    body: isGet ? undefined : JSON.stringify(options.data ?? {}),
  });

  if (options.responseType === "blob") {
    if (!res.ok) {
      return { code: res.status, data: null as T, message: res.statusText };
    }
    const blob = await res.blob();
    return { code: 0, data: blob as T, message: "" };
  }

  return res.json();
}
