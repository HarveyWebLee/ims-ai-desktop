"""D2 StateGraph stream_events(v3) 适配单测"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.application.execution.agent_stream import run_agent_stream
from app.graph.agent_stream_adapter import (
    iter_agent_sse_events,
    iter_state_graph_sse_events,
    supports_tool_calls_projection,
)


class TestStreamProjectionDetection:
    def test_supports_tool_calls_when_registered(self):
        class FakeStream:
            extensions = {"messages": 1, "tool_calls": 2}

        assert supports_tool_calls_projection(FakeStream()) is True

    def test_missing_tool_calls_for_state_graph(self):
        class FakeStream:
            extensions = {"messages": 1, "values": 2}

        assert supports_tool_calls_projection(FakeStream()) is False


class TestParentGraphStreamBridge:
    @pytest.mark.asyncio
    async def test_run_agent_stream_delegates_without_keyerror(self):
        """run_agent_stream 委托父图流，不得因投影缺失抛 KeyError。"""
        from app.persistence.bootstrap import init_persistence

        await init_persistence(None)

        async def fake_stream(**_kwargs):
            yield ("tool_start", {"tool": "navigate_to", "args": {"path": "设施管理"}})
            yield (
                "tool_end",
                {
                    "tool": "navigate_to",
                    "ok": True,
                    "summary": "已跳转",
                },
            )
            yield ("message", {"type": "text", "delta": "已为您处理"})

        events: list[tuple[str, dict]] = []
        with patch(
            "app.graph.parent_graph_stream.stream_parent_graph",
            side_effect=fake_stream,
        ):
            async for evt in run_agent_stream(
                thread_id="sg-stream-test",
                model_id="qwen3.7-plus",
                input_payload={"messages": [HumanMessage(content="去设施管理")]},
            ):
                events.append(evt)

        names = [e[0] for e in events]
        assert "error" not in names
        assert "tool_start" in names
        assert "tool_end" in names
        assert "message" in names


class TestStateGraphStreamAdapter:
    def test_iter_state_graph_emits_tool_pair(self):
        """values 增量解析：AIMessage.tool_calls + ToolMessage。"""

        class FakeMessagesStream:
            def __init__(self, tokens):
                self._tokens = list(tokens)

            @property
            def text(self):
                return iter(self._tokens)

        class FakeValuesChannel:
            def __init__(self, states):
                self._states = list(states)
                self._i = 0
                self._closed = False
                self._items = []
                self._error = None
                self._subscribed = False
                self._is_async = False

            def __iter__(self):
                while self._i < len(self._states):
                    yield self._states[self._i]
                    self._i += 1

        ai = AIMessage(
            content="",
            id="ai1",
            tool_calls=[
                {
                    "name": "query_alarms",
                    "args": {"start_time": "近三天"},
                    "id": "tc1",
                    "type": "tool_call",
                }
            ],
        )
        tool = ToolMessage(
            content=json.dumps({"ok": True, "summary": "成功"}),
            tool_call_id="tc1",
            name="query_alarms",
            id="tm1",
        )

        class FakeStream:
            extensions = {"messages": object(), "values": object()}
            interrupted = False
            interrupts = []

            def interleave(self, *names):
                msg_stream = FakeMessagesStream(["好的"])
                values = [
                    {"messages": [HumanMessage(content="查告警", id="h1")]},
                    {"messages": [HumanMessage(content="查告警", id="h1"), ai]},
                    {"messages": [HumanMessage(content="查告警", id="h1"), ai, tool]},
                    {"messages": [HumanMessage(content="查告警", id="h1"), ai, tool]},
                ]
                vi = iter(values)
                mi = iter([msg_stream])
                order = ["values", "messages", "values", "values", "values"]
                for name in order:
                    if name == "messages":
                        yield ("messages", next(mi))
                    else:
                        yield ("values", next(vi))

        events = list(iter_state_graph_sse_events(FakeStream()))
        assert ("tool_start", {"tool": "query_alarms", "args": {"start_time": "近三天"}}) in events
        assert any(e[0] == "tool_end" and e[1]["tool"] == "query_alarms" for e in events)
        assert ("message", {"type": "text", "delta": "好的"}) in events

    def test_pump_emits_tool_end_before_agent_llm(self):
        """tool_start 后应在 ToolMessage 落盘即 emit tool_end，不等待 agent 二次 LLM。"""

        class FakeMessagesStream:
            @property
            def text(self):
                return iter([])

        ai = AIMessage(
            content="",
            id="ai-pump",
            tool_calls=[
                {
                    "name": "query_devices",
                    "args": {"search": "门禁"},
                    "id": "tc-pump",
                    "type": "tool_call",
                }
            ],
        )
        tool = ToolMessage(
            content='{"ok": true, "summary": "成功"}',
            tool_call_id="tc-pump",
            name="query_devices",
            id="tm-pump",
        )

        class FakeStream:
            extensions = {"messages": object(), "values": object()}
            interrupted = False
            interrupts = []
            _latest: dict | None = None
            _pump_steps = 0

            def _pump_next(self) -> bool:
                self._pump_steps += 1
                if self._pump_steps == 1:
                    self._latest = {"messages": [HumanMessage(content="查", id="h1"), ai, tool]}
                    return True
                return False

            def interleave(self, *names):
                values = [
                    {"messages": [HumanMessage(content="查", id="h1")]},
                    {"messages": [HumanMessage(content="查", id="h1"), ai]},
                ]
                for state in values:
                    yield ("values", state)

        events = list(iter_state_graph_sse_events(FakeStream()))
        names = [e[0] for e in events]
        tool_start_idx = names.index("tool_start")
        tool_end_idx = names.index("tool_end")
        assert tool_end_idx > tool_start_idx
        assert events[tool_end_idx][1]["tool"] == "query_devices"

    def test_tool_error_stopped_pump_emits_tool_end_and_waits_llm(self):
        """工具快速失败（pump stopped）仍 emit tool_end，并继续 interleave 等 LLM 文本。"""

        class FakeMessagesStream:
            def __init__(self, tokens):
                self._tokens = list(tokens)

            @property
            def text(self):
                return iter(self._tokens)

        ai = AIMessage(
            content="",
            id="ai-err",
            tool_calls=[
                {
                    "name": "send_device_cmd",
                    "args": {
                        "device_code": "D1",
                        "variable_name": "门控制状态",
                        "variable_value": "1",
                    },
                    "id": "tc-err",
                    "type": "tool_call",
                }
            ],
        )
        tool = ToolMessage(
            content='{"ok": false, "summary": "变量匹配到多个可写项"}',
            tool_call_id="tc-err",
            name="send_device_cmd",
            id="tm-err",
        )

        class FakeStream:
            extensions = {"messages": object(), "values": object()}
            interrupted = False
            interrupts = []
            _latest = {"messages": [HumanMessage(content="下发", id="h1"), ai]}

            def _pump_next(self) -> bool:
                self._latest = {
                    "messages": [HumanMessage(content="下发", id="h1"), ai, tool],
                }
                return False

            def interleave(self, *names):
                yield (
                    "values",
                    {"messages": [HumanMessage(content="下发", id="h1"), ai]},
                )
                yield (
                    "messages",
                    FakeMessagesStream(["变量名存在歧义，请改用 varName。"]),
                )

        events = list(iter_state_graph_sse_events(FakeStream()))
        assert any(e[0] == "tool_start" and e[1]["tool"] == "send_device_cmd" for e in events)
        assert any(e[0] == "tool_end" and e[1]["tool"] == "send_device_cmd" for e in events)
        assert ("message", {"type": "text", "delta": "变量名存在歧义，请改用 varName。"}) in events

    def test_pump_stopped_after_sync_tool_still_emits_tool_end(self):
        """pump 返回 stopped 时若 _latest 已有 ToolMessage，仍应 emit tool_end。"""

        class FakeMessagesStream:
            @property
            def text(self):
                return iter([])

        ai = AIMessage(
            content="",
            id="ai-sync",
            tool_calls=[
                {
                    "name": "query_devices",
                    "args": {"search": "门"},
                    "id": "tc-sync",
                    "type": "tool_call",
                }
            ],
        )
        tool = ToolMessage(
            content='{"ok": true, "summary": "共 1 台"}',
            tool_call_id="tc-sync",
            name="query_devices",
            id="tm-sync",
        )

        class FakeStream:
            extensions = {"messages": object(), "values": object()}
            interrupted = False
            interrupts = []
            _latest = {"messages": [HumanMessage(content="查", id="h1"), ai]}

            def _pump_next(self) -> bool:
                # 模拟同步 ToolNode：pump 内完成工具并写入 _latest，再返回 False
                self._latest = {
                    "messages": [HumanMessage(content="查", id="h1"), ai, tool],
                }
                return False

            def interleave(self, *names):
                yield (
                    "values",
                    {"messages": [HumanMessage(content="查", id="h1"), ai]},
                )

        events = list(iter_state_graph_sse_events(FakeStream()))
        assert any(e[0] == "tool_start" and e[1]["tool"] == "query_devices" for e in events)
        assert any(e[0] == "tool_end" and e[1]["tool"] == "query_devices" for e in events)
        assert not any(e[0] == "error" for e in events)

    def test_tool_pump_prefers_answered_over_later_interrupt(self):
        """本工具 ToolMessage 已落盘时，即使 stream 已 interrupt，仍应先 emit tool_end。"""

        ai = AIMessage(
            content="",
            id="ai-detail",
            tool_calls=[
                {
                    "name": "get_device_detail",
                    "args": {"device_name": "716门禁"},
                    "id": "tc-detail",
                    "type": "tool_call",
                }
            ],
        )
        tool = ToolMessage(
            content='{"ok":true,"summary":"在线"}',
            name="get_device_detail",
            tool_call_id="tc-detail",
        )

        class FakeStream:
            extensions = {"messages": object(), "values": object()}
            interrupted = True
            interrupts = [
                {
                    "value": {
                        "type": "confirm",
                        "tool": "send_device_cmd",
                        "message": "确认开门？",
                    }
                }
            ]
            _latest = {
                "messages": [HumanMessage(content="查状态", id="h1"), ai, tool],
            }

            def _pump_next(self) -> bool:
                return False

            def interleave(self, *names):
                yield (
                    "values",
                    {"messages": [HumanMessage(content="查状态", id="h1"), ai]},
                )

        events = list(iter_state_graph_sse_events(FakeStream()))
        assert any(e[0] == "tool_start" and e[1]["tool"] == "get_device_detail" for e in events)
        assert any(e[0] == "tool_end" and e[1]["tool"] == "get_device_detail" for e in events)
        assert any(e[0] == "interrupt" for e in events)
        tool_end_idx = next(i for i, e in enumerate(events) if e[0] == "tool_end")
        interrupt_idx = next(i for i, e in enumerate(events) if e[0] == "interrupt")
        assert tool_end_idx < interrupt_idx

    def test_tool_pump_stopped_emits_interrupt_from_stream_flags(self):
        """pump 停止时优先读 stream.interrupted / interrupts（同步不再读 AsyncPostgres）。"""

        ai = AIMessage(
            content="",
            id="ai-hitl",
            tool_calls=[
                {
                    "name": "send_device_cmd",
                    "args": {"device_code": "D1"},
                    "id": "tc-hitl",
                    "type": "tool_call",
                }
            ],
        )

        hitl_payload = {
            "type": "confirm",
            "tool": "send_device_cmd",
            "message": "确认下发指令？",
        }

        class FakeInterrupt:
            value = hitl_payload

        class FakeStream:
            extensions = {"messages": object(), "values": object()}
            interrupted = True
            interrupts = [FakeInterrupt()]
            _latest = {"messages": [HumanMessage(content="开门", id="h1"), ai]}

            def _pump_next(self) -> bool:
                return False

            def interleave(self, *names):
                yield (
                    "values",
                    {"messages": [HumanMessage(content="开门", id="h1"), ai]},
                )

        events = list(iter_state_graph_sse_events(FakeStream(), model_id="qwen3.7-plus"))

        assert ("tool_start", {"tool": "send_device_cmd", "args": {"device_code": "D1"}}) in events
        assert ("interrupt", hitl_payload) in events
        assert not any(e[0] == "error" for e in events)

    def test_iter_state_graph_emits_multiple_tool_starts(self):
        """同轮多个 tool_calls 应各 emit tool_start。"""

        class FakeMessagesStream:
            def __init__(self, tokens):
                self._tokens = list(tokens)

            @property
            def text(self):
                return iter(self._tokens)

        ai = AIMessage(
            content="",
            id="ai-multi",
            tool_calls=[
                {
                    "name": "query_alarms",
                    "args": {"start_time": "近三天"},
                    "id": "tc1",
                    "type": "tool_call",
                },
                {
                    "name": "navigate_to",
                    "args": {"path": "设施管理"},
                    "id": "tc2",
                    "type": "tool_call",
                },
            ],
        )
        tool1 = ToolMessage(
            content='{"ok": true}',
            tool_call_id="tc1",
            name="query_alarms",
            id="tm1",
        )
        tool2 = ToolMessage(
            content='{"ok": true}',
            tool_call_id="tc2",
            name="navigate_to",
            id="tm2",
        )

        class FakeStream:
            extensions = {"messages": object(), "values": object()}
            interrupted = False
            interrupts = []

            def interleave(self, *names):
                msg_stream = FakeMessagesStream([])
                values = [
                    {"messages": [HumanMessage(content="查告警并跳转", id="h1")]},
                    {"messages": [HumanMessage(content="查告警并跳转", id="h1"), ai]},
                    {
                        "messages": [
                            HumanMessage(content="查告警并跳转", id="h1"),
                            ai,
                            tool1,
                            tool2,
                        ]
                    },
                ]
                vi = iter(values)
                mi = iter([msg_stream])
                for name in ["values", "values", "values"]:
                    if name == "messages":
                        yield ("messages", next(mi))
                    else:
                        yield ("values", next(vi))

        events = list(iter_state_graph_sse_events(FakeStream()))
        tool_starts = [e for e in events if e[0] == "tool_start"]
        assert len(tool_starts) == 2
        assert {e[1]["tool"] for e in tool_starts} == {"query_alarms", "navigate_to"}

    def test_iter_state_graph_interrupt_stops_after_first_tool(self):
        """interrupt 时仅 emit 第一个 tool_start，不继续后续 tool。"""

        class FakeMessagesStream:
            @property
            def text(self):
                return iter([])

        ai = AIMessage(
            content="",
            id="ai-int",
            tool_calls=[
                {"name": "query_alarms", "args": {}, "id": "tc1", "type": "tool_call"},
                {"name": "navigate_to", "args": {"path": "x"}, "id": "tc2", "type": "tool_call"},
            ],
        )

        class FakeStream:
            extensions = {"messages": object(), "values": object()}
            interrupted = True
            interrupts = [{"value": {"type": "ask_params", "tool": "query_alarms"}}]

            def interleave(self, *names):
                values = [
                    {"messages": [HumanMessage(content="查", id="h1")]},
                    {"messages": [HumanMessage(content="查", id="h1"), ai]},
                ]
                for state in values:
                    yield ("values", state)

        events = list(iter_state_graph_sse_events(FakeStream()))
        tool_starts = [e for e in events if e[0] == "tool_start"]
        assert len(tool_starts) == 1
        assert tool_starts[0][1]["tool"] == "query_alarms"
        assert any(e[0] == "interrupt" for e in events)

    def test_interrupt_flushes_tool_end_in_same_values_batch(self):
        """同批 values 含 ToolMessage 时，HITL 提前 return 仍应先 emit tool_end。"""

        ai_detail = AIMessage(
            content="",
            id="ai-batch",
            tool_calls=[
                {
                    "name": "get_device_detail",
                    "args": {"device_name": "716门禁"},
                    "id": "tc-batch",
                    "type": "tool_call",
                }
            ],
        )
        tool_detail = ToolMessage(
            content='{"ok":true,"summary":"在线"}',
            name="get_device_detail",
            tool_call_id="tc-batch",
            id="tm-batch",
        )

        class FakeStream:
            extensions = {"messages": object(), "values": object()}
            interrupted = True
            interrupts = [
                {
                    "value": {
                        "type": "confirm",
                        "tool": "send_device_cmd",
                        "message": "确认开门？",
                    }
                }
            ]
            # pump 期间 _latest 尚无 ToolMessage，模拟图内结果仅出现在 values 增量
            _latest = {
                "messages": [HumanMessage(content="查状态", id="h1"), ai_detail],
            }

            def _pump_next(self) -> bool:
                return False

            def interleave(self, *names):
                yield (
                    "values",
                    {
                        "messages": [
                            HumanMessage(content="查状态", id="h1"),
                            ai_detail,
                            tool_detail,
                        ]
                    },
                )

        events = list(iter_state_graph_sse_events(FakeStream()))
        assert any(e[0] == "tool_end" and e[1]["tool"] == "get_device_detail" for e in events)
        assert any(e[0] == "interrupt" for e in events)
        tool_end_idx = next(i for i, e in enumerate(events) if e[0] == "tool_end")
        interrupt_idx = next(i for i, e in enumerate(events) if e[0] == "interrupt")
        assert tool_end_idx < interrupt_idx

    def test_iter_state_graph_emits_custom_tool_sse(self):
        """plan_execute 的 get_stream_writer custom 投影应产出 __custom__。"""

        class FakeStream:
            extensions = {
                "messages": object(),
                "values": object(),
                "custom": object(),
            }
            interrupted = False
            interrupts: list = []

            def interleave(self, *names):
                assert "custom" in names
                yield (
                    "custom",
                    {"sse_event": "tool_start", "tool": "query_alarms", "args": {}},
                )
                yield (
                    "custom",
                    {
                        "sse_event": "tool_end",
                        "tool": "query_alarms",
                        "result": '{"ok": true}',
                    },
                )

        events = list(iter_state_graph_sse_events(FakeStream()))
        customs = [e[1] for e in events if e[0] == "__custom__"]
        assert [c.get("sse_event") for c in customs] == ["tool_start", "tool_end"]
        assert customs[0]["tool"] == "query_alarms"

    def test_tool_end_not_flooded_on_values_shrink_or_orphan_messages(self):
        """AC-07：values 回缩 / 孤儿 ToolMessage 不得重复 tool_end。"""
        h = HumanMessage(content="导出近三天告警", id="h1")
        ai = AIMessage(
            content="",
            id="ai1",
            tool_calls=[
                {
                    "name": "download_file",
                    "args": {"start_time": "近三天"},
                    "id": "tc1",
                    "type": "tool_call",
                }
            ],
        )

        class FakeStream:
            extensions = {"messages": object(), "values": object()}
            interrupted = False
            interrupts: list = []

            def __init__(self) -> None:
                self._latest = {"messages": [h, ai]}

            def _pump_next(self) -> bool:
                return False

            def interleave(self, *names):
                yield ("values", {"messages": [h, ai]})
                for i in range(30):
                    tool = ToolMessage(
                        content=json.dumps({"ok": True, "summary": "ready"}),
                        tool_call_id="tc1",
                        name="download_file",
                        id=f"tm-{i}",
                    )
                    orphan = ToolMessage(
                        content=json.dumps({"ok": True, "summary": f"orphan-{i}"}),
                        tool_call_id="",
                        name="download_file",
                    )
                    self._latest = {"messages": [h, ai, tool, orphan]}
                    if i % 2 == 0:
                        yield ("values", {"messages": [h]})
                    yield ("values", {"messages": [h, ai, tool, orphan]})

        events = list(iter_state_graph_sse_events(FakeStream()))
        starts = [e for e in events if e[0] == "tool_start"]
        ends = [e for e in events if e[0] == "tool_end"]
        assert len(starts) == 1
        assert len(ends) <= 1

    def test_iter_agent_sse_events_dispatches(self):
        class FakeStream:
            extensions = {"tool_calls": 1}

            def interleave(self, *names):
                assert names == ("messages", "tool_calls")
                yield ("messages", type("M", (), {"text": iter(["hi"])})())

        events = list(iter_agent_sse_events(FakeStream()))
        assert ("message", {"type": "text", "delta": "hi"}) in events


class TestAsyncGraphRunStreamAdapter:
    @pytest.mark.asyncio
    async def test_aiter_message_text_tokens_async_projection(self):
        """message.text 为 AsyncProjection 时应 async for，不能同步 for。"""
        from app.graph.agent_stream_adapter import _aiter_message_text_tokens

        class FakeAsyncText:
            def __aiter__(self):
                async def _gen():
                    for t in ("你好", "世界"):
                        yield t

                return _gen()

        class FakeMessage:
            text = FakeAsyncText()

        tokens = [t async for t in _aiter_message_text_tokens(FakeMessage())]
        assert tokens == ["你好", "世界"]

    @pytest.mark.asyncio
    async def test_iter_agent_sse_events_async_routes_without_interleave(self):
        """AsyncGraphRunStream 无 interleave 时应走 _async_iter_state_graph_sse_events。"""
        from app.graph.agent_stream_adapter import iter_agent_sse_events_async

        class FakeAsyncStream:
            extensions = {"messages": object(), "values": object()}

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return None

        routed = False

        async def fake_async_iter(_stream, *, model_id=""):
            nonlocal routed
            routed = True
            yield ("message", {"type": "text", "delta": "hi"})

        events: list[tuple[str, dict]] = []
        with patch(
            "app.graph.agent_stream_adapter._async_iter_state_graph_sse_events",
            side_effect=fake_async_iter,
        ):
            async for evt in iter_agent_sse_events_async(_async_return(FakeAsyncStream())):
                events.append(evt)

        assert routed is True
        assert events == [("message", {"type": "text", "delta": "hi"})]


async def _async_return(value: Any) -> Any:
    return value


class TestFlowIrTokenGate:
    def test_suppresses_flow_ir_json_chunks(self):
        from app.graph.agent_stream_adapter import _FlowIrTokenGate, _is_flow_ir_leak_text

        assert _is_flow_ir_leak_text('{"conditions": [], "entry": "", "nodes": []}')
        gate = _FlowIrTokenGate()
        out: list[str] = []
        for chunk in [
            "{\n",
            '"conditions"',
            ": [],\n",
            '"entry"',
            ': "",\n',
            '"nodes"',
            ": []\n}",
        ]:
            out.extend(gate.feed(chunk))
        out.extend(gate.flush())
        assert out == []

    def test_passes_normal_assistant_text(self):
        from app.graph.agent_stream_adapter import _FlowIrTokenGate

        gate = _FlowIrTokenGate()
        out: list[str] = []
        for chunk in ["已", "为您", "下发指令"]:
            out.extend(gate.feed(chunk))
        out.extend(gate.flush())
        assert "".join(out) == "已为您下发指令"
