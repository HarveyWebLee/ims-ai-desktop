import { describe, expect, it } from "vitest";
import type { HitlPayload } from "@ims/shared-types";
import type { AiMessage, AiMessageBlock } from "../types";
import {
  applyPendingInterruptToMessages,
  findPendingInterruptFromMessages,
  isGraphLevelHitlType,
  resolveActiveHitlMessageId,
  shouldPreserveHitlOnStreamDone,
  shouldShowHitlQuickActions,
  shouldHideMessagePlanForInteractiveHitl,
  shouldShowPlanConfirmActions,
  shouldShowToolConfirmActions,
} from "./hitlInterruptUtils";

function assistantMsg(
  id: string,
  blocks: AiMessageBlock[],
  extra: Partial<AiMessage> = {},
): AiMessage {
  return {
    id,
    role: "assistant",
    blocks,
    createdAt: Date.now(),
    ...extra,
  };
}

const planConfirmPayload: HitlPayload = {
  type: "plan_confirm",
  tool: "__plan__",
  message: "确认计划",
  steps: [{ id: "1", label: "查", tool: "query_alarms", status: "awaiting_confirm" }],
};

const askParamsPayload: HitlPayload = {
  type: "ask_params",
  tool: "query_alarms",
  message: "补时间",
  fields: [{ name: "start_time", label: "开始", type: "text" }],
};

const confirmPayload: HitlPayload = {
  type: "confirm",
  tool: "send_device_cmd",
  message: "确认下发",
};

describe("isGraphLevelHitlType", () => {
  it("covers all HitlPayload types", () => {
    expect(isGraphLevelHitlType("plan_confirm")).toBe(true);
    expect(isGraphLevelHitlType("ask_params")).toBe(true);
    expect(isGraphLevelHitlType("confirm")).toBe(true);
    expect(isGraphLevelHitlType("other")).toBe(false);
  });
});

describe("shouldPreserveHitlOnStreamDone", () => {
  it("preserves plan_confirm without tool_call", () => {
    expect(
      shouldPreserveHitlOnStreamDone(planConfirmPayload, [
        { type: "interrupt", payload: planConfirmPayload },
      ]),
    ).toBe(true);
  });

  it("preserves ask_params without tool_call", () => {
    expect(
      shouldPreserveHitlOnStreamDone(askParamsPayload, [
        { type: "interrupt", payload: askParamsPayload },
      ]),
    ).toBe(true);
  });

  it("preserves confirm without tool_call (preflight / plan 门控确认)", () => {
    expect(
      shouldPreserveHitlOnStreamDone(confirmPayload, [
        { type: "interrupt", payload: confirmPayload },
      ]),
    ).toBe(true);
  });

  it("preserves confirm when tool still running", () => {
    expect(
      shouldPreserveHitlOnStreamDone(confirmPayload, [
        { type: "interrupt", payload: confirmPayload },
        {
          type: "tool_call",
          tool: "send_device_cmd",
          status: "running",
          args: {},
        },
      ]),
    ).toBe(true);
  });
});

describe("resolveActiveHitlMessageId", () => {
  it("finds message with interrupt block", () => {
    const messages = [assistantMsg("a1", [{ type: "interrupt", payload: planConfirmPayload }])];
    expect(resolveActiveHitlMessageId(messages, null)).toBe("a1");
  });

  it("prefers mid-matched assistant over later interrupt-less bubble", () => {
    const payload = { ...askParamsPayload, mid: "m-door" };
    const messages = [
      assistantMsg("a1", [{ type: "interrupt", payload }], { mid: "m-door" }),
      assistantMsg("a2", [{ type: "text", content: "总结" }], { mid: "m-broadcast" }),
    ];
    expect(resolveActiveHitlMessageId(messages, payload)).toBe("a1");
  });

  it("falls back to pendingInterrupt with awaiting plan", () => {
    const messages = [
      assistantMsg("a2", [], {
        planSteps: [
          {
            id: "1",
            label: "查",
            tool: "query_alarms",
            status: "awaiting_confirm",
          },
        ],
      }),
    ];
    expect(resolveActiveHitlMessageId(messages, planConfirmPayload)).toBe("a2");
  });
});

describe("findPendingInterruptFromMessages", () => {
  it("returns last assistant interrupt", () => {
    const messages = [assistantMsg("a1", [{ type: "interrupt", payload: askParamsPayload }])];
    expect(findPendingInterruptFromMessages(messages)).toEqual(askParamsPayload);
  });

  it("backfills mid from assistant message", () => {
    const messages = [
      assistantMsg("a1", [{ type: "interrupt", payload: askParamsPayload }], { mid: "m1" }),
    ];
    expect(findPendingInterruptFromMessages(messages)?.mid).toBe("m1");
  });
});

describe("applyPendingInterruptToMessages", () => {
  it("attaches pending interrupt to mid-matched assistant", () => {
    const pending = { ...confirmPayload, mid: "m2" };
    const messages = [
      assistantMsg("a1", [{ type: "text", content: "旧" }], { mid: "m1" }),
      assistantMsg("a2", [{ type: "text", content: "新" }], { mid: "m2" }),
    ];
    const next = applyPendingInterruptToMessages(messages, pending);
    expect(next[1].blocks.some((b) => b.type === "interrupt")).toBe(true);
    expect(findPendingInterruptFromMessages(next)?.tool).toBe("send_device_cmd");
  });
});

describe("action visibility helpers", () => {
  it("plan confirm actions only for plan_confirm", () => {
    expect(shouldShowPlanConfirmActions(planConfirmPayload, true)).toBe(true);
    expect(shouldShowPlanConfirmActions(confirmPayload, true)).toBe(false);
  });

  it("tool confirm actions only for confirm", () => {
    expect(shouldShowToolConfirmActions(confirmPayload, true)).toBe(true);
    expect(shouldShowToolConfirmActions(askParamsPayload, true)).toBe(false);
  });

  it("quick actions bar only for ask_params", () => {
    expect(shouldShowHitlQuickActions(confirmPayload, true)).toBe(false);
    expect(shouldShowHitlQuickActions(askParamsPayload, true)).toBe(true);
    expect(shouldShowHitlQuickActions(planConfirmPayload, true)).toBe(false);
    expect(shouldShowHitlQuickActions(confirmPayload, false)).toBe(false);
  });

  it("hides message plan section during interactive plan_confirm", () => {
    expect(shouldHideMessagePlanForInteractiveHitl(planConfirmPayload, true)).toBe(true);
    expect(shouldHideMessagePlanForInteractiveHitl(planConfirmPayload, false)).toBe(false);
    expect(shouldHideMessagePlanForInteractiveHitl(askParamsPayload, true)).toBe(false);
  });
});

describe("applyPendingInterruptToMessages", () => {
  it("creates a new assistant card when mid has no assistant yet", () => {
    const messages: AiMessage[] = [
      {
        id: "u1",
        role: "user",
        mid: "m1",
        blocks: [{ type: "text", content: "开门" }],
        createdAt: 1,
      },
      assistantMsg("a1", [{ type: "text", content: "已开门" }], { mid: "m1" }),
      {
        id: "u2",
        role: "user",
        mid: "m2",
        blocks: [{ type: "text", content: "查告警" }],
        createdAt: 2,
      },
    ];
    const pending: HitlPayload = {
      ...askParamsPayload,
      mid: "m2",
    };
    const out = applyPendingInterruptToMessages(messages, pending);
    expect(out).toHaveLength(4);
    expect(out[3].role).toBe("assistant");
    expect(out[3].mid).toBe("m2");
    expect(out[3].blocks.some((b) => b.type === "interrupt")).toBe(true);
    expect(out[1].blocks.some((b) => b.type === "interrupt")).toBe(false);
  });
});
