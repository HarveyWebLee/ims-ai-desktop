"""
工具 schema 两段式（渐进披露）。

官方路径：create_agent + wrap_model_call / wrap_tool_call（见 LangChain Dynamic tool selection）。
- 未解锁：模型只见同名 stub（短描述 + 空参数 schema）
- 同名首调：不调 MCP，回传完整 JSON Schema 并写入 unlocked
- 已解锁：绑完整 schema，走真实工具（含 HITL / hooks）
- chat 新消息：ContextVar 触发 before_agent 清空 unlocked；resume 不触发
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable, Sequence
from contextvars import ContextVar
from typing import Annotated, Any, NotRequired

from langchain.agents.middleware import (
    AgentMiddleware,
    AgentState,
    ModelRequest,
    ModelResponse,
)
from langchain.agents.middleware.types import ToolCallRequest
from langchain_core.messages import ToolMessage
from langchain_core.tools import BaseTool, StructuredTool
from langgraph.types import Command
from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)

# chat 置 True → before_agent 清空 unlocked；resume 置 False
current_schema_phase_reset: ContextVar[bool] = ContextVar(
    "current_schema_phase_reset",
    default=False,
)

# 参数本来就短：始终全量 schema，避免无谓两轮
ALWAYS_FULL_SCHEMA_TOOLS: frozenset[str] = frozenset({"retrieve_knowledge"})

_SHORT_DESC_MAX = 160


class _EmptyToolArgs(BaseModel):
    """未解锁阶段：不向模型暴露业务参数槽。"""

    model_config = ConfigDict(extra="forbid")


def _replace_list(_left: list[str] | None, right: list[str] | None) -> list[str]:
    """允许清空（[]）与整表替换；unlock 时由 middleware 自行合并后写入。"""
    return list(right) if right is not None else []


class SchemaPhaseAgentState(AgentState):
    """create_agent 扩展态：本轮已注入完整 schema 的工具名。"""

    unlocked_tool_names: NotRequired[Annotated[list[str], _replace_list]]


def shorten_tool_description(text: str, *, max_len: int = _SHORT_DESC_MAX) -> str:
    """截取首句/前缀作短描述，控制 bind_tools token。"""
    raw = (text or "").strip()
    if not raw:
        return ""
    cut = raw
    for sep in ("。", "！", "？", ". ", "!\n", "?\n", "\n"):
        if sep in cut:
            head = cut.split(sep, 1)[0].strip()
            if head:
                cut = head + ("。" if sep == "。" else "")
                break
    if len(cut) <= max_len:
        return cut
    return cut[: max_len - 1] + "…"


def tool_args_json_schema(tool: BaseTool) -> dict[str, Any]:
    """提取工具参数 JSON Schema（供解锁回传）。"""
    schema = getattr(tool, "args_schema", None)
    if schema is None:
        return {"type": "object", "properties": {}}
    if isinstance(schema, dict):
        return dict(schema)
    if hasattr(schema, "model_json_schema"):
        return dict(schema.model_json_schema())
    if hasattr(schema, "schema"):
        return dict(schema.schema())
    return {"type": "object", "properties": {}}


def build_schema_stub_tool(full_tool: BaseTool) -> BaseTool:
    """同名 stub：仅名+短描述+空 schema；执行应由 wrap_tool_call 拦截。"""

    name = full_tool.name
    desc = shorten_tool_description(full_tool.description or name)

    def _should_not_run(**_kwargs: Any) -> str:
        return f"工具 {name} 尚未注入完整参数 schema。请等待 schema 回传后再按参数再次调用。"

    return StructuredTool.from_function(
        func=_should_not_run,
        name=name,
        description=desc or name,
        args_schema=_EmptyToolArgs,
    )


def _disclosure_message(tool_name: str, schema: dict[str, Any]) -> str:
    body = json.dumps(schema, ensure_ascii=False, indent=2)
    return (
        f"已选定工具「{tool_name}」。以下为完整参数 JSON Schema；"
        f"请按此 schema 再次调用同名工具（须填写有效参数，勿再传空对象）。\n"
        f"```json\n{body}\n```"
    )


def _merged_unlocked(state: dict[str, Any], tool_name: str) -> list[str]:
    prev = state.get("unlocked_tool_names") or []
    names = {str(x) for x in prev if x}
    names.add(tool_name)
    return sorted(names)


class ToolSchemaPhaseMiddleware(AgentMiddleware[SchemaPhaseAgentState]):
    """按 unlocked 在 stub / 完整工具之间切换；首调解锁不调 MCP。"""

    state_schema = SchemaPhaseAgentState

    def __init__(self, tools: Sequence[BaseTool]) -> None:
        super().__init__()
        self._full_by_name: dict[str, BaseTool] = {t.name: t for t in tools}
        self._stub_by_name: dict[str, BaseTool] = {
            t.name: build_schema_stub_tool(t)
            for t in tools
            if t.name not in ALWAYS_FULL_SCHEMA_TOOLS
        }

    def _select_tools_for_model(self, request: ModelRequest) -> list[BaseTool | dict[str, Any]]:
        unlocked = {str(x) for x in (request.state.get("unlocked_tool_names") or []) if x}
        selected: list[BaseTool | dict[str, Any]] = []
        for tool in request.tools:
            if not isinstance(tool, BaseTool):
                selected.append(tool)
                continue
            name = tool.name
            if name in ALWAYS_FULL_SCHEMA_TOOLS or name in unlocked:
                selected.append(self._full_by_name.get(name, tool))
            else:
                selected.append(self._stub_by_name.get(name, tool))
        return selected

    def before_agent(self, state: SchemaPhaseAgentState, runtime: Any) -> dict[str, Any] | None:
        if current_schema_phase_reset.get():
            logger.debug("tool_schema_phase: reset unlocked on new chat turn")
            return {"unlocked_tool_names": []}
        return None

    async def abefore_agent(
        self, state: SchemaPhaseAgentState, runtime: Any
    ) -> dict[str, Any] | None:
        return self.before_agent(state, runtime)

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        tools = self._select_tools_for_model(request)
        return handler(request.override(tools=tools))

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Any],
    ) -> Any:
        tools = self._select_tools_for_model(request)
        return await handler(request.override(tools=tools))

    def _unlock_or_run(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Any],
    ) -> Any:
        tool_call = request.tool_call
        name = str(tool_call.get("name") or "")
        call_id = str(tool_call.get("id") or "")
        unlocked = {str(x) for x in (request.state.get("unlocked_tool_names") or []) if x}

        if not name or name in ALWAYS_FULL_SCHEMA_TOOLS or name in unlocked:
            full = self._full_by_name.get(name)
            if full is not None:
                return handler(request.override(tool=full))
            return handler(request)

        full = self._full_by_name.get(name)
        schema = (
            tool_args_json_schema(full)
            if full is not None
            else {
                "type": "object",
                "properties": {},
            }
        )
        merged = _merged_unlocked(dict(request.state), name)
        logger.info("tool_schema_phase: unlock tool=%s", name)
        return Command(
            update={
                "unlocked_tool_names": merged,
                "messages": [
                    ToolMessage(
                        content=_disclosure_message(name, schema),
                        tool_call_id=call_id,
                        name=name,
                    )
                ],
            }
        )

    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Any],
    ) -> Any:
        return self._unlock_or_run(request, handler)

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Any],
    ) -> Any:
        tool_call = request.tool_call
        name = str(tool_call.get("name") or "")
        call_id = str(tool_call.get("id") or "")
        unlocked = {str(x) for x in (request.state.get("unlocked_tool_names") or []) if x}

        if not name or name in ALWAYS_FULL_SCHEMA_TOOLS or name in unlocked:
            full = self._full_by_name.get(name)
            if full is not None:
                return await handler(request.override(tool=full))
            return await handler(request)

        full = self._full_by_name.get(name)
        schema = (
            tool_args_json_schema(full)
            if full is not None
            else {
                "type": "object",
                "properties": {},
            }
        )
        merged = _merged_unlocked(dict(request.state), name)
        logger.info("tool_schema_phase: unlock tool=%s", name)
        return Command(
            update={
                "unlocked_tool_names": merged,
                "messages": [
                    ToolMessage(
                        content=_disclosure_message(name, schema),
                        tool_call_id=call_id,
                        name=name,
                    )
                ],
            }
        )


def build_tool_schema_phase_middleware(
    tools: Sequence[BaseTool],
) -> ToolSchemaPhaseMiddleware | None:
    """开关关闭时返回 None，不挂 middleware。"""
    from app.config import settings

    if not settings.agent_tool_schema_twophase:
        return None
    return ToolSchemaPhaseMiddleware(tools)
