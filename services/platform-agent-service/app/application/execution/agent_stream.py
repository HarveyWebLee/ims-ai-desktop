"""父图流式入口：委托 ``stream_parent_graph``。"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any


async def run_agent_stream(
    *,
    thread_id: str,
    model_id: str,
    input_payload: dict[str, Any] | Any,
    auth_token: str | None = None,
) -> AsyncIterator[tuple[str, dict[str, Any]]]:
    """父图 ``astream_events(v3)`` → SSE 事件元组。"""
    from app.graph.parent_graph_stream import stream_parent_graph

    async for event in stream_parent_graph(
        thread_id=thread_id,
        model_id=model_id,
        input_payload=input_payload,
        auth_token=auth_token,
    ):
        yield event
