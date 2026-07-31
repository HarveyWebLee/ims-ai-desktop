/**
 * 执行过程区块合并 / 过滤单测
 */
import { describe, expect, it } from "vitest";
import { coalesceExecutionBlocks, filterExecutionBlocksForMessage } from "./chatCardUtils";
import type { AiMessageBlock } from "./types";

describe("coalesceExecutionBlocks", () => {
  it("merges awaiting_hitl + done of same tool into one done row", () => {
    const blocks: AiMessageBlock[] = [
      {
        type: "tool_call",
        tool: "send_device_cmd",
        status: "awaiting_hitl",
        args: { action: "开门" },
      },
      {
        type: "tool_call",
        tool: "send_device_cmd",
        status: "done",
        args: { action: "开门", device_code: "D1" },
        result: '{"ok":true}',
      },
    ];
    const merged = coalesceExecutionBlocks(blocks);
    expect(merged).toHaveLength(1);
    expect(merged[0]).toMatchObject({
      type: "tool_call",
      tool: "send_device_cmd",
      status: "done",
      result: '{"ok":true}',
    });
  });

  it("keeps different tools as separate rows", () => {
    const blocks: AiMessageBlock[] = [
      {
        type: "tool_call",
        tool: "query_alarms",
        status: "done",
        args: {},
      },
      {
        type: "tool_call",
        tool: "send_device_cmd",
        status: "done",
        args: {},
      },
    ];
    expect(coalesceExecutionBlocks(blocks)).toHaveLength(2);
  });
});

describe("filterExecutionBlocksForMessage", () => {
  it("keeps hitl tool rows", () => {
    const blocks: AiMessageBlock[] = [
      {
        type: "tool_call",
        tool: "send_device_cmd",
        status: "awaiting_hitl",
        args: {},
      },
    ];
    const interrupt = {
      type: "interrupt" as const,
      payload: {
        type: "ask_params" as const,
        tool: "send_device_cmd",
        fields: [],
      },
    };
    expect(filterExecutionBlocksForMessage(blocks, interrupt)).toHaveLength(1);
  });
});
