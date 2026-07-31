"""AC-30/31：BPMN HITL 续跑不重跑已完成节点；reject 清理 execution_state。"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from tests.test_bpmn_execution_kernel import _conditional_door_document

from app.application.execution.bpmn_graph import build_execution_graph
from app.application.execution.execution_context import ExecutionContext
from app.graph.parent_graph import bpmn_execute_node
from app.services.bpmn_execution_state import (
    clear_bpmn_execution_state,
    get_bpmn_execution_state,
    set_bpmn_execution_state,
)


def _ctx_after_query_online() -> ExecutionContext:
    ctx = ExecutionContext(thread_id="t-bpmn-hitl", user_message="开门")
    ctx.set_node_output(
        "step_query",
        json.dumps({"ok": True, "onlineStatus": "在线"}, ensure_ascii=False),
    )
    ctx.mark_node("step_query", "AUTO", "done")
    ctx.mark_node("cond_online", "CONDITION", "done", matched_branch_key="if_online")
    ctx.mark_node("step_open", "AUTO", "awaiting_hitl")
    return ctx


@pytest.fixture(autouse=True)
def _clean_state():
    clear_bpmn_execution_state("t-bpmn-hitl")
    yield
    clear_bpmn_execution_state("t-bpmn-hitl")


@pytest.mark.asyncio
async def test_ac30_resume_does_not_rerun_device_detail():
    """续跑只完成开门工具，不二次调用 get_device_detail。"""
    tid = "t-bpmn-hitl"
    doc = _conditional_door_document()
    ctx = _ctx_after_query_online()
    set_bpmn_execution_state(
        tid,
        {
            "paused_node_id": "step_open",
            "ctx": ctx.to_state_dict(),
            "interrupt_payload": {
                "type": "confirm",
                "tool": "send_device_cmd",
                "message": "确认开门？",
            },
            "tool": "send_device_cmd",
            "tool_args": {"device_name": "716门禁", "action": "开门"},
        },
    )

    invoked: list[str] = []

    async def fake_invoke(tool_name: str, args: dict[str, Any], **_kwargs):
        invoked.append(tool_name)
        yield ("tool_start", {"tool": tool_name, "args": args})
        yield (
            "tool_end",
            {
                "tool": tool_name,
                "result": json.dumps({"ok": True, "summary": "已开门"}, ensure_ascii=False),
            },
        )

    async def empty_continue(*_a, **_k):
        if False:
            yield ("done", {})
        return
        yield  # pragma: no cover

    writer = MagicMock()
    with (
        patch("contracts.context.current_thread_id") as mock_tid,
        patch("app.graph.hitl_interrupt.interrupt_or_raise", return_value={"type": "approve"}),
        patch(
            "app.application.execution.tool_executor.execute_tool_invoke",
            side_effect=fake_invoke,
        ),
        patch(
            "app.application.execution.bpmn_plan_runner.execute_bpmn_plan",
            side_effect=empty_continue,
        ),
        patch("langgraph.config.get_stream_writer", return_value=writer),
    ):
        mock_tid.get.return_value = tid
        result = await bpmn_execute_node(
            {
                "flow_document": doc,
                "plan_params": {},
                "user_message": "开门",
                "model_id": "deepseek-v4-flash",
            }
        )

    assert result.get("route") == "end"
    assert invoked == ["send_device_cmd"]
    assert "get_device_detail" not in invoked
    assert get_bpmn_execution_state(tid) is None


@pytest.mark.asyncio
async def test_ac31_reject_clears_execution_state():
    """拒绝 HITL 后清除 bpmn_execution_state。"""
    tid = "t-bpmn-hitl"
    doc = _conditional_door_document()
    ctx = _ctx_after_query_online()
    set_bpmn_execution_state(
        tid,
        {
            "paused_node_id": "step_open",
            "ctx": ctx.to_state_dict(),
            "interrupt_payload": {
                "type": "confirm",
                "tool": "send_device_cmd",
                "message": "确认开门？",
            },
            "tool": "send_device_cmd",
            "tool_args": {},
        },
    )

    with (
        patch("contracts.context.current_thread_id") as mock_tid,
        patch(
            "app.graph.hitl_interrupt.interrupt_or_raise",
            return_value={"type": "reject"},
        ),
        patch("langgraph.config.get_stream_writer", return_value=MagicMock()),
    ):
        mock_tid.get.return_value = tid
        result = await bpmn_execute_node(
            {
                "flow_document": doc,
                "plan_params": {},
                "user_message": "开门",
                "model_id": "deepseek-v4-flash",
            }
        )

    assert result.get("cancelled") is True
    assert get_bpmn_execution_state(tid) is None


@pytest.mark.asyncio
async def test_ac28_kernel_offline_branch():
    """AC-28：离线支执行、开门 skipped（内核级）。"""
    from tests.test_bpmn_execution_kernel import (
        _collect_events,
        _conditional_door_document,
        _make_stream_step,
    )

    doc = _conditional_door_document()
    stream = _make_stream_step(
        {
            "get_device_detail": json.dumps(
                {"ok": True, "onlineStatus": "离线"},
                ensure_ascii=False,
            ),
            "query_device_history": json.dumps(
                {"ok": True, "summary": "历史"},
                ensure_ascii=False,
            ),
        }
    )
    events = await _collect_events(doc, stream_step=stream)
    tools = [e[1]["tool"] for e in events if e[0] == "tool_end"]
    assert tools == ["get_device_detail", "query_device_history"]
    skipped = [e[1] for e in events if e[0] == "plan_update" and e[1].get("status") == "skipped"]
    assert any(s.get("node_id") == "step_open" for s in skipped)


@pytest.mark.asyncio
async def test_d3_auth_failure_marks_error_not_skipped():
    """鉴权失败应标 error，不得当作用户取消 skipped。"""
    from app.application.execution.bpmn_graph import ExecutionNode
    from app.application.execution.node_handlers.auto import run_auto_node

    node = ExecutionNode(
        id="step_q",
        type="AUTO",
        data={"title": "查", "tool": "query_alarms"},
    )
    ctx = ExecutionContext()
    graph = build_execution_graph(
        {
            "nodes": [
                {"id": "start_0", "type": "start", "data": {}},
                {"id": "step_q", "type": "AUTO", "data": {"tool": "query_alarms"}},
                {"id": "end_0", "type": "end", "data": {}},
            ],
            "edges": [
                {"sourceNodeID": "start_0", "targetNodeID": "step_q"},
                {"sourceNodeID": "step_q", "targetNodeID": "end_0"},
            ],
        }
    )

    async def stream_step(_node, _params, _msg):
        yield ("tool_start", {"tool": "query_alarms", "args": {}})
        yield (
            "tool_end",
            {
                "tool": "query_alarms",
                "result": json.dumps(
                    {
                        "ok": False,
                        "summary": "请先登录",
                        "data": {"error_code": "authentication_required"},
                    },
                    ensure_ascii=False,
                ),
            },
        )

    events = [
        e
        async for e in run_auto_node(
            node, ctx, graph, params={}, user_message="", stream_step=stream_step
        )
    ]
    updates = [e[1] for e in events if e[0] == "plan_update"]
    assert updates[-1]["status"] == "error"
    assert ctx.node_runtimes["step_q"].status == "error"
