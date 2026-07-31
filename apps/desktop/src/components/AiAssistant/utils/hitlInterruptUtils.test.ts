import { describe, expect, it } from "vitest";
import type { HitlPayload } from "@ims/shared-types";
import type { AiMessage, AiMessageBlock } from "../types";
import {
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
