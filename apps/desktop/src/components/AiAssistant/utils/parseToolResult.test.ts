import { describe, expect, it } from "vitest";
import {
  parseToolResultClientActions,
  parseToolResultOk,
  parseToolResultUserCancelled,
} from "./parseToolResult";

describe("parseToolResultClientActions", () => {
  it("prefers client_actions over client_action", () => {
    const result = JSON.stringify({
      ok: true,
      summary: "导出完成",
      client_action: { action: "download", url: "/a", filename: "a.xlsx" },
      client_actions: [
        { action: "download", url: "/1", filename: "1.xlsx" },
        { action: "download", url: "/2", filename: "2.xlsx" },
      ],
    });
    expect(parseToolResultClientActions(result)).toEqual([
      { action: "download", url: "/1", filename: "1.xlsx" },
      { action: "download", url: "/2", filename: "2.xlsx" },
    ]);
  });

  it("falls back to single client_action", () => {
    const result = JSON.stringify({
      ok: true,
      summary: "跳转",
      client_action: { action: "navigate", path: "/devices" },
    });
    expect(parseToolResultClientActions(result)).toEqual([
      { action: "navigate", path: "/devices" },
    ]);
  });

  it("returns empty for missing or invalid JSON", () => {
    expect(parseToolResultClientActions(undefined)).toEqual([]);
    expect(parseToolResultClientActions("not-json")).toEqual([]);
    expect(parseToolResultClientActions(JSON.stringify({ ok: true, summary: "x" }))).toEqual([]);
  });
});

describe("parseToolResultOk / user_cancelled", () => {
  it("reads ToolResult fields", () => {
    expect(parseToolResultOk(JSON.stringify({ ok: false, summary: "失败" }))).toBe(false);
    expect(
      parseToolResultUserCancelled(
        JSON.stringify({ ok: false, summary: "已取消", user_cancelled: true }),
      ),
    ).toBe(true);
  });
});
