import { describe, expect, it } from "vitest";

import type { PlanStep } from "@ims/shared-types";
import type { FlowDocumentJSON } from "@/components/BpmnFlowgram";
import type { AiMessage } from "../types";
import {
  applyBpmnSnapshotToMessages,
  enrichMessagesWithTraceRuns,
  findPlanOwnerMessageIndex,
} from "./enrichHistoryWithTrace";

const bpmnDoc = {
  nodes: [
    { id: "1", type: "AUTO", data: { title: "查询", tool: "query_alarms" } },
    { id: "2", type: "AUTO", data: { title: "导出", tool: "download_file" } },
  ],
  edges: [],
} as unknown as FlowDocumentJSON;

const planSteps: PlanStep[] = [
  { id: "1", label: "查询告警", tool: "query_alarms", status: "done" },
  { id: "2", label: "导出报表", tool: "download_file", status: "skipped" },
];

function assistantMessage(partial?: Partial<AiMessage>): AiMessage {
  return {
    id: partial?.id ?? "a1",
    role: "assistant",
    blocks: [{ type: "text", content: "ok" }],
    createdAt: 1,
    planSteps,
    planFlowDocument: bpmnDoc,
    ...partial,
  };
}

function userMessage(id: string): AiMessage {
  return {
    id,
    role: "user",
    blocks: [{ type: "text", content: "hello" }],
    createdAt: 1,
  };
}

describe("enrichMessagesWithTraceRuns", () => {
  it("does not wipe planFlowDocument when trace plan lacks flow_document", () => {
    const messages: AiMessage[] = [assistantMessage()];
    const enriched = enrichMessagesWithTraceRuns(messages, [
      {
        run_id: "run-1",
        events: [],
        plan_snapshot: {
          steps: planSteps,
          graph: { nodes: [], edges: [], mermaid: "" },
        },
      },
    ]);
    expect(enriched[0].planFlowDocument).toEqual(bpmnDoc);
    expect(enriched[0].planSteps).toEqual(planSteps);
  });

  it("uses trace flow_document when snapshot provides it", () => {
    const traceDoc = {
      nodes: [
        {
          id: "2",
          type: "AUTO",
          data: { title: "导出", tool: "download_file" },
        },
      ],
      edges: [],
    } as unknown as FlowDocumentJSON;
    const messages: AiMessage[] = [assistantMessage({ planFlowDocument: bpmnDoc })];
    const enriched = enrichMessagesWithTraceRuns(messages, [
      {
        run_id: "run-1",
        events: [],
        plan_snapshot: {
          steps: [{ id: "2", label: "导出", tool: "download_file", status: "done" }],
          flow_document: traceDoc,
        },
      },
    ]);
    expect(enriched[0].planFlowDocument).toEqual(traceDoc);
  });
});

describe("findPlanOwnerMessageIndex", () => {
  it("prefers assistant with plan_confirm interrupt over last assistant", () => {
    const messages: AiMessage[] = [
      userMessage("u1"),
      assistantMessage({
        id: "a1",
        planSteps: undefined,
        planFlowDocument: null,
      }),
      userMessage("u2"),
      assistantMessage({
        id: "a2",
        blocks: [
          {
            type: "interrupt",
            payload: {
              type: "plan_confirm",
              tool: "plan_confirm",
              message: "confirm",
              steps: planSteps,
            },
          },
        ],
      }),
      userMessage("u3"),
      assistantMessage({
        id: "a3",
        planSteps: undefined,
        planFlowDocument: null,
        blocks: [{ type: "text", content: "后续闲聊" }],
      }),
    ];

    expect(findPlanOwnerMessageIndex(messages, { steps: planSteps })).toBe(3);
  });

  it("matches by step overlap in multi-turn when no interrupt remains", () => {
    const messages: AiMessage[] = [
      userMessage("u1"),
      assistantMessage({
        id: "a1",
        planSteps: undefined,
        planFlowDocument: null,
        blocks: [{ type: "text", content: "你好" }],
      }),
      userMessage("u2"),
      assistantMessage({
        id: "a2",
        planSteps,
        planFlowDocument: null,
      }),
      userMessage("u3"),
      assistantMessage({
        id: "a3",
        planSteps: undefined,
        planFlowDocument: null,
        blocks: [{ type: "text", content: "谢谢" }],
      }),
    ];

    expect(findPlanOwnerMessageIndex(messages, { steps: planSteps })).toBe(3);
  });
});

describe("applyBpmnSnapshotToMessages", () => {
  it("attaches bpmn snapshot to plan owner not last assistant", () => {
    const messages: AiMessage[] = [
      userMessage("u1"),
      assistantMessage({
        id: "a1",
        planSteps: undefined,
        planFlowDocument: null,
      }),
      userMessage("u2"),
      assistantMessage({
        id: "a2",
        planSteps,
        planFlowDocument: null,
      }),
      userMessage("u3"),
      assistantMessage({
        id: "a3",
        planSteps: undefined,
        planFlowDocument: null,
        blocks: [{ type: "text", content: "后续回复" }],
      }),
    ];

    const result = applyBpmnSnapshotToMessages(messages, {
      steps: planSteps,
      flow_document: bpmnDoc,
    });

    expect(result[1].planFlowDocument).toBeNull();
    expect(result[3].planFlowDocument).toEqual(bpmnDoc);
    expect(result[3].planSteps).toEqual(planSteps);
    expect(result[5].planFlowDocument).toBeNull();
  });

  it("does not attach when no plan owner exists", () => {
    const messages: AiMessage[] = [
      userMessage("u1"),
      assistantMessage({
        id: "a1",
        planSteps: undefined,
        planFlowDocument: null,
        blocks: [{ type: "text", content: "纯对话" }],
      }),
    ];

    const result = applyBpmnSnapshotToMessages(messages, {
      steps: planSteps,
      flow_document: bpmnDoc,
    });

    expect(result).toEqual(messages);
  });
});
