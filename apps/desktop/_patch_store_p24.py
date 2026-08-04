from pathlib import Path
import re

path = Path("e:/WORK/CODE/ims-ai-desktop/apps/desktop/src/components/AiAssistant/store.ts")
text = path.read_text(encoding="utf-8")

old_import = (
    'import type { AiMessage, AiSession, HitlPayload } from "./types";\n'
    'import { reconcilePlanStepsWithToolBlocks } from "./utils/planGraphUtils";'
)
new_import = (
    'import type { AiMessage, AiSession, HitlPayload } from "./types";\n'
    "import {\n"
    "  getMessageWriteThreadId,\n"
    "  type ThreadSnapshot,\n"
    '} from "./threadRuntime";\n'
    'import { reconcilePlanStepsWithToolBlocks } from "./utils/planGraphUtils";'
)
if old_import not in text:
    raise SystemExit("import block not found")
text = text.replace(old_import, new_import, 1)

helper = r'''
/** 读取写入目标 thread 的消息列表（当前会话或后台快照） */
function baseMessagesForWrite(s: {
  currentThreadId: string;
  messages: AiMessage[];
  threadSnapshots: Record<string, ThreadSnapshot>;
}): { threadId: string; messages: AiMessage[]; isCurrent: boolean } {
  const threadId = getMessageWriteThreadId(s.currentThreadId);
  const isCurrent = threadId === s.currentThreadId;
  const messages = isCurrent
    ? s.messages
    : (s.threadSnapshots[threadId]?.messages ?? []);
  return { threadId, messages, isCurrent };
}

function commitThreadMessages(
  s: {
    currentThreadId: string;
    messages: AiMessage[];
    pendingInterrupt: HitlPayload | null;
    threadSnapshots: Record<string, ThreadSnapshot>;
  },
  threadId: string,
  messages: AiMessage[],
  extra?: Record<string, unknown>,
): Record<string, unknown> {
  const isCurrent = threadId === s.currentThreadId;
  const prev = s.threadSnapshots[threadId];
  let pending = prev?.pendingInterrupt ?? null;
  if (isCurrent) {
    pending =
      extra && "pendingInterrupt" in extra
        ? (extra["pendingInterrupt"] as HitlPayload | null)
        : s.pendingInterrupt;
  } else if (extra && "pendingInterrupt" in extra) {
    pending = extra["pendingInterrupt"] as HitlPayload | null;
  }
  const threadSnapshots = {
    ...s.threadSnapshots,
    [threadId]: { messages, pendingInterrupt: pending },
  };
  if (isCurrent) {
    return { messages, threadSnapshots, ...(extra ?? {}) };
  }
  return { threadSnapshots, ...(extra ?? {}) };
}

'''

anchor = "/** 助手消息上可局部更新的元数据字段 */"
if anchor not in text:
    raise SystemExit("anchor not found")
text = text.replace(anchor, helper + anchor, 1)

old_iface = (
    "  messages: AiMessage[];\n"
    "  isStreaming: boolean;\n"
    "  /** 正在拉取历史会话消息（切换会话期间不展示欢迎空态） */\n"
    "  isLoadingHistory: boolean;"
)
new_iface = (
    "  messages: AiMessage[];\n"
    "  isStreaming: boolean;\n"
    "  /** P2-4：各 thread 是否仍有进行中的 SSE */\n"
    "  streamingByThread: Record<string, boolean>;\n"
    "  /** P2-4：切走会话时缓存消息 / HITL，供后台流继续写入与切回恢复 */\n"
    "  threadSnapshots: Record<string, ThreadSnapshot>;\n"
    "  /** 正在拉取历史会话消息（切换会话期间不展示欢迎空态） */\n"
    "  isLoadingHistory: boolean;"
)
if old_iface not in text:
    raise SystemExit("iface fields not found")
text = text.replace(old_iface, new_iface, 1)

old_methods = (
    "  createNewSession: () => string;\n"
    "  switchSession: (threadId: string) => void;\n"
    "  setSessions: (sessions: AiSession[]) => void;\n"
    "  setMessages: (messages: AiMessage[]) => void;"
)
new_methods = (
    "  createNewSession: () => string;\n"
    "  switchSession: (threadId: string) => void;\n"
    "  /** 当前或指定 thread 是否 streaming */\n"
    "  isThreadStreaming: (threadId?: string) => boolean;\n"
    "  /** 切会话前是否已有可恢复快照（有消息或仍在流式） */\n"
    "  hasThreadSnapshot: (threadId: string) => boolean;\n"
    "  clearThreadSnapshot: (threadId: string) => void;\n"
    "  setSessions: (sessions: AiSession[]) => void;\n"
    "  setMessages: (messages: AiMessage[]) => void;"
)
if old_methods not in text:
    raise SystemExit("methods not found")
text = text.replace(old_methods, new_methods, 1)

old_init = (
    "      messages: [],\n"
    "      isStreaming: false,\n"
    "      isLoadingHistory: false,"
)
new_init = (
    "      messages: [],\n"
    "      isStreaming: false,\n"
    "      streamingByThread: {},\n"
    "      threadSnapshots: {},\n"
    "      isLoadingHistory: false,"
)
text = text.replace(old_init, new_init, 1)

old_create = r'''      createNewSession: () => {
        const threadId = uuidv4();
        set({
          currentThreadId: threadId,
          messages: [],
          pendingInterrupt: null,
          isLoadingHistory: false,
        });
        return threadId;
      },

      switchSession: (threadId) =>
        set({
          currentThreadId: threadId,
          messages: [],
          pendingInterrupt: null,
          isLoadingHistory: true,
        }),

      setSessions: (sessions) => set({ sessions }),

      setMessages: (messages) => set({ messages }),'''

new_create = r'''      createNewSession: () => {
        const threadId = uuidv4();
        set((s) => {
          const snapshots = { ...s.threadSnapshots };
          snapshots[s.currentThreadId] = {
            messages: s.messages,
            pendingInterrupt: s.pendingInterrupt,
          };
          return {
            threadSnapshots: snapshots,
            currentThreadId: threadId,
            messages: [],
            pendingInterrupt: null,
            isStreaming: Boolean(s.streamingByThread[threadId]),
            isLoadingHistory: false,
          };
        });
        return threadId;
      },

      switchSession: (threadId) =>
        set((s) => {
          if (threadId === s.currentThreadId) return s;
          const snapshots = { ...s.threadSnapshots };
          snapshots[s.currentThreadId] = {
            messages: s.messages,
            pendingInterrupt: s.pendingInterrupt,
          };
          const target = snapshots[threadId];
          const hasCache =
            Boolean(target && target.messages.length > 0) ||
            Boolean(s.streamingByThread[threadId]);
          return {
            threadSnapshots: snapshots,
            currentThreadId: threadId,
            messages: target?.messages ?? [],
            pendingInterrupt: target?.pendingInterrupt ?? null,
            isStreaming: Boolean(s.streamingByThread[threadId]),
            // 有快照或后台仍在流：不拉历史，避免冲掉进行中气泡
            isLoadingHistory: !hasCache,
          };
        }),

      isThreadStreaming: (threadId) => {
        const s = useAiAssistantStore.getState();
        const tid = threadId ?? s.currentThreadId;
        return Boolean(s.streamingByThread[tid]);
      },

      hasThreadSnapshot: (threadId) => {
        const s = useAiAssistantStore.getState();
        const snap = s.threadSnapshots[threadId];
        return Boolean(
          (snap && snap.messages.length > 0) || s.streamingByThread[threadId],
        );
      },

      clearThreadSnapshot: (threadId) =>
        set((s) => {
          if (!(threadId in s.threadSnapshots) && !(threadId in s.streamingByThread)) {
            return s;
          }
          const threadSnapshots = { ...s.threadSnapshots };
          delete threadSnapshots[threadId];
          const streamingByThread = { ...s.streamingByThread };
          delete streamingByThread[threadId];
          return {
            threadSnapshots,
            streamingByThread,
            isStreaming:
              threadId === s.currentThreadId
                ? false
                : Boolean(streamingByThread[s.currentThreadId]),
          };
        }),

      setSessions: (sessions) => set({ sessions }),

      setMessages: (messages) =>
        set((s) => {
          const tid = getMessageWriteThreadId(s.currentThreadId);
          return commitThreadMessages(s, tid, messages);
        }),'''

if old_create not in text:
    raise SystemExit("create/switch block not found")
text = text.replace(old_create, new_create, 1)

old_add = r'''      addUserMessage: (content) => {
        const id = uuidv4();
        const msg: AiMessage = {
          id,
          role: "user",
          blocks: [{ type: "text", content }],
          createdAt: Date.now(),
        };
        set((s) => ({ messages: [...s.messages, msg] }));
        return id;
      },'''

new_add = r'''      addUserMessage: (content) => {
        const id = uuidv4();
        const msg: AiMessage = {
          id,
          role: "user",
          blocks: [{ type: "text", content }],
          createdAt: Date.now(),
        };
        set((s) => {
          const { threadId, messages } = baseMessagesForWrite(s);
          return commitThreadMessages(s, threadId, [...messages, msg]);
        });
        return id;
      },'''
if old_add not in text:
    raise SystemExit("addUserMessage not found")
text = text.replace(old_add, new_add, 1)

# Wrap all remaining `set((s) => ({ messages: s.messages.map(...)}))`
pattern = re.compile(
    r"set\(\(s\) => \(\{\n( +)messages: s\.messages\.map\((.*?)\n\1\}\)\),?\n\1\}\)",
    re.DOTALL,
)


def repl(m: re.Match) -> str:
    indent = m.group(1)
    inner = m.group(2)
    # inner ends with `)` of map( before `,\n`
    # The regex captured up to newline before closing `})`
    # Reconstruct carefully — original was:
    # set((s) => ({
    #   messages: s.messages.map(....),
    # }))
    return (
        f"set((s) => {{\n"
        f"{indent}const {{ threadId, messages: base }} = baseMessagesForWrite(s);\n"
        f"{indent}const messages = base.map({inner}\n"
        f"{indent}return commitThreadMessages(s, threadId, messages);\n"
        f"{indent}}})"
    )


text2, n = pattern.subn(repl, text)
print("wrapped map mutators:", n)

old_stream = (
    "      setStreaming: (streaming) => set({ isStreaming: streaming }),\n"
    "      setPendingInterrupt: (payload) => set({ pendingInterrupt: payload }),"
)
new_stream = r'''      setStreaming: (streaming) =>
        set((s) => {
          const tid = getMessageWriteThreadId(s.currentThreadId);
          const streamingByThread = { ...s.streamingByThread };
          if (streaming) {
            streamingByThread[tid] = true;
          } else {
            delete streamingByThread[tid];
          }
          return {
            streamingByThread,
            isStreaming: Boolean(streamingByThread[s.currentThreadId]),
          };
        }),
      setPendingInterrupt: (payload) =>
        set((s) => {
          const tid = getMessageWriteThreadId(s.currentThreadId);
          const isCurrent = tid === s.currentThreadId;
          const prev = s.threadSnapshots[tid];
          const messages = isCurrent ? s.messages : (prev?.messages ?? []);
          const threadSnapshots = {
            ...s.threadSnapshots,
            [tid]: { messages, pendingInterrupt: payload },
          };
          if (isCurrent) {
            return { pendingInterrupt: payload, threadSnapshots };
          }
          return { threadSnapshots };
        }),'''
if old_stream not in text2:
    raise SystemExit("streaming block not found")
text2 = text2.replace(old_stream, new_stream, 1)

path.write_text(text2, encoding="utf-8")
print("ok commits", text2.count("commitThreadMessages"))
print("base", text2.count("baseMessagesForWrite"))
