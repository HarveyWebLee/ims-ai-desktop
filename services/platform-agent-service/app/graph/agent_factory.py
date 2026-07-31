"""
LangGraph Agent 实例构建与缓存

按 `model_id` 创建（或复用缓存的）可执行 Agent：
- 带工具的 ReAct Agent（create_agent）
- 无工具的纯对话 Agent（chat_direct 节点）
- 父 StateGraph（唯一运行时入口，见 parent_graph.py）

二者共用同一套 checkpointer，保证多轮会话历史可还原。
"""

from __future__ import annotations

from pathlib import Path

from app.persistence.bootstrap import get_checkpointer as _get_persistence_checkpointer

_agent = None
_chat_agent = None
_last_model_id: str | None = None
_last_chat_model_id: str | None = None
_prompt_version: int | None = None
_chat_prompt_version: int | None = None

_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def _get_checkpointer():
    """返回 LangGraph checkpointer（Postgres 或内存）。"""
    return _get_persistence_checkpointer()


def load_system_prompt() -> str:
    from app.services.prompt_assembly import build_system_prompt

    return build_system_prompt()


def load_chat_direct_system_prompt() -> str:
    from app.services.prompt_assembly import build_chat_direct_system_prompt

    return build_chat_direct_system_prompt()


def get_chat_agent(model_id: str):
    """获取或重建「无工具」Chat Agent。"""
    global _chat_agent, _last_chat_model_id, _chat_prompt_version
    from langchain.agents import create_agent

    from app.models.router import resolve_chat_model

    system_prompt = load_chat_direct_system_prompt()
    prompt_version = hash(system_prompt)

    if (
        _chat_agent is not None
        and _last_chat_model_id == model_id
        and _chat_prompt_version == prompt_version
    ):
        return _chat_agent

    model = resolve_chat_model(model_id)
    _chat_agent = create_agent(
        model=model,
        tools=[],
        system_prompt=system_prompt,
        checkpointer=_get_checkpointer(),
    )
    _last_chat_model_id = model_id
    _chat_prompt_version = prompt_version
    return _chat_agent


def get_agent(model_id: str):
    """按 model_id 获取或重建带工具的 create_agent ReAct Agent。"""
    global _agent, _last_model_id, _prompt_version
    from langchain.agents import create_agent

    from app.models.router import resolve_chat_model
    from app.tools.registry import get_agent_tools

    system_prompt = load_system_prompt()
    prompt_version = hash(system_prompt)

    if _agent is not None and _last_model_id == model_id and _prompt_version == prompt_version:
        return _agent

    model = resolve_chat_model(model_id)
    tools = get_agent_tools()
    _agent = create_agent(
        model=model,
        tools=tools,
        system_prompt=system_prompt,
        checkpointer=_get_checkpointer(),
    )
    _last_model_id = model_id
    _prompt_version = prompt_version
    return _agent


def get_parent_graph(model_id: str):
    """编译并缓存父 StateGraph（classify / HITL / plan / react 唯一入口）。"""
    from app.graph.parent_graph import build_parent_graph

    return build_parent_graph(model_id=model_id)


def reset_agent_cache() -> None:
    """清空 Agent 单例缓存。"""
    global _agent, _chat_agent, _last_model_id, _last_chat_model_id
    global _prompt_version, _chat_prompt_version
    _agent = None
    _chat_agent = None
    _last_model_id = None
    _last_chat_model_id = None
    _prompt_version = None
    _chat_prompt_version = None
    try:
        from app.graph.parent_graph import reset_parent_graph_cache

        reset_parent_graph_cache()
    except Exception:  # noqa: BLE001
        pass
    try:
        from app.tools.registry import reset_agent_tools_cache

        reset_agent_tools_cache()
    except Exception:  # noqa: BLE001
        pass
