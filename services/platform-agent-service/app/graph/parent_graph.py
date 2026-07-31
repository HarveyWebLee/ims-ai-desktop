"""
父 StateGraph：classify / plan_confirm / device / plan / BPMN / react 唯一运行时入口。

拓扑（与 docs/architecture/03-agent-runtime.md 对齐）::

    START → classify
      ├─ chat_direct   → create_agent(tools=[]) → END   # AGENT_INTENT_AI_FIRST=false
      ├─ device_gate   → interrupt(ask_params) → react | END
      ├─ plan_confirm  → interrupt(plan_confirm) → plan_execute | bpmn_execute | END
      └─ react         → create_agent(tools=MCP) → END  # AGENT_INTENT_AI_FIRST=true 时恒走此路
"""

from __future__ import annotations

import json
import logging
from typing import Annotated, Any, Literal

from langchain_core.messages import AIMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from app.graph.context import AgentContext
from app.graph.router import TaskRoute, classify_task
from contracts.hitl import is_hitl_approve, is_hitl_reject, merge_hitl_resume_args

logger = logging.getLogger(__name__)

RouteKind = Literal[
    "chat_direct",
    "device_gate",
    "plan_confirm",
    "plan_execute",
    "bpmn_execute",
    "react",
    "end",
]

_parent_graph_cache: dict[str, Any] = {}


class ParentState(TypedDict, total=False):
    """父图状态：路由字段 + messages（与 create_agent 子图共享）。"""

    messages: Annotated[list, add_messages]
    route: RouteKind
    user_message: str
    llm_user_message: str
    model_id: str
    metadata: dict[str, Any]
    plan_steps: list[dict[str, Any]]
    plan_params: dict[str, dict[str, Any]]
    flow_document: dict[str, Any] | None
    plan_graph: dict[str, Any] | None
    plan_confirm_payload: dict[str, Any] | None
    device_interrupt_payload: dict[str, Any] | None
    device_tool_args: dict[str, Any]
    cancelled: bool
    cancel_message: str


def _ctx_from_state(state: ParentState) -> AgentContext:
    return AgentContext(
        thread_id="",
        message=str(state.get("user_message") or ""),
        llm_user_message=str(state.get("llm_user_message") or state.get("user_message") or ""),
        metadata=dict(state.get("metadata") or {}),
    )


async def classify_node(state: ParentState) -> dict[str, Any]:
    """意图路由 + Plan/设备门控预判，写入下一跳 route。

    ``AGENT_INTENT_AI_FIRST=true``（默认）时旁路门控，恒路由 ``react``；
    ``false`` 时保留 chat_direct / plan_confirm / device_gate 原路径。
    """
    from app.config import settings

    if settings.agent_intent_ai_first:
        return {"route": "react"}

    ctx = _ctx_from_state(state)
    base_route = classify_task(ctx)
    model_id = str(state.get("model_id") or "")

    if base_route == TaskRoute.CHAT:
        return {"route": "chat_direct"}

    from app.services.device_control_gate import prepare_device_control_hitl_gate
    from app.services.plan_confirm import prepare_plan_confirm_gate_async

    plan_gate = await prepare_plan_confirm_gate_async(ctx, model_id=model_id)
    if plan_gate is not None:
        return {
            "route": "plan_confirm",
            "plan_steps": plan_gate.steps,
            "plan_params": plan_gate.params_by_tool,
            "plan_graph": plan_gate.interrupt_payload.get("graph"),
            "flow_document": plan_gate.interrupt_payload.get("flow_document"),
            "plan_confirm_payload": plan_gate.interrupt_payload,
        }

    device_gate = prepare_device_control_hitl_gate(ctx, model_id=model_id)
    if device_gate is not None:
        return {
            "route": "device_gate",
            "device_interrupt_payload": device_gate.interrupt_payload,
            "device_tool_args": device_gate.tool_args,
        }

    return {"route": "react"}


def _route_after_classify(state: ParentState) -> RouteKind:
    return state.get("route") or "react"  # type: ignore[return-value]


def resolve_post_confirm_execution_route(flow_document: Any) -> RouteKind:
    """
    plan_confirm 批准后的执行路由。

    - 灰度 ``AGENT_BPMN_CONDITION_EXEC=true`` 且画布含可执行 CONDITION → ``bpmn_execute``
    - 否则线性 ``plan_execute``（与 flag 关闭行为一致）
    """
    from app.application.execution.bpmn_graph import flow_document_has_executable_conditions
    from app.config import settings

    if (
        isinstance(flow_document, dict)
        and settings.agent_bpmn_condition_exec
        and flow_document_has_executable_conditions(flow_document)
    ):
        return "bpmn_execute"
    return "plan_execute"


def plan_confirm_node(state: ParentState) -> dict[str, Any]:
    """多步 Plan 确认：图内 interrupt，resume 后写入执行参数或取消。"""
    from app.graph.hitl_interrupt import interrupt_or_raise
    from app.services.bpmn_orchestration import build_bpmn_snapshot
    from app.services.plan_graph import normalize_approved_plan_steps
    from app.services.session_store import set_thread_bpmn_snapshot

    payload = dict(state.get("plan_confirm_payload") or {})
    resume_value = interrupt_or_raise(payload)

    if is_hitl_reject(resume_value):
        return {
            "route": "end",
            "cancelled": True,
            "cancel_message": "已取消执行计划。如需调整，请重新描述您的需求。",
            "messages": [AIMessage(content="已取消执行计划。如需调整，请重新描述您的需求。")],
        }

    steps = list(state.get("plan_steps") or [])
    params_by_tool = dict(state.get("plan_params") or {})
    flow_document = state.get("flow_document")
    user_message = str(state.get("user_message") or "")

    if is_hitl_approve(resume_value) and isinstance(resume_value, dict):
        from langgraph.config import get_config

        from app.services.bpmn_orchestration import (
            flow_document_to_plan_steps,
            merge_bpmn_steps_with_previous,
        )
        from app.services.plan_confirm import merge_plan_params, propagate_query_alarm_filter_params

        user_steps = resume_value.get("steps")
        user_graph = resume_value.get("graph")
        user_flow_doc = resume_value.get("flow_document")
        pending_steps = list(steps)

        if isinstance(user_flow_doc, dict):
            extracted = flow_document_to_plan_steps(user_flow_doc)
            user_steps = merge_bpmn_steps_with_previous(extracted, pending_steps)
        elif isinstance(user_steps, list) and user_steps:
            user_steps = merge_bpmn_steps_with_previous(user_steps, pending_steps)

        if isinstance(user_steps, list) and user_steps:
            steps = normalize_approved_plan_steps(user_steps)
            active_tools = {str(s.get("tool") or "") for s in steps if s.get("tool")}
            inferred = merge_plan_params(user_message, steps)
            merged_params: dict[str, dict[str, Any]] = {}
            for tool in active_tools:
                base = {**dict(inferred.get(tool) or {}), **dict(params_by_tool.get(tool) or {})}
                if base:
                    merged_params[tool] = base
            params_by_tool = merged_params
            propagate_query_alarm_filter_params(params_by_tool, steps)
            if isinstance(resume_value.get("params_by_tool"), dict):
                for tool, raw in resume_value["params_by_tool"].items():
                    if isinstance(raw, dict):
                        base = dict(params_by_tool.get(tool) or {})
                        base.update(raw)
                        params_by_tool[tool] = base

        if isinstance(user_flow_doc, dict):
            flow_document = user_flow_doc
        if isinstance(user_graph, dict):
            plan_graph = user_graph
        else:
            plan_graph = state.get("plan_graph")

        thread_id = str(get_config().get("configurable", {}).get("thread_id") or "")
        if thread_id:
            set_thread_bpmn_snapshot(
                thread_id,
                build_bpmn_snapshot(
                    steps=steps,
                    flow_document=flow_document if isinstance(flow_document, dict) else None,
                    graph=plan_graph if isinstance(plan_graph, dict) else None,
                ),
            )

    for step in steps:
        if str(step.get("status")) == "awaiting_confirm":
            step["status"] = "pending"

    next_route = resolve_post_confirm_execution_route(flow_document)

    return {
        "route": next_route,
        "plan_steps": steps,
        "plan_params": params_by_tool,
        "flow_document": flow_document,
    }


async def device_gate_node(state: ParentState) -> dict[str, Any]:
    """设备控制缺槽：图内 interrupt(ask_params)，批准后执行并结束（结构化结果不依赖 LLM 复述）。"""
    from langgraph.config import get_stream_writer

    from app.graph.hitl_interrupt import interrupt_or_raise
    from app.mcp.client import get_mcp_pipeline_tools_sync

    payload = dict(state.get("device_interrupt_payload") or {})
    tool_args = dict(state.get("device_tool_args") or {})
    resume_value = interrupt_or_raise(payload)

    if is_hitl_reject(resume_value):
        return {
            "route": "end",
            "cancelled": True,
            "cancel_message": "已取消操作。如需调整，请重新描述您的需求。",
            "messages": [AIMessage(content="已取消操作。如需调整，请重新描述您的需求。")],
        }

    merged = merge_hitl_resume_args(resume_value, tool_args)
    tool_name = str(payload.get("tool") or "send_device_cmd")
    tools = {t.name: t for t in get_mcp_pipeline_tools_sync()}
    tool = tools.get(tool_name)
    if tool is None:
        return {
            "route": "end",
            "messages": [AIMessage(content=f"工具不可用：{tool_name}")],
        }

    writer = get_stream_writer()
    writer({"sse_event": "tool_start", "tool": tool_name, "args": merged})

    # 工具包装器内 interrupt + bypass 由 MCP client 处理
    raw = await tool.ainvoke(merged)
    result_text = raw if isinstance(raw, str) else str(raw)
    writer({"sse_event": "tool_end", "tool": tool_name, "result": result_text})

    # 用户可见文案仅用 summary，禁止把原始 ToolResult JSON 注入对话（与模型无关）
    reply = _format_device_command_reply(result_text, tool_name=tool_name)
    return {
        "route": "end",
        "messages": [AIMessage(content=reply)],
    }


def _format_device_command_reply(result_text: str, *, tool_name: str) -> str:
    """从 ToolResult JSON 生成面向值班员的短回复（不含原始 JSON）。"""
    try:
        data = json.loads(result_text)
    except json.JSONDecodeError, TypeError:
        text = (result_text or "").strip()
        return text[:300] if text else f"设备指令 `{tool_name}` 已处理。"

    if not isinstance(data, dict):
        return f"设备指令 `{tool_name}` 已处理。"

    summary = str(data.get("summary") or "").strip()
    ok = bool(data.get("ok"))
    if summary:
        return summary
    if data.get("user_cancelled"):
        return "已取消设备指令下发。"
    return "设备指令下发成功。" if ok else "设备指令下发失败，请检查参数后重试。"


async def plan_execute_node(state: ParentState) -> dict[str, Any]:
    """逐步执行 Plan：委托 ``execute_plan_steps``（失败 Re-plan + retry 标记）。

    HITL 仍仅经 MCP 工具包装器内 ``interrupt``；业务失败（ok=false）走图内
    ``retry_policy`` / ``build_replan_after_failure``，禁止图外 pending。
    """
    from langgraph.config import get_stream_writer

    from app.application.execution.plan_runner import execute_plan_steps
    from app.mcp.client import get_mcp_pipeline_tools_sync
    from contracts.context import current_auth_token, current_thread_id

    writer = get_stream_writer()
    steps = list(state.get("plan_steps") or [])
    params_by_tool = dict(state.get("plan_params") or {})
    user_message = str(state.get("user_message") or "")
    thread_id = str(state.get("thread_id") or current_thread_id.get() or "")
    auth_token = current_auth_token.get()
    tools = {t.name: t for t in get_mcp_pipeline_tools_sync()}

    # awaiting_confirm → pending，便于 execute_plan_steps 纳入执行
    for step in steps:
        if str(step.get("status")) == "awaiting_confirm":
            step["status"] = "pending"

    async def _stream_step(
        step: dict[str, Any],
        params: dict[str, Any],
        _user_message: str,
    ):
        tool_name = str(step.get("tool") or "")
        tool = tools.get(tool_name)
        if tool is None:
            yield (
                "tool_start",
                {"tool": tool_name, "args": params},
            )
            yield (
                "tool_end",
                {
                    "tool": tool_name,
                    "result": json.dumps(
                        {
                            "ok": False,
                            "summary": f"工具不可用：{tool_name}",
                            "data": {"tool": tool_name},
                        },
                        ensure_ascii=False,
                    ),
                },
            )
            return

        yield ("tool_start", {"tool": tool_name, "args": params})
        try:
            raw = await tool.ainvoke(params)
            result = raw if isinstance(raw, str) else str(raw)
        except Exception as exc:  # noqa: BLE001
            from langgraph.errors import GraphInterrupt

            from contracts.hitl import McpHitlSignal

            if isinstance(exc, (GraphInterrupt, McpHitlSignal)):
                raise
            result = json.dumps(
                {"ok": False, "summary": str(exc), "data": {"tool": tool_name}},
                ensure_ascii=False,
            )
        yield ("tool_end", {"tool": tool_name, "result": result})

    summaries: list[str] = []
    text_parts: list[str] = []
    async for event_name, payload in execute_plan_steps(
        steps,
        params_by_tool,
        user_message,
        thread_id=thread_id,
        auth_token=auth_token,
        stream_step=_stream_step,
    ):
        if event_name == "interrupt":
            from app.graph.hitl_interrupt import interrupt_or_raise

            interrupt_or_raise(payload if isinstance(payload, dict) else {})
            return {"route": "end", "plan_steps": steps, "plan_params": params_by_tool}

        if event_name in ("tool_start", "tool_end", "replan", "message"):
            custom: dict[str, Any] = {"sse_event": event_name}
            if isinstance(payload, dict):
                custom.update(payload)
            writer(custom)

        if event_name == "tool_end" and isinstance(payload, dict):
            tool_name = str(payload.get("tool") or "")
            raw = str(payload.get("result") or "")
            try:
                data = json.loads(raw)
                summary = (
                    str(data.get("summary") or raw[:120]) if isinstance(data, dict) else raw[:120]
                )
            except json.JSONDecodeError, TypeError:
                summary = raw[:120]
            label = next(
                (str(s.get("label") or tool_name) for s in steps if s.get("tool") == tool_name),
                tool_name,
            )
            summaries.append(f"- {label}：{summary}")

        if event_name == "message" and isinstance(payload, dict):
            delta = payload.get("delta")
            if delta:
                text_parts.append(str(delta))

        if event_name == "error":
            writer({"sse_event": "error", **(payload if isinstance(payload, dict) else {})})
            return {
                "route": "end",
                "plan_steps": steps,
                "plan_params": params_by_tool,
                "messages": [
                    AIMessage(content=str((payload or {}).get("message") or "计划执行失败"))
                ],
            }

    if text_parts:
        text = "".join(text_parts).strip()
    elif summaries:
        text = "计划执行完成。\n" + "\n".join(summaries)
    else:
        text = "计划执行完成。"
    return {
        "route": "end",
        "plan_steps": steps,
        "plan_params": params_by_tool,
        "messages": [AIMessage(content=text)],
    }


async def bpmn_execute_node(state: ParentState) -> dict[str, Any]:
    """BPMN 条件图执行：委托 bpmn_plan_runner；HITL 经 interrupt + execution_state 续跑。"""
    import json

    from langgraph.config import get_stream_writer

    from app.application.execution.bpmn_graph import build_execution_graph
    from app.application.execution.bpmn_plan_runner import (
        execute_bpmn_plan,
        resolve_bpmn_resume_start_node,
    )
    from app.application.execution.execution_context import ExecutionContext
    from app.application.execution.tool_executor import execute_tool_invoke
    from app.graph.hitl_interrupt import interrupt_or_raise
    from app.services.bpmn_execution_state import (
        clear_bpmn_execution_state,
        get_bpmn_execution_state,
    )
    from contracts.context import current_auth_token, current_thread_id
    from contracts.hitl import is_hitl_reject, merge_hitl_resume_args

    writer = get_stream_writer()
    flow_document = state.get("flow_document")
    if not isinstance(flow_document, dict):
        return {
            "route": "end",
            "messages": [AIMessage(content="BPMN 执行缺少 flow_document")],
        }

    params_by_tool = dict(state.get("plan_params") or {})
    user_message = str(state.get("user_message") or "")
    model_id = str(state.get("model_id") or "")
    thread_id = str(current_thread_id.get() or "")
    auth_token = current_auth_token.get()
    summaries: list[str] = []

    def _forward(event_name: str, payload: Any) -> None:
        if event_name not in (
            "tool_start",
            "tool_end",
            "plan_update",
            "message",
            "replan",
            "error",
        ):
            return
        custom: dict[str, Any] = {"sse_event": event_name}
        if isinstance(payload, dict):
            custom.update(payload)
        writer(custom)

    async def _run_plan(
        *,
        resume_ctx: ExecutionContext | None = None,
        resume_start_node_id: str | None = None,
    ) -> dict[str, Any] | None:
        """执行或续跑；遇 interrupt 则图内暂停。返回值非 None 表示提前结束。"""
        nonlocal summaries
        async for event_name, payload in execute_bpmn_plan(
            flow_document,
            params_by_tool,
            user_message,
            thread_id=thread_id,
            auth_token=auth_token,
            model_id=model_id,
            resume_ctx=resume_ctx,
            resume_start_node_id=resume_start_node_id,
        ):
            if event_name == "interrupt":
                # 暂存已由 bpmn_plan_runner 写入；interrupt 后节点将重启
                interrupt_or_raise(payload if isinstance(payload, dict) else {})
                return {"route": "end"}
            _forward(event_name, payload)
            if event_name == "message" and isinstance(payload, dict):
                delta = payload.get("delta")
                if delta:
                    summaries.append(str(delta))
            if event_name == "tool_end" and isinstance(payload, dict):
                raw = str(payload.get("result") or "")
                try:
                    data = json.loads(raw)
                    if isinstance(data, dict) and data.get("summary"):
                        summaries.append(str(data["summary"]))
                except json.JSONDecodeError, TypeError:
                    pass
            if event_name == "error":
                return {
                    "route": "end",
                    "messages": [
                        AIMessage(
                            content=str(
                                (payload or {}).get("message")
                                if isinstance(payload, dict)
                                else "BPMN 执行失败"
                            )
                        )
                    ],
                }
        return None

    # 节点重启后续跑：先取回 interrupt 结果，完成暂停工具，再从后继继续
    saved = get_bpmn_execution_state(thread_id) if thread_id else None
    if isinstance(saved, dict) and saved.get("interrupt_payload"):
        resume_value = interrupt_or_raise(dict(saved["interrupt_payload"] or {}))
        if is_hitl_reject(resume_value):
            clear_bpmn_execution_state(thread_id)
            msg = "已取消操作。如需调整，请重新描述您的需求。"
            return {
                "route": "end",
                "cancelled": True,
                "cancel_message": msg,
                "messages": [AIMessage(content=msg)],
            }

        ctx = ExecutionContext.from_state_dict(dict(saved.get("ctx") or {}))
        paused_id = str(saved.get("paused_node_id") or "")
        tool_name = str(saved.get("tool") or "")
        tool_args = merge_hitl_resume_args(
            resume_value,
            dict(saved.get("tool_args") or {}),
        )
        last_result = ""
        if tool_name:
            async for event_name, payload in execute_tool_invoke(
                tool_name,
                tool_args,
                auth_token=auth_token,
                thread_id=thread_id or None,
                hitl_confirm_bypass=True,
            ):
                if event_name == "interrupt":
                    # 嵌套 HITL（如补参后再 confirm）
                    set_payload = {
                        **saved,
                        "interrupt_payload": payload if isinstance(payload, dict) else {},
                        "tool_args": tool_args,
                        "ctx": ctx.to_state_dict(),
                    }
                    from app.services.bpmn_execution_state import set_bpmn_execution_state

                    set_bpmn_execution_state(thread_id, set_payload)
                    interrupt_or_raise(payload if isinstance(payload, dict) else {})
                    return {"route": "end"}
                _forward(event_name, payload)
                if event_name == "tool_end" and isinstance(payload, dict):
                    last_result = str(payload.get("result") or "")

        if paused_id and last_result:
            ctx.set_node_output(paused_id, last_result)
            node_type = "AUTO"
            if paused_id in ctx.node_runtimes:
                node_type = ctx.node_runtimes[paused_id].node_type or "AUTO"
            ctx.mark_node(paused_id, node_type, "done")
            _forward(
                "plan_update",
                {
                    "step_id": paused_id,
                    "node_id": paused_id,
                    "node_type": node_type,
                    "status": "done",
                    "tool": tool_name,
                },
            )

        graph = build_execution_graph(flow_document)
        start_from = resolve_bpmn_resume_start_node(graph, ctx, paused_id or None)
        # 清暂停标记后再续跑，避免嵌套中断误判
        clear_bpmn_execution_state(thread_id)
        early = await _run_plan(resume_ctx=ctx, resume_start_node_id=start_from)
        if early is not None:
            return early
        text = "".join(summaries) or "BPMN 计划执行完成。"
        return {"route": "end", "messages": [AIMessage(content=text)]}

    early = await _run_plan()
    if early is not None:
        return early
    text = "".join(summaries) or "BPMN 计划执行完成。"
    return {"route": "end", "messages": [AIMessage(content=text)]}


def _route_after_plan_confirm(state: ParentState) -> RouteKind:
    route = state.get("route")
    if route in ("plan_execute", "bpmn_execute", "end"):
        return route  # type: ignore[return-value]
    return "end"


def _route_after_device_gate(state: ParentState) -> RouteKind:
    route = state.get("route")
    if route == "react":
        return "react"
    return "end"


def build_parent_graph(*, model_id: str):
    """编译父 StateGraph；按 model_id 缓存子图（react/chat 绑定不同 create_agent）。"""
    from app.graph.agent_factory import get_agent, get_chat_agent

    cache_key = model_id or "__default__"
    if cache_key in _parent_graph_cache:
        return _parent_graph_cache[cache_key]

    react_agent = get_agent(model_id)
    chat_agent = get_chat_agent(model_id)

    workflow = StateGraph(ParentState)
    workflow.add_node("classify", classify_node)
    workflow.add_node("plan_confirm", plan_confirm_node)
    workflow.add_node("device_gate", device_gate_node)
    workflow.add_node("plan_execute", plan_execute_node)
    workflow.add_node("bpmn_execute", bpmn_execute_node)
    workflow.add_node("chat_direct", chat_agent)
    workflow.add_node("react", react_agent)

    workflow.add_edge(START, "classify")
    workflow.add_conditional_edges(
        "classify",
        _route_after_classify,
        {
            "chat_direct": "chat_direct",
            "plan_confirm": "plan_confirm",
            "device_gate": "device_gate",
            "react": "react",
        },
    )
    workflow.add_conditional_edges(
        "plan_confirm",
        _route_after_plan_confirm,
        {
            "plan_execute": "plan_execute",
            "bpmn_execute": "bpmn_execute",
            "end": END,
        },
    )
    workflow.add_conditional_edges(
        "device_gate",
        _route_after_device_gate,
        {"react": "react", "end": END},
    )
    workflow.add_edge("chat_direct", END)
    workflow.add_edge("react", END)
    workflow.add_edge("plan_execute", END)
    workflow.add_edge("bpmn_execute", END)

    from app.graph.agent_factory import _get_checkpointer

    compiled = workflow.compile(checkpointer=_get_checkpointer())
    _parent_graph_cache[cache_key] = compiled
    logger.info(
        "父 StateGraph 已编译: model_id=%s nodes=%s", model_id, list(compiled.get_graph().nodes)
    )
    return compiled


def reset_parent_graph_cache() -> None:
    """测试或热更新后清空父图缓存。"""
    _parent_graph_cache.clear()


def get_agent_topology(*, model_id: str = "") -> dict[str, Any]:
    """返回真实编译图拓扑（供 Trace / HTTP）。"""
    graph = build_parent_graph(model_id=model_id or "qwen3.7-plus")
    g = graph.get_graph()
    nodes = [{"id": n, "label": n} for n in g.nodes if n not in ("__start__", "__end__")]
    edges = [{"from": e.source, "to": e.target} for e in g.edges]
    return {
        "engine": "parent_state_graph",
        "nodes": nodes,
        "edges": edges,
        "mermaid": g.draw_mermaid() if hasattr(g, "draw_mermaid") else "",
    }
