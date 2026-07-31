/**
 * 将服务端 thread state 消息映射为前端 AiMessage 结构
 */
import { v4 as uuidv4 } from "uuid";
import type { ClientAction } from "@ims/shared-types";
import type { AiMessage, AiMessageBlock } from "../types";
import { extractUserDisplayText } from "./extractUserDisplayText";
import { resolveWorkspaceFromMessage } from "./workspaceFromTool";

/** 服务端返回的单条历史消息 */
export interface ThreadHistoryMessage {
  role: string;
  /** 新版：结构化 blocks */
  blocks?: AiMessageBlock[];
  /** 旧版兼容：纯文本 */
  content?: string;
}

function normalizeUserTextContent(content: string): string {
  return extractUserDisplayText(content);
}

function normalizeBlock(raw: Record<string, unknown>): AiMessageBlock | null {
  const type = raw.type as string;
  if (type === "text" && typeof raw.content === "string") {
    return { type: "text", content: normalizeUserTextContent(raw.content) };
  }
  if (type === "tool_call" && typeof raw.tool === "string") {
    return {
      type: "tool_call",
      tool: raw.tool,
      args: (raw.args as Record<string, unknown>) || {},
      status: (raw.status as "done") || "done",
      result: typeof raw.result === "string" ? raw.result : undefined,
    };
  }
  if (type === "client_action" && raw.action) {
    return {
      type: "client_action",
      action: raw.action as ClientAction,
      status: (raw.status as "done") || "done",
    };
  }
  if (type === "interrupt" && raw.payload) {
    return {
      type: "interrupt",
      payload: raw.payload as AiMessageBlock extends { type: "interrupt" }
        ? AiMessageBlock["payload"]
        : never,
    };
  }
  // 旧版纯文本 assistant 消息
  if (typeof raw.content === "string") {
    return { type: "text", content: raw.content };
  }
  return null;
}

/** 历史消息 → 聊天卡片列表 */
export function mapHistoryToMessages(history: ThreadHistoryMessage[]): AiMessage[] {
  const result: AiMessage[] = [];

  for (const item of history) {
    const role = item.role === "user" ? "user" : "assistant";
    let blocks: AiMessageBlock[] = [];

    if (Array.isArray(item.blocks) && item.blocks.length) {
      blocks =
        role === "user"
          ? item.blocks.map((block) => {
              if (block.type === "text" && typeof block.content === "string") {
                return {
                  ...block,
                  content: normalizeUserTextContent(block.content),
                };
              }
              return block;
            })
          : item.blocks;
    } else if (item.content) {
      blocks = [
        {
          type: "text",
          content: role === "user" ? normalizeUserTextContent(item.content) : item.content,
        },
      ];
    } else if (Array.isArray(item.blocks)) {
      blocks = (item.blocks as Record<string, unknown>[])
        .map((b) => normalizeBlock(b))
        .filter((b): b is AiMessageBlock => b != null);
    }

    if (!blocks.length) continue;

    const message: AiMessage = {
      id: uuidv4(),
      role,
      blocks,
      createdAt: Date.now(),
    };

    if (role === "assistant") {
      const workspaceContent = resolveWorkspaceFromMessage(message);
      if (workspaceContent) {
        message.workspaceContent = workspaceContent;
      }
    }

    result.push(message);
  }

  return result;
}
