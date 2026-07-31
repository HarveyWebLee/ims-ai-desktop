import { login as desktopLogin } from "@ims/desktop-api";

export async function login(data?: { username?: string; password?: string }) {
  const username = data?.username || "";
  const password = data?.password || "";
  const token = await desktopLogin(username, password);
  return { code: 0, data: { token }, message: "" };
}

export async function getUserInfo() {
  const { getAuthHeaders } = await import("@ims/desktop-api");
  const res = await fetch("/api/app/auth/info", {
    method: "POST",
    headers: getAuthHeaders(),
    body: "{}",
  });
  return res.json();
}
