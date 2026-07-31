import { describe, expect, it } from "vitest";
import type { AiMessage } from "../types";
import { resolveWorkspaceFromMessage } from "./workspaceFromTool";

function assistantMessage(
  blocks: AiMessage["blocks"],
  workspaceContent?: AiMessage["workspaceContent"],
): AiMessage {
  return {
    id: "a1",
    role: "assistant",
    blocks,
    createdAt: Date.now(),
    workspaceContent,
  };
}

describe("resolveWorkspaceFromMessage", () => {
  it("prefers existing workspaceContent when ok", () => {
    const existing = {
      kind: "alarm_query" as const,
      ok: true,
      total: 9,
      items: [],
      summary: "已有",
    };
    const msg = assistantMessage([], existing);
    expect(resolveWorkspaceFromMessage(msg)).toEqual(existing);
  });

  it("builds workspace from last successful query_alarms block", () => {
    const msg = assistantMessage([
      {
        type: "tool_call",
        tool: "query_alarms",
        args: { start_time: "今天", end_time: "" },
        status: "error",
        result: JSON.stringify({
          ok: false,
          summary: "请选择要查询的告警时间范围与筛选条件",
        }),
      },
      {
        type: "tool_call",
        tool: "query_alarms",
        args: { start_time: "今天 08:10", end_time: "今天 08:20" },
        status: "done",
        result: JSON.stringify({
          ok: true,
          summary: "共 2400 条告警",
          data: {
            total: 2400,
            items: [{ id: "1", deviceName: "系统联调0165" }],
            queryContext: {
              startTime: "2026-07-17 08:10:00",
              endTime: "2026-07-17 08:20:00",
            },
          },
        }),
      },
    ]);

    const workspace = resolveWorkspaceFromMessage(msg);
    expect(workspace?.kind).toBe("alarm_query");
    if (workspace?.kind === "alarm_query") {
      expect(workspace.ok).toBe(true);
      expect(workspace.total).toBe(2400);
      expect(workspace.items).toHaveLength(1);
    }
  });

  it("returns null when no successful query_alarms block", () => {
    const msg = assistantMessage([{ type: "text", content: "已为您查询到 2400 条告警。" }]);
    expect(resolveWorkspaceFromMessage(msg)).toBeNull();
  });

  it("builds workspace from get_device_detail block", () => {
    const msg = assistantMessage([
      {
        type: "tool_call",
        tool: "get_device_detail",
        args: { device_name: "B口门禁[172.168.1.43]" },
        status: "done",
        result: JSON.stringify({
          ok: true,
          summary: "设备详情",
          data: {
            device: {
              deviceCode: "zhonglian_103",
              deviceName: "B口门禁[172.168.1.43]",
              onlineStatusLabel: "离线",
              regionName: "A区",
              subSystemName: "门禁安检子系统",
              deviceGroupName: "门",
              ipAddress: "172.168.1.43",
              port: 8000,
            },
            onlineStatus: "离线",
          },
        }),
      },
    ]);

    const workspace = resolveWorkspaceFromMessage(msg);
    expect(workspace?.kind).toBe("device_detail");
    if (workspace?.kind === "device_detail") {
      expect(workspace.ok).toBe(true);
      expect(workspace.device.deviceCode).toBe("zhonglian_103");
      expect(workspace.device.ipAddress).toBe("172.168.1.43");
    }
  });

  it("builds workspace from send_device_cmd block", () => {
    const msg = assistantMessage([
      {
        type: "tool_call",
        tool: "send_device_cmd",
        args: { action: "开门" },
        status: "done",
        result: JSON.stringify({
          ok: true,
          summary:
            "已成功向设备「716门禁[172.168.1.42]」（zhonglian_108）下发变量 status_door_control=1。",
          data: {
            deviceCode: "zhonglian_108",
            deviceName: "716门禁[172.168.1.42]",
            variableName: "status_door_control",
            variableValue: "1",
            taskNo: "T-1001",
          },
        }),
      },
    ]);

    const workspace = resolveWorkspaceFromMessage(msg);
    expect(workspace?.kind).toBe("device_command");
    if (workspace?.kind === "device_command") {
      expect(workspace.ok).toBe(true);
      expect(workspace.deviceCode).toBe("zhonglian_108");
      expect(workspace.variableName).toBe("status_door_control");
      expect(workspace.taskNo).toBe("T-1001");
    }
  });
});
