"""
执行 Trace 采集服务：记录每轮对话的关键过程时间线。

覆盖：用户输入 → 上下文/被动 RAG / Playbook → LLM 入参摘要 →
工具（MCP / 本地 RAG）起止与参数结果 → 助手回复 → HITL / 结束。

旁听 SSE，不改写业务事件；超长内容截断并脱敏。
"""

from __future__ import annotations

import json
import time
import uuid
from typing import Any

# 截断上限（避免 Postgres JSONB / 面板膨胀）
_USER_MSG_MAX = 2000
_LLM_INPUT_MAX = 8000
_ASSISTANT_MAX = 8000
_TOOL_RESULT_MAX = 4000
_RAG_SNIPPET_MAX = 400
_RAG_BLOCKS_MAX = 8

_LOCAL_TOOLS = frozenset({"retrieve_knowledge"})


def _now_ms() -> int:
    return int(time.time() * 1000)


def _truncate(text: str, limit: int) -> str:
    raw = text or ""
    if len(raw) <= limit:
        return raw
    return raw[: max(0, limit - 1)] + "…"


def _mask_args(args: Any) -> Any:
    """敏感字段脱敏（递归一层 dict）。"""
    if not isinstance(args, dict):
        return args
    masked: dict[str, Any] = {}
    for key, value in args.items():
        lower = str(key).lower()
        if any(s in lower for s in ("password", "token", "secret", "authorization")):
            masked[key] = "***"
        elif isinstance(value, dict):
            masked[key] = _mask_args(value)
        elif isinstance(value, str) and len(value) > 2000:
            masked[key] = _truncate(value, 2000)
        else:
            masked[key] = value
    return masked


def _tool_channel(tool: str) -> str:
    """工具通道：rag / local / mcp。"""
    name = (tool or "").strip()
    if name == "retrieve_knowledge":
        return "rag"
    if name in _LOCAL_TOOLS:
        return "local"
    return "mcp"


def _summarize_rag_blocks(blocks: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for b in (blocks or [])[:_RAG_BLOCKS_MAX]:
        if not isinstance(b, dict):
            continue
        out.append(
            {
                "title": str(b.get("title") or "")[:120],
                "source": str(b.get("source") or "")[:200],
                "score": b.get("score"),
                "text": _truncate(str(b.get("text") or ""), _RAG_SNIPPET_MAX),
            }
        )
    return out


class TraceCollector:
    """
    单轮对话（run）的 trace 事件缓冲器。

    典型事件 kind:
        user_message / context / rag_passive / llm_input /
        assistant_message / plan / tool_start / tool_end /
        interrupt / client_action / replan / error / done
    """

    def __init__(self, *, thread_id: str, run_id: str | None = None) -> None:
        self.thread_id = thread_id
        self.run_id = run_id or str(uuid.uuid4())
        self.events: list[dict[str, Any]] = []
        self.started_at = _now_ms()
        self._assistant_buf: list[str] = []

    def add(
        self,
        kind: str,
        label: str,
        *,
        detail: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        event = {
            "id": str(uuid.uuid4()),
            "ts": _now_ms(),
            "kind": kind,
            "label": label,
            "detail": detail or {},
        }
        self.events.append(event)
        return event

    def record_user_message(self, message: str) -> dict[str, Any]:
        text = _truncate(message or "", _USER_MSG_MAX)
        return self.add(
            "user_message",
            "用户输入",
            detail={"message": text, "char_count": len(message or "")},
        )

    def record_context_snapshot(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        """
        记录本轮组装上下文（被动 RAG / Playbook / 工具子集 / LLM 入参）。

        由 stream_chat 经 ``__obs__`` 事件注入；不向桌面 SSE 透传。
        """
        emitted: list[dict[str, Any]] = []
        rag_blocks = payload.get("passive_rag_blocks")
        skip_rag = bool(payload.get("skip_passive_rag"))
        summarized = _summarize_rag_blocks(rag_blocks if isinstance(rag_blocks, list) else [])
        if summarized:
            emitted.append(
                self.add(
                    "rag_passive",
                    f"被动 RAG（命中 {len(summarized)} 条）",
                    detail={
                        "hit_count": len(summarized),
                        "blocks": summarized,
                        "query": _truncate(str(payload.get("rag_query") or ""), 200),
                    },
                )
            )
        elif skip_rag:
            emitted.append(
                self.add(
                    "rag_passive",
                    "被动 RAG（本轮跳过）",
                    detail={"skipped": True, "reason": "device_control_intent"},
                )
            )
        else:
            emitted.append(
                self.add(
                    "rag_passive",
                    "被动 RAG（无命中）",
                    detail={"hit_count": 0, "skipped": False},
                )
            )

        playbook_ids = payload.get("playbook_ids") or []
        if isinstance(playbook_ids, list) and playbook_ids:
            emitted.append(
                self.add(
                    "context",
                    f"Playbook 注入（{len(playbook_ids)}）",
                    detail={"playbook_ids": playbook_ids},
                )
            )

        tool_names = payload.get("tool_names") or []
        emitted.append(
            self.add(
                "context",
                "本轮编排上下文",
                detail={
                    "model_id": payload.get("model_id") or "",
                    "run_mode": payload.get("run_mode") or "",
                    "tool_subset": tool_names if isinstance(tool_names, list) else [],
                    "tool_subset_strategy": payload.get("tool_subset_strategy") or "",
                    "domains": payload.get("domains") or [],
                },
            )
        )

        llm_input = str(payload.get("llm_user_message") or "")
        emitted.append(
            self.add(
                "llm_input",
                "发送给大模型的本轮用户侧内容",
                detail={
                    "content": _truncate(llm_input, _LLM_INPUT_MAX),
                    "char_count": len(llm_input),
                    "truncated": len(llm_input) > _LLM_INPUT_MAX,
                },
            )
        )
        return emitted

    def record_plan(
        self, steps: list[dict[str, Any]], *, graph: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        detail: dict[str, Any] = {"steps": steps}
        if isinstance(graph, dict):
            detail["graph"] = graph
        return self.add(
            "plan",
            f"任务计划（{len(steps)} 步）",
            detail=detail,
        )

    def note_assistant_delta(self, delta: str) -> None:
        """累积助手流式文本（不立即落盘）。"""
        if delta:
            self._assistant_buf.append(delta)

    def flush_assistant_message(self, *, reason: str = "") -> dict[str, Any] | None:
        """将累积的助手回复落为一条 trace。"""
        if not self._assistant_buf:
            return None
        text = "".join(self._assistant_buf)
        self._assistant_buf.clear()
        if not text.strip():
            return None
        return self.add(
            "assistant_message",
            "大模型回复",
            detail={
                "content": _truncate(text, _ASSISTANT_MAX),
                "char_count": len(text),
                "truncated": len(text) > _ASSISTANT_MAX,
                "flush_reason": reason,
            },
        )

    def record_sse(self, event_name: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        """将 SSE 事件映射为 trace 条目。"""
        if event_name == "message":
            delta = ""
            if isinstance(payload, dict):
                delta = str(payload.get("delta") or payload.get("content") or "")
            self.note_assistant_delta(delta)
            return None

        if event_name == "tool_start":
            tool = str(payload.get("tool", ""))
            channel = _tool_channel(tool)
            args = _mask_args(payload.get("args"))
            label_prefix = {
                "rag": "RAG 工具开始",
                "local": "本地工具开始",
                "mcp": "MCP 工具开始",
            }.get(channel, "工具开始")
            return self.add(
                "tool_start",
                f"{label_prefix}：{tool}",
                detail={
                    "tool": tool,
                    "channel": channel,
                    "args": args,
                    "args_json": _truncate(
                        json.dumps(args, ensure_ascii=False, default=str),
                        3000,
                    ),
                },
            )

        if event_name == "tool_end":
            from app.services.task_planner import parse_tool_result_ok

            tool = str(payload.get("tool", ""))
            channel = _tool_channel(tool)
            result = str(payload.get("result", ""))
            ok, summary = parse_tool_result_ok(result)
            label_prefix = {
                "rag": "RAG 工具完成" if ok else "RAG 工具失败",
                "local": "本地工具完成" if ok else "本地工具失败",
                "mcp": "MCP 工具完成" if ok else "MCP 工具失败",
            }.get(channel, "工具完成" if ok else "工具失败")

            result_obj: Any = None
            try:
                result_obj = json.loads(result) if result.strip().startswith("{") else None
            except json.JSONDecodeError, TypeError:
                result_obj = None

            detail: dict[str, Any] = {
                "tool": tool,
                "channel": channel,
                "ok": ok,
                "summary": _truncate(summary or "", 500),
                "result_preview": _truncate(result, _TOOL_RESULT_MAX),
                "result_truncated": len(result) > _TOOL_RESULT_MAX,
            }
            if isinstance(result_obj, dict):
                # RAG / ToolResult 结构化摘要
                if channel == "rag":
                    detail["rag_mode"] = result_obj.get("mode")
                    detail["rag_summary"] = _truncate(str(result_obj.get("summary") or ""), 1500)
                    sources = result_obj.get("sources") or result_obj.get("hits") or []
                    if isinstance(sources, list):
                        detail["rag_sources"] = [
                            {
                                "title": str(s.get("title") or "")[:120]
                                if isinstance(s, dict)
                                else str(s)[:120],
                                "source": str(s.get("source") or "")[:200]
                                if isinstance(s, dict)
                                else "",
                            }
                            for s in sources[:8]
                        ]
                else:
                    detail["result_ok"] = result_obj.get("ok")
                    detail["result_summary"] = _truncate(str(result_obj.get("summary") or ""), 500)
                    if "data" in result_obj:
                        try:
                            detail["result_data_preview"] = _truncate(
                                json.dumps(result_obj.get("data"), ensure_ascii=False, default=str),
                                2000,
                            )
                        except TypeError, ValueError:
                            pass

            return self.add("tool_end", f"{label_prefix}：{tool}", detail=detail)

        if event_name == "interrupt":
            return self.add(
                "interrupt",
                "等待用户确认/补参",
                detail={"payload": _mask_args(payload) if isinstance(payload, dict) else {}},
            )
        if event_name == "client_action":
            action = payload.get("action", "unknown") if isinstance(payload, dict) else "unknown"
            return self.add(
                "client_action",
                f"客户端动作：{action}",
                detail={"action": payload},
            )
        if event_name == "error":
            return self.add(
                "error",
                str(
                    payload.get("message", "执行错误") if isinstance(payload, dict) else "执行错误"
                ),
                detail=payload if isinstance(payload, dict) else {},
            )
        if event_name == "replan":
            return self.add(
                "replan",
                str((payload or {}).get("reason") if isinstance(payload, dict) else "重新规划")
                or "重新规划",
                detail=payload if isinstance(payload, dict) else {},
            )
        if event_name == "done":
            return self.add(
                "done", "本轮对话结束", detail=payload if isinstance(payload, dict) else {}
            )
        return None

    def export(self) -> dict[str, Any]:
        self.flush_assistant_message(reason="export")
        return {
            "thread_id": self.thread_id,
            "run_id": self.run_id,
            "started_at": self.started_at,
            "ended_at": _now_ms(),
            "events": self.events,
        }
