"""BPMN 节点处理器注册表。"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from typing import Any, Protocol

from app.application.execution.bpmn_graph import ExecutionGraph, ExecutionNode
from app.application.execution.execution_context import ExecutionContext

NodeHandlerFn = Callable[
    [ExecutionNode, ExecutionContext, ExecutionGraph],
    AsyncIterator[tuple[str, dict[str, Any]]],
]


class NodeHandler(Protocol):
    """节点处理器协议。"""

    async def run(
        self,
        node: ExecutionNode,
        ctx: ExecutionContext,
        graph: ExecutionGraph,
    ) -> AsyncIterator[tuple[str, dict[str, Any]]]: ...


NODE_REGISTRY: dict[str, NodeHandlerFn] = {}


def register_node_handler(node_type: str, handler: NodeHandlerFn) -> None:
    """注册节点类型处理器（大小写不敏感）。"""
    NODE_REGISTRY[node_type.upper()] = handler
    NODE_REGISTRY[node_type.lower()] = handler


def get_node_handler(node_type: str) -> NodeHandlerFn | None:
    """按类型获取处理器。"""
    return NODE_REGISTRY.get(node_type) or NODE_REGISTRY.get(node_type.upper())
